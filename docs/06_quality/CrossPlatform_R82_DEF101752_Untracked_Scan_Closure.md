# DEF-101-752 — R82 帳本瘦身與站點收斂證據檔

本檔承接 `docs/06_quality/AutoSDD_Defect_Log.md` 的 `DEF-101-752` 列。該列在 R82 前的
「狀態」欄原文已逼近帳本單列 700 bytes 上限的存量豁免棘輪，R82 依帳本瘦身慣例（判例
同 `CrossPlatform_R79_Debt_Audit.md`／`CrossPlatform_R81_Ledger_Triage.md`／
`CrossPlatform_R82_Ledger_Closure.md` 等既有證據檔）把欄內長文逐字保全於本檔，帳本列上
只留索引與本檔案指標。

🔴 **命名訂正**（本輪四方複審 Architect 發現，2026-08-27）：本檔原本不採
`CrossPlatform_*.md` 命名慣例，自述理由是「該輪任務邊界不得觸碰
`tools/lib/governance_docs.py`」——但同一輪的 diff 其實**已經**改了該檔（新增登記其他
證據檔），這句自陳站不住，屬純粹的命名疏忽未跟進慣例，並非刻意迴避登記。

🔴 **二次訂正**（帳本結案輪修復包，2026-08-27）：上一段的「維持原檔名不再改動」判斷
本身也站不住——原檔名 `DEF101752_R82_Untracked_Scan_Closure.md` 不符
`_GOVERNANCE_DOC_GLOBS`（`CrossPlatform_*.md`／`Quota_*.md`）任一樣式，把它硬塞進
`_GOVERNANCE_DOCS` 只是讓「登記面」單方面認得它，`unregistered_governance_docs()`
的**發現面**（glob 掃描磁碟）依然找不到，形成「登記了但磁碟掃描找不到它」——與本機制
原本要防的「磁碟上有卻沒登記」方向相反，一樣是登記面與發現面不一致。正確做法是讓
檔名符合 glob 樣式，本檔已改名為 `CrossPlatform_R82_DEF101752_Untracked_Scan_Closure.md`
並同步更新 `tools/lib/governance_docs.py::_GOVERNANCE_DOCS` 與所有引用此檔名的站點。

## §1 R82 前「狀態」欄原文（逐字保全，零改寫）

