# R77 修復規劃書（12 包）

- 產出時間：2026-08-06
- 規劃者：R77 修復規劃官
- 輸入：`r77_triage.md`（60 工作項）＋ 對抗式複驗判決（49 筆 P0/P1：存活 38、證偽 11）＋ 未複驗 P2/P3 11 筆（R77-50~60）
- repo HEAD（本回合實查）：`a1ee537`
- 🔴 工作樹開場**非乾淨**：`git status --porcelain` 回三行——`docs/06_quality/AutoSDD_Defect_Log.md` M／`AutoSDD_Defect_Log_archive_INDEX.md` M／`AutoSDD_Defect_Log_archive_60.md` ??。另一個並行 agent 正在歸檔帳本，**PKG-03 不得在該 agent 交付前動工**。

---

## 0. 本回合實測的基線（所有驗收指令的比較基準，非引用他人宣稱）

| 量測 | 值 | 取得方式（本回合真跑） |
|---|---|---|
| 根層 unittest | `Ran 1979 tests in 243.878s` ／ `OK (skipped=43)` ／ rc=0 | `python tools/run_root_unittests.py` |
| `MIN_TESTS` | `1979`（`tools/run_root_unittests.py:58`） | Read |
| **餘裕（關鍵）** | 實況 1979 ＝ 下限 1979，**slack 0**；保鮮期 FAIL 線＝1979×1.25＝2473 | 上兩列相除 |
| 八支快層守門 | `check_script_parity` / `check_ntfs_paths` / `check_defect_log_crossref` / `check_wrapper_thinness` / `check_pytest_baseline_sites` / `check_gha_action_versions` / `archive_defect_log --check` / `sync_onboarding_baselines --check-snapshot` **rc 全 0** | 逐支真跑 |
| 根層護欄 ruff | `All checks passed!` rc=0 | `ruff check tools/ --no-cache` |
| 缺陷帳本未結列 | **85／全 104**，warn=86、fail=98；主檔 232,158 bytes | `check_defect_log_crossref.py --unresolved-count` |
| 護欄層棘輪（R77 當時＝**檔數**） | 凍結值 `53` vs `tools/tests/*.py` 磁碟實數 **56**。🔴 R78 ARCH-03：該檔數常數已於 R77 移除，接手者為 `TestGuardLayerRatchet` 的逐檔行數表 `_FROZEN_GUARD_LINES`（量的是**淨行數**）。本列保留為 R77 當回合的量測快照，**不是現行判準** | Grep ＋ 檔案計數 |
| ONBOARDING 快照（Windows 欄） | `autoclaude-pytest-snapshot: {'passed': 3919, 'skipped': 224}` | `sync_onboarding_baselines.py --check-snapshot` |
| **AISDLC_SDD/scripts/tests** | **rc=1，3 failed / 317 passed / 1 skipped**（triage §9 的線索，本回合現查坐實） | `python -m pytest AISDLC_SDD/scripts/tests -q` |

### 🔴 新立案 R77-61（本回合現查，不在原 60 項內）

`AISDLC_SDD/scripts/tests/test_copy_on_evolve.py::_bash_with_python()`（:234-263）把 **`usr/bin/bash.exe` 排在 `bin/bash.exe` 之前**當候選。`usr/bin/bash.exe` 通得過它自己那道 `command -v python` 探測（繼承 Windows PATH），卻**不會**把 Git 的 `/usr/bin` 併進 PATH ⇒ 腳本內的 coreutils 全部缺席。實測逐字：

```
127 = CompletedProcess(args=['C:\\Program Files\\Git\\usr\\bin\\bash.exe', 'scripts/copy_on_evolve.sh', ...])
scripts/copy_on_evolve.sh: line 81: mkdir: command not found
```

三支紅：`test_auto_syncs_skill_stamps_on_evolve_def_58_002`／`test_auto_appends_gitignore_block_on_evolve_def_59_001`／`test_auto_regens_framework_status_on_evolve_def_96_001`。
形態＝**同一份知識住兩個家、只有一個家被鎖**（repo 早有 SSOT `tools/lib/Find-GitBash.ps1`，R73 DEF-101-778 同型教訓）。歸 **PKG-06**。

---

## 1. 分派總表（存活 38 ＋ 未複驗 11 ＋ 新立 1 ＝ 50 筆的去向）

| 包 | order | 承載的 item |
|---|---|---|
| PKG-01-UNBLOCK | 1 | R77-07, R77-15, R77-44a, R77-45a, R77-46s, R77-53a, R77-53b, R77-59b |
| PKG-02-DOCTRUTH | 2 | R77-11, R77-16, R77-19, R77-21, R77-26s, R77-44b, R77-45b, R77-59a |
| PKG-03-LEDGER | 2 | R77-22, R77-31, R77-32, R77-53c |
| PKG-04-CROSSREF | 3 | R77-12, R77-39b, R77-53d, R77-59e |
| PKG-05-CI | 2 | R77-02, R77-06b, R77-14, R77-17, R77-20, R77-36, R77-38, R77-55 |
| PKG-06-CARRIER | 2 | R77-03, R77-43b, R77-50, R77-51, R77-61 |
| PKG-07-NIGHTLY | 2 | R77-04, R77-05s, R77-30 |
| PKG-08-ACT | 2 | R77-23, R77-47, R77-48, R77-49 |
| PKG-09-LOCKS | 2 | R77-18, R77-33, R77-52, R77-56a |
| PKG-10-PARITY | 2 | R77-13, R77-54 |
| PKG-11-SKIPGOV | 2 | R77-37, R77-39a, R77-56b |
| PKG-12-DEBT | 2 | R77-57, R77-58 |
| — 需拍板 | — | R77-06a, R77-08, R77-10, R77-24, R77-25, R77-60 |
| — 刻意不修 | — | R77-01, R77-05h, R77-09, R77-26h, R77-27, R77-28, R77-29, R77-34, R77-35, R77-40, R77-41, R77-42, R77-43a, R77-46h, R77-47① |

字尾：`a/b/c/d/e`＝同一 item 依檔案歸屬拆到不同包；`s`＝證偽項中可救的那一半（salvage）；`h`＝該項的 headline 主張（已證偽或無安全修法）。

---

## 2. 檔案擁有權（**逐包互斥，零交集**）

**全域規則（每包都適用，寫進 must_not_touch）**
1. 只准動自己 `files_touched` 列出的檔。要動別包的檔＝寫進交件回報，不要自己改。
2. 🔴 **R78 ARCH-03 訂正（原文已作廢，勿照做）**：本條原本寫「不得在 `tools/tests/` 新增檔案——`_FROZEN_GUARD_FILE_COUNT = 53` 是 shrink-only 棘輪」。那個常數在 R77 同輪就被刪了（全庫零賦值定義），**接手者是逐檔行數棘輪** `tools/tests/test_adr_xplat001_c1c2_lock.py::TestGuardLayerRatchet`（`_FROZEN_GUARD_LINES`）。現行規則：**`tools/tests/` 的淨行數不得上升**（DEF-101-561③）——新增檔案本身**不**違規，只要同一次變更內刪掉等量以上的行；反之只改既有巨檔卻淨增一行照樣紅。仍**優先**併進既有檔（那是成本最低的合法路徑），但不要拿一個不存在的理由砍掉設計選項。重釘須跑 `--print-guard-lines` 並在 `_GUARD_LINES_REPIN_LOG` 補一列（含淨額與理由）。
3. **不得刪除任何測試**：根層實況 1979 ＝ `MIN_TESTS` 1979，**slack 0**，刪一支當場紅。新增測試上限到 2473（保鮮期 FAIL 線）。
4. **不得重釘 `MIN_TESTS`**：那是收尾包在所有包停工後的動作，任一修復包重釘都會製造中途值（DEF-101-701 已列舉七次前例）。
5. **只有 PKG-03 可以寫缺陷帳本**（`AutoSDD_Defect_Log*.md`）。其他包要新增／結掉的列，寫成交件回報交給 PKG-03 統一落列。
6. **只有 PKG-01 可以編輯根 `CLAUDE.md`**。其他包若因新增機械物而需要改鐵律三那張表，把該列的**確切新文字**寫進交件回報，由收尾包套用（維持表與 `_IRON_LAW3_UNCOVERED` 一致就不會紅）。
7. 禁 `--no-verify`、禁 `AUTOCLAUDE_SKIP_HOOKS=1`、禁跳過或註解掉失敗測試。
8. 禁為了讓數字好看調高任何門檻／棘輪／體積上限；棘輪只准變少。**GA 的 `WINDOW_SPAN_MAX_FACTOR` 與 `STALENESS_MAX_DAYS` 明令不得放寬。**
9. 禁用 `--allow-pg-extras` 繞過 `sync_onboarding_baselines.py --write` 的拒跑。
10. 帳本列禁半形直線符號、單列 ≤700 bytes、詳情進具名證據檔。
11. 訂正註記**不得逐字抄錄被訂正的假話**；要讓機器解析的字串寫進 docstring 或字串字面值，不要寫在註解或錨定行上。
12. 禁動凍結版目錄 `AISDLC_SDD/AISDLC_SDD_v0.01` ~ `v0.29`（Copy-on-Evolve）。
13. 禁動 PreToolUse deny 面：`.claude/settings.json`、`.claude/hooks/**`、`AutoClaude/.claude/settings.json`、`AISDLC_SDD/AISDLC_SDD_v0.30/.claude/settings.json`。**任何 hook 註冊面變動一律需拍板**（repo 有「hook 誤觸 deny 把所有工具硬鎖死」的 P0 判例）。

