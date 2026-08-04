"""CI paths 覆蓋根層消費檔 meta contract — DEF-101-042 治本鎖 / DEF-101-068(a) 擴充（S6）.

WHY（Rule 9 / Rule 12 fail-loud）：測試目錄的 contract test 消費 monorepo
根層檔案時，其 CI 載體的 paths 過濾必須包含該根層檔，否則「只改根層消費檔」的
變更下回歸鎖恰好不跑（假綠盲區）。此同構缺陷已三度出現於 aisdlc-sdd-ci
（DEF-101-037 → DEF-101-042 → 複審抓 sdd_hook_router.py 殘漏），人工盤點 paths
已被實證不可靠——本鎖把「paths 與消費點同步」升級為機械斷言，永久終結打地鼠：
未來任何測試新增根層消費點而漏補 paths，本測試即紅。

S6（第六輪複審 DEF-101-068(a)）：先前本鎖只讀 aisdlc-sdd-ci.yml 一份、只掃
AISDLC_SDD/scripts/tests/ 一個目錄，對 windows-compat-ci.yml／macos-compat-ci.yml
與其實際執行的 tools/tests/ 完全零機械保護——這正是先前一輪 windows-compat-ci.yml
漏補 tools/check_ntfs_paths.py 能夠逃過檢測的結構性根因。現擴充為「workflow ↔
其實際執行的測試目錄」對照表，逐一參數化驗證：

  - aisdlc-sdd-ci.yml      ↔ AISDLC_SDD/scripts/tests/（`python -m pytest scripts/tests/`）
  - windows-compat-ci.yml  ↔ tools/tests/（`unittest discover -s tools/tests`）
  - macos-compat-ci.yml    ↔ tools/tests/（`unittest discover -s tools/tests`）

做法：正則掃描對應目錄所有 test_*.py 源碼的根層消費慣用法——
  ``os.path.join(_monorepo_root(), "a", "b")`` / ``_monorepo_root() / "a" / "b"``
（AISDLC_SDD/scripts/tests/ 慣用法）與
  ``os.path.join(REPO_ROOT, "a", "b")`` / ``REPO_ROOT / "a" / "b"``
（tools/tests/ 慣用法，該目錄下 ``REPO_ROOT = Path(__file__).resolve().parents[2]``
剛好等於 monorepo 根）——重組 repo 相對路徑；凡指向磁碟上存在的檔案，一律斷言被
對應 workflow 的 push＋pull_request paths 覆蓋（fnmatch glob 語意）。
**R67 round 2 訂正**：本段原文為「凡指向磁碟上存在**且不在 AISDLC_SDD/ 下**（該前綴由
``AISDLC_SDD/**`` 天然覆蓋）的檔案」，那句豁免的前提**只對 aisdlc-sdd-ci.yml 成立**
（實查：它的 paths 確有 ``AISDLC_SDD/**`` 一條），對 macos／windows-compat-ci.yml
**不成立**——那兩支的 AISDLC_SDD 白名單只有 ``scripts/**``／``v*/tools/**``／
``v*/.claude/**``／``v0.01/requirements-ci.txt`` 四條。於是「AISDLC_SDD/ 下、但不在這四條
之內」的消費檔會被本鎖**主動
丟棄**而永遠測不到，`AISDLC_SDD/conftest.py` 正是活體案例（掃描器**看得見**它、卻在最後
一步被前綴過濾器扔掉）。豁免已拆除，改為逐 workflow 用它自己的 paths 判定。另附兩道防呆：push/PR
清單對稱鎖（防單側漏補，三份 workflow 皆驗）、已知消費檔必被掃出（防正則退化
令本鎖形同虛設）。

S26（第八輪複審 R6，Architect 親自實測 fnmatch 逐一比對抓到）：`_scan_dir_for_root_paths()`
先前只認得 `os.path.join(REPO_ROOT, "a", "b")` / `REPO_ROOT / "a" / "b"` 這種「引用固定
路徑字串」的慣用法，完全沒有涵蓋 `tools/tests/` 三支新測試檔
（test_check_hooks_liveness.py／test_check_defect_log_crossref.py／
test_check_wrapper_thinness.py）皆使用的 `import check_hooks_liveness as m`（搭配
`sys.path.insert(0, str(Path(__file__).resolve().parents[1]))` 把待測目錄的父目錄
塞進 sys.path）這種「直接 import 根層同儕模組」慣用法——導致
windows-compat-ci.yml／macos-compat-ci.yml 皆漏收 tools/check_hooks_liveness.py／
check_defect_log_crossref.py／check_wrapper_thinness.py／_stdio_utf8.py 四支模組
（後者透過前三者遞移 import 被消費）卻毫無機械訊號。新增 `_scan_import_consumed_paths()`：
以 BFS 從 `directory` 內的 test_*.py 出發，掃描其 `import <module>`／
`import <module> as <alias>` 頂層陳述式，將 `module` 解析為「該來源檔自身所在目錄」
下的 `<module>.py`（對齊本 repo `sys.path.insert(0, parents[1])` 慣例），並對新發現的
根層 .py 檔遞迴重複同一掃描（fixed point，關閉「測試只 import A，A 內部又 import B」
的第二層盲區，如 check_hooks_liveness.py → _stdio_utf8.py）。與既有
`os.path.join`/`REPO_ROOT /` 正則並行執行、聯集後再套用磁碟存在性過濾器，兩種偵測
機制互不排斥。

R50（第 50 輪 Mac/Windows 相容性四方複審）：`tools/tests/test_windowsapps_guard_cross_consistency.py`
用 `_tracked_files(pattern)`（`git ls-files -- pattern`）對整個 repo 做 glob 動態掃描
（例：`_tracked_files("*.ps1")` 取得「當下全部 git 追蹤的 .ps1 檔」），而非引用某個
固定路徑字面值或 import 陳述式——這是與盲區 A（`_scan_dir_for_root_paths()`／
`_scan_import_consumed_paths()` 解析器猜測範圍不夠）、盲區 B（`_KNOWN_SUBPROCESS_ONLY_CONSUMERS`
登記的執行期子行程消費）並列的第三種消費形態（盲區 C），且先前無任何機械訊號涵蓋
——連盲區 B 那種手動登記清單兜底都沒有，四方複審實測 10/10 全綠卻未攔下該檔案
新增 6 支 .ps1 消費檔（呼叫 python 未經 WindowsApps guard SSOT）未被
macos-compat-ci.yml paths 覆蓋的缺口。比照盲區 B 手法：新增 `_KNOWN_GLOB_SCAN_CONSUMERS`
顯式登記「哪個測試檔＋掃描哪個 glob pattern」，斷言該 pattern 字面值仍存在於來源碼中
（防登記腐化），再對其*動態即時*執行 `git ls-files -- pattern` 取得的真實結果
（非寫死清單，隨檔案新增/刪除自動同步，不會像盲區 B 清單一樣需要人工同步維護內容）
逐一機械斷言被對應 workflow 的 push/pull_request paths 覆蓋。刻意不比照盲區 A
擴充成通用正則掃描器：該檔另一處 `_tracked_files("*.py")` 語意上會匹配整個
`AutoClaude/`（500+ 檔）等大範圍前綴，若也納入通用掃描器會逼 CI paths 逐一列舉
數百檔或改用會讓每次原始碼異動都觸發本 workflow 的過寬萬用字元，這既不實際也偏離
本輪複審實測揪出的具體缺口（.ps1 6 支檔案）；`_KNOWN_GLOB_SCAN_CONSUMERS` 僅登記
已被實測證實有真實覆蓋缺口的 `*.ps1` 一項，`*.py` 的更廣語意留待未來若有實測缺口
再議（同盲區 B 手動登記僅涵蓋已知具體案例的既有慣例）。

S12（第七輪複審 DEF-101-068(a) 續；掃描面現況已由 R56 訂正，見下）：四份 workflow
中 root-infra-ci.yml 是唯一「刻意不設 paths 過濾」者（見該檔頭註解：NTFS 敵意檔名閘
需對任何路徑生效，paths 白名單必留盲區）——硬套上方「消費檔 ⊆ paths」同一套正則毫無
意義（沒有 paths 可比對）。root-infra-ci.yml 真正的同構風險改頭換面成另一種盲區：
它的 py_compile 步驟只用 ``find tools ...`` 掃描根層 ``tools/`` 一個目錄；若日後在
monorepo 根新增另一個含 .py 腳本的目錄（如 ``scripts/``、``bin/``），該目錄會完全
逃過 root-infra-ci 的 py_compile 守門而不自知——這正是 DEF-101-042／DEF-101-068(a)
那種「消費者存在但守門忘了看它」的同一類缺陷，只是發生在「掃描根目錄清單」而非
「觸發 paths 清單」上。
**R56 修正（文字與現況同步，零邏輯變動）**：本段原文為「bash -n／py_compile 兩個
步驟只用 ``find tools ...`` 掃描根層 ``tools/`` 一個目錄」——R56 已把 bash -n 擴為
``git ls-files -z -- '*.sh' …`` 全庫 tracked ``*.sh``＋三處 git-hooks 目錄（見該
workflow 第 1 道，實測 n=174），故該宣稱對 bash -n 已不成立、僅對 py_compile 仍成立
（這種「半真」比全錯更難察覺，故顯式訂正）。
故本節另立兩道專屬 root-infra-ci.yml 的機械鎖（見檔案下方）：
  1. 鎖死「刻意不設 paths」的設計決策本身，防止日後被誤「補全」paths 而
     重新引入假綠盲區；
  2. 掃描 git 追蹤的全部 .sh／.py 檔，斷言不在 AutoClaude/、AISDLC_SDD/、
     .claude/ 之外、也不在 tools/ 之內的「無主根層腳本」為空集——一旦出現即
     代表有新目錄逃過 root-infra-ci 的守門。**豁免依據（R56 訂正）**：``.sh``
     已由 root-infra-ci 第 1 道全庫 bash -n 覆蓋；``.py`` 之豁免依據為 AutoClaude
     ruff／pytest 與 AISDLC_SDD ci-gate。**勿再援引「子專案各自已有獨立 CI／hook
     把關」作為 ``.sh`` 的豁免理由**——R56 實查證偽：``AutoClaude/tools/git-hooks/
     pre-commit`` 只有 ruff／LOC／CLAUDE.md／EOL 四道、``AISDLC_SDD/.githooks/
     pre-push`` 只轉呼 ci-gate.sh，兩者皆無 ``bash -n``；這正是 R56 把 bash -n
     擴為全庫、並同步訂正 ``tools/git-hooks/pre-commit:170`` 原註解（「子專案腳本
     由各自 hook 把關」→「委派鏈是空的」）的理由。

R52（第 52 輪 Mac/Windows 相容性四方複審 Architect/SA/SD 交叉發現）：
`tools/tests/test_dev_start.py` 的 `TestNightlyHeartbeatFilenameContract` 用
`self._REPO / "AutoClaude" / "tools" / "run_local_nightly.sh"`（class 屬性
`self._REPO`，非字面 token `REPO_ROOT`／`_monorepo_root()`）讀取原始碼——與
盲區 B／C 同屬「掃描器方法論邊界」而非「解析器猜測範圍不夠」，`_JOIN_RE`／
`_SLASH_RE` 對此結構上零訊號，導致 windows-compat-ci.yml 漏列
`AutoClaude/tools/run_local_nightly.sh` 逃過本鎖（11 passed 未攔截）。第四種
消費形態（盲區 D），比照盲區 B／C 手法新增 `_KNOWN_LITERAL_PATH_CONSUMERS`
顯式登記「檔案＋消費它的來源檔」並機械斷言覆蓋 workflow paths。

R53（第 53 輪 Mac/Windows 相容性四方複審 Architect/SA/SD/QA 交叉發現）：兩處
獨立缺陷同輪修復——
(1) 盲區 D 登記表 R52 只補了 `test_dev_start.py` 用 `self._REPO` 消費
    `run_local_nightly.sh` 這一筆，但同一支消費檔內用完全相同手法（`self._REPO`
    ／class 屬性 `_REPO`）另外讀取了 `run_local_nightly.ps1`（僅 1 處）與
    `install_mac_nightly.sh`（3 處呼叫點、橫跨 3 個測試類）卻未登記——現行雖因
    `windows-compat-ci.yml` 的 `**/*.ps1` 萬用字元＋明列 `install_mac_nightly.sh`、
    `macos-compat-ci.yml` 的 `**/*.sh` 萬用字元＋明列 `run_local_nightly.ps1`
    意外雙重覆蓋而無假綠，但登記表本身名不符實、零機械保護，補齊這 2 筆
    （`tools/install_mac_nightly.sh`／`AutoClaude/tools/run_local_nightly.ps1`）。
(2) `_JOIN_RE`（`os.path.join(REPO_ROOT, ...)` 慣用法掃描器）只認得無底線字面
    token `REPO_ROOT`，對 `tools/tests/` 下 21/24 個測試檔慣用的底線前綴
    `_REPO_ROOT` 變數命名結構性零命中；而並用的 `_SLASH_RE`（`REPO_ROOT / "a"`
    慣用法）先前因**無錨定的純子字串匹配**才「巧合」命中 `_REPO_ROOT`——這反而
    是另一種未防護的假陽性風險（子字串匹配對 `FOO_REPO_ROOT` 這類非本意識別字
    同樣會誤命中，見下方測試）。改用共用 token `_REPO_ROOT_TOKEN`（顯式收斂
    `_REPO_ROOT`／`REPO_ROOT`／`_monorepo_root()` 三種寫法皆為完整識別字，非
    子字串）＋前置負向 lookbehind 防止嵌在更長識別字中誤判，`_JOIN_RE`／
    `_SLASH_RE` 兩者行為對稱一致；並新增獨立單元測試直接驗證兩個正則物件本身
    的涵蓋面（回應「安全網自身缺乏測試」的測試設計缺口）。

R54（第 54 輪複審 SA/SD 交叉觀察，純架構前瞻 watch item，非現行缺陷，19 passed
無違規）：本鎖的三份手寫登記字典——`_KNOWN_SUBPROCESS_ONLY_CONSUMERS`（盲區 B，
R19）／`_KNOWN_GLOB_SCAN_CONSUMERS`（盲區 C，R50）／`_KNOWN_LITERAL_PATH_CONSUMERS`
（盲區 D，R52，且 R53 才發現盲區 D 內部登記本身漏補）——已與 WindowsApps guard
家族（DEF-101-400）同構演化出「正則/登記表軍備競賽」模式，但後者已有 Architect
明訂的收斂門檻（「若出現第 6 個繞過手法，優先評估 AST-based 掃描」），本鎖側從未
被賦予對等門檻。比照 DEF-101-400 措辭訂立決策準則供未來輪參考：**若再出現第 4
個盲區，或單一盲區內部第 2 次漏登記，優先評估收斂為程式化反向驗證（如對
`_KNOWN_*` 字典本身跑一次「有無遺漏子路徑」的通用掃描），而非再疊一份手寫登記
字典**。本節純記錄門檻，不阻擋、不改動任何測試邏輯。

R67（第 67 輪 Mac/Windows 相容性複審；R54 門檻首次被觸發並兌現）：R66 收斂出的
SSOT `tools/lib/sdd_latest.py` 被 `tools/tests/` 下 10 支測試檔 `import sdd_latest`
消費，卻在 macos-compat-ci.yml／windows-compat-ci.yml 雙邊 paths 皆未列名，而本鎖
19 passed 全綠零訊號（DEF-101-042 同構假綠）。根因是 `_SYSPATH_PARENTS_RE`（第五個
盲區，盲區 E）要求 `Path(__file__).resolve().parents[N]` **逐字內嵌**在
`sys.path.insert(...)` 引數裡；而該 10 支消費者用的全是「先把基底綁進具名變數、再用
該變數組路徑」的寫法（`_REPO_ROOT = _TESTS_DIR.parents[1]` +
`sys.path.insert(0, str(_REPO_ROOT / "tools" / "lib"))`），對逐字正則結構性零命中。
判別條件竟是**寫法變體**而非語意——同一句 `sys.path.insert` 換個等價寫法就從「看得見」
變成「看不見」。

依檔頭 R54 訂立的收斂門檻（「若再出現第 4 個盲區……優先評估收斂為程式化反向驗證，
而非再疊一份手寫登記字典」），本輪**不再疊第 6 條正則、也不新增第 4 份登記字典**，
改為 **AST 解析 + 常數傳播**（本 repo 先例：`tools/check_script_parity.py::
_extract_tier_map_from_source`）：以 `ast.parse` 找出全部 `sys.path.insert` 呼叫，
對其第 2 引數做符號求值（`Path(__file__)`／`__file__`／`.resolve()`／`.parent`／
`.parents[N]`／`/ "seg"`／`.joinpath()`／`str()`／`os.path.join`／`os.path.dirname`
／`os.path.abspath`），並解析同檔內的名稱綁定，使 inline 形態與變數形態在語意上等價
地解析到同一個目錄——寫法變體不再是判別條件（見
`test_sys_path_insert_forms_resolve_equivalently`，直接對解析器斷言四種等價寫法必須
給出同一目錄）。另配 fail-loud（`test_no_unresolvable_sys_path_inserts`）：解析不出
的 `sys.path.insert` 會被列名讓本鎖紅，而非像舊正則那樣靜默略過——**靜默略過正是本輪
缺陷得以存活的機制**（Rule 12）。實測：改用 AST 後掃描結果相對舊正則
NEW=+1（`tools/lib/sdd_latest.py`）、LOST=0、無法解析者 0。

R67 round 2（SA-R67-01 ＋ SD-R67-02 兩方交叉發現，**同輪原地復發**）：上一段 R67 才
修完「新增的承重檔不在 compat-CI paths、且本鎖對它結構性失明」，**同一輪新增的**
`AISDLC_SDD/AISDLC_SDD_v0.30/conftest.py` 又完全命中同一件事（雙 workflow paths
命中 0 次、本鎖 24 passed 零訊號）。根因有**兩層**，兩層都修：

  1. **盲區 F ── pytest 隱式載入的 rootdir conftest**。`conftest.py` 是 pytest 依
     rootdir 自動載入的，**結構上不會出現在任何 step 的命令列、也不被任何測試
     import**：`_scan_dir_for_root_paths()`（路徑字面）與 `_scan_import_consumed_paths()`
     （import BFS）兩套偵測機制對它同時零訊號。這與盲區 B／C／D 同屬「掃描器方法論
     邊界」，但**不再疊第 4 份手寫登記字典**（R54 收斂門檻已於上一段兌現一次）：改用
     **程式化反向驗證**——直接向 git 要「repo 內全部 conftest.py（tracked ＋ 未被
     .gitignore 排除的 untracked）」，逐一斷言被兩支 compat-CI 的 paths 覆蓋（見
     `test_pytest_rootdir_conftests_covered_by_ci_paths`）。**刻意連 untracked 也要**：
     本輪的缺陷檔在被 commit 之前就該紅，只認 tracked 等於把訊號延後到 commit 之後。
     判準取「repo 內全部 conftest.py」這個**誠實的超集**——精確集合（哪些 rootdir 真被
     CI 的 pytest 用到）要解析 `run:` 區塊裡的 shell，脆弱且會變成另一個會腐化的推論；
     而超集在現況下的額外成本是 0（其餘 conftest 早已被既有萬用字元覆蓋）。
  2. **`AISDLC_SDD/` 前綴豁免的前提是錯的**（見上方檔頭訂正段）。這一層才解釋「為何
     上一輪升級成 AST 之後仍漏」：對 `AISDLC_SDD/conftest.py` 而言掃描器**根本沒瞎**
     （`tools/tests/test_subprocess_encoding_hygiene.py` 以 `_REPO_ROOT / "AISDLC_SDD"
     / "conftest.py"` 消費它，`_SLASH_RE` 命中），是最後那道 `not p.startswith(
     "AISDLC_SDD/")` 把它扔了。單修第 1 層而不拆這個豁免，本鎖仍會對整個
     `AISDLC_SDD/` 子樹（compat-CI 四條白名單之外的部分）繼續失明。

盲區 G ── `from <套件> import <模組>`（DEF-101-042 假綠第 7 種形態）
  舊 `_FROM_IMPORT_RE` 只抓 `from` 後**第一段名稱**，下游再把它當模組名去找 `<name>.py`。
  於是 `from lib import baseline_origin as BO` 得出的是**套件名** `lib`，找不到 `lib.py`
  就**靜默丟棄**——真正被消費的 `tools/lib/baseline_origin.py` 對本鎖結構性隱形。同構受害者
  `tools/lib/defect_ledger_index.py`（`tools/archive_defect_log.py` ＋
  `tools/check_defect_log_crossref.py` 以同一句式消費）。實測後果：兩支 SSOT 在
  windows-compat-ci.yml／macos-compat-ci.yml 的 paths **雙邊命中 0 次**，而本鎖 34 passed
  全綠 ⇒ 只改這兩支檔的 push 不會觸發任一支 compat-CI。`root-infra-ci.yml` 無 paths 過濾故
  純 Python 迴歸仍被 ubuntu 攔下，**逃掉的正是 Windows／macOS 專屬迴歸**——也就是這兩支
  workflow 唯一存在的理由。

  依 R54 收斂門檻（第 4 個盲區起優先程式化反向驗證、不再疊手寫登記字典）與 R67 的先例，
  本輪**拆掉兩條 import 正則、改 AST**（`ast.Import` 逐 alias、`ast.ImportFrom` 以
  `module` ＋ `alias.name` 組出候選），並一併修掉同源的兩個結構性限制：
    · **候選基底目錄**由「自身目錄＋父目錄」兩層寫死，改為**逐層祖先到 monorepo 根**。
      `AISDLC_SDD/scripts/tests/` 下 20 支測試寫 `from scripts import sdd_version`，靠的是
      ci-gate 的 `cd AISDLC_SDD && python -m pytest scripts/tests/` 把 `AISDLC_SDD/` 放進
      sys.path（第三層祖先）——兩層候選對它零命中。
    · **sys.path 是行程全域的**：`tools/tests/test_find_git_bash_parity.py` 的
      `import bash_probe_spec` 依賴 `import integration_gate_core` 的 side effect（該檔逐字
      註解如此記載）。故 BFS 改為累積一個全域 sys.path 池並跑到 fixed point（實測 2 輪收斂）。
  fail-loud（`test_no_unresolvable_imports`）：解析不出對應檔案的 import 會被列名讓本鎖紅，
  唯一可辯護的忽略理由是「標準庫（`sys.stdlib_module_names` 機械認定）／已宣告第三方
  （`_KNOWN_EXTERNAL_MODULES`，刻意最小）」。**靜默丟棄本身就是機制缺陷**——盲區 E 與盲區 G
  兩次都是靠它存活的。實測：改 AST ＋ 祖先基底 ＋ 全域池後，無法解析的 import 由 21 筆降為
  **0 筆**，掃描面 84 → 113 檔（NEW=29、LOST=0）。

盲區 H ── 模組層 list literal 內的相對路徑字串
  `tools/tests/test_doc_env_prefix_platform_parity_r60.py` 用模組層 `_LIVE_DOCS = [...]`
  名冊（10 份活文件）逐份讀取，而非 `_REPO_ROOT / "…"` 路徑運算式，也不是 import ⇒
  `_JOIN_RE`／`_SLASH_RE`／import BFS 三者同時零訊號。實測使 `README.md`／`useMacWin.md`／
  `docs/AISDLC_Agent_UserGuide.md`（名冊 n=10，三者皆在冊且磁碟存在，兩支 compat-CI 都跑
  這棵樹）在雙邊 paths 皆未涵蓋。新增 `_module_level_list_literal_strings()`（AST：
  模組層 `ast.Assign`／`ast.AnnAssign` 的 `ast.List`，含巢狀結構內的 `ast.Constant` 字串），
  刻意不含模組層 `dict`／`tuple`——本鎖自己的 `_KNOWN_*` 登記表正是那個形狀，納入會把
  「鎖記載的檔案」誤算成消費檔而逼出一批假需求。
"""
from __future__ import annotations

