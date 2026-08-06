# R78 交棒任務書（跨平台相容性輪）

> **平台**：Windows 11 Pro build 26200 真機。工具側 PowerShell 引擎＝**pwsh 7.6.4（Core）**；
> `powershell.exe -NoProfile` 才是 5.1（Desktop），凡 PS 5.1 語意的標的一律顯式外呼。
> **本檔用途**：讓 R79 不必採信任何宣稱就能接手。
> **🔴 本輪新立體例（已上機械物 `TestR78HandoffClaimsCarryLiveCommands`）**：
> 交棒書凡述及「尚未做／還缺／已推送」這類**狀態**，一律附**現查指令**，不寫快照結論。
> R77 交棒書有兩筆因此在寫下的當天就成為假話（tag 其實已推、nightly stage 其實已補）。

---

## 0. 🔴 R79 開場必讀

1. **本輪的修復沒有再經第三方複審。** 四方複審查的是 R77；針對那 30 筆 finding 所做的
   五個修復包，是**作者自證**。依本 repo 自己的成熟度判準 M3「作者自證不計分」
   ⇒ **R79 請把本輪每一句「已修畢」都當成待複驗**。這與 R77 交棒書的同一句話同義，
   差別是：本輪至少把「複審 R77」這一層補上了，而 R77 那一層是完全空白。
2. 🔴 **帳本未結列已抵達 warn 線**（收輪實測；現查 `python tools/check_defect_log_crossref.py --unresolved-count`）。
   工具自己的話：「請在本輪就結掉／指派掉幾筆，不要等撞線——撞線時能做的事跟現在一樣多，只是選擇更少」。
   **R79 開場第一件事就是這個**，而且要知道兩件事：
   ①**歸檔對這條線完全無效**（未結列結構上不可搬）；
   ②清債包的結論是**真槓桿在 `DEF-101-676`（26KB 級結構改動），不是多結幾筆**。
3. **有 8 筆 backlog 被續改派到 R79**（`DEF-101-790`／`795`／`796`／`797`／`798`／`802`／`803`／`810`）。
   它們原由 R76 改派 R77、R77 未做完、R78 未處理。**請逐筆判定「真承接」或「明文關閉並附理由」，
   不要再順延一輪**——連續三輪順延就是這批列的實況。

---

## 1. 收輪時的實測狀態

> 🔴 **R79 請自己重跑，不要採信本表。** 本 repo 已有判例：同一條指令、同一台機器、
> 相隔幾分鐘 rc 由 0 翻 1（成因見 `DEF-101-886`）。

共用前綴：

```powershell
$r='D:\CursorProject\AISDCL_Agent'; $p="$r\.venv\Scripts\python.exe"
$env:PYTHONUTF8='1'; $env:PYTHONDONTWRITEBYTECODE='1'
```

🔴 **讀 rc 不接管線**（pwsh 7.x 會保留前一個值＝真紅讀成綠）。現在有 PreToolUse 守衛擋這個形態，
而本輪它的鑑別力被大幅修正過——見 `DEF-101-879`。

| 閘門 | 指令 |
|------|------|
| 根層 unittest | `& $p "$r\tools\run_root_unittests.py"` |
| LOC budget | `& $p "$r\AutoClaude\tools\check_loc_budget.py"`（🔴 **住 AutoClaude 側**，根層無此檔——收尾者本輪誤用根層路徑拿到 rc=2） |
| 帳本一致性 | `& $p "$r\tools\check_defect_log_crossref.py"` |
| 帳本保全 | `& $p "$r\tools\archive_defect_log.py" --check` |
| ONBOARDING 基線／指紋 | `& $p "$r\tools\sync_onboarding_baselines.py" --check` ／ `--check-snapshot` |
| 腳本對等 | `& $p "$r\tools\check_script_parity.py"` |
| 薄殼守門 | `& $p "$r\tools\check_wrapper_thinness.py"` |
| pytest 基線站點 | `& $p "$r\tools\check_pytest_baseline_sites.py"` |
| GHA 版本 | `& $p "$r\tools\check_gha_action_versions.py"` |
| NTFS 路徑 | `& $p "$r\tools\check_ntfs_paths.py"` |
| 排程漂移 | `& $p "$r\tools\check_scheduled_task_drift.py"`（本輪已補**執行履歷**判準） |
| Windows smoke | `& powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$r\tools\windows_smoke_local.ps1"` |
| context 水位 | `& $p "$r\tools\session_resume_planner.py" --check` |