---

## 3. 逐包規格

### PKG-01-UNBLOCK（order 1，**必須先單獨完成並 commit，其他包才動工**）

- **scope**：解開兩道會擋住本輪其他所有包的結構鎖，並訂正根 CLAUDE.md 三筆已證偽/過期的宣稱。
- **files_touched**
  - `CLAUDE.md`
  - `docs/06_quality/CrossPlatform_Scan_Dimensions.md`
  - `tools/tests/test_doc_loc_baseline_freshness_r60.py`
- **做什麼**
  1. **R77-07**：在維度表新增 `Scan-W`、`Scan-Q` 兩列。三個硬形式：①符合 `_SCAN_DEFINED_RE = r'^\| \*\*(Scan-[A-Z])\*\*'`（雙星號、行首無縮排）；②落在 `scan_table_lines()` 的**同一段連續 `|` 區塊**內（遇第一個非 `|` 起頭行即停，R68 被空行截斷過）；③代號**只能是單一大寫字母**——`_SCAN_CODE_RE` 會把 `Scan-Q3` 讀成 `Scan-Q`，別再造帶數字的變體。
  2. **R77-15**：把 `assertLessEqual(len(_IRON_LAW3_UNCOVERED), 4)`（:3234）拆成**兩個量**：分子（覆蓋數，只准上升）與分母（已知危害類數，允許長大）。同步 `_IRON_LAW3_TOPIC_KEYWORDS`——`test_topic_pairing_surface_is_non_empty`（:3266-3268）斷言 `{pairs 的主題鍵} == set(_IRON_LAW3_TOPIC_KEYWORDS)`，**具名機械物的新列**必須同步該常數；標「無機械物」的新列只需同步 `_IRON_LAW3_UNCOVERED`。
  3. **R77-53a**：`CrossPlatform_Scan_Dimensions.md:75` 散文寫死的數字改成**現查指令**（ADR-XPLAT-002 §8 表頭規則 3：完成判準欄禁寫死量測常數）。
  4. **R77-53b**：`test_doc_loc_baseline_freshness_r60.py:4479-4495` 的退場判準掃描面補 `.md`。
  5. **R77-44a**：把「PowerShell 工具＝原生 5.1」這個**理由**改寫成實況（工具側實為 pwsh 7.6.4，排程側才是 5.1）。**保留鐵律一的 Bash 禁令本身**，只改理由，並補一句「引擎敏感的驗證一律顯式 `powershell.exe -NoProfile -File`」。
  6. **R77-45a**：訂正根因 n=8 模型、mac→Win 方向對調兩筆。
  7. **R77-46s**：「讀 rc 禁接管線」的**理由**改寫為：pwsh 7 提前中斷管線時不更新 `$LASTEXITCODE`（保留前值）、PS 5.1 則寫入 -1，兩者都讓 rc 不可信。操作規則本身不變。
  8. **R77-59b**：`CLAUDE.md:226` 的寫死行號改成可解析的錨（節標題／符號名），不要寫行號。
- **must_not_touch**：其他 11 包的任何檔；`ONBOARDING.md`；`docs/04_planning/**`；缺陷帳本；`AISDLC_SDD/AISDLC_SDD_v0.0*`~`v0.29`；PreToolUse deny 面。**不得為了讓鐵律三那張表好看而把「無機械物」列刪掉**——只有真的補了掃描器才准改該列，且具名檔案必須真的在守該列主題（`TestR75IronLawMechanismSubstance` 會驗）。**不得在訂正註記裡逐字抄錄被訂正的假話**（R73 被自己的鎖抓 5 次的形態）。
- **acceptance**（PowerShell，前置：`$env:PYTHONUTF8='1'; $env:PYTHONDONTWRITEBYTECODE='1'; $py='D:\CursorProject\AISDCL_Agent\.venv\Scripts\python.exe'`）
  1. `Push-Location 'D:\CursorProject\AISDCL_Agent'; & $py tools\run_root_unittests.py; "rc=$LASTEXITCODE"; Pop-Location` → **rc=0**，且輸出含 `✅ unittest 數量下限釘選通過：發現 1979 個測試`（若你新增了測試，數字須 ≥1979 且 ≤2473）
  2. `& $py tools\check_defect_log_crossref.py` → **rc=0**（SC-7 維度代號鎖在此支）
  3. `& $py tools\check_pytest_baseline_sites.py` → **rc=0**
  4. **注入自檢（證明 R77-15 真的解開了）**：暫時往 `_IRON_LAW3_UNCOVERED` 塞第 5 筆並跑第 1 條 → 必須 **rc=0**（改前實測是 `AssertionError: 5 not less than or equal to 4`）；驗完**還原**。
- **parallel_safe_with**：無（本包獨佔 order 1）

---

### PKG-02-DOCTRUTH（order 2）

- **scope**：ONBOARDING 雲端錨與 provenance 欄、ADR/交棒書/成熟度表三處失實宣稱。
- **files_touched**
  - `ONBOARDING.md`
  - `tools/sync_onboarding_baselines.py`、`tools/lib/baseline_origin.py`
  - `docs/04_planning/R76_HANDOFF.md`、`docs/04_planning/ADR/**`
  - `docs/06_quality/CrossPlatform_R76_Scan_Findings.md`、`docs/06_quality/Scheduled_Jobs_Lifecycle_Review_R75.md`
  - `AISDLC_SDD/CLAUDE.md`
- **做什麼**
  1. **R77-11**：補 provenance 兩欄（直譯器／sdk_extra）。**先瘦身再加**：欄位常數本體住 `tools/lib/baseline_origin.py`（不在 `SPECIAL_FILES` 內、無額度壓力）；真正吃額度的是 `sync_onboarding_baselines.py` 的 `measure_provenance()` 每欄 1 行 ⇒ 補 2 欄＝2 行＝RED，**必須先在該檔瘦身 ≥2 行**。實測門檻：加 1 行 PASS、加 2 行 RED。🔴 **禁止走「調高 SPECIAL_FILES 上限」**（鎖訊息 :2564-2565 逐字「那是砸溫度計」）。
  2. **R77-16**：訂正 ONBOARDING 散文。🔴 **絕不可**在 `cloud-ci-status:` 那一行的說明文字裡寫出 `measured-at=<值>` 形態——`_CLOUD_FIELD_RE` 會把它當欄位解析、`parse_cloud_fields` 對重複鍵 fail-loud（R75 已踩兩次）。要寫成「本錨的 `measured-at` 欄」。
  3. **R77-21**：雲端結論錨回填。33 支判準在守：`red=` 必須逐字對上表格 failure 列；`pending`（若填）須是真 commit、HEAD 祖先且 head-sha 後代；`head-sha` 須真 commit＋HEAD 祖先＋與 `checked-at` 因果一致；**同一行散文不得出現任何可解析的 `欄位=值` 字樣**。🔴 **絕不可**把判準改成「比 `origin/main`」——那正是 R75 的 P0（判準的比較對象隨被它所判的動作而改變，結構上每次 push 必紅）。錨與 §7 表③ 必須同一個 commit 改。
  4. **R77-19**：`CrossPlatform_R76_Scan_Findings.md` 的 M2 格：分母寫死 25 而實測 36/37。若改成機械量測，**判準必須雙邊帶**——crossref 的「當前輪」刻意 fail-open 落後一輪、輪初分母恆 0，單邊判準在開輪當下結構上不可滿足（R75「下限型判準要雙邊帶」）。體積餘裕充足（102,414／262,144）。
  5. **R77-26s**：ADR §4.2 把寫死的 `48/18` 換成**現查指令**（不要改寫成 47——下一輪照樣漂移）。
  6. **R77-44b / R77-45b**：ONBOARDING 與交棒書兩處同款失實宣稱同步訂正（與 PKG-01 的 CLAUDE.md 半邊說法必須一致）。
  7. **R77-59a**：lifecycle 文件五處失實／脆弱錨（`:475,556,561,644,657`）——指向已刪檔、硬編行號 `:99-127` 實際落在 `:90~:185`、兩處顏色/日期快照。行號一律換成可解析的錨。
