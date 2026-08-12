# AutoSDD R85 歷史文件歸檔盤點與提案（P9）

> 🔴 **本檔是否需要登記進治理文件登記面？** —— **機械上不需要，但這是一個「看得見的決定」，須由收尾窗口確認。**
>
> - 登記面 SSOT＝`tools/lib/governance_docs.py` 的 `_GOVERNANCE_DOCS`；其**發現面** glob 是
>   `_GOVERNANCE_DOC_GLOB = "CrossPlatform_*.md"`、目錄 `_GOVERNANCE_DOC_DIR = docs/06_quality`。
>   本檔名為 `AutoSDD_R85_Archive_Proposal.md`，**不符合該慣例** ⇒ `unregistered_governance_docs()`
>   不會對它轉紅（當回合實測：`check_defect_log_crossref.py` rc=0，且輸出逐字為「具名治理文件 **31 份**皆已登記」，
>   不含本檔）。
> - 🔴 **但 `governance_docs.py:105~108` 逐字記載過一個判例**：`CrossPlatform_R82_Ledger_Closure.md`
>   一度「刻意取名 `AutoSDD_R82_*` 以避開本清單」，該註解把它定性為
>   「**沒有登記權的人用改名讓『不受管』變成看得見的決定**」，並要求後續補登記。本檔的檔名形態與那次相同，
>   故**不主張自己免管**：本檔承擔的義務較弱（它不寫出「某 DEF-ID 現居某檔」的居所宣稱，只寫「某檔有誰在讀」的
>   盤點結論），是否納管由持有 `tools/lib/` 的收尾窗口裁決。
> - **體積上限（若納管）**：fail `_LEDGER_FAIL_BYTES = 256 * 1024 = 262,144` bytes；
>   warn `_LEDGER_WARN_BYTES = 240 * 1024 = 245,760` bytes（`tools/check_defect_log_crossref.py:1158~1162`；
>   來源是 Read 工具單次讀取上限，非 git/markdown 限制）。本檔遠低於該線。

---

## 1. 目的與射程（明文劃界）

**目的**：回應掌舵者「歷史文件數量太多，請進行 Archive」。

**射程宣告 —— 本輪只做盤點與提案，一個檔都沒有被搬動、刪除或改寫。**

為何不當場搬：

1. **並行輪次不得做淨減法。** 根 `CLAUDE.md` 鐵律三下方〈跨檔參照稅〉已判過：合併／刪除鎖檔後，
   全樹十餘支測試會因「git-tracked 但磁碟不存在」的 fail-loud 轉紅，而**那類紅只有 `git rm`／stage 能消除**，
   並行包一律禁止 git 操作 ⇒ 淨減法**只能由收尾單人窗口做**。
2. **本包是唯讀研究包**，工作樹由 3 個並行 agent 共用。R84 曾有一次 `git stash` 清空 16 個修改檔 ＋ 4 個未追蹤檔
   （見鐵律五立案事實）。
3. 因此本檔的產物是**一份可逐字照抄執行的清單**，交給收尾窗口執行。

**盤點母體**：116 支候選檔（`docs/04_planning/` 的 `R*_HANDOFF.md` 與 `AutoSDD_improving_1*.md`；
`docs/06_quality/` 的 `CrossPlatform_*.md` 與 `AutoSDD_Defect_Log_archive_*.md`）。

---

## 2. 既有先例：Archive 不是新發明，SOP 已經存在

| 事實 | 實測值 |
|------|--------|
| `docs/04_planning/Archive/` 已存在 | 103 檔、1,469,597 bytes（含 `AutoSDD_improving_01`～`_102` 共 102 支 ＋ README） |
| `docs/06_quality/Archive/` 已存在 | 99 檔、630,094 bytes（`AutoSDD_ZeroTrust_Audit_*` 98 支 ＋ README） |
| 歸檔 SOP 權威源 | `docs/04_planning/Archive/README.md`（含轉址規則、四方案評比、機械鎖清單） |
| 轉址規則 | `docs/<04_planning\|06_quality>/<檔名>` → 上層找不到時改到 `docs/<同層>/Archive/<同檔名>` |
| 轉址規則的**射程** | `tools/tests/test_ntfs_trailing_space_device_name.py` 的 `_ARCHIVABLE_DOC_RE`：**只**認 `AutoSDD_improving_\d+(_backlog)?\.md` 與 `AutoSDD_ZeroTrust_Audit_\d+\.md` |

🔴 **這條射程是本次盤點最重要的單一事實**：`R*_HANDOFF.md`、`CrossPlatform_*.md`、
`AutoSDD_Defect_Log_archive_*.md` **都不在轉址規則內** ⇒ 把它們搬進 `Archive/` 之後，
所有指向它們的 `.md` 引用會斷鏈，而 `TestRootDocsPathRefsAreCaseExact` 對「上層與 Archive 皆不中」
那一支是**刻意放行**的（避免死連結偵測變噪音）⇒ **斷鏈是靜默的，沒有任何測試會紅**。
這不是「安全」，是「失效不可見」——與本 repo 反覆判過的「假綠與修好表徵相同」同型。