import ast
import fnmatch
import ntpath
import os
import re
import subprocess
import sys
from typing import NamedTuple

import pytest
import yaml

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))


def _monorepo_root() -> str:
    # scripts/tests/ → scripts/ → AISDLC_SDD/ → monorepo 根
    return os.path.dirname(os.path.dirname(os.path.dirname(_TESTS_DIR)))


_WORKFLOWS_DIR = os.path.join(_monorepo_root(), ".github", "workflows")

# workflow 檔名 ↔ 其實際執行的測試目錄（見各 workflow 內對應 run: 步驟）。
_WORKFLOW_TEST_DIRS: dict[str, str] = {
    "aisdlc-sdd-ci.yml": _TESTS_DIR,
    "windows-compat-ci.yml": os.path.join(_monorepo_root(), "tools", "tests"),
    "macos-compat-ci.yml": os.path.join(_monorepo_root(), "tools", "tests"),
}


def _workflow_paths(workflow_filename: str) -> tuple[list[str], list[str]]:
    wf = os.path.join(_WORKFLOWS_DIR, workflow_filename)
    with open(wf, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    on = data.get("on") or data.get(True)  # YAML 1.1 把裸 key `on` 解析為布林 True
    return on["push"]["paths"], on["pull_request"]["paths"]


# _monorepo_root()（AISDLC_SDD/scripts/tests/ 慣用法）與 REPO_ROOT／_REPO_ROOT
# （tools/tests/ 慣用法，該目錄下巧合等於 monorepo 根；21/24 個測試檔實際採用
# 底線前綴 `_REPO_ROOT` 命名慣例，僅 3 個無底線）皆可能出現在被掃描目錄中；
# 三者統一辨識為完整識別字（前置負向 lookbehind 防止嵌在更長識別字中誤判，如
# `FOO_REPO_ROOT`），誤配對到的候選路徑會被下方「磁碟上存在」過濾器自然濾除
# （安全網）。R53：修復 `_JOIN_RE` 先前只認無底線 `REPO_ROOT`、與 `_SLASH_RE`
# （先前靠無錨定子字串匹配才「巧合」吃到底線前綴）行為不對稱的正則死角。
_REPO_ROOT_TOKEN = r"(?:_monorepo_root\(\)|_REPO_ROOT|REPO_ROOT)"
_NOT_WORD_BEFORE = r"(?<![A-Za-z0-9_])"
_JOIN_RE = re.compile(
    rf"os\.path\.join\(\s*{_NOT_WORD_BEFORE}{_REPO_ROOT_TOKEN}\s*,([^)]*)\)"
)
_SLASH_RE = re.compile(
    rf'{_NOT_WORD_BEFORE}{_REPO_ROOT_TOKEN}((?:\s*/\s*"[^"]+")+)'
)
_STR_RE = re.compile(r'"([^"]+)"')

# S26／R19 舊實作：`_IMPORT_RE`（`import X`／`import X as Y`）＋ `_FROM_IMPORT_RE`
# （只取 `from` 後第一段名稱）兩條正則。兩者已由下方 AST 解析取代——理由見檔頭
# 〈盲區 G〉：`_FROM_IMPORT_RE` 對 `from lib import baseline_origin as BO` 得出的是
# **套件名** `lib`，下游拿它去找 `lib.py` 找不到就靜默丟棄，被消費的模組因此隱形。

# R19 修復包 A 盲區 A：`sys.path.insert(0, str(Path(__file__).resolve().parents[N]))`
# 或其後接 `/ "seg1" / "seg2" ...` 路徑片段（如 tools/tests/test_platform_utils_dedup.py
# 的 `parents[1] / "lib"`，把 tools/lib/ 塞進 sys.path 才能 `import platform_utils`）。
# 舊版 candidate_base_dirs 只猜「own_dir / parent(own_dir)」兩層寫死候選，platform_utils.py
# 實際多一層 lib/ 子目錄，兩個候選都撲空。原以正則動態抓出原始碼裡實際出現的
# sys.path.insert 陳述式所指向的路徑，相對於來源檔自身位置解析 parents[N]，取代猜測。
#
# R67 盲區 E：該正則要求整串 `Path(__file__).resolve().parents[N]` **逐字內嵌**在
# `sys.path.insert(...)` 引數裡，對「基底先綁進具名變數再組路徑」的等價寫法結構性
# 零命中（詳見檔頭 R67）。依 R54 收斂門檻改用 AST 解析 + 常數傳播取代該正則，讓
# 判別條件回歸語意而非寫法變體。以下為 AST 實作。

# `A = B / "x"` 與 `B = A` 這類互相參照的名稱綁定會讓符號求值無限遞迴，設遞迴深度
# 上限硬停（解析不出即回 None → 由 fail-loud 測試列名，不會靜默略過）。
_MAX_PATH_EXPR_DEPTH = 40

# 可被符號求值的 os.path 函式：join（首引數為路徑、其餘為字串片段）與
# 一元的 dirname／abspath／realpath／normpath。
_OS_PATH_UNARY = ("os.path.abspath", "os.path.realpath", "os.path.normpath")


def _dotted_name(node: ast.AST) -> str | None:
    """把 `os.path.join` / `Path` 這類「純名稱點鏈」還原成字串；非純點鏈回傳 None。"""
    parts: list[str] = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if not isinstance(node, ast.Name):
        return None
    parts.append(node.id)
    return ".".join(reversed(parts))


def _eval_path_expr(
    node: ast.AST,
    source_file: str,
    bindings: dict[str, ast.expr],
    _depth: int = 0,
) -> str | None:
    """符號求值一個「路徑運算式」AST 節點 → 絕對路徑字串；無法靜態解析則回傳 None。

    支援本 repo `sys.path.insert` 實際出現的全部慣用法（見檔頭 R67 清單）。關鍵在於
    `ast.Name` 分支會透過 `bindings` 追進同檔內的名稱綁定，故 inline 形態
    （`Path(__file__).resolve().parents[1] / "lib"`）與變數形態
    （`_REPO_ROOT = _TESTS_DIR.parents[1]` 後 `_REPO_ROOT / "tools" / "lib"`）
    會解析到同一個目錄——這正是舊正則做不到、導致 R67 假綠的那件事。
    """
    if _depth > _MAX_PATH_EXPR_DEPTH:
        return None
    nxt = _depth + 1

    if isinstance(node, ast.Name):
        if node.id == "__file__":
            return os.path.abspath(source_file)
        bound = bindings.get(node.id)
        return None if bound is None else _eval_path_expr(bound, source_file, bindings, nxt)

    if isinstance(node, ast.Call):
        dotted = _dotted_name(node.func)
        if dotted in ("Path", "PurePath", "str", "os.fspath") and len(node.args) == 1:
            return _eval_path_expr(node.args[0], source_file, bindings, nxt)
        if dotted == "os.path.dirname" and len(node.args) == 1:
            base = _eval_path_expr(node.args[0], source_file, bindings, nxt)
            return None if base is None else os.path.dirname(base)
        if dotted in _OS_PATH_UNARY and len(node.args) == 1:
            return _eval_path_expr(node.args[0], source_file, bindings, nxt)
        if dotted == "os.path.join" and node.args:
            base = _eval_path_expr(node.args[0], source_file, bindings, nxt)
            segs = _literal_str_args(node.args[1:])
            return None if base is None or segs is None else os.path.join(base, *segs)
        # 方法呼叫（接收者本身是路徑運算式）：X.resolve() / X.absolute() / X.joinpath(...)
        if isinstance(node.func, ast.Attribute):
            if node.func.attr in ("resolve", "absolute", "expanduser"):
                return _eval_path_expr(node.func.value, source_file, bindings, nxt)
            if node.func.attr == "joinpath":
                base = _eval_path_expr(node.func.value, source_file, bindings, nxt)
                segs = _literal_str_args(node.args)
                return None if base is None or segs is None else os.path.join(base, *segs)
        return None

    if isinstance(node, ast.Attribute) and node.attr == "parent":
        base = _eval_path_expr(node.value, source_file, bindings, nxt)
        return None if base is None else os.path.dirname(base)

    # X.parents[N]
    if (
        isinstance(node, ast.Subscript)
        and isinstance(node.value, ast.Attribute)
        and node.value.attr == "parents"
        and isinstance(node.slice, ast.Constant)
        and isinstance(node.slice.value, int)
    ):
        base = _eval_path_expr(node.value.value, source_file, bindings, nxt)
        if base is None:
            return None
        for _ in range(node.slice.value + 1):
            base = os.path.dirname(base)
        return base

    # X / "seg"（pathlib 慣用法；鏈式 X / "a" / "b" 由遞迴自然展開）
    if (
        isinstance(node, ast.BinOp)
        and isinstance(node.op, ast.Div)
        and isinstance(node.right, ast.Constant)
        and isinstance(node.right.value, str)
    ):
        base = _eval_path_expr(node.left, source_file, bindings, nxt)
        return None if base is None else os.path.join(base, node.right.value)

    return None


def _literal_str_args(args: list[ast.expr]) -> list[str] | None:
    """全部引數皆為字串字面值時回傳其值清單；只要有一個不是就回傳 None（不猜）。"""
    out: list[str] = []
    for a in args:
        if not (isinstance(a, ast.Constant) and isinstance(a.value, str)):
            return None
        out.append(a.value)
    return out


def _is_sys_path_insert(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "insert"
        and _dotted_name(node.func.value) == "sys.path"
    )


def _parse_sys_path_inserts(src: str, source_file: str) -> tuple[list[str], list[str]]:
    """解析 `source_file` 原始碼中全部 `sys.path.insert` 陳述式。

    回傳 ``(可靜態解析出的絕對目錄清單, 無法解析者的「檔案:行號: 原式」描述清單)``。
    第二個回傳值讓「掃描器看不懂某句 sys.path.insert」這件事**可被觀測**（見
    `test_no_unresolvable_sys_path_inserts`）；舊正則對看不懂的形態一律靜默略過，
    R67 缺陷正是靠這個靜默存活的。
    """
    try:
        tree = ast.parse(src)
    except SyntaxError:  # 語法壞掉的檔案由其他閘門（py_compile）負責，本鎖不重複報
        return [], []

    # 名稱綁定表：同名以「先出現者」為準（模組層 Assign 在 ast.walk 的 BFS 順序中
    # 早於函式/類別內的同名指派）。誤配到的候選目錄會被下游「磁碟上存在」過濾器
    # 自然濾除（與既有正則路徑同一道安全網）。
    bindings: dict[str, ast.expr] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name):
                bindings.setdefault(target.id, node.value)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.value:
            bindings.setdefault(node.target.id, node.value)

    dirs: list[str] = []
    unresolved: list[str] = []
    for node in ast.walk(tree):
        if not (_is_sys_path_insert(node) and isinstance(node, ast.Call)):
            continue
        if len(node.args) < 2:
            continue
        resolved = _eval_path_expr(node.args[1], source_file, bindings)
        if resolved is None:
            unresolved.append(f"{source_file}:{node.lineno}: {ast.unparse(node)}")
        else:
            dirs.append(os.path.normpath(resolved))
    return dirs, unresolved


