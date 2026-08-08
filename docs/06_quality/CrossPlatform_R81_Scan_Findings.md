# CrossPlatform_R81_Scan_Findings — R81 第一批九路掃描的**唯一居所**

## §0 這份檔為什麼存在

R81 第一批派出 **9 個專家 agent**（6 路掃描／調研 ＋ 1 路 ADR 設計 ＋ 2 位獨立審查者），
共產出 **83 筆 findings ＋ 1 份 ADR ＋ 2 份 verdict（11 筆 blocking）**。這些輸出當時只活在
workflow journal（`subagents/workflows/wf_*/journal.jsonl`）裡——那是會被清掉的暫存檔。
R80 已經吃過一次這個虧（88 筆發現在額度上限被打斷後只剩暫存檔），本檔是同一條紀律的續行：
**掃描完就先落磁碟，再談要修哪幾筆。**

🔴 **誠實劃界（先讀完再引用）**：

1. **證據欄逐字保全**，未改寫、未潤飾；`為何要緊`／`建議修法` 亦為 agent 原文。本檔作者
   只寫了章節骨架與 §1 的統計，**沒有替任何一筆重新判定真偽**。
2. **83 筆全部是「單一 agent 自陳」，未經第三方複驗**——唯一例外是額度那條主線：ADR 的
   宣稱被 SA 與 SD 兩位獨立審查者逐條實查過（住姊妹檔 `CrossPlatform_R81_Quota_Review.md`），
   那一路的可信度明顯高於其餘五路。**其餘五路今天沒有任何 verdict**，引用時請自己複驗。
3. **每一路都自陳了 `honest_gaps`**，逐路收在該節的 `.4` 小節。凡 agent 自己說「這是推得值
   不是實測值」的，落地時一律必須當場複驗——本檔不替它們背書。
4. **本輪的量測環境有污染**：`scan:skipped` 自陳 session 起始 `git status` 為 clean、跑完
   後有 6 支 M ＋ 1 支 ??（同輪並行 agent 就地改 tracked 生產碼）。兩棵樹今天的 failed
   因此**不是** PG 或 skip 造成的（詳見 `SKP-S3-02`）。同樣的理由，本檔多筆宣稱「某閘門
   今天 rc=1」的發現在本檔生成當回合已由別的包修掉（例如 `hook_wiring.py 407>400`
   ——本檔生成當回合 `check_loc_budget.py` 實測已回 rc=0）。**閘門狀態是會漂移的量測值，
   一律現查，不要引用本檔的 rc**。
5. **另外兩路住姊妹檔**：research:quota ＋ ADR ＋ 兩份 verdict 住
   `CrossPlatform_R81_Quota_Review.md`；scan:ledger 的 34 筆住
   `CrossPlatform_R81_Ledger_Triage.md`。對照表見 §8。

## §1 九路全景

| 路 | 本檔 ID 前綴 | 筆數 | P0 | P1 | P2 | P3 | 居所 |
|---|---|---|---|---|---|---|---|
| scan:xplat | `XPL-` | 7 | 0 | 3 | 3 | 1 | §2 |
| scan:subtraction | `SUB-` | 8 | 2 | 3 | 1 | 2 | §3 |
| scan:skipped | `SKP-` | 12 | 1 | 5 | 6 | 0 | §4 |
| scan:autoclaude-helm | `HLM-` | 10 | 2 | 4 | 3 | 1 | §5 |
| research:quota | `QTA-` | 12 | 3 | 5 | 4 | 0 | **姊妹檔 Quota_Review**（§8） |
| design:architect（ADR-XPLAT-005） | — | 17 項 key decision ＋ 9 個 step ＋ 12 條 open question | — | — | — | — | **姊妹檔 Quota_Review**（全文另居 ADR 目錄） |
| review:SA | `SA-B*` | 7 blocking ＋ 9 non-blocking（verdict = **REJECT**） | — | — | — | — | **姊妹檔 Quota_Review** |
| review:SD | `SD-B*` | 4 blocking ＋ 7 non-blocking（verdict = **APPROVE_WITH_CONDITIONS**） | — | — | — | — | **姊妹檔 Quota_Review** |
| scan:ledger | `LDG-` | 34 | 1 | 6 | 16 | 11 | **姊妹檔**（§8） |

**findings 合計 83 筆**（六路掃描／調研，不含 ADR 與兩份 verdict；另 11 筆 blocking）。

> 🔴 上表的筆數與 severity 分佈是本檔生成當回合由 `findings[].severity` 現數的，不是抄來的。
> **原始 ID 在九路之間會重複**（多路都用 `S1-01`），故本檔一律加前綴；引用時請用帶前綴的形態。

## §2 scan:xplat — 跨平台相容性深掃（7 筆）

**任務**：找〈鐵律三〉對照表**表外**的新危害類，優先報「Windows 上看不見、只有 mac/Linux 會炸」的方向。

**agentId**：`a5bd928418b74a167`　**筆數**：7（P0 0／P1 3／P2 3／P3 1）

### §2.1 索引

| 本檔 ID | 原始 ID | sev | 標題（逐字） | 檔案:行 | 成本 |
|---|---|---|---|---|---|
| `XPL-S1-01` | S1-01 | P1 | `git ls-files` 的非 ASCII 路徑引號化，靠一個**未追蹤的 `.git/config`** 才沒炸；630 條 tracked 路徑受影響，且慣例無任何機械物 | tools/lib/self_help_exec_parity.py:48（違規站點）；.git/config（遮蔽來源）；tools/run_shellcheck.py:91；.github/workflows/root-infra-ci.yml:391 | medium |
| `XPL-S1-02` | S1-02 | P1 | BSD/GNU coreutils 掃描器的射程只有 29 支 `.sh`，`.yml` 一支都不看——而 macos-compat-ci 有 28 個 inline `run:` 跑在 macos-latest 上 | .github/workflows/macos-compat-ci.yml（28 個 run: 區塊）；.github/workflows/root-infra-ci.yml（3 筆 `date -d`）；tools/tests/test_bash32_compat.py（掃描面） | medium |
| `XPL-S1-03` | S1-03 | P1 | 跨平台 API 掃描器抓 `preexec_fn=`（POSIX-only），卻不抓它的鏡像 `creationflags=`／`startupinfo=`（Windows-only，POSIX 上直接 ValueError） | tools/tests/test_platform_neutral_paths.py:2770（只認 preexec_fn）；.claude/hooks/context_budget_guard.py:975,1026；.claude/hooks/sdd_hook_router.py:237；tools/session_resume_planner.py:404,531,1031 | small |
| `XPL-S1-04` | S1-04 | P2 | 掃描器只認 `os.` 與 `signal.` 兩個 owner，整個 `ctypes.*` 平面失明——`ctypes.windll` 在 POSIX 不存在，repo 有 9 個站點 | tools/tests/test_platform_neutral_paths.py:2760-2769（owner 判準）；tools/dev_start.py:675,680,685,973,977,979,1051；tools/tests/test_dev_start.py:1496,1506 | small |
| `XPL-S1-05` | S1-05 | P2 | `_POSIX_ONLY_SIGNALS` 只有 5 個成員，`SIGALRM`／`alarm`／`SIGPIPE`／`SIGCHLD` 全在表外——LATEST 框架版的兩支 hook 有 6 個站點 | tools/tests/test_platform_neutral_paths.py:2709；AISDLC_SDD/AISDLC_SDD_v0.30/.claude/hooks/closure_evidence_verify.py:95,96,106；AISDLC_SDD/AISDLC_SDD_v0.30/.claude/hooks/post_commit_drift.py:111,112,124 | small |
| `XPL-S1-06` | S1-06 | P2 | `sorted(Path)` 在 Windows 走 case-fold、在 POSIX 走原字元序 ⇒ `tree_fingerprint()` 的 digest 是平台相依的，正好抵銷 DEF-101-613「讓指紋跨平台一致」的修法 | tools/sync_onboarding_baselines.py:747（`for path in sorted(root.glob(pattern))`） | small |
| `XPL-S1-07` | S1-07 | P3 | 文字模式檔案 I/O 的預設編碼無人守：`open()` 今天 0 站點純靠自律，`read_text()`／`write_text()` 已有 9 個未帶 `encoding=` 的站點 | AutoClaude/tests/test_evaluator_kill_tree.py:110,140；AutoClaude/tests/test_perception.py:360,366,377,437；AutoClaude/tests/tools/test_run_act_core.py:81,97,98 | small |

### §2.2 逐筆（證據逐字保全）

#### `XPL-S1-01`｜[P1] `git ls-files` 的非 ASCII 路徑引號化，靠一個**未追蹤的 `.git/config`** 才沒炸；630 條 tracked 路徑受影響，且慣例無任何機械物

- **檔案:行**：tools/lib/self_help_exec_parity.py:48（違規站點）；.git/config（遮蔽來源）；tools/run_shellcheck.py:91；.github/workflows/root-infra-ci.yml:391
- **成本**：medium

**為何要緊（逐字）**：這正是本 repo R73 已判過的病（`Find-GitBash` 把一台機器的安裝路徑寫成常數）的第二個入口，只是這次那個「機器的偶然事實」住在 `.git/config` 裡，連 grep 都掃不到。後果是**方向性的**：本機恆綠，mac 開發機／CI runner／任何 fresh clone 上這 630 條路徑變成打不開的字串——掃描面靜默縮小，而縮小的方向是「看起來更乾淨」（R76 Scan-H⑦ 同型）。self_help_exec_parity 還有 `_SELF_HELP_DEBT_FROZEN = 116` 這種**雙向精確比對**的計數，掃描面一漂移就是別台紅、本機綠。今天沒炸只是運氣：該消費者 `rel.endswith(".sh")` 過濾掉了全部非 ASCII（非 ASCII `.sh` 實測 0 支）——不是因為有人守著。

**當回合實測證據（逐字保全）**：

```text
當回合實測（probe5.py, rc=0）：
`git config --show-origin --get-all core.quotepath` → rc=0，`file:.git/config\tfalse`。`.git/config` 由 `git clone` 就地新建、**不是 tracked**，不隨 repo 走；git 內建預設是 `true`。
全庫 `git ls-files` = 27,566 條，其中**630 條非 ASCII**。同一支 `index_modes()` 在兩種設定下：
  quotepath=false → `AISDLC_SDD/AISDLC_SDD_v0.01/guides/user/sample/Devops-android手機APP_01_記帳軟體.md`
  quotepath=true  → `"AISDLC_SDD/.../Devops-android\346\211\213\346\251\237APP_01_\350\250\230\345\270\263\350\273\237\351\253\224.md"`
兩者 key 集合**差 630 筆**；C-quoted key 數 = 630，其中第一筆 `Path(ROOT/key).is_file()` → **False**（檔案靜默掉出掃描面）。
Grep 實測：repo 內約 15 個 `git ls-files`／`git diff` 站點**明文帶** `-c core.quotepath=false`（check_ntfs_paths.py:352、check_gha_action_versions.py:214、check_pytest_baseline_sites.py:168、tools/git-hooks/pre-commit:211 等），而 `tools/lib/self_help_exec_parity.py:48` 的 `["git","-C",str(repo_root),"ls-files","-s"]` **沒有**，也沒用 `-z`；`.github/workflows/root-infra-ci.yml` 同檔內 367 行有 `-c core.quotePath=false`、391 行沒有。
全庫 grep `quotepath`：沒有任何 tracked 檔會替 fresh clone 設定它（唯一的 `git config core.quotepath false` 在 AutoClaude/tests/test_playbook_runner.py:846，作用對象是測試用臨時 repo）。
```

**建議修法（逐字）**：

```text
①把 `-c core.quotepath=false`（或 `-z`）從「15 個站點各自記得」升成共用取數層：在 `tools/lib/` 開一支 `git_ls_files()` SSOT，全部消費者改走它；②補一支具名判準（掃 `.py`/`.sh`/`.yml` 內的 `git ... ls-files`／`diff --name-only`，未帶 `-z` 也未帶 `core.quotepath=false` 即紅，行尾豁免出口比照 `# ps-lint-ok`），並附合成注入紅綠自證；③判準要能在**本機**轉紅——不得依賴 `.git/config`，測試裡以 `-c core.quotepath=true` 明文構造對照組；④順手把 `.git/config` 那筆改成由 bootstrap 顯式設定並登記理由，或乾脆移除以免繼續遮蔽。
```

#### `XPL-S1-02`｜[P1] BSD/GNU coreutils 掃描器的射程只有 29 支 `.sh`，`.yml` 一支都不看——而 macos-compat-ci 有 28 個 inline `run:` 跑在 macos-latest 上

- **檔案:行**：.github/workflows/macos-compat-ci.yml（28 個 run: 區塊）；.github/workflows/root-infra-ci.yml（3 筆 `date -d`）；tools/tests/test_bash32_compat.py（掃描面）
- **成本**：medium

**為何要緊（逐字）**：這條紀律的知識已經寫得很完整（連 `tools/macos_smoke_local.sh:39-40` 都逐字複述一遍），但**同一份知識住兩個家、只有 `.sh` 那個家被鎖**——正是 R73 判過的形態。危害面是不對稱的：Windows 開發機上的 Git Bash 帶的是 **GNU** userland、ubuntu CI 也是 GNU，兩邊都會給出「這樣寫沒問題」的假訊號；只有 macos-latest 的 BSD userland 會炸，而那 28 個 run: 區塊剛好就是唯一跑在那裡的東西，也剛好一個觀測者都沒有。root-infra-ci 那 3 筆 `date -d` 今天安全純粹因為它只跑 ubuntu——但它與 macos-compat-ci 是同一個目錄下的姊妹檔，複製一段 step 過去或替 root-infra 加一個 macos job 都不會有任何東西轉紅。

**當回合實測證據（逐字保全）**：

```text
當回合實測（probe7.py + probe8.py，皆 rc=0）：
`test_bash32_compat._scan_trees()` 實跑回傳 6 棵、合計 **29 支檔**，副檔名集合 = `['.sh', '<none>']`，`any .yml/.yaml in surface? False`。
用**該掃描器自己的 `_PATTERNS` 與 `_split_code_comment`** 去掃 12 支 workflow 的 inline `run:` 區塊 → 命中 **3 筆**，全在 `root-infra-ci.yml`：
  `if ! waiver_deadline=$(date -u -d "${WAIVER_UNTIL} 23:59:59" +%s 2>/dev/null); then`
  `age=$(( (now - $(date -u -d "$last" +%s)) / 86400 ))`
  `if a_epoch=$(date -u -d "$a_when" +%s 2>/dev/null); then`
  → 皆判為「date -d（GNU；BSD date 用 -v/-j -f）」
 runs-on 實測：`root-infra-ci.yml` = ['ubuntu-latest']（17 個 run:）；`macos-compat-ci.yml` = ['macos-latest','ubuntu-latest']（**28 個 run:**）。
該掃描器檔頭第 7~8、16~17 行逐字寫著 B 組要防的就是 `grep -P／readlink -f／sed -i／stat -c／date -d／timeout／xargs -r／find -printf`。
```

**建議修法（逐字）**：

```text
把 `test_bash32_compat.py` 的掃描面從「tracked `.sh` + git-hooks」擴到 `.github/workflows/*.yml` 的 inline `run:` 區塊（複用既有 `_PATTERNS` 與 `_split_code_comment`，不新增第二份規則表——避免再開一個會漂移的家）。至少對 `runs-on` 含 `macos-latest` 的 job 判紅；ubuntu-only job 可先只登記不判（或判 warn），但要把 `runs-on` 當成判準輸入而不是寫死。順手替 root-infra 那 3 筆補 `# bash4-ok: ubuntu-only job` 之類的行尾豁免並註明理由，讓「哪些是刻意的」變成可查的量測值。
```

#### `XPL-S1-03`｜[P1] 跨平台 API 掃描器抓 `preexec_fn=`（POSIX-only），卻不抓它的鏡像 `creationflags=`／`startupinfo=`（Windows-only，POSIX 上直接 ValueError）

- **檔案:行**：tools/tests/test_platform_neutral_paths.py:2770（只認 preexec_fn）；.claude/hooks/context_budget_guard.py:975,1026；.claude/hooks/sdd_hook_router.py:237；tools/session_resume_planner.py:404,531,1031
- **成本**：small

**為何要緊（逐字）**：這是最能說明問題的一筆：掃描器作者**明確想過這對 kwarg**（POSIX-only 那一側是逐字寫死的特例判準），卻只補了一邊——而漏掉的正好是「Windows 上寫得出來、mac 上必炸」的那個方向，也正是〈鐵律三〉整節在防的思考慣性（R71 修 DEF-101-759 時寫出 DEF-101-766 的同一個病）。今天 8 個站點全部安全，只因為它們一律走 `context_budget_guard.NO_WINDOW`，而那個常數用 `getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(..., 0)` 在 POSIX 取 0（`creationflags=0` 不觸發 raise）——這是一個人在一個地方做對了，不是一道門。下一個直接寫 `creationflags=subprocess.CREATE_NO_WINDOW` 的人，會讓那支 hook 在 macOS 上當場 ValueError，而本機不會有任何東西轉紅。

**當回合實測證據（逐字保全）**：

```text
當回合實測（probe3.py, rc=0）：
以 `inspect.getsource(subprocess.Popen.__init__)` 讀**本機實際會跑的 stdlib 原始碼**，三行 raise 並存：
  `creationflags` → `raise ValueError("creationflags is only supported on Windows "`
  `startupinfo`   → `raise ValueError("startupinfo is only supported on Windows "`
  `preexec_fn`    → `raise ValueError("preexec_fn is not supported on Windows "`
掃描器 `_foreign_api_uses()` 第 2770 行只有 `node.arg == "preexec_fn"` 一個 keyword 判準；對 `creationflags`／`startupinfo` 零判準。
全活躍面（排除 v0.01~v0.29 凍結版）掃出 `creationflags=` **8 個站點 / 4 個檔**（上列）。
對照組：同一支掃描器對合成片段裡的 `os.startfile` 正常命中（`[(7,'Windows-only','os.startfile')]`）⇒ 掃描器本身沒壞，是詞彙表缺這一半。
```

**建議修法（逐字）**：

```text
在 `_foreign_api_uses()` 既有的 `ast.keyword` 分支旁補對稱判準：`node.arg in {"creationflags","startupinfo"}` → `("Windows-only", ...)`。既有的站點級守衛（enclosing-if／early-return-guard／try-capability）會自動套用，所以 `arm_sentinel()` 那個 `if os.name != "nt": return` 的站點會被正確特赦；`NO_WINDOW` 常數那條則需明文豁免（`getattr` 兜底已是正解，用行尾 xplat-ok 標記登記理由）。順帶把 `_WINDOWS_ONLY_OS_ATTRS` 這類「手抄封閉清單」加一條後設判準：清單成員數只准上升（同覆蓋率棘輪精神）。
```

#### `XPL-S1-04`｜[P2] 掃描器只認 `os.` 與 `signal.` 兩個 owner，整個 `ctypes.*` 平面失明——`ctypes.windll` 在 POSIX 不存在，repo 有 9 個站點

- **檔案:行**：tools/tests/test_platform_neutral_paths.py:2760-2769（owner 判準）；tools/dev_start.py:675,680,685,973,977,979,1051；tools/tests/test_dev_start.py:1496,1506
- **成本**：small

**為何要緊（逐字）**：判準寫成 `owner == "os"` / `owner == "signal"` 這種逐一列舉的形狀，代價是**新增一個 owner 就整片失明**，而失明是靜默的：掃描器照跑、照綠、照回報命中數，只是那一族從來不在分母裡。`ctypes.windll`／`WinDLL`／`OleDLL` 在 macOS/Linux 的 `ctypes` 上根本不存在（AttributeError），而 dev_start.py 是 mac 側 `dev_start.sh` 的共用後端——這一族一旦有人漏守衛，炸點會落在開發者「第一次在 mac 上開工」的那一步。這也是 CLAUDE.md 表格自陳「有機械物」的那一列（`$IsWindows` 等 PS 6+ 專屬／platform-neutral）在 Python 側的實際覆蓋缺口，屬於**低報分子**的反面：分子被算成 1，實際只覆蓋該類的一部分。

**當回合實測證據（逐字保全）**：

```text
當回合實測（probe2.py / probe3.py，皆 rc=0）：
合成片段（3 個 `ctypes.windll` + 1 個 `os.startfile`）餵給 `_foreign_api_uses()` → 回傳 **只有** `[(7, 'Windows-only', 'os.startfile')]`，3 個 `ctypes.windll` 一個都沒抓到。
對真實檔 `tools/dev_start.py`：字面 `ctypes.windll` 出現 **7 次**，掃描器在該檔的全部命中是 `[(251,'os.killpg'),(262,'os.killpg'),(262,'signal.SIGKILL'),(1018,'os.killpg'),(257,'os.killpg')]` ⇒ 對 `ctypes.windll` **0 命中**。
全活躍面掃出 `ctypes.windll` **9 個站點 / 2 個檔**。
程式碼實查：`tools/dev_start.py:672` 是 `if platform_utils.is_windows():`，即現有站點**確實有守衛**（且 `is_windows` 已在掃描器的 `_PLATFORM_DECIDING_SYMBOLS` 裡）⇒ 今天沒有 live 缺陷，缺的是門。
```

**建議修法（逐字）**：

```text
把 owner 判準由硬編碼的兩個字串改成一張 `{owner: {attr: 方向}}` 表，先補 `ctypes`（`windll`／`WinDLL`／`OleDLL`／`oledll`／`WINFUNCTYPE`／`FormatError` → Windows-only）與 `subprocess`（`CREATE_*`／`STARTUPINFO`／`DETACHED_PROCESS` → Windows-only）。同時補一支後設鎖：表內 owner 數與 attr 數只准上升（比照〈鐵律三〉覆蓋率棘輪），並以合成注入證明每個新 owner 都真的會轉紅。
```

#### `XPL-S1-05`｜[P2] `_POSIX_ONLY_SIGNALS` 只有 5 個成員，`SIGALRM`／`alarm`／`SIGPIPE`／`SIGCHLD` 全在表外——LATEST 框架版的兩支 hook 有 6 個站點

- **檔案:行**：tools/tests/test_platform_neutral_paths.py:2709；AISDLC_SDD/AISDLC_SDD_v0.30/.claude/hooks/closure_evidence_verify.py:95,96,106；AISDLC_SDD/AISDLC_SDD_v0.30/.claude/hooks/post_commit_drift.py:111,112,124
- **成本**：small

**為何要緊（逐字）**：與 S1-04 同一個根（手抄封閉清單），但危害面更貼近使用者：這兩支是**框架發給使用者的 `.claude/hooks/`**，會在別人的專案裡跑。POSIX 訊號家族約 20 個，清單只涵蓋 5 個，缺的正好包含最常被誤用的 `signal.alarm`／`SIGALRM`（Windows 無）與 `SIGPIPE`（repo 自己有一支 `test_pre_commit_dispatcher_sigpipe.py` 在處理這個主題）。今天全部站點都正確用了 `hasattr` 分支，所以掃描器補不補都不影響現況——但這也意味著**沒有任何東西在保護那個 `hasattr` 分支不被下一個人拿掉**，而拿掉之後 Windows 上是 AttributeError、mac 上完全正常，方向與本 repo 平常擔心的相反。

**當回合實測證據（逐字保全）**：

```text
當回合實測（probe3.py, rc=0）：
`_POSIX_ONLY_SIGNALS` 實跑印出 = `['SIGHUP','SIGKILL','SIGQUIT','SIGUSR1','SIGUSR2']`（5 個）。
全活躍面掃出表外的 POSIX-only signal 站點 **6 筆 / 2 檔**，且**兩檔都在 `AISDLC_SDD_v0.30`（＝LATEST 活版，不是凍結版）**：`signal.SIGALRM` ×2、`signal.alarm` ×4。
程式碼實查（Read）：兩支都是 `has_alarm = hasattr(signal, "SIGALRM")` 再分支，Windows 走 ThreadPoolExecutor + `future.result(timeout=)`（closure_evidence_verify.py:93-116、post_commit_drift.py:109-135）⇒ 現有站點**寫得正確**，且掃描器的 `_capability_probed()` 本來就會因為 `hasattr` 探測而特赦它們。
```

**建議修法（逐字）**：

```text
把 `_POSIX_ONLY_SIGNALS` 補齊到 `signal` 模組在 POSIX 專屬的實際集合（`SIGALRM`／`SIGPIPE`／`SIGCHLD`／`SIGCONT`／`SIGSTOP`／`SIGTSTP`／`SIGWINCH`／`SIGBUS`／`SIGTRAP` 等）並納入函式名（`alarm`／`setitimer`／`getitimer`／`pthread_kill`／`sigwait`／`pause`），同時補 Windows-only 側的 `CTRL_C_EVENT`／`CTRL_BREAK_EVENT`。更好的作法是**不要手抄**：以 `set(dir(signal))` 在兩平台的差集當資料來源產生清單並釘住，讓「Python 升版新增訊號」不會靜默擴大盲區。
```

#### `XPL-S1-06`｜[P2] `sorted(Path)` 在 Windows 走 case-fold、在 POSIX 走原字元序 ⇒ `tree_fingerprint()` 的 digest 是平台相依的，正好抵銷 DEF-101-613「讓指紋跨平台一致」的修法

- **檔案:行**：tools/sync_onboarding_baselines.py:747（`for path in sorted(root.glob(pattern))`）
- **成本**：small

**為何要緊（逐字）**：DEF-101-613 特地把 hash 前的 bytes 折行尾，明說目的是讓指紋在 macOS／CI 上對得上；但**排序這一軸沒有一起處理**，等於同一個目標留了第二個入口沒關。今天分歧是 0，所以它是純潛伏——但觸發條件低到不像話：任何人往那四棵樹丟一支 `Test_Foo.py`（大寫開頭）就會讓 Windows 與 macOS 算出**位元組完全相同、指紋卻不同**的結果。而這個指紋是 `--check-snapshot` 判定 ONBOARDING §7 表② 是否 stale 的唯一因果觸發器，失效表徵是「在 mac 上開箱即紅、且紅得沒有道理」——最容易被下一個人當成 flaky 而整條關掉。

**當回合實測證據（逐字保全）**：

```text
當回合實測（probe8.py, rc=0）機制自證：
  輸入 `['README.md','readme_extra.md','Test_A.py','test_b.py']`
  `sorted(key=PureWindowsPath)` → `['README.md','readme_extra.md','Test_A.py','test_b.py']`
  `sorted(key=PurePosixPath)`   → `['README.md','Test_A.py','readme_extra.md','test_b.py']`
  same order? **False**