---

## 2. 掌舵者六題與三個系統問題

### Q1｜全面掃描 Mac × Win11 相容性

本輪的主軸不是再掃一次，而是**補跑 R77 積欠的四方複審**——結果證明那是對的：
**30 筆 finding（9 blocking）**，逐筆見 `docs/06_quality/CrossPlatform_R78_Review.md`。

🔴 **一句話結論：R77 最重要的兩個交付物，都犯了 R77 自己診斷出來並寫進根 `CLAUDE.md` 的那個病**
（「鎖存在但沒有鑑別力」）。三方各自獨立打中同一支 hook。

🔴 **誠實劃界：mac 真機零覆蓋**（與 R77 同）。mac 半邊全是讀碼與 POSIX 語意推論。

### Q2｜架構檢視與「拿掉不合理機制」

本輪的減法不在「刪掉什麼」，而在**把三個假的東西變成真的**：

| 標的 | 處置 |
|---|---|
| `_FROZEN_GUARD_FILE_COUNT`（全庫零定義、十餘處引用，其中 LOC 工具拿它當整層豁免依據） | 引用逐處改述正確語意；**判準射程由「反引號路徑」擴到「反引號 Python 識別字」**——那正是逃逸的縫 |
| `--print-guard-lines`（棘輪紅燈訊息教人跑，但不存在） | 實作，並附「文字教人跑的旗標必須真的有人分派」的雙向判準 |
| 行數棘輪重釘零成本 | 新增 append-only 稽核列（不寫理由即紅、淨額結構上不可能缺席） |
| M1~M6 寄生在輪次專屬掃描文件 | 搬進輪次中立 SSOT `docs/06_quality/CrossPlatform_Maturity_Criteria.md` ＋ 新鮮度鎖 |

### Q3｜雙向落差（mac 開發 ↔ Windows 開發）

**攔截率現值一律現跑**（本檔依體例不登載數字）：

```powershell
& $p -m unittest tools.tests.test_platform_neutral_paths.TestXplatInjectionMatrix
```

（`setUpClass` 末行印 `[Xplat injection matrix] Win2mac=<hit>/<total> mac2Win=<hit>/<total>`）

🔴 **本輪新增一個此前未登記的隱形面，而且它是這一題最深的品種**：

> **git 的行尾正規化只作用於 index、從不回寫工作樹；而 `git status` 比對時兩側套用同一份
> 正規化 ⇒ 工作樹與政策不符時，結構上不可見。**

實測並修復 144 支 `.sh`（工作樹 CRLF）與 6 支 `.ps1`（工作樹 LF）。連帶推論：
**雲端 fresh clone 全綠不蘊含本機開發環境為綠**，因為 `actions/checkout` 一律重新 smudge。
用 act 那條線自己的話說：**唯一在檢查 `.ps1` 行尾的 CI 判準，只跑在它唯一不可能失敗的那個狀態上。**

### Q4｜Windows 常犯低級錯誤的根因

R77 的 n=36 歸因（LOCKBLIND 44%／CARRIER 19%）**本輪未重算**——因為量測器本身被查出有盲區
（`DEF-101-880`）。修好之後**尚未以新尺重跑**，所以：
🔴 **R79 在重跑之前，不得引用 R77 那組百分比。** 重跑指令：

```powershell
& $p "$r\tools\probe\audit_session.py" --latest 5
```

本輪對這一題的實質貢獻是**把兩個觀測者修對**：攔截器（hook）補了別名、跨語句、位置先後、
字串遮蔽；量測器（probe）補了逐工具計數與 per-session 崩塌判準。修之前它們
**判定分歧 3 例**，修之後 0 例。

### Q5｜挖深與技術債