---

## 3. 量測表（當回合實測，`.venv/bin/python` 讀 `stat().st_size`）

### 3.1 家族總計

| 家族 | 檔數 | 總 bytes |
|------|-----:|---------:|
| `docs/04_planning/R*_HANDOFF.md` | 11 | 313,857 |
| `docs/04_planning/AutoSDD_improving_1*.md` | 7 | 192,293 |
| `docs/06_quality/CrossPlatform_*.md` | 31 | 1,627,277 |
| `docs/06_quality/AutoSDD_Defect_Log_archive_*.md` | 67 | 2,154,244 |
| **候選合計** | **116** | **4,287,671** |

（同目錄下另有非候選的活文件：`AutoSDD_Defect_Log.md` 205,003、`AutoSDD_Iteration_Prompt_Template.md` 31,293、
`Skipped_Test_Inventory_R76.md` 62,769、`Scheduled_Jobs_Lifecycle_Review_R75.md` 63,238 等，皆不在本次提案內。）

### 3.2 逐檔（bytes / 行數）

**`R*_HANDOFF.md`**

| 檔 | bytes | 行 | | 檔 | bytes | 行 |
|---|---:|---:|---|---|---:|---:|
| R74 | 14,818 | 198 | | R80 | 22,907 | 321 |
| R75 | 12,942 | 190 | | R81 | 19,256 | 294 |
| R76 | 55,541 | 735 | | R82 | 31,233 | 428 |
| R77 | 22,757 | 338 | | R83 | 53,838 | 514 |
| R78 | 19,395 | 299 | | R84 | 24,542 | 282 |
| R79 | 36,628 | 465 | | | | |

**`AutoSDD_improving_1*.md`**

| 檔 | bytes | 行 | | 檔 | bytes | 行 |
|---|---:|---:|---|---|---:|---:|
| 103 | 46,348 | 489 | | 107 | 21,981 | 181 |
| 104 | 37,620 | 213 | | 108 | 11,938 | 126 |
| 105 | 37,095 | 166 | | 109 | 7,164 | 100 |
| 106 | 30,147 | 182 | | | | |

**`CrossPlatform_*.md`（31 支，前十大）**

| 檔 | bytes | 行 |
|---|---:|---:|
| R60_Fix_Evidence | 200,024 | 1,384 |
| R81_Scan_Findings | 172,697 | 1,631 |
| R76_Scan_Findings | 105,749 | 768 |
| R81_Quota_Review | 104,403 | 1,093 |
| R79_Debt_Audit | 97,393 | 1,119 |
| R81_Ledger_Triage | 91,349 | 913 |
| R68_Scan_Findings | 87,727 | 117 |
| Scan_Dimensions | 69,667 | 464 |
| R60_Fix_Evidence_r3 | 68,065 | 942 |
| R82_Ledger_Closure | 67,057 | 689 |

**`AutoSDD_Defect_Log_archive_*.md`（67 支，前五大）**：`_04` 215,094／`_02` 183,179／`_01` 175,469／
`_03` 109,563／`_30` 89,010；`_INDEX` 70,495。

---

## 4. 三桶分類

### 桶總計

| 桶 | 檔數 | bytes | 說明 |
|---|---:|---:|---|
| **① 可歸檔** | 12 | 332,728 | 無活消費端；搬了不會有任何測試轉紅 |
| **② 須保留** | 76 | 2,498,796 | 有活消費端或明文政策禁止歸檔 |
| **③ 須先改判準** | 28 | 1,456,147 | 有具名鎖在讀，改掉指定常數後才可搬 |
| **可回收合計（①＋③）** | **40** | **1,788,875** | 約 1.71 MiB |

---

### 桶① 可歸檔（12 支 / 332,728 bytes）

| 檔 | bytes | 消費端實查 | 備註 |
|---|---:|---|---|
| `R74_HANDOFF.md` | 14,818 | **全庫零引用**（`git grep -F -- 'R74_HANDOFF.md' -- tools/ .github/ AutoClaude/ AISDLC_SDD/` rc=1） | 最乾淨的一支 |
| `R77_HANDOFF.md` | 22,757 | **全庫零引用** | 同上 |
| `R79_HANDOFF.md` | 36,628 | 僅 `tools/session_resume_planner.py:64` 的**註解**指路 | 註解斷鏈，無鎖 |
| `R80_HANDOFF.md` | 22,907 | 僅 `test_negative_existence_claims_r82.py:352` 的**合成字面**（同組含不存在的 `R9_HANDOFF.md`） | 合成語料不讀磁碟 |
| `R81_HANDOFF.md` | 19,256 | 同上（`:351`）＋ `:10` 註解 | 同上 |
| `R82_HANDOFF.md` | 31,233 | 僅 2 處 `.md` 交叉引用 | — |
| `AutoSDD_improving_103.md` | 46,348 | `test_ntfs_trailing_space_device_name.py:722,731` 屬 `test_resolver_has_discriminating_power` 的**合成 tracked set**（該測試 docstring 逐字寫「合成 index，不依賴現況」） | 轉址規則已覆蓋此檔名形態 |
| `AutoSDD_improving_104.md` | 37,620 | 僅 `tools/lib/quota_escalation.py:13` 與 `test_adr_xplat001_c1c2_lock.py:1205` 的**註解** | 同上 |
| `AutoSDD_improving_105.md` | 37,095 | 僅 `test_doc_loc_baseline_freshness_r60.py:4162` 的**註解** | 同上 |
| `AutoSDD_improving_106.md` | 30,147 | 僅 `.md` 引用 9 處 | 同上 |
| `AutoSDD_improving_107.md` | 21,981 | 僅 `.md` 引用 7 處 | 同上 |
| `AutoSDD_improving_108.md` | 11,938 | 僅 `.md` 引用 1 處 | 同上 |

