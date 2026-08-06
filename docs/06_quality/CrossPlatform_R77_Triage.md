# R77 跨平台輪 — Triage（十二維深掃 → 可執行修復序）

- 產出時間：2026-08-06
- 輸入：`tasks/w1x98bvda.output`（12 維 StructuredOutput，213,313 字元／1,761 行，已分段全讀）＋ 12 份證據檔 `r77_scan_{A,B,C,D,E,F,G,H,N,T,W,Q}.md`（Glob 實查：**12 份全部存在**，size 26,800~48,713 bytes）
- repo HEAD（各維一致回報）：`a1ee537`；工作樹開場即有 3 行 porcelain（`AutoSDD_Defect_Log.md` M／`archive_INDEX.md` M／`archive_60.md` ??），十二維一致回報**非掃描 agent 所為**（另一個並行 agent 在歸檔帳本）
- 本檔是後續所有修復包的**唯一依據**。

---

## 0. 數字總帳

| 量 | 值 | 出處 |
|---|---|---|
| 原始 finding 總數 | **139** | task output `logs[0]` 逐字「掃描完成：12/12 維回報，共 139 筆 finding」；逐維點數 A9 B7 C14 D10 E12 F12 G12 H11 N13 T14 W11 Q14 = 139 ✅ |
| 跨維真重複（同一缺陷、≥2 維各報一次） | **12 對** | 見 §1 |
| 剔除為越界 | **0** | 見 §2 |
| 去重後真實缺陷數 | **127** | 139 − 12 |
| 結構化回傳的工作項數 | **60** | schema 上限；60 個工作項**完整覆蓋** 127 筆（低優先者以同包同檔複合項承載，複合項標題內逐一點名原始 ID）。全 127 筆的逐筆對照見 §5 |

> 🔴 **誠實劃界**：`total_after_dedup=127` 與 `items=60` 不相等，這是刻意的——60 是 schema 硬上限，不是缺陷數。我**沒有**為了湊數把任何一筆丟掉；§5 的對照表是完整的，refuter 可逐筆反查。

---

## 1. 去重紀錄（12 對真重複，全部合併保留最強取證）

| # | 合併後 | 併入的原始 ID | 各自最強取證（保留者以 ★ 標） | 理由分歧？ |
|---|---|---|---|---|
| M1 | hook fail-CLOSED 誤擋 Task | A-02 ★／W-07 | A-02：七輸入 rc 矩陣（Bash=2/Read=0/Task=0/壞JSON=2/空=2/缺 tool_name=2）＋ 指出三支姊妹 hook 走 bytes 層 decode、唯一 fail-closed 那支沒這道防線。W-07：同一組七輸入、另補「tool_name=null→2」與 `tool_input.command` 簽名鍵修法 | 否。兩維獨立命中同一段程式碼、同一組 rc |
| M2 | act 薄殼寫死 workflow | A-03／F-11 ★ | A-03：21 ubuntu job 中 12 個零通道的**結構推導**（含 root-infra 與 windows-nightly-alert 點名）。F-11：`run_act.ps1 -List` 實跑 JOB_COUNT=9 對照根目錄 `act -l`=25 的**執行量測** | 否。F-11 是量測、A-03 是影響面盤點，互補 |
| M3 | root-infra 本機通道缺口 | C-06／F-03 ★ | C-06：19 道逐道比對，4 道無本機等價（全量 `bash -n`／pwsh 語法／.ps1 CRLF／第 19 道）。F-03：`act -j root-infra` 實跑 `pwsh: command not found` exitcode 127 ＋ 映像實查 PWSH/RUFF/GH 三缺 | ⚠️ **有分歧**：C-06 提議「做 root-infra act 薄殼」並自陳「act 能不能跑是推論」；F-03 實測證明**照 C-06 的處方會在第 2 道 127**。合併後以 F-03 的量測為準，C-06 的處方須加 `full-latest` 映像或 pwsh 安裝步 |
| M4 | root-infra 第 15 道哨兵豁免到期＋理由已被證偽 | C-09／F-12 ★ | C-09：WAIVER_UNTIL/REASON/MAX_AGE_DAYS 三個常數逐字＋08-05 四筆 never-started 反證。F-12：同三常數＋兩軌最近成功時戳做算術得「約 08-13/14 push 全紅」 | 否 |
| M5 | 雲端結論錨落後＋§7 表③ 失實 | C-04／D-02 ★ | C-04：錨逐字＋`git log a61bf0c..HEAD`=4。D-02：同上＋三支 workflow 對 HEAD 的 gh 現查皆 failure＋指出「漏做即合格」的語意反轉 | 否 |
| M6 | Windows nightly 不跑根層 unittest／SDD 雙軌 | C-07／N-02 ★ | C-07：.ps1 2010 行 vs .sh 267 行的 stage 逐項對照＋R73 撤回句逐字。N-02：同段逐字＋指出 `windows_smoke_local.ps1:62-66` 也把 tools/tests pytest 列為不在範圍 | 否 |
| M7 | `--help` 直接開跑 nightly | C-12／G-10 ★ | C-12：15 處函式層 param、檔頂零 param()。G-10：同上＋把家族擴到全部 11 支 .ps1（col0_param 為空者 5 支、`$Help` 命中皆 []）＋點出 `windows_smoke_local.ps1` 同形態零登記 | 否。G-10 是 C-12 的超集 |
| M8 | 本輪新維度代號未定義 → SC-7 紅 | W-01／Q-08 ★ | W-01：`Scan-W` 記憶體注入帳本列 → SC-7 訊息逐字。Q-08：`Scan-Q` 同型注入＋額外抓到 `_SCAN_CODE_RE` 會把 `Scan-Q3` 讀成 `Scan-Q`（R76 已用過一次並逃過） | 否。同一缺陷、兩個代號，Q-08 多一層歷史證據 |
| M9 | drift checker 無 push 閘門消費其 rc | H-09／N-13 ★ | H-09：全庫 Grep 逐站點歸類，唯一消費者是 `run_local_nightly.ps1:1919-1944`。N-13：同結論＋指出 R76 已記載並排進「包 I」而包 I 未落地（`git log -- pre-push` 停在 R69） | 否 |
| M10 | 缺陷帳本未結列逼近硬閘 | T-7／D-10 ★ | 兩維同一支工具同一則輸出（85／104、warn 86 fail 98、bytes 232,158）。D-10 多一句歸屬聲明（bytes 下降是別的 agent 歸檔造成） | 否 |
| M11 | 退場欄形式主義（8/8 未指派） | E-05／T-11 ★ | E-05：`_UNPINNED_EXIT_RE` 逐字＋:624 自陳不驗輪號。T-11：同 8 筆＋逐筆理由自陳「未證實硬技術障礙」＋棘輪 slack=0 | 否。另 G-09 提供「兩個家」的機制解釋，一併併入（見 §5 R77-13） |
| M12 | 護欄層規模判準零鑑別力 | E-01／H-08 ★ | E-01：`scan_h_problems()` 三款判準逐條＋14 個取樣點自 git 物件重建（26286→54188）。H-08：同三元組實跑＋逐 commit 回算＋top-5 集中度 38% | 否 |

