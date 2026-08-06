# CrossPlatform R76 — 十二路掃描合成報告（去重／分級／修復序）

> **產出角色**：合成員（唯讀）。本檔對 R76 十二路掃描回傳的 **78 筆原始發現**做去重、假陽性剔除、
> 重新分級與修復序排定。**本檔沒有改動任何生產碼、鎖檔、缺陷帳本或設定**。
>
> **環境**：Windows 11 Pro build 26200／PowerShell 5.1.26100.8875／venv Python 3.11.9／
> `HEAD=4ee955e`／git 2.51.0.windows.1。日期 2026-08-05。
>
> **🔴 本檔的所有「已驗證」皆指合成員本人在本輪真跑過的指令**（見〈附錄 A：合成員親驗紀錄〉）。
> 凡我沿用原掃描員證據而未親驗者，證據強度欄一律標 `引用`，不標 `已親驗`。

---

## 0. 一頁結論

### 0.1 數量

| 項目 | 數 |
|------|-----|
| 原始發現（12 維） | 78 |
| 去重後 | **67**（合併 11 筆：見 §2 去重帳） |
| 合成員本輪**新**發現（不在 78 筆內） | **1**（R76-00——**由本檔自身的存在觸發**，見 §0.2） |
| **P0** | **2** |
| **P1** | **16** |
| P2 | 32 |
| P3 | 18 |
| 判定「不該修／需授權」 | 10 類（見 §5） |
| 我下修嚴重度的 | 2 筆（R76-47、R76-67；理由見 §3 備註） |
| 我判定「不是缺陷、是報表」而移出發現表的 | 1 筆（Scan-T 第 10 筆，見 §5.10） |
| 缺席維度 | **0**（11 個已定義維度全跑，另加 Q3-Skipped 專項；見 §4.3） |

### 0.2 兩筆 P0

#### R76-00｜🔴 **本檔的存在當場讓一道根層閘門轉紅，而修它的唯一登記點零 LOC 餘裕 ⇒ 兩道棘輪互相死鎖**

**這一筆不在 12 維回傳的 78 筆內——它是我寫完本檔後複驗才顯形的，而且肇事者就是本檔。**
上一版本檔（同一任務的中斷回合）在 §附錄 A 第 1 項記載 `check_defect_log_crossref.py` → **rc=0**；
那是**在本檔被寫到磁碟之前**量的。本檔落地後我重跑，逐字：

```
RC=1
❌ 具名治理文件涵蓋面與磁碟脫節（1 筆）：
  - CrossPlatform_R76_Scan_Findings.md：符合具名治理文件的命名慣例（CrossPlatform_*.md）
    卻未登記進 check_defect_log_crossref.py 的 _GOVERNANCE_DOCS —— 未登記＝該檔同時逸出
    **體積守門**與 archive_defect_log 的**指針稽核**…
```

三件事同時成立，逐項都已機械確認：

1. **它擋住每一次 push、也擋雲端。** rc 有兩個硬消費者：`tools/git-hooks/pre-push:291` 的八支
   快層守門迴圈（R69 起**任何 push 皆跑**）與 `.github/workflows/root-infra-ci.yml:436`。
2. **它讓 §0.3 序 1 那 8 筆孤兒列的警告「消失」了，但缺陷沒消失。** 該檢查在
   `check_defect_log_crossref.py:1297` 就 `return 1` **早退**，孤兒檢查與那 8 筆
   `⚠️ 當前輪時鐘 fail-open 窗口` 現在**根本跑不到**（實測輸出總共只有 2 行）。
   ⇒ 這是本輪第二次證實「一個先跑的閘門會遮蔽後面閘門的訊號」，而遮蔽方向是**看起來變乾淨**。
3. **修法被另一道棘輪鎖死。** 工具自己給的第一條出口是「在 `_GOVERNANCE_DOCS` 補一筆」，
   而 `_GOVERNANCE_DOCS`（`:1169`）一筆一行 ⇒ **+1 行**；該檔現值
   **1474/1474（餘裕 0）**，判準 `check_loc_budget.check_special_files():286` 逐字
   `if actual > max_lines` ⇒ 1475 > 1474 **當場 violation**，pre-push 的 AutoClaude leg
   與 `autoclaude-ci` 同時紅。**兩道棘輪的合法動作互為對方的違規。**

**兩條出口（必須擇一，且都要在本輪動任何 push 之前做）**：

- **(a) 零成本、我建議先用這條**：把本檔改名成不符合 `CrossPlatform_*.md` 慣例的檔名
  （工具訊息自己列出這條出口，逐字：「若它確實不該受治理文件義務管，請改名成不符合該慣例的
  檔名，讓『不管』也是一個看得見的決定」）。**代價**：得回答「本檔到底該不該受治理文件義務管」
  ——我的判斷是**該管**（它會被下一輪引用、會長大、正是體積守門與指針稽核的標的），所以 (a) 是
  止血不是解法。
- **(b) 正解**：先執行 R76-16 的「騰餘裕」那一半（把 `check_defect_log_crossref.py` 從
  1474/1474 降下來），再登記本檔並在檔內寫明它為何屬於治理文件類。
  ⇒ **這使 R76-16 由「序 1」升為整輪的第 0 個動作**，見 §0.3 修正後的順序。

> 🔴 **這一筆的方法論價值高於它的修復成本**：它不是「鎖壞了」，而是**兩道各自正確的鎖在
> 交界處產生了不可滿足的狀態**——與 R75 頭號教訓（判準的比較對象不得隨被它所判的動作而改變）
> 同一族，但這次是**跨兩道鎖**：A 鎖要求你加一行，B 鎖禁止你加那一行。
> 本 repo 既有的「射程失明」清單裡沒有這個形態，建議在 Scan-H 補一條必跑項：
> **「新鎖要求的補救動作，是否會違反另一道既有硬閘？」**（見 §7 建議新增判準）

#### R76-01｜Windows 上 `git clone` 到稍長的目錄會產出「半套 checkout」，而唯一解藥只存在於「已 clone 好」的 local config。

我以單變因 A/B 親驗，而且**比原掃描員報的更嚴重**：

```
target len = 168
=== A) no flag rc=128 ===
error: unable to create file AISDLC_SDD/AISDLC_SDD_v0.01/build/reports/verification/PHASE-G-FINAL-DOD-AUDIT-2026-04-27.md: Filename too long
（另 5 行同類）
A bootstrap.ps1 present? False
=== B) with core.longpaths=true rc=0 ===
B bootstrap.ps1 present? True
A files=301  B files=27523  missing=27222
```

- 168 字元的 checkout 根 ⇒ **27,523 支 tracked 檔只落地 301 支**（原掃描員在 125 字元下量到缺 414 支；損害隨路徑長度非線性放大）。
- `tools\bootstrap.ps1` **不在** A 的磁碟上 ⇒ ONBOARDING 教的第一步就不存在。
- 旗標的居所我也查了：`git config --system` rc=1、`--global` rc=1、主 checkout `--local` → `true`。
  **也就是說：保護只在「已經成功 clone 過的那個 repo 裡」，fresh clone 零保護。**
- 全庫零文件教過 `git clone` 指令（原掃描員 `git grep 'git clone'` 對六份權威文件 rc=1）。

這直接命中掌舵者第 1 點（Windows 部署不得有相容性 bug）與第 3 點（mac 開發時對 Windows 的落差）：
mac 側 PATH_MAX 1024/4096 結構上沒有這個形態，所以只在 mac 開發的人永遠不會發現。

### 0.3 本輪必修清單（依序，不可換序的已標「⛔ 相依」）

> 🔴 **R76-00 落地後本表已重排**（原表把 R76-04 排序 0、R76-16 排序 1）。改動理由：
> `check_defect_log_crossref.py` **現在就已經 rc=1**（不是「等 R76 寫第一列帳本才會紅」），
> 而唯一的登記式修法需要該檔的 LOC 餘裕 ⇒ **騰餘裕變成整輪的第一個動作**。

| 序 | ID | 為什麼是「本輪必修」 |
|----|-----|----------------------|
| **0** | **R76-00** | ⛔ **現在就是紅的**（我實測 rc=1），且擋 pre-push 與 root-infra-ci。先用出口 (a)（改名）止血，或直接走序 1→2 的正解。**在這一筆解掉之前，本輪任何 push 都會被擋** |
| **1** | R76-16 | ⛔ **升為第一個程式碼動作**（原排序 1，因 R76-00 而成為它的前置）。六支 raw-line 棘輪餘裕 0~2 行；R76-00 的正解要動的 `check_defect_log_crossref.py` 餘裕正好是 **0**，序 3 要動的 `archive_defect_log.py`(1507/1507) 也是 **0** ⇒ 不先騰餘裕，兩包一動就撞硬閘並被要求「先重構再具名入帳」 |
| **2** | **R76-00(b)** | 騰出餘裕後登記本檔進 `_GOVERNANCE_DOCS`，並在本檔內寫明它為何屬於治理文件類；若序 0 已用改名止血，此步是把止血換成正解 |
| **3** | R76-04 | ⛔ **必須在寫入本輪第一列帳本之前做完**。8 筆孤兒列一旦時鐘前進即讓同一支工具轉 rc=1（**注意：現在被 R76-00 的早退遮蔽著，看不到那 8 筆警告**）。此步是**純 .md 註記**，不動任何有 LOC 餘裕問題的檔 |
| **4** | R76-01 | 開箱阻塞型 P0；修法是文件 + 一個算式，成本低 |
| **5** | R76-08 | 「有鎖在守假話」且**方向反了**——照規矩訂正文件會讓根層 unittest 轉紅。留著會讓下一輪重複手工補一個其實已有鎖的形態 |
| **6** | R76-02 + R76-18 + R76-03 | 同一支 workflow；R76-18（把步驟複製到阻斷層）**必須在 R76-02 之後**，否則是把編碼缺陷複製一份 |
| **7** | R76-05 + R76-06 + R76-12 + R76-13 | 排程／觀察期同一批檔案，必須同包（見 §4.2 包 B）；其中 R76-06 是 R75 頭號教訓的**第三次同形態復發** |
| **8** | R76-07 + R76-09 + R76-10 + R76-14 | 四道現行 fail-open：註解買免檢、`PYTHONUTF8` 遮蔽、`grep -iFx` locale 崩潰、152 支從未執行的斷言 |
| 9 | R76-11、R76-15、R76-17 | 結構性但可與上列平行（不同檔案） |

### 0.4 本輪最重要的三個結構性結論

1. **「豁免的解除條件已達成、豁免仍在生效」本輪抓到 3 個獨立實例**（R76-05 nightly drift／R76-49 root-infra `WAIVER_UNTIL`／R76-06 E3 的鏡像）。這是 R75 頭號教訓「補償欄位在上游改善後必須同時刪除」的家族性復發——**承接者是「人記得讀一行 WARN」的豁免，一律等於永久豁免**。
2. **「判準的比較對象不得隨被它所判的動作而改變」第三次復發**（R76-06 E3：判準要求「移除 smoke 後 drift checker 回 rc=0」，而期望值 SSOT 同時列兩支任務 ⇒ 執行它授權的動作必然讓它轉紅）。R75 為此付出 main 三支全紅的代價並上了機械物，而該機械物的射程（R76-26/27）只圈住單一模組的三種函式命名。
0. 🔴 **新增（R76-00，本檔自身觸發）：兩道各自正確的鎖可以在交界處產生不可滿足的狀態。** A 鎖
   （治理文件登記）要求你加一行，B 鎖（LOC 棘輪，餘裕 0）禁止你加那一行。這不是「鎖壞了」，
   本輪也沒有任何維度的必跑項會問這件事——**現有的射程檢查全部是單鎖視角**。
   附帶的第二個教訓同樣貴：**先跑的閘門會遮蔽後面閘門的訊號，而遮蔽方向是「看起來變乾淨」**
   （早退讓 8 筆孤兒警告整批消失）。
3. **本輪的 fail-open 全都長在「專門治它的機制」上**：R76-07（反向 hook 判準用整檔 substring）、R76-08（守著已失效的「已知缺口」清單）、R76-24（Scan-H 自己的通過判準對行數翻倍失明）、R76-25（鐵律三實質判準對 console 編碼列近乎恆綠）。掌舵者第 5 點要的「最壞情況會不會恆綠」，答案是**會，而且集中在護欄層自己**。

---

## 1. 逐筆發現表

**證據強度欄**：`已親驗` = 合成員本輪真跑過（附錄 A 有指令與輸出）／`引用` = 沿用原掃描員的 measured 證據，我未重跑／`部分推論` = 核心已測但某一段自陳為推論。

**建議包**欄對應 §4.2 的包代號。

### 1.1 P0

| ID | 維度 | 嚴重度 | 檔案 | 一句話 | 證據強度 | 建議修法 | 包 |
|----|------|--------|------|--------|----------|----------|-----|
| **R76-00** | **合成員新發現** | **P0** | `tools/check_defect_log_crossref.py:1169`（`_GOVERNANCE_DOCS`）／本檔自身 | 本檔符合 `CrossPlatform_*.md` 治理文件慣例而未登記 ⇒ 該工具**現在就 rc=1**（擋 pre-push 快層 `:291` 與 `root-infra-ci.yml:436`），且它在 `:1297` **早退**、把 R76-04 那 8 筆孤兒警告整批遮蔽；而唯一的登記式修法要 **+1 行**，該檔卻是 **1474/1474 餘裕 0** ⇒ **兩道棘輪的合法動作互為對方的違規** | **已親驗**（rc=1 逐字輸出、輸出總長 2 行證實早退、兩個 rc 消費者逐行確認、`check_special_files():286` 判準 `actual > max_lines` 逐字確認） | (a) 止血：本檔改名成不符 `CrossPlatform_*.md`（工具訊息自列的出口）；(b) 正解：先做 R76-16 騰餘裕 → 登記本檔 → 在檔內寫明它為何屬治理文件類。另建議 Scan-H 補一條必跑項：「新鎖要求的補救動作，是否會違反另一道既有硬閘？」 | **F（前置）** |
| R76-01 | Scan-F | **P0** | `ONBOARDING.md`（Windows 開箱段）／`useMacWin.md:98`／`tools/check_ntfs_paths.py:24` | `git clone` 未帶 `-c core.longpaths=true` 時在 >~120 字元根目錄產出半套 checkout（我實測 168 字元 → 27,523 支只落地 301 支、rc=128、`tools/bootstrap.ps1` 缺席），而旗標只存在於已完成 checkout 的 local config，全庫零文件教過 clone 指令 | **已親驗**（單變因 A/B，`git config --system/--global` 皆 rc=1）；「mac 無此形態」屬**部分推論**（未有 mac 真機） | ①ONBOARDING Windows 開箱補第 0 步 `git clone -c core.longpaths=true <url>`；②同處給 `git config --global core.longpaths true` 讓「忘記帶旗標」不再是單點故障；③`useMacWin.md:98` 就地註明「dev_start 設的 longpaths 是 clone **之後**才生效」；④`check_ntfs_paths.py` 把隱含假設變成輸出：印「可安全 checkout 的根長度上限＝247−最深目錄長度」與「fail 門檻 200 對應的根預留＝47」 | A |

### 1.2 P1（16 筆）