def _resolve_sys_path_insert_dirs(src: str, source_file: str) -> list[str]:
    """`_parse_sys_path_inserts` 的目錄投影（僅取可解析者），供 BFS 掃描器使用。"""
    return _parse_sys_path_inserts(src, source_file)[0]


def _scan_dir_for_root_paths(directory: str) -> set[str]:
    found: set[str] = set()
    if not os.path.isdir(directory):
        return found
    for name in sorted(os.listdir(directory)):
        if not (name.startswith("test_") and name.endswith(".py")):
            continue
        with open(os.path.join(directory, name), encoding="utf-8") as f:
            src = f.read()
        for m in _JOIN_RE.finditer(src):
            segs = _STR_RE.findall(m.group(1))
            if segs:
                found.add("/".join(segs))
        for m in _SLASH_RE.finditer(src):
            segs = _STR_RE.findall(m.group(1))
            if segs:
                found.add("/".join(segs))
    return found


# ── 盲區 G：import 陳述式解析（AST，取代兩條正則）─────────────────────────────
class _ImportRequest(NamedTuple):
    """一句 import（或 `import a, b` 的單一 alias）對「磁碟檔案」的解析請求。

    `targets` 是**候選模組路徑段序列**——`from lib import baseline_origin` 同時可能意指
    「`lib.py` 裡的一個名字」與「`lib/` 底下的模組 `baseline_origin`」，兩者都列為候選、
    由磁碟存在性裁決（不猜）。舊 `_FROM_IMPORT_RE` 只產生前者的套件名 `lib`，於是後者
    ——也就是真正被消費的那個檔——結構上永遠看不見（檔頭〈盲區 G〉）。
    """

    targets: tuple[tuple[str, ...], ...]
    level: int          # 相對 import 層數（`from ..x import y` ⇒ 2）；0 ＝ 絕對 import
    top: str            # 頂層名稱，用於判定「標準庫／已宣告第三方 ⇒ 可正當忽略」
    lineno: int
    source: str         # ast.unparse 還原的原式，供 fail-loud 訊息引用


def _import_requests(src: str) -> list[_ImportRequest]:
    """把原始碼中每一句 import 解析為「被消費的模組」候選（語意，不是字面排列）。

    - `ast.Import`：**逐 alias** 一個請求——`import a, b` 少解析到一個也必須被看見。
    - `ast.ImportFrom`：整句一個請求，候選同時含 `<module>` 與 `<module>/<name>`，
      因此 `from lib import baseline_origin`、`from lib import a, b as c`、
      `from lib.sub import x` 三種形態都得出被消費的模組本身。
    """
    try:
        tree = ast.parse(src)
    except SyntaxError:  # 語法壞掉的檔案由 py_compile／ruff 負責，本鎖不重複報
        return []
    out: list[_ImportRequest] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                segs = tuple(alias.name.split("."))
                out.append(
                    _ImportRequest((segs,), 0, segs[0], node.lineno, ast.unparse(node))
                )
        elif isinstance(node, ast.ImportFrom):
            mod = tuple(node.module.split(".")) if node.module else ()
            targets: list[tuple[str, ...]] = [mod] if mod else []
            targets += [mod + (a.name,) for a in node.names if a.name != "*"]
            out.append(
                _ImportRequest(
                    tuple(targets), node.level, mod[0] if mod else ".",
                    node.lineno, ast.unparse(node),
                )
            )
    return out


def _ancestor_dirs(source_file: str) -> list[str]:
    """來源檔自身目錄起逐層向上到 monorepo 根（含），近者優先。

    WHY（為何不是「自身目錄＋父目錄」兩層寫死候選）：`import X` 解析到哪個檔，取決於
    執行期 sys.path／cwd。`AISDLC_SDD/scripts/tests/` 下 20 支測試寫 `from scripts import
    sdd_version`，靠的是 ci-gate 以 `cd AISDLC_SDD && python -m pytest scripts/tests/`
    把 `AISDLC_SDD/` 放進 sys.path（`python -m` 會插入 cwd）——那是**第三層祖先**，兩層
    寫死候選對它結構性零命中。逐層向上是「哪一層是 sys.path 根」這件事的誠實超集；
    誤配到的候選一律被下游磁碟存在性過濾器濾除（與既有正則路徑同一道安全網）。
    """
    root = os.path.normpath(_monorepo_root())
    out: list[str] = []
    d = os.path.dirname(os.path.abspath(source_file))
    while True:
        out.append(d)
        if os.path.normpath(d) == root:
            break
        parent = os.path.dirname(d)
        if parent == d:  # 走到檔案系統根（來源檔在 repo 外）
            break
        d = parent
    return out