**近似但刻意不合併者（保留為獨立缺陷，理由）：**
- `F-01`（act 對兩支平台 smoke 假綠）與 `N-05`（macOS 側本輪覆蓋為零）：**已合併**（同一機制的兩半，N-05 提供誠實劃界的處置）。
- `N-03`（交棒書方向對調）與 `N-04`（對面平台 API 零機械物）：**不合併**。N-04 是缺口本體，N-03 是治理文件對該缺口的**誤診**（「只有 mac 真機補得了」）。兩者修法不同（加掃描器 vs 訂正文件），且 N-03 是 N-04 的下游後果。
- `D-06`（治理文件引用零掃描面）與 `Q-07`（Skipped_Test_Inventory 三鎖射程外）：**不合併**。D-06 是通用掃描器缺口，Q-07 是一個具體實例＋該檔 18 行已過期基線的內容修復。
- `E-03`（刪 28 凍結版，政策級）與 `T-12`（債務量測須分 live/frozen 欄）：**不合併**。同一根因、兩種完全不同成本的處置（XL vs S）。

---

## 2. 剔除紀錄

**剔除為越界：0 筆。**

逐項檢查過、**刻意不剔除**的邊緣案例：

| 候選 | 為何看起來越界 | 為何仍保留 |
|---|---|---|
| A-08（`write_text` 未帶 `newline=` 434 處） | 掃描者自陳「存量債、非活缺陷、`.gitattributes` 已擋」 | 它的危害路徑（寫給 bash 吃的**未追蹤**暫存 .sh → Linux/Docker `$'\r': command not found`）正好是 `.gitattributes` 幫不上忙的那一格，屬 Mac×Win 相容性射程 |
| A-09（FileStateRepository 未排序 ＋ naive 本地時間） | 「dev 用途、production 走 Pg」 | NTFS 字母序 vs APFS readdir 序會讓同一斷言 Windows 綠／mac 紅並看起來像 flaky——本 repo 已為「假 flaky」付過三次學費（DEF-101-268 等） |
| T-12（Copy-on-Evolve 讓債 ×30） | 「不提修法」 | 它提的是**量測紀律**（分 live/frozen 欄），直接影響 Q5 所有存量數字的可信度 |
| G-12（軌道② active 容器其實是空的） | 屬 AISDLC_SDD 治理，非跨平台 | 根 CLAUDE.md 把「active 為 26 號」寫成常數＝本 repo 反覆吃虧的形態，落在「治理文件失實宣稱」射程 |
| W-09（session jsonl 零消費者） | 屬工具鏈觀測，非 repo 缺陷 | 它是 M2／M4 分子唯一可能自動化的來源，直接服務 Q6 |
| E-03（刪 28 個凍結版目錄） | 需掌舵者核准、非本輪可做 | 「需人工決策」正是 [[no-defer-unless-justified]] 允許延後的兩類之一，但**必須明說並提案**，不得靜默略過 |

**十二維自陳的未覆蓋面（不是 finding，但 refuter 與後續包必須知道）：**
1. **mac 真機零覆蓋**——12 維全部一致自陳。凡涉 macOS 執行期行為者一律是讀碼／POSIX 標準語意推論（A-01 mac PATH、A-06 `resolve()` 不正規化大小寫、B-01 mac 側 `core.protectNTFS` 預設值、C-08 launchd、N-05）。
2. **AISDLC_SDD 凍結版 v0.01~v0.29 內容**——依 Copy-on-Evolve 只計數不分析。
3. **雲端零觸發**——所有 gh 查詢皆唯讀；帳務停擺期間無法 dispatch 驗證任何修復。
4. Scan-A／E 兩維自陳**未做**「動工前 `gh run list` 雲端 CI 可用性現查」（採信任務書前提）。Scan-A 另自陳未做「當前平台實跑入口腳本」（由 Scan-F 承擔，F 已實跑）。
5. **方法論警告（Scan-A 實測，全體適用）**：Grep 工具的 content 輸出會把部分斜線渲染成反斜線（兩例實證）。⇒ **凡涉路徑分隔符的 finding 不得引用 Grep content**，須用 Read 或 runtime `repr()`。Scan-F 另有一筆因此被證偽（`test_ps51_compat._TREE_FLOORS` 疑似逸出序列＝假警報）。

---

## 3. 分級判準與我改過的等級

判準（本輪一致套用）：**這個東西壞掉時誰會發現**。
- **P0**：現在就在造成錯誤結果，或會讓另一平台開箱即壞，且沒有任何機械物會說話。
- **P1**：另一平台會壞／閘門沒有鑑別力／宣稱與實況不符，但今天還沒咬到人。
- **P2**：前瞻缺口／可觀測的架構債。
- **P3**：整潔性、文件精確度。

十二維共回報 **9 筆 P0**（B-01、C-01、C-02、F-01、N-01、N-02、N-03、Q-01、Q-02）。我維持 6 個 P0 工作項，**三筆下修並逐筆說明**（refuter 請優先加壓這三筆的降級是否正確）：