- **must_not_touch**：`CLAUDE.md`（PKG-01）；`docs/06_quality/CrossPlatform_Scan_Dimensions.md`（PKG-01）；`tools/check_pytest_baseline_sites.py`（PKG-04）；缺陷帳本；`tools/tests/**`；凍結版目錄；PreToolUse deny 面。🔴 **禁止用 `--allow-pg-extras` 繞過 `--write` 拒跑**。R76_HANDOFF.md 有前科（DEF-101-868：斷鏈 ID 引用＋占位形站點上限 5>4 讓兩道根層鎖轉紅），改它前後都要跑根層 unittest。
- **acceptance**
  1. `& $py tools\sync_onboarding_baselines.py --check-snapshot` → **rc=0**
  2. `& $py tools\check_defect_log_crossref.py` → **rc=0**（含指針稽核＋體積守門）
  3. `& $py tools\run_root_unittests.py` → **rc=0**（雲端錨 33 支判準、doc 基線鎖都在這棵樹）
  4. `& $py tools\check_pytest_baseline_sites.py` → **rc=0**（只讀不改，確認沒被你的文字編輯掃到）
- **parallel_safe_with**：PKG-03, PKG-05, PKG-06, PKG-07, PKG-08, PKG-09, PKG-10, PKG-11, PKG-12

---

### PKG-03-LEDGER（order 2；**外部前置：等另一個 agent 的歸檔工作 commit 完才動工**）

- **scope**：缺陷帳本內容修復＋歸檔器判準。本輪**唯一**能寫帳本的包。
- **files_touched**
  - `docs/06_quality/AutoSDD_Defect_Log.md`
  - `docs/06_quality/AutoSDD_Defect_Log_archive_*.md`、`docs/06_quality/AutoSDD_Defect_Log_archive_INDEX.md`
  - `tools/archive_defect_log.py`、`tools/tests/test_archive_defect_log.py`
- **做什麼**
  1. **R77-31**：六筆死信／錯配／零載體。**互鎖**：重開 726 會讓未結 85→86＝正好踩 warn 線（warn 非阻塞）；結掉 550 給 84 ⇒ **兩件都做淨回 85**。
  2. **R77-32**：真的把列結掉（現況 85／warn 86／fail 98）。🔴 **歸檔不會降低此數**（工具自己每次都印這句）；唯一出路是結列或改派具名承接者。**本輪其他包若要新增未結列，總數不得超過 97**（fail=98）。
  3. **R77-22**：DEF-101-834 的訂正。🔴 **不可就地改 `archive_60.md`**——`conservation_problems()` 的位元組守恆會擋（該檔 :294 逐字）。訂正以**主檔新列**承載，並確保跨檔狀態不矛盾（`--check` 判準 3）。
  4. **R77-53c**：`archive_defect_log.py:222,425` 的 `NOT-PROVEN` 目前無可判定定義——補上可機械判定的定義（或明文改成「本欄不可機械判定，只作人工註記」並讓判準不再消費它）。
- **must_not_touch**：`tools/check_defect_log_crossref.py`／`tools/tests/test_check_defect_log_crossref.py`（PKG-04）；任何非帳本檔。帳本列**禁半形直線符號**、單列 ≤700 bytes、詳情進具名證據檔。**不得為了讓未結數好看而把列改成假的狀態字**（R74 的帳本死結真相＝判準把 `fail-open` 當活躍狀態字）。
- **acceptance**
  1. `& $py tools\check_defect_log_crossref.py` → **rc=0**
  2. `& $py tools\archive_defect_log.py --check` → **rc=0**
  3. `& $py tools\check_defect_log_crossref.py --unresolved-count` → 印出的未結數**必須 ≤ 85**（動工前 85；本包的職責是往下走，不是持平）
  4. `& $py tools\run_root_unittests.py` → **rc=0**
- **parallel_safe_with**：PKG-02, PKG-05, PKG-06, PKG-07, PKG-08, PKG-09, PKG-10, PKG-11, PKG-12（**與 PKG-04 序列化**）

---

### PKG-04-CROSSREF（order 3；**前置：PKG-11 與 PKG-03 都已 commit**）

- **scope**：帳本判準本體＋兩張登記表的登記動作。
- **files_touched**
  - `tools/check_defect_log_crossref.py`、`tools/tests/test_check_defect_log_crossref.py`
  - `tools/check_pytest_baseline_sites.py`
- **做什麼**
  1. **R77-12**：承接稽核只覆蓋 15%、條件式交棒判準只讀輪號字面。🔴 **必須照既有判例走「釘現況＋只硬擋新增列」**——程式碼自己在 `:592-596` 記著 ARCH-R59-NB4「一次全紅＝閘門上線即永紅，而永紅的閘門會被整個關掉，比沒有鎖更糟」；直接上新判準會讓 36 筆同時翻紅。第二個硬約束：`test_shipped_ceiling_matches_the_shipped_whitelist`（:1816）釘死 `ceiling == len(whitelist)` **相等**（不是 ≤）。
  2. **R77-39b**：把 `docs/06_quality/Skipped_Test_Inventory_R76.md` 登記進 `_GOVERNANCE_DOCS`（:1131-1150）與 `check_pytest_baseline_sites._SCAN_FILES`。⚠️ **兩個前置都必須先成立**：①PKG-01 已定義 `Scan-Q`（否則 SC-7 當場紅）；②PKG-11 已把該檔 18 行過期基線 claim 補上標記（否則 baseline-sites 當場紅）。**任一前置未成立就不要登記**，把原因寫進交件回報。
  3. **R77-53d**：`test_check_defect_log_crossref.py:2453` 退場判準掃描面漏 `.md`。
  4. **R77-59e**：`check_pytest_baseline_sites.py:58-69` 的寫死行號／掃描面換成可解析的錨。
- **must_not_touch**：帳本 `.md`（PKG-03）；`tools/archive_defect_log.py`（PKG-03）；`docs/06_quality/Skipped_Test_Inventory_R76.md`（PKG-11）。🔴 **不得上修任何 ceiling 製造餘裕**——`crossref:721` 逐字「只准變小：新的未結列請走硬規則② 的兩條合法出口，**不是**把它加進豁免名單」。
- **acceptance**
  1. `& $py tools\check_defect_log_crossref.py` → **rc=0**
  2. `& $py tools\check_pytest_baseline_sites.py` → **rc=0**
  3. `& $py tools\run_root_unittests.py` → **rc=0**
  4. **永紅自檢**：把 `git stash` 過的動工前帳本還原後再跑第 1 條 → 仍 **rc=0**（證明新判準不是「上線即全紅」）
- **parallel_safe_with**：PKG-02, PKG-05, PKG-06, PKG-07, PKG-08, PKG-09, PKG-10, PKG-12

---

### PKG-05-CI（order 2）

- **scope**：GitHub workflows 本體＋雲端可用性量測工具。
- **files_touched**
  - `.github/workflows/**`（11 支 yml）
  - `tools/lib/ci_liveness.py`
  - `tools/check_gha_action_versions.py`、`tools/tests/test_gha_action_versions.py`
  - `tools/tests/test_workflow_permission_concurrency_lock.py`、`tools/tests/test_workflow_schedule_sync.py`