def _resolve_import_request(
    req: _ImportRequest, own_dir: str, base_dirs: list[str]
) -> list[str]:
    """把一個解析請求對映到磁碟上實際存在的 .py 檔（可能多個；找不到回空清單）。"""
    if req.level:
        # 相對 import：基底是「來源檔所在套件」往上 level-1 層
        base = own_dir
        for _ in range(req.level - 1):
            base = os.path.dirname(base)
        search = [base]
    else:
        search = base_dirs
    hits: list[str] = []
    for base in search:
        for segs in req.targets:
            candidate = os.path.join(base, *segs) + ".py"
            if os.path.isfile(candidate):
                hits.append(candidate)
    return hits


# 可正當忽略的**第三方**頂層模組。標準庫另由 `sys.stdlib_module_names` 機械認定（不手
# 維護）。本集合刻意保持最小：新增一個沒登記的第三方 import 會讓
# `test_no_unresolvable_imports` 當場列名——那就是「解析不出不准靜默跳過」的意思，
# 同 `tools/run_root_unittests.py::_THIRD_PARTY_PREREQS` 的理念（宣告清單即豁免依據）。
_KNOWN_EXTERNAL_MODULES = frozenset({"pytest", "yaml"})

# sys.path 是**行程全域**的：A 模組 import B 時把某目錄插進 sys.path，之後 C 模組的
# `import D` 就解析得到。實例：`tools/tests/test_find_git_bash_parity.py` 的
# `import bash_probe_spec` 依賴的是 `import integration_gate_core` 的 side effect
# （該檔逐字註解如此記載）。故 BFS 維護一個**累積**的 sys.path 池並跑到 fixed point；
# 池只會單調成長、且成員數以走訪檔數為界，實測 2 輪收斂（上限純為防呆）。
_MAX_SYS_PATH_POOL_ROUNDS = 5

# directory → (consumed, unresolvable sys.path.insert, unresolvable import) 記憶化。
# 本鎖有 6 支測試各自要整份掃描結果，fixed point 又把單次成本乘上收斂輪數。
_IMPORT_SCAN_CACHE: dict[str, tuple[set[str], list[str], list[str]]] = {}


def _import_scan_round(
    directory: str, sys_path_pool: frozenset[str]
) -> tuple[set[str], list[str], list[str], frozenset[str]]:
    """單輪 BFS。回傳 (消費檔, 無解 sys.path.insert, 無解 import, 更新後的 sys.path 池)。"""
    consumed: set[str] = set()
    bad_inserts: list[str] = []
    bad_imports: list[str] = []
    pool = set(sys_path_pool)
    if not os.path.isdir(directory):
        return consumed, bad_inserts, bad_imports, frozenset(pool)
    root = _monorepo_root()
    visited: set[str] = set()
    queue = [
        os.path.join(directory, name)
        for name in sorted(os.listdir(directory))
        if name.startswith("test_") and name.endswith(".py")
    ]
    while queue:
        f = os.path.abspath(queue.pop(0))
        if f in visited or not os.path.isfile(f):
            continue
        visited.add(f)
        with open(f, encoding="utf-8") as fh:
            src = fh.read()
        own_dir = os.path.dirname(f)
        insert_dirs, unresolved = _parse_sys_path_inserts(src, f)
        bad_inserts.extend(unresolved)
        pool.update(insert_dirs)
        base_dirs = [*_ancestor_dirs(f), *sorted(pool)]
        for req in _import_requests(src):
            hits = _resolve_import_request(req, own_dir, base_dirs)
            if not hits:
                # 🔴 靜默丟棄本身就是機制缺陷（檔頭〈盲區 G〉）：只有「標準庫／已宣告
                # 第三方」是可辯護的忽略理由，其餘一律列名讓本鎖紅。
                if (
                    req.top not in sys.stdlib_module_names
                    and req.top not in _KNOWN_EXTERNAL_MODULES
                ):
                    where = os.path.relpath(f, root).replace(os.sep, "/")
                    bad_imports.append(f"{where}:{req.lineno}: {req.source[:120]}")
                continue
            for hit in hits:
                rel = os.path.relpath(hit, root).replace(os.sep, "/")
                if rel.startswith(".."):  # repo 外，非本鎖標的
                    continue
                consumed.add(rel)
                queue.append(hit)
    return consumed, bad_inserts, bad_imports, frozenset(pool)


def _import_scan(directory: str) -> tuple[set[str], list[str], list[str]]:
    """BFS ＋ 全域 sys.path 池 fixed point 的完整 import 消費掃描（記憶化）。"""
    cached = _IMPORT_SCAN_CACHE.get(directory)
    if cached is None:
        pool: frozenset[str] = frozenset()
        consumed: set[str] = set()
        bad_inserts: list[str] = []
        bad_imports: list[str] = []
        for _ in range(_MAX_SYS_PATH_POOL_ROUNDS):
            consumed, bad_inserts, bad_imports, new_pool = _import_scan_round(directory, pool)
            if new_pool <= pool:
                break
            pool = new_pool
        cached = (consumed, bad_inserts, bad_imports)
        _IMPORT_SCAN_CACHE[directory] = cached
    return set(cached[0]), list(cached[1]), list(cached[2])


def _scan_import_consumed_paths(
    directory: str,
    unresolved_out: list[str] | None = None,
    unresolved_imports_out: list[str] | None = None,
) -> set[str]:
    """BFS 掃描 `directory` 內 test_*.py 的 import 陳述式 → 被消費的根層檔案。

    對新發現的根層 .py 檔遞迴重複同一掃描（fixed point），關閉「測試只 import A、
    A 內部又 import B」的第二層盲區（見檔頭 S26）。

    R67：`unresolved_out` 收集走訪範圍內**無法靜態解析**的 `sys.path.insert` 描述，供
    `test_no_unresolvable_sys_path_inserts` fail-loud。
    盲區 G：`unresolved_imports_out` 收集**解析不出對應檔案、又非標準庫／已宣告第三方**
    的 import 描述，供 `test_no_unresolvable_imports` fail-loud——舊實作對這些一律靜默
    丟棄，而那正是本輪缺陷得以存活的機制。
    """
    consumed, bad_inserts, bad_imports = _import_scan(directory)
    if unresolved_out is not None:
        unresolved_out.extend(bad_inserts)
    if unresolved_imports_out is not None:
        unresolved_imports_out.extend(bad_imports)
    return consumed


# ── 盲區 H：模組層 list literal 內的相對路徑字串 ─────────────────────────────
def _module_level_list_literal_strings(src: str) -> set[str]:
    """模組層 list literal（含其內嵌結構）裡的全部字串字面值（檔頭〈盲區 H〉）。

    這是本 repo 宣告「這支測試會讀哪幾份檔」的既有形態——例：
    `tools/tests/test_doc_env_prefix_platform_parity_r60.py::_LIVE_DOCS`（10 份活文件
    名冊）。它既不是 `_REPO_ROOT / "…"` 路徑運算式、也不是 import 陳述式，兩套既有
    掃描器同時零訊號。

    誠實劃界：
      · 只認**模組層指派**的 `ast.List`。函式／類別內的 list 不在射程內（那是區域資料，
        納入會把大量非宣告字串掃進來）。
      · 刻意**不**含模組層 `dict`／`tuple`：本鎖自己的 `_KNOWN_*` 登記表正是那個形狀，
        納入會把「鎖記載的檔案」誤算成「aisdlc-sdd-ci 的消費檔」而逼出一批假需求。
      · 是否為真路徑不在此判定——由 `_scan_module_level_path_literals()` 的形態過濾與
        `_consumed_root_paths()` 的磁碟存在性過濾器裁決。
    """
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return set()
    out: set[str] = set()
    for stmt in tree.body:
        value = stmt.value if isinstance(stmt, (ast.Assign, ast.AnnAssign)) else None
        if not isinstance(value, ast.List):
            continue
        for node in ast.walk(value):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                out.add(node.value)
    return out


def _looks_like_repo_relative_path(text: str) -> bool:
    """只放行「repo 相對、POSIX 分隔符」的字串——絕對路徑／磁碟機／`..` 逃逸一律擋掉。

    否則 `os.path.join(_monorepo_root(), text)` 可能組出 repo 外的真實檔案，讓它以
    無法被 workflow paths（一律 repo 相對）匹配的形態進入消費集合而假紅。
    單一前導點是**允許**的（`.github/workflows/…`／`.claude/…` 都是合法 repo 相對路徑），
    擋掉的是 `..` 逃逸。
    """
    return bool(
        text
        and "\\" not in text
        and ":" not in text
        and not text.startswith(("/", ".."))
        and not os.path.isabs(text)
    )


def _scan_module_level_path_literals(directory: str) -> set[str]:
    found: set[str] = set()
    if not os.path.isdir(directory):
        return found
    for name in sorted(os.listdir(directory)):
        if not (name.startswith("test_") and name.endswith(".py")):
            continue
        with open(os.path.join(directory, name), encoding="utf-8") as f:
            src = f.read()
        found |= {
            s for s in _module_level_list_literal_strings(src)
            if _looks_like_repo_relative_path(s)
        }
    return found


def _consumed_root_paths(directory: str) -> set[str]:
    found = (
        _scan_dir_for_root_paths(directory)
        | _scan_import_consumed_paths(directory)
        | _scan_module_level_path_literals(directory)
    )
    # 只留「磁碟上存在的檔案」——join 到目錄／動態片段者非本鎖標的
    return {p for p in found if os.path.isfile(os.path.join(_monorepo_root(), p))}


@pytest.mark.parametrize(
    "src,expect_join,expect_slash",
    [
        # 無底線 REPO_ROOT／_monorepo_root()：既有慣用法，修復前後皆須命中。
        ('os.path.join(REPO_ROOT, "a", "b")', True, None),
        ('REPO_ROOT / "a" / "b"', None, True),
        ('os.path.join(_monorepo_root(), "a", "b")', True, None),
        ('_monorepo_root() / "a" / "b"', None, True),
        # R53：底線前綴 _REPO_ROOT（tools/tests/ 21/24 檔實際命名慣例）——修復前
        # _JOIN_RE 結構性零命中，_SLASH_RE 靠無錨定子字串「巧合」命中；修復後
        # 兩者須對稱皆命中。
        ('os.path.join(_REPO_ROOT, "a", "b")', True, None),
        ('_REPO_ROOT / "a" / "b"', None, True),
    ],
)
def test_join_re_and_slash_re_symmetric_for_underscore_prefix(src, expect_join, expect_slash):
    """R53 QA/Architect/SA/SD 四方交叉發現：`_JOIN_RE`／`_SLASH_RE` 這兩個「防
    假綠安全網」正則自身先前無任何獨立單元測試驗證涵蓋面，導致 `_JOIN_RE` 對
    底線前綴 `_REPO_ROOT`（主流命名慣例）結構性零命中的死角長期無訊號。本測試
    直接對正則物件斷言，鎖住修復後的對稱行為，防止未來再退化。
    """
    if expect_join is not None:
        assert bool(_JOIN_RE.search(src)) is expect_join, f"_JOIN_RE 對 {src!r} 命中應為 {expect_join}"
    if expect_slash is not None:
        assert bool(_SLASH_RE.search(src)) is expect_slash, (
            f"_SLASH_RE 對 {src!r} 命中應為 {expect_slash}"
        )


def test_slash_re_does_not_match_longer_embedding_identifier():
    """R53 附帶防呆：`_SLASH_RE` 修復底線前綴死角時新增的前置負向 lookbehind，
    須確認未反過來對「REPO_ROOT 只是更長識別字尾碼」的情況（如
    `FOO_REPO_ROOT`）誤判為本鎖標的變數——修復前的純子字串匹配對此會誤命中
    （見 R53 檔頭說明），修復後應正確排除。
    """
    assert not _SLASH_RE.search('FOO_REPO_ROOT / "a" / "b"'), (
        "_SLASH_RE 不應把 FOO_REPO_ROOT 這類更長識別字尾碼誤判為 REPO_ROOT 本尊"
    )


# R67 盲區 E：`sys.path.insert` 解析器的四種等價寫法。全部意在把 `<repo>/tools/lib`
# 塞進 sys.path，僅寫法不同；來源檔一律假定位於 `<repo>/tools/tests/test_fake.py`。
# 舊 `_SYSPATH_PARENTS_RE` 只認第 1 種（inline），對第 2~4 種（具名變數基底）結構性
# 零命中——而 R66 SSOT `tools/lib/sdd_latest.py` 的 10 支真實消費者用的全是第 2/3 種。
_SYS_PATH_INSERT_EQUIVALENT_FORMS: dict[str, str] = {
    # 1. inline：舊正則唯一認得的形態（tools/tests/test_platform_utils_dedup.py）
    "inline-parents": 'sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))\n',
    # 2. 具名 _REPO_ROOT 基底（tools/tests/test_platform_neutral_paths.py 等 8 支實際寫法）
    "named-repo-root": (
        "_TESTS_DIR = Path(__file__).resolve().parent\n"
        "_REPO_ROOT = _TESTS_DIR.parents[1]\n"
        'sys.path.insert(0, str(_REPO_ROOT / "tools" / "lib"))\n'
    ),
    # 3. 具名 _TOOLS_DIR 中繼基底（tools/tests/test_windows_forbidden_filename_parity.py）
    "named-tools-dir": (
        "REPO_ROOT = Path(__file__).resolve().parents[2]\n"
        '_TOOLS_DIR = REPO_ROOT / "tools"\n'
        'sys.path.insert(0, str(_TOOLS_DIR / "lib"))\n'
    ),
    # 4. os.path 家族（AISDLC_SDD/scripts/tests/ 慣用法，含 ".." 相對片段）
    "os-path-join": (
        "HERE = os.path.dirname(os.path.abspath(__file__))\n"
        'sys.path.insert(0, os.path.join(HERE, "..", "lib"))\n'
    ),
}

