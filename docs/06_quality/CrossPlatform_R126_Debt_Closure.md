# R126 落地輪 — 缺陷結案存證

> **性質**：技術債總清償循環令 v2 第一投（2026-09-04）。R125 交棒書已明言「重跑指令就綠」的
> 低垂果子摘完，本輪改為**落地輪**：對 R121 裁決包已選定方向、帳本列仍 open 的 needs-dev 項
> 真的動手實作，過四方定點複審後結案；另順手清掉數筆「只差一支鎖／一段程式」的小項。
> **帳本未結列**：起 49 → 訖見 `R126_HANDOFF.md`（本檔逐節記各筆的落地取證；帳本列只放索引，
> 依 Playbook §4.6）。
> **護欄層**：淨額見 `_GUARD_LINES_REPIN_LOG` 的 R126 列與 `--print-guard-lines` 現查；本輪
> 淨額為正（回歸鎖落地），款(11) 連續上升計數自 R123 起為第二輪 ⇒ 下一結案窗口的淨額必須 ≤ 0。
> **體例**：不使用「延後到R／交給R／留給R／承接輪次：R」等前瞻輪號句型；轉述並行包交件一律標
> `[他包回報]`，主控親跑者不標。所有數字皆為本 session 親跑 tool_result。

---

## §0 方法與防互踩

1. 唯讀分診沿用 R125 兩波 Workflow 的 journal（本機暫存）作為候選來源，本輪不重新分診。
2. 四張需要設計裁決的卡（`DEF-200-241`／`DEF-200-137`／`DEF-200-244`／`DEF-200-243`）先寫成
   設計卡，派四方（Architect／SA／SD／QA，`model: sonnet`）**動碼前**複審；設計卡與複審結論
   摘要見 §D。其餘小項（803／257／951／217／263／248／172／247）不涉設計分歧，直接實作。
3. 全部程式碼與帳本編修由本單一窗口序列完成（鐵律七檢查表第 1 項）；並行包只做唯讀複審。
4. 每項落地皆附：改動座標、針對測試實跑輸出、突變／對照組如何驗紅。

---

## §DEF-101-803 零相依探針「守門失守」轉為具名 fail（R121 裁決方向 B）

**缺陷**：`tools/tests/test_run_root_unittests.py::ZeroDepEnvironmentDiscriminationTest` 的兩支
floor 探針今日不會真的跑整棵樹，只是因為 `MIN_TESTS` 餘裕恰好小於被封鎖相依帶走的測試數
——這是巧合不是結構保證；一旦守門失守，症狀是難以歸因的 `TimeoutExpired` error。

**落地**：兩支 floor 測試（`test_blocked_prereqs_reproduce_collection_collapse`／
`test_zero_dep_message_says_environment_not_disappearance`）各加一條
`assertNotIn("unittest 數量下限釘選通過", proc.stdout, …)`——整棵樹被跑起來時，會先印出這句
通過訊息，於是變成具名 fail。RED 依裁決卡以推理代替（無法安全注入 `MIN_TESTS` 造真紅）。

**驗證**：`pytest tools/tests/test_run_root_unittests.py -k ZeroDepEnvironmentDiscriminationTest -q`
→ `3 passed, 108 deselected`，rc=0。

## §DEF-200-257 `SentinelWiringTest` 正／負向等待時間具名並綁方向鎖

**缺陷**（R96 §F-①）：負向斷言 3 處 `8.0`、正向 1 處 `30.0`，兩個字面值彼此零判準——負向窗若短於
正向 spawn 的真實延遲，負向就會因「還沒來得及生出來」而假綠。

**落地**（`tools/tests/test_context_budget_guard.py`）：
- 具名常數 `_SENTINEL_ARM_WAIT_S = 30.0`／`_SENTINEL_NO_ARM_WAIT_S = 8.0`／
  `_SENTINEL_SPAWN_SAFETY_FACTOR = 3.0`，四個站點改用常數。
- 靜態方向鎖 `test_the_wait_windows_are_ordered`：`0 < NO_ARM < ARM`、安全係數 ≥ 1。
- 動態方向鎖：正向測試 `test_an_earned_session_actually_spawns_the_arming_run` 量出實測 spawn
  延遲，斷言 `延遲 × 安全係數 ≤ NO_ARM`——R96 候選修法「把正向延遲量出來當負向門檻的下界」
  的機械面（Windows 專屬路徑，其他平台照舊 skip）。