| 原 | 原級 | 我判 | 為何下修 |
|---|---|---|---|
| C-01（R76 診斷把兩 step 對調） | P0 | **P1** | 它不產生錯誤結果，是**誤導下一輪**。與 N-03 同型。仍屬最高優先的 P1（會讓 R77 把預算投錯地方） |
| N-03（交棒書方向對調＋誤診） | P0 | **P1** | 同上。其量測本體（mac→Win 攔截率 0/10）是 N-04 的內容，N-04 保留為 P1 <!-- xplat-rate-history: R77 動工前量測，現值見 CrossPlatform_Maturity_Criteria.md M5 列的載具 --> |
| Q-01（pg-contract 155 支零下限斷言） | P0 | **P1** | 雲端上 env **有設**，155 支今天真的在跑 ⇒ 是 latent（env 一掉才靜默歸零）。真正今天就是 0 的是 Q-02（本機 nightly 每晚照樣 skip 143 支），Q-02 維持 P0 |

**上修 0 筆。** 合併項的等級取構成筆中最高者（例：R77-01 = B-01(P0) + B-06(P3) → P0）。

---

## 4. 修復包切分（16 包）與檔案歸屬證明

### 4.1 包→擁有檔案（**互不重疊**）

| 包 | 擁有的檔案／目錄（唯一擁有者） |
|---|---|
| **PKG-HOOK** | `.claude/settings.json`、`.claude/hooks/**`（含新增 `_run.py`、`lint_powershell_command.py`）、`AutoClaude/.claude/settings.json`、`AutoClaude/tools/hooks/**`、`AISDLC_SDD/AISDLC_SDD_v0.30/.claude/settings.json`、`tools/tests/test_check_hooks_liveness.py` |
| **PKG-PRECOMMIT** | `tools/git-hooks/pre-commit`、`tools/check_ntfs_paths.py`、`AISDLC_SDD/scripts/component_sanitizer.py`、`AutoClaude/autoclaude/utils/logger.py`、`tools/tests/test_windows_forbidden_filename_parity.py`、`tools/tests/test_windowsapps_guard_bash_parity.py`、`tools/tests/test_ps1_bom.py` |
| **PKG-GATEWIRE** | `tools/git-hooks/pre-push`、`tools/integration_gate_core.py`、`tools/check_hooks_liveness.py`、`tools/check_scheduled_task_drift.py` |
| **PKG-ACT** | `.actrc`、`AutoClaude/tools/run_act_core.py`、`AutoClaude/tools/run_act.ps1`、`AutoClaude/tools/run_act.sh`、`AutoClaude/tests/test_perception.py`、`tools/tests/test_smoke_ci_sync.py` |
| **PKG-CI** | `.github/workflows/**`、`tools/ci_liveness.py`、`tools/tests/test_workflow_permission_concurrency_lock.py`、`tools/tests/test_gha_action_versions.py` |
| **PKG-SCHED** | `AutoClaude/tools/run_local_nightly.ps1`、`AutoClaude/tools/run_local_nightly.sh`、`tools/windows_smoke_local.ps1`、`tools/macos_smoke_local.sh`、`tools/scheduled_task_expectations.json`、`tools/install_mac_nightly.sh`、`tools/install_windows_nightly.ps1`、`tools/tests/test_schedule_capability_parity.py`、`AutoClaude/tools/{ga_window,observability_snapshot,drift_log_snapshot}.py`、`AutoClaude/tests/tools/test_run_local_nightly_static.py` |
| **PKG-LOCK-A** | `tools/tests/test_platform_neutral_paths.py`、`tools/tests/test_subprocess_encoding_hygiene.py`、新增 `tools/tests/_xplat_injection_corpus.py`、`tools/lib/windows_skip_tags.py` |
| **PKG-LOCK-B** | `tools/tests/test_doc_loc_baseline_freshness_r60.py`、`tools/check_defect_log_crossref.py`、`tools/tests/test_check_defect_log_crossref.py`、`tools/check_gha_action_versions.py`、新增 `tools/lib/check_sequence.py` |
| **PKG-PARITY** | `tools/check_script_parity.py`、`tools/check_wrapper_thinness.py`、`tools/tests/test_check_script_parity.py`、`tools/tests/test_check_wrapper_thinness.py` |
| **PKG-ARCH** | `tools/tests/test_adr_xplat001_c1c2_lock.py`、`AutoClaude/tools/check_loc_budget.py`、`AISDLC_SDD/scripts/ci-gate.sh`、（提案）`tools/governance_tests/` |
| **PKG-SKIP** | `tools/lib/skip_tag_policy.py`、`tools/run_root_unittests.py`、`tools/tests/test_run_root_unittests.py`、`AutoClaude/tests/conftest.py`、`AutoClaude/tests/contract/test_ac_matrix_scaffolding.py`、`AutoClaude/tests/integration/test_pgvector_hnsw_recall.py`、`AutoClaude/tests/test_gap014_020.py`、`AutoClaude/tests/test_gap039_049.py`、`docs/06_quality/Skipped_Test_Inventory_R76.md` |
| **PKG-DEBT** | `AutoClaude/pyproject.toml`、`AutoClaude/CLAUDE.md`、`AutoClaude/tests/contract/test_claude_md_*.py`、`AutoClaude/tools/{_check_claude_md,_compute_sha,setup_pg_runtime_role}.py`、`AISDLC_SDD/scripts/ruff.toml`(新)、`AISDLC_SDD/AISDLC_SDD_v0.30/tools/fsm_runtime/_chaos_b28_benchmark.py`、AutoClaude/AISDLC_SDD 兩樹的 ruff `--fix` 面 |
| **PKG-DOC-CLAIM** | 根 `CLAUDE.md`、`ONBOARDING.md`、`docs/06_quality/*.md`（除 Skipped_Test_Inventory 與帳本家族）、`docs/04_planning/**/*.md`、`tools/sync_onboarding_baselines.py`、`tools/check_pytest_baseline_sites.py`、`AISDLC_SDD/CLAUDE.md` |
| **PKG-LEDGER** | `docs/06_quality/AutoSDD_Defect_Log.md`、`docs/06_quality/archive_*.md`、`docs/06_quality/archive_INDEX.md`、`tools/archive_defect_log.py`、`tools/tests/test_archive_defect_log.py`、`tools/lib/sdd_latest.py` |
| **PKG-XPLAT** | `AutoClaude/autoclaude/infra/repositories/file_state_repository.py`、`AISDLC_SDD/AISDLC_SDD_v0.30/tools/fsm_runtime/file_lock.py`、`tools/lib/platform_utils.py`、`tools/tests/test_platform_utils_dedup.py` |
| **PKG-PROBE** | `tools/probe/**`（全新目錄） |