# 🔴 R68（windows-compat-ci 首度真跑到本套件才顯形）：假「絕對」路徑的**錨點**必須與
# 受測解析器所用的錨點一致，否則測試對「本機是哪個平台」做了未言明的前提假設。
#
# 原寫法 `os.path.join(os.sep, "repo", ...)` 在 POSIX 上得 `/repo/...`（真絕對），在
# Windows 上卻得 `\repo\...`——那是 **drive-relative**（缺磁碟機代號）而非絕對路徑。
# 而 `_eval_path_expr()` 解析 `__file__` 時走的是 `os.path.abspath(source_file)`，
# Win32 `GetFullPathNameW` 會補上「目前工作磁碟機」⇒ 實得 `D:\repo\tools\lib`、期望值
# 仍是 `\repo\tools\lib`，兩者分屬不同 anchor ⇒ 4 支參數化案例在 Windows 上全紅
# （CI run 30701321963 逐字：`assert ['D:\\repo\\tools\\lib'] == ['\\repo\\tools\\lib']`）。
#
# 修法是讓期望值與受測物**走同一條正規化路徑**（`os.path.abspath`），而不是各自組字串：
# POSIX 上 abspath 對 `/repo/...` 是 no-op、行為不變；Windows 上兩側同樣被補上目前磁碟機
# 而相等。同型判例見 `tools/tests/_platform_helpers.py::ABS_FAKE_REPO`（該處是 pathlib
# join 語意的同一個坑）。
_FAKE_REPO = "repo"


def _fake_abs(*segments: str) -> str:
    """組出在**當前平台語意下真正絕對**的假路徑（Windows 上含磁碟機代號）。

    刻意透過 module-global `os` 取用（而非 import 期綁定 `os.path.abspath`），使
    `TestWindowsPathSemantics` 得以換上 Windows 語意 shim 後在 macOS/Linux 當場重跑
    本函式與受測解析器——「換平台」因此是本機可驗的事，不必等 Windows runner。
    """
    return os.path.abspath(os.path.join(os.sep, *segments))


@pytest.mark.parametrize("form_name", sorted(_SYS_PATH_INSERT_EQUIVALENT_FORMS))
def test_sys_path_insert_forms_resolve_equivalently(form_name):
    """R67 盲區 E 回歸鎖：解析器的判別條件必須是**語意**，不是**寫法變體**。

    WHY（Rule 9 — 測試驗意圖）：`_resolve_sys_path_insert_dirs()` 存在的唯一理由是
    「知道測試檔把哪個目錄塞進 sys.path，才能把 `import X` 解析成真實根層檔」。這件
    事只取決於該陳述式指向哪個目錄，與作者選擇 inline 還是先綁變數**在語意上毫無關
    係**。R67 之前它卻只認 inline 一種寫法，於是 R66 的 SSOT
    `tools/lib/sdd_latest.py`（10 支消費者全用具名變數形態）對本鎖完全隱形，雙
    compat-CI 漏列它卻 19 passed 全綠。本測試把「四種等價寫法必須解析到同一個目錄」
    釘成契約：任何讓解析器退回「只認某種特定字面排列」的改動（含改回正則）即刻轉紅。
    """
    fake_source = _fake_abs(_FAKE_REPO, "tools", "tests", "test_fake.py")
    expected = _fake_abs(_FAKE_REPO, "tools", "lib")
    src = _SYS_PATH_INSERT_EQUIVALENT_FORMS[form_name]
    resolved = _resolve_sys_path_insert_dirs(src, fake_source)
    assert resolved == [expected], (
        f"sys.path.insert 寫法 {form_name!r} 應解析為 {expected!r}（與其餘等價寫法同），"
        f"實得 {resolved!r}——解析器又退化成認寫法而非認語意（R67 盲區 E 同構）"
    )


# ──────────────────────────────────────────────────────────────
# R68 回歸鎖：上一條在 Windows 路徑語意下也必須成立（本機可驗，不必等 runner）
# ──────────────────────────────────────────────────────────────
# 下一行的磁碟機字面值是**模擬 Windows 用的輸入資料本身**（要模擬「Win32 abspath 會補上
# 目前工作磁碟機」就非得有一個磁碟機代號不可），不是被當成本機真實路徑去 join／resolve
# 的假 repo 根——與 `_platform_helpers.ABS_FAKE_REPO`（該檔的 win32 分支同樣寫死磁碟機、
# 且同樣列在該掃描器的 _ALLOWED 豁免）是同一個性質。故用該掃描器提供的行尾豁免標記。
_SIMULATED_WINDOWS_CWD = "D:\\a\\AISDCL_Agent\\AISDCL_Agent"  # platform-ok: 模擬器輸入資料，非本機路徑


class _WindowsPathShim:
    """`os.path` 的 Windows 語意替身：ntpath ＋ 忠實模擬 Win32 `GetFullPathNameW`。

    為何不能直接把 `os.path` 換成 `ntpath` 了事：非 Windows 上 `ntpath.abspath` 走
    `_abspath_fallback`，而 `ntpath.isabs("\\\\repo\\\\x")` 回 True（ntpath 把「單一
    前導分隔符」也算絕對）⇒ 原樣返回、**不補磁碟機代號**。但真 Windows 的
    `ntpath.abspath` 走 `nt._getfullpathname`，會補上目前工作磁碟機——「補磁碟機」正是
    本缺陷的關鍵一步。直接用 ntpath 的鎖會恆綠＝零鑑別力（本機實測確認：未補此步時
    4 支案例全 OK，補上後 4 支全 FAIL、與 CI 逐字相符）。
    """

    def __getattr__(self, name):
        return getattr(ntpath, name)

    def abspath(self, path: str) -> str:
        drive, rest = ntpath.splitdrive(path)
        if drive:
            return ntpath.normpath(path)
        if rest.startswith("\\"):                       # drive-relative：補目前磁碟機
            return ntpath.splitdrive(_SIMULATED_WINDOWS_CWD)[0] + ntpath.normpath(rest)
        return ntpath.normpath(ntpath.join(_SIMULATED_WINDOWS_CWD, path))


class _WindowsOsShim:
    """`os` 的 Windows 語意替身（只覆寫 `sep`／`path`，其餘一律轉發真 `os`）。"""

    sep = "\\"
    path = _WindowsPathShim()

    def __getattr__(self, name):
        return getattr(os, name)


@pytest.mark.parametrize("form_name", sorted(_SYS_PATH_INSERT_EQUIVALENT_FORMS))
def test_sys_path_insert_forms_resolve_equivalently_under_windows_semantics(
    form_name, monkeypatch
):
    """🔴 R68：上一條鎖不得對「本機是哪個平台」做未言明的前提假設。

    WHY（Rule 9 — 測意圖）：上一條鎖驗的是「解析器認語意、不認寫法」。這個意圖與作業
    系統毫無關係，所以它**在每個平台上都必須得出同一個結果**。實際上它曾經借用
    `os.sep` 組假絕對路徑，於是在 Windows 上期望值退化成 drive-relative、與受測物
    `abspath` 出來的 `D:\\...` 恆不相等——4 支案例在 windows-compat-ci 首度真跑時全紅
    （run 30701321963）。那 4 個紅燈說的不是「解析器壞了」，是「測試自己的前提在這台
    機器上不成立」——**假紅比假綠更快讓人學會忽略紅燈**（同
    `tools/tests/test_doc_loc_baseline_freshness_r60.py::
    TestR67R3ThisFileMakesNoUnstatedPlatformAssumption` 判例，方向換成 Windows）。

    手法：把本模組的 module-global `os` 換成 Windows 語意 shim 後**重跑上一條鎖本身**
    （不是複製一份等價邏輯——複製品會與被鎖對象各自漂移）。

    邊界（誠實劃界）：只模擬 `os.sep` 與 `os.path`（ntpath ＋ GetFullPathNameW 的補磁碟機
    行為）。真實檔案系統、大小寫不敏感、UNC、`\\\\?\\` 長路徑前綴、`os.name` 皆**不在**
    模擬範圍 ⇒ 本鎖綠**不等於**「本檔在真 Windows 上必綠」，只等於「上一條鎖不因路徑
    分隔符/anchor 語意而異」。對受測物而言這已是全部：`_eval_path_expr()` 的平台輸入
    只有 `os.path`／`os.sep`，不讀 `os.name`、不碰磁碟。
    """
    monkeypatch.setitem(globals(), "os", _WindowsOsShim())
    test_sys_path_insert_forms_resolve_equivalently(form_name)


def test_no_unresolvable_sys_path_inserts():
    """R67 fail-loud（Rule 12）：掃描器看不懂的 `sys.path.insert` 必須當場列名。

    WHY：R67 缺陷之所以能存活，不是因為掃描器「判斷錯」，而是因為它對看不懂的形態
    **靜默略過**——沒有任何訊號告訴任何人「這裡有一句我沒讀懂、因此下游 import 解析
    是不完整的」。本鎖把「解析失敗」從靜默降級升成顯式失敗：新增一句本解析器不支援
    的 sys.path.insert 寫法時，作者當場看到它，必須擴充 `_eval_path_expr()`（或改寫
    成可靜態解析的形態），而不是在幾輪之後才由某次四方複審實測撞出假綠。
    """
    unresolved: list[str] = []
    for directory in _WORKFLOW_TEST_DIRS.values():
        _scan_import_consumed_paths(directory, unresolved_out=unresolved)
    assert not unresolved, (
        "以下 sys.path.insert 陳述式無法被 _eval_path_expr() 靜態解析，其指向的目錄"
        "不會納入 import 解析候選，該路徑下的根層消費檔將對本鎖隱形（R67 盲區 E 同構"
        "假綠）。請擴充 _eval_path_expr() 支援該寫法，或把該陳述式改寫成可靜態解析的"
        "形態：\n  " + "\n  ".join(sorted(set(unresolved)))
    )


# ──────────────────────────────────────────────────────────────
# 盲區 G 回歸鎖：`from <套件> import <模組>` 必須解析出**被消費的模組**
# ──────────────────────────────────────────────────────────────
@pytest.mark.parametrize(
    "src,must_contain",
    [
        # 盲區 G 本體（`tools/tests/test_doc_loc_baseline_freshness_r60.py` 與
        # `tools/sync_onboarding_baselines.py` 的真實寫法）。舊 `_FROM_IMPORT_RE` 對這一句
        # 得出的是套件名 `lib`，找不到 `lib.py` 即靜默丟棄 ⇒ tools/lib/baseline_origin.py
        # 對本鎖結構性隱形，雙 compat-CI 漏列它卻 34 passed 全綠。
        ("from lib import baseline_origin as BO\n", ("lib", "baseline_origin")),
        # 多目標：兩個都要看得見（舊正則一個都沒有）
        ("from lib import a, b as c\n", ("lib", "a")),
        ("from lib import a, b as c\n", ("lib", "b")),
        # 點狀套件路徑（舊正則的 `[A-Za-z_][A-Za-z0-9_]*` 只吃到第一段）
        ("from lib.sub import x\n", ("lib", "sub", "x")),
        ("from autoclaude.utils import logger as L\n", ("autoclaude", "utils", "logger")),
        # 🔴 既有形態不得退化（S26／R19 已守住的三種）
        ("import platform_utils\n", ("platform_utils",)),
        ("import check_hooks_liveness as m\n", ("check_hooks_liveness",)),
        ("import autoclaude.models.escalation\n", ("autoclaude", "models", "escalation")),
        # `from mymod import func`：被消費的是 mymod 本身，這一半也要在候選內
        ("from integration_gate_core import main\n", ("integration_gate_core",)),
    ],
)
def test_import_parser_yields_consumed_module_not_only_package_name(src, must_contain):
    """盲區 G 回歸鎖：import 解析的判別條件必須是**語意**（誰被消費），不是**寫法**。

    WHY（Rule 9 — 測意圖）：本鎖存在的唯一理由是「知道測試會讀到哪些根層檔，才能斷言
    那些檔在 compat-CI 的 paths 內」。`from lib import baseline_origin` 被消費的是
    `tools/lib/baseline_origin.py`——這與作者寫 `import` 還是 `from … import`、有沒有
    `as`、套件名有幾段點，語意上毫無關係。舊實作卻只認 `from` 後第一段名稱，於是
    `tools/lib/baseline_origin.py` 與 `tools/lib/defect_ledger_index.py` 兩支被真實消費的
    SSOT 在雙 compat-CI paths 皆缺席而無任何訊號：**只改這兩支檔的 push 不會觸發任一支
    compat-CI**，Windows／macOS 專屬迴歸因此逃過雲端攔阻（DEF-101-042 假綠第 7 種形態）。
    任何讓解析退回「只認第一段名稱／只認某種字面排列」的改動（含改回正則）即刻轉紅。
    """
    targets = {t for r in _import_requests(src) for t in r.targets}
    assert must_contain in targets, (
        f"import 陳述式 {src.strip()!r} 應解析出被消費模組 {must_contain}，"
        f"實得候選 {sorted(targets)}——解析器又退回認寫法而非認語意（盲區 G 同構）"
    )