| ID | 維度 | 嚴重度 | 檔案 | 一句話 | 證據強度 | 建議修法 | 包 |
|----|------|--------|------|--------|----------|----------|-----|
| R76-02 | Scan-C | P1 | `.github/workflows/windows-compat-ci.yml:1239,1282` | runner 把 `shell: powershell` 步驟寫成無 BOM 暫存 `.ps1`，PS 5.1 以 ANSI codepage 誤讀繁中 ⇒ 第 05 步自 R48 起**從未執行過一次**（雲端逐字 `ParserError`），第 04 步僅靠 mojibake 引號恰好成對而偶然通過 | **已親驗**（我自跑位元組掃描：`windows-smoke` step[2] nonascii=0 → ASCII-SAFE；`windows-nightly-full` step[2] nonascii=195／step[3] nonascii=441，皆命中 cp1252 引號位元組 → PARSE-HAZARD；雲端 log 為引用） | ①兩個 run 本體改全 ASCII（中文 WHY 移到 step 上方註解），逐字照抄同檔 L676-691 已驗證作法；②新增機械鎖（併入 `tools/tests/test_gha_action_versions.py`）：`shell == 'powershell'` 的 run 本體必須 `body.isascii()`，附 bug-injection 紅綠；刻意不鎖 `pwsh` | D |
| R76-03 | Scan-C | P1 | `ONBOARDING.md:352`／`tools/lib/ci_liveness.py:273` | `continue-on-error` 讓 run 層 conclusion=success，job 層紅只透過 GitHub issue 顯形，而該通道**零讀者** ⇒ 一筆真實 P1 橫跨 R72~R75 四輪「雲端全綠」宣稱 | **已親驗**（`gh issue list` 唯一單 #10、state=OPEN、created 2026-07-14、updated 2026-08-03） | ①ONBOARDING 表③ 回填 SOP 加第 6 步：對兩支 compat-CI 帶 `continue-on-error` 的 job 另記 job 層結論欄，判準併入 cloud 錨家族（比較對象只能是被測 commit 自己的歷史，**不得**用 `origin/`）；②收輪清單加一條：`gh issue list --state open --search '深度回歸失敗 in:title'` 必須為空，否則不得宣稱雲端全綠 | D |
| R76-04 | **Scan-D + Scan-G** | P1 | `docs/06_quality/AutoSDD_Defect_Log.md:129,130,132,133,134,135,137,138` | R75 留下 8 筆「承接者＝已結束的 R75」的未結列；孤兒判準現在只因時鐘 stale 而綠，R76 一寫第一列帳本即擋住每一次 push；且 R75 交棒書只登記 2 筆（少報 8 筆） | **已親驗**（實跑 rc=0 但印出 8 筆 `⚠️ 當前輪時鐘 fail-open 窗口` 逐字警告，末行自陳「本輪若尚未寫入任何帳本列，此值仍停在上一輪」） | 寫任何新帳本列**之前**，對 8 列於**狀態欄**就地追加（不改寫原文）：R75 已服務者寫「🔴 R76 回執：…」＋改首詞；未服務者寫「🔴 R76 改派：承接輪次 **R76**／**未指派**」＋可執行解鎖條件。另把 `R75_HANDOFF.md:114` §5-3 由「兩筆未結」改為現查指令 | C |
| R76-05 | **Scan-D + Scan-H + Scan-M** | P1 | `AutoClaude/tools/run_local_nightly.ps1:1865-1889`／帳本 `:131`（DEF-101-794） | 排程漂移的具名豁免其解除條件**已達成**（status=ok）卻仍生效 ⇒ 從現在起任何真的排程回歸都被歸類為「已知存量」不計 finalFailures；唯一 stale 自檢是 nightly log 裡一行給人看的 WARN | **已親驗**（`check_scheduled_task_drift.py` → `status=ok` / 兩支任務各「全部 7 項設定符合期望」/ RC=0） | ①`:1888` drift 分支移出白名單（只留 `ok`／`skip`）並同步 `test_run_local_nightly_static.py` 的 `_DRIFT_STUB` 期望（附注入紅綠）；②更好的形態：第一次觀測到 `status=ok` 就寫持久化旗標，之後 drift 一律計入 ⇒ 豁免**自動退場**，不靠人讀 WARN；③帳本 `:131` 貼實測輸出並結案；④同步訂正 `R75_HANDOFF.md:94`、`Scheduled_Jobs_Lifecycle_Review_R75.md:322`、`tools/windows_smoke_local.ps1:124` 三處已失實的 `rc=1` | B |
| R76-06 | Scan-M | P1 | `tools/windows_smoke_local.ps1:112-113` | smoke 退場判準 E3 逐字要求「移除後 drift checker 回 rc=0」，而期望值 SSOT 同時列兩支任務 ⇒ 執行 E3 授權的動作**必然**讓判準轉紅（且經 nightly 白名單 fail-closed 每晚硬 exit 1）＝R75 頭號教訓第三輪同形態復發；本輪 E1/E2/E3 前置全部成立，該判準**現在就會被行使** | 引用（原掃描員以注入式期望值 JSON 實測 `status=task_missing` rc=1；我親驗了其前提 `status=ok` rc=0） | ①E3 改寫為不隨動作改變的量測對象：「`AutoClaude_Nightly` 存在，且 `check_scheduled_task_drift.py --expectations <只含 nightly>` 回 rc=0」；②`check_scheduled_task_drift.py` 補 `--tasks <name>[,<name>]` 篩選（純函式 `evaluate()` 已可接子集，只差 CLI 入口），讓「對單一任務取證」不需偽造 SSOT；③與 R75 §5 D-4 四處同步清單併為同一個 DoD | B |
| R76-07 | Scan-H | P1 | `tools/tests/test_doc_loc_baseline_freshness_r60.py:2816` | 「hook 宣稱↔實際註冊」判準用**整檔 substring** 判「已註冊」（`if name in settings_text:`）⇒ `settings.json` 的一個 `_comment` 就買到免檢；拔掉真 wiring 只留註解，根 CLAUDE.md:60 那句「已橋接 2 支」成假話而零訊號＝R75 剛修掉的 OR 型通行證原地復活 | **已親驗**（逐行讀出 `:2816 if name in settings_text:` 與其後 `continue`；注入輸出為引用） | 把 `if name in settings_text:` 換成「解析出的 hook command 集合」判定——直接複用同 repo 既有的 `test_subprocess_encoding_hygiene.py::hook_command_scripts()`（`json.loads` → `hooks[*][*].hooks[*].command`），簽名改 `registered: set[str]`；補注入測試「只在 `_comment` 出現的 hook 不算已註冊」。另把 CLAUDE.md:60 的行號（59／64）拿掉或納入判準 | E |
| R76-08 | Scan-G | P1 | `docs/06_quality/CrossPlatform_Scan_Dimensions.md:303` ＋ `tools/tests/test_check_defect_log_crossref.py:1573` | 硬規則② 的「已實測不涵蓋」仍列著 R74 已涵蓋的「否定語意」，而一支**綠燈**測試用 `assertIn("否定語意", …)` 把這句假話釘死 ⇒ **照規矩訂正文件會讓根層閘門轉紅**，方向與該文件自訂的「被涵蓋時翻紅強迫改文件」完全相反 | **已親驗**（`reassign_hit('open（無回執）')=False`／`('零改派')=False`／`('沒有回執')=False`／`('未改派')=False`，對照 `('改派為：未指派')=True`；並逐字讀出該 `assertIn` 迴圈） | 同一 commit 兩邊一起改：①文件把該項改為「R74 起已涵蓋（`_REASSIGN_NEGATED_RE`），自此不在不涵蓋清單內」，並把三項對齊 `orphan_backlog_problems()` docstring 現行內容；②該測試判準由「必須提到 否定語意」**翻轉**為「規格段的不涵蓋清單必須逐字等於 docstring 的不涵蓋清單」（集合相等，任一邊未同步即紅）；③追加注入：文件仍列一個已被 `reassign_hit` 擋掉的形態即紅 | C |
| R76-09 | Scan-N | P1 | `tools/check_gha_action_versions.py:193`（代表站點）／`.claude/settings.json:5` | `read_text()/open()` 缺 `encoding=` 這一整類 mac→Windows 缺陷**零靜態掃描器**，且其執行期可見度被 `env.PYTHONUTF8=1` 關掉（而另有一道鎖在強制那個值存在）⇒ agent 驅動的開發迴圈裡這一類缺陷結構上不可見 | 引用（單變因 A/B：剝 `PYTHONUTF8` → `UnicodeDecodeError: 'cp950'` rc=1；帶之 → rc=0；本機 zh-TW） | ①`tools/tests/test_platform_neutral_paths.py` 增第五道 AST 判準：四棵測試樹＋生產碼樹掃 `read_text/write_text/open` 缺 `encoding=`（二進位模式排除），附 `# encoding-ok: <WHY>` 行尾豁免＋stale 自檢；②指定一條閘門 leg 以**剝除** `PYTHONUTF8` 執行（pre-push root-infra 慢層加一次 `env -u PYTHONUTF8` 子集，或 `windows-compat-ci.yml` 加 `env: PYTHONUTF8: ''` 對照 step），別再把區分本機與雲端的變數全域正規化掉 | I |
| R76-10 | Scan-N | P1 | `tools/git-hooks/pre-commit:174,206` | 兩條 NTFS 大小寫碰撞閘是 **locale 相依的 fail-open**：Git Bash 的 GNU grep 3.0 對 `-i`＋`-F` 在無 UTF-8 locale 時 SIGABRT，`\|\| true` 把崩潰吞成「沒有碰撞」；照鐵律一用 `Find-GitBash` 複驗這道閘的人拿到假綠 | **已親驗**（我自跑：無 locale → `Aborted` **rc=134**；`LC_CTYPE=C.UTF-8` → 命中 rc=0；`-Fx` 不帶 `-i` → rc=1 正常。並確認兩行皆 `grep -iFx … \|\| true`） | ①兩處改用本檔已在用的 bash 3.2 折疊慣例：`tr '[:upper:]' '[:lower:]'` 各折一次後用 `grep -Fx`（不帶 `-i`）；②`\|\| true` 改為捕捉 rc，`rc -gt 1` 時 fail-loud（grep 的 1＝無命中正常，≥2＝工具出事）；③測試增一支「剝除 `LC_ALL/LC_CTYPE/LANG` 後直接跑 `bash tools/git-hooks/pre-commit`」的載具 | H |
| R76-11 | Scan-N | P1 | `.github/workflows/windows-compat-ci.yml:612`／`macos-compat-ci.yml` | push 事件對 `AutoClaude/autoclaude/**` 的 Windows/macOS 覆蓋率僅 **14%**，且 `paths` 命中 ≠ 執行——`AutoClaude/tests/**` 100% 在 paths 內，但兩支 smoke **從不跑那棵樹**（跑全樹的只有週頻＋`continue-on-error` 的 nightly-full）⇒「push 後全綠」對 AutoClaude 生產碼在兩平台的行為零證據力 | 引用（`git ls-files` 全量比對；原掃描員自陳 matcher 為自寫近似，數量級可信） | ①兩支 smoke 各加一步「AutoClaude 平台敏感子集」（如 `pytest AutoClaude/tests -q -m 'not perf and not pg_real' -k 'path or encoding or platform or shell or subprocess'`），把 push 時真機證據由 0 提到非 0；②若不加，就把 `AutoClaude/tests/**` 那條 paths 旁註明「本條只觸發 workflow，push 時不執行該樹」，並同步 ONBOARDING 的覆蓋敘述，避免「100% 命中」被讀成「100% 覆蓋」 | D |
| R76-12 | Scan-M | P1 | `AutoClaude/.gitignore:57`（缺列）／`AutoClaude/.drift_log_history.jsonl` | 五本觀察期帳本裡**唯一被 git 追蹤**的就是 drift 那本 ⇒ 進帳會被 `git checkout -- .`／`stash`／`reset --hard`／worktree 切換靜默回捲；已實測損失 UTC 2026-07-27 一整天（該日 6 支 nightly log 都寫了、磁碟與所有 commit 都沒有那筆） | **已親驗**（`git ls-files --error-unmatch` 逐支：drift **TRACKED**、observability／ac4／mutation／perf 皆 untracked）；「哪個 git 操作抹的」屬**部分推論**（未查 reflog） | 二擇一並明文寫下理由：(A) 加進 `.gitignore`（沿用第 74 行同段註解措辭）＋`git rm --cached` 一次，與其他三軌對齊；(B) 若刻意 tracked，就必須加「寫入後回讀 + 與 pre-snapshot 計數比對」＋pre-commit/pre-push 的「只准增行」棘輪。無論哪個，都要在 `Scheduled_Jobs_Lifecycle_Review_R75.md` §2.1 補記「已知曾損失 1 筆（UTC 2026-07-27）」，因為「只剩 2 筆」的推算建立在帳本從未被回捲的假設上 | B |
| R76-13 | Scan-M | P1 | `AutoClaude/tools/drift_log_ga_check.py:100`／`observability_ga_check.py` | GA 判準量的是**筆數**不是**天數**，且對「整段沒跑」零偵測 ⇒ observability 以「30 筆橫跨 58 個日曆天、窗內含 12 天全黑」宣告「30 天零事件 GA 取證通過」 | **已親驗**（我自跑兩支 GA check：obs `[PASS] green_streak=44 >= window=30 (total 44 records)` rc=0／drift `[FAIL] green_streak=28 < window=30` rc=1；並自量兩本帳本：obs last30 span **58 日曆天**、窗內 9 個 >1 日 gap、最大 `2026-06-29 -> 2026-07-11 = 12 days`；drift span 65 天、10 個 gap） | 語意抄 `ac4_progress_check.py` 已存在的兩個欄位、不另發明第三套：①`staleness_days`＝最後一筆到現在的 UTC 日數，超門檻即 rc≠0；②窗內連續性判準＝`(最後一筆日 − 第一筆日 + 1) ≤ window×K`（K 寫死並附 WHY），至少也要把該 span 與窗內最大 gap 印進 PASS/FAIL 訊息；③`--window` 的 help／docstring 由「天數」改「筆數」，文案與實作同口徑 | B |
| R76-14 | Q3-Skipped | P1 | `.github/workflows/autoclaude-ci.yml:96,255,328` | 224 支 skip 裡 **192 支（86%）在兩平台與全部 11 支 workflow 都沒有任何通道跑到**；152 支可用一次 CI recipe 修改救回（含 alembic 0007~0012 migration 契約、三層 schema 契約、PG 既有 9 表 DDL 漂移鎖——**從未被執行過的斷言**），其中 63 支已實測 1.4 秒轉綠 | 引用（逐 workflow 反查 10 個測試檔名全 NONE；scratchpad 另建 venv 裝 driver 後 `62 passed, 1 skipped in 1.42s`；本機 `docker ps` 顯示 pgvector 容器 healthy ⇒ DB 從來不是瓶頸） | ①把 `pg-contract` job 已有的完整 recipe（services + `[dev,postgres,pgvector]` + DSN env + `alembic upgrade head`）最後一步由單檔擴為 `pytest tests/contract/ tests/integration/ -q -rs` ⇒ 一次收回 148 支；②主 test job `:96` 加 `sdk` extra 收回 3 支；③11 支 claude CLI 依賴（付費 binary＋巢狀 session 必死結，DEF-101-089）加新標籤明示**永久不覆蓋**並登記，不要混在可救的那堆裡 | G |
| R76-15 | **Q3 + Scan-A×2** | P1 | `AutoClaude/tests/conftest.py:261`／`AISDLC_SDD/conftest.py:50`／兩支 `test_conftest_windows_native_skip_report.py` | 反方向 skip 可見度**三個缺口疊在一起**：①AutoClaude 側 windows-only 站點 8/8 有標籤、posix-only 0/6 有標籤 ⇒ R74 為此新增的區塊在 Windows 側**結構性零輸出**，而棘輪把欠債凍結成 6 讓它恆綠；②AISDLC_SDD 側整套反方向機制缺席，且該檔「行為對齊 AutoClaude/tests/conftest.py」的宣稱已成假話；③反方向報表在兩個子專案都**零回歸鎖**，刪掉即全綠 | 引用（靜態普查逐站點列出；`Select-String 'NATIVE-ONLY\|TOOL-ABSENCE'` 對 224 支輸出零命中；`non_windows_native_skips` repo-wide 只 2 個命中且都是生產端自己） | ①`_POSIX_TAG_RATCHET` 由「凍結存量」改**逐輪下修的 shrink-only**（現值 1/6/1），或讓該區塊改讀**方向**而非標籤；②`AISDLC_SDD/conftest.py` 補三常數＋純函式＋第二區塊（比照姊妹檔，不 import 根層模組——兩套 pytest root 不同；不得用 emoji，見該檔 DEF-101-069）；③兩支既有鎖檔各加反方向案例＋負向案例（**必須併入既有檔**，`_FROZEN_GUARD_FILE_COUNT` 禁新增鎖檔）；④順帶修 `test_perception_platform_honesty.py:84` 的標籤（`skipif(sys.platform != "darwin")` 正確標籤是 `[MAC-NATIVE-ONLY]`） | G |
| R76-16 | **Scan-T + Scan-D×2** | P1 | `AutoClaude/tools/check_loc_budget.py:278,373` | 六支 raw-line 棘輪餘裕只剩 **0~2 行**，而 `SPECIAL_FILES` 與根層 tools tier **兩層都沒有預警帶**（只有 AutoClaude tier 有 `TIER_WARN_MARGIN=6`）⇒ 第一個訊號就是紅，且解鎖程序要求「先刪死碼／抽共用模組再具名入帳」＝一行修復被要求先做一次重構 | **已親驗**（我自跑該模組函式：`margin=0 400/400 CLAUDE.md`／`0 1474/1474 check_defect_log_crossref.py`／`0 1507/1507 archive_defect_log.py`／`1 1617/1618 check_script_parity.py`／`1 1999/2000 dev_start.py`／`2 1497/1499 sync_onboarding_baselines.py`；`TIER_WARN_MARGIN = 6`） | ①`check_special_files()` 與 `build_root_tools_reports()` 各回 `(violations, warn_band)`，warn 判準 `0 <= cap - actual <= N`（建議 5，理由寫在常數上方），`--json` 加 `special_warn_band`／`root_tools_warn_band`，**rc 一律不變**；②本輪順手騰餘裕：`AutoClaude/CLAUDE.md` 的 4 處 `baseline-ok:` 歷史快照行整併或搬進 sprint_history；③合成注入測試（budget 調到 actual+1 → 進 warn_band 且 rc=0；actual−1 → 進 violations 且 rc=1）。**不要**調高 400 或 1618 | F |
| R76-17 | Scan-T | P1 | `AutoClaude/pyproject.toml:24` | `keyboard>=0.13` 仍無平台條件（R68-67 open 跨 8 輪），其 metadata 就是 macOS 側 pyobjc 傘包的成因；而該相依在 macOS 上根本不生效（真正擋路者是 `os.geteuid() != 0`）⇒ 非 root 的 mac 使用者付了安裝面卻拿不到功能 | **已親驗**（`importlib.metadata`：keyboard 0.13.5 → `Requires-Dist: pyobjc ; sys_platform == "darwin"`；`git grep` → `pyproject.toml:24: "keyboard>=0.13",` 無 marker，對照同檔 :14/:23/:69 三條都有 marker）；「162 發行版／24.4MB」為引用 | 建議走 (b)：移出核心相依、新開 `[project.optional-dependencies] hotkey = ["keyboard>=0.13,<0.14"]`（**不要**寫死 `win32`——Linux root 仍可用，寫死會製造新的單平台判準）。同步 `bootstrap.ps1`／`bootstrap.sh`／根 CLAUDE.md／ONBOARDING §5 的 extras 字串；`hotkey_handler.py` 已有 `_KEYBOARD_AVAILABLE` 旗標故程式碼免改；ONBOARDING:529「需輔助使用權限」須同時訂正為 euid 判準 | J |