🔴 **`improving_103`～`108` 是唯一「歸檔已被預先接線」的一族**：`_ARCHIVABLE_DOC_RE` 覆蓋其檔名形態，
搬檔後 `.md` 引用經轉址規則仍解析得到 ⇒ 零斷鏈。**它們也是唯一有順序約束的一族**（見下）。

🔴 **`R*_HANDOFF` 搬檔的已知副作用（不會紅，但要知道）**：轉址規則射程外 ⇒ 上表那些
`.md` 交叉引用與 `.py` 註解會斷鏈且**靜默**。

---

### 桶② 須保留（76 支 / 2,498,796 bytes）—— 逐筆點名誰在讀

| 檔 | bytes | 誰在讀（file:line） | 歸檔後會怎樣 |
|---|---:|---|---|
| `AutoSDD_Defect_Log_archive_*.md`（**67 支，2,154,244**） | 2,154,244 | ① **明文政策**：`docs/06_quality/Archive/README.md` 逐字「它的歷史分冊 `AutoSDD_Defect_Log_archive_*.md` **也不住這裡**……一律留在 `docs/06_quality/` 上層」；② **機械鎖直接斷言它們不得被歸檔**：`tools/tests/test_ntfs_trailing_space_device_name.py:739~742` `assertIsNone(archive_fallback("docs/06_quality/AutoSDD_Defect_Log_archive_02.md"), "轉址規則射程外溢到帳本家族 —— 那個家族不歸檔進 Archive/")`；③ `tools/check_defect_log_crossref.py:1055,1299` 與 `tools/archive_defect_log.py:690` 以 **pathlib glob**（不跨 `/`）在上層列舉；④ `AISDLC_SDD/scripts/tests/test_ci_paths_cover_root_consumers.py:1455~1466` 的 `"defect-log-archive"` 條目：pathspec `docs/06_quality/AutoSDD_Defect_Log_archive_*.md`、**最少 2 筆**、具名見證 `_02.md` | **這一桶不要動。** 它是最大的一塊（2.15 MB），但有一支測試專門斷言「它不歸檔」——歸檔它等於把那支鎖倒過來改，而政策是它的上游 |
| `R83_HANDOFF.md` | 53,838 | `test_adr_xplat001_c1c2_lock.py::handoff_guard_total_problems`，`_HANDOFF_RECONCILE_SINCE = 83`；掃描面 `_GUARD_TOTAL_DOC_GLOBS` 含 `docs/04_planning/R*_HANDOFF.md`（**pathlib glob，不跨 `/`**） | 搬走＝該輪三元組對帳失去輸入 |
| `R84_HANDOFF.md` | 24,542 | 同上（R84 命中 `(79083, 81738, 2655)`）；另 `test_doc_loc_baseline_freshness_r60.py:6898` `test_the_newest_handoff_carries_its_own_lower_bound` 要求**最新一份**自己收得到 stale 宣稱 | 搬走＝最新一份不在掃描面，該測試取 `max()` 會落到 R82 |
| `AutoSDD_improving_109.md` | 7,164 | ① 它是**當前輪 R85 的 `guard-total` 標記唯一站點**（`:99` `<!-- guard-total:R85 -->`），而 `_GUARD_TOTAL_DOC_MIN_SITES = 2` 要求本輪標記在計畫書與掃描發現文件**兩邊**都有；② `test_check_defect_log_crossref.py:1223` `test_real_ledger_current_round_is_two_digit_and_not_the_planning_dir_max` 以**非遞迴** glob 取上層 improving 並 `assertTrue(improving, …)`；③ 根 `CLAUDE.md` 三軌表取號規則＝「`docs/04_planning/` 現存最大號＋1」 | 上層清空＝②當場紅、③下一輪不知從幾號開始 |
| `CrossPlatform_Scan_Dimensions.md` | 69,667 | **4 處 CI `paths:`**（`windows-compat-ci.yml:472,752`、`macos-compat-ci.yml:348,626`）＋ `tools/check_defect_log_crossref.py:427,577,587`（規格權威）＋ `tools/archive_defect_log.py:50,61,403` | CI 觸發面與判準權威同時失準 |
| `CrossPlatform_Maturity_Criteria.md` | 18,085 | **4 處 CI `paths:`**（`windows-compat-ci.yml:241,554`、`macos-compat-ci.yml:107,428`）＋ `tools/tests/test_maturity_criteria_r79.py:54` `_SSOT = … / "CrossPlatform_Maturity_Criteria.md"`＋ `test_doc_loc_baseline_freshness_r60.py:3802,4011,4156,6576` | M1~M6 判準 SSOT，直接讀檔 |
| `CrossPlatform_R85_Ledger_Closure.md` | 56,205 | `tools/lib/defect_ledger_index.py:558,605,677`（本輪 15 列瘦身原文的居所）＋ `governance_docs.py:143` | 本輪活文件 |
| `CrossPlatform_R85_Scan_Findings.md` | 39,653 | `governance_docs.py:148`＋`test_adr_xplat001_c1c2_lock.py:1197`；且它是 `guard-total:R85` 的第二個必要站點（`_GUARD_TOTAL_DOC_GLOBS` 含 `docs/06_quality/CrossPlatform_R*_Scan_Findings.md`） | 本輪活文件 |
| `CrossPlatform_R84_Scan_Findings.md` | 17,131 | `governance_docs.py:136`＋`test_adr_xplat001_c1c2_lock.py:1165,1184`（具名居所字串） | 上一輪居所，帳本列仍指向它 |
| `CrossPlatform_R83_Scan_Findings.md` | 58,267 | `governance_docs.py:128`＋`test_adr_xplat001_c1c2_lock.py:1148`；帶 `guard-total:R83` 稽核痕跡 | 同上 |