- **做什麼**
  1. **R77-02**：在 `tools/tests/test_gha_action_versions.py` **內**（不新增檔案）加 `runs-on` 標籤白名單掃描（`ubuntu-latest`／`ubuntu-24.04`／`ubuntu-22.04`／`windows-latest`／`macos-latest`）。純新增測試、不動生產路徑。⚠️ 同檔 `TestWindowsCiHeaderSnapshotLock` 會從 `windows-compat-ci.yml` 檔頭註解表反算 runs-on 分佈並斷言相等——你若順手改任何 workflow 的 runs-on，**必須同步該檔頭表**。
  2. **R77-06b**：`ci_liveness` 看不見 push 軌。(a) **不要**塞進 `scheduled_workflow_periods()` 那條路——無 cron 的 workflow 沒有 `cron_period_days`，塞進去無值；另開「push 閘 never-started 比率」判準。(b) 只讀 `gh`、不寫 repo。(c) 帳務停擺期間 `gh` 查詢可能拿到截斷視窗，判準要對「視窗下緣≠停擺起點」誠實劃界。
  3. **R77-14**：訂正 root-infra 第 15 道哨兵的 `WAIVER_REASON` **文字**（須保留 `DEF-\d{3}-\d{3}` 形態，`test_waiver_declares_deadline_and_reason` 會驗；`_WAIVER_RE` 釘死 10 空格縮排）。🔴 **不要**把 `WAIVER_UNTIL` 清成 `""`（合法終態但拆掉安全網，約 08-14 起 age>10 會讓**每次 push** 硬紅＝R68 死鎖形狀）。🔴 若要把哨兵改讀 job 層，`_QUERY_LOOP_RE` 要求該 step 內 `for wf in …; do` **恰好一個**。
  4. **R77-17**：`check_gha_action_versions.py` 改 accumulate-then-report（現況第一筆就 return，紅印在第 1 行後接 12 行綠）。測試只斷言 rc（:171/179/187），不釘輸出行數或順序。須保留 `nested_action_generation` 的 `OSError try/except`，並確保 `_WORKFLOWS_DIR != 真根目錄`（單元測試 fixture 注入）時仍跳過第一段。LOC 266/750，加 20~30 行零壓力。
  5. **R77-20**：dormant job 改名（`test_workflow_schedule_sync.py` 只綁「cron 字串 ↔ job if 字串」兩個集合，不綁 name ⇒ 改名不紅）。🔴 **若要啟用 04:00/05:00 cron**，判準 2（每條 schedule cron 必須被至少一個 if 引用）會當場紅——cron 與 if 必須同 commit 改。動 `macos-compat-ci` 的 job name 前先查 `test_workflow_permission_concurrency_lock.py`。
  6. **R77-36**：pg-contract 155 支零下限斷言 → 在 workflow 加 count 斷言。已驗互鎖不咬：`check_pytest_baseline_sites.py` 只掃 6 份 CLAUDE/README/ONBOARDING 家族檔，`.github/workflows` 在其掃描面之外。
  7. **R77-38**：把 workflow `:12` 那句「仍留 nightly」的註解**改誠實**（五軌 TLC 其實零自動通道）。既有鎖是 paths 覆蓋鎖與 gha-action-versions，都不看註解文字。🔴 **另一半（真的建 nightly TLC 通道）不做**——見 §5。
  8. **R77-55**：兩支 SDD workflow 的 concurrency 群組不分事件（`aisdlc-sdd-ci.yml:71-73`、`aisdlc-sdd-arch-fitness.yml:52-54`，修過三次仍活著）＋compat-CI 的 paths 對家清單手抄無鎖（`test_workflow_permission_concurrency_lock.py:53-57`）。paths 鎖與 yml 必須同 commit。
- **must_not_touch**：`tools/tests/test_smoke_ci_sync.py`（PKG-08）；`AutoClaude/tools/run_act*`／`.actrc`（PKG-08）；`tools/check_pytest_baseline_sites.py`（PKG-04）；`tools/git-hooks/**`（PKG-06）。🔴 **不得為了讓地端載具好看而從 `autoclaude-ci.yml` 拿掉 pg-contract 的 services**（那是明文硬閘，拆它＝砸溫度計）。🔴 **不得新增 schedule job**（帳務停擺中，且會落進 root-infra-ci 的擁擠時段）。**不得放寬 `MAX_AGE_DAYS`**。
- **acceptance**
  1. `& $py tools\check_gha_action_versions.py` → **rc=0**
  2. `& $py tools\run_root_unittests.py` → **rc=0**（三支 workflow 鎖都在這棵樹）
  3. **R77-17 鑑別力自檢**：暫時在某支 workflow 塞第二種 `actions/checkout` 版本 → 第 1 條必須 **rc=1 且一次印出全部不一致項**（改前只印第一筆）；驗完還原。
  4. `& $py -c "import sys;sys.path.insert(0,r'D:\CursorProject\AISDCL_Agent\tools');import lib.ci_liveness"` → **rc=0**（語法/匯入）
- **parallel_safe_with**：PKG-02, PKG-03, PKG-04, PKG-06, PKG-07, PKG-08, PKG-09, PKG-10, PKG-11, PKG-12

---

### PKG-06-CARRIER（order 2）

- **scope**：本機 hook／pre-commit／pre-push 載具層＋保留裝置名判準＋Git Bash 解析 SSOT。
- **files_touched**
  - `tools/git-hooks/pre-commit`、`tools/git-hooks/pre-push`
  - `tools/tests/test_pre_push_dispatcher.py`、`tools/tests/test_pre_commit_dispatcher_sigpipe.py`
  - `tools/check_ntfs_paths.py`、`tools/tests/test_windows_forbidden_filename_parity.py`、`tools/tests/test_windowsapps_guard_bash_parity.py`
  - `AISDLC_SDD/scripts/component_sanitizer.py`、`AISDLC_SDD/scripts/tests/test_copy_on_evolve.py`
  - `AutoClaude/autoclaude/utils/logger.py`
  - `AutoClaude/tools/hooks/enforce_docs_path.py`、`AutoClaude/tools/hooks/check_sh_eol.py`
- **做什麼**
  1. **R77-61（新立，先做——它現在就是紅的）**：`test_copy_on_evolve.py::_bash_with_python()` 的候選順序改為 `bin/bash.exe` 優先，或直接改用 repo 既有 SSOT 的解析結果。探測條件要同時驗 `command -v python` **與** `command -v mkdir`（現行探測通得過卻仍缺 coreutils，正是它今天放行 rc=127 的原因）。
  2. **R77-03**：pre-push 慢層對「只改子專案」不觸發，89~98% 掃描面在盲區。🔴 **不要**把慢層改成任何 push 都跑——會直接踩翻 `test_pre_push_dispatcher.py:498` 的 `assertFalse`，且該鎖的 WHY 有實據（111.89s × 每次子專案 push，逼出 `--no-verify` 就全線蒸發）。**走第三條路**：只把四支跨平台掃描器（`test_platform_neutral_paths`／`test_subprocess_encoding_hygiene`／`test_ps51_compat`／`test_pre_commit_dispatcher_sigpipe`）提到快層。**動工前先量這四支的耗時**；若合計新增 >20s，停下來回報、不要硬上。
  3. **R77-50**：`enforce_docs_path.py:66-90` 與 `check_sh_eol.py:107-116` 的 `Path.resolve()` 大小寫正規化只在 Windows 發生 ⇒ 兩支 exit-2 阻斷級 hook 在兩平台給出方向相反的錯。⚠️ 這兩支是 exit-2 阻斷級，**改動前先在拋棄式輸入上驗四種 rc**（正常路徑 / 越界路徑 / 壞 JSON / 空 stdin），把矩陣貼進交件回報。**不得改變它們的註冊面**（只改判準內部）。
  4. **R77-51**：保留裝置名判準與其自稱的權威模型三處不符。可安全做的：①`logger.py:68` 的**立案理由**訂正（「保留裝置名在 Windows 上 `open()` 會拋 OSError」在 Win11 25H2 實測為假）；②`pre-commit:347-353` 的「兜底改由 root-infra-ci.yml 第 1 道承擔」訂正（該 workflow 73/100 從未啟動）。🔴 **不要動四處 `_RESERVED_RE` 的正則**：`test_windows_forbidden_filename_parity.py` 要求四處逐字相同＋錨①（CON/PRN/AUX/NUL 相鄰、間隙 ≤5 字元、新名一律加尾端），只改一處即紅；且 `LEADING_SPACE_RESERVED_SEGMENTS` 樣本電池要求 validator 必須放行前導空白形態。COM0 過攔／上標變體那兩筆**需拍板**（見 §4）。
  5. **R77-43b**：`.ps1` 的 **BOM** 無 commit 層閘 → 補上（BOM 是 blob 層事實，看暫存區就判得出來，不違反 pre-commit「看暫存區 blob 不看工作樹」原則）。🔴 **CRLF 那一半不做**（見 §5）。
- **must_not_touch**：`tools/lib/GitHooksInstallCommon.ps1`／`tools/git_hooks_install_common.py`（PKG-10）；`tools/tests/test_platform_neutral_paths.py`／`test_subprocess_encoding_hygiene.py`／`test_ps51_compat.py`（PKG-09——你只在 pre-push 裡**引用**它們的檔名，不得編輯其內容）；`.claude/**`、`AutoClaude/.claude/**`（deny 面）；`AISDLC_SDD/AISDLC_SDD_v0.0*`~`v0.29`。🔴 **不得用 `git add --renormalize` 改 `.ps1` 位元組**（index 恆 LF、產生零 diff，只會改本機工作樹，不是可入庫的修復）。
- **acceptance**
  1. `Push-Location 'D:\CursorProject\AISDCL_Agent'; & $py -m pytest AISDLC_SDD/scripts/tests -q; "rc=$LASTEXITCODE"; Pop-Location` → **rc=0**（動工前實測 rc=1／3 failed／317 passed；驗收要求 320 passed、0 failed）
  2. `& $py tools\run_root_unittests.py` → **rc=0**
  3. `& $py tools\check_ntfs_paths.py` → **rc=0**
  4. **pre-push 快層耗時實測**：改造後跑一次快層並貼出牆鐘秒數；新增耗時 ≤20s
  5. **hook rc 矩陣**：對兩支 exit-2 hook 各餵 4 種輸入，貼出 rc（不得有任何一種從 0 變 2 或從 2 變 0，除非那正是修復標的並已說明）