**驟證**：`pytest tools/tests/test_context_budget_guard.py -k SentinelWiringTest -q` →
`13 passed, 527 deselected in 28.58s`，rc=0（含新增的靜態鎖與動態鎖）。

## §DEF-101-951 compat-CI 四處 skip 模組清單 ↔ `tools/lib/*skip*.py` 根層同步鎖（R121 方向 B）

**缺陷**：skip 判準族被 LOC tier 切成 7 支 `tools/lib/*skip*.py`，清單在 windows-／macos-compat-ci
的 push／pull_request 各抄一份（4 處複本）；唯一看著它的鎖住 AISDLC_SDD 側，不在根層 unittest
閘門射程。新增 skip 模組漏列 paths 時根層零訊號（同位置實踩兩次）。

**落地**（`tools/tests/test_smoke_ci_sync.py`，不新增鎖檔——併入既有 workflow 同步鎖檔）：
`_paths_blocks()` 抽 workflow 內每個 `paths:` 清單塊（`paths-ignore:` 不算、註解不中斷塊、
縮排回退結束塊），`TestSkipModuleListsMirrorToolsLib` 斷言每一處含 skip 模組的塊其集合 ==
`tools/lib` 磁碟上 `*skip*.py` 集合；塊數下限 4（抽取式漂移不得靜默降級成假綠）；合成注入
（真塊刪一項 ⇒ 不等）與抽取式保真度（`paths-ignore`／註解／縮排）各一支。

**驗證**：`pytest tools/tests/test_smoke_ci_sync.py -k TestSkipModuleListsMirrorToolsLib -q` →
`3 passed, 29 deselected, 4 subtests passed`，rc=0（4 subtests＝4 處複本各自對上 7 支）。

## §DEF-200-217 E5：harness import 第三種洗白形態（`sys.path` ＋ 裸模組名）

**缺陷**（R100 §E-5）：`sys.path.insert(…"tools"/"lib")` ＋ `import quota_limits` 這種形態，
importlinter（grimp 解析不到）與既有 AST 判準（只看首段 ∈ {tools, _claude} 或含 `.claude`）
都看不到；帳本原記的阻擋因素 `DEF-200-208` 早已 fixed@R101，本項自解鎖後多輪無人補。
E1／E3／E4 已併入 `DEF-200-207`、E2 fixed@R116 ⇒ 本列只剩 E5。

**落地**（`AutoClaude/tests/test_r82_quota_axis_and_shipped_defaults.py`）：`_launders_sys_path()`
（AST：`sys.path.<insert|append|extend>(…)` 且引數字串常數含 `tools`／`.claude`）＋
`_harness_basenames()`（現查 `tools/`、`tools/lib/`、`.claude/hooks/` 的 `*.py` 基名，不寫死）；
`_harness_imports()` 在檔內有洗白路徑時，裸 import 首段命中基名集合即紅。合成注入
`test_the_judge_catches_sys_path_laundering`（含基名集合非空且含 `quota_limits` 的保真度斷言）
＋對照組 `test_a_bare_name_without_sys_path_laundering_is_not_flagged`（純裸名／無關路徑不誤判）。
`AutoClaude/.importlinter` no-harness-import 的〈誠實劃界〉補記第三形態。

**驗證**：`pytest tests/test_r82_quota_axis_and_shipped_defaults.py -q` → `97 passed`，rc=0；
ruff 對三支改動檔 `All checks passed!`。production 面現查 `autoclaude/` 零 `sys.path` 操弄站點，
故新判準對真倉庫零命中不是 vacuous——合成注入證明它會咬。

## §DEF-200-263 生產側 `setup_logger` 換 `log_dir` 不再靜默沿用舊握把

**缺陷**（R96 §F-⑧）：第二次以不同 `log_dir` 呼叫時 `if root.handlers: return root` 靜默沿用舊
`RotatingFileHandler`，`log_dir` 被無聲丟棄；測試側 `DEF-200-154` 修好後，唯一會讓它現形的
WinError 32 訊號也消失。