對四棵真實指紋樹逐棵比對（probe2.py, rc=0）：v001(54 檔)／v030(78)／scripts(29)／autoclaude(282)，`win_order == posix_order` 皆 **True** ⇒ **今天 0 分歧**（該四棵檔名目前全無大小寫混排會翻序的組合）。
程式碼實查：`tools/sync_onboarding_baselines.py:746-751` 先 `digest = hashlib.sha256()`，再 `for path in sorted(root.glob(pattern))`，逐檔 update `path.relative_to(root).as_posix()` 與 `_normalize_eol(bytes)` ⇒ **順序直接進 digest**。同檔 41-45 行逐字記載 DEF-101-613 的立案理由正是「fresh clone／CI runner／macOS 上四格必然全部對不上」，修法是行尾正規化。
```

**建議修法（逐字）**：

```text
把 `sorted(root.glob(pattern))` 改成對**平台中立的鍵**排序：`sorted(root.glob(pattern), key=lambda p: p.relative_to(root).as_posix())`（digest 本來就是用這個字串當鍵，兩者對齊也更誠實）。同時補一支自證測試：以合成檔名集合斷言 `PureWindowsPath` 與 `PurePosixPath` 兩種排序下 digest 相同——這支測試在 Windows 上就跑得出紅綠，不必等 mac 真機。
```

#### `XPL-S1-07`｜[P3] 文字模式檔案 I/O 的預設編碼無人守：`open()` 今天 0 站點純靠自律，`read_text()`／`write_text()` 已有 9 個未帶 `encoding=` 的站點

- **檔案:行**：AutoClaude/tests/test_evaluator_kill_tree.py:110,140；AutoClaude/tests/test_perception.py:360,366,377,437；AutoClaude/tests/tools/test_run_act_core.py:81,97,98
- **成本**：small

**為何要緊（逐字）**：CLAUDE.md 表格的「console 編碼」那一列指向的機械物，實際射程是 subprocess 與 stdio，不含檔案 I/O——這是一個**射程比欄名窄**的情況（同 R78 對「行尾」欄名的訂正）。`open()` 現在是 0 站點，看起來很乾淨，但那是紀律的結果不是門的結果：`locale.getpreferredencoding()` 在 mac 是 UTF-8、在 Windows 非 UTF-8 codepage 下是 CP950，而本 repo 幾乎每個檔都有中文。今天被 `PYTHONUTF8=1` 全面遮蔽（九支本機閘門都硬設它，R74 已判過這正是「把區分本機與雲端的變數正規化掉」），所以連 Windows 側都測不出來。9 個既存站點都在 AutoClaude 測試裡、影響有限，故列 P3；真正的缺口是寫入面沒有門。

**當回合實測證據（逐字保全）**：

```text
當回合實測（probe1.py, rc=0，AST 掃全活躍面）：
  `open()` 無 `encoding=` 且非 binary mode → **0 站點**
  `Path.read_text()` 無 `encoding=` → **4 站點**
  `Path.write_text()` 無 `encoding=` → 初掃 6，逐行複核後**扣掉 1 筆誤報**（`tools/tests/test_doc_loc_baseline_freshness_r60.py:2691` 是 `write_text(..., "utf-8")`＝位置引數傳編碼，我的 AST 判準只看 keyword 才誤標）⇒ 實為 **5 站點**，合計 9。
本機執行環境：`PYTHONUTF8=1`、`locale.getpreferredencoding(False)=utf-8`。
既有機械物射程實查（Grep `tools/tests/test_subprocess_encoding_hygiene.py` 的類別/常數）：`_FUNC_TAILS = {run, Popen, check_output, check_call, call}`、`TestSubprocessEncodingHygiene`／`TestChildEncodingHygiene`／`TestEntryPointStdioProtection`／`TestRegisteredHookScriptsAreInChildEncodingScope` ⇒ 全部圍繞 **subprocess 子行程與 entry-point stdio**，對 `open()`／`read_text()`／`write_text()` **零判準**。
```

**建議修法（逐字）**：

```text
比照〈鐵律三〉表上「`Get-Command` 解析」那一列已被接受的形狀（存量 0 也值得立門）：在 `test_subprocess_encoding_hygiene.py` 或 `test_platform_neutral_paths.py` 補一支 AST 判準——文字模式的 `open()`／`Path.open()`／`read_text()`／`write_text()` 必須明示 `encoding=`（位置引數也算，別重蹈我這次的誤報），行尾 `# encoding-ok: <WHY>` 豁免。先把 9 個既存站點補上 `encoding="utf-8"`（都是測試，改動風險極低），再把判準接進根層 unittest 閘門。
```

### §2.3 本路 `verified_commands`（逐字保全）

```text
全部在 PowerShell 工具內執行（Bash 工具已依鐵律一禁用）。python 一律絕對路徑 `D:\CursorProject\AISDCL_Agent\.venv\Scripts\python.exe`。

1) Bash 工具 `echo probe` → **被 PreToolUse hook 攔下**（`block_bash_on_windows.py`，非 rc；確認守衛活著）
2) `& '<py>' -c 'import sys,platform; print(sys.version); print(platform.platform())'` → rc=0；`3.11.9`、`Windows-10-10.0.26200-SP0`
3) `& '<py>' <scratchpad>\probe1.py` → **rc=0**（AST 掃活躍面文字 I/O：open 0／read_text 4／write_text 6〔複核後 5〕／parse failures 0；PYTHONUTF8=1；getpreferredencoding=utf-8）
4) `& '<py>' <scratchpad>\probe2.py` → **rc=0**（四棵指紋樹 win/posix 排序比對皆 True；`_foreign_api_uses` 對合成 3×ctypes.windll 命中 0、對 os.startfile 命中 1；dev_start.py 字面 7 次 / 掃描器 0 命中）
5) `& '<py>' <scratchpad>\probe3.py` → **rc=0**（`inspect.getsource(subprocess.Popen.__init__)` 印出 creationflags/startupinfo/preexec_fn 三行 raise；詞彙表 modules=8／os_attrs=16／signals=5；表外命中：creationflags 8 站點/4 檔、ctypes.windll 9 站點/2 檔、signal POSIX-only 6 站點/2 檔）
6) `& '<py>' <scratchpad>\probe5.py` → **rc=0**（`git config --show-origin --get-all core.quotepath` rc=0 → `file:.git/config false`；index_modes 三種取法皆 27,566 keys，true/false 差 **630**；C-quoted key 630，首筆 `is_file()` → False；`.sh` 面 168/168 無差、非 ASCII `.sh` = 0；NFD 檢查：非 ASCII 630 條中可分解者 **0**）
7) `& '<py>' <scratchpad>\probe6.py` → **rc=0**（os.environ 大小寫：設 `R81CaseProbe` 讀 `R81CASEPROBE` → `'v'`；非大寫 env 讀取 3 筆皆 `ComSpec`；bare rmtree 2 筆；tempdir `.resolve()` 在 Windows 為 identity；asyncio/socket/locale 面近乎 0）
8) `& '<py>' <scratchpad>\probe7.py` → **rc=0**（`_scan_trees()` 六棵 29 檔、副檔名 `['.sh','<none>']`、`.yml` 不在射程；12 支 workflow 的 inline run: 以該掃描器自身 `_PATTERNS` 掃出 3 筆 `date -d`，全在 root-infra-ci.yml）
9) `& '<py>' <scratchpad>\probe8.py` → **rc=0**（root-infra-ci runs-on=['ubuntu-latest'] / 17 run:；macos-compat-ci runs-on=['macos-latest','ubuntu-latest'] / **28 run:**；sorted(Path) 合成集合 win≠posix 排序）
10) PowerShell 直跑 git 取數（Push-Location/Pop-Location 成對）：`git ls-files` → rc=0、27,566 條；非 ASCII 630 條；最長 tracked 相對路徑 142 字元
11) PowerShell 直跑：`git config --show-origin --get-all core.quotepath` → rc=0 `file:.git/config false`；`git -c core.quotepath=true|false ls-files -- '<guides/user/sample>'` 兩組輸出逐字對照（八進位轉義 vs 原字）

Read/Grep 工具（不經 shell）核對的權威源：CLAUDE.md:245-275〈鐵律三〉表；tools/tests/test_platform_neutral_paths.py:2698-2778、2805-2838；tools/tests/test_subprocess_encoding_hygiene.py 類別/常數清單；tools/tests/test_bash32_compat.py:5-119；tools/sync_onboarding_baselines.py:616-646、724-767；tools/lib/self_help_exec_parity.py:40-127；.claude/hooks/context_budget_guard.py:220-267、955-1027；tools/session_resume_planner.py:390-419；tools/dev_start.py:660-694；AISDLC_SDD_v0.30/.claude/hooks/{post_commit_drift.py:96-135, closure_evidence_verify.py:82-116}；.github/workflows/macos-compat-ci.yml:1-669。
```

### §2.4 本路 `honest_gaps`（逐字保全）

```text
**唯讀執行，未改任何檔**（符合指示）。以下誠實劃界：

1. **沒有 mac 真機，凡「mac 上會怎樣」皆非親測。** 具體地：
   - S1-03 的 POSIX 致命性，證據是**本機 stdlib 原始碼**裡的 `raise ValueError(...)` 三行，不是在 POSIX 上跑出來的例外。
   - S1-06 的 POSIX 排序，用 `PurePosixPath` 當 key 在 Windows 上做代理量測，不是真的在 mac 上 `sorted(PosixPath)`。
   - S1-01 的「fresh clone 會拿到 quotepath=true」，證據是 `--show-origin` 顯示唯一來源是未追蹤的 `.git/config` ＋ git 文件化預設，**我沒有真的另做一次 clone 驗證**。
2. **macOS NFD 這條線我查了、結論是不存在，故未列入 findings**：630 條非 ASCII tracked 路徑中 `NFD(x) != x` 的有 **0** 條（漢字不可分解）。若未來加入帶重音符號的檔名，這條會重新活過來。
3. **`.github/workflows/macos-compat-ci.yml` 我只讀了 1114 行中的 1-669。** 那 28 個 inline `run:` 是用正則對全檔計數的，我**沒有逐一讀完**它們的內容 ⇒ S1-02 我只能宣稱「掃描器結構上看不到它們」，**不能**宣稱「它們裡面有／沒有 BSD 不相容的寫法」。用該掃描器 `_PATTERNS` 自動掃的結果是該檔 0 命中，但那組 pattern 本身只涵蓋 8 類 GNU-only 選項，不是 BSD 相容性的完整判準。
4. **一律靜態＋探針，未跑任何閘門。** 沒跑 `run_root_unittests.py`、pytest、ci-gate、act。所以「這些 findings 不會讓現有閘門轉紅」是我的推論而非實測——特別是 S1-06 的修法（改 sort key）是否會改動 ONBOARDING §7 已回填的四棵指紋值，**我沒有實算**（今天四棵 win/posix 同序，理論上不變，但沒驗）。
5. **查了但判定不值得列入 findings 的**（避免灌水，一併誠實交代）：
   - `os.environ` 大小寫（Windows 不分、POSIX 分）：機制為真且不在表上，但 3 個站點全是 `os.environ.get("ComSpec", "")` 帶預設值，其一還在 `if os.name == "nt":` 內 ⇒ 零 live 缺陷，門的價值也低。
   - `shutil.rmtree` 未帶 `ignore_errors/onerror/onexc`：2 個站點，皆在 `tools/tests/test_dev_start.py`，且同檔已有 `_rmtree_force` helper ⇒ 屬同檔慣例不一致，非跨平台缺口主線。
   - macOS `tempfile.gettempdir()` 的 `/var → /private/var` symlink：我只證明了 **Windows 上 `.resolve()` 是 identity**，**沒有找到任何一個會因此壞掉的具體站點**（沒去做「tempdir 路徑與 resolve 後路徑相比較」的站點級掃描）⇒ 不列為 finding，留給下輪。
   - GNU/BSD coreutils 在 `.sh` 側：`test_bash32_compat.py` 覆蓋完整（A 組 bash4 語法 + B 組 8 類 GNU-only 選項，含合成注入紅綠自證）⇒ **不是**缺口，我原本以為是，實查後撤回。
   - Homebrew arm64/Intel 路徑分歧：`tools/lib/windowsapps_guard.sh:83-84` 已同時涵蓋 `/opt/homebrew` 與 `/usr/local` ⇒ 已有人守。
6. **S1-03/04/05 同源。** 三者都是 `_foreign_api_uses()` 手抄封閉清單的不同縫；我拆成三筆是因為修法、詞彙表位置與 live 站點集合各自獨立，但若貴輪的記帳方式偏好單筆，可合併成「跨平台 API 詞彙表無完整性判準」一筆，分子分母請據此調整，別重複計數。
7. **S1-01 的嚴重度我拿不太準。** live 危害today = 0（該消費者過濾 `.sh`，非 ASCII `.sh` 為 0），我判 P1 的理由是「本機 `.git/config` 會遮蔽掉未來任何違規」這個結構性失明，而非現有損害。若貴輪的 P1 定義要求 live 損害，這筆應降為 P2。
```

## §3 scan:subtraction — 架構減法（8 筆）

**任務**：找可**刪除或合併**的護欄與重複模組，每筆要有「為什麼刪掉是安全的」的實測論證。

**agentId**：`af115ee3a2ee3d1d5`　**筆數**：8（P0 2／P1 3／P2 1／P3 2）

### §3.1 索引

| 本檔 ID | 原始 ID | sev | 標題（逐字） | 檔案:行 | 成本 |
|---|---|---|---|---|---|
| `SUB-S1-01` | S1-01 | P0 | compat-CI 的 `paths` 白名單：925 行手工清單 ×4 份近乎相同的複本，外加 1,566 行專門用來對帳它的鎖 | .github/workflows/windows-compat-ci.yml:205 與 :465；.github/workflows/macos-compat-ci.yml:74 與 :341；AISDLC_SDD/scripts/tests/test_ci_paths_cover_root_consumers.py:264 | medium |
| `SUB-S1-02` | S1-02 | P0 | 五支雲端 workflow 自 2026-08-07 起每次 push 都在數秒內 failure、零步驟執行 ⇒ 整個「workflow 設定護欄」子層目前零鑑別力，且 38/43 支本機 skip 的指定跑道已死 | .github/workflows/（全部 5 支）；tools/lib/ci_liveness.py | medium |
| `SUB-S1-03` | S1-03 | P1 | `guardrail_lib ≤400` LOC tier 套在 tools/lib/ 上，純機械分檔製造了 +877 行與一支 368 行「只做再匯出」的門面；下一次分檔已經排隊（hook_wiring.py 407/400 現正紅） | tools/lib/windows_skip_tags.py:1-30 與 :353-368；AutoClaude/tools/check_loc_budget.py:270 | medium |
| `SUB-S1-04` | S1-04 | P1 | 7 支 hook payload 讀取器，6 支逐字相同、卻已漂移成 3 種不同行為（實測），而所有消費端都已經有共用層可用 | AutoClaude/tools/hooks/check_lang.py:40、check_sh_eol.py:97、enforce_docs_path.py:59、loc_budget_check.py:50、check_ps1_encoding.py:62；.claude/hooks/lint_powershell_command.py:494、context_budget_guard.py:1093 | small |
| `SUB-S1-05` | S1-05 | P1 | `index_modes()` 與它的 exec-bit 判準逐字住兩個家——而第二個家是 R80 減法包自己新建的 SSOT | tools/lib/self_help_exec_parity.py:34,45；tools/tests/test_platform_neutral_paths.py:3576,3578,3589 | small |
| `SUB-S1-06` | S1-06 | P2 | 攔截器與量測器共用判準卻各存一份複本，理由（「hook 只能是被抄的一方」）已被同一支檔案自己的程式碼推翻 | tools/probe/audit_session.py:133,152,327,338,347；.claude/hooks/lint_powershell_command.py:115,127,212,213 | small |
| `SUB-S1-07` | S1-07 | P3 | 三支 probe 是同型物（其中一支逐字自稱），可收成單一入口的三個子命令 | tools/probe/misstep_attribution.py:11,29-33；tools/probe/reset_window_distribution.py:7,24-25；tools/probe/audit_session.py:65-71 | small |
| `SUB-S1-08` | S1-08 | P3 | `_git()` 在兩支 dispatcher 測試檔逐字重複 | tools/tests/test_pre_commit_dispatcher_sigpipe.py（`_git`）；tools/tests/test_pre_push_dispatcher.py（`_git`） | small |

### §3.2 逐筆（證據逐字保全）

#### `SUB-S1-01`｜[P0] compat-CI 的 `paths` 白名單：925 行手工清單 ×4 份近乎相同的複本，外加 1,566 行專門用來對帳它的鎖

- **檔案:行**：.github/workflows/windows-compat-ci.yml:205 與 :465；.github/workflows/macos-compat-ci.yml:74 與 :341；AISDLC_SDD/scripts/tests/test_ci_paths_cover_root_consumers.py:264
- **成本**：medium

**為何要緊（逐字）**：這是本 repo 最典型的「同一份知識住四個家」——而且第四個家（那道 1,566 行的鎖）唯一的職責就是替前三個家對帳。它換到的東西只有 CI 分鐘數；付出的是 925 行手工清單、72 次人工補列、7 個相同族缺陷號，以及每次新增根層消費檔時的一道必踩地雷。`root-infra-ci.yml` 已用「不設 paths」證明這個取捨可以反過來做。

**當回合實測證據（逐字保全）**：

```text
實測（本回合）：
(1) 逐 block 量測 `pathsblocks.py`：
    macos-compat-ci.yml:74  paths block = 266 lines, 108 glob entries
    macos-compat-ci.yml:341 paths block = 199 lines, 108 glob entries
    windows-compat-ci.yml:205 paths block = 259 lines, 107 glob entries
    windows-compat-ci.yml:465 paths block = 201 lines, 107 glob entries
    TOTAL lines inside paths blocks: 1003
(2) 集合比對：`macos-compat-ci.yml:341 vs :74  shared=108 only_here=0 only_there=0`（檔內兩份 100% 相同）；`windows-compat-ci.yml:205 vs macos:74  shared=96 only_here=11 only_there=12`。
(3) 最長逐字相同連續段：`mac86 vs win220 = 74 行`、`mac86 vs mac353 = 61 行`、`win220 vs win479 = 53 行`。
(4) 這份清單的維護成本有帳可查：workflow 檔內 `DEF-101-042` 回指共 **72 次**（macos 34／windows 33／aisdlc-sdd 5），每一次都標記一次「有人漏補 paths、被鎖抓到後手動補列」。
(5) 對帳鎖本體 `AISDLC_SDD/scripts/tests/test_ci_paths_cover_root_consumers.py` = **1566 行**，其 `_workflow_paths()` 逐字 `return on["push"]["paths"], on["pull_request"]["paths"]` —— 「雙邊都要列」就是檔內兩份複本存在的原因。該檔 docstring 引用 7 個相異 DEF 號（DEF-101-037/042/068/281/286/400/721），全是同一族「paths 漏列 ⇒ 只改根層消費檔不觸發 CI」。
(6) `root-infra-ci.yml` 已經做過相反的決定並寫在檔頭：**刻意不設 paths 過濾**。
(7) PR 面實測：`git rev-list --count --merges HEAD` = **0**；`git branch -r` 只有 `origin/main`；`gh pr list --state all` 共 9 筆，最後一筆 2026-07-13（R15 前後），其中 8 筆是 dependabot。
```

**建議修法（逐字）**：

```text
分兩段，先做保守那段：
① 立刻可做（−400 行，覆蓋率只升不降）：刪掉兩支 compat-CI 的 `pull_request.paths` 兩個 block（macos:341 的 199 行、windows:465 的 201 行），`pull_request` 觸發改為無 paths 過濾。代價＝dependabot 那類 PR（近 4 個月 9 筆）會多跑一次 compat-CI；收益＝清單從此只有一個家，且 `_workflow_paths()` 的 pull_request 那一半連同它的雙邊斷言可以一起刪。
② 建議與舵手拍板（−925 行 + 該鎖大部分，合計約 −2,000 行）：compat-CI 比照 `root-infra-ci.yml` 完全不設 paths。此後 DEF-101-042 這一族在結構上消失（沒有白名單就沒有漏列），1,566 行的對帳鎖只需保留「root-infra 那一半」的設計決策鎖。
🔴 不要反過來做：不要再蓋一支「檢查四份 paths 是否一致」的新鎖——那是第五個家。
```

#### `SUB-S1-02`｜[P0] 五支雲端 workflow 自 2026-08-07 起每次 push 都在數秒內 failure、零步驟執行 ⇒ 整個「workflow 設定護欄」子層目前零鑑別力，且 38/43 支本機 skip 的指定跑道已死

- **檔案:行**：.github/workflows/（全部 5 支）；tools/lib/ci_liveness.py
- **成本**：medium

**為何要緊（逐字）**：本 repo 為「workflow 設定不能寫錯」蓋了一整層護欄（paths 對帳 1566、permissions/concurrency 鎖 1357、action 版本鎖 703+295+458、runner label 白名單、workflow timeout 覆蓋、smoke/CI 同步 1355、排程能力對等 591…約 9,000 行），而它們守的那個東西**已經連續 4 次 push 沒有執行過任何一個步驟**。同時 38 支測試在本機 skip、在雲端也跑不到 ⇒ 它們今天在任何地方都沒有被執行。這正是「恆綠＝零鑑別力」的系統級版本，而且沒有任何機械物會出聲——`ci_liveness.py` 結構上看不到 push 軌。

**當回合實測證據（逐字保全）**：

```text
實測（本回合 `gh run list`）：
  windows-compat-ci.yml 最近 8 次全 `failure`，7 次 createdAt→updatedAt 相差 3~14 秒；最新一次 `gh run view 31254543751` 顯示主 job `Windows smoke` startedAt 11:14:51 → completedAt 11:14:53（**2 秒**）、`"steps":[]`（一個步驟都沒跑）。
  macos-compat-ci / root-infra-ci / autoclaude-ci / aisdlc-sdd-ci 最近 4 次同樣全 failure，耗時 3~15 秒（唯一例外是 aisdlc-sdd-ci 2026-08-06 的 15 分鐘那次，之後就變成秒退）。