- **parallel_safe_with**：PKG-02, PKG-03, PKG-04, PKG-05, PKG-07, PKG-08, PKG-10, PKG-11, PKG-12（**與 PKG-09 序列化**：兩包都在動 pre-push 快層引用的那四支掃描器的**存在性**，PKG-09 先 commit 再讓 PKG-06 接線）

---

### PKG-07-NIGHTLY（order 2）

- **scope**：本機 nightly／smoke 的覆蓋缺口與 CLI 契約。
- **files_touched**
  - `AutoClaude/tools/run_local_nightly.ps1`、`AutoClaude/tools/run_local_nightly.sh`
  - `tools/windows_smoke_local.ps1`、`tools/macos_smoke_local.sh`
  - `tools/dev_start.py`
  - `AutoClaude/tests/tools/test_run_local_nightly_static.py`
  - `tools/tests/test_schedule_capability_parity.py`
- **做什麼**
  1. **R77-04**：Windows nightly／smoke 皆不跑根層 unittest。🔴 **不要新增 stage**——新增 stage 要同步四處（summary 行／summary JSON／exit-decision 清單／`Format-Rc` 標籤），而 summary 行被 `tools/dev_start.py` 以**跨檔字面正則**解析（DEF-101-263②／R25 跨檔字面鎖），改契約會連帶弄紅那組鎖。**把 `python tools/run_root_unittests.py` 掛進既有的 `local_ci_gate` stage 內**，summary 契約完全不動。若實作上不可行，**停手回報，改走拍板**（見 §4）。
  2. **R77-05s**（證偽項的可救半）：🔴 **不可**把 DSN 設定搬到 Stage L 之前（`:985-986` 的順序是刻意的；`:1051-1052` 明載 pg-e2e stage 自己會在 alembic 後 swap 成 asyncpg DSN，提前設會撞 `MissingGreenlet`）。**正解**＝在既有 pg-e2e stage（`:1190`）內把選擇面從目前兩支擴到 `tests/contract/test_alembic_*.py`——那時 DSN 已就緒、不動 summary 契約、不新增 stage。
  3. **R77-30**：`--help` 直接開跑 7 stage nightly。檔頂補 `param([switch]$Help)`。已實測：PS 5.1 下 `-File x.ps1 --help` → `USAGE-PRINTED rc=0`（PowerShell 對 `--Help` 做前綴比對）；但它**不會**拒絕未知引數（`--forse` → 照樣開跑），所以還要加一段 leftover-args 檢查。家族共 11 支 .ps1，`windows_smoke_local.ps1` 同形態零登記，一併處理。
- **must_not_touch**：`AutoClaude/tools/ga_window.py`／`observability_snapshot.py`／`drift_log_snapshot.py`（本輪不動，見 §5）；`tools/scheduled_task_expectations.json`、`tools/install_*_nightly.*`（本輪不動）；`.github/workflows/**`（PKG-05）；`AutoClaude/tools/run_act*`（PKG-08）；`AutoClaude/tests/**` 除 `tests/tools/test_run_local_nightly_static.py`（PKG-11/PKG-12）。🔴 **不得放寬 GA 的 `WINDOW_SPAN_MAX_FACTOR`／`STALENESS_MAX_DAYS`**。🔴 **不得回填舊日期的量測紀錄**去補 GA 視窗（＝捏造量測）。🔴 **不得改 nightly summary 行／JSON 的字面契約**。
- **acceptance**
  1. `& $py tools\run_root_unittests.py` → **rc=0**（`test_schedule_capability_parity` 在此樹）
  2. `Push-Location 'D:\CursorProject\AISDCL_Agent\AutoClaude'; & $py -m pytest tests/tools/test_run_local_nightly_static.py -q; "rc=$LASTEXITCODE"; Pop-Location` → **rc=0**
  3. **`--help` 契約實測**（四種輸入，貼出逐行 rc）：`powershell.exe -NoProfile -File <script> --help` → rc=0 且**未開跑**；`-Help` → rc=0 未開跑；`--forse`（未知引數）→ **rc≠0** 且未開跑；無引數 → 正常開跑
  4. **R77-04 鑑別力自檢**：故意讓 `tools/tests` 某支失敗，跑 `local_ci_gate` stage → 該 stage 必須 **rc≠0**（證明真的接上了，不是宣告有、執行者無）；驗完還原
- **parallel_safe_with**：PKG-02, PKG-03, PKG-04, PKG-05, PKG-06, PKG-08, PKG-09, PKG-10, PKG-11, PKG-12

---

### PKG-08-ACT（order 2）

- **scope**：act 地端 CI 載具的假綠與覆蓋缺口。
- **files_touched**
  - `.actrc`
  - `AutoClaude/tools/run_act_core.py`、`AutoClaude/tools/run_act.ps1`、`AutoClaude/tools/run_act.sh`
  - `tools/tests/test_smoke_ci_sync.py`
- **做什麼**
  1. **R77-49**：薄殼寫死 workflow，只看得到 9／25 個 job。🔴 掃描結論「薄殼原本就 `"$@"` 全轉，不需動」**只對一半**：`run_act.sh:24` 是 `python "$SCRIPT_DIR/run_act_core.py" "$@"`（真全轉），`run_act.ps1:51-55` 則是**顯式 param 映射**（不是全轉）⇒ 兩支的修法不對稱，必須各自處理，並確保處理後仍通過 `check_wrapper_thinness`（該檔屬 PKG-10，你只被它檢查、不得編輯）。
  2. **R77-48**：零本機通道登記表指名兩個不存在的載具。改動限於 `test_smoke_ci_sync.py` 的 `_CI_STEP_LOCAL_CARRIER` 字典。四個地板要守：①`test_named_local_carriers_actually_exist` 有 `assertGreaterEqual(len(referenced), 4)`（:1147）——把 `:914` 改成 `_NO_CARRIER` 前綴會使它被排除（:1140），要確認 `referenced` 仍 ≥4；②`_MIN_CI_STEPS = 20`（:932）抽取下限不得跌破；③兄弟鎖 `test_registered_smoke_groups_exist*` 同步；④守門必須從「只驗檔案存在」升級成「**驗指涉可反查**」（形態四的共同修法）。
  3. **R77-23**：root-infra 4 道無本機等價；act 因映像缺 pwsh 在第 2 道 rc=127。🔴 **不要**把 `.actrc` 的 `-P ubuntu-latest` 全域換成 full-latest——該檔是三個消費者共用的 SSOT（`run_act.ps1|.sh`、`AISDLC_SDD/scripts/act-ci.sh`），換掉會連 `-j test` 一起改映像，且 `--pull=false` 在場 ⇒ 未預拉必直接失敗。**較安全**：在 root-infra step 前加一步 `command -v pwsh` 的存在檢查並 fail-loud 指路。
  4. **R77-47**：三個載具缺陷。①`services` panic 是 **act 0.2.89 上游 bug**（GetHealth 對 nil container 解參考），repo 內無正確程式修法 ⇒ **只在 `run_act_core.py`／文件記載「帶 services 的 job 在 act 上不可用，改走 `docker-compose.ci.yml`」**；②加 `--init` 前注意 `.actrc` 已有 `--container-architecture linux/amd64`（Apple Silicon 走 QEMU 是刻意設計）；③docker cp 併發互踩＝序列化。
- **must_not_touch**：`.github/workflows/**`（PKG-05）；`AutoClaude/tests/**`（PKG-11/PKG-12——特別是 `AutoClaude/tests/test_perception.py`，**本輪不動**）；`tools/check_wrapper_thinness.py`／`check_script_parity.py`（PKG-10）；`AutoClaude/tools/run_local_nightly.*`（PKG-07）。🔴 **絕不可**為了讓 act 好看而從 `autoclaude-ci.yml` 拿掉 pg-contract 的 services。
- **acceptance**
  1. `& $py tools\run_root_unittests.py` → **rc=0**（`test_smoke_ci_sync` 在此樹）
  2. `& $py tools\check_wrapper_thinness.py` → **rc=0**
  3. `& $py tools\check_script_parity.py` → **rc=0**
  4. **R77-49 量測對拍**：`powershell.exe -NoProfile -File AutoClaude\tools\run_act.ps1 -List` 印出的 JOB_COUNT，與在 repo 根跑 `act -l` 的 job 數**必須相等**（動工前實測 9 vs 25）；貼出兩個數字
  5. **兩支薄殼對稱自檢**：同一組引數分別餵 `.ps1` 與 `.sh`，兩者轉給 `run_act_core.py` 的 argv 必須逐字相同（用 `--dry-run`／echo 取證）
- **parallel_safe_with**：PKG-02, PKG-03, PKG-04, PKG-05, PKG-06, PKG-07, PKG-09, PKG-10, PKG-11, PKG-12

---

### PKG-09-LOCKS（order 2；**須早於 PKG-06 的 pre-push 接線 commit**）