def test_from_import_does_not_collapse_to_package_name_only():
    """把舊行為**逐一點名**釘死：只得出套件名 ＝ 解析失敗，不是解析成功。

    WHY：上一條斷言的是「新答案在候選裡」，本條斷言的是「舊答案不足以充當答案」。
    兩者缺一都可能被一個「候選集合裡塞進套件名就算過」的實作騙過去。
    """
    targets = {t for r in _import_requests("from lib import baseline_origin as BO\n")
               for t in r.targets}
    assert targets != {("lib",)}, (
        "解析結果只有套件名 `lib`——這正是舊 `_FROM_IMPORT_RE` 的行為：下游拿 `lib` 去找 "
        "`lib.py` 找不到就靜默丟棄，被消費的 tools/lib/baseline_origin.py 因此隱形"
    )
    assert ("lib", "baseline_origin") in targets


def test_no_unresolvable_imports():
    """盲區 G fail-loud（Rule 12）：解析不出對應檔案的 import 必須當場列名。

    WHY：盲區 G 之所以能存活，不是掃描器「判斷錯」，而是它對解析不出的模組名
    **靜默跳過**——沒有任何訊號說「這裡有一句我沒對映到檔案，因此消費面是不完整的」。
    本鎖把它升級為顯式失敗，唯一可辯護的忽略理由是「標準庫（`sys.stdlib_module_names`
    機械認定）／已宣告第三方（`_KNOWN_EXTERNAL_MODULES`）」。新增一個沒登記的第三方
    相依、或寫出本解析器對映不到的 import 形態時，作者當場看到它。
    """
    unresolved: list[str] = []
    for directory in _WORKFLOW_TEST_DIRS.values():
        _scan_import_consumed_paths(directory, unresolved_imports_out=unresolved)
    assert not unresolved, (
        "以下 import 陳述式解析不出對應檔案，且頂層名稱既非標準庫也未登記於 "
        "_KNOWN_EXTERNAL_MODULES ⇒ 其消費的檔案（若在 repo 內）對本鎖隱形（盲區 G 同構"
        "假綠）。請擴充 _resolve_import_request()／_ancestor_dirs() 的解析面，或把該第三方"
        "模組登記進 _KNOWN_EXTERNAL_MODULES：\n  " + "\n  ".join(sorted(set(unresolved)))
    )


# ──────────────────────────────────────────────────────────────
# 盲區 H 回歸鎖：模組層 list literal 內的相對路徑字串
# ──────────────────────────────────────────────────────────────
def test_module_level_list_literal_paths_are_visible():
    """盲區 H：以 list literal 宣告「我會讀這幾份檔」的形態必須被掃描面看見。

    WHY（Rule 9 — 測意圖）：`tools/tests/test_doc_env_prefix_platform_parity_r60.py` 用
    模組層 `_LIVE_DOCS = [...]` 名冊逐份讀取活文件（而非 `_REPO_ROOT / "…"` 路徑運算式），
    於是 `README.md`／`useMacWin.md`／`docs/AISDLC_Agent_UserGuide.md` 三份**真被消費**的
    文件在雙 compat-CI paths 皆缺席——改文件不觸發 compat-CI，守著它們的鎖恰好不跑。
    這與盲區 A~F 的每一種都不同：既非路徑運算式、亦非 import、亦非 glob／子行程／
    conftest 隱式載入，而是「宣告資料」這第三種消費宣告形態。
    """
    src = (
        "_LIVE_DOCS = [\n"
        '    "README.md",\n'
        '    "docs/AISDLC_Agent_UserGuide.md",\n'
        '    ".github/workflows/autoclaude-ci.yml",\n'
        "]\n"
        "_PAIRS = [(\"useMacWin.md\", 3)]\n"
    )
    got = _module_level_list_literal_strings(src)
    for expected in (
        "README.md",
        "docs/AISDLC_Agent_UserGuide.md",
        ".github/workflows/autoclaude-ci.yml",
        "useMacWin.md",  # 巢狀 tuple 內的字串也算（名冊常帶伴隨值）
    ):
        assert expected in got, f"模組層 list literal 內的 {expected!r} 未被掃出，實得 {sorted(got)}"
    # 單一前導點不得被誤當成 `..` 逃逸擋掉（`.github/`／`.claude/` 是合法 repo 相對路徑）
    assert _looks_like_repo_relative_path(".github/workflows/autoclaude-ci.yml")
    assert not _looks_like_repo_relative_path("../outside.md")


def test_live_docs_registry_consumers_are_detected():
    """盲區 H 端到端：真實名冊的三份代表必須出現在 tools/tests 的消費集合裡。

    上一條驗解析器、本條驗「接到真實 repo 上仍然有效」——解析器對得起自己卻沒被接進
    `_consumed_root_paths()` 的話，覆蓋斷言照樣是恆真的（本鎖歷史上多次的失效形態）。
    """
    consumed = _consumed_root_paths(os.path.join(_monorepo_root(), "tools", "tests"))
    for rel in ("README.md", "useMacWin.md", "docs/AISDLC_Agent_UserGuide.md"):
        assert rel in consumed, (
            f"{rel} 是 test_doc_env_prefix_platform_parity_r60.py::_LIVE_DOCS 的成員"
            f"（磁碟上存在），卻不在消費集合內——盲區 H 掃描器未被接進 _consumed_root_paths()"
        )


@pytest.mark.parametrize("workflow_filename", sorted(_WORKFLOW_TEST_DIRS))
def test_push_and_pr_paths_symmetric(workflow_filename):
    push, pr = _workflow_paths(workflow_filename)
    assert push == pr, (
        f"{workflow_filename}: push 與 pull_request paths 不對稱（單側漏補）：{push} vs {pr}"
    )


def test_known_consumers_detected():
    """正則退化防呆：已知消費檔必被掃出，否則本鎖形同虛設。"""
    consumed: set[str] = set()
    for directory in _WORKFLOW_TEST_DIRS.values():
        consumed |= _consumed_root_paths(directory)
    expected = {
        "tools/check_ntfs_paths.py",
        "tools/git-hooks/pre-commit",
        ".claude/settings.json",
        "AutoClaude/.claude/settings.json",
        ".claude/hooks/sdd_hook_router.py",
        # S26：import-based BFS 新增偵測（見上方檔頭 S26 說明）
        "tools/check_hooks_liveness.py",
        "tools/check_defect_log_crossref.py",
        "tools/check_wrapper_thinness.py",
        "tools/_stdio_utf8.py",  # 經 check_hooks_liveness.py 等三檔遞移 import 偵得
        # R19 修復包 A 盲區 A：test_platform_utils_dedup.py 的
        # `sys.path.insert(0, ...parents[1] / "lib")` 動態解析偵得
        "tools/lib/platform_utils.py",
        # R67 round 2：`AISDLC_SDD/conftest.py`——掃描器**一直看得見**它
        # （test_subprocess_encoding_hygiene.py 以 `_REPO_ROOT / "AISDLC_SDD" /
        # "conftest.py"` 消費，`_SLASH_RE` 命中），卻被 `test_all_root_consumers_
        # covered_by_ci_paths()` 舊有的 `AISDLC_SDD/` 前綴豁免在最後一步扔掉。
        # 釘進本表＝鎖住「掃描面看得見它」這半邊，與豁免拆除那半邊互補。
        "AISDLC_SDD/conftest.py",
        # R67 盲區 E（本鎖失明的那一支）：R66 SSOT `tools/lib/sdd_latest.py`，其 10 支
        # 消費者一律用變數形態 `sys.path.insert(0, str(_REPO_ROOT / "tools" / "lib"))`
        # ——舊 `_SYSPATH_PARENTS_RE` 逐字正則零命中、此表亦未登記，兩道防線同時無訊號
        # 才讓雙 compat-CI paths 缺列假綠存活。改 AST 解析後偵得；同步釘進本表，
        # 使「解析器再退化回只認 inline 形態」當場紅（見檔頭 R67）。
        "tools/lib/sdd_latest.py",
        # 盲區 G（`from <套件> import <模組>`）：舊 `_FROM_IMPORT_RE` 只取 `from` 後第一段
        # 名稱 `lib`，找不到 `lib.py` 就靜默丟棄。這兩支被 `from lib import …` 消費的 SSOT
        # 因此隱形（baseline_origin：tools/tests/test_doc_loc_baseline_freshness_r60.py ＋
        # tools/sync_onboarding_baselines.py；defect_ledger_index：tools/archive_defect_log.py
        # ＋ tools/check_defect_log_crossref.py）。改 AST 解析後偵得。
        "tools/lib/baseline_origin.py",
        "tools/lib/defect_ledger_index.py",
        # 盲區 G 附帶揭露：`from autoclaude.execution.pre_run_validator import
        # _is_windows_apps_alias_stub`（tools/tests/test_windowsapps_guard_cross_consistency.py）
        # ——舊正則吃不到點狀套件路徑的第二段起，這支被直接斷言行為的檔一直缺席雙邊 paths。
        "AutoClaude/autoclaude/execution/pre_run_validator.py",
        # 盲區 G 附帶揭露：`from scripts import sdd_version`（AISDLC_SDD/scripts/tests/ 下
        # 20 支測試的慣用法，靠 ci-gate 的 `cd AISDLC_SDD` 讓 cwd 進 sys.path）——舊「自身
        # 目錄＋父目錄」兩層寫死候選解不到第三層祖先，改逐層向上後偵得。
        "AISDLC_SDD/scripts/sdd_version.py",
        # 盲區 H（模組層 list literal 內的相對路徑字串）：
        # tools/tests/test_doc_env_prefix_platform_parity_r60.py::_LIVE_DOCS 名冊成員。
        "README.md",
        "useMacWin.md",
        "docs/AISDLC_Agent_UserGuide.md",
    }
    missing = expected - consumed
    assert not missing, f"掃描器漏抓已知消費檔（正則退化）：{missing}"


@pytest.mark.parametrize("workflow_filename", sorted(_WORKFLOW_TEST_DIRS))
def test_all_root_consumers_covered_by_ci_paths(workflow_filename):
    """消費檔 ⊆ 該 workflow 自己的 paths。

    R67 round 2：拆掉此處原有的 `not p.startswith("AISDLC_SDD/")` 前綴豁免。該豁免的
    理由（「由 `AISDLC_SDD/**` 天然覆蓋」）**只對 aisdlc-sdd-ci.yml 成立**；
    macos／windows-compat-ci.yml 的 AISDLC_SDD 白名單只有四條子路徑，於是落在那四條
    之外的消費檔會被本鎖**主動丟棄**——`AISDLC_SDD/conftest.py` 就是這樣在掃描器看得見
    的情況下逃掉的（詳見檔頭 R67 round 2）。判準改為「一律拿該 workflow 自己的 paths
    比對」：對 aisdlc-sdd-ci.yml 而言 `AISDLC_SDD/**` 照樣一條命中，行為不變；對兩支
    compat-CI 而言不再有免驗的整片子樹。
    """
    push, _ = _workflow_paths(workflow_filename)
    tests_dir = _WORKFLOW_TEST_DIRS[workflow_filename]
    uncovered = [
        p
        for p in sorted(_consumed_root_paths(tests_dir))
        if not any(fnmatch.fnmatch(p, pat) for pat in push)
    ]
    assert not uncovered, (
        f"根層消費檔未列入 {workflow_filename} paths"
        f"（只改該檔時其回歸鎖不會跑，DEF-101-042 同構）：{uncovered}"
    )


# --- root-infra-ci.yml 專屬機械鎖（S12 / DEF-101-068(a)）---------------------------
# root-infra-ci.yml 刻意不設 paths 過濾，上方 _workflow_paths()/_consumed_root_paths()
# 一套「消費檔 ⊆ paths」正則對它不適用（沒有 paths 可比對）。以下改針對它真正的
# 同構風險（掃描根目錄清單而非觸發 paths 清單）另立專屬檢核，見檔頭 S12 說明。

_ROOT_INFRA_CI_PATH = os.path.join(_WORKFLOWS_DIR, "root-infra-ci.yml")