### 4.2 🔴 已知的跨包觸點（**必須序列化，不得並行**）

非重疊原則在下列 5 處**做不到零觸點**，我不假裝做得到，改為明寫執行序：

| # | 觸點檔案 | 涉及包 | 序列化規則 |
|---|---|---|---|
| X1 | `AutoClaude/autoclaude/utils/logger.py`、`AutoClaude/tests/test_perception.py` | PKG-PRECOMMIT／PKG-ACT **先**，PKG-DEBT 的 `ruff --fix` **後** | `ruff --fix` 掃整棵 AutoClaude 樹，會動到這兩支。**PKG-DEBT 必須最後跑** |
| X2 | 4 支 `w/lf` 的 .ps1（`tools/lib/GitHooksInstallCommon.ps1` 等） | PKG-PRECOMMIT 做 `git add --renormalize`；PKG-PARITY 可能改其內容 | PKG-PARITY 的內容修改**先**，renormalize **後**（renormalize 是位元組層操作，內容改完再做一次即可） |
| X3 | `tools/tests/test_check_hooks_liveness.py`（A-06 的 parity 測試落點） | PKG-HOOK 唯一擁有 | A-06 的 `platform_utils` 收斂**只提案不落地**在本輪；落地時歸 PKG-XPLAT 並須等 PKG-HOOK 收工 |
| X4 | 四條棘輪常數（`_E501_DEBT_CEILING`／`_ENTRY_WAIVER_CEILING`／`_UNPINNED_HANDOVER_CEILING`／`_UNPINNED_CEILING`） | T-2 的共用預警帶 helper 住 PKG-LOCK-A；呼叫點在 PKG-LOCK-B 與 PKG-PARITY | PKG-LOCK-A **先**建 helper，另兩包**後**接呼叫點 |
| X5 | `check_defect_log_crossref._GOVERNANCE_DOCS`／`check_pytest_baseline_sites._SCAN_FILES`（Q-07 要登記一份文件進去） | 前者 PKG-LOCK-B、後者 PKG-DOC-CLAIM、文件本體 PKG-SKIP | 三包協調：PKG-SKIP 先修文件內容與代號（依賴 R77-07 的 Scan-Q 定義），兩支登記表由各自擁有者加行 |

### 4.3 🔴 動工序（硬相依，不可顛倒）

1. **R77-07（Scan-W／Scan-Q 補進維度表）**——不做這一步，任何含這兩個代號的帳本列或掃描發現檔會讓 SC-7 當場紅並擋住**每一次 push**。且必須落在**同一段連續表格區塊內**（`scan_table_lines()` 遇第一個非 `|` 起頭行即停）。
2. **R77-15（鐵律三棘輪改覆蓋率判準）**——不改它，其他修復要登記的任何新「未覆蓋面」都會撞紅（W-03 注入實測：第 5 項 → `AssertionError: 5 not less than or equal to 4`）。
3. **R77-11（`sync_onboarding_baselines.py` 先瘦身到餘裕 ≥10）**——不做，交棒書 §5-4 的 provenance 欄位加不進去（實測：加 1 行 PASS、加 2 行 RED）。
4. **R77-32（帳本容量）**——本輪動工前先決定「最多能新增幾筆未結列」（現況 85，warn 86，fail 98）。歸檔不降此數。
5. R77-24（PKG-ARCH 移除 `_FROZEN_GUARD_FILE_COUNT`）與 E-09（護欄層分家）**必須同一個 commit 落地**，否則 `guard_count_problems` 會因檔數變動而紅。
6. PKG-DEBT 的 `ruff --fix` **最後跑**（見 X1）。

---

## 5. 全 127 筆 → 60 工作項對照表

> 欄位：`工作項` / `構成的原始 ID` / `級` / `包` / `對應掌舵者題`