- **scope**：跨平台掃描鎖的掃描面缺口與方向失明。
- **files_touched**
  - `tools/tests/test_platform_neutral_paths.py`、`tools/tests/test_subprocess_encoding_hygiene.py`、`tools/tests/test_ps51_compat.py`
  - `tools/tests/test_run_root_unittests.py`
  - `tools/lib/windows_skip_tags.py`、`tools/lib/skip_tag_policy.py`
  - `tools/run_root_unittests.py`
- **做什麼**
  1. **R77-52**：兩支姊妹鎖掃描面差 44 檔（缺口正好蓋住整層 hook）＋下限無腐化上界（`tools/tests` floor=10／actual=56 ⇒ **82% 掃描面可靜默蒸發而全綠**）＋方向判不出 108 站點。**藥方已存在**：`test_subprocess_encoding_hygiene.py:105-116` 早就把這個病診斷完並開好藥（雙邊帶＋`repin_ceiling`），只餵給兩個病人中的一個 ⇒ **把同一套雙邊帶搬到 `test_platform_neutral_paths.py`**。
  2. **R77-33**：對面平台專屬 API 整類零機械物。**併進 `test_platform_neutral_paths.py`**，該檔已在檔內兩處記載過這個做法（🔴 R78 ARCH-03 訂正：原文的禁令理由 `_FROZEN_GUARD_FILE_COUNT = 53` 已不存在，見 §2 全域規則第 2 條——現行約束是「淨行數不得上升」，併進既有檔仍是成本最低的合法路徑，但那是**取捨**不是禁令）。
  3. **R77-18**：`_WINDOWS_SKIP_TAG_EXEMPT` 零 stale 自檢、零牙。在既有 `tools/tests/test_run_root_unittests.py` 內加自檢（不新增檔案）。兩個具體風險：①`run_root_unittests.py:119` 明載既有測試會 `mock.patch.dict(run_root_unittests._WINDOWS_SKIP_TAG_EXEMPT, …)`，新斷言必須在 assert 當下讀**活體模組屬性**；②不得與那些 patch 併行（unittest 序列執行沒問題，但任何平行 runner 會互踩——本 repo 有「並行突變互踩假紅」判例）。
  4. **R77-56a**：`skip_tag_policy.py:44,152-155,236` 標籤詞彙表無成員檢查、兩棵 `fsm_runtime` 樹零覆蓋。🔴 **不得把測試側的平台述詞換成 `is_windows()` helper**——`skip_tag_policy.py:66-97` 是用**述詞的字面原始碼**（`sys.platform == "win32"`、`os.name == "nt"` …）判定是否需要 Windows skip 標籤，換掉會讓它們對該表**隱形**（Scan-H⑥ 教科書式互撞，R77-27 已證偽該方向）。
- **must_not_touch**：`tools/git-hooks/**`（PKG-06）；`CLAUDE.md`（PKG-01——你若補了新掃描器而鐵律三那張表該改列，**寫進交件回報**，不要自己改）；`tools/tests/test_doc_loc_baseline_freshness_r60.py`（PKG-01）；`AutoClaude/tests/**`。🔴 **不得重釘 `MIN_TESTS`**（收尾包的事）。🔴 **不得下修任何 floor**；補雙邊帶時上界只准是「當下實況＋明示的成長容忍」，不得是拍腦袋的大數。
- **acceptance**
  1. `& $py tools\run_root_unittests.py` → **rc=0**，`發現 N 個測試` 的 N ≥1979 且 ≤2473
  2. **掃描面腐化自檢**（證明雙邊帶真的長牙）：暫時把 `tools/tests` 內任一支掃描器改名／移走 → 第 1 條必須 **rc=1**（改前是全綠）；驗完還原
  3. **R77-33 落點自檢**：把一個「對面平台專屬 API」的合成違規注入拋棄式檔 → 新掃描器必須命中；貼出命中行
  4. `& $py tools\check_script_parity.py` → **rc=0**
- **parallel_safe_with**：PKG-02, PKG-03, PKG-04, PKG-05, PKG-07, PKG-08, PKG-10, PKG-11, PKG-12（**與 PKG-06 序列化**）

---

### PKG-10-PARITY（order 2）

- **scope**：腳本對等／薄殼厚度／退場欄形式主義。
- **files_touched**
  - `tools/check_script_parity.py`、`tools/tests/test_check_script_parity.py`
  - `tools/check_wrapper_thinness.py`、`tools/tests/test_check_wrapper_thinness.py`
  - `tools/lib/GitHooksInstallCommon.ps1`、`tools/lib/git_hooks_install_common.sh`、`tools/git_hooks_install_common.py`
- **做什麼**
  1. **R77-13**：8 筆「退場：未指派」。**安全解＝把 8 筆改填具名輪號，或真的收斂掉幾筆**。🔴 **不要**把鎖改成「驗證輪號仍在未來」——`:624-627` 與 `CrossPlatform_Scan_Dimensions.md §191` 已載明會造成永紅，且形狀等同 R75 那個 P0（判準的比較對象隨被判動作改變）。收斂任一筆須**同 commit** 同步 `_TIER_BASELINE`（`test_baseline_covers_every_live_entry_and_agrees_on_tier` 要求逐字相等）；`_TIER34_FLOOR = 10` 只准上修、`_UNPINNED_CEILING = 8` 只准下修（本回合實查 `tools/check_script_parity.py:1172,1198`）。
  2. **R77-54**：parity 家族四缺口——①LATEST 薄殼釘選分成兩套（`check_script_parity.py:386`）；②薄殼宣稱沒人量（`check_wrapper_thinness.py:82,409`）；③紅印在第 1 行後接 12 行綠（同 R77-17 的 accumulate-then-report 形態）；④訊息指路單一檔（`tools/lib/GitHooksInstallCommon.ps1`）。
- **must_not_touch**：`tools/tests/test_ps1_bom.py`（**特別警告**：鐵律三那張表若把它以反引號寫回「行尾」那一列，實質判準會當場紅——它守的是 BOM 不是行尾）；`tools/git-hooks/**`（PKG-06）；`AutoClaude/tools/run_act*`（PKG-08）；`CLAUDE.md`（PKG-01）。🔴 **`tools/tests/` 淨行數不得上升**（`TestGuardLayerRatchet`；R78 ARCH-03 訂正：原文寫的「不得新增鎖檔」是已退場的檔數棘輪語意）。🔴 **不得上修 `_UNPINNED_CEILING`／下修 `_TIER34_FLOOR`**。
- **acceptance**
  1. `& $py tools\check_script_parity.py` → **rc=0**，且輸出的 `unpinned` 計數 **< 8**（動工前實測 `unpinned 8/8`；持平不算完成）
  2. `& $py tools\check_wrapper_thinness.py` → **rc=0**
  3. `& $py tools\run_root_unittests.py` → **rc=0**
  4. **accumulate-then-report 自檢**：同時注入兩筆不同的 parity 違規 → 兩支工具必須**一次印出兩筆**（改前只印第一筆）；驗完還原
- **parallel_safe_with**：PKG-02, PKG-03, PKG-04, PKG-05, PKG-06, PKG-07, PKG-08, PKG-09, PKG-11, PKG-12

---

### PKG-11-SKIPGOV（order 2；**必須在 PKG-04 之前 commit**）

- **scope**：skip 治理文件的內容真實性＋AutoClaude 測試側的 skip reason 與自鎖型債。
- **files_touched**
  - `docs/06_quality/Skipped_Test_Inventory_R76.md`
  - `AutoClaude/tests/contract/test_ac_matrix_scaffolding.py`
  - `AutoClaude/tests/integration/test_pgvector_hnsw_recall.py`
  - `AutoClaude/tests/test_gap014_020.py`、`AutoClaude/tests/test_gap039_049.py`
  - `AutoClaude/tests/conftest.py`
- **做什麼**
  1. **R77-39a**：把 `Skipped_Test_Inventory_R76.md` 的 18 行過期基線 claim 逐行更新，並補上 `<!-- ... -->` 形態的可解析標記，讓它**具備被登記進治理面的資格**（登記動作由 PKG-04 做）。前置：PKG-01 已定義 `Scan-Q`。
  2. **R77-37**：skip reason 三筆——誤判永久不覆蓋／指向不存在通道（`Grep hnsw .github/workflows` → `No matches found`，reason 卻逐字寫「CI nightly 啟用」）／藏 59 支 backlog。⚠️ 改 `test_pgvector_hnsw_recall.py` 的兩行 reason 會被 AutoClaude pre-commit 的**整檔 ruff** 擋下（該檔當回合 `ruff check` rc=1／3 fixable）⇒ **在同一次編輯把那 3 筆 ruff 問題一併修掉**（你正在動這支檔，屬自己的 mess，不是「改善鄰近程式碼」）。**不得用 `--no-verify` 繞過。**
  3. **R77-56b**：29 支 AC matrix 佔位 skip 的函式體是 `pytest.fail(...)` ⇒ 想清這筆債的人會先吃一個紅（形態三：制度在懲罰誠實）。把「佔位」與「未實作」兩件事拆開：佔位改成明示的 `pytest.skip(reason=...)` 並在 reason 內寫可反查的座標，`pytest.fail` 只留給真的該紅的情形。