本機全套實測（`python -m pytest tools/tests -q -rs`，367.02s，rc=1）：`5 failed, 2418 passed, 43 skipped, 1439 subtests passed`。43 筆 skip 依標籤分群：**MAC-NATIVE-ONLY 24／POSIX-NATIVE-ONLY 14**／UNTAGGED 3／TOOL-MISSING 2。
這 38 筆 skip 的 reason 逐字寫著它們的跑道，例：`[MAC-NATIVE-ONLY] … 本鎖只在 macOS runner（macos-compat-ci.yml）上有意義，非 Darwin 平台跳過而非假綠`。
既有的活性偵測器 `tools/lib/ci_liveness.py` 的自述射程是「GitHub **排程**軌逐軌活性偵測」（DEF-101-703），push 軌不在它的視野內。
```

**建議修法（逐字）**：

```text
這一筆的正確處置不是刪程式碼，是先讓「雲端沒在跑」變成看得見的事：
① 把 `tools/lib/ci_liveness.py` 的射程由「排程軌」擴到「push 軌」，判準取「最近 N 次 run 的 `steps` 皆為空 ⇒ 這條軌沒有真的在跑」（不是看 conclusion——秒退的 conclusion 也是 failure，與真失敗同形）。這是**加行**，但它是 S1-01 的前置：不知道雲端死了，就無從判斷那 925 行白名單值不值得留。
② 在雲端恢復前，不要再為 workflow 設定新增任何鎖（新鎖今天一律恆綠）。
③ 38 支「指定跑道已死」的 skip 需要在收輪報告裡被計入「今天沒有任何地方跑到」，而不是計入 skipped 的正常水位。
```

#### `SUB-S1-03`｜[P1] `guardrail_lib ≤400` LOC tier 套在 tools/lib/ 上，純機械分檔製造了 +877 行與一支 368 行「只做再匯出」的門面；下一次分檔已經排隊（hook_wiring.py 407/400 現正紅）

- **檔案:行**：tools/lib/windows_skip_tags.py:1-30 與 :353-368；AutoClaude/tools/check_loc_budget.py:270
- **成本**：medium

**為何要緊（逐字）**：這是一條「不合理機制」的教科書案例：判準優化的是**單檔行數**，而 repo 付的是**總行數 + 一支純儀式的門面 + 五份 sys.path 接線**。它還會自我複製——`hook_wiring.py`（R80 才建的 hook 佈線 SSOT）今天就已 407/400 現正紅，下一輪要嘛重釘棘輪、要嘛照著訊息再拆一次，重演 +877。掌舵者要的是減法，而這條機制的存在本身就是加法的引擎。

**當回合實測證據（逐字保全）**：

```text
實測（本回合）：
(1) `AutoClaude/tools/check_loc_budget.py:270` → `"guardrail_lib": {"budget": 400, "patterns": ["tools/lib/"]}`。
(2) 跑 `python AutoClaude/tools/check_loc_budget.py --json`（rc=1）：
    root_tools_violations: `{'rel_path': 'tools/lib/hook_wiring.py', 'loc': 407, 'tier': 'guardrail_lib', 'budget': 400, 'over_by': 7}`
    root_tools_warn_band: `{'rel_path': 'tools/lib/skip_group_policy.py', 'loc': 395, 'budget': 400, 'headroom': 5}`
(3) `tools/lib/windows_skip_tags.py` 檔頭逐字自述：「R75 拆分：本檔原本一檔身兼四種職責（**508 code／727 raw 行**）。把 monorepo 根層 tools/ 納入 check_loc_budget.py 的 LOC 分級後，tools/lib/ 的 guardrail_lib tier ≤400 當場把它擋下」，並自稱「本檔保留三件事，**一件都不是業務邏輯**」，檔尾是一張 `__all__` 27 個名字的再匯出表。
(4) 拆後現況行數（本回合 inv.py 實量）：windows_skip_tags 368 + skip_tag_policy 596 + skip_static_scan 440 + skip_runtime_report 155 + skip_source_io 45 = **1,604 行**（skip_group_policy 591 是既有檔，未計）。對照拆前 727 raw ⇒ **淨增約 +877 行，零行為變化**。
(5) 該 tier 的違規訊息本身在指路加行：`"先刪死碼／抽共用模組（先例：tools/lib/ci_liveness.py）"`——「抽共用模組」就是製造下一支門面。
```

**建議修法（逐字）**：

```text
① 把 `tools/lib/` 從 `guardrail_lib ≤400` 的射程移出，或把 budget 改成對「政策資料表型模組」不適用（判準：模組內 `def` 少於 N 個、其餘是常數表 ⇒ 行數與複雜度不相關）。
② 之後把 `windows_skip_tags.py` 的 368 行門面刪掉，讓 `run_root_unittests.py` 直接 import 四支實作模組；或反向合回單一 `skip_policy.py`。預估 −500~−870 行。
🔴 保留一件事不能動：門面裡那幾支「把本模組命名空間的常數傳進實作」的薄包裝是 `test_run_root_unittests.py::test_hints_and_tag_are_shared_with_the_runtime_lock_not_copied` 的明文契約（mock.patch.object 注入要跟著變）。合併後那個契約自動成立（同一個模組），但要在合併的同一個 commit 裡確認該測試仍紅得起來。
```

#### `SUB-S1-04`｜[P1] 7 支 hook payload 讀取器，6 支逐字相同、卻已漂移成 3 種不同行為（實測），而所有消費端都已經有共用層可用

- **檔案:行**：AutoClaude/tools/hooks/check_lang.py:40、check_sh_eol.py:97、enforce_docs_path.py:59、loc_budget_check.py:50、check_ps1_encoding.py:62；.claude/hooks/lint_powershell_command.py:494、context_budget_guard.py:1093
- **成本**：small

**為何要緊（逐字）**：這與 R80 包 C 抓到的兩份 `_bash_exe`（一個 `except Exception`、一個 `except OSError`）是**同一個病、下一層**：宣稱「各自一份」的複本實際上是手抄本，抄完之後其中一份被改對了、其他四份沒跟上，而 repo 內零判準會轉紅。`enforce_docs_path.py` 是阻斷級 PreToolUse hook，它在這個輸入上直接死掉、判定根本沒產出。

**當回合實測證據（逐字保全）**：

```text
實測（本回合）：
(1) 正規化 AST 雜湊（unparse→剝 docstring→unparse→sha256）：`80f6d2343b6c` 共 4 份，各 15 行 —— check_lang / check_sh_eol / enforce_docs_path / loc_budget_check 的 `read_hook_payload`；`79b6854072f6` 共 2 份，各 21 行 —— lint_powershell_command / context_budget_guard 的 `read_payload`。
(2) 第 5 份 `check_ps1_encoding.py::read_hook_payload` 多一行守衛 `return obj if isinstance(obj, dict) else {}`，其餘逐字相同 ⇒ **它已經與另外四份漂移**。
(3) 行為差異實測（同一份輸入 `[1,2,3]`，合法 JSON 但頂層非 object，直接餵 stdin）：
    check_ps1_encoding.py   rc=0  stderr=''
    enforce_docs_path.py    rc=1  AttributeError: 'list' object has no attribute 'get'
    check_sh_eol.py         rc=0  但走自己的 fail-open：`[check_sh_eol] ALLOW: hook 自身異常 → fail-open：AttributeError(...)`
    loc_budget_check.py     rc=1  AttributeError（同上）
    check_lang.py           rc=1  AttributeError（同上）
  ⇒ 5 份、3 種行為、零測試在比對它們。
(4) 共用層是現成的：這 5 支**全部**已經 `sys.path.insert(..., 'tools'/'lib')`（check_lang:22、check_ps1_encoding:53、enforce_docs_path:23、check_sh_eol:73、loc_budget_check:22-23），且其中 3 支已經 `from hook_path_scope import ...`（同目錄共用層，3 個消費者）。
```

**建議修法（逐字）**：

```text
把 `read_hook_payload()` 收成一份放在 `tools/lib/`（新檔或併入既有 `platform_utils.py` —— 兩者的 sys.path 已經都接好了），採 `check_ps1_encoding.py` 那個**較嚴的**版本（含 `isinstance(obj, dict)` 守衛）。五支 AutoClaude hook 改 import；`.claude/hooks` 兩支同法（它們由 `_hook_launcher.py` 的 `runpy.run_path` 起，需在啟動器加一行把 `tools/lib` 放上 sys.path，而該啟動器的 fail-open 契約由 `tools/tests/test_check_hooks_liveness.py::TestHookLauncherContract` 守著，改完必須重跑它）。預估 −90 行，且順手修掉 3 份會拋 AttributeError 的守衛。
```

#### `SUB-S1-05`｜[P1] `index_modes()` 與它的 exec-bit 判準逐字住兩個家——而第二個家是 R80 減法包自己新建的 SSOT

- **檔案:行**：tools/lib/self_help_exec_parity.py:34,45；tools/tests/test_platform_neutral_paths.py:3576,3578,3589
- **成本**：small

**為何要緊（逐字）**：R73 的 `Find-GitBash` 判例（同一份知識住兩個家、只有一個家被改）在 R80 的**減法包自己身上**復發了一次：包 F 為了繞開 `check_script_parity.py` 的零餘裕 LOC 棘輪把判準抽成 `tools/lib/self_help_exec_parity.py`，抽的時候是**抄**了測試檔那份 `index_modes`，不是 import。兩個家各自帶著一個會漂移的凍結存量數（lib 側 `_SELF_HELP_DEBT_FROZEN=116`、測試側 `_BARE_SH_DOC_DEBT_FROZEN=87`），改了一邊另一邊不會紅。

**當回合實測證據（逐字保全）**：

```text
實測（本回合，同時載入兩份並對拍）：
  `E2 lib index_modes entries = 27566  test copy entries = 27566  identical = True`
正規化 AST 雜湊比對：`23932e8d5bde` 兩份，各 14 行 —— `tools/lib/self_help_exec_parity.py::index_modes` 與 `tools/tests/test_platform_neutral_paths.py::index_modes`。
重複的正則字面：`'(?<![\\w./-])\\./([A-Za-z0-9_./-]+\\.sh)\\b'` 兩份 —— lib 側叫 `_SELF_HELP_DOT_SLASH_RE`（:34），測試側叫 `_BARE_SH_INVOCATION_RE`（:3578）。常數 `_INDEX_MODE_EXEC = "100755"` 亦兩份（lib:35、測試:3576）。
可 import 性已由既有消費端證明：`tools/check_script_parity.py:135` 逐字 `from lib import self_help_exec_parity as _self_help`。
lib 側自己的 docstring 逐字承認兩者是同一件事：「本模組補的就是這一面（**同一條判準、換一個掃描面**）」。
```

**建議修法（逐字）**：

```text
`tools/tests/test_platform_neutral_paths.py` 刪掉自己那份 `index_modes()`／`_INDEX_MODE_EXEC`／`_BARE_SH_INVOCATION_RE`，改 `from lib import self_help_exec_parity`（該測試檔已在 sys.path 上放了 `tools/`，`check_script_parity.py` 的寫法可直接照抄）。兩個凍結存量常數保持各自獨立（它們量的是不同掃描面，這一半不是重複）。預估 −30 行，並讓「判準改一次、兩個掃描面同時生效」變成結構保證。
```

#### `SUB-S1-06`｜[P2] 攔截器與量測器共用判準卻各存一份複本，理由（「hook 只能是被抄的一方」）已被同一支檔案自己的程式碼推翻

- **檔案:行**：tools/probe/audit_session.py:133,152,327,338,347；.claude/hooks/lint_powershell_command.py:115,127,212,213
- **成本**：small

**為何要緊（逐字）**：這是「複本 + 對帳鎖」與「單一來源」之間選錯的一筆：付出＝兩份字典、3 個重複正則、一支專門比對它們的測試類，換到的鑑別力＝零（單一來源不可能漂移）。而它的理由是一個**自己的程式碼已經推翻**的前提，所以它會一直被當成「已論證過的設計決策」而不被複查。

**當回合實測證據（逐字保全）**：

```text
實測（本回合）：
重複正則字面 3 組，兩端逐字相同：
  `'#\\s*ps-lint-ok:\\s*\\S'` —— hook:115 `_EXEMPT_RE` ／ probe:327 `EXEMPT_RE`
  `'Find-GitBash'` —— hook:213 ／ probe:338（皆 `_FIND_GIT_BASH_RE`）
  `'\\.sh(?![\\w])'` —— hook:212 `_SH_SCRIPT_RE` ／ probe:347 `_CORROBORATORS['bare-bash-sh']`
另有整張 `SHARED_PATTERN_SOURCE` 字典兩份（hook:127、probe:152），probe 側註解逐字寫「**兩邊各存一份逐字相同的複本**」「修改守則：本字典要與 hook 那份逐字相同」。
維護這兩份一致所付的代價是第三個機械物：`tools/tests/test_check_hooks_liveness.py:1730 TestHookAndProbeShareOneCriterion`（:1710 起以 AST 抽字典做字面相等 + 行為一致雙向比對）。
🔴 該複本的理由（probe:129-134「那支 hook 由 runpy.run_path 起、sys.path 上沒有 tools/ ⇒ 它只能是被借的一方」）成立，但**推不出「所以 probe 要抄」**：probe:137-141 已經 `importlib.util.spec_from_file_location(...)` + `exec_module(_lint_ps_hook)` 把整支 hook 載進來，並逐字 `mask_regions = _lint_ps_hook.mask_regions`。方向本來就是 probe→hook，能借函式就能借常數。probe:133 自己也承認這一點（「而**函式**不必：本檔是 import 的一方，借得到就不該再抄」），只是沒把同一句話套到常數上。
史料佐證代價真的發生過：probe:146 記載 R77「hook 那份有 Tee-Object、本檔那份沒有，兩份零比對 ⇒ 同一條規則攔得下、卻量不到」。
```

**建議修法（逐字）**：

```text
`tools/probe/audit_session.py` 把 `SHARED_PATTERN_SOURCE`、`EXEMPT_RE`、`_FIND_GIT_BASH_RE` 與 bare-bash-sh 佐證正則全部改成向已載入的 `_lint_ps_hook` 借（形態與既有的 `mask_regions = _lint_ps_hook.mask_regions` 完全一致）。連帶刪掉 `TestHookAndProbeShareOneCriterion` 的**字面相等**那一向（單一來源後恆真），只留**行為一致**那一向（它守的是「同一批指令兩端判定相同」，那不是重複）。預估 −60 行（probe ~40 + 鎖 ~20）。
🔴 保留 hook 側為唯一定義處，方向不可反轉——hook 在 import 期爆掉會破壞它的 fail-open 契約。
```

#### `SUB-S1-07`｜[P3] 三支 probe 是同型物（其中一支逐字自稱），可收成單一入口的三個子命令

- **檔案:行**：tools/probe/misstep_attribution.py:11,29-33；tools/probe/reset_window_distribution.py:7,24-25；tools/probe/audit_session.py:65-71
- **成本**：small

**為何要緊（逐字）**：這一桶是「量測配方要可重跑」這條正確要求的產物，不該整批刪（R80 已就 `xplat_injection_matrix` 明文裁決保留，理由是刪掉等於把 DEF-101-796『沒有可重跑產物』原封不動放回去）。但三支各自重寫一次「找逐字稿根目錄 → 逐行 json.loads → 容錯 → 分桶 → 印表 → 落 jsonl」，是同一份骨架的三份手抄本，而它們彼此之間沒有任何對拍。

**當回合實測證據（逐字保全）**：

```text
實測（本回合）：
消費者普查（掃全 repo 程式碼／設定，排除 docs/）：`tools/probe/xplat_injection_matrix.py` code=0 test=1；`misstep_attribution.py` code=1（唯一那個 code 消費者是 `reset_window_distribution.py` 的一句註解）；`reset_window_distribution.py` code=1（`tools/session_resume_planner.py:296` 的註解）。三支皆無任何閘門呼叫。
`reset_window_distribution.py:7` 逐字：「本檔是 `misstep_attribution.py` 的**同型物**：來源清單、判準、每一…」
三支的 CLI 形狀相同（argparse + `--json` + `--jsonl <out>` 逐筆落檔供 diff），資料源都是 `~/.claude/projects/<slug>/*.jsonl` 逐字稿或缺陷帳本。
行數：audit_session 993、misstep_attribution 496、reset_window_distribution 182、xplat_injection_matrix 305（合計 1,976）。
```

**建議修法（逐字）**：

```text
抽一支 `tools/probe/_transcript_corpus.py`（逐字稿列舉、逐行解析、容錯、jsonl 輸出、`--json/--jsonl/--since/--latest` 共用旗標），三支 probe 各自只留自己的判準與分桶表。預估 −250~−350 行。
🔴 兩條界線不可越：① 不得把任何 probe 接進閘門的 rc（`xplat_injection_matrix --apply` 會就地改共用工作樹，DEF-101-886）；② 不得刪掉任何一支的判準本體與其 WHY —— 它們是那幾個缺陷唯一的可重跑產物。
```

#### `SUB-S1-08`｜[P3] `_git()` 在兩支 dispatcher 測試檔逐字重複

- **檔案:行**：tools/tests/test_pre_commit_dispatcher_sigpipe.py（`_git`）；tools/tests/test_pre_push_dispatcher.py（`_git`）
- **成本**：small

**為何要緊（逐字）**：單筆很小，但它落在 R80 S5-04 剛立下的判別式的錯邊：「這兩份**能不能** import 對方？能，卻選擇不 → 那不是獨立重寫，是複本」。兩支都在 `tools/tests/` 同一棵樹、同一個 sys.path 上，能 import。留著它等於讓那條剛寫好的判別式在下一輪自我打臉。

**當回合實測證據（逐字保全）**：

```text
正規化 AST 雜湊比對（本回合 dupfn.py，門檻 ≥10 行）：`1b50ec335be1` 兩份，各 10 行 —— `tools/tests/test_pre_commit_dispatcher_sigpipe.py::_git` 與 `tools/tests/test_pre_push_dispatcher.py::_git`。剝除 docstring／註解後逐字相同。
收斂目的地已存在且兩支都在用同一棵樹：`tools/tests/_platform_helpers.py`（539 行，被 21 支測試檔消費，`tools/run_root_unittests.py` 與 `tools/lib/bash_probe_spec.py` 亦消費）。
```

**建議修法（逐字）**：

```text
`_git()` 移進 `tools/tests/_platform_helpers.py`，兩支測試改 import。預估 −10 行。可與 S1-05 併成同一個「測試樹共用層收斂」的 commit。
```

### §3.3 本路 `verified_commands`（逐字保全）

```text
本回合真的跑過、逐字如下（全部走 PowerShell 工具，零 Bash 工具；讀檔／搜尋走 Read/Grep 工具）：

1. `Get-ChildItem -Path 'D:\CursorProject\AISDCL_Agent\tools\tests' -File | Select-Object Name,Length`（rc=0）
2. `Get-ChildItem -Path 'D:\CursorProject\AISDCL_Agent\tools' -File -Filter *.py`（rc=0）
3. `Get-ChildItem -Path '...\.claude\hooks' -File -Recurse` ／ `'...\AutoClaude\tools\hooks'`（rc=0）
4. `Get-Content -LiteralPath '...\.claude\settings.json' -Encoding utf8 -Raw`（rc=0；20 個 hook 條目、全 exec form）
5. `& .venv\Scripts\python.exe <scratchpad>\inv.py` → rc=0，`TOTAL 92229 files 117`（護欄層總行數普查）
6. `& .venv\Scripts\python.exe <scratchpad>\dupfn.py 10` → rc=0，`scanned 109 py files`，6 組跨檔重複函式（雜湊 80f6d2343b6c ×4、79b6854072f6 ×2、79cedf44575b ×2、d6b0668bfe6f ×2、23932e8d5bde ×2、1b50ec335be1 ×2），`TOTAL redundant lines ~132`
7. `& .venv\Scripts\python.exe <scratchpad>\deadconst.py` → rc=0，8 個空容器常數（`tools/lib/skip_tag_policy.py:96 _WINDOWS_SKIP_TAG_EXEMPT uses=0`）
8. `& .venv\Scripts\python.exe <scratchpad>\subject.py` → rc=0（test↔subject 反查表）
9. `Push-Location <repo>; & python <scratchpad>\e1.py` → rc=0：
   `E1 hook_command_scripts count = 20`
   `E2 lib index_modes entries = 27566  test copy entries = 27566  identical = True`
   `E4 _WINDOWS_SKIP_TAG_EXEMPT = {}`
10. `& python <scratchpad>\consumers.py` → rc=0（低消費者模組普查）
11. `& python <scratchpad>\dupre.py` → rc=0，9 組跨檔重複正則字面
12. `& python <scratchpad>\dupblock.py 30` → rc=0，4 份 30 行相同區塊（mac:86/mac:353/win:220/win:479）
13. `& python <scratchpad>\maxrun.py` → rc=0：`mac86 vs win220 = 74 行`、`mac190 vs win314 = 47`、`mac86 vs mac353 = 61`、`win220 vs win479 = 53`
14. `& python <scratchpad>\pathsblocks.py` → rc=0：四大 paths block 266/199/259/201 行、108/108/107/107 globs，`TOTAL lines inside paths blocks: 1003`，`macos:341 vs macos:74 shared=108 only_here=0 only_there=0`
15. `& python -c "<統計 workflow 內 DEF-101-042 回指>"` → `total DEF-101-042 back-references in workflows: 72`；lock 內相異 DEF 號 7 個
16. `git branch -r` / `git log --merges --oneline -20` / `git rev-list --count --merges HEAD` → 只有 origin/main、**0 merge commits**
17. `gh pr list --state all --limit 20` → rc=0，共 9 筆，最後一筆 2026-07-13
18. `gh run list --workflow windows-compat-ci.yml --limit 8 --json ...` → rc=0，最近 8 次全 failure、7 次 3~14 秒
19. `gh run view 31254543751 --json conclusion,jobs,...` → 主 job 2 秒、`"steps":[]`
20. `gh run list --workflow {macos-compat-ci,root-infra-ci,autoclaude-ci,aisdlc-sdd-ci}.yml --limit 4` → 全 failure、3~15 秒
21. `& python AutoClaude\tools\check_loc_budget.py --json` → **rc=1**；`tools/lib/hook_wiring.py loc=407 budget=400 over_by=7`（violation）、`tools/lib/skip_group_policy.py loc=395 headroom=5`（warn band）
22. `& python -m pytest tools/tests -q --no-header -p no:cacheprovider -rs` → **rc=1**，`5 failed, 2418 passed, 43 skipped, 1 warning, 1439 subtests passed in 367.02s`；skip 分群 `MAC-NATIVE-ONLY 24 / POSIX-NATIVE-ONLY 14 / UNTAGGED 3 / TOOL-MISSING 2`；5 筆 failed＝TestMain.test_main_against_real_repo_is_clean、TestEarlyExitAnnouncesUnrunChecks.test_the_real_gate_still_reaches_the_late_checks、TestR79RowByteCeiling ×2、UntaggedWindowsLikeSkipsTest.test_real_run_with_floor_reds_on_an_untagged_windows_skip（皆為進場既有，非本回合造成——本回合唯讀，零檔案修改）
23. `& python <scratchpad>\drift.py` → rc=0，五支 hook 對同一份 `[1,2,3]` payload 的實測：check_ps1_encoding rc=0 靜默／enforce_docs_path rc=1 AttributeError／check_sh_eol rc=0 走自身 fail-open／loc_budget_check rc=1 AttributeError／check_lang rc=1 AttributeError
24. `& python -m pytest tools/tests/test_git_hooks_install_common.py -q` → rc=0，`20 passed`（用來確認 R80 交棒 #1 的 `_SH_MAX_LINES` 已不再紅，故未列入發現）

本回合**未修改任何 repo 檔案**（只在 scratchpad 寫探針腳本）。
```

### §3.4 本路 `honest_gaps`（逐字保全）

```text
1. **我沒有實際做過任何一筆刪除的「刪掉後仍綠」驗證。** 全部 8 筆都是唯讀階段的診斷 + 可行性論證。S1-01 的 −2,000 行、S1-03 的 −870 行只有量測依據（行數、集合比對、tier 設定），沒有「真的刪一次再跑一次閘門」的紅綠自證。要落地前每一筆都必須先做那件事。

2. **S1-02 的根因我沒有查實。** 我只證明了「五支 workflow 都在數秒內 failure、`steps` 為空」，**沒有**取得 GitHub 回報的失敗原因（billing / quota / runner 分配）。記憶檔記載 R76 曾發生「Actions 額度用盡」，但那是史料不是本回合的量測，我沒有拿到 `gh api` 的帳務端證據。若真因是別的（例如 workflow YAML 在某次 commit 後語法失效），處置方向會完全不同。

3. **S1-01 的「刪掉 paths 後 CI 分鐘數會增加多少」我算不出來。** compat-CI 近 4 次都是秒退，拿不到正常跑一次要幾分鐘的數字，所以「代價」那一欄我只能給 PR 次數（近 4 個月 9 筆），給不出分鐘數。這一筆要拍板前需要一次雲端恢復後的實測基線。

4. **S1-03 的 +877 行是「拆前 727 raw」對「拆後五檔實量」的對照，而 727 那個數字來自 `windows_skip_tags.py` 自己的檔頭自述，不是我量的**（拆分發生在 R75，工作樹上已不存在拆前版本）。我沒有去 git 歷史把那一版撈出來重量。方向（分檔製造淨增）我有把握，確切數字要以 `git show <R75 前的 sha>:tools/lib/windows_skip_tags.py` 重量為準。

5. **兩筆我原本以為是發現、實測後撤回，列在這裡以免下一輪重踩：**
   (a) `tools/lib/skip_tag_policy.py::_WINDOWS_SKIP_TAG_EXEMPT` 我先判成「空且零消費者的死常數」——**錯**。跨檔 grep 顯示它經 `windows_skip_tags.py:107/114/149` → `run_root_unittests.py:515` 真的接上電，且 `exemption_problems()` 有合成注入自證。我的探針只數了模組**內部**的引用。
   (b) `test_bootstrap_ps1.py` 與 `test_windowsapps_guard_cross_consistency.py` 兩支同名的 `test_windowsapps_only_python_stub_is_skipped_and_reports_not_found` 正規化 AST 雜湊相同（`79cedf44575b`）——但逐行讀完發現 `self._run` 在兩邊指向**不同腳本**（bootstrap.ps1 vs dev_start.ps1），是兩個標的的同型測試，**不是複本**。雜湊相同在這裡是假陽性。