> partial（本輪只修 3／14 個 fail-open 站點，其餘**承接輪次：R71**——用 `partial` 而非
> `fixed` 是刻意的：這筆的根因是「掃描面政策」而非單一檔案，只修三處不算修完）：三處
> 掃描面改為 **tracked ∪ untracked-not-ignored**（`git ls-files` ∪ `git ls-files -o
> --exclude-standard`；排除 venv／快取的效果原本就靠 `.gitignore`，`--exclude-standard`
> 一樣排除得掉）。盲區已封由 `TestScanSurfaceCoversUntrackedFiles` 以**真實 untracked
> 探針**證明——同一支測試內對照兩個掃描面：修前的 tracked-only 看不到它／修後看得到且
> 被判違規（只證後者的話，掃描面被改回去時本鎖不會說話）。實測：舊掃描面 5461 檔、含
> 探針=False；新掃描面 5462 檔、含探針=True。隔離鎖側同樣實測：注入 untracked 的
> `AISDLC_SDD/scripts/_probe_untracked_violation.py`（`from autoclaude.utils.logger
> import …`）⇒ `1 failed, 23 passed`；刪除 ⇒ `24 passed`。**承接 R71 的其餘站點（依風險
> ×成本排序）**：`test_windowsapps_guard_cross_consistency.py:488`、
> `test_windowsapps_guard_bash_parity.py:208/241`（後兩者的等值斷言納入 untracked 會被
> 本機草稿打成偽陽，需拆兩本帳）、`test_ps1_bom.py:74`、`test_bash32_compat.py:133`、
> `test_ps51_compat.py:187`、`test_windows_forbidden_filename_parity.py:639`、
> `test_find_git_bash_parity.py:787`、`test_workflow_permission_concurrency_lock.py:698`、
> `test_ci_paths_cover_root_consumers.py:1159`（同檔 :1083 已用 `--others
> --exclude-standard`，是本 repo 最早封閉此盲區的先例）、`check_gha_action_versions.py:213`、
> `tools/macos_smoke_local.sh:180`（被 `test_smoke_ci_sync.py` 的 pathspec 逐字互鎖，
> 改單邊必翻紅）。**判定為「加 untracked 反而有害」、刻意維持 tracked-only 的六處**（其
> tracked-only 是寫在 docstring 內的刻意語意，納入 untracked 會分別造成 LATEST 被草稿
> 目錄劫持／本機暫存檔打紅無辜 commit／存在性鎖恆綠）：`AISDLC_SDD/scripts/sdd_version.py:77`
> （版本推導）、`tools/check_ntfs_paths.py:276`、
> `AISDLC_SDD/scripts/tests/test_ntfs_length_gate.py:306`、
> `tools/tests/test_ntfs_trailing_space_device_name.py:454`（及 `:523` 的真相集那一半）、
> `tools/git-hooks/pre-commit:172`、`AISDLC_SDD/scripts/tests/test_copy_on_evolve.py:465`
> 🔴 **R71 帳本包就地追加：改派為「未指派」（原文逐字保全，零改寫）**。起因＝
> `check_defect_log_crossref.py` 本輪對本列印出 fail-open 窗口警告（逐字「承接輪次 R71
> **恰等於**由『發現情境』欄推得的當前輪」），而 R71 的第一批帳本列一落地、當前輪即由
> R70 推進為 R71 ⇒ 本列的 R71 指派**已等於指向正在進行中的這一輪**；到 R72 就會低於
> 當前輪而被硬規則② 判為孤兒 backlog（rc=1 硬閘）。**本包當回合逐檔實查，R71 並未
> 承接**：對本列點名的殘餘站點跑 `grep -c exclude-standard`，
> `test_windowsapps_guard_cross_consistency.py`／`test_windowsapps_guard_bash_parity.py`／
> `test_ps1_bom.py`／`test_bash32_compat.py`／`test_ps51_compat.py`／
> `test_windows_forbidden_filename_parity.py`／`test_find_git_bash_parity.py`／
> `test_workflow_permission_concurrency_lock.py`／`check_gha_action_versions.py`／
> `tools/macos_smoke_local.sh` **全部為 0**（`test_ci_paths_cover_root_consumers.py`
> 已不在該路徑，需重新定位）。故依本閘門自己給的合法出口①**就地追加改派**，不改寫
> 任何歷史原文：**改派為：未指派**，解鎖條件與站點清單完全沿用本欄上文（依風險×成本
> 排序的 12 站點、以及「判定為加 untracked 反而有害、刻意維持 tracked-only」的六處
> 不動）。🔴 **若本輪 commit 前主控其實已把這些站點做完，正確處置是改為就地追加「回執」
> 並把首詞改為已結 token，而不是留著這筆改派**——本附記是為了消滅一個**已知會在 R72
> 變成硬紅**的孤兒指派，不是為了宣稱這些站點不必做 ｜🔴 R81 改派，承接輪次：**R82**
> （本輪做不完：11 個承接站點今日逐檔實測仍有 10 個是 tracked-only 掃描面〔R71~R80
> 十輪零進展〕，根因是掃描面政策不是單一檔案，須拆成每包 2~3 站點各附 untracked 探針
> 的注入紅綠；且該列已標明六處「加 untracked 反而有害」的站點不可一律套用）

## §2 R82 本輪處置結果

R81 帳本包實測「11 個承接站點今日逐檔實測仍有 10 個是 tracked-only 掃描面」；
`test_ci_paths_cover_root_consumers.py` 需重新定位。本輪（R82）逐站點動手，結果如下。

### §2.1 全量修復（9 站點）