# py_compile 步驟只掃描根層 tools/（R56 修正：bash -n 已擴為全庫 tracked *.sh，
# 見 root-infra-ci.yml 第 1 道；原註解「bash -n／py_compile 兩步驟只掃描根層 tools/」
# 在 R56 擴面後已成半真）。豁免依據（R56 修正）：`.sh` 已由 root-infra-ci 第 1 道
# 全庫 bash -n 覆蓋；`.py` 之豁免依據為 AutoClaude ruff/pytest 與 AISDLC_SDD ci-gate
# （.claude/hooks/sdd_hook_router.py 另受 windows-compat-ci.yml／aisdlc-sdd-ci.yml
# paths 覆蓋，見 test_known_consumers_detected 已驗證）。原註解「各自已有獨立 CI
# ……覆蓋其 .sh」已被 R56 實查證偽（兩子專案 hook 皆不含 bash -n，委派鏈是空的），
# 勿再援引「子專案 hook 把關」作為 .sh 的豁免理由。
# 其餘任何根層 .sh／.py 若不在 tools/ 之下即為無主腳本。
_ROOT_INFRA_SCAN_EXEMPT_PREFIXES = ("AutoClaude/", "AISDLC_SDD/", ".claude/", "tools/")


def _git_ls_files(pathspec: str) -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "--", pathspec],
        cwd=_monorepo_root(),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    )
    return [line for line in result.stdout.splitlines() if line]


def test_root_infra_ci_has_no_paths_filter():
    """鎖死 root-infra-ci.yml「刻意不設 paths 過濾」的設計決策（見該檔頭註解）。

    NTFS 敵意檔名閘必須對任何路徑的新增檔案生效，paths 白名單天生必留盲區，
    故此 workflow 唯一安全做法是不設 paths（每次 push/PR 全跑，皆為輕量步驟，
    成本可忽略）。若日後有人「比照其餘三份 workflow」補上 paths 清單，會
    重新引入本測試檔案存在的目的正要根除的假綠盲區——只改被排除路徑時，
    NTFS 閘／腳本語法閘就不會跑。本鎖鎖死此決策，防止被誤「補全」。
    """
    with open(_ROOT_INFRA_CI_PATH, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    on = data.get("on") or data.get(True)
    push = on.get("push") or {}
    pull_request = on.get("pull_request") or {}
    assert "paths" not in push, (
        "root-infra-ci.yml 的 push 觸發不應設 paths 過濾"
        "（NTFS 敵意檔名閘需對任何路徑生效，見該檔頭註解；補 paths 會重新引入假綠盲區）"
    )
    assert "paths" not in pull_request, (
        "root-infra-ci.yml 的 pull_request 觸發不應設 paths 過濾（理由同 push，見上）"
    )


# --- 執行期子行程消費（盲區 B，R19 修復包 A）---------------------------------------
# AutoClaude/tools/run_act_core.py 完全不被 tools/tests/ 下任何測試檔以 import 或
# 路徑字串引用——它是被 run_act.sh/.ps1 以「子行程呼叫殼腳本」方式消費，測試測的是
# 黑盒殼腳本行為（subprocess 呼叫 shell script），而非直接 import 核心邏輯。這類
# 「執行期子行程消費」關係，上方 `_scan_import_consumed_paths()` 的靜態正則 import-BFS
# 結構上永遠看不到——與盲區 A 不同性質（盲區 A 是解析器猜測範圍不夠，這裡是掃描器
# 方法論邊界），故不再對此加新正則規則（過去 S6→S12→S26 三輪皆是加新正則打地鼠），
# 改用顯式清單 + 機械斷言其被對應 workflow 的 push+pull_request paths 覆蓋
# （fail-loud：檔案不存在或未被覆蓋即讓本測試紅），手法仿照上方
# test_known_consumers_detected() 的 expected 顯式集合。
# R32 Scan-B 訂正：tools/bootstrap_core.py 已於 R31（DEF-101-281）新增
# tools/tests/test_bootstrap_core.py 直接 import 之，不再是「執行期子行程消費」，
# 已被上方 `_scan_import_consumed_paths()` 一般掃描器自動涵蓋，故自本清單移除；
# 僅 run_act_core.py 仍屬此盲區（見 DEF-101-286 待補測試）。
# R69（終審 P1，DEF-101-721 續）：`AutoClaude/.loc_baseline` 於本輪被補進兩支 compat-CI
# 的 push+PR 共 4 個 paths 區塊，卻**沒有任何機械物看守它繼續存在**——實測把那 4 條刪光，
# 本檔 34 支全綠、零訊號（正是 DEF-101-042 假綠的同一形態，只是這次發生在「已補上的
# 條目會不會被後人刪掉」這一面）。
# 它確實有根層消費者，且屬盲區 B 而非盲區 A：`tools/tests/test_doc_loc_baseline_freshness_r60.py`
# 的 `measure_adr_loc_live()` **刻意不直接讀這支檔**（該函式 docstring 逐字寫明理由），
# 而是以子行程跑 `AutoClaude/tools/check_loc_budget.py --json`，由該工具去讀 `.loc_baseline`
# 並回吐 `baseline=`，再與 ADR 內的 `baseline=` token 逐字比對 ⇒ 靜態 import-BFS 與路徑
# 字面正則對它結構上零訊號。實測（R69，macOS）：把 `.loc_baseline` 由 17032 改為 17033，
# `TestR69AdrMeasurementTokensAreLive::test_real_adrs_carry_no_unreproducible_measurement_token`
# 由 OK 轉 FAILED（`baseline=17032 與現查值 17033 不符`）⇒ **只改這一支檔就能讓 compat-CI
# 內的根層測試轉紅**，故它必須在兩支 compat-CI 的 paths 內，否則該場景下閘門恰好不跑。
# ⇒ 這也就地否決了「它是無消費端的殘留項、應改為消去消費面」那條替代解：消費面是活的。
_KNOWN_SUBPROCESS_ONLY_CONSUMERS: dict[str, tuple[str, ...]] = {
    "AutoClaude/tools/run_act_core.py": ("macos-compat-ci.yml", "windows-compat-ci.yml"),
    "AutoClaude/.loc_baseline": ("macos-compat-ci.yml", "windows-compat-ci.yml"),
}


def test_known_subprocess_only_consumers_covered_by_ci_paths():
    """盲區 B 機械鎖：見上方 _KNOWN_SUBPROCESS_ONLY_CONSUMERS 說明。"""
    for rel_path, workflow_filenames in _KNOWN_SUBPROCESS_ONLY_CONSUMERS.items():
        abs_path = os.path.join(_monorepo_root(), rel_path)
        assert os.path.isfile(abs_path), (
            f"{rel_path} 不存在（已改名/搬移？）— _KNOWN_SUBPROCESS_ONLY_CONSUMERS "
            "顯式清單須同步更新，否則本鎖名不符實"
        )
        for workflow_filename in workflow_filenames:
            push, pr = _workflow_paths(workflow_filename)
            for label, paths in (("push", push), ("pull_request", pr)):
                assert any(fnmatch.fnmatch(rel_path, pat) for pat in paths), (
                    f"{rel_path}（執行期子行程消費，靜態 import-BFS 結構上看不到）"
                    f"未被 {workflow_filename} 的 {label} paths 覆蓋"
                )


# --- git ls-files glob 動態掃描消費（盲區 C，R50）---------------------------------
# tools/tests/test_windowsapps_guard_cross_consistency.py 用 `_tracked_files(pattern)`
# （`git ls-files -- pattern`）動態掃描全部 git 追蹤檔案，而非靜態字面路徑引用或
# import 陳述式——上方 `_scan_dir_for_root_paths()`／`_scan_import_consumed_paths()`
# 兩種偵測機制對此結構性零訊號（見檔頭 R50 說明），連盲區 B 的手動登記清單都沒有。
# 比照盲區 B（`_KNOWN_SUBPROCESS_ONLY_CONSUMERS`）手法：顯式登記「哪個測試檔＋
# 掃描哪個 glob pattern」，再對其*動態即時*執行 `git ls-files -- pattern` 取得的
# 真實結果（非寫死清單，隨檔案新增/刪除自動同步）逐一機械斷言被對應 workflow 的
# push+pull_request paths 覆蓋。與盲區 B 不同：盲區 B 登記的是固定檔名，本清單登記
# 的是「測試檔＋pattern」，覆蓋範圍隨 git 追蹤狀態自動變動，不需要每次新增/刪除
# 符合 pattern 的檔案時手動同步清單內容（只有 pattern 本身或消費它的測試檔改名時
# 才需要同步）。
_KNOWN_GLOB_SCAN_CONSUMERS: dict[str, tuple[str, tuple[str, ...]]] = {
    "tools/tests/test_windowsapps_guard_cross_consistency.py": (
        "*.ps1",
        ("macos-compat-ci.yml", "windows-compat-ci.yml"),
    ),
}


def test_known_glob_scan_consumers_covered_by_ci_paths():
    """盲區 C 機械鎖：見上方 _KNOWN_GLOB_SCAN_CONSUMERS 說明。"""
    for rel_test_path, (pattern, workflow_filenames) in _KNOWN_GLOB_SCAN_CONSUMERS.items():
        abs_test_path = os.path.join(_monorepo_root(), rel_test_path)
        assert os.path.isfile(abs_test_path), (
            f"{rel_test_path} 不存在（已改名/搬移？）— _KNOWN_GLOB_SCAN_CONSUMERS "
            "顯式清單須同步更新，否則本鎖名不符實"
        )
        with open(abs_test_path, encoding="utf-8") as f:
            src = f.read()
        assert f'"{pattern}"' in src or f"'{pattern}'" in src, (
            f"{rel_test_path} 原始碼已不含 glob pattern {pattern!r}（改名/改寫？）"
            "——_KNOWN_GLOB_SCAN_CONSUMERS 顯式清單須同步更新，否則本鎖名不符實"
        )
        # R67 round 2：此處原同樣排除 `AISDLC_SDD/` 前綴（理由與
        # test_all_root_consumers_covered_by_ci_paths() 同源，同樣是錯的——見檔頭
        # 訂正段）。一併拆除；實測拆除後 `*.ps1` 在 AISDLC_SDD/ 下的 122 支全部命中
        # 兩支 compat-CI 既有 pattern（`AISDLC_SDD/scripts/**`／`v*/tools/**`／
        # windows 側 `**/*.ps1`），本鎖仍綠——但從此**是驗過才綠**，不是被扔掉才綠。
        matched = _git_ls_files(pattern)
        for workflow_filename in workflow_filenames:
            push, pr = _workflow_paths(workflow_filename)
            for label, paths in (("push", push), ("pull_request", pr)):
                uncovered = [
                    rel for rel in matched if not any(fnmatch.fnmatch(rel, pat) for pat in paths)
                ]
                assert not uncovered, (
                    f"{rel_test_path} 以 `_tracked_files({pattern!r})`（git ls-files "
                    "glob 動態掃描，靜態 import-BFS／路徑字面正則結構上看不到，盲區 C）"
                    f"消費的檔案未被 {workflow_filename} 的 {label} paths 覆蓋：{uncovered}"
                )


# --- self._REPO 字面路徑消費（盲區 D，R52）---------------------------------------
# tools/tests/test_dev_start.py 的 TestNightlyHeartbeatFilenameContract 用
# `self._REPO / "AutoClaude" / "tools" / "run_local_nightly.sh"`（class 屬性
# `_REPO = Path(dev_start.__file__).resolve().parents[1]`，非字面 token
# `REPO_ROOT`／`_monorepo_root()`）讀取原始碼做心跳契約錨點斷言——上方
# `_JOIN_RE`／`_SLASH_RE` 只認得字面 token `REPO_ROOT`／`_monorepo_root()`，對
# 這種 class 屬性間接消費慣用法結構上零訊號（R52 四方複審實測揪出：
# windows-compat-ci.yml 漏列此檔案、本鎖 11 passed 未攔截）。與盲區 B／C 性質
# 相同（掃描器方法論邊界，非解析器猜測範圍不夠），比照同一手法：顯式登記
# 「檔案 + 消費它的來源檔」+ 機械斷言消費關係仍存在（防登記腐化）＋覆蓋
# workflow paths。
#
# R53（Architect/SA/SD/QA 交叉發現）：同一支消費檔 `test_dev_start.py` 內用完全
# 相同手法（`self._REPO` 或其 class 屬性 `_REPO`）另外讀取了
# `run_local_nightly.ps1`（`TestNightlyHeartbeatFilenameContract
# .test_windows_reader_filename_matches_ps1_writer`）與 `install_mac_nightly.sh`
# （`TestNightlyHeartbeatFilenameContract.test_installer_third_site_filename_
# and_threshold`／`TestCrossSiteLiteralLocks._installer_text`／
# `TestNightlyHeartbeatCrossSiteBehavioralEquivalence._INSTALLER`，橫跨 3 個
# 測試類）卻未登記，R52 只補了 `run_local_nightly.sh` 一筆。`tools/tests/` 同時
# 被 windows-compat-ci.yml／macos-compat-ci.yml 兩份 workflow 執行（見
# `_WORKFLOW_TEST_DIRS`），故兩檔皆須登記兩份 workflow：`run_local_nightly.ps1`
# 現行由 windows 側 `**/*.ps1` 萬用字元＋macos 側明列覆蓋，`install_mac_nightly.sh`
# 現行由 macos 側 `**/*.sh` 萬用字元＋windows 側明列覆蓋——雙重覆蓋非巧合免驗證
# 的理由，仍須機械鎖住，否則任一側覆蓋機制被移除即靜默失效。
_KNOWN_LITERAL_PATH_CONSUMERS: dict[str, tuple[str, tuple[str, ...]]] = {
    "AutoClaude/tools/run_local_nightly.sh": (
        "tools/tests/test_dev_start.py",
        ("windows-compat-ci.yml",),
    ),
    "AutoClaude/tools/run_local_nightly.ps1": (
        "tools/tests/test_dev_start.py",
        ("windows-compat-ci.yml", "macos-compat-ci.yml"),
    ),
    "tools/install_mac_nightly.sh": (
        "tools/tests/test_dev_start.py",
        ("windows-compat-ci.yml", "macos-compat-ci.yml"),
    ),
}


def test_known_literal_path_consumers_covered_by_ci_paths():
    """盲區 D 機械鎖：見上方 _KNOWN_LITERAL_PATH_CONSUMERS 說明。"""
    for rel_path, (consumer_rel_path, workflow_filenames) in _KNOWN_LITERAL_PATH_CONSUMERS.items():
        abs_path = os.path.join(_monorepo_root(), rel_path)
        assert os.path.isfile(abs_path), (
            f"{rel_path} 不存在（已改名/搬移？）— _KNOWN_LITERAL_PATH_CONSUMERS "
            "顯式清單須同步更新，否則本鎖名不符實"
        )
        abs_consumer_path = os.path.join(_monorepo_root(), consumer_rel_path)
        assert os.path.isfile(abs_consumer_path), (
            f"{consumer_rel_path} 不存在（已改名/搬移？）— _KNOWN_LITERAL_PATH_CONSUMERS "
            "顯式清單須同步更新，否則本鎖名不符實"
        )
        with open(abs_consumer_path, encoding="utf-8") as f:
            consumer_src = f.read()
        basename = rel_path.rsplit("/", 1)[-1]
        assert basename in consumer_src, (
            f"{consumer_rel_path} 原始碼已不含 {basename!r}（改名/改寫？）"
            "——_KNOWN_LITERAL_PATH_CONSUMERS 顯式清單須同步更新，否則本鎖名不符實"
        )
        for workflow_filename in workflow_filenames:
            push, pr = _workflow_paths(workflow_filename)
            for label, paths in (("push", push), ("pull_request", pr)):
                assert any(fnmatch.fnmatch(rel_path, pat) for pat in paths), (
                    f"{rel_path}（`self._REPO` 等非字面 REPO_ROOT/_monorepo_root() "
                    f"token 間接消費，靜態正則看不到，盲區 D）未被 {workflow_filename} "
                    f"的 {label} paths 覆蓋"
                )


# --- pytest 隱式載入的 rootdir conftest（盲區 F，R67 round 2）---------------------
# `conftest.py` 由 pytest 依 rootdir **自動載入**，結構上不會出現在任何 CI step 的
# 命令列、也不被任何測試 import ⇒ 上方兩套掃描器同時零訊號（見檔頭 R67 round 2）。
# 依 R54 收斂門檻**不再新增第 4 份手寫登記字典**，改用程式化反向驗證：直接向 git 要
# 「repo 內全部 conftest.py」，逐一斷言被兩支 compat-CI 的 paths 覆蓋。
#
# 為何是這兩支 workflow：`tools/tests/` 由它們執行（見 `_WORKFLOW_TEST_DIRS`），且兩者
# 各自都會實跑 AutoClaude pytest ＋ `AISDLC_SDD/scripts/ci-gate.sh`（v0.01／LATEST 雙軌
# ＋ scripts/tests）＋ LATEST `tools/fsm_runtime/tests` ⇒ repo 內任何一支 conftest 的
# 改動都可能改變它們的收集/回報結果。aisdlc-sdd-ci.yml 不納入本鎖：它已有 `AISDLC_SDD/**`
# 一條全覆蓋，而 `AutoClaude/**` 下的 conftest 不在它的執行面內（納入只會逼出一條假需求）。
_FAMILY_COVERAGE_WORKFLOWS: tuple[str, ...] = ("macos-compat-ci.yml", "windows-compat-ci.yml")

# 家族鍵 → (git pathspec, 成員數下限, 必須被列舉到的活體代表, WHY)。
#
# 這兩個家族的共通點，也是它們同時逃過上方全部掃描器的原因：**成員身分不是靠某個
# 檔案「提到」它建立的**——conftest 由 pytest 依 rootdir 隱式載入、歸檔帳本由
# `tools/check_defect_log_crossref.py` 在執行期 `glob()` 掃進來——於是無論解析器多聰明，
# 掃「命令列字面」或「import 陳述式」都不可能看見它們。故一律改由 git **即時列舉**：
# 成員隨檔案新增/刪除自動同步，不需要有人記得維護清單（與盲區 C 的
# `_KNOWN_GLOB_SCAN_CONSUMERS` 同一理念，但連「登記哪個測試檔」都不需要）。
_GIT_ENUMERATED_FAMILIES: dict[str, tuple[str, int, tuple[str, ...], str]] = {
    "pytest-rootdir-conftest": (
        "*conftest.py",
        5,
        ("AISDLC_SDD/conftest.py", "AISDLC_SDD/AISDLC_SDD_v0.30/conftest.py"),
        "pytest 依 rootdir 隱式載入；能改變整套測試的收集與回報（collect_ignore／fixture／"
        "pytest_terminal_summary）。兩支 compat-CI 各自都實跑 AutoClaude pytest ＋ "
        "AISDLC_SDD/scripts/ci-gate.sh（v0.01／LATEST 雙軌＋scripts/tests）＋ LATEST "
        "fsm_runtime pytest ⇒ 任一支 conftest 的改動都可能改變它們的結果。",
    ),
    "defect-log-archive": (
        "docs/06_quality/AutoSDD_Defect_Log_archive_*.md",
        2,
        ("docs/06_quality/AutoSDD_Defect_Log_archive_02.md",),
        "tools/check_defect_log_crossref.py::main() 以 "
        "`_DEFECT_LOG.parent.glob(\"AutoSDD_Defect_Log_archive_*.md\")` 執行期掃描全部歸檔"
        "（量大小上限、驗歸檔索引 bullet），而 tools/tests/test_check_defect_log_crossref.py::"
        "TestMain::test_main_against_real_repo_is_clean 就是拿**真實 repo** 跑那支 main()；"
        "tools/tests/test_ntfs_trailing_space_device_name.py 另以迴圈變數 `REPO_ROOT / rel` "
        "讀 archive_02（`_SLASH_RE` 只認字面字串，對迴圈變數零命中）。主檔 "
        "`docs/06_quality/AutoSDD_Defect_Log.md` 早已列入 paths，歸檔卻沒有——同一支鎖的"
        "輸入被切成「有觸發的一半」與「沒觸發的一半」。",
    ),
}


def _git_enumerate(pathspec: str) -> list[str]:
    """依 git pathspec 列舉：tracked ＋ **未被 .gitignore 排除的 untracked**。

    🔴 untracked 那半邊不是可選項：本輪出事的三支新檔（`AISDLC_SDD_v0.30/conftest.py`、
    `AutoSDD_Defect_Log_archive_38.md`／`_39.md`）在四方複審當下全部是 untracked。只認
    `git ls-files` 等於把訊號延後到 commit 之後，而 pre-commit 正是在 commit **之前**跑
    ——那時本鎖看不到它，就等於整輪都不會紅（本輪原地復發的機制之一）。
    """
    tracked = _git_ls_files(pathspec)
    result = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard", "--", pathspec],
        cwd=_monorepo_root(),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    )
    untracked = [line for line in result.stdout.splitlines() if line]
    return sorted(set(tracked) | set(untracked))