- 未結列現查：`& $p "$r\tools\check_defect_log_crossref.py" --unresolved-count`
- 本輪結案 3 筆**皆附實測證明**（`DEF-101-297`／`278`／`435`，最老的立帳於 R33）
- 逐筆判定與證據見 `docs/06_quality/CrossPlatform_R78_Debt_Audit.md`
- 🔴 **帳本容量的真槓桿是 `DEF-101-676`（26KB 級結構改動），不是多結幾筆**——這一句是清債包的結論，本輪未動

### Q6｜成熟度判準

**SSOT ＝ `docs/06_quality/CrossPlatform_Maturity_Criteria.md`**（本輪新建，輪次中立）。

核心設計原則一句話：**不能量「有幾道閘」，要量「缺陷穿過幾道閘」**——前者可以靠新增鎖無限刷分，
而新增鎖正是本 repo 目前缺陷的最大單一來源。

六條的達標判定現況見該檔 §「現況總判」。三個刻意的設計：
① **未做複審一律判 N/A、禁記 0**（否則不做事就滿分）；
② **M3 作者自證不計分**（唯一能防「加一道沒鑑別力的鎖來刷分」）；
③ **沒有任何一條是「缺陷數 ≤ N」**（那種門檻會被「少寫幾列帳本」滿足）。

### S1｜`AutoClaude_Nightly` 還要跑多久、能不能加速

**不得退場。** 觀察期四軌的終點由 **span**（最後 30 筆的首末日期距離）綁住而非筆數——
**筆數早就夠了，卡的是天數**。算式與最早收斂日見 `DEF-101-887` 與 nightly 診斷回報；
現值一律現查 nightly log 的 `END observation progress` 行。

🔴 **唯一合法槓桿是命中率**（別再漏跑）。每漏一晚，兩個日期各往後推**至少**一天。
❌ 不得放寬 `WINDOW_SPAN_MAX_FACTOR`／`STALENESS_MAX_DAYS`。

### S2｜`AutoClaude_WindowsSmoke` 與觸發時刻

**不得退場**（理由沿用 R77：E1 雲端主通道活性遠未達退場門檻）。

🔴 **本輪解開了「掌舵者說改成 23:30、實際卻是 21:30」之謎**：
`tools/install_windows_nightly.ps1` 的 `-SmokeAt` **預設值就是 21:30**，
任何一次不帶參數重跑安裝器都會 Unregister→Register 把 23:30 蓋掉，
而舊版偵測器**看不到觸發時刻** ⇒ 整個改動靜默失效。

**收尾者的裁決＝維持 21:30 並釘進偵測器**（21:30 一樣在開機時段，且滿足既有的
「smoke 早於 nightly」機械鎖；改回 23:30 需額外旗標繞過該不變量並提權重跑安裝器）。
**這一格若掌舵者堅持 23:30，是需要他拍板的**，改法寫在 `scheduled_task_expectations.json` 的
`_why_trigger_time`。

### S3｜skipped 徹底解決

🔴 **本輪的重大發現**：PG 全開環境下暴露的 failed **不是 R77 說的 4 支**。
其中最嚴重的一組：

> 線上 `autoclaude` DB 的 `alembic_version` 標著 head，但 migration 0010 的 `backfill_legacy_fk()`
> **根本不存在**。用乾淨 DB 做對照實驗證明 migration 本身沒問題——是那個 DB 當初沒跑完。
> **`alembic_version = head` 不保證整條鏈真的跑過，而全 repo 唯一能偵測這件事的，
> 就是那 3 支被 skip 藏起來的測試。**

已修（DB ＋ 5 支缺 env 隔離的測試）。修後 PG 全開的實測數字見 nightly 診斷回報。
**偵測缺口未補**（沒有任何機制在守「head ≠ 整條鏈跑過」），已併入 `DEF-101-863` 的散文。

四組基線現值：`& $p "$r\tools\sync_onboarding_baselines.py" --check`（表② 那四欄）。

---

## 3. 本輪最重要的一般化規則

### 3-1 🔴 剛落地的新鎖，第一件事就抓到寫它的人——**三次**

1. wiring context 守衛 → 當天才落地的 PostToolUse 註冊面鎖當場紅（它比預期更嚴，是**雙向**的）
2. 重釘棘輪 → 補稽核列那幾行**自己改變了被量測的行數**，第一次的數字當場過期（自我指涉）
3. 在重釘理由裡寫死量測數字 → 而那個檔自己的規則就是禁止寫死數字