- **must_not_touch**：`tools/check_defect_log_crossref.py`／`check_pytest_baseline_sites.py`（PKG-04 負責登記，你只負責讓檔案有資格被登記）；`AutoClaude/tests/test_perception.py`（本輪不動）；`AutoClaude/tests/tools/**`（PKG-07）；`AutoClaude/pyproject.toml`（PKG-12）；`AutoClaude/autoclaude/**`（PKG-06/PKG-12）。🔴 **不得刪除任何測試**（根層 slack 0；AutoClaude 側 3919/224 是 ONBOARDING 快照基線，掉數會讓 `--check-snapshot` 紅）。
- **acceptance**
  1. `Push-Location 'D:\CursorProject\AISDCL_Agent\AutoClaude'; & $py -m pytest tests/ -q; "rc=$LASTEXITCODE"; Pop-Location` → **rc=0**，`passed` ≥3919、`skipped` **< 224**（動工前基線 3919 passed／224 skipped；skip 數必須真的下降）
  2. `Push-Location 'D:\CursorProject\AISDCL_Agent\AutoClaude'; & 'D:\CursorProject\AISDCL_Agent\.venv\Scripts\ruff.exe' check tests/integration/test_pgvector_hnsw_recall.py --no-cache; "rc=$LASTEXITCODE"; Pop-Location` → **rc=0**
  3. `& $py tools\sync_onboarding_baselines.py --check-snapshot` → **rc=0**（若快照因 skip 數下降而過期，用 `--write` 更新，**禁 `--allow-pg-extras`**）
  4. `& $py tools\run_root_unittests.py` → **rc=0**
- **parallel_safe_with**：PKG-02, PKG-03, PKG-05, PKG-06, PKG-07, PKG-08, PKG-09, PKG-10, PKG-12

---

### PKG-12-DEBT（order 2）

- **scope**：AutoClaude 側可安全清的技術債＋兩處生產碼平台語意。
- **files_touched**
  - `AutoClaude/pyproject.toml`
  - `AutoClaude/tools/_check_claude_md.py`、`AutoClaude/tools/_compute_sha.py`、`AutoClaude/tools/setup_pg_runtime_role.py`
  - `AutoClaude/autoclaude/infra/repositories/file_state_repository.py`
  - `AISDLC_SDD/AISDLC_SDD_v0.30/tools/fsm_runtime/file_lock.py`
  - `AISDLC_SDD/AISDLC_SDD_v0.30/tools/fsm_runtime/_chaos_b28_benchmark.py`
- **做什麼**
  1. **R77-57**：①`pyproject.toml:10-135` 依賴 15 筆無上限（含 3 筆 0.x）→ 補上界；②三支零引用孤兒腳本（`_check_claude_md.py`／`_compute_sha.py`／`setup_pg_runtime_role.py`）→ 逐支判定「刪除」或「補上唯一消費者」，**兩者擇一並說明**，不要留著不動；③800 常數住兩個家 → 收斂成單一權威源；④`_chaos_b28_benchmark.py` 的量測紀律（債 ×30）→ 分 live/frozen 欄。
  2. **R77-58**：①`file_lock.py:9-12,33-43` 的 `os.open` 在 Windows 是文字模式，使 sentinel 變 CRLF → 加 `os.O_BINARY`／顯式 `newline="\n"`；②`file_state_repository.py:42,98,138,151` checkpoint 目錄列舉未排序且時戳秒粒度 → NTFS 字母序 vs APFS readdir 序會讓同一斷言 Windows 綠／mac 紅並看起來像 flaky（本 repo 已為「假 flaky」付過三次學費）→ 顯式排序＋提高時戳解析度。
- **must_not_touch**：🔴 **不得跑全樹 `ruff --fix`**（R77-40 已證偽：`I001` 自動修復會拆 import 增行，而 AutoClaude LOC 總帳 total=20296／cap=20438、餘裕僅 142 行；`F821` 是真 bug 候選須逐筆人工判）。`AutoClaude/CLAUDE.md`（400/400 已滿載，本輪不動）；`AutoClaude/tools/check_loc_budget.py`（R77-60，需拍板）；`AutoClaude/tests/**`（PKG-11）；`AutoClaude/autoclaude/utils/logger.py`（PKG-06）；`AutoClaude/tools/run_act*`／`run_local_nightly.*`（PKG-08／PKG-07）；`AISDLC_SDD/AISDLC_SDD_v0.0*`~`v0.29`（Copy-on-Evolve 凍結）。
- **acceptance**
  1. `Push-Location 'D:\CursorProject\AISDCL_Agent\AutoClaude'; & $py -m pytest tests/ -q; "rc=$LASTEXITCODE"; Pop-Location` → **rc=0**，`passed` ≥3919
  2. `Push-Location 'D:\CursorProject\AISDCL_Agent\AutoClaude'; & $py tools\check_loc_budget.py; "rc=$LASTEXITCODE"; Pop-Location` → **rc=0**
  3. `Push-Location 'D:\CursorProject\AISDCL_Agent\AutoClaude'; & 'D:\CursorProject\AISDCL_Agent\.venv\Scripts\ruff.exe' check . --no-cache; "rc=$LASTEXITCODE"; Pop-Location` → 錯誤數**不得比動工前多**（動工前先量一次並記錄）
  4. `& $py -m pytest AISDLC_SDD/AISDLC_SDD_v0.30/tools/fsm_runtime/tests -m "not chaos" -q` → **rc=0**
  5. **R77-58① 位元組級驗紅**：對 sentinel 檔做 bytes 級斷言（`b"\n" in data and b"\r\n" not in data`），改前必須紅、改後綠；貼出兩次輸出
- **parallel_safe_with**：PKG-02, PKG-03, PKG-04, PKG-05, PKG-06, PKG-07, PKG-08, PKG-09, PKG-10, PKG-11

---

## 4. needs_pm_signoff（掌舵者拍板，不得自行改判）

| # | 事項 | 為何必須拍板 |
|---|---|---|
| S-1 | **R77-06a — GitHub Actions 帳務**（root-infra-ci 近 100 run 僅 18 成功、19 天 373/584 never-started） | 只有帳號持有人處理得了。🔴 連帶效應必須先讓掌舵者知道：它同時把 R77-03／R77-04 的**雲端兜底打掉約 82%** ⇒ 本輪其他判斷一律**不得假設雲端會接住**。 |
| S-2 | **R77-08／R77-10 — PreToolUse deny 面變動** | 新增／改動 hook matcher 直接踩「hook 誤觸 deny 會把所有工具硬鎖死」那一層 P0。且兩者被既有鎖夾死：`test_check_hooks_liveness.py:338/344` 釘死「退化 payload 必 fail-closed（rc=2）」，而 `test_pretooluse_matcher_task.py:41-48` 要求根 settings.json 每個 PreToolUse matcher 含 `Task` ⇒ 新 matcher 只能寫 `'PowerShell\|Task'`，於是新守衛必須自帶「tool≠PowerShell → exit 0」的射程限縮，恰好複製 R77-08 的退化-payload 形態。**這是 Scan-H⑥ 兩道鎖互為對方違規，需要人決定放棄哪一邊。** |
| S-3 | **R77-24 — 護欄層分家＋移除 `_FROZEN_GUARD_FILE_COUNT`** | 當回合查到 **6 道互鎖**：檔數棘輪逐字相等、`MIN_TESTS` 收集下限、AutoClaude 側鎖…… 任何分家／搬移都必須同 commit 改多個常數，且其中包含「調整棘輪」——本輪硬性禁令要求不得自行為之。 |
| S-4 | **R77-25 — Copy-on-Evolve 刪 28 個凍結版**（26073 檔 92.7% 位元組重複） | ADR-XPLAT-002 §8 item 10 明文列為**未指派的政策決定**；且 v0.02／v0.05 正被兩支 bridge 測試執行、`autoclaude-ci.yml:18-20` 對那些路徑觸發 ⇒ 刪＝拆活閘門。**只能由掌舵者決定政策，不能由修復包單方面執行。** |
| S-5 | **R77-60 — root tools tier 系統重設計**（最大 6 支全以 `SPECIAL_FILES` 逐檔議價 1474~2000） | 動的是護欄層硬上限的治理方式。任何「調整上限」的動作本輪明令禁止；改成別種治理方式屬架構決策。 |
| S-6 | **R77-04 的替代路徑（若 PKG-07 回報「掛進既有 stage 不可行」）** | 那就必須改 nightly summary 契約，牽動 `tools/dev_start.py` 的跨檔字面鎖與四處同步點。契約變更請掌舵者拍板後再做。 |
| S-7 | **R77-51 的 COM0／上標變體兩筆** | 四處 `_RESERVED_RE` 的等值鎖要求逐字相同、且錨① 對相鄰性有硬約束 ⇒ 修正 COM0 過攔要一次改四處並重釘鎖。它同時牽涉「repo 的判準要不要與 `git core.protectNTFS` 完全對齊」這個政策問題（對齊＝放行 COM0，等於**放寬**一個現有攔截）。**放寬型變更一律拍板。** |