6. **`tools/tests/` 下最大的四支檔（test_dev_start.py 6686、test_doc_loc_baseline_freshness_r60.py 5927、test_platform_neutral_paths.py 5033、test_adr_xplat001_c1c2_lock.py 4521，合計 22,167 行＝護欄層近 1/4）我沒有做內部重疊分析。** 跨檔重複函式／正則的普查掃得到它們，但「同一支檔案內部有沒有兩個判準在守同一件事」需要逐類讀，本回合的預算不允許。這是下一輪最大的未探勘面。

7. **`.claude/hooks` 與 `AutoClaude/tools/hooks` 之間，除了 payload 讀取器（S1-04）之外我沒有找到其他重複。** `hook_path_scope.py` 是正當的共用層（3 個消費者），`check_ps1_encoding.py`／`check_sh_eol.py` 的 hook↔unittest 雙層在 R80 S5-09 已裁決為合理雙層，我沒有推翻它的證據。

8. **我沒有跑 `tools/run_root_unittests.py`（根層閘門本體），只跑了 `pytest tools/tests`。** 兩者的收集面與 MIN_TESTS 判準不同，所以我報的 2418 passed 不能拿來當「根層閘門綠」的憑據。
```

## §4 scan:skipped — pytest skipped 普查與消除方案（12 筆）

**任務**：當回合真跑兩棵樹的 census，逐類提出可執行的消除方案（環境未啟用／平台結構性／工具缺席／untagged／真技術債）。

**agentId**：`ae16b7c58c2b5e6c3`　**筆數**：12（P0 1／P1 5／P2 6／P3 0）

### §4.1 索引

| 本檔 ID | 原始 ID | sev | 標題（逐字） | 檔案:行 | 成本 |
|---|---|---|---|---|---|
| `SKP-S3-01` | S3-01 | P0 | AutoClaude CI 的 Tests job 連四次 push 都是 0 steps／從未執行 ⇒ 17 支 posix-only skip 全世界沒有任何機械證據跑過 | .github/workflows/autoclaude-ci.yml:139 (census step) ／ tools/lib/skip_group_policy.py:376 (_UNMEASURED_RUNNER_PROFILES) | medium |
| `SKP-S3-02` | S3-02 | P1 | 本輪兩棵樹今天的 failed 全部是同輪並行 agent 改檔的附帶紅，與 skip／PG 皆無關——不修正歸因會讓整個 S3 量測被誤讀 | tools/lib/hook_wiring.py:1 (407>400) ／ docs/06_quality/AutoSDD_Defect_Log.md | small |
| `SKP-S3-03` | S3-03 | P1 | 開 SD07_REAL_PG_E2E_ENABLED／PG_REAL_ENABLED 後 skip 一支都沒少，只是換了一道更深的「語料缺件」閘——真正的歸零開關是 seed_kb.py | AutoClaude/tests/integration/test_pgvector_real_recall.py:106 ／ AutoClaude/tests/perf/test_pgvector_recall_perf.py:108 | medium |
| `SKP-S3-04` | S3-04 | P2 | AUTOCLAUDE_TEST_PG_DSN 的正確形態與 PG 角色名（R80 猜 postgres 是錯的）——今天實查的權威答案 | AutoClaude/tests/conftest.py:131 (_ASYNC_DRIVERS / pg_dsn_problems) ／ AutoClaude/tools/local_ci_gate.py:97 (_PG_DSN) | small |
| `SKP-S3-05` | S3-05 | P1 | [TOOL-MISSING]／[PG-CORPUS-MISSING] 是未登記標籤，機械上一律算 untagged——4 支 untagged 只是「標籤字面沒對齊」，改字串即消 | tools/lib/skip_tag_policy.py:438 (_NONLITERAL_TAG_DEBT) ／ tools/lib/skip_group_policy.py:67 (skip_group) | small |
| `SKP-S3-06` | S3-06 | P1 | 「找不到 < 3.11 的直譯器」是假診斷：本機有 pyenv 3.10.11、shutil.which 也找得到，壞的是 pyenv-win 的 .BAT shim | tools/tests/test_dev_start.py:5798 (_find_sub_min_interpreter) | medium |
| `SKP-S3-07` | S3-07 | P1 | untagged=23 的逐支補標清單（AutoClaude 樹）——(d) 欠債主體的完整處置表 | AutoClaude/tests/（逐支見證據） | medium |
| `SKP-S3-08` | S3-08 | P2 | symlink 權限 2 支（root 1 ＋ AutoClaude 1）：實測 Developer Mode 關閉、SeCreateSymbolicLinkPrivilege 不存在 ⇒ 開一個開關即可歸零 | tools/tests/test_dev_start.py (TestStepSwitchCacheCleanup) ／ AutoClaude/tests/infra/test_sdd_to_playbook_adapter.py:182 | small |
| `SKP-S3-09` | S3-09 | P2 | [TOOL-ABSENCE] sdk extra 3 支：bootstrap 的安裝 target 結構上不含 sdk ⇒ 走 bootstrap 的環境一律拿不到 | AutoClaude/tests/infra/adapters/test_sdk_executor_adapter.py:207 ／ AutoClaude/pyproject.toml:133 | small |
| `SKP-S3-10` | S3-10 | P2 | 11 支 nested-session skip 在 nightly 會跑，但 win32+nopg+solo 剖面從未被 census ⇒「有跑」只有一則人工對帳、沒有機械證據 | AutoClaude/tests/test_gap014_020.py:80 ／ AutoClaude/tests/test_gap039_049.py:50 ／ tools/lib/skip_group_policy.py:380 | small |
| `SKP-S3-11` | S3-11 | P2 | (e) 真技術債逐支：7 支被 skip 掉的測試其斷言落點根本還沒建，其中 2 支「沒有任何自動通道會跑」 | AutoClaude/tests/contract/test_ac_matrix_scaffolding.py:329 ／ AutoClaude/tests/integration/test_pgvector_hnsw_recall.py:183 ／ AutoClaude/tests/integration/test_pgvector_real_recall.py:236 | large |
| `SKP-S3-12` | S3-12 | P2 | 另外兩棵活測試樹（AISDLC_SDD/scripts/tests、LATEST fsm_runtime/tests）只有靜態站點帳、沒有 runtime census 入口 ⇒ 它們的 skip 不受任何天花板管轄 | AISDLC_SDD/scripts/ci-gate.sh ／ tools/lib/skip_tag_policy.py:388 | medium |

### §4.2 逐筆（證據逐字保全）

#### `SKP-S3-01`｜[P0] AutoClaude CI 的 Tests job 連四次 push 都是 0 steps／從未執行 ⇒ 17 支 posix-only skip 全世界沒有任何機械證據跑過

- **檔案:行**：.github/workflows/autoclaude-ci.yml:139 (census step) ／ tools/lib/skip_group_policy.py:376 (_UNMEASURED_RUNNER_PROFILES)
- **成本**：medium

**為何要緊（逐字）**：這 17 支不是「在 Windows 上 skip 但別處有跑」——是**全世界都沒跑**。skip census 的整個設計前提（結構性 skip 的目標是「互補剖面有人跑到」）在 AutoClaude 這棵樹上today 是空的。而且它比帳面更嚴重：`_UNMEASURED_RUNNER_PROFILES` 只登記「沒量過健康值」，實況是**連測試本身都沒執行**，兩者差一個量級。四次連續啞掉沒有任何東西出聲＝失效是靜默的。

**當回合實測證據（逐字保全）**：

```text
任務 (b) 的直接答案：**沒有人量過，而且連跑都沒跑**。

① census 工具今天自己講出來（rc=0）：
  & .venv\Scripts\python.exe AutoClaude\tools\local_ci_gate.py --census-only ac_default.log
  rc=0
  [skip census] AutoClaude/tests@win32+pg+nested 共 44 支：platform=17／…
  ℹ️ [skip target] …：結構性 skip 17 支，它們的目標**不是** 0，而是「在互補剖面 `AutoClaude/tests@linux+pg+solo` 上真的被跑到」——而該剖面至今沒有人量過 ⇒ 這些測試目前**沒有任何機械證據**顯示它們在世界上任何一處跑過。

② 更糟的是那個唯一會量它的 runner 根本沒在跑。gh api 逐 run 實查（rc=0）：
  gh api repos/wuweihungmobile/AISDCL_Agent/actions/jobs/93095887118 --jq '"started=\(.started_at) completed=\(.completed_at) steps=\(.steps|length) runner=\(.runner_name)"'
  rc=0
  started=2026-08-08T11:14:51Z completed=2026-08-08T11:14:53Z steps=0 runner=
  同查另三個 run：
  31191595350 failure steps=0 2026-08-07T15:14:17Z -> 2026-08-07T15:14:26Z
  31128288018 failure steps=0 2026-08-06T21:24:47Z -> 2026-08-06T21:24:49Z
  31119121708 failure steps=0 2026-08-06T16:14:38Z -> 2026-08-06T16:14:56Z
  ⇒ 2s~18s、steps=0、runner 空字串 ⇒ 四次連續 push 的整套 AutoClaude 測試在雲端一步都沒跑（形態符合 Actions 額度/帳單耗盡，見記憶 R76/R77）。
  `gh run view --job 93095887118 --log` → rc=1「log not found: 93095887118」（沒有 log 因為沒有執行）。
```

**建議修法（逐字）**：

```text
分兩件事，不要混：
(1) 先確認雲端為何 0 steps（billing/額度）——這是前提，不修的話下面全部白做。查：`gh api repos/:owner/:repo/actions/runs/31254543809 --jq .conclusion` 與 GitHub Billing 頁。
(2) 在額度恢復前，用地端 act 取得該剖面實測值（root tree 的 linux 剖面正是這樣拿到的，見 skip_group_policy.py:291 註記）：於 monorepo 根跑 `tools/run_act.ps1 -Job test`，取其 `[skip census] AutoClaude/tests@linux+…` 那一行逐格填入 `_RUNTIME_SKIP_CEILING` 與 `_RUNTIME_SKIP_CEILING_MAX`，並把 `_UNMEASURED_RUNNER_PROFILES` 對應列刪除。
(3) 加一道「雲端 job 必須真的有 steps」的取證：`steps=0` 目前與「全部通過」在 conclusion 以外無從分辨，正是本 repo 的〈反事後諸葛取證規則〉要防的形態。
```

#### `SKP-S3-02`｜[P1] 本輪兩棵樹今天的 failed 全部是同輪並行 agent 改檔的附帶紅，與 skip／PG 皆無關——不修正歸因會讓整個 S3 量測被誤讀

- **檔案:行**：tools/lib/hook_wiring.py:1 (407>400) ／ docs/06_quality/AutoSDD_Defect_Log.md
- **成本**：small

**為何要緊（逐字）**：任務指定要回報「設了 PG DSN 之後新暴露出來的 failed」（R80 前例 4 個）。**今天的正確答案是 0**——若照時序天真歸因，會把 5 支 LOC 紅寫成「PG 暴露的真缺陷」，製造一筆假事實並讓下一輪去查錯的地方。這正是記憶〔parallel-mutation-audit-collision〕已重演三次的形態：並行 agent 就地改 tracked 生產碼，跑全套的鏡拿到假紅。

**當回合實測證據（逐字保全）**：

```text
session 起始時 git 為 clean（env 區塊逐字：Status: (clean)）。跑完兩輪後實查（rc 未接管線）：
  git status --porcelain
   M AISDLC_SDD/scripts/tests/test_hook_wiring_cwd_safety.py
   M AutoClaude/.claude/settings.json
   M docs/06_quality/AutoSDD_Defect_Log.md
   M docs/06_quality/AutoSDD_Defect_Log_archive_INDEX.md
   M tools/lib/hook_wiring.py
   M tools/tests/test_check_hooks_liveness.py
  ?? docs/06_quality/AutoSDD_Defect_Log_archive_64.md
  HEAD=8314939

根層 4 failed 的內容全部是缺陷帳本歸檔中途態：
  FAIL test_check_defect_log_crossref.TestR79RowByteCeiling.test_the_real_ledger_baselines_are_exact_not_padded
  AssertionError: Items in the second set but not the first: 'DEF-101-422' 'DEF-101-274' 'DEF-01-007'
  （＝這三筆剛被搬進 archive_64.md，主檔查無 ID）

AutoClaude 第二輪 5 failed 的根因是 LOC 破線，我以**乾淨環境**單獨重跑複驗：
  & .venv\Scripts\python.exe AutoClaude\tools\check_loc_budget.py   → rc=1
  [ROOT-TOOLS] [guardrail_lib<=400] tools/lib/hook_wiring.py: 407 > 400 (+7)
  python -m pytest tests/tools/test_check_loc_budget_tier_headroom_warn.py -q  → 1 failed, 14 passed（未設任何 PG 變數）
  python -m pytest tests/contract/test_loc_budget_tiered.py -q → 4 failed, 29 passed（未設任何 PG 變數）
  ⇒ 1+4=5，與第二輪的 5 failed 完全對上，且與 PG 環境變數無關。
```

**建議修法（逐字）**：

```text
(1) 歸因訂正：本輪 PG 環境變數暴露的新 failed ＝ **0**。
(2) 流程面：S3 這類「量全樹」的 agent 必須與做突變的 agent 序列化，或在 worktree 隔離跑（記憶已記載，本輪又踩一次）。
(3) `tools/lib/hook_wiring.py: 407 > 400` 是真違規但屬於別的包（R80 已記載該檔是 hook 佈線 SSOT），交由該包拆職責，不在 S3 射程。
```

#### `SKP-S3-03`｜[P1] 開 SD07_REAL_PG_E2E_ENABLED／PG_REAL_ENABLED 後 skip 一支都沒少，只是換了一道更深的「語料缺件」閘——真正的歸零開關是 seed_kb.py

- **檔案:行**：AutoClaude/tests/integration/test_pgvector_real_recall.py:106 ／ AutoClaude/tests/perf/test_pgvector_recall_perf.py:108
- **成本**：medium

**為何要緊（逐字）**：這是「設環境變數就會跑」這條 R79 成功經驗的**邊界**：它對第一道閘有效，對第二道（資料/語料）無效，而 census 的分群數字看起來完全沒動，會讓人以為「這條路已經走到底了」。真正剩下的動作是餵資料，而那件事 reason 已經逐字寫出指令、卻沒有任何自動通道會執行它。

**當回合實測證據（逐字保全）**：

```text
對照組兩次實跑（同一棵樹、相隔數分鐘）：

【基線】Push-Location AutoClaude; python -m pytest tests -q -rs
  AUTOCLAUDE-PG-DSN-IN-EFFECT=1 AUTOCLAUDE-NESTED-SESSION=1
  4199 passed, 44 skipped, 1 warning in 100.06s   （background exit code 0）
  相關 skip：
    SKIPPED [2] tests\integration\test_pgvector_real_recall.py: SD_07 pg_real：未啟用 SD07_REAL_PG_E2E_ENABLED=true 或缺 DSN（PM #2）
    SKIPPED [1] tests\integration\test_pgvector_real_recall.py:226: 同上
    SKIPPED [1] tests\perf\test_pgvector_recall_perf.py:67: [ENV-DISABLED] …（R-SD08-G-1 / set PG_REAL_ENABLED=1）——未啟用，非缺件

【開全部環境閘】同指令＋ $env:SD07_REAL_PG_E2E_ENABLED='true'; $env:PG_REAL_ENABLED='1'; DSN 顯式設為 postgresql+asyncpg://autoclaude:autoclaude@localhost:5432/autoclaude
  5 failed, 4194 passed, 44 skipped, 1 warning in 102.13s
  同一批 skip 變成：
    SKIPPED [2] tests\integration\test_pgvector_real_recall.py:106: [PG-CORPUS-MISSING] 本 DB 只有 0 列帶 embedding 的 knowledge_entries（需 ≥ 100）⇒ 這是**缺件**不是實作問題。先跑 `python tools/seed_kb.py --mock-pg-seed --pg-dsn <同一個 DSN>`
    SKIPPED [1] tests\integration\test_pgvector_real_recall.py:236: 雙 adapter failover fixture 缺失；由 SD_09 W2 議題 C 完整實作
    SKIPPED [1] tests\perf\test_pgvector_recall_perf.py:108: [TOOL-ABSENCE] 本 DB 只有 0 列帶 embedding 的 knowledge_entries（需 ≥ 100）⇒ 缺件…
  ⇒ 總數 44→44，**位移不是消除**。（5 failed 的歸因見 S3-02，非 PG 造成。）
```

**建議修法（逐字）**：

```text
(a) 環境未啟用類的完整配方（三段，缺一支都不會歸零）：
  1. $env:AUTOCLAUDE_TEST_PG_DSN = 'postgresql+asyncpg://autoclaude:autoclaude@localhost:5432/autoclaude'
     $env:AUTOCLAUDE_DB_DSN = $env:AUTOCLAUDE_TEST_PG_DSN; $env:AUTOCLAUDE_ALLOW_INSECURE_DB='1'
     （本機預設已由 conftest 自動注入同一字串，見 S3-04；顯式設值只在要覆寫時需要）
  2. $env:SD07_REAL_PG_E2E_ENABLED='true'; $env:PG_REAL_ENABLED='1'
  3. **關鍵新增**：Push-Location AutoClaude; & <venv>\python.exe tools/seed_kb.py --mock-pg-seed --pg-dsn $env:AUTOCLAUDE_TEST_PG_DSN
     ⇒ 預期再消 3 支（real_recall ×2、recall_perf ×1）。
  🔴 本輪**未執行** seed_kb（它會同時寫 PG 與 tests/fixtures/ 兩份檔＝改動 repo 檔案，違反本階段唯讀約束），故「再消 3 支」是推得值不是實測值，落地時必須當場複驗。
(b) 把 seed 這一步接進 local_ci_gate 的 pg_autodetect：偵測到 PG 但 knowledge_entries 為空時，現在是「注入 DSN 然後照樣 skip」，可改為一併 seed 或明確報「已注入但語料為空，下一步跑 X」。
```

#### `SKP-S3-04`｜[P2] AUTOCLAUDE_TEST_PG_DSN 的正確形態與 PG 角色名（R80 猜 postgres 是錯的）——今天實查的權威答案

- **檔案:行**：AutoClaude/tests/conftest.py:131 (_ASYNC_DRIVERS / pg_dsn_problems) ／ AutoClaude/tools/local_ci_gate.py:97 (_PG_DSN)
- **成本**：small

**為何要緊（逐字）**：任務要求回報正確形態、角色名、DB 名、port，避免重蹈 R80「照合法但不相容的 DSN 設值 → 15 支在 setup 硬炸」。同時要記一件好消息：那個缺陷**已經被 R80 修掉了**（conftest 的形態驗證＋收集前 fail-loud），今天照文件設值不會再炸——這一格不是待辦，是已閉環，別再排一次工。

**當回合實測證據（逐字保全）**：

```text
① 容器實查角色與 DB（rc=0）：
  docker exec autoclaude_pg psql -U autoclaude -d autoclaude -c "\du" -c "\l"
  rc=0
  Role name  | Attributes
  autoclaude | Superuser, Create role, Create DB, Replication, Bypass RLS
  （**只有 autoclaude 一個角色，沒有 postgres 角色** ⇒ R80「猜 postgres 是錯的」在今天仍成立）
  Databases: autoclaude / postgres / template0 / template1，Owner 皆 autoclaude
② 容器 env（rc=0）：docker inspect autoclaude_pg --format '{{json .Config.Env}}'
  ["POSTGRES_PASSWORD=autoclaude","POSTGRES_DB=autoclaude","POSTGRES_USER=autoclaude",…,"PG_MAJOR=18"]
③ port：docker ps → 0.0.0.0:5432->5432/tcp，Up 44 hours (healthy)，image pgvector/pgvector:pg18
④ R80 包 A 已把形態驗證做成機械物（conftest.py:134 `pg_dsn_problems`）：scheme 必須 postgresql*，且 `AUTOCLAUDE_TEST_PG_DSN` **必須**含 async driver（`+asyncpg`/`+psycopg`/`+aiopg`），否則 `pytest.UsageError` fail-loud；`AUTOCLAUDE_DB_DSN` 則不要求（消費端會自己 strip）。
⑤ 自動偵測用的字串與我實查的完全一致，本輪兩次跑都印：
  [PG autodetect] 已注入 AUTOCLAUDE_DB_DSN／AUTOCLAUDE_TEST_PG_DSN = postgresql+asyncpg://autoclaude:autoclaude@localhost:5432/autoclaude
```

**建議修法（逐字）**：

```text
權威值（今天實測）：
  DSN = postgresql+asyncpg://autoclaude:autoclaude@localhost:5432/autoclaude
  role=autoclaude  password=autoclaude  db=autoclaude  host=localhost  port=5432  image=pgvector/pgvector:pg18
  AUTOCLAUDE_TEST_PG_DSN **必須**帶 +asyncpg；AUTOCLAUDE_DB_DSN 帶不帶皆可（建議設成同一字串）。
本機**不需要**手動 export：conftest.pytest_configure 會自動偵測並注入同一字串（前提是 5432 在聽且 alembic_version 非空）。要覆寫才顯式設；要關掉自動偵測用 AUTOCLAUDE_NO_PG_AUTODETECT。
```

#### `SKP-S3-05`｜[P1] [TOOL-MISSING]／[PG-CORPUS-MISSING] 是未登記標籤，機械上一律算 untagged——4 支 untagged 只是「標籤字面沒對齊」，改字串即消

- **檔案:行**：tools/lib/skip_tag_policy.py:438 (_NONLITERAL_TAG_DEBT) ／ tools/lib/skip_group_policy.py:67 (skip_group)
- **成本**：small

**為何要緊（逐字）**：這是 (d) 這一類裡**成本最低、鑑別力最高**的一批：它們不是「沒人分類過」，而是分類了但用了自創字面。`skip_group` 的 docstring 逐字說這是刻意的（發明新標籤不得換到「看起來已分類」的待遇），所以正解一定是改 reason 而不是放寬判準。政策檔自己也已經寫好處置建議（skip_tag_policy.py:434~437 逐字指名這三個標籤該併入 `[TOOL-ABSENCE]`）。

**當回合實測證據（逐字保全）**：

```text
當回合探針（rc=0）：
  & .venv\Scripts\python.exe <scratchpad>\probe_tag.py
  rc=0
  ALL_SKIP_TAGS = ('[WINDOWS-NATIVE-ONLY]', '[POSIX-NATIVE-ONLY]', '[MAC-NATIVE-ONLY]', '[TOOL-ABSENCE]', '[ENV-DISABLED]', '[STRUCTURAL-PAIR]', '[DEBT]')
  TOOL-MISSING registered? -> False
  '[TOOL-MISSING] found no inte' -> group: untagged
  '[TOOL-ABSENCE] same meaning' -> group: tool-absence
  '[PG-CORPUS-MISSING] only 0 r' -> group: untagged
  _NONLITERAL_TAG_DEBT = {'[TOOL-MISSING]': 1, '[PG-CORPUS-MISSING]': 1, '[PG-CORPUS-STALE]': 1}

對照今天的 census 明細：根層 5 支 untagged 裡有 2 支的 reason 開頭**就寫著** `[TOOL-MISSING]`，卻被印成 `[未標籤]`、census 記 `tool-absence=0／untagged=5`：
  - [未標籤] test_dev_start.TestRealSubMinInterpreterPrelude.test_dev_start_prelude_loads_and_gate_fires_friendly
      理由：[TOOL-MISSING] 找不到版本 < (3, 11) 的真直譯器…
  - [未標籤] test_dev_start.TestRealSubMinInterpreterPrelude.test_documented_bootstrap_remediation_actually_loads
      理由：[TOOL-MISSING] …
AutoClaude 側開啟 PG 環境閘後，同型再出現 2 支 `[PG-CORPUS-MISSING]`（見 S3-03 證據）。
```

**建議修法（逐字）**：

```text
逐支改字面（純字串替換，零邏輯改動）：
  1. tools/tests/test_dev_start.py:5839 `[TOOL-MISSING]` → `[TOOL-ABSENCE]`（一處，涵蓋 2 支 skip）
  2. AutoClaude/tests/integration/test_pgvector_real_recall.py 的 `[PG-CORPUS-MISSING]` → `[TOOL-ABSENCE]`
  3. 同檔 `[PG-CORPUS-STALE]` → `[TOOL-ABSENCE]`
改完必須**同步下修** `skip_tag_policy._NONLITERAL_TAG_DEBT`（相等判準，清空即整列刪除；該表空掉後升級為零容忍），以及 `_RUNTIME_SKIP_CEILING`／`_RUNTIME_SKIP_CEILING_MAX` 兩張表的 `untagged`／`tool-absence` 兩格。
預期效果：根層 untagged 5→3、tool-absence 0→2（總數不變，但欠債分類終於為真）。
```

#### `SKP-S3-06`｜[P1] 「找不到 < 3.11 的直譯器」是假診斷：本機有 pyenv 3.10.11、shutil.which 也找得到，壞的是 pyenv-win 的 .BAT shim

- **檔案:行**：tools/tests/test_dev_start.py:5798 (_find_sub_min_interpreter)
- **成本**：medium

**為何要緊（逐字）**：skip reason 逐字宣稱「找不到版本 < (3,11) 的真直譯器（試過 …）」——**那是假的**。實況是「找到了、跑它、它自己壞掉、於是被 `if probe.returncode != 0: continue` 靜默吞掉」。這正是本 repo 紀律〔斷言環境缺件前必先實查〕在防的形態，而且它比一般假話更難看見：探針有 fallback、rc 是 0、測試「乾淨地」skip 掉。後果是這道 prelude 相容性鎖在 Windows 上**從未跑過**，而帳面上寫的是「這台機器缺件」——一個永遠不會有人去修的理由。

**當回合實測證據（逐字保全）**：

```text
探針逐字照抄 `_find_sub_min_interpreter()` 的候選清單與判定式重跑（rc=0）：
  & .venv\Scripts\python.exe <scratchpad>\probe_py.py
  rc=0
  cand='/usr/bin/python3'   which-> '/usr/bin/python3'   -> skipped (not found / not exists)
  cand='python3.9'          which-> None                 -> skipped
  cand='python3.10'         which-> 'C:\\Users\\wuwei\\.pyenv\\pyenv-win\\shims\\python3.10.BAT'
       -> rc=1 stdout='' stderr="'python3.10' is not recognized as an internal or external command,\nbatch file."
  cand='python3.8'          which-> None                 -> skipped
  cand='python3.7'          which-> None                 -> skipped