@pytest.mark.parametrize("family", sorted(_GIT_ENUMERATED_FAMILIES))
def test_git_enumerated_families_have_discriminating_power(family):
    """列舉器自證：抓不到東西的列舉器會讓下方覆蓋斷言**恆真**（同 `_MIN_*` 下限釘選慣例）。

    另釘住「必須被列舉到的活體代表」：conftest 家族的兩支代表一支 tracked、一支（本輪）
    untracked，正好各驗一條取得路徑——`--others` 那半邊被拆掉時本測試當場紅。
    """
    pathspec, floor, required, _why = _GIT_ENUMERATED_FAMILIES[family]
    found = _git_enumerate(pathspec)
    assert len(found) >= floor, (
        f"[{family}] pathspec {pathspec!r} 只列舉到 {len(found)} 個成員 < 下限 {floor}"
        f"——疑似 pathspec 漂移（0 命中會讓覆蓋斷言恆成立而靜默假綠）：{found}"
    )
    for rel in required:
        assert rel in found, (
            f"[{family}] 列舉器抓不到活體代表 {rel}——tracked／untracked 兩條取得路徑之一"
            f"失效，下方覆蓋斷言會對它恆真（實得 {len(found)} 個成員）"
        )


@pytest.mark.parametrize("workflow_filename", _FAMILY_COVERAGE_WORKFLOWS)
@pytest.mark.parametrize("family", sorted(_GIT_ENUMERATED_FAMILIES))
def test_git_enumerated_families_covered_by_ci_paths(family, workflow_filename):
    """盲區 F 機械鎖：家族每一名成員都必須被兩支 compat-CI 的 push＋PR paths 覆蓋。

    WHY（Rule 9 — 測意圖）：這兩個家族的成員是**承重檔**（一個決定「測試到底收集了什麼、
    印了什麼」，一個是跨參照鎖的真實輸入），卻都不會出現在任何 step 的命令列或 import
    陳述式裡。只改它們時 compat-CI 不被觸發 ⇒ 守著它們的鎖恰好不跑（DEF-101-042 同構）。
    R67 的 `AISDLC_SDD/AISDLC_SDD_v0.30/conftest.py` 是活體案例：它是 R67-F27
    「[WINDOWS-NATIVE-ONLY] skip 可見度」在官方閘門實際走的那條路徑上的**唯一**載具，
    拆掉它兩支 compat-CI 都不會被觸發、該機制靜默消失。

    aisdlc-sdd-ci.yml 刻意不納入：它已有 `AISDLC_SDD/**` 一條全覆蓋，而 `AutoClaude/` 與
    `docs/` 下的成員不在它的執行面內，納入只會逼出一條假需求。
    """
    pathspec, _floor, _required, why = _GIT_ENUMERATED_FAMILIES[family]
    members = _git_enumerate(pathspec)
    push, pr = _workflow_paths(workflow_filename)
    for label, paths in (("push", push), ("pull_request", pr)):
        uncovered = [rel for rel in members if not any(fnmatch.fnmatch(rel, pat) for pat in paths)]
        assert not uncovered, (
            f"[{family}] 成員未被 {workflow_filename} 的 {label} paths 覆蓋：{uncovered}\n"
            f"  這一族為何是承重檔：{why}\n"
            f"  處置：在該 workflow 的 push ＋ pull_request 兩個 paths 區塊各補一條；"
            f"版本樹複本請用 `AISDLC_SDD/AISDLC_SDD_v*/conftest.py` 這類萬用字元，讓 "
            f"Copy-on-Evolve 傳播出的下一版自動涵蓋，別留給下一輪再漏一次"
        )


def test_root_infra_ci_bash_and_py_scan_roots_have_no_stray_scripts():
    """root-infra-ci.yml 的 py_compile 步驟只掃描根層 tools/（R56 修正：bash -n
    已於 R56 擴為全庫 tracked *.sh，見該 workflow 第 1 道；本 docstring 首行原作
    「bash -n／py_compile 步驟只掃描根層 tools/」，擴面後已成半真故訂正）。

    若日後在 monorepo 根新增另一個含 .sh／.py 腳本、且不屬於 AutoClaude/、
    AISDLC_SDD/、.claude/ 的目錄，該目錄會完全逃過 root-infra-ci 的守門而不自知
    ——與 DEF-101-042／DEF-101-068(a) 同一類「消費者存在但守門忘了看它」缺陷，
    只是發生在掃描根目錄清單而非觸發 paths 清單。本鎖機械斷言：git 追蹤的全部
    .sh／.py 檔，扣除上述三個有獨立覆蓋的子專案／目錄後，必須全部落在 tools/
    之下。豁免依據見 `_ROOT_INFRA_SCAN_EXEMPT_PREFIXES` 上方註解（R56 修正：
    `.sh` 靠第 1 道全庫 bash -n、`.py` 靠 AutoClaude ruff/pytest 與 AISDLC_SDD
    ci-gate；「子專案 hook 把關 .sh」已被 R56 實查證偽，勿再援引）。
    """
    for ext in (".sh", ".py"):
        tracked = _git_ls_files(f"*{ext}")
        stray = [
            p
            for p in tracked
            if not p.startswith(_ROOT_INFRA_SCAN_EXEMPT_PREFIXES)
        ]
        assert not stray, (
            f"發現不在 tools/ 下、也不屬於 AutoClaude/／AISDLC_SDD/／.claude/ 的根層"
            f"{ext} 腳本，root-infra-ci.yml 的語法守門盤點不到"
            f"（.py 之 py_compile 只掃 tools/；.sh 雖已由第 1 道全庫 bash -n 覆蓋，"
            f"仍一併鎖「無主目錄」以防新目錄逃過其餘守門）"
            f"（DEF-101-068(a) 同構盲區）：{stray}"
        )