---

### 桶③ 須先改判準才能歸檔（28 支 / 1,456,147 bytes）

#### 3-A `R*_HANDOFF.md` × 3（87,878 bytes）

| 檔 | bytes | 要先改的鎖（檔＋符號） | 改什麼 |
|---|---:|---|---|
| `R75_HANDOFF.md` | 12,942 | `tools/tests/test_doc_loc_baseline_freshness_r60.py:6813` `_HANDOFF_CLAIMLESS_BASELINE` | 從該 `frozenset` 移除 `"docs/04_planning/R75_HANDOFF.md"` |
| `R76_HANDOFF.md` | 55,541 | 同上 | 移除 `"docs/04_planning/R76_HANDOFF.md"` |
| `R78_HANDOFF.md` | 19,395 | 同上 | 移除 `"docs/04_planning/R78_HANDOFF.md"` |

**歸檔這三支會讓哪支測試紅**：`test_doc_loc_baseline_freshness_r60.py:6891~6894`——
`ghosts = sorted(_HANDOFF_CLAIMLESS_BASELINE - scanned)`，訊息逐字
「`_HANDOFF_CLAIMLESS_BASELINE` 登記了掃描面上不存在的檔：{ghosts}」。
掃描面是 `_HANDOFF_GLOB = "docs/04_planning/*HANDOFF*.md"`，以 **pathlib `Path.glob`** 展開，
`*` **不跨 `/`** ⇒ 搬進 `Archive/` 即掉出掃描面。
**移除是被允許的方向**：該常數的註解逐字寫「① **自清**：登記在案的檔一旦收得到宣稱，本鎖立刻紅並要求把它刪掉（**只准縮**）」。

> ⚠️ 同時要確認 `test_the_newest_handoff_carries_its_own_lower_bound`（`:6898`）：它取
> `max(docs, key=_handoff_round)`。只要 R84（或 R85）留在上層，此條不受影響。

#### 3-B `CrossPlatform_*.md` × 25（1,368,269 bytes）

**全部 25 支共用同一道鎖，改法相同**：

- **要先改的鎖**：`tools/lib/governance_docs.py` 的 `_GOVERNANCE_DOCS`（tuple 常數，`:47~149`）。
- **歸檔後會紅的是**：`tools/check_defect_log_crossref.py:1314` → `oversize_problems(list(_GOVERNANCE_DOCS))`
  → `tools/lib/defect_ledger_index.py:168~172`，逐字
  「**具名治理文件不存在：{p.name} — 涵蓋面已與磁碟脫節，拒絕靜默跳過（跳過就等於這一份檔的體積守門被悄悄拿掉）**」
  ⇒ `check_defect_log_crossref.py` 回 **rc=1**；連帶
  `tools/tests/test_check_defect_log_crossref.py::TestMain::test_main_against_real_repo_is_clean`（拿真實 repo 跑 `main()`）轉紅。