**落地**（`AutoClaude/autoclaude/utils/logger.py`）：新增 `_warn_if_log_dir_diverges()`——既有
file handler 的 `baseFilename` 不落在新 `log_dir` 底下時，以 WARNING 具名新舊目錄出聲一次；
**維持不重建握把**（重建會在 Windows 留未關閉舊檔柄、且讓多次匯入的呼叫端拿到不同 handler），
只把靜默改成 fail-loud。回歸鎖 `tests/test_logger.py::test_def_200_263_switching_log_dir_is_loud_not_silent`：
換目錄 ⇒ WARNING 含 `DEF-200-263` 且點名新舊兩目錄、新目錄不被建立；同目錄再呼叫 ⇒ 不出聲。
落地當回合抓到一筆自己的假紅：訊息用 `%r` 印路徑會把反斜線寫成雙反斜線、與 `str(path)` 對不上
⇒ 改 `%s`。

**驗證**：`pytest tests/test_logger.py -q` → `36 passed`，rc=0；`check_loc_budget.py` violations=0
（total 17246→17256，ONBOARDING §7 表① live 格已 `--write` 回填）。

## §DEF-200-248 `AISDLC_SDD/conftest.py` 反方向 skip 報表

**缺陷**（原 `DEF-101-856` ③）：AISDLC_SDD 側只彙整 `[WINDOWS-NATIVE-ONLY]`；在 Windows 上跑時
真正失去的覆蓋（他平台專屬 skip）零標籤／零摘要／零計數，「兩平台 skip 行為對齊」無從佐證。

**落地**：`AISDLC_SDD/conftest.py` 補 `POSIX_NATIVE_SKIP_TAG`／`MAC_NATIVE_SKIP_TAG`／
`NON_WINDOWS_SKIP_TAGS`（字面值比照 AutoClaude 側慣例各持一份，SSOT＝根層
`tools/lib/windows_skip_tags.py`）、純函式 `non_windows_native_skips()`、`pytest_terminal_summary`
補反方向區塊（標題以 `sys.platform` 動態組字）；LATEST 版本樹 `AISDLC_SDD_v0.30/conftest.py`
同步 re-export（`pytest_terminal_summary` 本就是同一支函式物件，版本樹 rootdir 自動生效）。
回歸鎖三支（`scripts/tests/test_conftest_windows_native_skip_report.py`）：正向點名、探針真跑則沉默、
雙向同時各自獨立區塊；既有三案例的收集數逐字不變（反方向探針以 `posix_tagged_skip=None` 不生成）。

**驗證**：`pytest scripts/tests/test_conftest_windows_native_skip_report.py -q`（rootdir=AISDLC_SDD）
→ `16 passed in 4.07s`，rc=0。落地當回合抓到一筆自己的假紅：fnmatch 樣式 `*1 * DEF-200-248*`
要求半形空格、實際輸出是全形括號 ⇒ 改 `*1 *DEF-200-248*`。

## §DEF-200-172 ③.3 根 `CLAUDE.md` 三軌表補列 R 系列

**殘留**：八子項中 ①⑤④⑥⑧ 已各自拆列（257／260／259／261／263）、②→258、⑦已修，本列只剩
③「帳本體例三筆」。③.1（插列位置）與 ③.2（分隔符空格體例混用）依 R121 裁決卡為
closed-by-decision：前者受 append-only 紀律保護不得搬動，後者 `_row_cells()` 對兩種寫法皆吃得下
（零機械後果）；③.3（R 系列未進根 `CLAUDE.md` 三軌表）為 doc-fix。

**落地**：根 `CLAUDE.md`〈三條改進軌道〉表新增「（附）跨平台整合輪 R 系列」一列——指明交棒書／
證據檔位置、驅動器（缺陷帳本＋循環令）、輪號取法（數字排序）。三軌表標題與鐵律段不動。

**驗證**：`pytest tools/tests/test_doc_loc_baseline_freshness_r60.py` 全檔（含幽靈路徑、hook 宣稱、
鐵律機械物盤點三向）——見 `R126_HANDOFF.md` 已驗證節的實跑輸出。

## §DEF-200-247 死碼 `verify_token_guard_e2e.py` 真的刪除

**缺陷**：R81（`LDG-S1-22`）與 R121 裁決包皆已判「零 production 消費者、刪除」，但實際刪除多輪
未執行（R125 交棒書以 `absent-if` 錨釘住這件事）。