但那支直譯器**真的在**（rc=0）：
  pyenv versions →   3.10.11 ／ * 3.11.9 (set by D:\CursorProject\AISDCL_Agent\.python-version)
  Test-Path C:\Users\wuwei\.pyenv\pyenv-win\versions\3.10.11\python.exe → True
  & C:\Users\wuwei\.pyenv\pyenv-win\versions\3.10.11\python.exe -c "…" → rc=0 ver=3.10.11
另：uv 在本機可用，`uv python list` 顯示 cpython-3.10.18 / 3.9.23 / 3.8.20 皆 <download available>。
```

**建議修法（逐字）**：

```text
改 `_find_sub_min_interpreter()` 兩件事（都很小）：
  1. 候選清單補 Windows 形狀的發現路徑，順序放在 shim 之前：
     · `py -3.10 -c …`（Windows Python Launcher；本機今天 `Get-Command py` 為空，故不能只靠它）
     · pyenv-win：`%PYENV_ROOT%\versions\<ver>\python.exe` 逐版掃（本機命中 3.10.11）
     · uv managed：`uv python find 3.10`
  2. **rc!=0 不要靜默 continue**——把「找到了但跑不起來」與「根本沒找到」分成兩種 skip reason（前者是壞掉的載具，後者才是缺件）。這一條比第 1 條更重要：沒有它，下一個壞 shim 會用一模一樣的方式再隱形一次。
預期效果：根層 2 支 untagged/tool-absence skip 轉為**真的執行**，且是這道鎖第一次在 Windows 上有覆蓋。
```

#### `SKP-S3-07`｜[P1] untagged=23 的逐支補標清單（AutoClaude 樹）——(d) 欠債主體的完整處置表

- **檔案:行**：AutoClaude/tests/（逐支見證據）
- **成本**：medium

**為何要緊（逐字）**：untagged 的定義就是「還沒有人說得出它屬於哪一類」，補一句標籤就結案——它是四個 ZERO 群裡唯一**純文字成本**的一群，卻佔了 AutoClaude 欠債型 27 支裡的 23 支（85%）。不補標的代價不是難看：分群天花板的 untagged 那一格是「本鎖唯一真正有牙的地方」（skip_group_policy.py:260 自陳），23 支混在一起會讓後續每一輪都得重新人工盤點一次。

**當回合實測證據（逐字保全）**：

```text
今天實跑 census 的 -rs 明細（4199 passed, 44 skipped；census rc=0：platform=17／tool-absence=3／env-disabled=1／structural-pair=0／debt=0／untagged=23），23 支逐條盤點（加總 4+1+1+1+2+3+8+3=23，與 census 對得上）：
  [4] tests\contract\test_ac_matrix_scaffolding.py:329 — AC2-2／AC3-4／AC5-4／AC6-3「真斷言落點尚未建立」
  [1] tests\contract\test_pg_existing_schema_lock.py:318 — 「pgvector 已安裝；測 present case 改由 _present test」
  [1] tests\contract\test_pg_state_repository_contract.py:220 — 「sqlalchemy 已安裝，無法測試 ImportError 路徑」
  [1] tests\infra\test_sdd_to_playbook_adapter.py:182 — 「本機無建立 symlink 權限（[WinError 1314]）」
  [2] tests\integration\test_pgvector_hnsw_recall.py:183,189 — 「需 W3 G3 staging 資料集：1k seed + BGE-M3 真實向量…本 repo 目前沒有任何自動通道會跑這兩支」
  [3] tests\integration\test_pgvector_real_recall.py（模組層 ×2 ＋ :226 ×1）— 「SD_07 pg_real：未啟用 SD07_REAL_PG_E2E_ENABLED=true 或缺 DSN」
  [8] tests\test_gap014_020.py:789,830,882,923,961,1118,1162,1191 — 「【未啟用，非缺件】需要 claude CLI binary 且非巢狀 Claude Code session」
  [3] tests\test_gap039_049.py:443,462,660 — 同上
```

**建議修法（逐字）**：

```text
逐支貼標（reason **最前面**加標籤，判準只認開頭）：
  · ×11（gap014_020 ×8 ＋ gap039_049 ×3）→ `[ENV-DISABLED]`。語意精準：reason 自己已寫「【未啟用，非缺件】」，且 nightly（非巢狀）實測會跑。
  · ×3（pgvector_real_recall）→ `[ENV-DISABLED]`（開了環境閘會變成語料缺件，見 S3-03）。
  · ×2（test_pg_existing_schema_lock:318、test_pg_state_repository_contract:220）→ `[STRUCTURAL-PAIR]`。這兩支是 absent/present 互斥對，**結構上不可能歸零**，貼對標籤等於把它們正確移出欠債分母。
  · ×1（test_sdd_to_playbook_adapter:182 symlink）→ `[ENV-DISABLED]`（處置見 S3-08）。
  · ×4（ac_matrix_scaffolding）→ `[DEBT]` ＋ **必須寫承接輪次**（判準沿用 `_EXEMPT_HANDOVER_RE`＝大寫 R 加兩位數字，沒有承接者的欠債就是永久欠債）。
  · ×2（pgvector_hnsw_recall）→ `[DEBT]` ＋承接輪次（見 S3-11）。
貼完同步下修 `_RUNTIME_SKIP_CEILING`／`_RUNTIME_SKIP_CEILING_MAX` 的 `AutoClaude/tests@win32+pg+nested` 那兩格（untagged 23→0、env-disabled 1→15、structural-pair 0→2、debt 0→6）。⚠️ 兩張表都要改，只改一張會被 shrink-only 判準擋下。
```

#### `SKP-S3-08`｜[P2] symlink 權限 2 支（root 1 ＋ AutoClaude 1）：實測 Developer Mode 關閉、SeCreateSymbolicLinkPrivilege 不存在 ⇒ 開一個開關即可歸零

- **檔案:行**：tools/tests/test_dev_start.py (TestStepSwitchCacheCleanup) ／ AutoClaude/tests/infra/test_sdd_to_playbook_adapter.py:182
- **成本**：small

**為何要緊（逐字）**：這是最乾淨的「(a) 環境未啟用類」：不是缺件、不是平台結構性、也不是技術債，就是一個沒被打開的 Windows 開關。它今天被分在 untagged（AutoClaude）與 untagged（root），兩邊都讓欠債數字虛胖，而處置成本是「點一個開關 + 重開 session」。

**當回合實測證據（逐字保全）**：

```text
兩棵樹各一支，reason 逐字相同形態（今天的 census 明細）：
  root：[未標籤] test_dev_start.TestStepSwitchCacheCleanup.test_env_changed_removes_cache_dir_and_symlink
        理由：本機無建立 symlink 權限（[WinError 1314] 用戶端沒有這項特殊權限。…），略過 symlink 情境
  AutoClaude：SKIPPED [1] tests\infra\test_sdd_to_playbook_adapter.py:182: 本機無建立 symlink 權限（[WinError 1314] …）
機器狀態實查：
  Test-Path HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\AppModelUnlock → exists=True
  AllowDevelopmentWithoutDevLicense=      ← **空值＝Developer Mode 未開啟**
  whoami /priv 內含 SeCreateSymbolicLinkPrivilege → False
```

**建議修法（逐字）**：

```text
(1) 開 Windows 11 開發人員模式（設定 → 系統 → 開發人員專用 → 開發人員模式；一般使用者即可開，不需提權）。開啟後 `SeCreateSymbolicLinkPrivilege` 會出現在 token，兩支 skip 應轉為實跑。
(2) 🔴 **落地時必須當場複驗**，不要憑本條宣稱：開完重跑 `python tools/run_root_unittests.py` 與 AutoClaude pytest，確認 census 的對應格真的少 1。本輪未開該開關（會改動機器狀態，超出唯讀射程），故「開了就會消」是推得值。
(3) 在那之前先補標 `[ENV-DISABLED]`（見 S3-07），讓它至少落在正確的群。
```

#### `SKP-S3-09`｜[P2] [TOOL-ABSENCE] sdk extra 3 支：bootstrap 的安裝 target 結構上不含 sdk ⇒ 走 bootstrap 的環境一律拿不到

- **檔案:行**：AutoClaude/tests/infra/adapters/test_sdk_executor_adapter.py:207 ／ AutoClaude/pyproject.toml:133
- **成本**：small

**為何要緊（逐字）**：這是 (c) 工具缺席類的**全部**——AutoClaude 樹的 tool-absence 就這 3 支，裝一個 extra 即可歸零。而且 reason 已經把根因寫得很清楚：不是機器偶然沒裝，是 bootstrap 的 install target 不含它 ⇒ 每一台照 SOP 建起來的環境都會缺，包含 CI。

**當回合實測證據（逐字保全）**：

```text
今天 -rs 明細逐字：
  SKIPPED [3] tests\infra\adapters\test_sdk_executor_adapter.py:207: [TOOL-ABSENCE] 需要 claude-agent-sdk（選配 `[sdk]` extra；本測試要真的 PermissionResultAllow／Deny 型別，換成假物件等於不驗那個 isinstance 斷言）。🔴 這不是「這台機器剛好沒裝」——tools/bootstrap_core.py 的安裝 target 是 `.[dev,notifications,lint]`，不含 sdk ⇒ 走 bootstrap 的環境一律拿不到。跑法：在 AutoClaude/ 執行 `uv pip install -e '.[sdk]'` 後重跑本檔
extra 確實有宣告（Grep AutoClaude/pyproject.toml）：
  133:sdk = [
  134:    "claude-agent-sdk>=0.2.110",
  135:]
本輪 census：tool-absence=3，與這 3 支完全對應（該群今天只有這一個站點）。
```

**建議修法（逐字）**：

```text
兩種處置，二選一並寫明理由：
  (i) 若這 3 支的覆蓋值得常態保有：把 `sdk` 加進 `tools/bootstrap_core.py` 的安裝 target，並在 CI 的 install 步驟同步（否則地端消了、雲端還在 skip，變成新的剖面分歧）。
  (ii) 若 sdk 後端是選配、不值得每台都裝：維持現狀，但 `[TOOL-ABSENCE]` 就是正確分類，應把它移出「應歸零」的期待值——目前 `_SKIP_GROUP_TARGET` 把 tool-absence 定為 ZERO 群，與 (ii) 的決定相衝突，需要一併處理。
本機驗證指令（未執行，屬環境變更）：Push-Location AutoClaude; uv pip install -e '.[sdk]'; python -m pytest tests/infra/adapters/test_sdk_executor_adapter.py -q
🔴 注意本輪並行有其他 agent 在跑全套測試，直接改動共用 .venv 會造成互踩（記憶〔parallel-mutation-audit-collision〕），落地請在停工窗口做。
```

#### `SKP-S3-10`｜[P2] 11 支 nested-session skip 在 nightly 會跑，但 win32+nopg+solo 剖面從未被 census ⇒「有跑」只有一則人工對帳、沒有機械證據

- **檔案:行**：AutoClaude/tests/test_gap014_020.py:80 ／ AutoClaude/tests/test_gap039_049.py:50 ／ tools/lib/skip_group_policy.py:380
- **成本**：small

**為何要緊（逐字）**：這一批是 (b) 的**好消息面**——互補剖面真的存在而且就在本機（每日 nightly／schtasks）。缺的只是把它的 log 餵一次 census。相對於 S3-01 的 Linux 剖面（連跑都沒跑），這一格成本極低卻一直沒做，而它是唯一能把「nightly 有在跑」從敘事變成可稽核數字的動作。

**當回合實測證據（逐字保全）**：

```text
述詞（兩檔相同）：
  shutil.which("claude") is None or os.environ.get("CLAUDECODE") == "1"
今天這 11 支確實 skip（8＋3，見 S3-07 證據），因為本 session 是巢狀（census 標記逐字印出 `AUTOCLAUDE-NESTED-SESSION=1`）。
檔內自陳的互補證據是**人工對帳、不是機械物**（test_gap014_020.py:64-65）：
  「當回合對帳：nightly log 與巢狀 session 同一棵樹 collected 相同，nightly 少了 15 支 skip、多了 15 支 passed，且其 `-rs` 清單對本檔零命中 ⇒ 它們跑了而且綠。」
而該剖面在缺口帳上是白的（skip_group_policy.py:380 逐字）：
  "AutoClaude/tests@win32+nopg+solo": "QA-R80-01：nightly（非巢狀）與 pre-push 是兩個母體…取得＝對 nightly 的 pytest log 跑 `--census-only`。帳本 DEF-101-960"
```

**建議修法（逐字）**：

```text
(1) 找到最近一次 nightly 的 pytest log（run_local_nightly.ps1 的產物），直接跑：
    & <venv>\python.exe AutoClaude\tools\local_ci_gate.py --census-only <nightly-pytest.log>
    工具對未登記剖面會回 rc=3 並印出當場實測值，逐格填入 `_RUNTIME_SKIP_CEILING` 與 `_RUNTIME_SKIP_CEILING_MAX` 的 `AutoClaude/tests@win32+nopg+solo`，並刪掉 `_UNMEASURED_RUNNER_PROFILES` 對應列。
(2) 更根本：把 `--census-only` 接進 run_local_nightly.ps1 的收尾，讓 nightly 每天自己產生這個數字，而不是等人想起來。
(3) 本輪**不可能**在此 session 內量到（我就在巢狀 session 裡，CLAUDECODE=1），故此條僅提出配方、無實測。
```

#### `SKP-S3-11`｜[P2] (e) 真技術債逐支：7 支被 skip 掉的測試其斷言落點根本還沒建，其中 2 支「沒有任何自動通道會跑」

- **檔案:行**：AutoClaude/tests/contract/test_ac_matrix_scaffolding.py:329 ／ AutoClaude/tests/integration/test_pgvector_hnsw_recall.py:183 ／ AutoClaude/tests/integration/test_pgvector_real_recall.py:236
- **成本**：large

**為何要緊（逐字）**：這 7 支是唯一「不是設定問題、也不是平台問題」的一群：要消除它們必須真的寫測試/建語料。①~④ 的好消息是 reason 已寫出確切檔名與門檻（可直接開工）；⑤⑥ 的壞消息是它們連承接者都沒有，且自陳「沒有任何自動通道會跑」＝就算寫好了也不會被執行。⑦ 揭露了另一個結構問題：**skip 會層層堆疊**，淺層的環境 skip 會遮住深層的真欠債，所以「欠債清單」必須在最大環境剖面下盤點，否則永遠少算。

**當回合實測證據（逐字保全）**：

```text
今天 -rs 明細逐字（7 支）：
  ① AC AC2-2（mixin 物理刪除，W6）的真斷言落點尚未建立：AutoClaude/tests/contract/test_w6_deletion.py。門檻＝_runner_internals.py / _runner_compat.py 皆不存在
  ② AC AC3-4（多 run 並存，W3）…：AutoClaude/tests/integration/test_concurrent_runs.py。門檻＝5 run × abort 互不影響
  ③ AC AC5-4（SIGINT checkpoint SLA，W5）…：AutoClaude/tests/integration/test_sigint_checkpoint.py。門檻＝≤ 2s 寫入完成
  ④ AC AC6-3（OpenAPI 3.1 schema，W5）…：AutoClaude/tests/integration/test_config_schema_api.py。門檻＝openapi == 3.1.0 + ≥ 15 欄位
  ⑤⑥ test_pgvector_hnsw_recall.py:183,189 — 需 W3 G3 staging 資料集：1k seed + BGE-M3 真實向量。**本 repo 目前沒有任何自動通道會跑這兩支（當回合實查 .github/workflows 對本檔零命中）**
  ⑦ test_pgvector_real_recall.py:236（僅在開啟環境閘後現形）— 雙 adapter failover fixture 缺失；由 SD_09 W2 議題 C 完整實作
注意 ⑦ 在基線剖面**看不到**（被 pg_real 那一層 skip 蓋住），只有開了 SD07_REAL_PG_E2E_ENABLED 才露出來——見 S3-03 的兩次對照組輸出。
```

**建議修法（逐字）**：

```text
(1) 全部補 `[DEBT]` 標籤＋承接輪次（判準要求大寫 R 加輪號，見 S3-07）。
(2) ①~④：四支的檔名與門檻都已寫死在 reason 裡，屬「可直接排進 backlog 的具體工作」；建好檔後該 case 自動轉綠，並依 `test_pending_targets_match_the_ratchet` 的訊息下修 `_AC_TARGET_PENDING`／`_AC_TARGET_PENDING_CEILING`。
(3) ⑤⑥：先決定要不要保留。若保留，必須同時建立自動通道（現況是零通道 ⇒ 寫好也不會跑，等於製造新的隱形面）；若不保留，走顯式廢止而不是留著 skip。
(4) ⑦：盤點欠債時**一律在最大環境剖面下跑**（DSN + SD07_REAL_PG_E2E_ENABLED + PG_REAL_ENABLED + seed），否則會少算被遮住的那幾支。
```

#### `SKP-S3-12`｜[P2] 另外兩棵活測試樹（AISDLC_SDD/scripts/tests、LATEST fsm_runtime/tests）只有靜態站點帳、沒有 runtime census 入口 ⇒ 它們的 skip 不受任何天花板管轄

- **檔案:行**：AISDLC_SDD/scripts/ci-gate.sh ／ tools/lib/skip_tag_policy.py:388
- **成本**：medium

**為何要緊（逐字）**：訴求逐字是「徹底解決 skipped，沒有 skipped，全部可測」。若只治根層與 AutoClaude 兩棵，答案在字面上就不完整——這兩棵樹的 runtime skip 今天**沒有任何數字**（不是 0，是量不到），而本 repo 自己的紀律逐字寫著「量不到 ≠ 量到零」。靜態站點帳看得到「原始碼裡寫了幾個 skip 站點」，看不到「這次真的 skip 了幾支」，兩者不可互相替代（skip_runtime_report.py 檔頭已說明兩面互補）。

**當回合實測證據（逐字保全）**：

```text
全 repo 搜 census 消費端（Grep *.py，files_with_matches）只有 11 支檔，其中真正的入口只有兩個：
  tools\run_root_unittests.py         ← root 樹
  AutoClaude\tools\local_ci_gate.py   ← AutoClaude 樹
其餘 9 支是 policy／lib／它們自己的測試。
對 AISDLC_SDD 的閘門腳本搜 census/skip_group：
  Grep 'census|skip_group' in AISDLC_SDD/scripts/ci-gate.sh → No matches found
但這兩棵樹**確實有 skip 站點**且已進靜態帳（tools/lib/skip_tag_policy.py:388-401）：
  "AISDLC_SDD/scripts/tests": {windows-only 1, posix-only 1, tool-absence 11, runtime-skipTest 0, unclassified 0}
  LATEST_FSM_TESTS_TREE:      {windows-only 1, posix-only 1, tool-absence 2, runtime-skipTest 0, unclassified 0}
且 `_POSIX_TAG_RATCHET` 對這兩棵各記 1 筆未標籤欠債。
```

**建議修法（逐字）**：

```text
(1) 在 `AISDLC_SDD/scripts/ci-gate.sh` 的 pytest 步驟加 `-rs` 並落 log，收尾呼叫既有的 census（不要再造第三個入口——直接復用 `local_ci_gate.py --census-only`，它吃的是 pytest log 不綁樹）。
(2) 以當場實測值把 `AISDLC_SDD/scripts/tests@<平台>` 與 LATEST fsm_runtime 兩個剖面登記進 `_RUNTIME_SKIP_CEILING`／`_MAX`，並同步補進 `_FULL_SUITE_RUNNERS`（該表現在只有 5 列，兩棵樹的執行者完全不在帳上，`_FULL_SUITE_RUNNERS_MIN=5` 因此也該上調）。
(3) ⚠️ 凍結版 `AISDLC_SDD_v0.01`~ 各版依 Copy-on-Evolve 不動，射程只圈 `scripts/tests` 與 LATEST。
```

### §4.3 本路 `verified_commands`（逐字保全）

```text
全部在本回合實跑，逐字如下（rc 標示；凡接管線者已註明 rc 不可信、改以 log 內容為證）：

1) & "D:\CursorProject\AISDCL_Agent\.venv\Scripts\python.exe" "D:\CursorProject\AISDCL_Agent\tools\run_root_unittests.py" 2>&1 | Out-File -Encoding utf8 <scratchpad>\root_unittests.log
   → 顯示 rc=1，但**該 rc 經過管線不可信**（本 repo 鐵律）；權威證據取自 log 內容：
     "Ran 2466 tests in 337.685s" / "FAILED (failures=4, skipped=43)"
     "[skip census] tools/tests@win32 共 43 支：platform=38／tool-absence=0／env-disabled=0／structural-pair=0／debt=0／untagged=5／欠債型 5 支（目標 0）"

2) docker ps --format "{{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}"
   → autoclaude_pg / pgvector/pgvector:pg18 / Up 44 hours (healthy) / 0.0.0.0:5432->5432/tcp

3) docker exec autoclaude_pg psql -U autoclaude -d autoclaude -c "\du" -c "\l"   → rc=0
   → 角色只有 autoclaude（Superuser）；DB：autoclaude/postgres/template0/template1

4) docker inspect autoclaude_pg --format '{{json .Config.Env}}'   → rc=0
   → POSTGRES_PASSWORD=autoclaude / POSTGRES_DB=autoclaude / POSTGRES_USER=autoclaude / PG_MAJOR=18

5) Push-Location AutoClaude; & <venv>\python.exe -m pytest tests -q -rs 2>&1 | Out-File -Encoding utf8 <scratchpad>\ac_default.log; Pop-Location
   → background exit code 0；log 內：
     "AUTOCLAUDE-PG-DSN-IN-EFFECT=1 AUTOCLAUDE-NESTED-SESSION=1"
     "4199 passed, 44 skipped, 1 warning in 100.06s (0:01:40)"

6) & <venv>\python.exe AutoClaude\tools\local_ci_gate.py --census-only <scratchpad>\ac_default.log   → rc=0
   → "[skip census] AutoClaude/tests@win32+pg+nested 共 44 支：platform=17／tool-absence=3／env-disabled=1／structural-pair=0／debt=0／untagged=23／欠債型 27 支（目標 0）"
   → 並印出互補剖面警告（AutoClaude/tests@linux+pg+solo 至今沒有人量過）

7) Push-Location AutoClaude; $env:AUTOCLAUDE_TEST_PG_DSN='postgresql+asyncpg://autoclaude:autoclaude@localhost:5432/autoclaude'; $env:AUTOCLAUDE_DB_DSN=…; $env:AUTOCLAUDE_ALLOW_INSECURE_DB='1'; $env:SD07_REAL_PG_E2E_ENABLED='true'; $env:PG_REAL_ENABLED='1'; & <venv>\python.exe -m pytest tests -q -rs 2>&1 | Out-File … ; Pop-Location
   → 顯示 Exit code 1；log 內："5 failed, 4194 passed, 44 skipped, 1 warning in 102.13s (0:01:42)"

8) & <venv>\python.exe AutoClaude\tools\check_loc_budget.py   → rc=1
   → "[ROOT-TOOLS] [guardrail_lib<=400] tools/lib/hook_wiring.py: 407 > 400 (+7)"

9) Push-Location AutoClaude; & <venv>\python.exe -m pytest tests/tools/test_check_loc_budget_tier_headroom_warn.py -q --no-header（**未設任何 PG 變數**）
   → "1 failed, 14 passed in 0.42s"

10) Push-Location AutoClaude; & <venv>\python.exe -m pytest tests/contract/test_loc_budget_tiered.py -q --no-header（**未設任何 PG 變數**）
    → "4 failed, 29 passed in 0.71s"（9+10 合計 5，與第 7 項的 5 failed 完全對上 ⇒ 非 PG 造成）

11) git status --porcelain（未接管線）
    → 6 支 M ＋ 1 支 ??（含 tools/lib/hook_wiring.py、docs/06_quality/AutoSDD_Defect_Log.md、archive_64.md）；HEAD=8314939
    （session 起始時系統 env 區塊逐字為 "Status: (clean)"）