### 1.3 P2（32 筆）

| ID | 維度 | 檔案 | 一句話 | 證據 | 包 |
|----|------|------|--------|------|-----|
| R76-18 | Scan-C | `windows-compat-ci.yml:1218` | 「文件教的引擎」深度驗證整批掛在每週一次、非阻斷、fail-open 的 nightly；macOS 對等物（zsh／bash 3.2）全掛在每次 push 都跑的阻斷式 smoke ⇒ 這是 R76-02/03 能爛 21 天的層級性根因 | **已親驗**（我自跑 job 掃描：`windows-smoke continue-on-error=None`、`windows-nightly-full continue-on-error=True`） | D |
| R76-19 | Scan-M | `Scheduled_Jobs_Lifecycle_Review_R75.md:357`／`tools/windows_smoke_local.ps1:123-127` | R75 生命週期報告 §2.2.6／§4.3 說「工作缺席 rc 不會轉紅」，磁碟是 `STATUS_TASK_MISSING` rc=1 且經 nightly 白名單 fail-closed ⇒ 照那段話行動會把每晚回歸弄紅；smoke 腳本的「現況（2026-08-04 實查）」三項今日實測全部相反 | 引用（我親驗了其中 `status=ok` rc=0 那一項） | B |
| R76-20 | Scan-M | `tools/install_windows_nightly.ps1:41` | Windows `-Status` 被宣告為 mac 心跳的語意對等物，實缺三維度（新鮮度門檻／FAIL 計數／覆蓋連續性），且其唯一資料源會被安裝器自己抹掉；現場正處於 `LastTaskResult=267011`（從未執行）而 `-Status` 仍 rc=0 | 引用 | B |
| R76-21 | Scan-M | `CLAUDE.md:117` | 根 CLAUDE.md 對「schtasks 查詢假陰性」的**歸因是錯的**：真因是 Git Bash／MSYS 把 `/query` 改寫成 POSIX 路徑（與反斜線被吃掉同源），不是 schtasks 的怪癖 ⇒ 下一個踩到 `reg /query`／`sc /query` 的人學不到東西；且 `dev_start.py:1730` 印給使用者的正是那條 schtasks | 引用 | J |
| R76-22 | Scan-M | `tools/check_scheduled_task_drift.py:39` | R75 為「全缺席＝skip」加的 `--require-installed` 顯式開關**全 repo 零呼叫者** ⇒ 缺口實際仍 100% 開著，只是文件上從「無法關閉」改寫成「可被關閉」（DEF-101-757 換形狀重現） | 引用 | B |
| R76-23 | Scan-H | `tools/git-hooks/pre-push:290` | `check_scheduled_task_drift.py` 無任何 push 閘門消費其 rc；兩支 compat-CI 只把它列進 `paths:` 觸發面而從未有 `run:` step ⇒ 觸發面有、掃描面零 | 引用 | I |
| R76-24 | **Scan-E + Scan-H** | `tools/tests/test_adr_xplat001_c1c2_lock.py:3119,3141` | Scan-H 自己的通過判準有兩個洞：①檔數棘輪把護欄層成長全趕進「刻意不設上限」的 GLC 行數（13 個 commit 檔數恆為 56，行數 26,286→51,894 **+97.4%**，閘門每次 rc=0）；②凍結對可在**同一 commit** 與被量值一起調高而零張力，而其註解引 SA-R67-08 的假棘輪裁決當作已解決 | 引用（UEP=5／AC=48／GLC=56/51,894 三處一致） | E |
| R76-25 | Scan-H | `tools/tests/test_doc_loc_baseline_freshness_r60.py:2951` | 鐵律三「實質判準」的關鍵詞佐證對 console 編碼列**近乎恆綠**（任何開檔的 .py 都含 `encoding`；decoy 矩陣 6 支中 5 支假陰性），而其邊界宣告寫的是「抓得到完全沒碰那個主題」 | 引用 | E |
| R76-26 | Scan-H | `tools/tests/test_doc_loc_baseline_freshness_r60.py:3833` | R75 旗艦鎖漏掉等價形態 `git rev-parse origin`（無斜線，實測與 `origin/main` 同 sha）⇒ 完全逃逸；且缺 repo 自己要求的三段式「已實測不涵蓋」邊界宣告 | 引用（磁碟注入：`origin/main` 形態 rc=1、`origin` 形態 rc=0） | E |
| R76-27 | Scan-C | `tools/tests/test_doc_loc_baseline_freshness_r60.py:3867` | 同一支旗艦鎖的**射程**僅限單一測試模組內三種函式命名前綴，其他判準家族在射程外（現無違規者，故是缺口非缺陷） | 引用 | E |
| R76-28 | Scan-B | `AISDLC_SDD/scripts/component_sanitizer_callsite_scan.py:93,96` | 淨化呼叫點 AST 掃描器對「從未被淨化過的新識別字」**結構上恆綠**——它只抓得到「曾處理過的名字後來退化」，抓不到「新名字一開始就沒處理」，而後者正是歷史缺陷的真實形狀；另「像不像檔名」只認 4 種副檔名且該邊界未列入七項方法論邊界 | 引用（三態注入：新名字未淨化 → `6 passed`／控制組 rule_id → 2 failed／新名字已淨化 → 要求登記） | H |
| R76-29 | Scan-B | `tools/tests/test_windows_forbidden_filename_parity.py:547` | 「漏淨化呼叫點」這條軸在 AutoClaude 268＋root tools 29＋AISDLC_SDD/scripts 14 共 **311 支生產 .py** 上零機械覆蓋，而 DEF-101-384/390/442 三筆歷史缺陷全部發生在那 268 支裡（現況乾淨 ⇒ 缺機制非活缺陷） | 引用 | H |
| R76-30 | Scan-B | `AISDLC_SDD/scripts/component_sanitizer.py:46` 等四處 | R68 依「官方文件」加的上標保留名（COM¹²³／LPT¹²³）經真機實測為 **ACCEPT**（與被刻意排除的 CLOCK$ 同格）⇒ 兩處 **validator** 會硬擋 git 願意正常 clone 的檔名；且四處「本輪無真機、未跑 protectNTFS 對照」的欠條已成假話 | 引用（git 真機 clone A/B ＋ Win32 CreateFile 三造對帳） | H |
| R76-31 | Scan-E | `tools/tests/test_pre_push_dispatcher.py:65` 等三處 | 三份 `_usable_bash()` 的 AST 函式體**逐字相同**（bodyhash 皆 `d76f1fe72df570cb`），而保留多份的唯一理由正是「獨立重寫維持鑑別力」⇒ 前提被自己的程式碼證偽；SSOT 已存在（`_platform_helpers._BASH_SUBPATHS` 4 筆含 POSIX 佈局）但複本只有 2 筆 Windows-only ⇒ 漏掉的那格恰好是 mac 側 | 引用 | J |
| R76-32 | Scan-E | `AutoClaude/tools/run_local_nightly.sh:8` | 該對子的單平台面積自 R11 拍板後翻倍（929→**1,960** 行），mac 側仍 264 行（7.4:1），而拍板文字裡的 929 是死常數、七軌去向帳目未隨之重算 ⇒ 一個以「不該收斂」為結論的地板項，其量級前提已翻倍 | 引用（git 物件逐 commit 量測） | J |
| R76-33 | Scan-D | `CLAUDE.md:271,272,281` | 根 CLAUDE.md 自己的 AISDLC_SDD 指令示範用的是鐵律一明文禁止的裸 `bash <script>`（R72 訂正註記只覆蓋下一行的 `cd`，且位置在後），而這一類文件缺陷零機械覆蓋 | 引用（`(Get-Command bash).Source` → `C:\WINDOWS\system32\bash.exe`；正解 `Find-GitBash` → Git 版 rc=0） | J |
| R76-34 | Scan-D | `tools/tests/test_doc_loc_baseline_freshness_r60.py:2944,3020` | 具名機械物鎖的掃描面仍**非遞迴**（23 個帶「機械鎖／機械釘」字樣的檔在射程外，含 `ONBOARDING.md` 與 `AutoClaude/CLAUDE.md` 兩份活治理文件；根 `tools/` 下的 `.ps1` 被納入「可辨識副檔名」卻沒被納入「可掃描來源」）；而擴面前得先修 `::Symbol` 判準，否則會對合法的模組級常數錨誤報 2 筆 | 引用（現無活體幽靈 ⇒ 潛在缺口） | E |
| R76-35 | Scan-F | `AutoClaude/tools/run_local_nightly.ps1:465,1459,1821`／`g0_gate_check.ps1:49` | 四個在 PS 5.1 下跑的 production 站點用裸 `Get-Content` 讀檔（無 `-Encoding`），其中 `:1459` 直接餵 `ConvertFrom-Json` 決定「今天 nightly 有沒有進帳」；同一支檔的作者已為「寫」的方向加了 `-Encoding utf8` 卻漏了「讀」；今天不出事只因 5 支 jsonl 恰好純 ASCII（資料屬性、非設計保證） | 引用（同機實測 5.1 讀 UTF-8 CJK 吞掉 104 個換行、方向是「行數變少」＝會讓「最後一筆」抓錯的方向） | B |
| R76-36 | Scan-G | `docs/04_planning/R75_HANDOFF.md:124` | 「65 筆 `tool-absence` 站點未補標籤」零承接載體：無帳本列、判準函式 `untagged_tool_absence_sites()` **零消費者（連測試都沒有，是死函式）**、普查棘輪不區分有無標籤 ⇒ 只活在會被下一份交棒書取代的散文裡（DEF-101-521 同型） | 引用（65 = 38+16+11，比例 65/65） | C |
| R76-37 | Scan-G | `docs/06_quality/AutoSDD_Defect_Log.md:42`（DEF-53-001） | 跨軌交棒**死信**（routed 進軌道② RFC，`Grep 'DEF-53-001' AISDLC_SDD` → 0 命中），靠存量豁免白名單躲過硬規則② 後半句，而硬規則③ 至今無鎖；狀態 `routed` 對讀者的意思是「別人在處理」，實際沒有人在處理 | 引用 | C |
| R76-38 | Q3 | `tools/lib/skip_tag_policy.py:209` | runtime skip 支數（224／43）全庫沒有任何**值判準**閘門；既有站點分類棘輪只看得到「reason 為字面字串的靜態站點」，對 AutoClaude 可見度僅 30/224（13%）⇒ 下一次長到 300 也不會有人被通知 | 引用（四種靜態掃描結構上看不到的形態皆實證） | G |
| R76-39 | Q3 | `tools/lib/skip_tag_policy.py:152` | 靜態 skip 掃描射程排除兩棵 fsm_runtime 樹，**包含可變的 LATEST（v0.30，全 repo 最大一棵，1742 tests）**，其 4 個站點與 6 支 runtime skip 對所有棘輪隱形；排除理由（Copy-on-Evolve）對 v0.01~v0.29 成立、**對 LATEST 不成立** | 引用（`sdd_latest.py` 實查存在 ⇒ 註解自己指出的正解有零件可用） | G |
| R76-40 | Q3 | `tools/check_pytest_baseline_sites.py:58` | 「pytest 基線數字只准住一個家」的鎖是寫死 6 檔的白名單；本輪新增的盤點文件通篇寫著 `3900 passed, 224 skipped` 而該鎖 **rc=0**（R59 已被同形態咬過一次，修法是「再加一行」而非把判準反過來） | 引用 | G |
| R76-41 | Q3 | `AutoClaude/tests/contract/test_ac_matrix_scaffolding.py:217` | 29 支無條件 skip（占 224 的 13%，單一站點乘出 29 支）的 reason 與同一支的 docstring **直接矛盾**，且 23/29 的 target 檔其實已存在、2 條 target 根本不是檔案路徑 ⇒ 傳達錯誤資訊 | 引用 | G |
| R76-42 | Q3 | `tools/tests/test_dev_start.py:5837` 等 3 處 | skip 標籤存在兩套詞彙：`[TOOL-MISSING]` 與 SSOT 註冊的 `[TOOL-ABSENCE]`，用前者的站點被報告器判成「未標籤」（43 支中 11 支判未標，其中 2 處其實有意標籤）⇒ 標籤覆蓋率量測失真 | 引用 | G |
| R76-43 | Scan-A | `AISDLC_SDD/scripts/tests/test_install_post_commit_windowsapps_guard.py:85` 等三處 | 三份 `_latest_installer()` 複本用三種直譯器拼法（`python3`／`python3`／`python`），跑出的直譯器不是跑 pytest 的那一支（本機 `python3` → pyenv shim → 全域 3.11.9，對照 venv）；同目錄另有 5 處已用 `sys.executable`，而 bare-python 納管掃描**明文排除測試檔**故零機械物 | 引用；「乾淨 Windows checkout 會炸」原掃描員自陳**未能重現**⇒該半屬推論 | J |
| R76-44 | Scan-T | `AISDLC_SDD/scripts/ci-gate.sh:264` | AISDLC_SDD 全樹**零 ruff 閘門**：2,887 筆存量無人看守，live v0.30 佔 97 筆（換上 repo 自己的規則集是 3,375 筆）；`tools/ruff.toml:25-27` 的劃界註解無到期日、無承接輪次、無 stale 自檢（DEF-101-757 明文禁止的形態）；諷刺的是該框架的模板與 SOP 都在教它的使用者把 ruff 接進 CI | 引用 | J |
| R76-45 | Scan-T | `AutoClaude/tools/_compute_sha.py:10` 等 | 三支死碼/漂移複本仍在樹裡，其中 `_compute_sha.py` 是**帶著兩個已修缺陷的舊複本**（缺 posix path key 與 `is_file()` 分支）而它算的正是 mutation 鎖定的去重鍵 `source_sha256` ⇒ 拿錯的 sha 會污染鎖定判定 | 引用 | J |
| R76-46 | Scan-T | `tools/ruff.toml:64` | tools/tests E501 存量卡在 **139/139**（棘輪餘裕 0），豁免硬到期日 2026-11-02 剩 89 天，`_E501_WAIVER_MAX_DAYS=120` 讓「填很遠的日期」不可行 ⇒ 兩個時鐘同時歸零，且落地至今筆數一次都沒降 | 引用 | J |
| R76-47 | Scan-T | `docs/06_quality/AutoSDD_Defect_Log.md:44`／`AutoClaude/pyproject.toml:32-34` | DEF-101-018 的「1,147 筆」在兩處都 stale 且都沒記量測指令與執行目錄；同版 ruff 今日實測 824（cwd=AutoClaude）／3,711（cwd=repo 根）⇒ 任一讀法下都失實。**這正是本維度必跑項存在的理由本身還活著**（R68 已指名，八輪未動） | 引用 | C／J |
| R76-48 | Scan-N | `tools/git-hooks/pre-push:117` | 純子專案 push **不跑 root-infra 慢層**，而慢層是全部跨平台靜態掃描器在本機的唯一執行者（掃描面涵蓋子專案、觸發面不涵蓋）⇒ 最常見的「只改一個子專案」push 在本機得到「跨平台判準一條都沒跑」的綠燈 | 引用（tmp repo 端到端 marker 實測） | I |
| R76-49 | Scan-N | `.github/workflows/root-infra-ci.yml:494` | nightly 陳舊度哨兵被一張**已達成條件**的過期豁免（`WAIVER_UNTIL: 2026-08-10`）降級為 warning，而該檔自陳「非阻斷正是它爛掉 18 天的機制」；豁免條件已達成（兩軌 schedule 最近成功 2026-08-03） | 引用 | D |