- **要同步做什麼（二擇一，是政策決定不是技術選擇）**：
  1. **改路徑**：把該筆改成 `_REPO_ROOT / "docs" / "06_quality" / "Archive" / "<檔名>.md"`。
     檔案仍受體積守門與指針稽核 ⇒ **義務不變、只是換位置**。發現面 glob
     （`_GOVERNANCE_DOC_DIR.glob("CrossPlatform_*.md")`，pathlib、不跨 `/`）不會再看到它，
     所以 `unregistered_governance_docs()` 也不會吵。**建議走這條。**
  2. **整筆刪除**：該檔從此**同時逸出體積守門與指針稽核**。`governance_docs.py:44~46` 明載這正是
     `unregistered_governance_docs()` 在防的形態。走這條必須在該常數留下逐字理由。

**25 支逐檔（皆為 `governance_docs.py` 內具名，另列額外消費端者標註）**：

| 檔 | bytes | `_GOVERNANCE_DOCS` 行 | 額外消費端（歸檔後另需處理） |
|---|---:|---:|---|
| `CrossPlatform_R60_Fix_Evidence.md` | 200,024 | 48 | 🔴 `tools/tests/test_windows_smoke_heartbeat_doc_sync.py:76` 具名讀檔；`tools/archive_defect_log.py:49,56,228,345,349,355,742` 註解 |
| `CrossPlatform_R60_Fix_Evidence_r3.md` | 68,065 | 49 | 🔴 `tools/tests/test_archive_defect_log.py:2276` 具名 |
| `CrossPlatform_R61_Architect_Evidence.md` | 9,768 | 52 | — |
| `CrossPlatform_R61_SAQA_Evidence.md` | 8,923 | 53 | — （全庫僅此一處引用） |
| `CrossPlatform_R62_Architect_Evidence.md` | 16,181 | 54 | — |
| `CrossPlatform_R68_Scan_Findings.md` | 87,727 | 57 | `test_adr_xplat001_c1c2_lock.py:3891,4801` 註解 |
| `CrossPlatform_R75_Review_Evidence.md` | 43,000 | 59 | `test_check_defect_log_crossref.py:1136` 註解 |
| `CrossPlatform_R76_Scan_Findings.md` | 105,749 | 62 | `test_doc_loc_baseline_freshness_r60.py:6618` 註解 |
| `CrossPlatform_R77_Triage.md` | 39,009 | 65 | — |
| `CrossPlatform_R77_Fix_Plan.md` | 57,467 | 66 | — |
| `CrossPlatform_R78_Debt_Audit.md` | 17,564 | 69 | `check_defect_log_crossref.py:623` 註解 |
| `CrossPlatform_R78_Review.md` | 10,355 | 75 | `tools/run_root_unittests.py:58` 註解 |
| `CrossPlatform_R79_Debt_Audit.md` | 97,393 | 77 | 🔴 4 處**跨子專案**註解：`AutoClaude/tests/test_gap014_020.py:79`、`AutoClaude/tests/test_gap039_049.py:49`、`tools/session_resume_planner.py:38`、`tools/lib/defect_ledger_index.py:613` |
| `CrossPlatform_R79_Review.md` | 6,674 | 79 | — |
| `CrossPlatform_R80_Subtraction_Evidence.md` | 23,310 | 81 | 🔴 **7 支檔的 provenance 註解**：`check_script_parity.py:681`、`lib/bash_probe_spec.py:15`、`tests/_platform_helpers.py:229`、`test_git_hooks_install_common.py:32`、`test_pre_push_dispatcher.py:48`、`test_windows_forbidden_filename_parity.py:57`、`test_windowsapps_guard_bash_parity.py:77` |
| `CrossPlatform_R80_PackF_Posix_Evidence.md` | 19,470 | 84 | — |
| `CrossPlatform_R80_Scan_Findings.md` | 54,026 | 87 | 🔴 `test_adr_xplat001_c1c2_lock.py:962,982` 為**具名居所字串**；`lib/defect_ledger_index.py:628`、`check_defect_log_crossref.py:660` |
| `CrossPlatform_R80_Review.md` | 10,114 | 90 | — |
| `CrossPlatform_R81_Scan_Findings.md` | 172,697 | 95 | 🔴 `test_adr_xplat001_c1c2_lock.py:1001,1026,1046,1065,1087,3184` 具名居所；`lib/defect_ledger_index.py:657` |
| `CrossPlatform_R81_Quota_Review.md` | 104,403 | 96 | — |
| `CrossPlatform_R81_Ledger_Triage.md` | 91,349 | 97 | `check_defect_log_crossref.py:638`、`lib/defect_ledger_index.py:639` |
| `CrossPlatform_R81_Review.md` | 17,069 | 101 | `test_doc_loc_baseline_freshness_r60.py:4222` 註解 |
| `CrossPlatform_R82_Ledger_Closure.md` | 67,057 | 109 | 🔴 `check_defect_log_crossref.py:646`、`lib/defect_ledger_index.py:554,662`；另 `governance_docs.py:138,142` 拿它當**判例引用** |
| `CrossPlatform_R82_Scan_Findings.md` | 32,989 | 115 | 🔴 `test_adr_xplat001_c1c2_lock.py:1104,1119,1134` 具名居所 |
| `CrossPlatform_R82_Mac_Switch_Obstacles.md` | 7,886 | 120 | — |