12) & <venv>\python.exe <scratchpad>\probe_tag.py   → rc=0
    → ALL_SKIP_TAGS 七個；"TOOL-MISSING registered? -> False"；'[TOOL-MISSING] …' -> group: untagged；'[PG-CORPUS-MISSING] …' -> group: untagged
    → _NONLITERAL_TAG_DEBT = {'[TOOL-MISSING]': 1, '[PG-CORPUS-MISSING]': 1, '[PG-CORPUS-STALE]': 1}

13) & <venv>\python.exe <scratchpad>\probe_py.py（逐字重現 _find_sub_min_interpreter 的候選與判定）   → rc=0
    → cand='python3.10' which-> 'C:\Users\wuwei\.pyenv\pyenv-win\shims\python3.10.BAT'
       -> rc=1 stderr="'python3.10' is not recognized as an internal or external command"
    → 其餘四個候選 which 皆 None 或不存在

14) pyenv versions   → "3.10.11" / "* 3.11.9 (set by D:\CursorProject\AISDCL_Agent\.python-version)"
15) Test-Path C:\Users\wuwei\.pyenv\pyenv-win\versions\3.10.11\python.exe → True
    & C:\Users\wuwei\.pyenv\pyenv-win\versions\3.10.11\python.exe -c "import sys;print(...)"   → rc=0，ver=3.10.11

16) Get-Command uv → C:\Users\wuwei\AppData\Local\...\uv.exe；Get-Command zsh → 空；Get-Command py → 空
    uv python list → cpython-3.12.11 已裝、3.11.9(pyenv shim)、3.10.18/3.9.23/3.8.20 為 <download available>

17) Test-Path HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\AppModelUnlock → True；AllowDevelopmentWithoutDevLicense=（空）
    whoami /priv 內含 SeCreateSymbolicLinkPrivilege → False

18) gh run list --workflow=autoclaude-ci.yml --limit 5 --json …   → rc=0，最近 5 次 conclusion 全為 failure
19) gh api repos/wuweihungmobile/AISDCL_Agent/actions/jobs/93095887118 --jq '…'   → rc=0
    → started=2026-08-08T11:14:51Z completed=2026-08-08T11:14:53Z steps=0 runner=
20) 同查另三個 run 的 Tests job → 皆 steps=0（31191595350 / 31128288018 / 31119121708）
21) gh run view --job 93095887118 --log   → rc=1，"log not found: 93095887118"

22) Grep 'census|skip_group' in AISDLC_SDD/scripts/ci-gate.sh → No matches found
23) Grep 'skip_group_census|report_skip_census|census' 全 repo *.py → 11 支檔，真入口僅 tools/run_root_unittests.py 與 AutoClaude/tools/local_ci_gate.py
```

### §4.4 本路 `honest_gaps`（逐字保全）

```text
1) **本輪最大的量測污染：並行 agent 同時在改 tracked 生產碼。** session 起始 git 為 clean，跑完兩輪後有 6 支 M ＋ 1 支 ??。根層那 4 failed（缺陷帳本歸檔中途態）與 AutoClaude 第二輪那 5 failed（hook_wiring.py 407>400）都是它造成的。我用乾淨環境單獨重跑複驗了 AutoClaude 那 5 支（第 9、10 項），確認與 PG 無關；**根層那 4 支我只做了證據面歸因（失敗訊息點名的三個 DEF-ID 正是被搬進 archive_64.md 的那三筆），沒有做「還原後重跑」的對照組**——因為還原別的 agent 的在途工作違反唯讀約束且會互踩。故根層 4 failed 的歸因是高信度推論，不是實測對照組。

2) **「設了 PG DSN 後新暴露的 failed ＝ 0」這個結論的邊界。** 我比較的是「自動注入 DSN 的基線」與「額外開 SD07_REAL_PG_E2E_ENABLED＋PG_REAL_ENABLED」。我**沒有**跑「完全沒有 PG」的第三組（`AUTOCLAUDE_NO_PG_AUTODETECT=1`），所以「PG DSN 本身有沒有暴露 failed」嚴格說沒有今天的對照組——今天兩次跑 PG 都已經在效力內（兩次都印 AUTOCLAUDE-PG-DSN-IN-EFFECT=1）。R80 記載的「4 個從未執行過的真 failed」若指的是 nopg→pg 那一段，本輪未複驗該段。

3) **多處「預期會消 N 支」是推得值不是實測值**，因為它們都要求改動環境或檔案，超出本階段唯讀射程。逐條標明：
   · seed_kb.py 後再消 3 支（S3-03）——未執行，該指令會同時寫 PG 與 tests/fixtures/ 兩份檔。
   · 開 Developer Mode 後消 2 支（S3-08）——未執行，會改機器狀態。
   · uv pip install -e '.[sdk]' 後消 3 支（S3-09）——未執行，會改共用 .venv 且本輪有並行 agent 在跑全套。
   · 改 [TOOL-MISSING] 字面後 untagged 5→3（S3-05）——未執行，屬改檔。
   落地時每一條都必須當場複驗，不得引用本報告的數字當已驗證。

4) **AutoClaude/tests 的 linux 剖面我沒有量到**（任務 (b) 的核心）。我能證明的是兩件事：它從未被登記（`_UNMEASURED_RUNNER_PROFILES` 逐字），以及唯一會量它的 CI job 連四次 push 都 steps=0 沒執行。我**沒有**用 act 在本機容器跑一次 AutoClaude 那棵樹——那是可行但重的動作（記憶記載 act 映像缺 pwsh 會讓部分 job rc=127），且會與並行 agent 搶資源。所以「那 17 支在世界上任何一處跑過沒有」目前的答案是「查不到證據」，不是「已證明沒跑過」。

5) **CI 為何 steps=0，我只到「形態符合額度/帳單耗盡」為止。** 我沒有查 GitHub Billing（本機拿不到），也沒有讀 run 層級的 annotation。gh 的 log API 對該 job 回 "log not found"，與「從未執行」一致但不是直接證明。

6) **根層 4 failed 使 `run_root_unittests.py` 的 rc 為非零**，所以今天根層那個 census 是在一個「整體紅」的跑次裡印出來的。census 數字本身（43 支、分群明細）我認為可信（skip 統計與那 4 支 assertion 失敗無因果關係），但嚴格說我沒有在全綠跑次下複驗過同一組數字。

7) **AISDLC_SDD 兩棵樹（scripts/tests、LATEST fsm_runtime/tests）我完全沒有跑**，只做了「有沒有 census 入口」的靜態查證（S3-12）。它們今天真正 skip 幾支、理由是什麼，我沒有數字。

8) **zsh 相關 2 支（root）我沒有給出可執行的消除方案。** 實查 `Get-Command zsh` 為空，Windows 沒有原生 zsh（僅 MSYS2/Cygwin/WSL 可得），而那三條路各自都會引入新的載具問題（本 repo 已為 WSL 佔位版 bash 踩過 DEF-101-617/618）。我判斷這 2 支更接近「應標 `[POSIX-NATIVE-ONLY]` 或 `[TOOL-ABSENCE]` 並靠 linux 剖面覆蓋」，但**沒有驗證 linux 剖面上 zsh 是否存在**（root 的 linux census 是 platform=63／untagged=9，那 9 支是誰我沒查）。

9) 訴求逐字要的是「沒有 skipped，全部可測」。**依 repo 現行政策，單一平台上 skip 總數歸零是結構性不可能**（skip_group_policy.py:91 有整段論證：platform 群的意思正是「這支在別的平台才有驗證價值」，在 Windows 上硬跑它是把斷言變假）。我採用了該政策的定義（欠債型＝ZERO 群之和才是歸零標的）。若掌舵者要的是字面上的 0，那是與現行政策衝突的目標，需要先決策，不是我能單方面認定的。
```

## §5 scan:autoclaude-helm — AutoClaude 當舵手的勘查（10 筆）

**任務**：PG 連線參數查對、`AUTOCLAUDE_TEST_PG_DSN` 兩消費端、checkpoint／`scheduled_resume_at` 的真實能力、`example_playbook.yaml` 三欄位的執行語意、以及「今天缺什麼」的可行性判定。

**agentId**：`a091aaafa516266ef`　**筆數**：10（P0 2／P1 4／P2 3／P3 1）

### §5.1 索引

| 本檔 ID | 原始 ID | sev | 標題（逐字） | 檔案:行 | 成本 |
|---|---|---|---|---|---|
| `HLM-S1-01` | S1-01 | P0 | Windows 上兩個 executor 後端全部不可用 ⇒ 今天 `python -m autoclaude <playbook>` 一步都跑不了（R81-2/R81-3 的地基缺口） | AutoClaude/autoclaude/perception/pty_wrapper.py:163；AutoClaude/autoclaude/main.py:64-82 | medium |
| `HLM-S1-02` | S1-02 | P0 | 切到 Pg 後端會**靜默**廢掉 token-halt 的等待：`scheduled_resume_at` 被判為無法解析 → 一律回 0.0（等於「立刻續跑」） | AutoClaude/autoclaude/core/services/auto_resume.py:334-341；AutoClaude/autoclaude/infra/repositories/pg_state_repository.py:244-248 | small |
| `HLM-S1-03` | S1-03 | P1 | PG 連線參數查對完成：角色/DB/密碼皆為 `autoclaude`（R80 猜 `postgres` 是錯的），port 5432，schema 已 migrate 到鏈頭 | AutoClaude/docker-compose.ci.yml:29-34（CI 對等宣告）；N/A（本機容器為實測） | small |
| `HLM-S1-04` | S1-04 | P1 | S3-06 其實**早已落地且有效**——R80 掃描表寫「未落地（repo 內無 ID 痕跡）」是假事實，improving_104 §4.5「先修這個再談跑 Playbook」建立在過期資訊上 | AutoClaude/tests/conftest.py:116-182；docs/06_quality/CrossPlatform_R80_Scan_Findings.md:42 | small |
| `HLM-S1-05` | S1-05 | P1 | `global_goal` 的「每次修正都以此為判斷基準」在預設設定下**不會發生**——`enable_kernel_brain` 預設 False ⇒ 整個 Minimax correction 迴圈是關掉的 | AutoClaude/autoclaude/utils/config.py:19；AutoClaude/autoclaude/main.py:133；AutoClaude/autoclaude/core/kernel.py:230 | small |
| `HLM-S1-06` | S1-06 | P1 | `auto_compact_interval` 在 production 是**死碼**：唯一消費點只在已被拔除的 PlaybookRunner 路徑上，Kernel（唯一正式路徑）完全不讀它 | AutoClaude/autoclaude/execution/steps_orchestrator/_impl.py:144-155；AutoClaude/autoclaude/main.py:127-138 | medium |
| `HLM-S1-07` | S1-07 | P2 | Token Guard 的 80% compact／90% halt 是**真的接上電**（非註解），但整條鏈掛在一個易碎的前提：`peak_pct > 0` | AutoClaude/autoclaude/core/kernel.py:187-209、320-349；AutoClaude/autoclaude/infra/adapters/pty_executor.py:141-162 | small |
| `HLM-S1-08` | S1-08 | P2 | 要跑在 Pg 後端必須改三處設定，且 `storage.mode` 預設 `yaml_only` ⇒ 不改就等於沒有跨行程續航能力 | AutoClaude/config.yaml:98；AutoClaude/autoclaude/utils/config.py:232-253 | small |
| `HLM-S1-09` | S1-09 | P2 | 守 naive 時間戳的既有機械鎖，對 S1-02 這個方向**結構上失明**（它只掃產出端的 naive，看不到「產出 aware、消費端只吃 naive」） | tools/tests/test_platform_neutral_paths.py:4526-4534、4580-4584 | small |
| `HLM-S1-10` | S1-10 | P3 | AutoClaude 不自動載入 `.env`（無 python-dotenv）⇒ 排程／無人看管啟動時，`MINIMAX_API_KEY` 與 `AUTOCLAUDE_DB_DSN` 會靜默缺席 | AutoClaude/config.yaml:14 | small |

### §5.2 逐筆（證據逐字保全）

#### `HLM-S1-01`｜[P0] Windows 上兩個 executor 後端全部不可用 ⇒ 今天 `python -m autoclaude <playbook>` 一步都跑不了（R81-2/R81-3 的地基缺口）

- **檔案:行**：AutoClaude/autoclaude/perception/pty_wrapper.py:163；AutoClaude/autoclaude/main.py:64-82
- **成本**：medium

**為何要緊（逐字）**：§4.5 R81-3 第 3 點要求「把無人看管續跑的載體從 `claude -p -r` 換成 `python -m autoclaude <playbook>`，且跑在 Pg 後端」。今天這件事在這台 Windows 機器上**結構上做不到**：預設 pty 後端在 `pty.start()` 就不回返（不是報錯、是靜默卡住，連 `step_timeout_seconds` 都管不到——逾時判斷在 start() 之後的 while 迴圈裡），而唯一的替代後端連套件都沒裝。這是整條主線的前置條件，不解掉後面 4 項全部無從驗證。

**當回合實測證據（逐字保全）**：

```text
① 載具解析：`Get-Command claude` → `SOURCE=C:\Users\wuwei\.local\bin\claude.exe`／`TYPE=Application`（**不是** .cmd shim）。② 分支判定（當回合探針 rc=0）：`WEXPECT_AVAILABLE = True`／`resolve_command = ['C:\Users\wuwei\.local\bin\claude.EXE']`／`is_cmd_shim = False` ⇒ `start()` 走 `_start_wexpect`（pty_wrapper.py:163 的條件 `_WEXPECT_AVAILABLE and not _is_cmd_shim(...)` 成立）。③ 有界實測（args 用無害的 `--version`，60s 硬逾時）：`ELAPSED=60.0s => TIMEOUT: pty.start() DID NOT RETURN in 60s`；探針前後 `Get-Process claude` 三支 PID 的 StartTime 全部早於探針（08:58/01:08/前一日）⇒ `claude.exe` 確實從未被啟動，與根 CLAUDE.md 記載的三次量測（180/180/45s）同形，本回合為第四次獨立重現。④ 另一條路也是死的：`claude_agent_sdk MISSING`／`claude_code_sdk MISSING`（探針 rc=0），而 `config.yaml:90` 是 `backend: pty`。
```

**建議修法（逐字）**：

```text
兩條路擇一，且**都要先於**寫 Playbook：(a) 短路徑——`uv pip install 'autoclaude[sdk]'` 後把 `config.yaml` 的 `executor.backend` 改 `sdk`，繞開 wexpect（代價：SDK 後端的 production 里程遠少於 pty，且 `permission_mode` 需審）；(b) 正路徑——修 `pty_wrapper.start()` 的分支條件：`_is_cmd_shim` 今天是「唯一」把 Windows 導向 subprocess 的判準，但真正該問的是「wexpect 在這個載具上啟得起來嗎」。建議把 Windows 上的 `.exe` 也導向 `_start_subprocess`（該路徑已有完整實作與 CPython 原始碼驗證），並補一支「start() 必須在 N 秒內回返」的有界迴歸測試——目前零測試覆蓋 `start()` 的回返性，所以這個 P0 才能潛伏四輪。
```

#### `HLM-S1-02`｜[P0] 切到 Pg 後端會**靜默**廢掉 token-halt 的等待：`scheduled_resume_at` 被判為無法解析 → 一律回 0.0（等於「立刻續跑」）

- **檔案:行**：AutoClaude/autoclaude/core/services/auto_resume.py:334-341；AutoClaude/autoclaude/infra/repositories/pg_state_repository.py:244-248
- **成本**：small

**為何要緊（逐字）**：這正是 R81-3 表格裡「AutoClaude ＋ Playbook → PostgreSQL → 額度 reset 後還在嗎：在」所依賴的那個欄位。狀態確實還在（S1-04 已證欄位完整往返），但**它的語意在 Pg 後端上是死的**：`token_guard.resume_delay_minutes: 30` 會變成 0 秒，`auto_resume: true` ＋ `max_auto_resumes: 10` 於是變成「撞到 90% → 立刻原地重試 → 再撞 → …」連燒 10 次。失效方向是最壞的那一邊（不是不續跑，是不等就續跑），而且完全靜默——只有一行 warning，rc 全綠。這是本 repo 判過三次的「機制蓋好沒接電」的第四例，且**只在切到 Pg 後端時才出現**，正好就是本輪要切過去的那個後端。

**當回合實測證據（逐字保全）**：

```text
跨行程實測（Process A rc=0 存、Process B rc=0 讀）：A 呼叫 `PgStateRepository.schedule_resume(pid, delay_minutes=30)` → 回 `2026-08-08T13:50:19.673762+00:00`；B（全新行程 PID 39804）載回 `scheduled_resume_at= 2026-08-08T13:50:19+00:00`，但同一支 `seconds_until_resume()` 印出 `無法解析 scheduled_resume_at='2026-08-08T13:50:19+00:00': can't subtract offset-naive and offset-aware datetimes` 並回 **0.0**。並列對照（rc=0）把成因釘死：File 後端形態 `2026-08-08T21:51:00`（naive）→ **1799.5**；Pg 後端形態 `2026-08-08T13:51:00+00:00`（aware）→ **0.0**。根因＝`file_state_repository.py:116` 用 `datetime.now()`（naive）、`pg_state_repository.py:244` 用 `datetime.now(UTC)`（aware），而消費端 `auto_resume.py:335` 寫死 `resume_at - datetime.now()`（naive）⇒ Pg 那一支必拋 TypeError，被 336 行的 `except (ValueError, TypeError)` 吞掉、fallback 0.0。
```

**建議修法（逐字）**：

```text
修消費端而非產出端（產出端 aware 才是對的）：`seconds_until_resume()` 解析後若 `resume_at.tzinfo is not None` 就用 `datetime.now(resume_at.tzinfo)` 相減，否則維持 `datetime.now()`；`FileStateRepository.seconds_until_resume`（file_state_repository.py:129）是同一份邏輯的第二個家，須一併修或收斂成單一 SSOT。🔴 更關鍵的是補鎖：現有 4 支測試（test_dry_run_kernel_path.py:226-241）全部餵 naive `datetime.now()`，aware 形態**零覆蓋**，而其中 `test_seconds_until_resume_invalid` 還把「解析不了就回 0.0」釘成契約——所以這個缺陷在今天的測試庫裡是「正確通過」的。要加的是「Pg 後端產出的字串必須算得出正數秒」這一條，且判準要跨兩個後端對稱。
```

#### `HLM-S1-03`｜[P1] PG 連線參數查對完成：角色/DB/密碼皆為 `autoclaude`（R80 猜 `postgres` 是錯的），port 5432，schema 已 migrate 到鏈頭

- **檔案:行**：AutoClaude/docker-compose.ci.yml:29-34（CI 對等宣告）；N/A（本機容器為實測）
- **成本**：small

**為何要緊（逐字）**：§4.5 R81-3 明列「查對連線參數（角色名／DB 名／port）並寫進 ONBOARDING，本輪實測『猜 postgres 是錯的』」。現在有了實測答案，且順帶證明這顆 DB **不需要重新 migrate**（已在 0018 鏈頭、pgvector 就位）⇒ 跑 Playbook 前的 DB 前置是零工作量。另外校正一筆既有記憶：本機是 **pg18**、CI 是 **pg17**（docker-compose.ci.yml:27 逐字 `pgvector/pgvector:pg17`），版本漂移仍在。

**當回合實測證據（逐字保全）**：

```text
`docker inspect autoclaude_pg --format '{{json .Config.Env}}'`（rc=0）→ `POSTGRES_PASSWORD=autoclaude`／`POSTGRES_DB=autoclaude`／`POSTGRES_USER=autoclaude`／`PG_MAJOR=18`／`PG_VERSION=18.4-1.pgdg12+1`。Port（rc=0）→ `{"5432/tcp":[{"HostIp":"0.0.0.0","HostPort":"5432"}]}`。成功連線（rc=0）：`docker exec autoclaude_pg psql -U autoclaude -d autoclaude -c "SELECT version();"` → `PostgreSQL 18.4 (Debian 18.4-1.pgdg12+1) on x86_64-pc-linux-gnu`。Schema（rc=0）：`\dt` 回 **46 個 table**（含 `checkpoints`／`playbook_runs`／`goal_tasks`／`knowledge_entries` 分區族）；`SELECT * FROM alembic_version` → `0018_version_kind_discriminator`；`pg_extension` → `plpgsql 1.0`／`vector 0.8.2`。`\d checkpoints` 確認 `scheduled_resume_at timestamp with time zone` 欄位存在。可用 DSN 形態＝`postgresql+asyncpg://autoclaude:autoclaude@localhost:5432/autoclaude`。
```

**建議修法（逐字）**：

```text
把這組參數與「`-U postgres` 會 FATAL」的反例一起寫進根層 ONBOARDING（§7 或 PG 專節），並在同一處標明本機 pg18 vs CI pg17 的差異。⚠️ 密碼雖是 dev 值，仍屬 DSN 帳密——依 llm-config-governance 慣例，完整 DSN 應走 `.env` 的 `AUTOCLAUDE_DB_DSN`，ONBOARDING 只寫參數名與取得方式，不要把含密碼的完整字串貼進入庫文件。
```

#### `HLM-S1-04`｜[P1] S3-06 其實**早已落地且有效**——R80 掃描表寫「未落地（repo 內無 ID 痕跡）」是假事實，improving_104 §4.5「先修這個再談跑 Playbook」建立在過期資訊上

- **檔案:行**：AutoClaude/tests/conftest.py:116-182；docs/06_quality/CrossPlatform_R80_Scan_Findings.md:42
- **成本**：small

**為何要緊（逐字）**：§4.5 R81-3 把「先修這個再談跑 Playbook」列為 Pg 動作的前置封鎖條件；實況是它已經修好、還從「15 支在 setup 硬炸」升級成「收集前一則可執行指引」。照原文做會浪費一整包工，去修一個已經不存在的缺陷——正是 Q4 判定的最大桶（宣稱先於查證）在真實工作裡的形態，而這次它長在指導下一輪的計畫書上。另一面同樣重要：R80 掃描表的「未落地」判準是「repo 內無 ID 痕跡」，而痕跡明明就在（字串 `S3-06` 在 conftest.py 與 test_local_ci_gate.py:887 都在）⇒ 那個判準本身有鑑別力問題。

**當回合實測證據（逐字保全）**：

```text
conftest.py:116 逐字寫著 `# ── R80 包 A（S3-06）：\`AUTOCLAUDE_TEST_PG_DSN\` 的形態驗證`，實作為 `pg_dsn_problems()`（純函式）＋ `_check_pg_dsn_shape()`，掛在 `pytest_configure`（收集之前）。**當回合端到端實證**：設 `AUTOCLAUDE_TEST_PG_DSN='postgresql://autoclaude:autoclaude@localhost:5432/autoclaude'`（合法但同步形態）跑 contract 測 → **rc=4**，訊息逐字指出「少了 async driver」「兩類消費端驅動需求互斥」並直接給出修法字串。改用 `postgresql+asyncpg://...` 後（rc=0）→ **76 passed, 2 skipped in 1.84s**。互斥的兩端也已逐檔查證：非同步端 `tests/contract/test_pg_state_repository_contract.py`／`test_pg_existing_schema_lock.py` 把 DSN 原封餵給 `create_async_engine`（**必須**帶 `+asyncpg`）；同步端 `tests/contract/test_alembic_00*.py` 與 `conftest._resolve_real_pg_dsn`（:280）一律先 `re.sub(r"\+asyncpg", "", raw)` 再交 psycopg2（帶不帶都行）⇒ 交集只有一種寫法。
```

**建議修法（逐字）**：

```text
① 訂正 `CrossPlatform_R80_Scan_Findings.md:42` 該列狀態為已落地並附本回合 rc=4／rc=0 兩則實測；② 訂正 improving_104 §4.5 R81-3 第三個 ⚠️ bullet，把「先修這個再談跑 Playbook」改成「已修，直接用 `+asyncpg` 形態」；③ 檢討「repo 內無 ID 痕跡」這個落地判準——它掃的顯然不是 `AutoClaude/tests/**`，射程要補齊，否則下一輪還會再誤判一次。
```

#### `HLM-S1-05`｜[P1] `global_goal` 的「每次修正都以此為判斷基準」在預設設定下**不會發生**——`enable_kernel_brain` 預設 False ⇒ 整個 Minimax correction 迴圈是關掉的

- **檔案:行**：AutoClaude/autoclaude/utils/config.py:19；AutoClaude/autoclaude/main.py:133；AutoClaude/autoclaude/core/kernel.py:230
- **成本**：small

**為何要緊（逐字）**：§4.5 R81-2 的整個立論是「`global_goal` ＝無人看管那一跑缺的判準」，並引用 example_playbook.yaml 註解「每次修正都會以此為判斷基準，避免修正方向偏離整體目標」。實況是：**那句註解描述的能力預設是關的**。不開 flag 就換載具，拿到的 AutoClaude 只會照 Playbook 順序把 prompt 送出去、失敗就重試到耗盡然後 escalate——判斷力並不比 `claude -p -r` 多，而 R81-1 的整個分工論證（「headless 續跑只是手腳、不會做判斷」）就落空了。這一格是「機制蓋好沒接電」的變體：電閘存在、預設在 OFF。

**當回合實測證據（逐字保全）**：

```text
`config.py:19` → `enable_kernel_brain: bool = False`，其下註解逐字：「預設 False＝production 維持 brain=None（無 Minimax 逐步 correction、無 escalation 諮詢，零退化）」。`main.py:133` → `brain = MinimaxBrainAdapter(minimax) if cfg.minimax.enable_kernel_brain else None`。`kernel.py:230` → `if self._brain is not None and attempt < max_retries:` 才會呼叫 `decide_correction(..., global_goal=playbook.global_goal, ...)`（:243-247）。實查 `AutoClaude/config.yaml` 的 `minimax:` 區塊（第 8-18 行）**沒有** `enable_kernel_brain` 鍵 ⇒ 吃預設 False。brain=None 時失敗路徑直接落到 `POST_ATTEMPT` → 重試耗盡 → `ESCALATE`（kernel.py:285-291），全程沒有任何一次拿 global_goal 去判斷方向。剩下真正會發生的 global_goal 用途只有文字注入：`global_goal_anchor_plugin.py:59/62` 把它當 prompt 前綴（首步全文 500 字、非首步精簡 150 字）、:107-109 塞進 /compact 的 MEMORY ANCHOR。
```

**建議修法（逐字）**：

```text
開 flag 前先確認代價：啟用 `minimax.enable_kernel_brain: true` 會讓 **Minimax API 故障直接觸發 ESCALATION**（config.py:22-23 明載），且需要 `.env` 的 `MINIMAX_API_KEY`（config.yaml:14 另註「AutoClaude 不自動載入 .env」，見 S1-10）。建議在 R81 的可行性 Playbook 裡把 `enable_kernel_brain` 列為**必要設定**並在計畫書寫明「不開這個 flag 就等於沒有舵手」，同時把 example_playbook.yaml 那句註解補上前提條件——否則那句註解本身就是下一輪的假事實來源。
```

#### `HLM-S1-06`｜[P1] `auto_compact_interval` 在 production 是**死碼**：唯一消費點只在已被拔除的 PlaybookRunner 路徑上，Kernel（唯一正式路徑）完全不讀它

- **檔案:行**：AutoClaude/autoclaude/execution/steps_orchestrator/_impl.py:144-155；AutoClaude/autoclaude/main.py:127-138
- **成本**：medium

**為何要緊（逐字）**：§4.5 R81-2 把 `global_invariants.auto_compact_interval` 列為「掌舵者訴求 2（context 不要爆）的**已存在**機械化版本」，並在 R81-3 第 4 點要求「量 auto_compact_interval 的實效」。答案是：它今天在 production 一次都不會被觸發，因為承載它的那條路已在 SD_05 W6 被拔掉。這與互動側那道 90% 門檻「0/70 session 觸發過」不是同一種病——那個是水位到不了，這個是**程式碼根本不在執行路徑上**。若不先查清就去「量實效」，會量到一個恆為 0 的數字然後誤判成「門檻太高」。真正在 Kernel 路徑上管 context 的是 token_guard 的 80%/90%（見 S1-07），那是計 token 不是計次。

**當回合實測證據（逐字保全）**：

```text
全庫 grep `auto_compact_interval` 在 `autoclaude/` 底下只有兩處：`models/playbook.py:8`（欄位定義 `auto_compact_interval: int = 5  # 0 = disabled`）與 `execution/steps_orchestrator/_impl.py:144`（唯一讀取）。該讀取點的語意是**計次不計 token**：`interval = playbook.global_invariants.auto_compact_interval` / `if interval > 0 and runner._step_counter > 0 and runner._step_counter % interval == 0:` → `runner._send_compact(...)`，即「每 N 個 step 無條件送一次 /compact」，與 context 百分比毫無關係。可達性鏈：`run_steps_impl` 只被 `playbook_runner.py:218` 的 `PlaybookRunner._run_steps` 呼叫，而該方法只被同檔 :372 呼叫；全 `autoclaude/` 內 grep `PlaybookRunner(` **零命中**（無人實例化）。`main.py` 的 import 清單（:24-33）沒有 playbook_runner，流程是 `build_kernel(...)` → `AutoResumeService(kernel, ...)` → `service.run(...)`（:134-138），且 :123-124 逐字寫「SD_Improving_05 W6：雙路徑已移除；Kernel 路徑為唯一正式路徑。舊 PlaybookRunner 直連模式已於 W6 拔除」。
```

**建議修法（逐字）**：

```text
R81 先在計畫書把這一格的結論改掉（`auto_compact_interval` ＝ legacy 欄位、Kernel 不消費），再決定二選一：(a) 承認它是遺留欄位，於 models/playbook.py 標 deprecated 並在 README/AutoClaude_Guide 的欄位表（docs/AutoClaude_Guide.md:218 逐字寫「每 N 步送一次 /compact」）加註「Kernel 路徑不支援」——那三份文件今天都在描述一個不會發生的行為；(b) 若確實要「計次強制壓縮」這個能力，把它接進 Kernel 的 `_run_step` 迴圈。**不要**兩件事一起做，也不要在沒接電前就去量它。
```

#### `HLM-S1-07`｜[P2] Token Guard 的 80% compact／90% halt 是**真的接上電**（非註解），但整條鏈掛在一個易碎的前提：`peak_pct > 0`

- **檔案:行**：AutoClaude/autoclaude/core/kernel.py:187-209、320-349；AutoClaude/autoclaude/infra/adapters/pty_executor.py:141-162
- **成本**：small

**為何要緊（逐字）**：這是任務點名要查的「機制蓋好沒接電」高風險項，結論是**這一項已經接上了**（improving_78/79/82 三輪修的），不該再被當成缺口重修一次——本 repo 反覆在治的病之一就是去補一支已經存在的鎖。但要誠實劃界：整條鏈的存活取決於 `claude -p --output-format json` 的輸出裡有 `modelUsage[*].contextWindow` 這個欄位，那是**上游 CLI 的介面**，不在本 repo 控制下；`token_tracker.py:103-105` 自己也註明 pct 是「近似值、非 claude 自報」。一旦上游改欄位名，`peak_pct` 會恆為 0、整個 80/90 門檻靜默失效，而表徵與「跑得很順、從沒撞到門檻」完全相同。

**當回合實測證據（逐字保全）**：

```text
接線鏈逐段實查：`kernel.py:187` 建 `TokenObserver()` → :188-191 以 `on_event=observer` 傳進 `self._exec.execute(...)` → :205 `_consult_token_guard(..., observer.peak_pct, ...)` → :333 emit `ON_TOKEN_USAGE` → :339 `if tu.request_halt:` 回 `StepAction.HALT`（印 `TOKEN_HALT` marker）、:346 `if tu.request_compact:` 委派 `_handle_compact`（:366 `perform_compact` 送 /compact，:371 emit `POST_COMPACT` 收 Gap-008-E 連續失敗）。門檻來自 `config.yaml:60/62` 的 `compact_threshold_pct: 80.0`／`halt_threshold_pct: 90.0`（config.py:139/141 同預設，並有 `halt > compact` 的 model_validator）。訊號源：`pty_executor.py:146-160`，在 `output_format == "json"`（`config.py:66` 預設 `"json"`）時以 `context_pct_from_claude_json(parsed)` 算出 pct 並 emit `TOKEN_PCT`。🔴 易碎點：`kernel.py:331` 是 `if peak_pct <= 0: return None`，而 pct 的取得需要三件事同時成立——`--output-format json` 有加、輸出解析得出 JSON（否則 :164-168 只印 warning 就退回純文字）、且 JSON 內同時有 `usage` 與 `modelUsage.contextWindow`（token_tracker.py:107-125，任一缺就回 None）。`_token_observer.py` 檔頭自陳這條線在 improving_78 之前正是「production 結構性死碼」。另註：`config.yaml:70-74` 把 `context_patterns` 覆寫成只剩 4 條（預設 7 條，token_tracker.py:20-35），砍掉 `Context window:`／`[STATS: usage`／`Token usage:` 三條——這只影響 PTY 逐行文字的 fallback 解析，不影響 json 主路徑。
```

**建議修法（逐字）**：

```text
不要重蓋，改補一支**訊號源存活探針**：真跑一次 `claude -p --output-format json` 的最小 prompt，斷言 `context_pct_from_claude_json(parsed) is not None`。這比任何靜態測試都有鑑別力，因為它問的是「上游今天還發不發這個欄位」。可掛在 nightly（非 push 閘門，避免每次 push 都花 API 額度）。另外把 `config.yaml:70-74` 那份被砍成 4 條的 `context_patterns` 與 token_tracker 的 7 條預設對齊或直接刪掉該覆寫——同一份知識兩個家、且入庫的那個家是舊的。
```

#### `HLM-S1-08`｜[P2] 要跑在 Pg 後端必須改三處設定，且 `storage.mode` 預設 `yaml_only` ⇒ 不改就等於沒有跨行程續航能力

- **檔案:行**：AutoClaude/config.yaml:98；AutoClaude/autoclaude/utils/config.py:232-253
- **成本**：small

**為何要緊（逐字）**：R81-3 的整個論證（「AutoClaude 做得到而 claude -p -r 做不到，因為狀態在 PostgreSQL」）只有在 `mode` 不是預設值時才成立。照現況直接跑 `python -m autoclaude scripts/example_playbook.yaml`，checkpoint 會寫進 File backend，PG 那 46 張表一列都不會動——舵手狀態不落 DB，等於沒有 R81-3 說的那個結構優勢。另一個容易踩的坑：`db_only` 換了 playbook_id 演算法，所以從 File 切到 Pg 之後，既有 checkpoint **對不上**（stem vs sha256），會被當成沒有 checkpoint 而從頭跑。

**當回合實測證據（逐字保全）**：

```text
`config.yaml:98` → `mode: yaml_only`；`config.py:232` → `mode: Literal["yaml_only", "both", "db_only"] = "yaml_only"`。`db_only`／`both` 有 model_validator 硬閘（config.py:241-253）：沒有 `db_dsn` 也沒有 `AUTOCLAUDE_DB_DSN`／`AUTOCLAUDE_PG_DSN` 就直接 ValueError 拒絕啟動。另有 TLS 強制（factory.py:12-13）：非 TLS DSN 需 `AUTOCLAUDE_ALLOW_INSECURE_DB=1` override，本回合實測會印 `AUTOCLAUDE_ALLOW_INSECURE_DB=1，已停用 TLS 強制檢查（僅供 dev/test，禁止 production 使用）`。playbook_id 策略也隨 mode 改變（factory.py:41-62）：`yaml_only`/`both` 用 `Path.stem`、`db_only` 用 `sha256(abs_path)[:16]`——本回合實測 `R81_probe_playbook.yaml` → `6c86756b2a1ce144`。三處設定＝`storage.mode: db_only` ＋ env `AUTOCLAUDE_DB_DSN=postgresql+asyncpg://autoclaude:autoclaude@localhost:5432/autoclaude` ＋ env `AUTOCLAUDE_ALLOW_INSECURE_DB=1`。
```

**建議修法（逐字）**：

```text
在 R81 的可行性 Playbook 旁附一份 `config.local.yaml`（該檔已存在，929 bytes，且 `--config` 參數本就支援）把 `storage.mode: db_only` 寫進去，DSN 走 `.env` 的 `AUTOCLAUDE_DB_DSN`（絕不入庫，符合既有機密邊界）。並在 ONBOARDING 記下「切 mode 會換 playbook_id 演算法」這個一次性遷移陷阱。
```

#### `HLM-S1-09`｜[P2] 守 naive 時間戳的既有機械鎖，對 S1-02 這個方向**結構上失明**（它只掃產出端的 naive，看不到「產出 aware、消費端只吃 naive」）

- **檔案:行**：tools/tests/test_platform_neutral_paths.py:4526-4534、4580-4584
- **成本**：small

**為何要緊（逐字）**：這是根 CLAUDE.md 鐵律三那張表最想抓的形態：**有鎖在守、鎖是綠的、但守的是另一半**。比沒有鎖更難看見——因為表格上那一格已經有具名機械物，下一輪的覆蓋率棘輪會把它算進分子，看起來這類危害「已經有人管了」。R80 收輪報告已把「有鎖在守假話」列為重複發生的形態，這是同一形態的又一例。

**當回合實測證據（逐字保全）**：

```text
該鎖的判準核心是 `_is_naive_now_call()`（:4526-4533）——只認 `datetime.now()`／`utcnow()` 且**未傳任何 tz** 的呼叫。`PgStateRepository.schedule_resume` 用的是 `datetime.now(UTC)`（帶 tz、完全正確）⇒ 對這支掃描器而言是隱形的。欠債清單 `_NAIVE_TS_PERSIST_DEBT`（:4580）確實收了 File 側那一筆，理由欄逐字寫「checkpoint.saved_at；讀側 auto_resume 以 `resume_at - datetime.now()` 相減 ⇒ 這一筆就是 Kernel 會提早一小時恢復的那條路。不在本包所有權內，已交棒」——**它看見了消費端的形狀，卻只把它記成 File 那一筆的附註**，沒有把「消費端無法處理 aware 輸入」獨立成一條判準。於是 Pg 那一支（危害更大、且是本輪要切過去的後端）從頭到尾沒有任何東西在守。測試側同樣失明：4 支 `seconds_until_resume` 測試全餵 naive，且 `test_seconds_until_resume_invalid`（test_dry_run_kernel_path.py:240-241）把「解析不了 → 0.0」釘成契約。
```

**建議修法（逐字）**：

```text
補的不是掃描器而是**行為判準**：一支對稱測試，對 File／Pg／InMemory 三個 repository 各跑一次 `schedule_resume(delay_minutes=30)` → `seconds_until_resume(cp.scheduled_resume_at)`，斷言三者都回落在 (0, 1800] 區間。這條判準會在 S1-02 修好前必紅、修好後轉綠，且不依賴任何字串或 AST 形狀（後端換寫法也不會失明）。修好後把 `_NAIVE_TS_PERSIST_DEBT` 裡 file_state_repository 那筆的理由欄一併更新——它目前描述的因果已被本回合實測部分證偽（真正會出事的是 Pg 那一支，File 那一支反而是唯一算得對的）。
```

#### `HLM-S1-10`｜[P3] AutoClaude 不自動載入 `.env`（無 python-dotenv）⇒ 排程／無人看管啟動時，`MINIMAX_API_KEY` 與 `AUTOCLAUDE_DB_DSN` 會靜默缺席

- **檔案:行**：AutoClaude/config.yaml:14
- **成本**：small

**為何要緊（逐字）**：R81 的目標場景是**無人看管**啟動（schtasks／背景行程），而那種啟動方式不會經過任何 interactive shell 的 `source .env`。後果分兩種、都不會當場報錯：缺 `AUTOCLAUDE_DB_DSN` 時 `db_only` 會在啟動期 ValueError（這個還算 fail-loud）；缺 `MINIMAX_API_KEY` 時若 `enable_kernel_brain` 為 true，會等到第一次 correction 才炸成 ESCALATION（S1-05），而那時已經跑掉數個 step 了。

**當回合實測證據（逐字保全）**：

```text
`config.yaml:14` 逐字：「⚠ AutoClaude 不自動載入 .env（無 python-dotenv）——env 須由啟動方式注入（shell 先 source .env 或 export）」。實查 `AutoClaude/` 下 `.env` 存在（2505 bytes）、`.env.example` 存在（8144 bytes）。`main.py:103-107` 只讀 `os.environ.get("MINIMAX_API_KEY")` 等，沒有任何 dotenv 載入；`factory._resolve_dsn`（factory.py:68-70）同樣只讀 `os.environ`。
```

**建議修法（逐字）**：

```text
不要為此引入 python-dotenv（會多一個相依、且與既有機密邊界治理無關）。改在無人看管的啟動載具（schtasks Action 或包一層 .ps1）裡顯式注入這兩個 env，並在該載具開頭加一道前置斷言：兩個變數任一為空就 rc≠0 立即退出、不要開跑。這與本 repo「憑證是值不是 rc」的取證紀律同型——啟動前先驗前提，不要讓失敗延後到半路。
```

### §5.3 本路 `verified_commands`（逐字保全）

```text
全部在 PowerShell 工具內執行（未使用 Bash 工具）；python＝D:\CursorProject\AISDCL_Agent\.venv\Scripts\python.exe