### 1.4 P3（18 筆，摘要）

| ID | 維度 | 檔案 | 一句話 | 包 |
|----|------|------|--------|-----|
| R76-50 | Scan-C | `windows-compat-ci.yml:617` | 「同為 22 步」失實（我親驗：windows-smoke **steps=25**、macos-smoke 24），而檔頭快照鎖只驗 `runs-on` 與 shell 分佈、不驗步數 | D |
| R76-51 | Scan-D | `CLAUDE.md:206` | 在「請在 `AutoClaude/` 目錄下執行」段落裡指名 `tools/bootstrap.*`，但 `AutoClaude/tools/` 底下零筆（同檔後文自己說它在 monorepo 根層）；逃過 R75 新鎖因為路徑寫成 glob `.*` 不匹配副檔名判準 | J |
| R76-52 | **Scan-E + Scan-T** | `CrossPlatform_Scan_Dimensions.md:283` | **殭屍 backlog**：仍宣稱「五份同語言複本尚未逐一檢視」，而該家族已於 R66（DEF-101-624）收斂完畢且有 repo-wide 唯一性鎖 ⇒ 每輪固定支出一次 Architect 重複調查（該節自己記載過這筆支出） | C |
| R76-53 | Scan-E | `tools/tests/test_dev_start.py:1` | 護欄層零 per-file 尺寸約束（生產碼有 750 絕對紅線）：22/56 支已越線、最大 6,684 行＝紅線的 8.9 倍；檔數棘輪換來的是無界檔案 | — |
| R76-54 | Scan-F | `ONBOARDING.md:527` | 「凍結版 47 支 ps1 無 BOM 會 parser 斷裂」實測只有 29 支斷裂（**有聲**），另 18 支照樣 parse 得過、改成靜默亂碼（**無聲**）⇒ 把兩種性質相反的故障混成一句，讀者遇到無聲那組反而不會去換檔 | J |
| R76-55 | Scan-F | `tools/run_root_unittests.py:58` | MIN_TESTS 仍是 R74 自陳的「中途值」1819，實測已 1903；解除條件（四方複審收斂）在 R75 已滿足卻沒人重釘，而 1.046 倍落在 WARN 線（1.10）以下 ⇒ 缺席型漏做零訊號 | J |
| R76-56 | Scan-G | `AutoClaude/tools/run_local_nightly.ps1:250`／`tools/archive_defect_log.py:1486` | DEF-101-810／811 現查確認皆未修；810 是**每次誤打 `--help` 就真的開跑 7 stage nightly** 的活腳槍（`.sh` 側同型缺口早已修好＝雙平台不對稱），修復成本極低 | B／C |
| R76-57 | Scan-H | `tools/tests/test_check_wrapper_thinness.py:797` | R75 新增鎖的註解寫死兩個可現查的支數（18 支／15 支帶 `__main__`），違反 Scan-H 必跑項③（該鎖自己所在的檔正是專門檢查工具射程的） | E |
| R76-58 | Scan-M | `tools/dev_start.py:1707` | nightly 心跳哨兵在 mac 有四態精確消歧、Windows 只給「可能未啟用？或尚未首跑？」二選一猜測，而能回答的偵測器 R74 就已存在；DEF-101-200 交棒給「Windows 輪」而 R71/74/75/76 四輪皆是 Windows 輪 | B |
| R76-59 | Scan-M | `AutoClaude/tools/drift_log_snapshot.py:28` | 進帳「一天」的邊界落在**本地 08:00** 而非午夜（17 支 nightly log 中 7 支被記到與實際執行日不同的日曆日）；`StartWhenAvailable` 的補跑正落在 00:00–07:59 窗口 ⇒ 補跑記到前一天、若該日已有紀錄就是 `replaced`＝淨進帳 0 | B |
| R76-60 | Scan-M | `tools/scheduled_task_expectations.json:49` | `WakeToRun` 的 OS 層前提（powercfg RTCWAKE）被期望值 SSOT 點名為必要條件，卻不在它機械檢查的 7 項內；而 R75 對本機該前提「實測失效」的歸因與現測不符（今日 RTCWAKE=1/1、S3 可用） | B |
| R76-61 | Scan-M | `tools/install_windows_nightly.ps1:1` | 缺 mac 對等的平台守門（`install_mac_nightly.sh:70-74` 有 Darwin 守門＋指路對岸工具）⇒ 在 mac 的 pwsh 上以無意義例外失敗；`check_script_parity` 的 tier3 單邊豁免使無 parity 鎖比對守門對稱性 | J |
| R76-62 | Scan-N | `CLAUDE.md:344` | 鐵律三盤點表把**已有掃描器**的 PATHEXT 軸寫成「無機械物／沒有東西會紅」（注入實測會紅：`TestPathextReadsAreePlatformGuarded` FAILED），而盤點鎖是單向棘輪、結構上抓不到這種**低報**；附帶：該類別名有錯字 `AreePlatformGuarded` | E |
| R76-63 | Scan-N | `tools/tests/test_ntfs_trailing_space_device_name.py:523` | 程式碼內「路徑引用大小寫不符」零機械物——A15 鎖的掃描面只到根層 `docs/**.md`；Windows 與 macOS 皆大小寫不敏感 ⇒ 只有 Linux CI／act 容器會炸，且只在該行真被執行到時 | H |
| R76-64 | Scan-T | `AutoClaude/pyproject.toml:121` | AutoClaude 樹 824 筆 ruff 存量分佈在 211/551 支（38% 帶債），無全樹閘門；pre-commit 的 ruff 掃**整檔** ⇒ 「下一支你動到的檔」有 38% 機率要求你先清一批無關 lint 債；4 支同時逼近 LOC tier 上限（餘裕 5~7 行）與 E501 折行**互斥** | J |
| R76-65 | Scan-T | `AutoClaude/autoclaude/plugins/convergence_plugin.py:86` | 全 repo 唯一一筆 F821：`ConvergenceReport` 在生產碼零定義、只活在四份計畫書裡，而 `# type: ignore[name-defined]` 把 mypy 的嘴也堵住 ⇒ 走 `typing.get_type_hints()` 的路徑會 NameError | J |
| R76-66 | Q3 | `.github/workflows/autoclaude-ci.yml:544` | 名為 Perf Baseline 的 nightly job 沒有 PG 也沒設 `PG_REAL_ENABLED`，唯一的 pgvector 效能測試在該 job 裡照樣 skip ⇒ 綠燈代言它沒量的東西 | G |
| R76-67 | Scan-T | — | 結構性存量量化基線（凍結 SDD 複本佔 tracked 行數 92.2%、護欄測試樹是它所護生產碼的 2.04 倍）。**原掃描員自己判定「不該清、只該保持可觀測」** ⇒ 我把它移出發現表，改列 §5.10 | — |

---

## 2. 去重帳（哪幾維獨立命中同一根因）

> **🔴 紀律**：獨立命中次數是**可信度訊號**，不是理由正確的證明。本 repo 判例
> [[agent-consensus-not-proof-of-reasoning]]：R24 Architect+SD 一審皆命中同一現象，但兩人引用的
> 理由經實測證偽。故下表**分開記「現象」與「理由」**，並標注理由是否被獨立驗證。

| 合成 ID | 由哪幾維命中 | 現象是否一致 | 理由是否一致／已驗 | 我的處置 |
|---------|-------------|-------------|-------------------|----------|
| R76-04 | Scan-D、Scan-G | ✅ 完全一致（同 8 個帳本行號、同 rc 翻轉時點） | ✅ 兩維都指向 `orphan_backlog_problems()` 的 fail-open 時鐘窗口，**我親跑閘門看到那 8 筆警告逐字印出**，理由已獨立驗證 | 合併，保留 Scan-D 的注入模擬 + Scan-G 的 rc 消費者清單（互補） |
| R76-05 | Scan-D、Scan-H、Scan-M | ✅ 三維同一現象（`status=ok` 但豁免仍在） | ⚠️ **理由層有分歧且都對**：Scan-D 說「補償欄位在上游改善後必須刪除」；Scan-H 說「stale 自檢是一個 print，不是判準」；Scan-M 說「承接者退回成人」。三者是同一缺陷的三個面，**非互斥**。我親驗了共同前提（`status=ok` rc=0） | 合併，三個理由全部保留（修法欄因此有三條路，Scan-M 的「持久化旗標」是唯一讓豁免自動退場的，我標為建議首選） |
| R76-15 | Q3、Scan-A（×2 筆） | ✅ 一致（反方向 skip 可見度） | ✅ 三筆是**三個不同缺口**而非同一筆重報：AutoClaude 側零輸出（棘輪凍結欠債）／AISDLC_SDD 側機制整套缺席（+ 假的「行為對齊」宣稱）／兩側皆零回歸鎖 | 合併為一筆三子項（同一修法包，若分開做會像 R74 那樣只修一半） |
| R76-16 | Scan-T、Scan-D（×2 筆） | ✅ 一致 | ✅ Scan-T 給結構解（缺預警帶）、Scan-D 給兩個具體實例（1617/1618、400/400）。**我親跑 `check_loc_budget` 函式取得全部六格餘裕**，理由已獨立驗證 | 合併，並據此推導出本輪最重要的**相依關係**（見 §4.1 序 1） |
| R76-24 | Scan-E、Scan-H | ✅ 一致（三元組對成長失明） | ⚠️ **兩個不同機制**：Scan-E＝檔數棘輪把成長位移到不設上限的行數；Scan-H＝凍結對可同 commit 一起調高。都成立、都在同一支檔 | 合併為一筆兩子項（同檔必須同包） |
| R76-26 + R76-27 | Scan-H、Scan-C | ✅ 一致（R75 旗艦鎖不夠嚴） | ⚠️ 兩維看的是**不同軸**：Scan-H＝token 集合漏 `origin` 無斜線形態；Scan-C＝掃描面只圈單模組三種命名前綴。互補 | 保留兩個 ID 但同包（同一支函式群） |
| R76-52 | Scan-E、Scan-T | ✅ 完全一致（同一行、同一結論） | ✅ 兩維都獨立查到 `tools/lib/sdd_latest.py` 是 SSOT 且 R66 已收斂，證據互為佐證 | 合併 |
| R76-28 | Scan-B（F2 + F4） | 同維內兩筆 | 極性錯 + 副檔名白名單未揭露 ⇒ **同一次改動才有效**（原掃描員明言分開做會讓反轉只覆蓋一半站點） | 合併 |
| R76-19 | Scan-M（F5）＋Scan-D（F2 尾段） | ✅ 一致（stale 現況段） | 一致 | 併入 Scan-M 主筆，Scan-D 的第三處訂正併入 R76-05 修法欄 ④ |

**未合併但需並讀的兩對**（形態同族、檔案不同、修法不同，強行合併會漏修）：