| 工作項 | 原始 ID | 級 | 包 | 題 |
|---|---|---|---|---|
| R77-01 NTFS `.git` 家族四判準全放行 → Windows clone rc=128 | B-01, B-06 | P0 | PKG-PRECOMMIT | Q1 |
| R77-02 act 對兩支平台 smoke rc=0 零步驟＝假綠；macOS 本輪覆蓋為零 | F-01, N-05 | P0 | PKG-ACT | Q1,Q5 |
| R77-03 pre-push 慢層對「只改子專案」不觸發，89~98% 掃描面在盲區 | N-01 | P0 | PKG-GATEWIRE | Q1,Q3 |
| R77-04 Windows nightly／smoke 皆不跑根層 unittest，阻塞理由已自證失效 | C-07, N-02 | P0 | PKG-SCHED | Q1,Q3,S1 |
| R77-05 nightly 唯一全樹 stage 跑在 DSN 之前，143 支 PG 契約每晚照樣 skip | Q-02 | P0 | PKG-SCHED | S3,Q1 |
| R77-06 never-started 橫跨 19 天 373/584，ci_liveness 看不見 push 軌 | C-02 | P0 | PKG-CI | Q1,Q6 |
| R77-07 Scan-W／Scan-Q 代號未定義 → SC-7 擋 push（動工序第 1 項） | W-01, Q-08 | P1 | PKG-DOC-CLAIM | Q6 |
| R77-08 block_bash hook 對退化 payload fail-CLOSED，matcher 含 Task | A-02, W-07 | P1 | PKG-HOOK | Q4 |
| R77-09 hook wiring 裸 `python` 102/102 ＋ shim 15 份逐字複本零綁定 | A-01, E-07 | P1 | PKG-HOOK | Q1,Q2,Q3 |
| R77-10 PowerShell 工具面零觀測者（無任何 matcher 匹配） | W-04 | P1 | PKG-HOOK | Q4 |
| R77-11 交棒 §5-4 provenance：目標檔餘裕 1 行；該補的是直譯器/sdk_extra | H-04, Q-03 | P1 | PKG-DOC-CLAIM | Q6,S3 |
| R77-12 承接稽核只覆蓋 15%；條件式交棒判準只讀輪號字面 | G-01, F-10 | P1 | PKG-LOCK-B | Q5 |
| R77-13 退場欄形式主義：8/8 未指派、鎖不驗輪號、測試以 R99 當通過錨 | E-05, T-11, G-09 | P1 | PKG-PARITY | Q5,Q6 |
| R77-14 root-infra 第 15 道哨兵：只讀 run 層／豁免 08-10 到期／理由已偽 | G-02, C-09, F-12 | P1 | PKG-CI | Q1,Q6,S1 |
| R77-15 鐵律三棘輪把「量測值」與「認知範圍」綁成同一個數字 | W-03, W-10 | P1 | PKG-LOCK-B | Q4,Q6 |
| R77-16 同一支鎖檔兩缺陷：兩鎖相反信念全綠／散文宣稱的判準不存在 | H-03, D-01 | P1 | PKG-LOCK-B | Q6 |
| R77-17 早退遮蔽在第二支 pre-push 硬閘原封不動（7 早退點／4 檢查） | H-01 | P1 | PKG-LOCK-B | Q6 |
| R77-18 `_WINDOWS_SKIP_TAG_EXEMPT` 零 stale 自檢、零牙 | H-02 | P1 | PKG-SKIP | S3,Q6 |
| R77-19 M2 判準結構上獎勵「不做四方複審」；分母寫死 25 而實測 36/37 | D-03, W-06 | P1 | PKG-DOC-CLAIM | Q6 |
| R77-20 雲端三類無人看見：perf 真紅／dormant job 假 cron 名／simulate 零用 | C-03, C-05, C-13 | P1 | PKG-CI | Q1,Q6 |
| R77-21 雲端錨落後 4 commit 無 pending=；§7 表③ 五列失實 | C-04, D-02 | P1 | PKG-DOC-CLAIM | Q6 |
| R77-22 windows-nightly-full：R76 診斷把兩 step 對調；本機 PS5.1 parse 鎖可建 | C-01, G-11 | P1 | PKG-CI | Q6,Q1 |
| R77-23 root-infra 4 道無本機等價；act 因映像缺 pwsh 第 2 道 127 | C-06, F-03 | P1 | PKG-ACT | Q1,Q5 |
| R77-24 護欄層規模四缺陷：GLC 零鑑別力／檔數棘輪反效果／52% 守自己／tier 逐檔議價 | E-01, H-08, E-02, E-09, E-10 | P1 | PKG-ARCH | Q2,Q6 |
| R77-25 Copy-on-Evolve：26073 檔 92.7% 位元組重複，28/30 版永不被執行 | E-03 | P1 | PKG-ARCH | Q2,Q5 |
| R77-26 ADR §8.1 9 輪空表無到期機制；§4.2 現值住兩個家 | E-04, E-11 | P1 | PKG-DOC-CLAIM | Q2,Q6 |
| R77-27 護欄／工具層 120 個裸平台述詞；helper 無呼叫端鎖 | E-08 | P1 | PKG-XPLAT | Q2,Q3 |
| R77-28 mac launchd 零期望值 SSOT；兩支 smoke 零覆蓋對帳 | C-08, N-07 | P1 | PKG-SCHED | Q3 |
| R77-29 GA 兩軌最快 08-21/22 且無合法加速；漏跑機制已證實 | C-10 | P1 | PKG-SCHED | Q6,S1 |
| R77-30 `--help` 直接開跑 7 stage nightly；windows smoke 同形態零登記 | C-12, G-10 | P1 | PKG-SCHED | S1,S2 |
| R77-31 帳本六筆死信／錯配／零載體 | G-03, G-04, G-05, G-06, G-07, G-08 | P1 | PKG-LEDGER | Q5 |
| R77-32 帳本未結 85／warn 86／fail 98（餘裕 1 列） | T-7, D-10 | P1 | PKG-LEDGER | Q5 |
| R77-33 對面平台專屬 API 整類零機械物；M5 注入語料零落點 | N-04, N-09 | P1 | PKG-LOCK-A | Q3,Q6 |
| R77-34 `_MARKER_PAIRS` 是空 list，兩處閘門名不副實 | N-06 | P1 | PKG-PARITY | Q3 |
| R77-35 本機防線接線三缺口（liveness advisory／drift rc 無人看） | N-08, H-09, N-13 | P1 | PKG-GATEWIRE | Q1,Q6 |
| R77-36 pg-contract 155 支零下限斷言 | Q-01 | P1 | PKG-SKIP | S3 |
| R77-37 skip reason 三筆：誤判永久不覆蓋／指向不存在通道／藏 59 支 backlog | Q-04, Q-05, Q-10 | P1 | PKG-SKIP | S3,Q5 |
| R77-38 五軌 TLC 零自動通道，而 workflow 註解宣稱「仍留 nightly」 | Q-06 | P1 | PKG-CI | S3 |
| R77-39 skip 治理兩缺口：唯一文件三鎖射程外／無機械物看 skip 總數 | Q-07, Q-09 | P1 | PKG-SKIP | S3,Q6 |
| R77-40 三棵樹的 lint／LOC 存量債與零閘門（815／62／3485；CLAUDE.md 400/400） | T-1, T-4, T-3 | P1 | PKG-DEBT | Q5 |
| R77-41 7 條 slack≤1 棘輪，4 條完全沒有預警帶 | T-2 | P1 | PKG-LOCK-A | Q5,Q6 |
| R77-42 sanitize 委派鎖 10 個消費者只覆蓋 5，且無等值鎖 | B-04 | P1 | PKG-PRECOMMIT | Q1 |
| R77-43 .ps1 工作樹 CRLF 現有 4 支違規；BOM 無 commit 層閘 | F-06, N-10 | P1 | PKG-PRECOMMIT | Q1 |
| R77-44 「PowerShell 工具＝原生 5.1」住三個家、零個鎖、三個都是假的 | F-07 | P1 | PKG-DOC-CLAIM | Q4 |
| R77-45 上一輪三筆結論寫反／過期（根因 n=8 模型、mac→Win 方向對調＋誤診） | W-08, W-11, N-03 | P1 | PKG-DOC-CLAIM | Q4,Q3 |
| R77-46 rc 讀數管線污染方向相反；25/37 配方無具名的家；session jsonl 零消費者 | W-02, W-05, W-09 | P1 | PKG-PROBE | Q4,Q6 |
| R77-47 act 三個載具缺陷：services panic／zombie 假紅／docker cp 併發互踩 | F-02, F-04, F-08 | P1 | PKG-ACT | Q5 |
| R77-48 零本機通道登記表指名兩個不存在的載具，守門只驗檔案存在 | F-05 | P1 | PKG-ACT | Q1,Q3 |
| R77-49 act 薄殼寫死 workflow，只看得到 9／25 個 job | A-03, F-11 | P1 | PKG-ACT | Q1,Q5 |
| R77-50 `Path.resolve()` 大小寫：兩支 exit-2 阻斷級 hook 在兩平台方向相反的錯 | A-06 | P2 | PKG-HOOK | Q1,Q3 |
| R77-51 保留裝置名判準 vs 三個 oracle 不符（COM0／上標變體／立案理由）＋兩張缺口 | B-02, B-03, B-07, B-05, N-12 | P2 | PKG-PRECOMMIT | Q1,Q5 |
| R77-52 兩支姊妹鎖掃描面不對稱＋下限無腐化上界＋newline 缺口＋方向判不出 108 | A-04, A-05, A-08, N-11 | P2 | PKG-LOCK-A | Q1,Q3 |
| R77-53 Scan-H 必跑項的四個結構缺口（散文數字／NOT-PROVEN／退場判準掃描面／指令表） | H-05, H-06, H-07, H-10, H-11 | P2 | PKG-LOCK-B | Q6 |
| R77-54 parity 家族三缺口：LATEST 釘選兩套／薄殼宣稱沒人量／紅埋在第一行 | E-06, T-6, F-09, E-05b | P2 | PKG-PARITY | Q2,Q4 |
| R77-55 concurrency 群組不分事件（2 支 SDD workflow）＋paths 手抄無鎖 | C-11, C-14 | P2 | PKG-CI | Q1 |
| R77-56 skip 四缺口：29 支自鎖 AC matrix／標籤詞彙表無成員檢查／兩棵樹零覆蓋／2-224 起點 | Q-11, Q-12, Q-13, Q-14 | P2 | PKG-SKIP | S3 |
| R77-57 AutoClaude 側技術債五筆：依賴無上限 15／三支孤兒／800 兩個家／×30 量測紀律 | T-5, T-8, T-9, T-14, T-10, T-12 | P2 | PKG-DEBT | Q5 |
| R77-58 生產碼兩處平台語意：`os.open` 文字模式 CRLF／FileStateRepository 未排序 | A-07, A-09 | P3 | PKG-XPLAT | Q1 |
| R77-59 治理文件八處失實／脆弱錨（lifecycle 兩處／零掃描面／寫死行號／兩處快照／ruff 缺 W／軌道② 空） | D-04, D-05, D-06, D-07, D-08, D-09, T-13, G-12 | P2 | PKG-DOC-CLAIM | Q6,Q5 |
| R77-60 —（保留欄，見下方說明） | — | — | — | — |