**落地**：`git rm AutoClaude/tools/verify_token_guard_e2e.py AutoClaude/tests/tools/test_verify_token_guard_e2e.py`。
「同步 5 檔 7 處」逐面現查：`tools/check_script_parity.py` rc=0（.py 不在對等品登記面）；
`tools/check_pytest_baseline_sites.py` rc=0；全庫 `git grep verify_token_guard_e2e` 剩餘命中全在
docs／帳本／交棒書史料（不改寫歷史）；ONBOARDING §7 表② AutoClaude 測試樹指紋隨之變動，
以乾淨 venv `--write --with-slow` 回填（見 `R126_HANDOFF.md`）；全套第一跑另抓到
`test_platform_utils_dedup.py::_FROZEN_STDIO_FORCE_TREES` 的 `AutoClaude` 格須 24→23（該載具自帶
一處 stderr reconfigure）——R81 的估算沒點名這一面，本輪補齊。

**驗證**：`Test-Path` 兩檔皆 False；AutoClaude 針對測試與 LOC 閘門 rc=0。連鎖：兩份歷史交棒書
（R76／R125）以反引號指名該路徑屬當時為真的史料，不改寫；依 R99 判例把該路徑登記進
`_GHOST_PATH_BASELINE`（第二類「已刪除的孤兒腳本」）、天花板 18→19；ONBOARDING 表② 以全新乾淨
venv（`autoclaude_cleanvenv_20260904`，pgextras absent）`--write --with-slow` 回填：AutoClaude
4604 passed／175 skipped、ci-gate v0.01 1478／v0.30 1746／scripts 352，四棵樹指紋同步。

---

## §D 四張設計卡的四方動碼前複審（Architect／SA／SD／QA，`model: sonnet`，Workflow `wf_44dc4d34-d14`）

| 卡 | 標的 | Architect | SA | SD | QA | 落地時採納的條件 |
|---|---|---|---|---|---|---|
| D1 | DEF-200-241 | APPROVE | AWC | AWC | AWC | 回歸鎖類別**整個**改寫（三支依賴非空豁免表的既有方法會 StopIteration／vacuous）；`unresolved_only=True` 呼叫維持 main() 文字面第一個；`layout is None` 兩路徑一律不猜狀態 |
| D2 | DEF-200-137 | AWC（blocking） | AWC | APPROVE | APPROVE | 常數**進 `Policy`＋`ENV_SPEC`**、不變式 6 併入 `load_policy()` live fail-safe（非 quota_gate 裸常數）；設計卡「quota_policy.py 無空間」理由與現查 251/400 不符——**撤回該理由**；cbg 864-865 敘事註解同行數改字；kind 字面 belt-and-suspenders |
| D3 | DEF-200-244 | APPROVE | APPROVE | APPROVE | APPROVE | `excluded` 用 kind 差集去重；另開新增補檔（`PRD_Amendment_R126_GateExclusion.md`）而非就地改 Adopted 檔，Pacing 檔只加指針 |
| D4 | DEF-200-243 | AWC（blocking） | AWC（blocking） | AWC（blocking） | AWC（blocking） | 四方以真函式實測：純絕對門檻使 session（繼承 300）在剩 (150, 360] 分整段 far→mid（每個 5 小時窗後半、任何水位），經 `_pace_of()` 的 max 外溢成全域 rec 翻倍，並牴觸 R110 Q9(i) 接受的 A2=4 ⇒ **改採「與絕對門檻取較緊」**：只對自身文法解不出的軸，把完整 `effective_horizon()`（含 burn 分支）的結果與 window=None 的結果取 `tightest`；補 session 掃描式回歸鎖 |

D4-Q1 三份實算一致：`thresholds(300,30,360)=(30,150)` vs `thresholds(None,30,360)=(30,360)`；(151,360] 區間繼承版恆 far、純絕對恆 mid；`tightest` 版對 session 逐位元同今天、對 spend@504 分把 near 壓回 far。

---

## §DEF-200-241 交接載體判準的祖父化改讀「帳本結案事實」（R121 方向 B）