沿用 R70 已驗證手法：掃描面由純 `git ls-files` 改為 `git ls-files` ∪
`git ls-files -o --exclude-standard`（tracked ∪ untracked-not-ignored）。每處皆以真實
untracked 探針驗證：注入前對應測試綠燈 → 注入後翻紅（列出探針檔為違規／未覆蓋）→
刪除探針 → 恢復綠燈。探針檔皆為暫存，驗證完畢即刪除，不進 git index。

| 站點 | 掃描面函式 | 驗證方式與結果 |
|---|---|---|
| `tools/tests/test_windowsapps_guard_cross_consistency.py`（原 :488，`_tracked_files`） | `_tracked_files(pattern)` | 注入 `tools/_dep752_probe_windowsapps.py`（`def _is_windows_apps_stub`）：`test_windows_apps_predicate_impls_are_all_registered` 由綠轉紅（多出未登記站點）；刪除後 71 passed, 93 subtests passed |
| `tools/tests/test_ps1_bom.py`（原 :74，`_active_ps1_files`） | `_active_ps1_files()` | 注入 `tools/_dep752_probe_ps1bom.ps1`（剝 BOM、含中文）：`test_active_ps1_bom_policy` 翻紅；刪除後 5 passed |
| `tools/tests/test_bash32_compat.py`（原 :133，`_git_tracked`） | `_git_tracked(rel_prefix)` | 注入 `tools/git-hooks/_dep752_probe_bash32.sh`（`mapfile -t arr < f`）：`test_repo_trees_have_no_bash4_or_gnu_only_usage` 翻紅；刪除後 31 passed |
| `tools/tests/test_ps51_compat.py`（原 :187，`_git_tracked_ps1`） | `_git_tracked_ps1(rel_prefix)` | 注入 `tools/_dep752_probe_ps51.ps1`（`$x = $a ?? $b`）：`test_active_ps1_trees_have_no_ps7_only_usage` 翻紅；刪除後 9 passed |
| `tools/tests/test_windows_forbidden_filename_parity.py`（原 :639，`_ntfs_scan_candidates`） | `_ntfs_scan_candidates(latest_name)` | 注入 `tools/_dep752_probe_ntfs.py`（`RESERVED = {"CON","PRN","AUX","NUL"}`）：`test_registered_sites_match_repo_scan_exactly` 翻紅；刪除後 40 passed, 113 subtests passed |
| `tools/tests/test_find_git_bash_parity.py`（原 :787，`_tracked_ps1`） | `TestFindGitBashCallSites._tracked_ps1()` | 注入 `tools/_dep752_probe_findgitbash.ps1`（呼叫 `Find-GitBash`）：`test_call_site_registry_matches_repo_scan` 翻紅；刪除後 43 passed, 41 subtests passed |
| `tools/tests/test_workflow_permission_concurrency_lock.py`（原 :698，`_tracked_scripts`） | `_tracked_scripts()` | 注入 `zz_dep752_probe_workflow.sh`（repo 根，CI paths 覆蓋面外）：`test_every_tracked_script_triggers_both_compat_ci` 翻紅（windows-compat-ci.yml 未覆蓋）；刪除後 45 passed, 18 subtests passed |
| `AISDLC_SDD/scripts/tests/test_ci_paths_cover_root_consumers.py`（原 :1159，重新定位後為 `test_root_infra_ci_bash_and_py_scan_roots_have_no_stray_scripts`） | 改用同檔既有 `_git_enumerate()`（:1514 起，本 repo 最早封閉此盲區的先例，:1083 起始出現） | 注入 `zz_dep752_probe_stray.py`（monorepo 根）：翻紅（無主 .py 腳本）；刪除後 49 passed |
| `tools/check_gha_action_versions.py`（原 :213，`_tracked_workflow_files`） | `_tracked_workflow_files()` | 注入 `AutoClaude/.github/workflows/_dep752_probe.yml`（未登記巢狀 workflow）：`test_main_against_real_repo_is_green` 由 rc=0 翻為 rc=1；刪除目錄後 `test_gha_action_versions.py` + `test_check_gha_action_versions.py` 合計 53 passed |