> 🔴 **「具名居所字串」那幾筆是最貴的**：`test_adr_xplat001_c1c2_lock.py` 把
> 「某 DEF-ID 的詳情住在 `CrossPlatform_R8X_Scan_Findings.md` §B」寫成**斷言字串**。
> 搬檔後那些字串會變成假指路（指向不存在的上層路徑），而**它們是字串比對、不是路徑存在性檢查
> ⇒ 不會轉紅**。這是搬這一族時最容易漏的一半。

---

## 5. 取數管道自證（正對照組）

任何「0 命中／無消費端」的宣稱，都必須先證明搜尋工具本身找得到東西。以下為**同一個指令形態**的正負對照：

```bash
# 正對照（已知必中）：R85 掃描發現文件確實登記在 governance_docs.py
git grep -F -n -- 'CrossPlatform_R85_Scan_Findings.md' -- tools/lib/governance_docs.py
# → tools/lib/governance_docs.py:148:    _REPO_ROOT / "docs" / "06_quality" / "CrossPlatform_R85_Scan_Findings.md",
# → rc=0                                    ✅ 管道有牙

# 負對照（本盤點的宣稱之一）：R74 交棒書全庫零引用
git grep -F -n -- 'R74_HANDOFF.md' -- tools/ .github/ AutoClaude/ AISDLC_SDD/
# → （無輸出）  rc=1                          ✅ 同形態、同旗標，得到 0 命中
```

**rc 取法紀律**：兩者皆**未接管線**，rc 先存進變數再列印
（`git grep … ; PC_RC=$?; echo "rc=$PC_RC"`）。理由：`sh -c 'exit 7' | tail -1` 實測 rc=0，
且 `echo "$(basename $f) rc=$?"` 的命令替換會覆蓋 `$?`。

### 5.1 第二組自證：`glob` 的分隔符行為（本提案的核心機制）

「搬進 `Archive/` 就掉出掃描面」這句話對 pathlib 為真、對 git pathspec **不必然**為真。實測：

```bash
git ls-files 'docs/04_planning/*improving_01.md'
# → docs/04_planning/Archive/AutoSDD_improving_01.md      rc=0
#   ⇒ git pathspec 的 `*` **會**跨越 `/`
```
```python
pathlib.Path('.').glob('docs/04_planning/*improving_01.md')   # → []   ⇒ pathlib 的 `*` **不**跨 `/`
```

⇒ 判準用哪一種 glob，決定歸檔對它是「掉出掃描面」還是「照樣看得到」。本檔逐筆分類時已據此區分。
（本次候選的實際樣式如 `R*_HANDOFF.md`／`AutoSDD_Defect_Log_archive_*.md`，其字面前綴與 `Archive/` 不相容，
故兩種 glob 皆掉出掃描面；但**不可把這個結論外推到別的樣式**。）

### 5.2 第三組自證：已歸檔家族的天然對照實驗

不必搬任何檔就能量到「歸檔的效果」——`AutoSDD_ZeroTrust_Audit_*` 這一族**早就搬完了**：

| 查詢 | 實測 |
|---|---|
| `git ls-files 'docs/06_quality/AutoSDD_ZeroTrust_Audit_*.md'`（舊位置） | **0 筆** |
| `git ls-files 'docs/06_quality/Archive/AutoSDD_ZeroTrust_Audit_*.md'` | **98 筆** |
| pathlib `docs/06_quality` 內 `AutoSDD_ZeroTrust_Audit_*.md` | **0** |
| pathlib `docs/06_quality` 內 `AutoSDD_Defect_Log_archive_*.md`（對照組，未歸檔） | **67** |

⇒ 「搬進 `Archive/` ＝ 對上層 glob 完全消失」是**量到的**，不是推論的。

> ⚠️ **取數管道的已知陷阱（誠實劃界）**：`git ls-files` 對**零命中**回 **rc=0**（不是 1），
> 所以「rc 是 0 所以有找到」是假綠——本節一律以**行數**當憑證，不以 rc 當憑證。
> 這與根 `CLAUDE.md` 對 `Get-ScheduledTask` 的判決同型（憑證是值，不是 rc）。

### 5.3 基線 rc（歸檔前的對照值）

```bash
.venv/bin/python tools/check_defect_log_crossref.py    # rc=0
```
輸出逐字含「具名治理文件 **31 份**皆已登記且未逾體積上限（登記面對 `CrossPlatform_*.md` 發現面雙向核對）」。
⇒ **收尾窗口動手前後各跑一次，rc 必須都是 0**；若動手後變 1，訊息會逐字指名是哪一支檔脫節。

---

## 6. 可逐字執行的清單（依相依序；限收尾單人窗口）