**缺陷**：`check_handoff_carriers.py` 判準② 的自動祖父化依賴「目標輪 < 當前輪」，而帳本「發現情境」欄零輪號紀律使 `current_round()` 凍結在 R100；歷史前瞻行指名的 DEF-ID 一旦結案就從承接載體集合消失 ⇒ 假陽性；DEF-200-212 時期以具名豁免表（5 筆、天花板 5、D8 明文不得再調高）過渡 ⇒ 任何被前瞻行指名的列都結不了案（`DEF-200-213` 實質已解卻卡住＝本列的死結）。

**落地**（`tools/check_handoff_carriers.py`）：
- `ledger_def_ids(..., resolved_only=True)`：帳本家族內狀態欄首詞分類 ∉ `_UNRESOLVED_CLASSES` 的 ID（fixed／closed-by-decision／wontfix／no_action_needed…）；與 `unresolved_only` 互斥（`ValueError`）；版面解析不到的家族成員兩條路徑一律不猜狀態、整份排除。
- `carrier_doc_problems(..., done_ids=)`：前瞻行指名的 ID 若已結 ⇒ 那件事真的做完了 ⇒ 出局，不比輪號、不讀時鐘、只讀狀態欄首詞分類。`main()` 先取 `known_ids`（`unresolved_only=True`，維持文字面第一個呼叫）再取 `done_ids`。
- 豁免表 `_CARRIER_DOC_EXEMPTIONS` 清空、`_CARRIER_DOC_EXEMPTIONS_MAX_ENTRIES` 5→0（shrink-only 方向）；機制與 `exemptions=` 注入口保留供合成表驗證。
- `--self-test` 新增〈祖父化改讀帳本結案事實〉七道（已結進 done／不進 known／partial 不進 done／版面解析不到不貢獻／查無列紅／已結綠／done 空退回原判準）並把〈具名豁免〉段改為合成表。
- 回歸鎖 `test_check_defect_log_crossref.py::TestDef200241GrandfatheringReadsLedgerClosureNotTheClock`（取代 `TestDef200212NamedExemptionsZeroOutTheKnownFalsePositives`）：真倉庫 strict＋done_ids 零假陽性；**拿掉 done_ids 時五筆舊假陽性座標逐筆復發**（新判準真的在承重）；表空天花板 0；合成語意四道；豁免機制三性質以合成表驗。
- 🔴 **落地當回合追加（超出設計卡射程、同一原則）**：帳本結案 13 筆後，真倉庫閘門在**判準①**（commit 訊息 → 帳本承接輪）轉紅——commit `0398226` 的「已列 R118 交棒書呈報裁決」段落指名 `DEF-200-212`，212／241 結案後帳本再無承接輪次 ≥ R118 的未結列，而時鐘凍結在 R100 使 `n < cur` 永不祖父化 ⇒ 「把事情做完」讓判準① 轉紅＝241 要治的同一個迴圈在①重演。修法同原則：`commit_carrier_problems(..., done_ids=)`，宣告所在**段落**（空行分隔）指名已結 DEF-ID 即出局；粒度取段落而非整則訊息，避免一個已結 ID 替同則訊息裡無關的延後背書。self-test 加兩道（段落出局／無 done 兩段皆紅）、回歸鎖 `test_commit_criterion_also_reads_closure_facts_per_paragraph`（真 commit 綠、拿掉 done 紅、合成無關段落仍紅）。此項在動碼前四方複審之後才發生，交由本輪程式碼定點複審第二審覆核。