- **「讀檔未指名編碼」家族**：R76-09（Python `read_text` 缺 `encoding=`，被 `PYTHONUTF8` 遮蔽）與 R76-35（PowerShell `Get-Content` 缺 `-Encoding`，在 PS 5.1 nightly 上）。**同一根因語意、兩個語言、兩個檔案群、兩套修法**。建議在鐵律三的觸發清單裡新增「PowerShell 讀檔編碼」一列並誠實填「無機械物」，讓它被 shrink-only 棘輪數進去（目前它是清單外的黑戶）。
- **「已達成解除條件卻仍生效的豁免」家族**：R76-05（nightly drift）、R76-49（root-infra `WAIVER_UNTIL`）、R76-06（E3 的鏡像形態）。三個獨立實例，建議在同一輪一起收，並把「豁免必須自動退場」寫成一條通則。

---

## 3. 假陽性剔除與嚴重度調整

### 3.1 假陽性

**本輪零筆判定為假陽性。** 12 維回傳的 78 筆 `confidence` **全部是 `measured`**，沒有一筆是 `inferred`
（我逐筆核對過 JSON 的 confidence 欄）。我另外親驗了 12 筆最高風險的（附錄 A），**全部成立，其中一筆比原報更嚴重**（R76-01：missing 27,222 而非 414）。

值得記錄的是各掃描員**自己**剔除的假陽性（這是本輪品質的正面訊號，我複核後同意）：

| 被剔除的候選 | 剔除者 | 剔除理由（我複核同意） |
|-------------|--------|----------------------|
| `.claude/settings.json` 102 處 hook 用裸 `python` | Scan-A | ONBOARDING:90/107 已明文記載「勿改 hooks 的裸 python」＝已知且已接受 |
| `check_sh_eol.normalize_rel_path()` 磁碟機大小寫 | Scan-A | `resolve()` 會正規化 `d:`→`D:`，且 Windows `PurePath` 比對本身不分大小寫 |
| `PG_REAL_ENABLED` 疑為誤植變數名 | Q3 | 實查 `:26` 證明是真的讀取點，**假設自證為偽** |
| `windows_smoke_latest.log` 0 bytes | Scan-M | 是同時段另一 agent 的 in-flight transcript（02:39:45 完成 6011 bytes）。**該掃描員同時記下「本輪的『現在幾點』本身就是我一度算錯的量測值」** |
| `_has_system32_segment` 第三份複本 | Scan-E | 8 個消費者全是測試檔，依 ADR §4.5「測試側獨立重寫不計入 SDS」⇒ 不構成 SDS 低估 |
| Grep 工具把內容裡的 `/` 渲染成 `\` | Scan-T | 差點誤判成 P0 級「非 raw 字串轉義炸彈」，以 Read + `repr()` 雙重反證。**這條值得升為紀律**（見 §6） |

### 3.2 我調整的嚴重度（2 筆，皆下修，附理由）

| ID | 原級 | 我的級 | 理由 |
|----|------|--------|------|
| R76-47（ruff 1,147 stale） | P1（Scan-T） | **P2** | 危害是**文件準確度**（誤導趨勢論證），無執行期／平台影響，也不會機械性重複咬人。它會被引用的次數有限且修法只有兩行。**但**它是本維度必跑項自身的反例、已存活八輪，故我把它放進最便宜的包（C／J）確保被做掉，不因降級而遺失 |
| R76-67（結構性存量報表） | P3（Scan-T） | **移出發現表** | 原掃描員自己的處置欄寫的是「**不清，只把數字接上既有的量測站**」，且「清除成本：不適用（判定不清）」。它是量測報表＋一則「不該修」的裁決，不是缺陷。列在發現表裡會讓下一輪誤以為有待辦 ⇒ 移到 §5.10 |

### 3.3 我**不**調整但要標注邊界的一筆

**R76-02（nightly-full PS 5.1 編碼）我判 P1 而非 P0。** 按字面，「該 step 每次執行必紅」符合「雲端必紅」；
但它**不阻斷任何東西**（`continue-on-error: True`）、不讓任何平台開箱即壞、不擋任何 push。
我選 P1 而不是 P0，理由是嚴重度定義的實質面是「阻塞」而非「紅字存在」。
**若複審者採嚴格字面判準，這一筆可以合理地判 P0** —— 我把分歧點明寫在這裡，而不是靜默選一邊。

---

## 4. 修復序建議

### 4.1 硬相依鏈（不可換序）

> 🔴 **本鏈已因 R76-00 重排**：原鏈以 R76-04 起頭並假設「閘門現在是綠的、等寫帳本才會紅」。
> 實測 rc **已經是 1**，故真正的第 0 步是解掉 R76-00（改名止血，或先騰餘裕再登記）。

```
序 0  R76-00  解掉「本檔未登記 ⇒ crossref rc=1」
        │  (a) 改名止血〔零 LOC 成本〕 或 (b) 走序 1 再登記〔正解〕
        │  ⛔ 未解之前：pre-push 快層與 root-infra-ci 皆紅，且會遮蔽序 3 的訊號
        ▼
序 1  R76-16  LOC 預警帶 + 騰餘裕
        │  ⛔ 是 R76-00(b) 的前置；也因為序 3/5 要動的兩支檔餘裕是 0：
        │     check_defect_log_crossref.py 1474/1474
        │     archive_defect_log.py        1507/1507
        ▼
序 2  R76-00(b)  登記本檔進 _GOVERNANCE_DOCS（+1 行，需序 1 已騰出餘裕）
        ▼
序 3  R76-04  帳本 8 列註記（純 .md）
        │  必須在「本輪第一列帳本」之前
        ▼
序 4  包 C 其餘（R76-08 / 36 / 37 / 47 / 52 / 56-811）
序 5  包 F 其餘 + 包 A（R76-01，可與序 4 平行，不同檔）
        ▼
序 6  包 D（雲端 workflow）：R76-02 ──必須先於──▶ R76-18（否則把編碼缺陷複製一份）
                              R76-50 必須與任何步數變動同 commit（檔頭快照鎖會紅，那是它該有的行為）
        ▼
序 7  包 B（排程／觀察期）：R76-06 的 E3 改寫必須與 R75 §5 D-4 四處同步清單併為同一 DoD
序 8  包 E / H / I / G（可互相平行，見 §4.2）
```

### 4.1b R76-00 的兩道棘輪死鎖（本輪唯一的「合法動作互為違規」）

```
        A 鎖 unregistered_governance_docs()          B 鎖 check_special_files()
        「CrossPlatform_*.md 必須登記」              「check_defect_log_crossref.py ≤ 1474」
                    │                                          │
                    │ 要求：_GOVERNANCE_DOCS +1 行              │ 現值 1474/1474（餘裕 0）
                    ▼                                          ▼
              ┌─────────────────────────────────────────────────────┐
              │  滿足 A ⇒ 1475 行 ⇒ 違反 B                          │
              │  滿足 B ⇒ 不登記   ⇒ 違反 A（現況，rc=1）            │
              └─────────────────────────────────────────────────────┘
                    唯一無成本出口＝改名（放棄受 A 管）
                    正解＝先降 B 的分子（R76-16 騰餘裕），再滿足 A
```

### 4.2 包分組（**同包＝改同一支檔，分開做會互踩**）

| 包 | 為什麼必須同包 | 成員 |
|----|----------------|------|
| **A** 開箱 | `ONBOARDING.md` 是熱檔（另被 R76-03/54 觸及，需協調） | R76-01 |
| **B** 排程／觀察期 | `run_local_nightly.ps1`（R76-05 豁免／R76-35 `-Encoding`／R76-56 `--help`／R76-59 印 credited date 四筆同檔）＋`windows_smoke_local.ps1`（R76-06 E3／R76-19 現況段同檔）＋`check_scheduled_task_drift.py`（R76-06 `--tasks`／R76-22／R76-60 三筆同檔） | R76-05, 06, 12, 13, 19, 20, 22, 35, 56(810), 58, 59, 60 |
| **C** 帳本／交棒 | `AutoSDD_Defect_Log.md`（R76-04/36/37/47）＋`check_defect_log_crossref.py`（R76-08/37 硬規則③）＋`CrossPlatform_Scan_Dimensions.md`（R76-08/52）＋`archive_defect_log.py`（R76-56-811） | R76-04, 08, 36, 37, 47, 52, 56(811) |
| **D** 雲端 workflow | `windows-compat-ci.yml`（R76-02/03/11/18/50 五筆同檔）＋`test_gha_action_versions.py`（R76-02 新鎖／R76-50 快照鎖同檔） | R76-02, 03, 11, 18, 49, 50 |
| **E** 護欄鎖鑑別力 | 🔴 **`test_doc_loc_baseline_freshness_r60.py`（4,030 行）被 5 筆觸及**（R76-07/25/26/34/62），並行編輯必然衝突；`test_adr_xplat001_c1c2_lock.py` 被 R76-24 觸及 | R76-07, 24, 25, 26, 27, 34, 57, 62 |
| **F** LOC 餘裕 | 單檔 `check_loc_budget.py` ＋ `AutoClaude/CLAUDE.md`；**另含 R76-00(b) 所需的 `check_defect_log_crossref.py` 騰餘裕**（1474/1474）⇒ 本包是整輪的解鎖前置 | R76-16, **R76-00(b)** |
| **G** skip 盤點 | `skip_tag_policy.py`（R76-15/38/39）＋`autoclaude-ci.yml`（R76-14/66，**與包 D 不同檔故可平行**）＋兩支 conftest | R76-14, 15, 38, 39, 40, 41, 42, 66 |
| **H** 淨化層／NTFS | 🔴 **`tools/git-hooks/pre-commit` 被 R76-10（grep locale）與 R76-30（NTFS case 分支）同時觸及**；`check_ntfs_paths.py` 被 R76-01 與 R76-30 同時觸及 ⇒ **包 A 與包 H 需協調該檔** | R76-10, 28, 29, 30, 63 |
| **I** 編碼掃描器／pre-push | `pre-push` 被 R76-09（剝 PYTHONUTF8 的 leg）／R76-23（guard 迴圈）／R76-48（慢層觸發條件）三筆觸及 | R76-09, 23, 48 |
| **J** 文件／SSOT／技術債 | 多檔、彼此獨立，可拆多個小 commit 平行 | R76-17, 21, 31, 32, 33, 43, 44, 45, 46, 51, 54, 55, 61, 64, 65 |

### 4.3 可完全平行的分組

包 **A**、**D**、**E**、**G**、**I** 之間零檔案交集 ⇒ 可同時派工。
**例外兩處**（必須指定同一人或序列化）：
1. `check_ntfs_paths.py` — 包 A（R76-01 印算式）× 包 H（R76-30 移除上標列）
2. `ONBOARDING.md` — 包 A（clone 第 0 步）× 包 D（R76-03 表③ job 層欄）× 包 J（R76-54 拆 47→29+18）

### 4.4 收益/成本速覽（只列 P0+P1）

| ID | 成本 | 風險 | 收益 |
|----|------|------|------|
| **R76-00** | (a) 極低（改一個檔名）／(b) 低（1 行登記，但需先付 R76-16 的騰餘裕成本） | (a) 低但把「該不該受治理」變成隱性決定／(b) 零 | **極高**（**現在**就在擋每一次 push，且遮蔽 R76-04 的訊號） |
| R76-04 | 極低（8 行 .md 註記） | 零 | **極高**（不做則本輪每次 push 被擋） |
| R76-16 | 低（~25 行 + 1 測試） | 極低（rc 不變） | **極高**（解鎖序 2/3；把六個零預警硬閘轉成有預警） |
| R76-01 | 低（文件 + 一個算式） | 低（`--global` 需確認不與 CI runner 假設衝突） | **極高**（唯一 P0；Windows 開箱） |
| R76-08 | 低（1 行文件 + 1 支判準翻轉） | 低 | 高（消滅「有鎖在守假話」） |
| R76-02 | 低（run 本體改 ASCII + 1 鎖） | 低 | 高（一個 step 自 R48 從未跑過） |
| R76-10 | 低（2 行 grep 改寫 + rc 判斷） | 低 | 高（消滅一道 locale 相依 fail-open） |
| R76-14 | 低（1 行 pip extras + 1 行 pytest 路徑） | 中（148 支從未跑過的斷言首次執行，可能真的紅——**那正是收益**） | **極高** |
| R76-07 | 低（複用既有 `hook_command_scripts()`） | 低 | 高 |
| R76-05/06 | 中（跨 4~5 檔 + 測試期望翻向） | 中（E3 改寫涉及退場決策，需與 D-4 清單併案） | 高 |
| R76-09 | 中（新 AST 判準 + 一條剝 env 的 leg） | 中（新判準會抓出存量債，需先量） | **極高**（整類 mac→Win 缺陷目前不可見） |
| R76-11 | 中（兩支 smoke 各加一步） | 中（CI 時間增加） | 高 |
| R76-12 | 低（.gitignore + `git rm --cached`） | 低 | 高（保住唯一未達標的 GA 軌帳本） |
| R76-13 | 低（兩支 script 各加兩欄） | 低 | 高（PASS 訊息目前在說假話） |
| R76-15 | 中（跨兩子專案 + 4 檔） | 低 | 中高 |
| R76-17 | 低（1 行宣告 + 3~4 處字串 + 1 句文件） | 中低（改 extras 面，須先 grep workflow 是否隱式依賴） | 高（mac 安裝面 −80% 發行版數） |
| R76-03 | 低（SOP + 收輪清單一條） | 零 | 高（21 天盲區） |

---

## 5. 判定「不該修」／需授權（10 類）

| # | 標的 | 為什麼不該（現在）修 |
|---|------|---------------------|
| 5.1 | AISDLC_SDD **v0.01~v0.29 凍結版**：2,790 筆 ruff、47 支缺 BOM `.ps1`（其中 29 支 PS 5.1 必 ParserError）、`save_abort_report` 29 版未淨化站點、28 份 `requirements-ci.txt` 差異 | **Copy-on-Evolve 政策**：44 輪來只在使用者核准的例外下打破過兩次（R44/R45 判例）。v0.01 另是 ci-gate 的**凍結基線**，改它等於改被測基線。`requirements-ci.txt` 那批更是**設計使然非漂移**（`check_script_parity` 實跑：被鎖的三處 pyproject／v0.01／LATEST 皆 `pytest==9.1.1`，中間 28 份是無人安裝的歷史快照）。**只登記、不動手** |
| 5.2 | 11 支需 `claude` CLI binary 的 skip | 付費 binary ＋ 巢狀 session 必死結（DEF-101-089，`CLAUDECODE=1`）。**永久不覆蓋**，正確處置是加一個新標籤明示、登記進盤點文件，不要混進「可救的 152 支」 |
| 5.3 | UEP 5→4（ADR-XPLAT-002 Phase 2-B） | 需 **PM signoff**，§8.1 自 R67 建立至今是空表。連續 10 輪 ΔUEP=0 **責任不在工程側**，不要在工程包裡硬推 |
| 5.4 | 護欄層 GLC 樹級**硬上限** | ADR §4.3 已用兩組實測否決兩種上限設計（固定成長率、零餘裕棘輪），該論證不重辯。R76-24 的正解是**只量不判**的千行桶棘輪，不是設上限 |
| 5.5 | 改判 DEF-101-561③（把「禁新增鎖檔」換成「per-file 上限 + 檔數不設限」，即 R76-53 的第二步） | 推翻一條既有裁決，須帶實測數字走 §8.1 回執，**不得由執行者自行改判**。第一步（只量不判的 per-file 報表）不需 signoff，可做 |
| 5.6 | 把未橋接的 4 支 hook 橋進根層 `.claude/settings.json` | 會改動 **PreToolUse deny 面**，該檔自己記載過 P0：「hook 誤觸 deny 會把所有工具硬鎖死」。R74 已明文列為射程外並交棒 |
| 5.7 | ~~刪 `AutoClaude/tools/reschedule_g0_gatecheck.ps1`~~ **已於 R76 執行完畢（DEF-101-865），本列作廢** | 🔴 本列原判「成本中、收益低」並改推**低成本替代＝加一行 `# DEPRECATED`**；掌舵者要求技術債要真的清掉，故本輪把款一次付清。實際耦合面比本列估的**多一倍**：除 `_SINGLE_SIDED_EXEMPT` ＋ `ONBOARDING.md` 外，還有 macos-compat-ci 兩處 `paths:`、3 檔散文註記，以及 **4 個實測型下限**（`sched_family` 3→2、`AutoClaude/tools` floor 7→6 **兩個站點**、SSOT 35→34、AC 48→47）——本列原文只點到兩處且行號已 stale。`_TIER_BASELINE` 那一筆**刻意不刪**（該表維護規則：已收斂的 key 留為永久記憶，`_TIER34_FLOOR` 課責數把它仍計入 ⇒ 10/10 不變、地板不必也不得下修）。**教訓：「刪一支孤兒」的真成本不在檔案本身，在它被登記過幾次；沒現查就估成本，會系統性低估** |
| 5.8 | AutoClaude 樹**全樹** `ruff --fix`（R76-64） | 4 支檔 LOC tier 餘裕僅 5~7 行，而 E501 折行**會增行** ⇒ 兩個硬閘互斥。只做**會縮行**的那幾類（UP045/UP037/UP006/UP012），且 `sdd_governance_plugin.py` 的 2 筆走行內 `noqa`（0 行成本）；**不得**加 per-file-ignores（整檔永久失去該規則保護） |
| 5.9 | drift/observability 去重鍵改本地曆（R76-59 的「真正解法」） | 需一次性 migration，會斷既有 44/37 筆帳本的語意。本輪只該**把邊界講出來並可查**（加 WHY + 印 credited UTC date 與本地時刻） |
| 5.10 | **結構性存量本體**（凍結複本佔 tracked 行數 92.2%、護欄測試樹／生產碼 = 2.04x） | 兩者都受明文政策保護（5.1 與 5.4）。把它們列進「可清清單」會逼出該 ADR 自己警告過的壞行為（把可辯護的列硬刪）。**處置＝只維持可觀測**：數字不寫進任何散文（會 stale，正是 R76-47 的病），只在維度定義檔留「一律現查」的配方 |