---

## 5. deliberately_not_fixing（本輪刻意不修，逐筆附理由）

> 🔴 「沒時間」不是理由。以下每筆的理由都是「不做有優點」或「需人工決策／無安全修法」。

| item | 不修的理由 |
|---|---|
| **R77-01**（NTFS `.git` 家族四判準） | **已證偽（P0→P3）**：提案修法無效——兩支 sanitizer 都走 `stem = s.split('.',1)[0]`，`.git` 的 stem 是空字串，把 `.git` 加進保留名正則根本不會命中。且會撞三道既有硬閘。**修錯的東西比不修更糟。** |
| **R77-05h**（nightly DSN 順序） | **已證偽**：`:985-986` 的順序是刻意的（Stage L 要等同乾淨環境），提前設 DSN 會撞 `MissingGreenlet`。可救的那一半（擴 pg-e2e 選擇面）已排進 PKG-07。 |
| **R77-09**（hook shim 抽 launcher） | **已證偽**：立論前提（零綁定／mac 恆 127）被三道鎖與 setup-python 證偽 ⇒ 高機率白工，且動的是 PreToolUse deny 面。**做了是負收益。** |
| **R77-26h**（ADR §8.1 9 輪空表無到期機制） | 到期機制屬治理政策設計，非本輪可單方面訂。可救的那一半（§4.2 換現查指令）已排進 PKG-02。 |
| **R77-27**（120 個裸平台述詞換 helper） | **已證偽**：`skip_tag_policy.py:66-97` 用**述詞字面原始碼**判定是否需要 Windows skip 標籤，換成 `is_windows()` 會讓它們對該表隱形 ⇒ 修法本身會製造一個更大的盲區。 |
| **R77-28**（mac launchd 零期望值 SSOT／兩 smoke 零覆蓋對帳） | **已證偽**：兩支 smoke 的 `tier4_forbidden` 是明文裁決（`--print-collapse` 逐字「本身即為驗證載具，判定合流至單一核心會與 R12 QA-2 衝突，明文禁止收斂」）⇒ 直接做跨 smoke 覆蓋比較器是往那條裁決禁止的方向走。 |
| **R77-29**（GA 兩軌最快 08-21/22） | **無合法修法**：`ga_window.py:52` 明文「不得為了讓數字好看而調高本值（砸溫度計）」；回填舊日期＝捏造量測，違反反捏造紀律與反作弊規則。**唯一合法槓桿是等時間到**。本輪只記錄，不動。 |
| **R77-34**（`_MARKER_PAIRS` 是空 list） | **已證偽**：殘留純屬外觀——`:1545-1555` 的迴圈跑零次，`:951` 的錯誤訊息仍提供正確的加入路徑。**刪死碼的收益低於動它的風險。** |
| **R77-35**（liveness advisory rc 無人消費） | **降級 P2 且非缺陷**：advisory 是**明文設計意圖**（「任何探測失敗都不得影響閘門本體」），子行程繼承 stdout 故警告確實會印（未讀 rc ≠ 靜默）；drift 另有真正的 fail-closed 消費者（`run_local_nightly.ps1:1937-1945` 記 ERROR 並計入該輪失敗）。**把 advisory 改成阻斷會讓探測失敗癱瘓閘門本體**，那是負收益。 |
| **R77-40**（三棵樹 lint／LOC 存量債 815/62/3485） | **已證偽且危險**：`ruff --fix` 的 `I001` 會拆 import 增行，而 AutoClaude LOC 總帳餘裕僅 142 行；`F821` 是真 bug 候選須逐筆人工判；在 CI 加全樹 ruff 閘門會讓 push 軌立刻紅 815 筆。**需人工逐筆判定，不是一輪能做完的事。** |
| **R77-41**（7 條 slack≤1 棘輪、4 條無預警帶） | **已證偽**：最危險修法（上修 ceiling 製造餘裕）直接違反四道鎖的 shrink-only 契約；次之的「加黃帶」會在 `tools/` 四支守門檔各加行，而 `tools/tests` 這棵樹自己受 `_E501_DEBT_CEILING = 139`（slack **0**）管，新行超長即當場紅。**不動為宜。** |
| **R77-42**（sanitize 委派鎖 10 個消費者只覆蓋 5） | **已證偽**：等值鎖已守「第 5 份實作」這一類，10 支當回合全部確實 import 共用函式 ⇒ 補 5 支 `assertIs` 幾乎零增益，卻要往 `tools/tests/` 加約 50 行而該樹 E501 棘輪 slack 0。 |
| **R77-43a**（.ps1 工作樹 4 支 CRLF） | **結構上不可 commit**：index 已是 LF，`git add --renormalize` 對這 4 支產生**零 diff**，只能改本機工作樹位元組＝每台機器各自為政，不是可入庫的修復。且 pre-commit 檔頭 L278-284 明文「看暫存區 blob 不看工作樹」⇒ 任何 commit 層閘都必須違反該原則（Scan-H⑥）。BOM 那一半已排進 PKG-06。 |
| **R77-46h**（「7.6.4 把紅讀成綠」） | **已證偽**：把它寫進 CLAUDE.md／交棒書＝**在樹裡寫下一句新的假話**，而本 repo 明文禁止在訂正註記裡留假句子且有鎖在抓。可救的那一半（改寫 rc 管線的**理由**）已排進 PKG-01。另兩個子項（37/12 那筆）**未經查證，不得直接進修復包**——請以獨立 finding 重新立案。 |
| **R77-47①**（act `services` panic） | **上游 bug**：act 0.2.89 的 `GetHealth` 對 nil container 解參考，repo 內無正確程式修法。唯一「修法」是拿掉 pg-contract 的 services，而那是明文硬閘＝砸溫度計。PKG-08 只做「記載改走 `docker-compose.ci.yml`」。 |
| **R77-38 的另一半**（真的建 nightly TLC 通道） | ①R76 實測整套 TLC **333.01s**；②需 Java ＋ 下載 `tla2tools.jar`（新增外部相依）；③新增 schedule job 會落進 root-infra-ci 已擁擠的時段——而**雲端額度正好耗盡**（S-1）。在帳務恢復前新增雲端負載是負收益。 |
| **R77-53 的「散文寫死數字 327 處零掃描器」那一項** | 建一支「散文數字掃描器」會產生 327 筆立即違規＝上線即全紅，正是 `check_defect_log_crossref.py:592-596` 記載的 ARCH-R59-NB4「永紅的閘門會被整個關掉，比沒有鎖更糟」。**要做必須先有減量計畫**，屬下一輪標的。 |

---

## 6. 執行序與並行拓撲

```
order 1        PKG-01-UNBLOCK                （單獨跑，commit 後其他包才動工）
                      │
order 2   ┌───────────┼───────────┬──────────┬──────────┬──────────┐
          PKG-02      PKG-03*     PKG-05     PKG-07     PKG-08     PKG-11
          PKG-06 ←─── 等 PKG-09   PKG-09     PKG-10     PKG-12
                      │                                    │
order 3               └──────── PKG-04 ←─ 等 PKG-11 + PKG-03
```
- `*` PKG-03 另有**外部前置**：等目前那個並行 agent 的帳本歸檔 commit 完。
- 唯二的序列化對：**PKG-09 → PKG-06**（掃描器先落地，pre-push 再接線）、**PKG-11 + PKG-03 → PKG-04**（文件先有資格、帳本先安定，登記與判準才動）。
- 其餘同 order 的包**檔案零交集**，可全部並行。

## 7. 收尾包（不在 12 包內，由收輪者執行）

1. 全部 12 包停工後，取**含內容**的工作樹指紋兩次並確認相同（`git status --porcelain` ＋ `git diff HEAD` ＋ untracked 檔內容雜湊）。
2. 實跑 `python tools/run_root_unittests.py`，把印出的計數**直接填入** `MIN_TESTS`，零加減推算。
3. 套用各包交件回報中「需要改根 `CLAUDE.md` 鐵律三表」的條目（並同步 `_IRON_LAW3_UNCOVERED`／`_IRON_LAW3_TOPIC_KEYWORDS`）。
4. 由 PKG-03 之外的人**不要**碰帳本；本輪新增列請走 PKG-03 的交件通道。
5. push 後**必等五／六支雲端軌 completed**（R74 教訓）——但先確認 S-1 帳務是否恢復；未恢復時明說「雲端結論不可得」，不得以本機全綠代替。