**五筆退場豁免的原始理由（逐字保全，原住 `_CARRIER_DOC_EXEMPTIONS`）**：
1. `docs/04_planning/R102_HANDOFF.md`／`DEF-200-204`：「本行是在敘述帳本既有列的歷史狀態（『既有「承接輪次：R101」等舊列』，回顧語氣），不是本文件自己在交派新工作；DEF-200-204 本身已 fixed@R102（見帳本 AutoSDD_Defect_Log_archive_67.md）。目標輪 R101 早於修復輪，本應自動祖父化出局，但帳本時鐘凍結在 R100 使其失效。」
2. `docs/06_quality/CrossPlatform_R100_Scan_Findings.md`／`DEF-200-208`：「R100 收尾窗口把淨額死結的三個候選處置交棒 R101、承接列具名 DEF-200-208；該筆已 fixed@R101（一次性例外名冊落地，凍結表重釘，見帳本 AutoSDD_Defect_Log_archive_67.md）。目標輪 R101 早於修復輪，本應自動祖父化出局，但帳本時鐘凍結在 R100 使其失效。」
3. `docs/06_quality/CrossPlatform_R107_Ledger_Closure.md`／`DEF-101-559`：「R107 收尾窗口把『30 版同一 blob』材質化確認列為交棒 R108 候選、承接列具名 DEF-101-559；該筆已 closed-by-decision@R107（掌舵者條件式裁決，見帳本本文第 93 行）。目標輪 R108 早於修復輪，本應自動祖父化出局，但帳本時鐘凍結在 R100 使其失效。」
4. `docs/04_planning/R113_HANDOFF.md`／`DEF-200-212`：「本檔 :8 與 :18 兩行以「交由R114」記錄 R113 收輪時 R3 複審把本筆改判回 open 的歷史事實（敘事非交派）；DEF-200-212 已於後續輪次結案（strict 接線＋豁免面落地）。目標輪 R114 早於修復輪，本應自動祖父化出局，但帳本時鐘凍結在 R100 使其失效；本筆即 212 結案動作自身產生的同型假陽性（D8 一次性核准，存證 AutoSDD_Adjudication_Record_R120.md）。」
5. `docs/06_quality/CrossPlatform_R113_Ledger_Closure.md`／`DEF-200-212`：「本檔 :44 與 :116 兩行以「交由R114」記錄同一次 R3 複審改判（發現原文逐字所在檔）；DEF-200-212 已於後續輪次結案。目標輪 R114 早於修復輪，本應自動祖父化出局，但帳本時鐘凍結在 R100 使其失效；本筆即 212 結案動作自身產生的同型假陽性（D8 一次性核准，存證 AutoSDD_Adjudication_Record_R120.md）。」

**驗證**：`python tools/check_handoff_carriers.py --self-test` ✅ 全部通過（落地當回合先被自己的 self-test 抓到一筆 unpack 寫法錯誤，rc=1 後訂正）；`python tools/check_handoff_carriers.py` 真倉庫 ✅ rc=0（`[census]` 508 則 commit 訊息／14 筆前瞻宣告）；`pytest -k "Def200241 or Def200212 or EvidenceFamilyPointers"` → `11 passed, 5 subtests passed`。

## §DEF-200-213 帳本治理殘留（隨 241 治本解除死結）

**原文逐字保全（本輪帳本列瘦身前的「現象與證據」欄）**：「帳本治理三筆殘留，下一輪一次清：① `DEF-200-137` 的 F3／F4 兩筆無關發現仍與主發現擠同列（體例違反，且該列 699 bytes 已頂 `ROW_MAX_BYTES` ⇒ 就地拆解必越線）；② `DEF-200-195` 無回歸鎖（本輪禁止新增測試檔）；③ crossref 逐字列出 **18 筆已結列殘留待辦**；④ 待落地的 `--reconcile` 紅綠自證經實測**拒絕落地**（見§D-14）」

**裁決依據（R121 裁決卡方向 B，掌舵者 2026-09-02 採推薦；R121 對抗式證偽四道皆過）**：②`TestDef200195CrossRowReceiptFreshnessIsNotSelfSatisfied` 落地；③ 已結列殘留項現值僅 `DEF-101-060` 的「排入下一輪」敘事引述（crossref 自己標為可忽略）；④ 已定案拒絕落地；① F3／F4 兩筆皆觀察級（見 §DEF-200-137）記入證據檔、不另立列。R121 時結案被 `CrossPlatform_R100_Scan_Findings.md:103／:305` 兩行前瞻指名卡住——本輪 241 治本後，已結 ID 自動出局，本列得以結案（本檔 §DEF-200-241 的回歸鎖把這兩行列為「拿掉 done_ids 即復發」的母體之一：`DEF-200-208` 那一筆；213 的兩行同型）。

## §DEF-200-137 `draining()` 補 `COMPACT_COST_BUDGET_PP` 邊際（R121 方向 A ＋ R126 Architect 條件）

**原文逐字保全（本輪帳本列瘦身前的「分流去向」欄）**：「接進 `draining()`；鐵律七持有面：軸選擇屬設計判斷／`quota_policy.py` 400/400／`PrdDrainPercentMapsToTheBandsTest` 同改。F3＝`emit_to_model` 事件名沿用首次；今日 0 例，漏帶 `event=` 的新 PostToolUse 站點即兩則全丟（D3）、零鎖。F4＝`LatchRearmTest` stdout 斷言被前次 tmp 閂鎖過度決定＝脆弱綠非假綠」