### §2.2 拆帳分工（1 站點，非全量）

`tools/tests/test_windowsapps_guard_bash_parity.py`（原 :208/241）——R71 帳本包已預先
判定「等值斷言納入 untracked 會被本機草稿打成偽陽，需拆兩本帳」，R82 逐檔確認屬實：

- `_tracked_sh_files()`（供 `test_no_raw_unguarded_python_check_remains`／
  `test_repo_wide_scan_finds_no_unmigrated_sh_scripts` 等「offender 必須為空」形態掃描）
  **已改為 union**：注入 `tools/_dep752_probe_bashparity.sh`（裸 `command -v python`）：
  `test_repo_wide_scan_finds_no_unmigrated_sh_scripts` 翻紅；刪除後 28 passed, 37
  subtests passed。
- `_tracked_non_sh_shell_scripts()` / `_tracked_files()`（供 `test_hook_dir_roster_
  matches_repo_state` 這種「名冊 vs 實況」等值斷言）**刻意維持 tracked-only**：任何本機
  未 `git add` 的草稿 `.sh`（不論放在哪個目錄）都會被判成「名冊外的新 hooks 目錄」而
  偽陽——與六處「加 untracked 反而有害」站點同一種結構性風險（本機暫存檔打紅無辜
  commit），非本輪授權面內可安全處置，已於程式碼內原地註記。

### §2.3 跳過、未處置（1 站點）

`tools/macos_smoke_local.sh`（原 :180，`sh_files=$(git ... ls-files -- '*.sh' ...)`）
——**跳過，未動**。理由三重，逐一為真：

1. **腳本自身 docstring 已有明文裁決**（:169-171）：「取捨（刻意，非疏漏）：改用
   ls-files 後『完全未追蹤』的草稿 .sh 不再被掃到……換得與 CI 第 1 道同一判準、且
   本地暫存草稿不會造成假紅；新檔一經 `git add` 即入 index、立刻納入本檢查」——與六處
   「加 untracked 反而有害」站點同一種論證形狀（本機暫存檔打紅無辜 commit）。
2. **機械互鎖**：釘選值（`syntax_sh -lt 23` 等）與 `tools/tests/test_smoke_ci_sync.py`
   逐字互鎖（見 :232 註解），改單邊必翻紅，需同步改兩邊並重新核對釘選值。
3. **需 macOS 真機驗證**：本檔存在的核心價值是「以系統 bash 3.2（`$SYS_BASH`）解析，
   比 CI 的 ubuntu bash 5.x 更貼近真實 macOS 執行環境」，本機為 Windows，無法安全驗證
   修改後是否仍符合 bash 3.2 語意與釘選值。

承接輪次：未指派。解鎖條件二擇一：(a) 在 macOS 真機上重新裁定「是否值得放棄現有的
『本機草稿零假紅』特性以換取 untracked 覆蓋」並同步修 `test_smoke_ci_sync.py`；或
(b) 明文裁決本站點與六處「加 untracked 反而有害」站點同列，`partial` 首詞可能因此轉
`fixed`（因為屆時全部非刻意排除站點皆已處理）——本輪不逕自下此裁決，留給下一個有
macOS 真機或明確裁決權的執行者。

## §3 R110 結案（2026-08-29，macOS 窗口）

### §3.1 結案前主檔列原文（逐字保全，零改寫）

結案當下（HEAD `7cb8421`）主檔 `DEF-101-752` 列（結案前 2,428 bytes，逐欄如下；R110
起主檔列瘦身為 ≤700 bytes 的索引，`ROW_MAX_BYTES` 政策，原文自此只住本節）。

**「發現情境」欄原文**：

> R70（同一次 pre-push 阻斷的**元層級**根因；發現情境本身即本筆的主要價值）

**「現象與證據」欄原文**：