**另有一筆需人拍板方向（非不該修，是不該由執行者選）**：R76-30（COM¹²³/LPT¹²³）——
「移除四處」還是「只保留在兩個 sanitizer、拿掉兩個 validator」改動的是 **ADR 級判準（誰是權威模型）**。
但無論選哪個方向，**四處的「本輪無真機、未跑 protectNTFS 對照」那段話必須換成 R76 的實測結果**——
留著它就是本 repo 頭號教訓「訂正註記逐字引述假話＝製造新假話」。

---

## 6. 未覆蓋面誠實揭露

### 6.1 全維度共通的最大缺口

**🔴 macOS 側零真機實測（12/12 維皆然）。** 本輪只有 Windows 11 真機。以下結論**全部是推論**，不是量測：

- R76-01「mac 側 PATH_MAX 1024/4096 故無此形態」
- R76-09「方向乙（缺 encoding）在 mac 上全綠」、「方向甲在 mac 上會炸」
- R76-11「macos-smoke 不跑 AutoClaude 測試樹」（YAML 逐行實查，但非 mac 上真跑）
- R76-15 的 mac 側後果（`AISDLC_SDD/conftest.py` 在 mac 上反而是唯一會印 Windows 區塊那側）
- R76-17「162 個 pyobjc 發行版／24.4 MB」（引用 R68 的 mac 真機量測，本輪無法重現或反駁）
- R76-31「POSIX 佈局 2→4 筆的漏格在 mac 上是降級而非當下故障」
- R76-43「裸 `python` 在 mac 上的解析」
- R76-61「在 mac pwsh 上會拿到 `PlatformNotSupportedException`」
- Scan-M 必跑項的 **bash 側整條**：`install_mac_nightly.sh report_heartbeat` 在 Windows 上 source 即 exit 1，故 `awk %.1f vs python {:.1f}`／`_age_s -gt 8*86400 vs age_days > 8` 兩組 8 天邊界的 bash↔python 分歧（R67-M40/R68-M32 聲稱已消除）**本輪未複驗**
- macOS 側 210 支 skip **一支都沒實測**（ONBOARDING §7 macOS 欄的所有敘述都是從 skip 條件方向推導）
- ADR §5 Phase 3 第 1 列的驗收載具 P3-V2 在非 Darwin **整支 skip**，該節自陳「屆時的全綠是空轉」⇒ 本輪刻意不跑、不宣稱任何等價性

**⇒ 建議：下一輪必須是 macOS 真機輪**，且開場第一件事是把上列 11 條逐條驗掉。

### 6.2 「必跑項未完成」（依維度定義檔判定，非我的主觀）

| 維度 | 未完成的必跑項 | 缺口大小 |
|------|---------------|----------|
| **Scan-H** | 必跑項① **31 個新增鎖類別只做了 4 支紅綠實測** ⇒ 依 Scan-H 判準①，其餘 **27 支一律 `NOT-PROVEN`**（含 `TestBlockBashHookGuidanceSurvivesNonUtf8Locale`、`TestPreCommitBlocksCrOnShellScripts`、`TestSkipDirectionAndTagSymmetry`、`TestScheduledTaskDriftChecker` 等）。必跑項② 只查 4 張豁免表（另 12+ 張未驗，其中 `_WINDOWS_SKIP_TAG_EXEMPT` 與 `_COLLECTION_EXEMPT` 現為**空表** ⇒ stale 自檢迴圈零次＝結構上靜默通過，未驗非空時是否有牙）。必跑項③ 掃描面不完整（未掃 `tools/*.py` 存量註解、`.ps1/.sh`、workflow yml、AutoClaude/AISDLC_SDD 鎖檔；146 筆候選只複核約 45 筆）。必跑項⑤ 三種形態未做：**34 處裸 `assert` 在 `python -O` 下會蒸發**（其中多支正是「掃描面非空」錨）未驗、`diff`/`Compare-Object` 的 comm 型等價物未掃、未實際把 glob 改壞驗自錨 | **本輪最大的方法論缺口** |
| **Scan-B** | 必查 3 的 `.ps1` 那一腿沒做注入（`test_python_calls_in_ps1_all_go_through_ssot` 與 `_KNOWN_NTFS_ANCHOR_SITES` 等值鎖只靠讀原始碼判定前瞻性）；凍結版 7 檔×29 版的正向斷言未做鑑別力注入；AST 掃描器已揭露的 6 項盲區只驗了 pathlib `/` 一項的可達性 | 中 |
| **Scan-F** | 必跑項 5「同一批腳本在兩引擎各跑一次」只做到**解析層全覆蓋**（137 支×2 引擎）＋**執行層一支**；`bootstrap.ps1`／`dev_start.ps1`／`install_windows_nightly.ps1`／`run_local_nightly.ps1` **未在兩引擎下各實跑**。必跑項 6 只對 2 個閘門做注入 ⇒ `run_root_unittests.py`(rc=0/1903) 與 `local_ci_gate.ps1`(7/7 PASS) 兩個綠是 **NOT-PROVEN**。未跑 `--full-tlc`（五軌 TLA+/TLC 零執行）、`-m chaos`（34 支 deselected 從未人工跑過）、`-Act`／`-Pg` | 中高 |
| **Scan-E** | 必做第 4 項的 **AC 逐輪序列未取得**（自寫 AST 抽取器算 34、生產碼實跑 48，差 14 ⇒ 有登記表非字面 literal 宣告）。必做第 5 項只完成「量出下一步該減什麼」，未完成架構級解法的可行性驗證（P3-V2 在非 Darwin 整支 skip）。§4.5 SDS 是否仍為 1 未獨立確認 | 中 |
| **Scan-D** | 未跑 `--write` 回填、未跑根層 unittest 全套（三組鎖的活體 rc 是以「重用純函式＋唯讀探針」取得等價證據，抓不到「該組測試在完整套件內被 skip／collect 不到」）。`AISDLC_SDD/CLAUDE.md` 三份交叉一致只完成約 2/3。雲端 CI 現況未查 | 中 |
| **Scan-A** | Scan-A 無列舉式必跑項（範圍描述）。未做：`AutoClaude/autoclaude/` 194 支生產碼逐檔通讀、Python `import` vs 磁碟檔名大小寫、workflow/腳本內字串路徑大小寫（**只會在 Linux runner 顯形**）、時間／locale 面幾乎空白（tz-naive datetime、`st_mtime` 整秒截斷、collation） | 中 |
| **Scan-M** | `-Status` 本身**無負向對照**（負向對照只做在 drift checker 上；改動掌舵者排程超出授權面）。`ac4_progress_check` 滾動窗與 `staleness_days` 邊界未做兩側注入。窗內 12 天全黑（2026-06-29→07-11）的**成因未查**（當期 nightly log 已被 14 天輪替刪掉，本機已無材料）。WakeToRun 能否真的喚醒**未取證**（需人工 ops 睡眠實驗）。`LastTaskResult` 只取樣到「從未執行」一種 | 中 |
| **Q3-Skipped** | `AISDLC_SDD/scripts/tests` 4 支紅**未追根因**（確認是同輪另一掃描員留在 index 的探針檔造成，但未區分「污染」vs「真實漂移」）；34 支 chaos 未實跑；11 支 claude CLI skip 未嘗試；macOS 210 支零實測；示範用 scratchpad venv 而非正式 `uv pip install -e '.[postgres]'` 路徑（理論等價，依紀律註明未驗）；`_RUNTIME_SKIP_RATCHET` 與全樹掃描反轉**只有設計、零 bug-injection** ⇒ `NOT-PROVEN` | 中 |
| **Scan-N** | `.sh` 帶 CRLF 注入**未做端到端**（`.gitattributes` 會正規化，削弱它超出授權面）⇒ R74 的行尾閘**未經本輪驗紅**。Windows 保留裝置名注入在 Windows 上**結構不可行**（`core.protectNTFS` 連 `update-index` 都拒絕）。其餘四種方向乙注入未做（260 字元絕對路徑、`os.rename` 覆蓋、`import fcntl`、`shutil.which('bash')` → WSL）。paths 覆蓋率用自寫近似 matcher（未實作 `!` 排除與 `*` 不跨 `/`）。未跑 coverage ⇒「零覆蓋」指「零非-ubuntu-runner 執行」 | 中 |
| **Scan-G** | 硬規則③ 回執反查只做帳本**主檔** 10 筆，`AutoSDD_Defect_Log_archive_*.md` 家族（數十份）完全沒查。18 筆「已結列殘留待辦」只逐字判讀 6 筆，剩 12 筆未判讀。`orphan_backlog_problems()` 的**跨列**不涵蓋型未手動補洞。未查 `AISDLC_SDD/**` 活文件內的 backlog 宣稱（軌道② 帳本不在根層任何閘門射程內） | 中 |
| **Scan-C** | 必查 4「排程機制對稱」只做靜態對帳，未實跑 `-Status`／`--status` 修前修後逐字對照、未做「植入死排程後 `--status` 是否仍報健康」負向對照。`run_local_nightly.ps1`(1,960 行) vs `.sh`(264 行) 只讀檔頭去向帳目，未逐行對帳退出碼語意與 log 落點。5 支 workflow 不被任何 compat-CI paths 涵蓋，未逐支確認有無 tools/tests 消費者。編碼缺陷只取到 **n=1** 的 en-US(CP1252) runner 樣本，zh-TW(CP950) runner 形態無法取樣。macos-smoke step[18] vs windows-smoke step[22] 的配對**留白** | 中 |
| **Scan-T** | 未跑任何測試套件（唯讀存量量測 + 避免並行互踩）⇒ 所有「清除成本／風險」欄的驗證指令是**建議**不是跑過。函式級死碼**完全沒掃**（只到檔案級；需 `vulture`，未為此裝新依賴）。死碼掃描是「檔名字面提及」啟發式 ⇒ 我的 5 支候選是**下界不是全集**。13 對 `.sh`/`.ps1` 語意漂移沒查（沿用 DEF-101-068(d) 拍板）。29 份凍結版只做一組逐份 diff | 中 |

### 6.3 缺席維度

**零缺席。** 維度定義檔 `CrossPlatform_Scan_Dimensions.md:18-30` 定義的維度是
**Scan-A / B / C / D / E / F / G / H / M / N / T（共 11 個）**，本輪全數執行，另加一個任務書指定的
專項 `Q3-Skipped`（不在該表內）= 12 路。

> 🔴 **順手擋掉一個必然的假發現**：對該檔跑 `grep -oE 'Scan-[A-Z]'` 會多出**兩個單字母命中**
> （`:373`）。**那不是兩個缺席維度**，是該檔第 369-373 行明文記載的正則截斷偽陽性
> （R14 期臨時長名被 `Scan-[A-Z]` 截斷），該檔自陳「本包實測踩過一次」。
> 🔴 本段刻意**不逐字複述那兩個代號**（R76 收斂包實測）：邊界宣告的唯一住所是維度表那一段，
> 逐字複製到第二個家會讓 `test_adr_xplat001_c1c2_lock.py` 的 SC-7 把複本讀成真的「使用」而誤紅
> （SC-7 只排除維度表自己）。下一輪若有人「發現兩個維度從未執行」，請直接讀
> `CrossPlatform_Scan_Dimensions.md:369-373` 的邊界宣告，不要把它抄過來。

### 6.4 本輪環境本身的取證限制（會影響上列所有「綠」的有效期）

- **並行污染**：session 期間至少 3 個其他 agent 在同一主樹活動。我開場 `git status` 是 clean（只有帳本歸檔作業 + 一份新盤點文件），但 Scan-H 記錄到它跑完控制組後出現四項非它造成的改動；Scan-F 的 AISDLC_SDD ci-gate 曾因另一 agent 留在 index 的探針路徑而假紅（改以隔離 clone 取得乾淨 rc=0）。**⇒ 任何「全套 rc=0」只對取得它的那個時點有效**；收輪者必須在所有包停工後於主樹重跑一次。
- **worktree 隔離盲區**：Scan-F 的 ci-gate 綠是在「HEAD 內容」上取得的，**不含本輪其他 agent 尚未 commit 的修改**（記憶 [[worktree-isolation-uncommitted-blind-spot]] 的假陰性風險）。
- **量測管道自身會給假數字（本輪踩到 2 次，值得升為紀律）**：
  1. Grep 工具在這台 Windows 上把檔案**內容**裡的正斜線渲染成反斜線（Scan-T 差點誤判成 P0 級轉義炸彈，以 Read + `repr()` 雙重反證）。**任何關於路徑分隔符的判斷都不可只靠 Grep 內容輸出**——而路徑分隔符正是鐵律三的觸發項之一。
  2. Scan-M 一度把 0-byte log 讀成缺陷，複查發現是 in-flight transcript。**「現在幾點」本身就是一個會算錯的量測值**，任何以 mtime 推論「幾小時前」的結論都必須先對現在時刻取證。

---

## 7. 建議新增的判準（由 R76-00 直接推導，非泛泛建議）