> ⚠️ 上表列到 R77-59 共 **59 列**，結構化回傳為 **60 項**——差的那一項是把 R77-24 中的 `E-10`（root tools tier 逐檔議價）在結構化回傳裡**另立為 R77-60（P3, PKG-ARCH）**，以免 P1 複合項吞掉一筆 P3 而讓成本估計失真。兩處內容一致，refuter 以結構化回傳為準。

**覆蓋自檢**：上表逐 ID 點名 A-01~A-09(9)、B-01~B-07(7)、C-01~C-14(14)、D-01~D-10(10)、E-01~E-11+E-05b(12)、F-01~F-12(12)、G-01~G-12(12)、H-01~H-11(11)、N-01~N-13(13)、T-1~T-14(14)、W-01~W-11(11)、Q-01~Q-14(14) = **139 全數落點，零遺漏**。

---

## 6. 跨維共同形態（本輪最有價值的產出）

### 形態一｜**內部一致性被當成正確性：判準與它自稱的權威模型之間從來沒有機械連線**
- **B-02**：四處 `_RESERVED_RE` 的註解逐字自稱權威模型是 `git core.protectNTFS`，但 `COM0.txt` 在 git（兩次獨立拋棄式 repo）與 Win32 真機皆 ACCEPT，而四處全部 BLOCK；`LPT0` 正確**只是巧合**。守它的 `test_windows_forbidden_filename_parity.py` 驗的是「四處彼此一致」⇒ **四處一起錯結構上恆綠**。
- **B-07**：`logger.py:68` 的立案理由「保留裝置名在 Windows 上 `open()` 會拋 OSError」在本機 Windows 11 25H2 為假——三種 API（Python `open()`+iterdir／.NET `File.WriteAllText`／`cmd /c dir`）實測皆落地為真檔案。
- **E-11**：AC 現值住兩個家（鎖檔 47 自緊 vs ADR §4.2 散文 48），只有鎖檔那家被 `test_the_frozen_pair_matches_the_live_values` 綁住。
- ⇒ **對策方向**：凡「判準 vs 外部真相」的家族，必須有一個**外部 oracle 對拍測試**（B-01/B-02 共用 `git -c core.protectNTFS=true update-index --cacheinfo` 當 oracle 即可一次補上）。這與 R76 的「兩道鎖互為對方違規」是同一族的下一代：不是兩鎖互鎖，是**一群鎖互相取暖**。

### 形態二｜**單邊棘輪對「另一個方向的腐化」結構上失明，而那個方向正在動**
- **A-05**：drive-path 鎖 `tools/tests` floor=10 / actual=56 ⇒ **82% 掃描面可靜默蒸發而全綠**。姊妹鎖 `test_subprocess_encoding_hygiene.py:105-116` 早就把這個病診斷完並開好藥（雙邊帶＋`repin_ceiling`），**只餵給兩個病人中的一個**。
- **E-01+H-08**：`scan_h_problems()` 第三款只問 `glc_files > 0`，`glc_lines` 全程只被 `print`、零判準消費 ⇒ GLC 16 輪 26286→54188（**+106%**）而唯一通過判準全程綠、檔數恆 56。
- **Q-09**：`MIN_TESTS` 語意是收集數 `>= N`，對 skipped 零判準 ⇒ 同一棵樹同一個 commit 量出 **224/160/145/69 四個 skip 值，四次 rc 全 0**。
- **T-2**：7 條棘輪 slack≤1，其中 4 條（`_E501_DEBT_CEILING` 139/139、`_ENTRY_WAIVER_CEILING` 9/9、`_UNPINNED_HANDOVER_CEILING` 36/36、`_UNPINNED_CEILING` 8/8）**完全沒有預警帶**。
- ⇒ 每一個「只准變少」的棘輪都預設了「變多是安全的」，而 A-04（44 檔掃描面缺口）**實證掃描面確實會靜默縮小**。