**落地**：
- `quota_policy.Policy.compact_cost_budget_pp = 3.0`（排最後、帶預設，既有建構點逐字不受影響）；`quota_policy_env.ENV_SPEC` 新增 `AUTOSDD_QUOTA_COMPACT_COST_BUDGET_PP`（float，0~100）；`load_policy()` 新增 PRD §6.1 不變式 6（`< prepare − converge`）——違反即整組退回 `DEFAULT_POLICY` 並出聲（與四個錨點同一套 live fail-safe）；根 `.env.example` 由 `render_env_example()` 重生（+2 行）。
- `quota_gate.compact_margin_breached(readings, policy)`：五小時軸由 `quota_pace.windows()` 窗長 == 300 導出、並以 kind ∈ {session, five_hour, 5h} 為 belt-and-suspenders；用 `axis.pct` 原值；找不到五小時軸 ⇒ `False`（退回 band-only，不發明數字）。`draining()`：band ∈ `DRAINING_BANDS` **或**邊際被突破 ⇒ `"yes"`。
- 文字同步（`context_budget_guard.py` raw-line 餘裕 0 ⇒ 同行數就地改字）：864-865 註解由「全庫實查零實作」改為「已由 `quota_gate.draining()` 實作」；`_NEXT_STEP["no"]` 尾句由「🔴 未計入 PRD `COMPACT_COST_BUDGET_PP` 邊際 ⇒ 貼線時自行判斷」改為「五小時軸連同 PRD 邊際仍在 DRAIN 線下」；行數維持 1089。
- **設計卡訂正**：卡上「`quota_policy.py` 無空間」為假（現查 251/400、餘裕 149）；常數居所改由架構判準決定（帶跨欄位不變式的 PRD 門檻 ⇒ 進 `Policy`），該錯誤理由不進任何程式碼註解。
- F3／F4：依 R121 裁決卡記為觀察級，不另裁、不動碼。F3＝`emit_to_model` 事件名沿用首次、漏帶 `event=` 的新 PostToolUse 站點零鎖（今日 0 例）；F4＝`LatchRearmTest` stdout 斷言被前次 tmp 閂鎖過度決定（脆弱綠非假綠）。

**驗證**：`pytest tools/tests/test_context_budget_guard.py -k PrdDrainPercentMapsToTheBandsTest` → `5 passed, 3 subtests passed`（含新增：PRD 出廠值對帳＋不變式 6 live fail-safe 紅綠、五小時軸 83%→yes／81.9%→no／session 83%→yes／週軸 83%→no／空軸退回）；`pytest tools/tests/test_quota_policy.py` → `261 passed, 394 subtests passed`；`check_loc_budget.py` violations=0；cbg 1089 行不變。

## §DEF-200-244 PRD §4.2.2-b (4c) ＋ `gate_excluded=` 痕跡（R121 方向 B）

**落地**：條文＝`docs/04_planning/PRD_Amendment_R126_GateExclusion.md`（另開新檔、依「一版號一施工圖」慣例，SD 條件）；主 PRD 修訂表新增 v2.1.14 列；Pacing 檔 (4b) 之後只加一段指針，(4)／(4b) 一字不改。程式＝`quota_policy.decide()`：`excluded = sorted({kind∈readings} − {kind∈gate_list})`（僅 `gate_list` 非空時），併入 `reason` 的 note 集合為 `gate_excluded=a+b`；band／cap／rec／per_axis 一個位元不變。回歸鎖 `TestDef200244GateExclusionIsObservable` 四支（FALLBACK 留痕＋三欄對照組相等／全 FALLBACK fallback 無痕／未命中 MODEL_SCOPED 同時帶 `NOTE_MODEL_EXCLUDED`、命中則無痕／kind 去重排序）。

**驗證**：`pytest tools/tests/test_quota_policy.py -k Def200244` → `4 passed`；全檔 `261 passed`。

## §DEF-200-243 `windows()` 鄰軸繼承只准讓 horizon 更緊（R121 方向 B ＋ R126 四方修正）