> 🔴 **驗證載具自己有盲區，讓一個真實違規躲過整輪的全部把關**：`test_platform_utils_dedup.py:101` 以 `git ls-files "*.py"` 當掃描面 ⇒ **未追蹤（untracked）的 .py 天然不可見**。`platform_caps.py` 在 R69 **全程都是 untracked**，於是 `DEF-101-751` 那個衝突：**在 R69 四輪四方複審全數通過、且收尾者多次 `python tools/run_root_unittests.py` 全套實跑皆綠（多次 `Ran 1581 … OK`）之後，才在 `git add` 使該檔變成 tracked 的那一刻顯形**——四輪複審、四位審查員、多次全套閘門，沒有任何一次看得到它。**這不是鎖寫錯，是鎖看不到該看的地方**（同 Nightly 取證紀律 #4「驗證載具本身要被驗證」）。擴大盤點（`grep -rn ls-files`，19 個 Python 站點＋6 個 shell/CI 站點）確認同款盲區另有 11 處，其中 `AISDLC_SDD/scripts/tests/test_cross_subproject_import_isolation.py:122` 與事故檔**結構同構**（repo-wide `*.py` ＋ 禁用樣式掃描）；`tools/tests/test_extras_quoting_zsh_safety.py` 的檔頭更逐字把該盲區寫成「與 `test_platform_utils_dedup.py` 同政策」的**刻意取捨**——R69 證明那個取捨是錯的

**「分流去向」欄原文**：

> `tools/tests/test_platform_utils_dedup.py`／`AISDLC_SDD/scripts/tests/test_cross_subproject_import_isolation.py`／`tools/tests/test_extras_quoting_zsh_safety.py`（本輪修）＋ 其餘站點見下方盤點（本輪**未修**，誠實劃界）

**「狀態」欄原文（`partial@R82` 全文）**：

> partial@R82（承接：未指派）。R70 起 3 站點＋R82 本輪 9 站點**全量修復**＋1 站點**拆帳分工**（`test_windowsapps_guard_bash_parity.py`：offender 掃描已補 union，roster 比對比照六處刻意排除維持 tracked-only）。手法同構：掃描面改 `git ls-files` ∪ `-o --exclude-standard`，逐站點以注入 untracked 探針驗證修前不可見／修後可見且觸發，驗畢移除，全部測試綠燈。六處「加 untracked 反而有害」站點不動。唯一未觸及：`tools/macos_smoke_local.sh`——docstring 已明文「刻意，非疏漏」排除 untracked，且與 `test_smoke_ci_sync.py` pathspec 逐字互鎖，需 macOS 真機驗證。R70 前原文與 R82 逐站點紅綠實測全文見 `docs/06_quality/CrossPlatform_R82_DEF101752_Untracked_Scan_Closure.md`。

### §3.2 R110 本回合驗證（macOS 真機，逐字）

- `.venv/bin/python -m pytest tools/tests/test_smoke_ci_sync.py -q` →
  `29 passed, 2 subtests passed in 0.18s`（rc=0）：`tools/macos_smoke_local.sh` 與 CI
  第 1 道的 pathspec／釘選值逐字互鎖在 macOS 真機上綠燈。
- `sed -n '169,172p' tools/macos_smoke_local.sh` → 引句仍在原位：「取捨（刻意，非疏漏）：
  改用 ls-files 後『完全未追蹤』的草稿 .sh 不再被掃到……新檔一經 `git add` 即入 index、
  立刻納入本檢查」。

### §3.3 結案裁決

§2.3 的解鎖條件 (b) 於 R110 成立：明文裁決 `tools/macos_smoke_local.sh` 的 untracked
排除與六處「加 untracked 反而有害」站點**同列**——:169 起的取捨為具名設計（與 CI 第 1
道同一判準、本地暫存草稿零假紅、新檔一經 `git add` 即入 index 立刻納入檢查），非本缺陷
「掃描面看不到該看的地方」的疏漏形態，不在本缺陷射程。至此全部非刻意排除站點皆已處置
（R70 三站點＋R82 九站點全量修復＋一站點拆帳分工，紅綠實測見 §2），`partial` 首詞轉
`fixed@R110`。主檔列各欄同回合瘦身成索引，原文全文即上方 §3.1。