### 形態三｜**制度在懲罰誠實：把新發現的缺口寫下來會讓閘門轉紅，於是最省力解是不要寫**
- **W-03+W-10**：`assertLessEqual(len(_IRON_LAW3_UNCOVERED), 4)` 把「還有幾類沒人守」（該只准變少）與「我們知道有幾類危害存在」（挖深就會變多、且是好事）綁成同一個數字。注入第 5 項當場 `AssertionError: 5 not less than or equal to 4` ⇒ R72~R76 五類已實證的新危害**一項都沒進去**。
- **W-01+Q-08**：本輪兩個新維度代號一旦寫進帳本或掃描發現檔，SC-7 當場紅並擋住每一次 push。R76 已用 `Scan-Q3` 發生過一次，靠「那份文件不在掃描面」（Q-07）**僥倖逃過**。
- **D-03+W-06**：M2「失實宣稱密度」的分子＝**四方複審抓到的筆數** ⇒ 不做複審＝分子 0＝完美達標。R72、R74 兩輪已實際發生（DEF-101-801 逐字「本輪四方複審未執行…因 session 額度上限中止」）。
- **Q-11**：29 支 AC matrix 佔位 skip 的函式體是 `pytest.fail(...)` ⇒ **想清這筆債的人會先吃一個紅**，債因此自我保存。
- **H-04**：R76 交棒書派給 R77 的**第一項工作**，在目標檔上只剩 1 行空間就撞 R76 自己新加的鎖（加 1 行 PASS／加 2 行 RED）。
- ⇒ 這是 R76「Scan-H⑥ 兩道鎖互為對方違規」的第二代，機制不同：**單一棘輪同時量了「世界的狀態」與「我們的認知範圍」**。對策一律是**拆成兩個量**（覆蓋率只准上升、分母允許長大）。

### 形態四｜**委派鏈是空的：兩邊各自宣告對方是兜底，實際兩邊都不跑；而登記表只驗形式不驗指涉**
- **N-12**：`pre-commit:347-353` 逐字「兜底改由 root-infra-ci.yml 第 1 道承擔」——而 root-infra-ci **73/100 從未啟動**（C-02）。
- **C-07+N-02**：Windows nightly 不跑根層 unittest，理由脈絡是「mac 那邊每天跑」；而 Windows 開發者看不到那台的結果，push 又走不到慢層（N-01）。
- **F-05**：repo 對「什麼只能等雲端」的**唯一登記表**，Windows 半邊指名兩個不存在的載具（`run_local_nightly.ps1` 內 `run_root_unittests` 命中 0），而被指名的檔案自己的檔頭**逐字否認**；守門 `test_named_local_carriers_actually_exist` 只驗「檔案存在」故恆綠。
- **Q-05**：skip reason 逐字「CI nightly 啟用」，`Grep hnsw .github/workflows` → `No matches found`；DEF-101-863 未來要立的**形式判準也會放行它**。
- **E-05+T-11+G-09**：8 筆「退場：未指派」，鎖 `:624` 自陳不驗輪號，其測試 `:1483` 拿不存在的 `R99` 當通過錨。
- **G-01+F-10**：85 筆未結列 36 筆走「未指派」出口；DEF-101-693 交棒給「下一個 Windows 真機輪」已過**六個** Windows 真機輪而閘門恆綠——判準只讀輪號字面，不看那句話裡的條件是否已成立。
- ⇒ 共同修法：**指涉必須被解析**（登記的載具要反查得到、交棒的條件要能判定是否成立、退場的輪號要能與 `current_round()` 比大小）。

---

## 7. 掌舵者八題的覆蓋自檢

| 題 | 覆蓋 | 主要工作項 | 誠實劃界 |
|---|---|---|---|
| **Q1** 全面掃描相容性 | ✅ 強 | R77-01/02/03/04/06/09/23/43/50/51/52 | **mac 真機零覆蓋**（12 維一致自陳）。mac 半邊全部是讀碼／POSIX 標準語意推論 |
| **Q2** 架構檢視與拿掉不合理機制 | ✅ 強 | R77-24（移除檔數棘輪／護欄層分家／tier registry）、R77-25（刪 28 凍結版，需核准）、R77-09（shim 抽 launcher）、R77-54（合併兩套釘選）、R77-20（dormant job） | Scan-E 給出 5 列減法清單，每列三段論齊全；**所有修法皆設計判斷未實作驗證** |
| **Q3** 雙向落差 | ✅ 中強 | R77-33（mac→Win 攔截率實測 0/10）、R77-45（交棒書方向寫反）、R77-52（150 站點 108 判不出方向）、R77-28（launchd 零對照組／兩 smoke 零對帳）、R77-48 | 雙向注入的「Win→mac」半邊有量測，「mac→Win」半邊的**執行期驗證**仍缺 mac 真機 <!-- xplat-rate-history: R77 動工前量測，現值見 CrossPlatform_Maturity_Criteria.md M5 列的載具 --> |
| **Q4** Windows 低級錯誤根因 | ✅ 強 | R77-45（n=36 重新歸因：LOCKBLIND 44%／CARRIER 只 19%）、R77-46（rc 管線方向相反）、R77-10（零觀測者）、R77-44（工具實為 pwsh 7.6.4）、R77-08 | 36 列的桶歸屬是**關鍵詞啟發式**，數量級可信、確切百分比不可引用為常數 |
| **Q5** 挖深與技術債 | ✅ 強 | R77-40（ruff 815/62/3485）、R77-57（依賴/孤兒/重複常數）、R77-25、R77-31/32（帳本）、R77-12/13（backlog 老化） | 未做 mypy／型別債／clone detection／覆蓋率債。「577 筆可自動修」是 ruff 自報值，未實跑驗證 |
| **Q6** 成熟度判準 | ✅ 強 | **M1~M6 六條全部被指出判準本身有問題**：M1→R77-24（GLC 零鑑別力）、M2→R77-19（獎勵不複審＋分母錯＋開場除以零）、M5→R77-33（語料零落點⇒結構上不可逐輪比較）、M6→R77-46（37 配方 25 無家＝首次基線）、另 R77-53（NOT-PROVEN 不可判定）、R77-29（GA 到期日與唯一槓桿） | M3/M4 沒有被單獨立案，只在 R77-46（session 稽核可自動化分子）間接觸及 |
| **S1** AutoClaude_Nightly 處置 | ✅ 有明確答案 | **不得退場，需補 3 個 stage**：root_unittests（R77-04）、pg-contract 本機鏡像（R77-05，邊際成本實測約 21 秒）、SDD 雙軌（R77-04）；另 R77-30（`--help`）、R77-29（GA 命中率是唯一槓桿，近 30 天只有 15/30） | 補 stage 需同步四處（summary 行／summary JSON／exit-decision／Format-Rc）並更新 `dev_start.py` 跨檔字面鎖 |
| **S2** WindowsSmoke 處置與**提權指令** | ⚠️ **半覆蓋** | 處置有答案：C-02 把 E1 從「一筆 billing」改寫成「19 天 373 筆 never-started」⇒ **smoke 排程明確不得退場**（Scan-C must_run 逐字）；R77-59 含 D-05（lifecycle 檔以硬編行號 `:99-127` 指向實際 `:90~:185` 的退場判準段，照 SOP 執行會漏改一半） | 🔴 **「提權指令」這一項十二維無一觸及**——沒有任何一維報告 elevated 執行條件、`fix_nightly_catchup.ps1` 的提權前提、或 `Register-ScheduledTask` 需不需要系統管理員。**這題掃描沒覆蓋到**，須另派或由執行包當場現查補上 |
| **S3** skipped 徹底解決 | ✅ 強 | 四組實測基線：出廠 **224**／主 .venv **160**／nightly **145**／最佳可達 **69**（另根層 unittest 43、SDD 側 11）。真黑洞 33 支（+TLC 4~6）。R77-05/18/36/37/39/56 | 未在雲端驗任何一筆；Q-04 的「那 15 支 nightly 真的跑了」是**算術對帳＋清單差集的強推論**，不是逐支 PASS 行 |