現有 Scan-H 五條必跑項全部是**單鎖視角**：每一條都在問「這一道鎖有沒有牙／有沒有 stale 自檢／
有沒有人看它的 rc」。**沒有一條問兩道鎖之間的關係**，而 R76-00 證明那個縫隙會產生
「合法動作互為違規」的不可滿足狀態。建議補兩條：

| 建議判準 | 為什麼（本輪實證） | 落地形態（最便宜） |
|---------|-------------------|-------------------|
| **⑥ 新鎖要求的補救動作，是否會違反另一道既有硬閘？** | A 鎖要求 `_GOVERNANCE_DOCS` +1 行，B 鎖（1474/1474）禁止 +1 行 ⇒ 工具訊息教的第一條修法在磁碟現況下**不可執行** | 凡「錯誤訊息教人往某支檔加內容」的鎖，其測試須斷言該檔在 `check_loc_budget` 下有 ≥N 行餘裕（N＝該修法的行數成本）；否則訊息要同時給出零成本出口 |
| **⑦ 同一支工具內多道檢查的早退順序，是否會遮蔽後面檢查的訊號？** | `check_defect_log_crossref.py:1297` 早退，讓 R76-04 那 8 筆孤兒警告**整批消失**，而消失方向是「看起來變乾淨」 | 該類工具改為「全部檢查跑完再彙總 rc」，或在早退處印一行「尚有 N 道檢查未執行」；測試以雙缺陷注入驗證兩者都被列出 |

> 這兩條與 §5.4／§5.5 的界線：它們**不設任何新上限、不推翻任何既有裁決**，只要求
> 「鎖的錯誤訊息必須是可執行的」與「rc=1 不得吃掉其他檢查的輸出」，故不需 PM signoff。

---

## 附錄 A：合成員親驗紀錄（本輪真跑，逐字輸出見上文各筆 evidence）

| # | 驗的是哪筆 | 指令（cwd 皆為 repo 根或註明） | 結果 |
|---|-----------|-------------------------------|------|
| 1 | R76-04 | `python tools/check_defect_log_crossref.py`（**本檔寫入磁碟之前**跑的） | rc=0，但印出 **8 筆** `⚠️ 當前輪時鐘 fail-open 窗口` 逐字警告 + 18 筆已結列殘留待辦 |
| 1b | **R76-00** | 同一條指令，**本檔寫入磁碟之後**重跑 | **rc=1**、輸出只有 2 行（`❌ 具名治理文件涵蓋面與磁碟脫節（1 筆）` 點名本檔）⇒ ①第 1 項的 rc=0 已成過期量測，我保留它並標明時點而不是刪掉；②該工具在 `:1297` 早退，**第 1 項那 8 筆警告現在跑不到**。🔴 這正是本 repo 頭號紀律的實例：**同一條指令、同一台機器、相隔十幾分鐘，rc 由 0 翻 1，而肇事者是我自己的產出物** |
| 2 | R76-05 | `python tools/check_scheduled_task_drift.py` | `status=ok`／兩支任務各「全部 7 項設定符合期望」／**RC=0** |
| 3 | R76-08 | `from lib.defect_ledger_index import reassign_hit` 六種輸入 | 否定語意 4 種皆 **False**、合法 2 種皆 True ⇒ 規格段的「已實測不涵蓋」為假 |
| 4 | R76-08 | Read `test_check_defect_log_crossref.py` 的 `test_the_spec_records_the_known_uncovered_forms` | 逐字讀到 `for token in ("否定語意", "deferred@R59"): self.assertIn(...)` ⇒ 假話被綠燈測試釘死 |
| 5 | R76-07 | Read `test_doc_loc_baseline_freshness_r60.py:2806-2830` | 逐字 `:2816 if name in settings_text:` + `continue` ⇒ 整檔 substring 確認 |
| 6 | R76-10 | 以 LF 腳本經 `Find-GitBash` 跑三組 grep | 無 locale → **rc=134 Aborted**／`LC_CTYPE=C.UTF-8` → rc=0 命中／`-Fx` 不帶 `-i` → rc=1；`grep (GNU grep) 3.0` |
| 7 | R76-10 | Grep `pre-commit` | `:174` 與 `:206` 皆 `grep -iFx -e … \|\| true` |
| 8 | R76-01 | `git clone`（無旗標／帶 `-c core.longpaths=true`）到同長度目標 + 檔數對比 + 三層 config 查詢 | A rc=128／301 檔／無 bootstrap.ps1；B rc=0／27,523 檔／有 bootstrap.ps1；system+global 皆 rc=1、local=true。**探針 clone 已刪除（0 殘留）** |
| 9 | R76-16 | 以 `check_loc_budget` 自己的函式算全部 `SPECIAL_FILES` 餘裕（cwd=AutoClaude） | `0 / 0 / 0 / 1 / 1 / 2` 六格 + `TIER_WARN_MARGIN = 6` |
| 10 | R76-13 | 兩支 GA check 實跑 + 自量兩本帳本的日曆 span 與 gap | obs `[PASS] green_streak=44` rc=0 但 **last30 span = 58 天、最大 gap 12 天**；drift `[FAIL] 28<30` rc=1、span 65 天 |
| 11 | R76-12 | `git ls-files --error-unmatch` × 5 本帳本 | drift **TRACKED**，其餘 4 本 untracked |
| 12 | R76-02 / R76-18 / R76-50 | 自寫 pyyaml + 位元組掃描（cp1252 引號位元組 0x82/84/8b/91/92/93/94/9b） | windows-smoke step[2] nonascii=0 **ASCII-SAFE**、`continue-on-error=None`、**steps=25**；windows-nightly-full step[2] nonascii=195／step[3] nonascii=441 皆 **PARSE-HAZARD**、`continue-on-error=True` |
| 13 | R76-17 | `importlib.metadata` + `git grep keyboard` | keyboard 0.13.5 → `Requires-Dist: pyobjc ; sys_platform == "darwin"`；`pyproject.toml:24 "keyboard>=0.13",` 無 marker |
| 14 | R76-03 | `gh issue list --state all --limit 20` | 唯一單 **#10**、state=**OPEN**、created 2026-07-14、updated 2026-08-03 |
| 15 | §6.3 缺席維度 | Grep 維度定義檔 + Read `:18-30` 與 `:368-379` | 已定義維度＝A/B/C/D/E/F/G/H/M/N/T 共 11 個，全跑；另兩個單字母命中為該檔 `:369-373` 明載的正則截斷偽陽性（刻意不逐字複述，見 §6.3 註） |

**合成員零改動聲明**：除本檔外未寫入任何檔案。
🔴 **但「零改動」不等於「零後果」**——本檔的**存在本身**就讓 `check_defect_log_crossref.py` 由
rc=0 翻 rc=1（R76-00）。我把這件事寫進報告而不是靜默改名規避，理由是它是一筆真缺陷
（兩道棘輪在交界處不可滿足），規避掉就只有下一個新建 `CrossPlatform_*.md` 的人會再踩一次。
**收輪者請先讀 §0.2 R76-00 再決定要走出口 (a) 還是 (b)。**第 8 項的兩個探針 clone 建於 scratchpad 並已刪除，
第 6 項的探針腳本亦在 scratchpad。`git status` 較開場僅多本檔（另三項變動屬同輪其他 agent 的帳本歸檔作業）。


---

# §R76-FIX　複審收斂包（Fixer）逐筆取證

> 角色＝Fixer（修完全部存活 blocking 並把樹恢復成全綠）。本節每一行都是 2026-08-05 於
> Windows 11 Pro 原生 PowerShell 真跑的輸出，指令與 rc 同列。**未經我當回合實跑的宣稱一律
> 標為「前手落地、我只做存在性確認」**——這一節自己也適用「不採信任何宣稱」。

## §R76-FIX-0　先講清楚我進場時樹是什麼狀態

我不是從零開始修：進場時 `git status` 已有 57 筆變動，其中 `AutoClaude/tools/ga_window.py`
等前手（同一輪的前一段 Fixer 作業）的產物已在磁碟上。所以下表把 12 筆存活 blocking
分成兩類，**我只為「我做的」那一類的紅綠負責**：

| 複審筆 | 進場時狀態 | 我做了什麼 |
|---|---|---|
| ARCH-01 標記碰撞 | 前手已改名並加對照鎖 | 🔴 **它把樹弄紅了**——我抓到並修（見 §R76-FIX-2） |
| ARCH-02／SD-02 訊息餘裕登記表 | 前手已改三欄＋逐筆迭代＋納管第二支工具 | 存在性確認（`_ADD_CONTENT_DIRECTIVES` 實測 5 筆三欄） |
| ARCH-03 `nightly-red` 無新鮮度 | 前手已補 `nightly-run`／`nightly-checked-at` | 存在性確認（ONBOARDING 錨 `:488` 三欄俱在） |
| SA-01 Scheduled doc 自相矛盾 | 前手已改（含 SD 複驗要求擴大的 `:368` 那半） | 逐行讀過確認無殘留假句 |
| SA-02 fail-open 正則漏行尾註解 | 前手已收斂 SSOT | 🔴 **帳本那半沒修**——我補（見 §R76-FIX-1） |
| SA-03 archive_59 索引 | **未修** | 我修（見 §R76-FIX-3） |
| SA-04 GA 終點過期 | 前手已補兩份檔的回執 | 逐行讀過 |
| SD-01 nightly gap 訊息說謊 | 前手已改帶 status | 存在性確認 |
| SD-03 `keyboard` 覆蓋損失 | 前手已改 `.[dev,lint,hotkey]` ＋三處文件 | 存在性確認 |
| SD-04 兩支 GA 判定 112 行複本 | 前手已抽 `ga_window.py` ＋`assertIs` 鎖 | 存在性確認 |
| QA-01 鐵律三 `$env:*` 假話 | **未修** | 我修（見 §R76-FIX-4） |

## §R76-FIX-0b　🔴 收斂包宣稱「11 道閘門全綠」，但有**兩道**當時是紅的

任務書轉述收斂包自陳 11 道全綠、舵手親驗其中 7 道快閘門為 rc=0。我逐道重跑，抓到兩筆紅：

| 閘門 | 我實測 | 誰造的 | 為何沒被發現 |
|---|---|---|---|
| `python tools/run_root_unittests.py` | **rc=1**（ARCH-01 修法造成的 stale 標記） | 本輪 | 該包只跑了自己那支測試檔，沒跑整棵根層閘門 |
| `ruff check tools/`（pre-push leg ④／`root-infra-ci.yml` 第 16 道） | **rc=1**（3 筆 E501） | 本輪（HEAD 版同檔 rc=0） | **整輪無人跑過這一道**；且它不在舵手親驗的那 7 道裡 |

⇒ 兩筆都不在「7 道快閘門」的清單內，也都不會被 `pytest` 或缺陷帳本工具看見。這是本輪
`§R76-MATURITY` M3「作者自證不計分」那一條的直接證據：**自證過的收斂包，第三方一跑就紅兩道**。
立帳＝`DEF-101-858`（root unittests）／`DEF-101-864`（ruff）。

## §R76-FIX-1　SA-02 的另一半：帳本裡的假數字

複審指出兩件事，前手只修了機械面。我補帳本面：

```
python -c "...import test_doc_loc_baseline_freshness_r60 as m;
           print(m.cloud_fail_open_jobs(Path('.github/workflows')))"
→ 4
  autoclaude-mutation-on-change.yml:mutation-on-change
  autoclaude-pg-e2e-on-label.yml:pg-e2e-on-label      ← 修前逃逸的那一個
  macos-compat-ci.yml:macos-nightly-full
  windows-compat-ci.yml:windows-nightly-full
```

`DEF-101-846` 逐字寫著「現查 3 個 fail-open job」＝**寫成事實的假數字**，已就地訂正。
立帳＝`DEF-101-857`。

## §R76-FIX-2　🔴 ARCH-01 的修法自己把樹弄紅了（本輪最值得記的一筆）

進場後第一件事是跑根層閘門，**紅的**：

```
python tools/run_root_unittests.py                          → rc=1
tools/.last_failure.log:
  FAIL: test_subprocess_encoding_hygiene…test_repo_trees_have_no_unencoded_text_subprocess
  ['tools/tests/test_platform_neutral_paths.py:2050: encoding-ok 標記 stale（該行無被壓下的違規）',
   'tools/tests/test_platform_neutral_paths.py:2342: encoding-ok 標記 stale（該行無被壓下的違規）']
```

成因是**同一個缺陷換一層皮**：ARCH-01 的修法（把 file-IO 標記改名）是對的，但同一包在
**`#` 註解**裡逐字寫出了姊妹檔的標記字串來解釋這件事，而兩支掃描器的取標記函式**只認
COMMENT token**——在註解裡「提到」一個標記，與「登記」一個標記在機器眼中完全同形。
更難看的是該檔 `:2036` 上方**已經為自家標記寫過同一條理由**（「本註解刻意不逐字寫出它」），
只是戒了自己那一個字串、沒戒姊妹檔那一個。

處置：兩處註解改為不逐字引述任何編碼家族標記，並就地把它一般化成通則（要引述標記字串就
寫進 docstring／字串字面值）。複驗：

```
python -m unittest tools.tests.test_subprocess_encoding_hygiene → Ran 36 tests OK  rc=0
python -m unittest tools.tests.test_platform_neutral_paths      → Ran 73 tests OK  rc=0
```

立帳＝`DEF-101-858`。

## §R76-FIX-3　SA-03：archive_59 索引兩句假話 ＋ 留痕的結構性缺口

三項現查全部坐實（筆數與磁碟不符、`DEF-101-845` 兩張清單都沒進、「壓回 warn 線之下」為假
且違反同一標頭下一段自己的禁令）。處置分兩層：

- **散文層**：兩檔（`archive_59.md` 標頭與 `..._archive_INDEX.md` bullet）同步訂正，
  **不逐字重述被推翻的話**，筆數改為現查配方。
- **結構層**：標頭與索引新增「**被搬遷判準擋下**」欄——這是 `DEF-101-811`「排除留痕」
  先前結構上沒有的那一格（它只覆蓋 `--only`／`--keep` 路徑），也正是 845 消失在帳務外的
  原因。本次逐筆記名：`DEF-101-856`（判準① `cls=open`）／`DEF-101-845`（判準② 假陽性，
  已補反引號修正）。

複驗：`python tools/archive_defect_log.py --plan` 對 845 由「②狀態欄含活躍字樣 'open'」
轉為可搬（`925 B cls=fixed`）；`--check` rc=0；`check_defect_log_crossref.py` rc=0。
立帳＝`DEF-101-861`。

## §R76-FIX-4　QA-01：鐵律三對照表把一個有人守的形態記成沒人守

`git log -S` 實查坐實了最難看的那一點：掃描器與那句「無機械物」是**同一個 commit**
（R74 `a371068`）落地的。處置沿用同表 `Get-Command` 那一列的既有體例（保留「無機械物」
字樣＋括號內誠實交代唯一例外），因此 `_IRON_LAW3_UNCOVERED` 常數不必動。

🔴 **bug-injection 三向（我當回合真跑，不是讀出來的）**：

| 注入 | 期望 | 實測 |
|---|---|---|
| 該列拿掉「無機械物」字樣 | 棘輪鎖紅 | `AssertionError … 「\`$env:*\` 讀取」列未標『無機械物』` |
| 具名一個不存在的檔 | 假機械物鎖紅 | `CLAUDE.md 指名一個不存在的機械物 tools/tests/test_no_such_scanner_r76.py（三個解析基準皆找不到）` |
| 具名一個不存在的符號 | 同上 | `…但 \`TestNoSuchClassR76\` 不是該檔裡的 class／def ⇒ 指標已因改名或搬家靜默失效` |
| 現況 | 綠 | `ran=10 bad=0` |