**這不是負面紀錄。** 它是「有觀測者 vs 沒觀測者」那個量化差距最直接的實證：
機械物不是給別人用的，寫它的人同樣在違規率裡。

### 3-2 🔴 修好一個紅，會露出下一個紅——而遮蔽的方向永遠是「看起來變乾淨」

act 那條線：`.sh` 行尾轉綠之後，**立刻**露出 `.ps1` 方向的同型缺陷（原本被前一個紅擋住）。
`root-infra` 從 R77 卡死的第 4 步一路推進到第 11 步，**多驗了 7 步**——
而那 7 步裡有 2 步是紅的、此前從未被任何人看見。

⇒ **「跑到第一個綠就停」等於自願只看見一個紅。** 要跑到底。

### 3-3 🔴 一條 repo 級通則的射程可能是錯的

本 repo 有一條通則「Python 寫檔一律 `newline="\n"`」——**對 `.sh` 正確，
對 `.ps1` 正好是製造缺陷的指令**（政策要求 `.ps1` 工作樹為 CRLF）。
通則寫下時只想著一種檔案，而它被當成全域規則用了很多輪。

### 3-4 🔴 多 agent 共用一棵工作樹，會讓閘門的 rc 成為「別人鍵盤的函數」

實測：同一指令相隔數分鐘一紅一綠。連帶使 `MIN_TESTS` 重釘紀律要求的
「量測窗口前後工作樹指紋相同」在此作業型態下**結構上不成立**（`DEF-101-886`）。
本輪的處置是**收輪閘門一律在所有 agent 停工後的窗口內取得**——這是紀律，不是機械物。

### 3-5 🔴 排程在人工作業進行中觸發，量到的是「從未存在於版本史上」的樹

實測：nightly log 記某檔行數，而那個數字在**任何一個 commit 上都不存在**。
那種紅**既不是缺陷也不是綠，是無效樣本**，而現有取證鏈無處可表達這件事（`DEF-101-887`）。
本輪已讓 nightly 起跑印樹狀態指紋；**四個 collector 的寫入端仍不記**，所以觀察期統計
目前仍無法自動排除無效樣本。

---

## 4. 交給 R79 的事（依優先序）

1. **複驗本輪的五個修復包**（見 §0-1）。特別是 `DEF-101-879`／`880` 兩支守衛——
   它們是「觀測者」，觀測者自己錯了會污染所有下游結論。
2. **以修好的量測器重跑 Q4 的歸因**（見 §2-Q4），在那之前不得引用 R77 的百分比。
3. **逐筆處理續改派到 R79 的 8 筆 backlog**（見 §0-3）。
4. **四個 collector 補樹狀態欄位**，讓觀察期統計能自動排除無效樣本（`DEF-101-887`）。
5. **`.ps1` 行尾的止血機制**：本輪只證偽了 BOM hook、實測定點 Edit 無害，**寫入者未溯源**（`DEF-101-888`）。
6. **32 筆 grandfathered 幽靈符號名**（C 包誠實登記，附 stale 自檢）。
7. **mac 真機輪**：Q1 的 mac 半邊、Q3 的執行期那一半，都只有 mac 真機補得了。

---

## 5. 禁止事項（R79 動工前先讀）

1. ❌ 不准 `--no-verify`、不准 `AUTOCLAUDE_SKIP_HOOKS=1`、不准跳過或註解掉失敗測試。
2. ❌ 不准為了讓數字好看而調高任何門檻／棘輪／體積上限。棘輪的合法出口是
   「同一次變更內刪等量以上的行」，**重釘必須在 `_GUARD_LINES_REPIN_LOG` 補一列並寫出淨額與理由**（不補即紅）。
3. ❌ 不准把「尚未查核」寫成「已查核」。**本輪具體：五個修復包未經第三方複審、
   Q4 未以新尺重算、mac 側零覆蓋、雲端本輪 push 前未查。**