**落地**（`tools/lib/quota_pace.py::resolve()`）：新增 `grammar = tuple(window_minutes(kind) …)`；對 `gwin is None`（自身文法解不出）的軸，`horizon = tightest(effective_horizon(用繼承窗), effective_horizon(window=None))`；攤提（`band_inputs`）仍吃繼承後的 `wins`。**不採**設計卡原寫法「純絕對門檻」——四方實測它把 session 後半窗整段放寬並牴觸 R110 Q9(i)。

**回歸鎖**（`TestDef200243InheritedWindowMayOnlyTighten`）：spend@504 分＋同 reset 的 `weekly_all` ⇒ spend horizon 仍 far、乘數＝`pace_far`、rec 等於鄰軸單獨時（spend 不替全域節奏加碼；`weekly_all` 自己剩 504 分於 10080 窗本就合法 near，故 rec 不是本案觀測面——落地當回合第一版斷言 `paired.rec ≤ alone.rec` 為此假紅 16 vs 4，已訂正）；session 掃描 minutes∈[5,300]×pct∈{0,20,50,80,95} 與今天（繼承窗 300 的完整 `effective_horizon`）逐位元相同、five_hour 不受影響；三軸含長窗時 `amort.rate_window == 300`。

**驗證**：`pytest tools/tests/test_quota_policy.py` → `261 passed, 394 subtests passed`；`check_loc_budget.py` 無 root-tools warn（quota_pace.py 餘裕仍在 6 行以上）。程式碼複審（SD）抓到 tightest 覆寫 horizon 後 burn note 仍是繼承窗那一次的 `burn-thrifty`（far＋thrifty 自相矛盾）⇒ 改為 floor 勝出時 note 一併換成 floor 那一次的；回歸鎖補 `assertNotIn(NOTE_THRIFTY, spend_note)`。

---

## §E 實作 diff 的四方程式碼定點複審（Workflow `wf_94b54756-2fb`；一審全查＋每筆 blocking 派對抗式證偽員）

| 職能 | verdict | blocking 發現 → 處置 |
|---|---|---|
| Architect | APPROVE | 零 blocking；獨立覆核了設計卡射程外的追加（判準① 讀 done_ids）：與判準② 同構、段落粒度、不觸 R89／R98／R110 ⇒ 覆核通過 |
| SA | AWC | 證據檔在 staged 快照裡缺 §D 與四個 §DEF 小節（工作樹已補、未 `git add`）⇒ 證偽員判 refuted（現行工作樹已有）；收尾以工作樹為準重新 stage |
| SD | AWC | 17 處新註解自稱超前輪號未掛 `round-label-ok` ⇒ 逐物理行補標（含多行註解的每一行）；non-blocking：D4 burn note 矛盾（已修，見 §DEF-200-243）、803 列 843 bytes（已瘦身） |
| QA | AWC | 同上 round-label；守衛線棘輪未重釘（`_FROZEN_GUARD_LINES`／`_GUARD_LINES_REPIN_LOG`／prose 桶 +41）⇒ 本節下方逐項；non-blocking：交棒書體例（「還沒做」節已改為 list item＋現查指令）、hc 判準① 一筆紅（已由 done_ids 修法解除） |

**守衛線重釘（收尾單人窗口）**：`_FROZEN_GUARD_LINES` 七支重釘；`_GUARD_LINES_REPIN_LOG` 追加 R126 列 `91990→92306（+316）`；`_REPIN_LOG_FROZEN_PREFIX_LEN` 115→116；`_FROZEN_PREFIX_REWRITE_LEDGER` 追加 `("R126", 4ec1e958f341→faddc843e042, DEF-200-241)`；款(12) 兌現 `(126, 555)` 並重新武裝 128／552；prose 桶由 +41 回到 4111（新測試類別 docstring 指名受測模組路徑後脫離 exclusive prose）。本檔自身的 `TestThisLockObeysItsOwnNoHardcodedCountRule` 在重釘當回合抓到一筆「13 筆」裸計數，已改寫。`guard-total:R126` 標記行住 `R126_HANDOFF.md` 與 `CrossPlatform_R126_Scan_Findings.md` 兩份不同檔。

**未列入本輪（複審 non-blocking、留給下一結案窗口）**：`ledger_def_ids()` 對 `layout is None` 已改為兩路徑一律排除（本輪順手做了）；D1 設計卡歷史補記判準① 追加（本檔 §DEF-200-241 已記）。