【PG 連線與 schema — 任務點 1】
1. docker inspect autoclaude_pg --format '{{json .Config.Env}}'                                  → rc=0
   輸出：POSTGRES_PASSWORD=autoclaude / POSTGRES_DB=autoclaude / POSTGRES_USER=autoclaude / PG_MAJOR=18 / PG_VERSION=18.4-1.pgdg12+1
2. docker inspect autoclaude_pg --format '{{json .NetworkSettings.Ports}}'                        → rc=0
   輸出：{"5432/tcp":[{"HostIp":"0.0.0.0","HostPort":"5432"},{"HostIp":"::","HostPort":"5432"}]}
3. docker exec autoclaude_pg psql -U autoclaude -d autoclaude -c "SELECT version();"              → rc=0  ★成功的 psql 連線
   輸出：PostgreSQL 18.4 (Debian 18.4-1.pgdg12+1) on x86_64-pc-linux-gnu, compiled by gcc (Debian 12.2.0-14+deb12u1) 12.2.0, 64-bit  (1 row)
4. docker exec autoclaude_pg psql -U autoclaude -d autoclaude -c "\dt"                            → rc=0  (46 rows；含 checkpoints/playbook_runs/goal_tasks/knowledge_entries 分區族)
5. docker exec autoclaude_pg psql -U autoclaude -d autoclaude -c "SELECT extname, extversion FROM pg_extension;" → rc=0  (plpgsql 1.0 / vector 0.8.2)
6. docker exec autoclaude_pg psql -U autoclaude -d autoclaude -c "SELECT * FROM alembic_version;" → rc=0  (0018_version_kind_discriminator)
7. docker exec autoclaude_pg psql -U autoclaude -d autoclaude -c "\d checkpoints"                 → rc=0  (scheduled_resume_at = timestamp with time zone，可為 NULL)

【executor 載具 — 任務點 5 / S1-01】
8. Get-Command claude                                                                             → SOURCE=C:\Users\wuwei\.local\bin\claude.exe ; TYPE=Application
9. & $py $env:TEMP\probe_pty.py                                                                   → rc=0
   輸出：WEXPECT_AVAILABLE = True / resolve_command = ['C:\Users\wuwei\.local\bin\claude.EXE'] / is_cmd_shim = False / => start() branch = _start_wexpect (HANG RISK)
10. & $py $env:TEMP\probe_runner.py $py $env:TEMP\probe_start.py   （PtyWrapper(args=["--version"]).start()，60s 硬逾時）
    → 輸出：ELAPSED=60.0s => TIMEOUT: pty.start() DID NOT RETURN in 60s  （runner 自身 rc=0）
11. Get-Process -Name claude | Select Id,StartTime                                                 → 3 支，StartTime 全早於探針（08:58:29 / 01:08:08 / 前一日 07:52:20）⇒ claude.exe 未被啟動
12. & $py $env:TEMP\probe_deps.py                                                                  → rc=0
    輸出：claude_agent_sdk MISSING / claude_code_sdk MISSING / wexpect INSTALLED / psycopg2 INSTALLED / asyncpg INSTALLED / sqlalchemy INSTALLED / alembic INSTALLED

【AUTOCLAUDE_TEST_PG_DSN 兩消費端 — 任務點 2 / S1-04】
13. $env:AUTOCLAUDE_TEST_PG_DSN='postgresql://autoclaude:autoclaude@localhost:5432/autoclaude'
    & $py -m pytest tests/contract/test_pg_state_repository_contract.py -q --no-header             → rc=4
    輸出（節錄）：ERROR: [AUTOCLAUDE_TEST_PG_DSN] ... 少了 async driver ... 修法（把 postgresql:// 改成 postgresql+asyncpg://）
14. $env:AUTOCLAUDE_TEST_PG_DSN='postgresql+asyncpg://autoclaude:autoclaude@localhost:5432/autoclaude' ; $env:AUTOCLAUDE_ALLOW_INSECURE_DB='1'
    & $py -m pytest tests/contract/test_pg_state_repository_contract.py tests/contract/test_pg_existing_schema_lock.py -q --no-header → rc=0
    輸出：76 passed, 2 skipped in 1.84s ； [PG autodetect] 跳過：AUTOCLAUDE_TEST_PG_DSN 已由使用者顯式設定（顯式優先）

【checkpoint 跨行程存活 + scheduled_resume_at — 任務點 3 / S1-02】
15. & $py $env:TEMP\pg_save.py   （Process A，storage.mode=db_only）                               → rc=0
    輸出：REPO = PgStateRepository / SAVED playbook_id = 6c86756b2a1ce144 / scheduled_resume_at = 2026-08-08T13:50:19.673762+00:00 / PROCESS_A_PID = 3524
16. & $py $env:TEMP\pg_load.py   （Process B，全新行程）                                            → rc=0
    輸出：PROCESS_B_PID = 39804 / LOADED = True / step_idx=3 / step_id=T04 / total_steps=7 / peak_token_pct=91.5 /
          completed_step_ids=['T01','T02','T03'] / scheduled_resume_at=2026-08-08T13:50:19+00:00
          ★ seconds_until_resume | 無法解析 ...: can't subtract offset-naive and offset-aware datetimes → 回 0.0
17. & $py $env:TEMP\cmp_resume.py  （File vs Pg 形態並列）                                          → rc=0
    輸出：File backend style 2026-08-08T21:51:00 → seconds_until_resume = 1799.5
          Pg   backend style 2026-08-08T13:51:00+00:00 → seconds_until_resume = 0.0
18. docker exec autoclaude_pg psql -U autoclaude -d autoclaude -c "DELETE FROM checkpoints WHERE playbook_id='6c86756b2a1ce144'; DELETE FROM playbook_runs WHERE playbook_id='6c86756b2a1ce144';" → rc=0 (DELETE 1 / DELETE 1)
19. docker exec autoclaude_pg psql -U autoclaude -d autoclaude -c "SELECT count(*) FROM checkpoints WHERE playbook_id='6c86756b2a1ce144';" → rc=0 (count=0，探針資料已清乾淨)

【純讀檔／Grep（未經 shell）】
Read: docs/04_planning/AutoSDD_improving_104.md、AutoClaude/CLAUDE.md、AutoClaude/scripts/example_playbook.yaml、AutoClaude/docker-compose.ci.yml、
      AutoClaude/config.yaml、AutoClaude/tests/conftest.py、AutoClaude/autoclaude/{main.py, core/kernel.py, core/_token_observer.py,
      core/services/auto_resume.py, utils/config.py, utils/token_tracker.py, execution/evaluator.py, execution/steps_orchestrator/_impl.py,
      infra/adapters/{pty_executor.py, shell_evaluator.py}, infra/repositories/{factory.py, file_state_repository.py, pg_state_repository.py},
      plugins/token_guard/{watcher.py, thresholds.py}}、tools/tests/test_platform_neutral_paths.py、AutoClaude/tests/integration/test_dry_run_kernel_path.py