> **前置條件（缺一不可）**
> - 所有並行包已停工，工作樹只有你一個人在動（`git status --porcelain` 你自己看得懂每一行）。
> - 執行前先跑基線：`.venv/bin/python tools/check_defect_log_crossref.py`，rc 必須為 0。
> - 🔴 **一律 `git mv`，不得 `mv`**：`git mv` 保留追蹤，普通 `mv` 會讓檔案變成「git-tracked 但磁碟不存在」，
>   觸發全樹十餘支 fail-loud（＝〈跨檔參照稅〉那一筆）。
> - 🔴 **不得 `git stash`**（R84 曾清空 20 個檔）。

### 階段 0 — 建立量測基準

```bash
cd /Users/wuweihong/Antigravity/AISDCL_Agent
.venv/bin/python tools/check_defect_log_crossref.py; echo "BASELINE_RC=$?"     # 期望 0
.venv/bin/python tools/run_root_unittests.py > /tmp/r85_before.log 2>&1; echo "UT_RC=$?"
```

### 階段 1 — 桶①之 `improving`（零風險，轉址規則已覆蓋；**必須整段一起做**）

⚠️ **順序約束**：`test_ntfs_trailing_space_device_name.py::test_archive_and_active_round_ranges_do_not_interleave`
要求**已歸檔輪號全部小於仍在上層的輪號**。目前 Archive 最大 102、上層最小 103。
⇒ 只能從 103 起**連續**往上搬，且**必須把 109 留在上層**（見桶②）。搬 103~108 之後：archived max=108 < active min=109 ✅。
**不可只搬其中幾支造成號段交錯。**

```bash
git mv docs/04_planning/AutoSDD_improving_103.md docs/04_planning/Archive/
git mv docs/04_planning/AutoSDD_improving_104.md docs/04_planning/Archive/
git mv docs/04_planning/AutoSDD_improving_105.md docs/04_planning/Archive/
git mv docs/04_planning/AutoSDD_improving_106.md docs/04_planning/Archive/
git mv docs/04_planning/AutoSDD_improving_107.md docs/04_planning/Archive/
git mv docs/04_planning/AutoSDD_improving_108.md docs/04_planning/Archive/
# 驗收（四支鎖，README 指定）
.venv/bin/python -m unittest -v tools.tests.test_ntfs_trailing_space_device_name 2>&1 | tail -20; echo "RC=$?"
.venv/bin/python -m unittest tools.tests.test_check_defect_log_crossref 2>&1 | tail -5; echo "RC=$?"
```
**同步改的鎖：無。**（此族已被 `_ARCHIVABLE_DOC_RE` 轉址規則覆蓋。）
**回收：185,129 bytes。**

### 階段 2 — 桶①之 `R*_HANDOFF`（無鎖，但會靜默斷鏈）

```bash
for n in 74 77 79 80 81 82; do git mv "docs/04_planning/R${n}_HANDOFF.md" docs/04_planning/Archive/; done
.venv/bin/python -m unittest tools.tests.test_doc_loc_baseline_freshness_r60 2>&1 | tail -5; echo "RC=$?"
.venv/bin/python -m unittest tools.tests.test_negative_existence_claims_r82 2>&1 | tail -5; echo "RC=$?"
.venv/bin/python -m unittest tools.tests.test_adr_xplat001_c1c2_lock 2>&1 | tail -5; echo "RC=$?"
```
**同步改的鎖：無**（R83／R84 留在上層，`_HANDOFF_RECONCILE_SINCE=83` 與「最新一份」兩條皆不受影響）。
**已知代價**：`tools/session_resume_planner.py:64` 的 `R79_HANDOFF.md` 註解成為死指路（不會紅）。
建議同輪把該註解改為 `docs/04_planning/Archive/R79_HANDOFF.md`。
**回收：147,599 bytes。**

### 階段 3 — 桶③之 `R*_HANDOFF` ×3（**先改鎖，再搬檔**）

```bash
# 3-1 先改鎖：從 frozenset 移除三筆（該表註解逐字寫「只准縮」）
#     檔：tools/tests/test_doc_loc_baseline_freshness_r60.py:6813 _HANDOFF_CLAIMLESS_BASELINE
#     動作：刪掉 "docs/04_planning/R75_HANDOFF.md" / "R76_..." / "R78_..." 三行
#     ⚠️ 移除後該 frozenset 會變成空集合——先確認同檔沒有「非空」斷言再動手。
# 3-2 再搬檔
for n in 75 76 78; do git mv "docs/04_planning/R${n}_HANDOFF.md" docs/04_planning/Archive/; done
# 3-3 驗收
.venv/bin/python -m unittest tools.tests.test_doc_loc_baseline_freshness_r60 2>&1 | tail -5; echo "RC=$?"
```
**歸檔這三支會讓 `test_doc_loc_baseline_freshness_r60.py:6891` 的 ghosts 斷言轉紅**，
必須同步做 3-1。**回收：87,878 bytes。**

### 階段 4 — 桶③之 `CrossPlatform_*` ×25（最大一塊，**逐檔改常數**）

**每一支都是「先改 `governance_docs.py` 的那一行路徑，再 `git mv`」**，順序不可顛倒
（先搬檔會讓 `check_defect_log_crossref.py` 立刻 rc=1，把後續步驟埋在紅色裡）。