> 🔴 **載具自驗（依任務書第 6 條）**：第一版注入腳本四組全綠，我沒有直接下結論「鎖恆綠」，
> 而是先懷疑管道——查出是我新寫的那一列**列內出現兩次**「無機械物」，`replace(..., 1)`
> 只換掉第一次，注入根本沒生效。改成整列重寫並 `assert` 該列確實不再含該字樣後才拿到上表。
> 這正是本輪任務書第 6 條在防的東西，記在這裡當實例。

立帳＝`DEF-101-862`。

## §R76-FIX-5　追加射程（本機 PG）— 四件事的落點

掌舵者當場推翻「本機沒有 PostgreSQL」這個共同前提。完整取證進了
`Skipped_Test_Inventory_R76.md` §4.7（含配方、三個基線、逐筆根因、四情境注入表、
pg18／pg17 版本差揭露），此處只放索引與結論：

| 任務書項 | 落點 | 一句話結論 |
|---|---|---|
| ① 修 4 支 failed | §4.7.2／§4.7.3；`DEF-101-859`／`DEF-101-860` | 3 支＝開發 DB 沒真的 migrate 過（測試是對的）；1 支＝ground truth 與語料必須同一次 seed（檢索本身實測 recall 0.999） |
| ② 訂正假前提敘述 | §4.7 全節＋§6 訂正框＋§7 兩列 | 「需要 PG」不等於「沒有 PG」；157 支本機當場跑得到 |
| ③ 未啟用 vs 缺件 | §4.7.5；`DEF-101-863`（open＠R77） | 已落到踩到的那一支檔的 reason 字串；全樹 224 支尚未逐支套用，誠實交棒 |
| ④ pg18／pg17 揭露 | §4.7.4 | 本機 18.4、閘門 pg17；目前無已知行為差（複驗者曾以 pg17 重跑得逐位相同的 1241/40），但那是量測不是推論 |

---

## §R76-FIX-6　🔴 同一輪的兩列互相矛盾，而**沒有任何東西會說話**（收尾包發現，刻意不落地）

`DEF-101-856` 的第 ① 項寫「`reschedule_g0_gatecheck.ps1` 只標 DEPRECATED 未刪」，
`DEF-101-865` 寫「刪檔＋同步全部登記站點」。**兩列同輪、同標的、結論相反**，而磁碟站在後者
那一邊（收尾包當回合 `Test-Path` 實測回 `False`）。第 ① 項因此變成一條會讓 R77 白做一次的指令。

**為什麼現有判準一條都沒響**（逐條實查，非推測）：

| 既有判準 | 它問的問題 | 為何對本形態失明 |
|---|---|---|
| `orphan_backlog_problems()` | 承接輪號是不是早於當前輪 | 兩列的承接輪號都合法 |
| `residual_todo_notes()` | **已結列**是否還留著待辦字樣 | 矛盾的那一列是 `open`，直接被 `continue` 掉 |
| `supersession_notes()` | 同一列內是否「首詞舊、後段訂正」 | 訂正住在**另一列**，不在同一列內 |
| `_scan_target()` | 文件的狀態宣稱 ↔ 帳本實況 | 只跨「文件 ↔ 帳本」，不跨「帳本 ↔ 帳本」 |

⇒ 帳本**內部**的自我矛盾，在結構上落在所有判準的交界縫隙裡。

### 為什麼本輪不落地（依據是實測，不是「太難」）

通用的「兩列語意矛盾」偵測需要語意判斷，不在逐行正則的能力內（同 `orphan_backlog_problems()`
docstring 已載明的跨列邊界）。唯一可機械化的**代理**是：**未結列具名了一支磁碟上不存在的檔**
——本案正是靠這個特徵才可見。收尾包寫了原型（`git ls-files` 建路徑／basename 索引，掃未結列
反引號內帶副檔名的 token）對真帳本實跑，結果：

```
命中 9 列：DEF-53-001 / DEF-101-217 / DEF-101-271 / DEF-101-274 / DEF-101-398
          DEF-101-435 / DEF-101-596 / DEF-101-752 / DEF-101-856
```

逐列人工判讀後，**真陽性只有 2~3 列**，其餘六列分屬四種誤判形態：

1. **佔位名**（`SDD_improving_Automation_NN.md` 的 `NN` 是樣板變數，不是檔名）；
2. **提案中尚未建立的檔**（修法欄寫「建議新增 `tools/lib/bootstrap_lock.py`」）；
3. **刻意 untracked 的探針**（`_probe_untracked_violation.py` 之類，「不在樹裡」正是該列的內容）；
4. **相對路徑形態**（`../tools/dev_start.py` 由 `AutoClaude/` 起算，真檔在根層）。

訊噪比約 **25%**。上線即需白名單，而本帳本的首詞鎖是**零白名單**上線的（《格式定義》自載
「沒有任何『暫時容忍』清單可腐化」）——為了一條 25% 準確率的 warning 開一份白名單，
方向與該慣例相反。**故本輪只立帳不落地**（`DEF-101-867`），並把成本結論寫成可複驗的數字
而不是「評估後認為太難」。

### 交給 R77 的收斂設計（三步，每步都有可判定的驗收）

1. **先砍掉形態 1／2／4**：只對「帶目錄分隔符、且該列狀態欄不含『建議新增／應新增』字樣」
   的 token 判定；相對路徑先以列所在子專案為基準正規化。驗收＝對現帳本重跑，命中列數下降到
   只剩形態 3 與真陽性。
2. **形態 3 用「該列自己說它 untracked」放行**，而不是用檔名白名單——判準綁**列的內容**，
   不綁具名清單，才不會腐化。驗收＝`DEF-101-752` 不再命中，且把該列那句話刪掉後它會重新命中。
3. **上線為 warning-only**（比照 `residual_todo_notes()`），且**只有在真陽性率 ≥ 80% 時才上**。
   🔴 常亮的低準確率警告會退化成背景噪音——本 repo 已為此付過學費
   （`run_root_unittests.py` 的兩層 ratchet 註解逐字記載「純 WARN 擋不住 11 輪沒人重釘」）。

---

# §R76-MATURITY　四方對「迭代到怎樣才算成熟」的判準（掌舵者第 6 點）

> 掌舵者六點要求中的第 6 點在複審階段沒有人回答完。本節把四個角色各自的貢獻**收斂成一份
> 可量測、可證偽的判準表**，並附**本輪實測基線值**——沒有基線的判準是散文，不是判準。
>
> 🔴 **誠實邊界（先講）**：本節的四段角色貢獻，其中 Architect／SA／SD／QA 的原始論述在交到
> 我手上時**部分被截斷**。我保留了每段能確認的判準骨架與其明確給出的基線數字，
> **沒有替任何一位補寫他沒說完的話**；凡我自己加的（門檻取值、量測配方、本輪實測值）
> 一律標「Fixer 補」。要看原始完整論述請回四方複審輸出。

## 共同立場（四方唯一完全一致的一句）

**「閘門全綠」與「成熟」無關。** R75 的 12 筆 blocking 有 8 筆是「閘門自己沒有鑑別力／
射程失明」；R76 存活的 12 筆裡，**沒有一筆**會被任何現有閘門攔下。所以成熟度的量必須
量「缺陷穿過幾道閘」，不能量「有幾道閘」——後者可以靠新增鎖無限刷分，而新增鎖正是
本 repo 目前缺陷的最大單一來源。

## M1〜M6　判準表（每一條都可用本 repo 現成載具跑出數字）

| # | 判準（可證偽的斷言） | 量測配方 | 本輪實測 | 成熟門檻 | 來源 |
|---|---|---|---|---|---|
| **M1** | UEP 抵達可辯護地板，且該狀態被**正式承認**而非每輪重新解釋 | `python -m unittest tools.tests.test_adr_xplat001_c1c2_lock`（末行印 `[Scan-H triplet]` 三元組）＋ `ls` ADR-XPLAT-002 §8.1 回執表 | 🔴 **三元組一律現查、本欄不再登載**（本輪 E-11 訂正：此格原寫死的 AC 值在 R76 刪掉一支真孤兒、`_SINGLE_SIDED_EXEMPT` 隨之下修的**同一輪**就過期了，而鎖檔那家自緊、散文這家沒人守）。自 R65 起 ΔUEP 連續為 0 的**狀態**仍成立；§8.1 自 R67 建立至今**空表** | 二擇一：§8.1 出現回執且 UEP 較現值少 1；**或** ADR 正式宣告現值為終態並把 `_EXEMPT_PAIRS` 凍成 shrink-only、不再列為「目標」 | Architect |
| **M2** | 假宣稱密度單調下降 | 分子＝該輪複審抓到的「失實宣稱」筆數；分母＝該輪新帳本列數，**現查**：`python tools/check_defect_log_crossref.py --unresolved-count` 取當前輪代號後，數「發現情境」欄提及該輪的列（跨主檔＋所有 archive）。🔴 **本欄不得登載分母常數**——見右欄三個結構缺陷 | 🔴 **R76 的分母現查為 36〜37（依數法），不是此格原先寫死的 25**（本輪 W-06 重量：`DEF-101-832..867` 零缺號＝36 列；「發現情境」提及 R76 者＝37 列）⇒ 原記的兩個密度值都偏高，真值約 33/100 與 17/100。**方向不是自利的，但它就長在專門用來量失實宣稱的那條判準上** | **本判準在修好下列三點之前不得宣告達標**：<br>①**分子零≠滿分**：該輪未執行四方複審時一律判 **N/A**，禁記 0（R72／R74 皆為額度中止而零複審，照原算式反而完美達標）。<br>②**分母為 0 時不適用**：`current_round()` 由帳本推得且刻意 fail-open 落後一輪，輪初該輪零新列 ⇒ 開場除以零，此時只能記 N/A，**不得**讀成任一極端。<br>③**門檻改寫成絕對值**：真實分母下 `1÷36×100＝2.8`、`2÷36×100＝5.6`，原本的 3/100 實際語意是「至多 1 筆」；寫成比率會讓讀者以為一兩筆還在容許範圍。連續三輪**≤1 筆且無任何一筆 P1**才算達標 | SA |
| **M3** | 新增判準的**第三方**注入通過率＝100%（作者自證不計分） | 複審者對該輪每一支新鎖各做一次注入，逐筆記紅綠 | 前手 5 支自證 5/5；**我第三方複跑 3 支**（鐵律三三向、PG 前置四情境、ARCH-01 標記碰撞），其中 ARCH-01 那支**當場抓到修法自己把樹弄紅** | **連續兩輪 100%，且抽樣面含既有鎖庫隨機 20 支**（本輪未做既有鎖抽樣＝目前最大量測缺口） | SD |
| **M4** | 「宣稱射程 ≡ 實作射程」零落差 | 對每一道鎖的散文宣稱逐句取其**可執行判準**重跑（本輪的 `TestR75IronLawMechanismSubstance` 是這條的第一個機械化實例） | 本輪抓到 4 筆散文與實作不符（ARCH-02 三欄 vs 二欄、ARCH-03 無新鮮度、QA-01 假話、SA-03 筆數） | **一輪內 0 筆**，且該檢查本身有注入證明 | SD |
| **M5** | 雙向注入攔截率：mac→Win 與 Win→mac 兩個方向都 ≥80%，且差距 ≤10pp | 每輪跑固定形制 N=10 注入矩陣（每輪強制抽換 ≥2 題防過擬合），逐題記「哪一道閘攔下」 | 🔴 **本輪 N-03 以逐題可重跑的矩陣重量，結論與此格原值不同**（原值用「甲／乙」指稱兩組，而該標籤在本表內沒有定義，讀者無從判斷哪個方向是哪個 ⇒ 一併改成寫明方向）：**mac→Win 0/10（0%）**、**Win→mac 5/12（41%，扣掉一筆順帶命中後 4/12＝33%）**、差距 **33〜41pp**。且 Win→mac 命中的全在檔名／路徑／編碼層，**程式碼語意層仍是 0**。⚠️ mac→Win 那 0/10 **不需要 mac 真機才補得起來**——它是**靜態掃描面**的缺口（`os.getlogin`／`import pwd`／`os.fork`／`SIGKILL`／`os.symlink`／`/tmp` 硬編這類對面平台專屬 API 整類無判準），在 Windows 上就補得了 | 兩方向皆 ≥80% 且差距 ≤10pp，**連續三輪不倒退** | QA |
| **M6**（Fixer 補） | **從未被執行過的測試歸零**：每一支測試都至少在某條**會被人看到結論**的軌上真的跑過一次 | 對每個 skip 群組實跑「解除條件」並記 rc；`Skipped_Test_Inventory` §4.7.1 的三基線就是本輪的形態 | 本輪一次補測就曝出 **4 支從未被執行過的紅**（3 支存在數輪、1 支結構上不可能綠） | 盤點文件內「零覆蓋」欄為 0，且每一格都有當輪實跑 rc 佐證 | Fixer |

## 為什麼是這六條，而不是「缺陷數下降」

- **M1** 量的是「護欄層有沒有停止自我增殖」。Architect 的核心立場逐字是：成熟不是「缺陷變少」，
  是「護欄層停止自我增殖，而缺陷從結構性降級為單點」。UEP 連 9 輪不動卻仍掛在「目標」欄，
  就是護欄層在原地繞圈的證據。
- **M2／M4** 量的是「這一輪講了幾句與磁碟不符的話」。SA 的判準：那條曲線目前**沒有在降**，
  因為每輪都在造新的鎖、新的鎖又帶來新的散文宣稱。
- **M3** 是唯一能防「加一道沒有鑑別力的鎖來刷分」的設計：**作者自證不計分**。本輪 §R76-FIX-2
  就是這條的價值證明——前手自證過的修法，第三方一跑就紅。
- **M5** 直接對應掌舵者第 3 點（mac 開發時 Windows 不落差，反之亦然），而且它量的是缺陷
  穿過幾道閘，加鎖不會讓它上升。
- **M6** 對應掌舵者第 5 點（挖深、清技術債）。本輪的實證：**skip 是技術債裡最便宜藏身處**，
  因為它在摘要裡長得像「乾淨」。

## 現況總判：**未成熟**（六條裡 0 條達標）

| 判準 | 達標？ | 距離 |
|---|---|---|
| M1 | ❌ | 需要一次 ADR 級拍板（不需 code） |
| M2 | ❌ | 真實分母下 17〜33/100 vs「至多 1 筆」，仍差一個數量級；且判準本身的三個結構缺陷（分子零≠滿分／分母為 0 不適用／門檻改絕對值）在本輪才被寫進上表 |
| M3 | ❌ | 第三方抽樣面尚未含既有鎖庫 |
| M4 | ❌ | 本輪 4 筆 |
| M5 | ❌ | mac→Win **0%**（整類無判準）、Win→mac 33〜41%、程式碼語意層 0 |
| M6 | ❌ | 本輪剛把「零覆蓋」從 192 壓到個位數，但 4 支從未執行過的紅才剛浮出 |

🔴 **這六條刻意沒有一條是「缺陷數 ≤ N」**。本 repo 已有判例證明那種門檻會被「少寫幾列帳本」
滿足；上面六條全部是**比率或結構性狀態**，把列藏起來只會讓分母變小而分子不變，數字反而更差。