---

## 8. 給 refuter 的加壓建議（掃描者自己標為「推論而非量測」的清單）

按加壓價值排序：

1. **B-01 的入庫管道**：「mac/Linux 側 `core.protectNTFS` 預設不啟用」是 repo 自陳 ＋ 對 `-c protectNTFS=false` 的實測拼成，**不是對非 Windows 預設值的直接量測**。若該預設其實是 true，B-01 的入庫管道收窄為三條（`--no-verify`／GitHub web／未裝 hooks），嚴重度應下調。
2. **A-01**：「舵手那台 mac 的 PATH 上沒有 `python`」是推論。mac 真機一行 `command -v python` 即可定案。
3. **A-06**：「macOS `Path.resolve()` 不做大小寫正規化」是 POSIX `realpath(3)` 標準語意推論；Windows 側那一半是實測。
4. **C-02**：373 筆 never-started 只抽樣驗了 3 筆 annotation，其餘 370 筆用「duration ≤10s + failure」代理指標（已知有偽陽性：macos run 30695971121 duration 15s 但 steps=26 是真紅）。且 `--limit 100` 是視窗截斷，「自 07-14 起」是視窗下緣**不是停擺起點**。
5. **C-03**：「perf +72.7% 很可能是跨平台 baseline 污染」是推論；只證實了結構事實（`.perf_baseline.toml` tracked、只由 Windows 本機 nightly 寫）。
6. **F-12／R77-14** 的日期（約 2026-08-13/14）是三個實測值的算術，**不是對帳務何時恢復的預測**。
7. **W-07/A-02 的 cp950 分支**：用 cp1252 代打實測 rc=0。「真的會拋 UnicodeDecodeError 的 codepage 下會走到 fail-closed」是推論；但四條退化 payload 的 rc=2 是實測，立論不靠它。
8. **W-08 的百分比**（LOCKBLIND 44%／CARRIER 19%）是關鍵詞啟發式的人工分群；掃描者自陳「DEF-101-768 本是決策負荷根因列卻因含 CP950 被歸 BADPIPE」。
9. **E-09 的 52%／39.8%** 是引用次數比較的**啟發式**，看量級不宜當精確值。**E-10 混用兩種量法**（4358 是邏輯 LOC、8851 是 raw 行數，**不可相減**）。
10. **D-07** 是 Scan-D 唯一 `verified=false` 的一筆（唯讀紀律下未做注入實測）。
11. **H-06**：R76 的 4/31 與 Scan-H 的 111/376 是兩個**不可比**的啟發式；掃描者拒絕給「還剩幾支 NOT-PROVEN」的數字並論證該問題結構上不可回答——這個拒答本身值得複核。
12. **Scan-H 的 65 張豁免表只逐張驗了 2 張**，其餘 63 張用「同檔內有無 stale 語意測試」的弱啟發式，**跨檔的 stale 自檢會被誤判成沒有**（假陽性方向）。

---

## 9. 未被任何維度回報、但出現在覆蓋邊界裡的線索（不列 finding，供後續包留意）

- `AISDLC_SDD/scripts/tests` 本輪 **3 紅**（`dirname/mkdir: command not found`）——Scan-Q 自陳不在其射程、未追根因，**建議交 PKG-ACT 或 PKG-PRECOMMIT 當場現查**。
- `AutoClaude/logs/windows_smoke_2026-08-06_020035.log` 是本 session 另一個 agent 用 pwsh 7 呼叫 smoke 被 ENGINE-MISMATCH 守門擋下，**不是缺陷**（是守門有效的正向證據），別誤判歸屬。
- Scan-H 未能證實 R76 §6.2 的「34 處裸 assert 在 `python -O` 下會蒸發」宣稱：普查到 36 處**全部落在 tools/tests/**，非測試護欄程式碼 0 處。**只能說未證實，不能說該宣稱為假**。
- `file_state_repository.py:43` 的 `p.with_suffix(".tmp")` 對雙段副檔名只換最後一段——**行為正確、非缺陷**，Scan-B 已記在附錄避免下輪重查。
- 工作樹 144 支 `.sh` 是 CRLF——blob 全 LF、全部落在凍結版樹、活躍腳本 0 支、fresh checkout 實測拿到 LF。`test_pre_commit_dispatcher_sigpipe.py:149-155` 已逐字論證並刻意選擇看 index，**理由正確、不列為缺陷**。