```bash
# 4-1 對 §4 桶③-B 表列的 25 支，逐筆把 tools/lib/governance_docs.py 內
#     _REPO_ROOT / "docs" / "06_quality" / "<檔名>"
#   改成
#     _REPO_ROOT / "docs" / "06_quality" / "Archive" / "<檔名>"
#   （建議走「改路徑」而非「刪除」：義務不變，只是換位置——理由見 §4 桶③-B）
# 4-2 逐支搬檔
git mv docs/06_quality/CrossPlatform_R60_Fix_Evidence.md    docs/06_quality/Archive/
git mv docs/06_quality/CrossPlatform_R60_Fix_Evidence_r3.md docs/06_quality/Archive/
# …（其餘 23 支照 §4 桶③-B 表）
# ⚠️ 不要搬 Scan_Dimensions / Maturity_Criteria / R83_Scan_Findings / R84_Scan_Findings /
#    R85_Ledger_Closure / R85_Scan_Findings —— 那 6 支在桶②
# 4-3 驗收（這一步是本階段唯一的憑證）
.venv/bin/python tools/check_defect_log_crossref.py; echo "RC=$?"      # 必須仍是 0
.venv/bin/python -m unittest tools.tests.test_check_defect_log_crossref 2>&1 | tail -5; echo "RC=$?"
.venv/bin/python -m unittest tools.tests.test_archive_defect_log 2>&1 | tail -5; echo "RC=$?"
.venv/bin/python -m unittest tools.tests.test_windows_smoke_heartbeat_doc_sync 2>&1 | tail -5; echo "RC=$?"
```
**額外要一起改的**（否則變成假指路，且**不會轉紅**）：
- `tools/tests/test_windows_smoke_heartbeat_doc_sync.py:76` — `CrossPlatform_R60_Fix_Evidence.md` 具名路徑。
- `tools/tests/test_archive_defect_log.py:2276` — `CrossPlatform_R60_Fix_Evidence_r3.md` 具名。
- `tools/tests/test_adr_xplat001_c1c2_lock.py` 的具名居所字串（`:962,982,1001,1026,1046,1065,1087,1104,1119,1134,3184`）。
- `tools/tests/_platform_helpers.py:229` 等 7 支檔的 `R80_Subtraction_Evidence` provenance 註解。

**回收：1,368,269 bytes。**

### 階段 5 — 收尾驗收（一次全跑，貼出 rc）

```bash
.venv/bin/python tools/check_defect_log_crossref.py; echo "CROSSREF_RC=$?"        # 期望 0
.venv/bin/python tools/run_root_unittests.py > /tmp/r85_after.log 2>&1; echo "UT_RC=$?"
diff <(grep -c . /tmp/r85_before.log) <(grep -c . /tmp/r85_after.log)   # 參考用
ls docs/04_planning/*.md | wc -l ; ls docs/06_quality/*.md | wc -l       # 應顯著下降
```
🔴 **`run_root_unittests.py:58` 有 `MIN_TESTS` 下限**（當前 3268）。歸檔**不應**減少測試數；
若它下降，代表某支測試被 collection 略過了——那是必須查明的訊號，不是可以重釘的數字。

---

## 7. 一句話結論

**可回收 40 支檔 / 1,788,875 bytes（約 1.71 MiB）**，其中 **12 支（332,728 bytes）現在就能搬**，
**28 支（1,456,147 bytes）要先改 2 個具名常數**（`_HANDOFF_CLAIMLESS_BASELINE` 與 `_GOVERNANCE_DOCS`）。
**最大的一塊（帳本歷史分冊 67 支 / 2,154,244 bytes）刻意不動**——有一支測試專門斷言它不歸檔，
政策是它的上游，不是可以順手改掉的判準。

---

## 8. 本檔未驗證的事項（誠實劃界）

- 本輪**沒有實際搬動任何檔**，因此上述「哪支測試會紅」全部是**依判準原始碼推得**，
  除了 §5.2 那組天然對照實驗之外，**沒有一筆是搬檔後實測**。收尾窗口執行時應逐階段驗收，
  不採信本檔任何「會／不會紅」的宣稱。
- 未驗證：階段 3 移除 `_HANDOFF_CLAIMLESS_BASELINE` 三筆後該 frozenset 變空，是否有其他斷言要求它非空。
- 未驗證：`AutoSDD_Defect_Log_archive_INDEX.md` 的索引 bullet 對「磁碟上已不存在的 archive」是否有反向涵蓋性檢查
  （`archive_defect_log.py:896` 記載的方向是**磁碟→索引**；反向未查）。此項僅在有人推翻桶② 的政策時才需要。
- 未驗證：`.github/workflows/*.yml` 的 `paths:` 過濾器在 `CrossPlatform_Scan_Dimensions.md` 與
  `CrossPlatform_Maturity_Criteria.md` 之外，是否還有間接依賴本次搬動的 25 支檔（已 grep 過 4 支 workflow，未見命中）。