Grep: AUTOCLAUDE_TEST_PG_DSN / scheduled_resume_at / auto_compact_interval / extract_context_pct / TokenObserver|on_event=|TOKEN_PCT /
      enable_kernel_brain / PtyExecutor|SdkExecutorAdapter / steps_orchestrator|StepsOrchestrator / PlaybookRunner\(|run_steps_impl|_run_steps /
      seconds_until_resume / _NAIVE_TS_PERSIST_DEBT
```

### §5.4 本路 `honest_gaps`（逐字保全）

```text
誠實劃界——以下是我**沒有**驗證的，不要當成已驗證：

1. **完全沒有跑成一次真正的 Playbook。** S1-01 的 pty hang 把端到端驗證整條擋死了，所以「AutoClaude 當舵手」這件事本回合**一次都沒有被真的執行過**。下面所有關於執行語意的結論，來源都是讀程式碼 + 針對單一函式/單一 repository 的隔離探針，不是整場 run。

2. **S1-02 的證據停在 repository API 與消費函式兩層，沒有走完整條 halt→resume 迴圈。** 我實測的是「`PgStateRepository.schedule_resume()` 產出的字串，餵給 `auto_resume.seconds_until_resume()` 會回 0.0」。至於 production 的 halt 路徑是否**每次**都經由 `schedule_resume()` 落這個欄位（`plugins/checkpoint/_token_halt.py` 與 `execution/halt_handler.py` 這條線我只讀了 grep 命中行、沒有逐行追完），我沒有證。所以嚴格說：缺陷本身（aware 字串 → 0.0）已坐實，但「production 每一次 token-halt 都會踩到」是我的推論，不是量測。

3. **wexpect hang 的普遍性未知。** 我只在這一台機器、以 `claude.exe` 這一個載具、量了一次 60s。根 CLAUDE.md 記載的另三次（180/180/45s）不是我跑的。這個 hang 是否與 claude CLI 版本／wexpect 4.0.0／本機 console 狀態有關，我沒有做對照組（例如換一支普通 .exe 當 command 試 spawn），所以不能斷言「Windows 上一定會卡」。

4. **SDK 後端零驗證。** `claude_agent_sdk` 沒裝，所以 S1-01 提的修法 (a) 我完全沒試過，不知道裝了以後會不會有第二個坑。

5. **「15 支測試在 setup 硬炸」這個數字我沒有復現。** 那是 R80 掃描 S3-06 的原始說法；今天守衛已在收集前擋下（rc=4），所以那 15 支**現在炸不起來**了，我無從數。我只驗了「守衛會擋」與「正確 DSN 下 76 passed/2 skipped」。

6. **沒有跑 AutoClaude 全測試套件、沒有跑任何本機閘門（local_ci_gate / pre-push / act）。** 本回合是唯讀勘查，只跑了 2 個 contract 測試檔。所以我不能對「repo 現在是不是綠的」發表任何意見。

7. **S1-06（auto_compact_interval 死碼）的可達性論證來自 grep + import 清單，不是執行期追蹤。** 我確認了 `PlaybookRunner(` 在 `autoclaude/` 內零命中、`main.py` 不 import 它；但 `tests/` 裡有沒有別的入口、或有沒有透過 getattr／動態載入的路徑，我沒有窮盡。結論方向我有信心，但「絕對死碼」這個強度我不該宣稱。

8. **PG 那顆 DB 的 schema 我只看了 `checkpoints` 一張表的欄位。** 其餘 45 張表只看了名字。`goal_tasks`／`playbook_runs` 的 FK 語意、以及 db_only 模式下 playbook 本身怎麼進 DB（`yaml 僅供匯入`是什麼流程），我沒查。

9. **我改動了 PG 的資料（存了一筆探針 checkpoint 再刪掉）。** 這超出「唯讀」的字面，但限於我自己建立的 `playbook_id='6c86756b2a1ce144'` 兩列，已用 count=0 驗證清乾淨。**repo 內檔案一個字都沒改。**

10. **`.env` 我沒有讀**（含機密）。S1-10 關於 env 注入的結論來自 config.yaml 的註解與 main.py/factory.py 的 os.environ 讀取點，我不知道 `.env` 裡實際有沒有 `MINIMAX_API_KEY` 或 `AUTOCLAUDE_DB_DSN`。
```

## §B 護欄層行數棘輪 R81 重釘的逐檔清單與逐項必要性辯護

本節是 `tools/tests/test_adr_xplat001_c1c2_lock.py::_GUARD_LINES_REPIN_LOG` 的 R81 那一列
依**款(9)** 指名的逐檔清單的家（同 `CrossPlatform_R80_Scan_Findings.md` §B／§B-2／§B-3 的
體例：同一件事只有一個家）。由收尾者在 11 個包全部停工後的單人窗口一次重釘 ⇒ rc 可歸因。
本節記的是**第一次**重釘（+2369）；本輪第二次重釘（Architect 複審收斂包）的逐檔清單見 §B-2、
第四次（SD 複審收斂後的收尾包）見 §B-3。
累積淨額 <!-- guard-total:R81 --> 65390 → 68423（**+3033**），五次重釘：**+2369**（本節）／**+149**（§B-2）／**+42**（QA 複審三筆 blocking 的收斂包，逐檔＝`test_doc_loc_baseline_freshness_r60.py` +23 與 `test_adr_xplat001_c1c2_lock.py` +19；後者即該次重釘自身的稽核痕跡。🔴 該次**不是**單人窗口取得，SA／SD 同時在唯讀審查同一棵樹）／**+443**（§B-3）／**+30**（§B-4，pre-push 攔下後的補包）。

🔴 **本輪是 `[非淨減法輪]`，據實標記、不用「淨額仍下降」把成長蓋過去**（R80 判例）。
成長**全部**落在護欄層（測試），而**生產碼是淨減的**——hook payload 手抄本收斂
（7 支各自帶一份 → 共用層 `tools/lib/platform_utils.py`）在生產側淨 −39 行，其中
收尾者本人刪掉 `context_budget_guard.py` 的 21 行手抄本。護欄層之所以只增不減，是因為
本輪新開的判準面（額度節流、跨平台 5 類新危害、Q4 宣稱對帳、腳本介面等價）此前
**一個觀測者都沒有**，沒有等量的舊判準可以退場去換。

| 檔 | 舊 → 新 | 增量 | 這些行買到了什麼（必要性辯護） |
|---|---|---|---|
| `test_context_budget_guard.py` | 2282 → 3085 | +803 | 額度節流的 **80/95 兩道門**與其分支判定的成對注入。此前守衛只認 context 水位，而額度是另一個分母（撞額度那刻水位可能僅 ~18%，每一道 context 守衛都會放行）⇒ 這一面先前零判準 |
| `test_platform_neutral_paths.py` | 5033 → 5675 | +642 | 鐵律三新登記危害類的門：`$env:TEMP`／`TMP` 站點級守衛、`Get-Command` 裸解析只准住 SSOT、大小寫敏感度自陳的**證偽探針**（`TestIronLaw3NoMechanismClaimsAreFalsifiable`——治的是「自陳沒人守」這種**低報分子**，它與過報同樣讓治理數字失真） |
| `test_doc_loc_baseline_freshness_r60.py` | 5927 → 6288 | +361 | Q4 的**首道宣稱對帳機械物**。本輪重跑失誤分群後最大桶是「宣稱先於查證」，而那一桶此前完全沒有機械物——它發生在 inline 指令字串與 rc 讀數上，永遠不會變成 repo 裡的檔案，所有靜態掃描器結構上看不到 |
| `test_bash32_compat.py` | 609 → 819 | +210 | macOS 內建 bash 3.2 的語法面判準（關聯陣列／`declare -A`／`readarray` 等 4.x-only 構造）。此前只有「腳本能不能解析」沒有「在 3.2 能不能解析」，而 macOS 正是本 repo 的第二平台 |
| `test_check_script_parity.py` | 1977 → 2111 | +134 | `.sh`／`.ps1` 雙載具的**行為等價**判準（旗標集、rc 語意、`--help` 出口），落在新共用層 `tools/lib/script_interface_parity.py` 上。此前兩側只有「都存在」沒有「行為一致」 |
| `test_dev_start.py` | 6686 → 6774 | +88 | 隨 dev_start 平台分支新增的對應注入 |
| `test_pre_commit_dispatcher_sigpipe.py` | 498 → 581 | +83 | **hook payload SSOT 的回歸鎖**（`TestHookPayloadSingleHome`）：7 份手抄本實測已漂移成 3 種行為，其中阻斷級 `enforce_docs_path.py` 餵 `[1,2,3]`／`null` 時 rc=1 AttributeError＝守衛還在、判定沒產出。本鎖同時擋住「再長出第二個家」（掃 `sys.stdin` 自讀）。收尾者在此再 +5 行：移除 `context_budget_guard.py` 的具名排除並寫明到期理由 |
| `_platform_helpers.py` | 539 → 549 | +10 | 上述跨平台判準共用的測試輔助 |
| `test_archive_defect_log.py` | 3786 → 3791 | +5 | 隨帳本歸檔（`archive_64`）新增的守恆判準 |
| `test_smoke_ci_sync.py` | 1355 → 1359 | +4 | smoke 與 CI 對應面的同步判準微調 |
| `test_workflow_permission_concurrency_lock.py` | 1357 → 1360 | +3 | workflow 權限面的並行鎖判準微調 |
| `test_find_git_bash_parity.py` | 1228 → 1230 | +2 | `Find-GitBash` SSOT 消費者面的微調 |

🔴 **本輪未刪任何行換取餘裕、未調高任何門檻、未放寬任何棘輪、未動漂移容忍值。**
唯一往**下**釘的是 `OVERSIZE_ROW_EXCESS_CEILING`（138938 → 138936，−2），來源見下面 §C。

## §B-2 護欄層行數棘輪 R81 **第二次**重釘（Architect 複審收斂包）的逐檔清單

同 §B 的體例（同一件事只有一個家）。由收斂者在**單人窗口**（無任何 agent 在跑 ⇒ rc 可歸因）
一次重釘。淨額 **67759 → 67908（+149）**，累積總量與算術見 §B 那一行帶標記的宣稱。

🔴 **本行刻意不複述那個標記的字面**（R81 QA 收斂包實測補記）：該標記是**被機械判讀**的，
複述一次就多出一個受判的站點——而本節記的是**史料淨額**（67759 → 67908），與現行累積總量
天生不同 ⇒ 那個站點必然對不上帳。本行原本逐字帶著該標記，第三次重釘後當場以 `[總量不符]`
轉紅（訊息指名本行行號）。這與 R79／R80 已判過的「在被機械判讀的面上，解釋 X 的字面
等於又用了一次 X」是同一個形態，只是這次的載體是史料段落而不是訂正註記。

🔴 **本節同樣是 `[非淨減法輪]`，而且沒有生產碼淨減可以拿來抵**（§B 那一段有，本節沒有）。

| 檔 | 舊 → 新 | 增量 | 這些行買到了什麼（必要性辯護） |
|---|---|---|---|
| `test_context_budget_guard.py` | 3085 → 3215 | +130 | B1／B2 兩筆 blocking 的回歸鎖，各 2~4 條、全部成對（控制組 ＋ 注入組）。**B1**：額度節流閘在「快取過期／不存在」時對任意規模的扇出**全數放行**（探針實測：過期 600s／額度 99% ⇒ 42 次 `Agent` 派發放行 42、擋下 0），此前這條路徑上只有正向控制組，沒有任何一條在問「量不到的時候到底放行了多少」。**B2**：快取檔案契約（檔名＋schema）有三份互不相關的字面複本，而**生產綁定零覆蓋**——既有快取測試全部傳明確 `path` 給 `read_quota()`，結構上量不到「hook 讀的正好是 meter 寫的那一支」 |
| `test_adr_xplat001_c1c2_lock.py` | 4545 → 4564 | +19 | 本次重釘自身的稽核痕跡（`_GUARD_LINES_REPIN_LOG` 新列），款(9) 要求的登記手續 |

**為何沒有等量的舊判準可以退場**：這兩條守的性質此前一個觀測者都沒有（理由同上格）。
新增的 6 條裡**刻意保留一條反向**（`test_a_dead_endpoint_with_no_evidence_still_allows`：
真的量不到、又沒有任何撞線證據時**仍然放行**）——只鎖單向會讓下一個人用「一律 fail-closed」
滿足它，而那正是 L4 當初被否決的形態（斷網與額度滿了外觀完全相同且靜默）。

**同輪另一個治理面的變動（不進本表，度量面不同）**：`.claude/hooks/` 此前**不在任何 LOC 預算
的掃描面內**，本次納入 `check_loc_budget.py`——4 支走根層 tier（`guardrail_cli<=750`）、
`context_budget_guard.py`（1634 raw）走 `SPECIAL_FILES` 的 shrink-only 棘輪，門檻＝納管當下
的實際行數。🔴 **誠實：這件事當下不會讓任何東西變小**，它買到的是「下一個人再往裡面塞就會紅」。

## §B-3 護欄層行數棘輪 R81 **第四次**（收尾包）重釘的逐檔清單

同 §B／§B-2 的體例（同一件事只有一個家）。由收尾者在**單人窗口**（四方複審 17 筆 blocking
收斂到最後一筆時，所有包已停工，樹上只有一人 ⇒ rc 可歸因）一次重釘。
淨額 **67950 → 68393（+443）**，累積總量與四段算術見 §B 那一行帶標記的宣稱
（🔴 本節同樣不複述那個標記的字面，理由見 §B-2 的第一段紅字）。

🔴 **本節是 `[非淨減法輪]`。**

| 檔 | 舊 → 新 | 增量 | 這些行買到了什麼（必要性辯護） |
|---|---|---|---|
| `test_context_budget_guard.py` | 3215 → 3631 | +416 | SD 複審四筆 blocking 的回歸鎖。**取數器的失效形態逐一具名**（憑證讀不到／HTTP 狀態碼／連線失敗／200 但讀不出額度桶）——此前四種全部塌成同一句「量不到」，而「量不到」正是**放行**的理由 ⇒ 一個壞掉的取數器與一個健康的低用量帳戶外觀完全相同。另含：降級必須**出聲**且同一來源不重複喊、節流訊息與降級訊息不得互相冒充、扇出帳本不得含 session id 且壞掉時讀成 0 而非讀成封鎖、TTL 更新槽十六路並行只准一個贏、節流帶訊息要說出這條帶還會持續多久 |
| `test_adr_xplat001_c1c2_lock.py` | 4583 → 4605 | +22 | 本次重釘自身的稽核痕跡（`_GUARD_LINES_REPIN_LOG` 新列），款(9) 要求的登記手續 |
| `test_platform_neutral_paths.py` | 5675 → 5678 | +3 | `sorted(Path)` 餵進 digest 時必須帶平台中立的鍵（`XPL-S1-06` 的落地物）判準微調 |
| `test_doc_loc_baseline_freshness_r60.py` | 6311 → 6313 | +2 | 幽靈路徑判準掃描面的微調 |

🔴 **生產側是「搬家」不是淨減——這一格是收尾者現查後對交棒稿的訂正。**
額度撞線判讀整個主題自 `.claude/hooks/context_budget_guard.py` 搬進
`tools/lib/quota_limits.py`，該 hook 由納管當下的 1634 raw 行降到 **1451**（−183）；
但接收端自己是 **341 行的新檔** ⇒ 生產側合計仍為正。把 −183 單獨引用成「生產碼淨減」
會讓 §B 那一段真正的 −39（hook payload 手抄本收斂）被一個假的同向數字放大。

**同一次的棘輪下釘（真的往下走的那一筆）**：`AutoClaude/tools/check_loc_budget.py` 的
`SPECIAL_FILES` 對該 hook 的 raw-line 門檻由 **1634 下釘到 1451**。R69 P3 的慣例是
「門檻＝納管當下實際行數、零餘裕設計」，合法縮小後不下修，那 183 行餘裕就是日後
無聲加回去的破口——該棘輪自己的紅燈訊息逐字寫著這句話。下釘後餘裕 0，落在
`SPECIAL_WARN_MARGIN` 的**非阻塞**預警帶內（`check_loc_budget.py` 實測 rc=0、violations=0），
這正是該設計預期的狀態。

## §B-4 護欄層行數棘輪 R81 **第五次**（pre-push 攔下後的補包）重釘的逐檔清單

同 §B／§B-2／§B-3 的體例（同一件事只有一個家）。**單人窗口**：commit 已落地、所有包停工，
樹上只有補包者 ⇒ rc 可歸因。淨額 **68393 → 68423（+30）**，累積總量與五段算術見 §B
那一行帶標記的宣稱（🔴 本節同樣不複述那個標記的字面，理由見 §B-2 的第一段紅字）。

🔴 **本節是 `[非淨減法輪]`。**

| 檔 | 舊 → 新 | 增量 | 這些行買到了什麼（必要性辯護） |
|---|---|---|---|
| `test_adr_xplat001_c1c2_lock.py` | 4605 → 4623 | +18 | 本次重釘自身的稽核痕跡（`_GUARD_LINES_REPIN_LOG` 新列），款(9) 要求的登記手續。與 §B-3 那一列的 +22 同型 |
| `test_windowsapps_guard_cross_consistency.py` | 2184 → 2196 | +12 | `_ZERO_GUARD_BARE_PY_SITES` 新登記 `tools/lib/script_interface_parity.py`：該檔的 `_EXTERNAL_BINS` 是「兩平台同名外部執行檔」的**比對用白名單資料**（`python`／`python3` 與 act／docker／ruff 並列），本檔一次都不 spawn 它們 ⇒ 分診為「非呼叫：資料字串」，與同表 `check_wrapper_thinness.py` 同型 |

### 🔴 這一包的存在本身是判例：**commit 這個動作會改變掃描面**

上面第二列之所以到 pre-push 才紅，不是因為收尾漏跑閘門——收尾**跑了而且是綠的**。
`script_interface_parity.py` 在收尾當下還是 untracked，而該鎖的掃描面只看 git-tracked ⇒
它在 `git commit` 的那一刻才首次進入射程。同一個 commit 也讓兩支新 `tools/lib/*.py`
（`quota_ledger.py`／`quota_limits.py`）落入 `test_ci_paths_cover_root_consumers.py` 的射程，
形態完全一樣。

在本 repo 這已是**第三次**：R78 收輪一次、R79 的 `tools/probe/xplat_injection_matrix.py` 一次
（該筆的註記逐字寫著「已是第二次」）、本筆。前兩次都只把個案登記掉，**沒有人動「收尾在
commit 前跑」這個順序**——所以它必然再來。可能的處置（本輪不做，交棒）：收尾閘門在
commit 之後、push 之前再跑一次；或把「有新 untracked 生產檔」本身當成一個要出聲的狀態。

**同一輪內第二次被同一支判準攔下**（`test_ci_paths_cover_root_consumers.py`）也值得記：
本輪稍早的收尾包已替四支新 `tools/lib/*.py` 補過 CI paths，之後又新增兩支就沒跟上。
補列這個動作只覆蓋當下已存在的檔，**「這一輪已經補過了」不是可以少查一次的理由**。

## §C 收尾者對 `DEF-101-870` 一列的措辭訂正（兩處，語意不變）

R81 的包在該列追加附記時寫下兩個字面，各自踩到一道與該列**主題無關**的鎖：

1. **`改派：` 抓不到。** `check_defect_log_crossref.py::_handover_rounds()` 只認**承接語境**的
   五種樣式（`承接輪次／承接者`、`R… 承接`、`列 R…`、`backlog R…`、`交棒／移交／交由 R…`），
   `改派：` 不在其中 ⇒ 該列會變成沒有承接者的孤兒 backlog。**訂正**：改寫成 `承接輪次：R82`。
   這不是繞過判準，是改用判準認得的那個詞——語意本來就是「承接」。
2. **「凍結版」使本列誤入 ADR-XPLAT-001 §4.3.1。** `falls_into_adr_431()` 的判準是「分流欄
   **或**狀態欄同時出現 `凍結版／凍結基線` 與 `不回補／wontfix`」。該列原本用「凍結版」
   三字修飾**目錄名慣例**（三段版號 `\d+\.\d+` 漏抓 `v1.0.1` 形態），與 Copy-on-Evolve
   回補政策毫無關係，卻因為同一格裡另有 `wontfix` 而湊齊兩組字樣，被 C1／C2 硬擋抓住。
   **訂正**：改成「各版目錄名慣例」（語意等同，凍結版目錄名本就是兩段）。

**為何是訂正敘述而不是補 C1／C2**：本列與 §4.3 無關，為它在 `ONBOARDING.md` §9 虛構一列
就是幽靈登記。這一步有直接判例——`DEF-101-552` 當年實查該缺陷在 v0.01~v0.29 全部零命中，
結論逐字是「**不存在凍結版落差**，§4.3 對它是 N/A 而非豁免，§9 不該為它虛構一列；該列敘述
已據實訂正，因此不再落入 §4.3.1」。本次走同一條路。

🔴 **只改本輪自己寫下的字，不動歷史原文**：兩處都是 R81 追加的附記。該列更早的
「或明文 wontfix」（R77 原文）**刻意留著沒動**——動它就違反帳本的原文逐字保全，而且
只要「凍結版」不在，兩組字樣就湊不齊，本來也不需要動。

**代價與帳**：訂正後該列淨 **−2 bytes**，故 `OVERSIZE_ROW_EXCESS_CEILING` 由 138938 往下釘到
138936（實測值直接填入；該常數受 `test_the_real_ledger_baselines_are_exact_not_padded`
要求**逐字等於**實測，不是上界，留餘裕就是日後無聲加回去的破口）。**列上刻意不留指針**：
再犯時 C1／C2 硬擋會逐字指名本列，那道鎖本身就是這件事的守衛，列上再寫一份就是第二個家。

## §8 姊妹檔對照表（`DEF-101-587` 體例）

`docs/06_quality/` 的具名治理文件受體積守門（fail 262,144 bytes ／ warn 245,760 bytes，
上限來源＝Read 工具單次讀取上限，與缺陷帳本是同一條物理界線）。R81 第一批的輸出量
超過單檔容量（第一版實測 253,373 bytes，已越 warn 線），故拆成**三份姊妹檔**，
三份**都**登記進 `tools/lib/governance_docs.py` 的 `_GOVERNANCE_DOCS`。
本檔＝`docs/06_quality/CrossPlatform_R81_Scan_Findings.md`。

| 檔 | 承載 |
|---|---|
| `docs/06_quality/CrossPlatform_R81_Scan_Findings.md`（入口） | §0 誠實劃界／§1 九路全景／§2 scan:xplat 7 筆／§3 scan:subtraction 8 筆／§4 scan:skipped 12 筆／§5 scan:autoclaude-helm 10 筆 |
| `docs/06_quality/CrossPlatform_R81_Quota_Review.md` | §2 research:quota 12 筆／§3 ADR-XPLAT-005 的核心決策・實作步驟・開放問題／SA 與 SD 兩份 verdict 的逐筆 blocking 與 non-blocking |
| `docs/06_quality/CrossPlatform_R81_Ledger_Triage.md` | scan:ledger 的 34 筆未結列四類分流（A 已修好只差狀態欄／B 前提不成立／C 本輪做得完／D 本輪做不完須改派） |
| `docs/04_planning/ADR/ADR-XPLAT-005-quota-aware-throttling-and-fanout-resume.md` | ADR 全文（狀態 `Proposed`；SA 給 REJECT、SD 給 APPROVE_WITH_CONDITIONS，11 筆 blocking 未收斂前不得視為已核准） |

## §9 這三份檔為何屬於「具名治理文件」

兩項義務同時成立，與 `CrossPlatform_R80_Scan_Findings.md` 的資格相同：

1. **體積守門**——複審者要判「R81 還有哪些缺口開著」就得讀完它，所以它承擔與缺陷帳本
   同等的可讀性義務；
2. **指針稽核**——它逐筆寫出「某發現的座標在某檔某行」的宣稱，而那些宣稱會過期。

---

## §10 act 憑證（Linux 剖面實跑讀數）

🔴 **本節的存在理由**：QA 複審質疑「act 實測 Linux 剖面 POSIX-NATIVE-ONLY = 0」這句話
**在 repo 內對不上帳**——它當時只活在某個 agent 的交件回報裡，而交件回報不是 repo 的一部分，
下一輪查不到。這與本 repo 反覆判過的「一個數字只要住進人會讀的散文、就必須有東西看得到它」
同型，只是這一次連散文都沒有。本節把關鍵讀數落進 repo，讓它變成可稽核的。

**取證方式**：舵手親跑 act（ubuntu 容器），log 落在 session scratchpad（85,141 bytes／490 行）。
本節數字由收斂包**自行從 log 重抽一次**（`SKIPPED [n]` 逐行加總、關鍵字計次），
不採信任何轉述讀數——重抽的過程當場改正了一筆單位混淆，見下方 ⚠️。

| 讀數 | 值 | 來源行 |
|---|---|---|
| pytest 結果 | `3989 passed, 236 skipped in 58.00s` | log 第 411 行 |
| pytest rc | `AUTOCLAUDE-TEST-PYTEST-RC=0` | log 第 412 行 |
| job 結論 | `Job succeeded` | log 第 489 行 |
| skip 普查 | `AutoClaude/tests@linux+pg+solo 共 236 支：platform=53／tool-absence=0／env-disabled=15／structural-pair=0／debt=4／untagged=164／欠債型 183 支（目標 0）` | log 第 413 行 |
| 普查警告 | `skip census: this platform profile has no measured ceiling yet (advisory)` | log 第 417 行 |

**平台專屬 skip 的三個方向**（收斂包自行加總，非轉述）：

| 標籤 | `SKIPPED [n]` 站點行數 | 加總支數 | 全 log 出現次數 |
|---|---|---|---|
| `WINDOWS-NATIVE-ONLY` | 36 | **53** | 37 |
| `POSIX-NATIVE-ONLY` | 0 | **0** | 0 |
| `MAC-NATIVE-ONLY` | 0 | **0** | 0 |

⚠️ **重抽當場改正的單位混淆**：轉述給收斂包的讀數是「`WINDOWS-NATIVE-ONLY = 36`」，
而 log 自己在第 184 行印的是「**53** 個 Windows 專屬測試」。兩個數字都對，量的是不同的東西：
**36 是 `SKIPPED [n]` 的站點行數、53 是那些站點加總的測試支數**（pytest 的 skip 摘要按位置分組，
一個站點可帶多支）。⇒ 只寫一個數字而不寫單位，下一輪一定會有人拿它跟另一個單位的數字對帳。

### 🔴 這份憑證證明不了什麼（誠實劃界，比上表重要）

- **`MAC-NATIVE-ONLY = 0` 不代表 mac 有覆蓋。** 它只說明那棵樹裡**沒有 mac-only 標籤的測試**，
  而 mac 剖面本輪**零覆蓋**（全部量測都在 Windows 11 真機取得）。這兩句話在螢幕上長得很像。
- **`POSIX-NATIVE-ONLY = 0` 是「零命中」，不是「零風險」。** act 跑的是 ubuntu 容器＝GNU coreutils；
  mac 是 BSD coreutils，那一整類差異結構上不在這一跑的射程內。
- **`Job succeeded` 不等於 CI 綠。** act 是本機容器，環境與 GitHub Actions runner 不同；
  本輪雲端結論另查（見交棒書 §0-2）。
- **`untagged=164` 是本輪最大的一塊，且它不是「已知安全」**——它是「還沒有人去分類」。