4. ❌ **Windows 上禁用 Bash 工具**；禁裸 `cd`；**讀 rc 不接管線**（守衛的鑑別力本輪剛大幅修正過）。
5. ❌ 不准用 `--allow-pg-extras` 繞過 `sync_onboarding_baselines.py --write` 的拒跑。
6. ❌ 缺陷帳本列禁半形直線符號、列 ≤700 bytes、詳情進具名證據檔。
   **新建 `docs/06_quality/CrossPlatform_*.md` 必須同時登記進 `_GOVERNANCE_DOCS`**（本輪踩過一次）。
7. ❌ **不要在多 agent 並行期間取閘門讀數**（見 §3-4）。

---

## 6. R78 自身的失誤紀錄（本節是本檔的誠信擔保）

1. **§3-1 那三次**（被自己剛落地的鎖抓到），細節見該節。
2. **我在帳本列裡引用了一份當時還不存在的證據檔**（`CrossPlatform_R78_Review.md`）——
   正是本輪在治的「宣稱一個不存在的東西」。發現後補建該檔並登記進治理面。
3. **我把 `check_loc_budget.py` 的路徑寫成根層**（實際住 AutoClaude 側），拿到 rc=2 才發現。
   已寫進 §1 表格以免下一輪重蹈。
4. **我一開始把「昨晚兩支排程都失敗」判讀成「現在有東西壞了」**——實測後才發現那是
   在 commit 前 1.5~2.5 小時量到的半成品。**現象真、理由錯**，當場向下游 agent 發出更正。
5. **我對 nightly 的 root_unittests 給了錯誤的假設**（以為是 SA-03 的探針互踩）。
   診斷 agent 用 log 全檔 grep 零命中推翻了它，並找出真因。**我採納了它的推翻。**
6. **改派 backlog 時第一次改錯位置**：`_handover_rounds` 只認「承接輪次」後**緊接**的數字，
   我把舊輪號留在前面，改了等於沒改。第二次才對。
7. **補 compat-CI 的 `paths:` 時只補了一半。** 我加了 `tools/act/**` 就以為那一項做完了，
   漏掉同輪新增的 `.actrc` 與 `tools/session_resume_planner.py`——是回填包跑 ci-gate 時
   被 `test_ci_paths_cover_root_consumers.py` 逐字點名出來的。**這是本輪第四次「機械物抓到收尾者」**，
   也再次驗證 R77 交棒書禁令第 7 條（新增 `tools/` 子目錄要補兩支 compat-CI 的 paths）的必要性——
   我讀過那條禁令，仍然只做了一半。
8. 🔴 **我對執行中的 agent 食言。** 我明文寫給回填包「我在你回報前不會再動樹」，然後在它跑的期間
   為了收斂棘輪改了四個檔（`CLAUDE.md` ＋ 兩支測試 ＋ 兩支 workflow）。
   `measure_slow_on_stable_tree()` 的指紋夾就是為了擋這件事而存在的。
   已即時向它自陳並請它重跑。**記在這裡是因為它同時是 `DEF-101-886` 的又一個實例**：
   共用工作樹的序列化紀律**沒有機械物**，靠的是人記得——而我在寫下那條紀律的同一輪就違反了它。

---

## 7. 本檔取證邊界

| 內容 | 強度 |
|---|---|
| §1 各閘門 | **指令**（本檔依新體例不登載 rc 快照——那是下一輪必須自己跑出來的東西） |
| §2 Q1 的 30 findings／9 blocking | **當回合真跑**（四方複審 16 agents，逐筆見 Review 檔） |
| §2 Q3 的 144 支 `.sh` 與 6 支 `.ps1` | **當回合真跑**（renormalize 前後逐步輸出、位元組級抽驗） |
| §2 Q4 的兩支守衛修復 | **當回合真跑**（9 道注入證明、修後端到端全通） |
| §2 S1 的 span 算式 | **引用**（nightly 診斷 agent 的量測，收尾者未重算） |
| §2 S3 的 DB 對照實驗 | **引用**（nightly 診斷 agent 的量測） |
| §3-1 三次 | 收尾者親身經歷 |
| §6 六筆 | 收尾者親身經歷 |

> 🔴 **本檔寫於 commit 之前**，且交棒書自己也在閘門掃描面內。
> 收尾者在 commit 前會對「含本檔」的樹重跑閘門——若 R79 發現本檔造成任何紅，
> 那代表那次重跑沒做或做得不夠，請直接記在下一輪的失誤紀錄裡。
