# CrossPlatform R213 附錄 B 任務書（姊妹檔；自主檔逐字搬入）

> 主檔 `CrossPlatform_R213_DebtZero_FourParty_Evidence.md` 於 260,320 bytes 越過 warn 線（245,760），依 `DEF-101-587` 姊妹檔體例，把〈附錄 B〉整節原文逐字搬到本檔；主檔原位留同名標題＋指針。登記＝`tools/lib/governance_docs.py`。

## 附錄 B 任務書（逐字；額度視窗回復後直接派工用）


### B-ctx_pack_r213

```markdown
# R213 共同脈絡包（所有子代理必讀；主控＝Fable 5.1 舵手，你＝Sonnet 執行者）

## 0. 使命（掌舵者 2026-10-12 原文，逐字）
「我的完成的定義是沒有積欠ＢＵＧ與技術債！」「為何33 項依設計不做，請評估合理性，若不合理請全部完成。另外以下29 項等症狀、8 項只欠驗收紀錄，請確實完成測試驗收！」「這輪授權可以把週Token用完」
標的 PRD：`docs/01_requirements/AutoClaude_Token_監控與喚醒機制_PRD_v2.1.md` §16（2605～2780 行；101 列結案表在 §16.2）。
三本帳：`docs/06_quality/AutoSDD_Defect_Log.md`（未結 0）、`AutoSDD_External_Blocked_Log.md`（5 列）、`AutoSDD_Structural_Debt_Log.md`（6 列）。

## 1. 主控裁決（你不必重新決定；覺得錯就在報告〈異議〉節寫出證據，主控會看）
- R1 「做完」＝(a) 101 列無未分類 ＋ (b) 三本帳未結 0 ＋ (c) ⏸ 只准留給「症狀在本 repo 製造不出來」的列（法務人工檢核、無人 commit/push 的掌舵者安全裁決）。
- R2 33 ➖ 列主控預判全部合理（邊界兩列：施工圖 A3／§4.2.5 bursting_ok、A5b 無主處置），由 Architect 鏡逐列覆核。
- R3 29 ⏸ 三分法：【做】T3 statusLine 額度回寫、§4.5.4 週軸→FRESH、§4.5.10 探測 ≤90s、§8-3 index.lock、§6.1 不變式 9、§3.2 hotkey 註冊、§8-1 429 有界退避、§12 治理面擴列、§8-12 無人窗 deny 網路、§12 日誌遮蔽開關、§4.3 PreCompact hook；【再判 ➖（功能等價物已在或前提不存在）】T1 OTel、T2 逐字稿加總、引擎獨立遙測、§4.2.3 自動降級、§4.4.3 turns 預算、§4.5.1 逐 worktree commit、§4.5.2 長睡承接、§8-2 reset 漂移、§8-9 NEEDS_HUMAN、§9 三列、§12 schema 防偽、§12 供應鏈、§15.4 P4 超額、A5c(b)；【保留 ⏸】§13 法務、A7。
- R4 8 📎：§11.1／§11.2／§11.7 以 `tools/probe/` 探針＋真跑紀錄補件；§11.3 以 AutoClaude 計時測試補件；§11.8 需 24 小時牆鐘（另案起跑）；CLI 清單三列以家族判定結案。
- R5 長債：DEF-101-018 ruff 存量清零（凍結版本排除）、DEF-101-398 dev_start 拆分、DEF-101-701 headroom、DEF-101-702 R68 28 列交叉結案、DEF-101-980 ADR-005 狀態裁決；DEF-101-960 與外部軌 Windows 四列如實保留。

## 2. 鐵律（違反＝交件無效）
1. 回覆與報告一律繁體中文；首行固定 `STATUS: DONE|PARTIAL|BLOCKED`。數字只准引用你本次真跑指令的輸出，逐字貼 rc 與摘要行；沒跑就寫「未驗證」。
2. 一律絕對路徑（repo 根 `/Users/wuweihong/Antigravity/AISDCL_Agent`）；複合指令用子殼 `(cd /abs && …)`，不要裸 `cd`。python 用 `/Users/wuweihong/Antigravity/AISDCL_Agent/.venv/bin/python`。
3. 禁止：任何 git 寫入（commit／stash／checkout／restore／reset／clean）；跑 `tools/session_resume_planner.py --pace|--arm-*|--register-*`；跑 `tools/lib/quota_burndown.py --issue|--revoke`；打真實 usage 端點（測試一律 mock `urllib.request.urlopen`，只准讀 `quota_meter.read_cache()`）；刪逐字稿；改 `.claude/**`（分類器會擋，成品放 scratchpad 交主控）；改 `tools/tests/test_adr_xplat001_c1c2_lock.py`、三本帳、PRD、CLAUDE.md、`env.shared`、`.env`、ONBOARDING.md、`AISDLC_SDD/` 除 `AISDLC_SDD_v0.30` 以外的任何版本目錄。
4. LOC 預算已貼頂的檔（新增一行就紅）：`tools/lib/quota_gate.py` 499/500、`tools/session_resume_planner.py` 750/750、`tools/lib/quota_escalation.py` 400/400、`tools/lib/skip_group_policy.py` 400/400、`tools/lib/schedule_backend.py` 397/400、`.claude/hooks/context_budget_guard.py` 1089/1089、`tools/run_root_unittests.py` 777/777、`tools/dev_start.py` 1951/1952、`tools/lib/hook_wiring.py` 782/782、`tools/archive_defect_log.py` 1507/1507。要在這些檔加 N 行，就同檔搬 ≥N 行「史料型註解／docstring 沿革」到 scratchpad `lore_moved_<檔名>.md`（主控會收進證據檔）。新 `tools/lib/*.py` ≤400 行；新 `tools/*.py` ≤750 行且 argv 要走 `tools/_cli_flags.py` 的 `reject_unknown_argv`。驗證：`.venv/bin/python AutoClaude/tools/check_loc_budget.py`（rc=0 才算）。
5. `tools/tests/` 總行數棘輪本輪餘裕 1 行：新增測試行必須在 `tools/tests/` 內刪等量史料行抵銷（只刪註解／docstring 沿革，不刪斷言）；交件前跑 `.venv/bin/python tools/tests/test_adr_xplat001_c1c2_lock.py --print-guard-lines | head -2` 把「淨額」行逐字貼進報告（目標 ≤ +0）。探針放 `tools/probe/`（不計棘輪）。AutoClaude 測試放 `AutoClaude/tests/`（指紋樹，主控負責回填）。
6. 文件／註解：禁寫「延後到 R<N>」「下一輪」；DEF 編號寫全名 `DEF-200-NNN`；新文件禁出現英文 `通過(英)`／`略過(英)` 配數字；輪號註解（含 R\d+）行尾加 `# round-label-ok`；中文一字算 2 欄、每行 ≤100 欄（`.venv/bin/ruff check <你改的檔>` 必須乾淨）。
7. 跨平台：文字 I/O 一律 `encoding="utf-8"`；時間戳帶 offset（`datetime.now(timezone.utc)`／`astimezone()`）；不寫死路徑；subprocess 帶 `encoding="utf-8", errors="replace"`；平台專屬 API 要有平台守衛。鎖＝`tools/tests/test_platform_neutral_paths.py`（會掃到你）。
8. 測試指令：根層全套 `env -u AUTOSDD_PARALLEL_TESTS AUTOSDD_SENTINEL_OFF=1 .venv/bin/python tools/run_root_unittests.py`（慢，最後跑一次）；針對性 `(cd tools/tests && AUTOSDD_SENTINEL_OFF=1 ../../.venv/bin/python -m unittest test_x.TestY -v)`；AutoClaude `(cd AutoClaude && ../.venv/bin/python -m pytest tests/ -q -x -p no:cacheprovider)`；針對性加檔名。每改完一支就跑對應測試，不累積。
9. 每個新判準先紅後綠：先寫會失敗的測試、再補碼、貼兩次 rc。
10. 交件：報告寫到 scratchpad（路徑主控指定），回覆只貼 `STATUS:` 行＋≤12 行摘要＋報告路徑；長證據一律落檔。

## 3. 本輪已知座標（省你搜尋）
- 額度讀數：`tools/lib/quota_meter.py::read_cache()`（零 token）；判決 `tools/lib/quota_policy.py::decide()`；守門 `tools/lib/quota_gate.py`（`endpoint_probe_verdict` :739、`write_halt_marker` :817）；遲滯 `tools/lib/quota_stability.py`；單位正規化鎖 `tools/tests/test_context_budget_guard.py::QuotaUnitNormalizationTest`。
- statusLine 回寫：producer `tools/statusline_context_feed.py::build_feed_doc`（:84，現只轉 model／context_window）；feed 檔 `~/.autosdd/context_feed/<sid>.json`；讀端 `tools/lib/harness_feed.py`；`claude` 2.1.296 二進位內嵌 schema 自述 statusLine 輸入含選用 `rate_limits`（訂閱帳號、首次 API 回應後出現）。
- 喚醒路由：`tools/session_resume_planner.py::choose_resume_route`（:1141；`STRATEGY_FRESH` :1105）；純函式住 `tools/lib/resume_route.py`（298 行，有餘裕）；方向鎖測試 `tools/tests/test_context_budget_guard.py` :3004～3127。
- 付費探測：`tools/session_resume_planner.py::probe_quota`（:481，subprocess timeout=180）、`tick_plan`（:535，`MAX_PROBE_ATTEMPTS` 已在）。
- 續跑窗 git 快照：`tools/lib/relay_machine.py::git_status_snapshot`（:144）。
- 引擎：撞線 halt `AutoClaude/autoclaude/plugins/token_guard/policy.py::evaluate_quota`（:192）；開機自檢 `AutoClaude/autoclaude/execution/boot_self_check.py`（不變式 8／11～13 已在，`boot_self_check()` :419）；hotkey `AutoClaude/autoclaude/perception/hotkey_handler.py`、入口 `AutoClaude/autoclaude/main.py` :240～276（`HotkeyHandler()` 建了卻沒 `register()`）；長睡拒絕 `AutoClaude/autoclaude/core/services/auto_resume.py::_wait`（:333）；PG 遮蔽 `AutoClaude/autoclaude/infra/repositories/pg_state_repository.py::_redact`（:75）；logger `AutoClaude/autoclaude/utils/logger.py::setup_logger`（:46）；`.autoclaude/` 目前**沒有**被任何 .gitignore 忽略（`git check-ignore` 空）。
- importlinter 規則 9：autoclaude 不得 import `tools`／`.claude`；跨層只走檔案契約。
```

### B-brief_review_common

```markdown
# R213 四方獨立審查共同脈絡（Architect／SA／SD／QA；Sonnet；唯讀鏡；互不交談）

## 審什麼
掌舵者原文（2026-10-12）：「我的完成的定義是沒有積欠ＢＵＧ與技術債！」「為何33 項依設計不做，請評估合理性，若不合理請全部完成。另外以下29 項等症狀、8 項只欠驗收紀錄，請確實完成測試驗收！」
本輪（R213）主控裁決與落地全貌＝`docs/06_quality/CrossPlatform_R213_DebtZero_FourParty_Evidence.md`（先讀〈一〉〈二〉〈三〉）；共同脈絡包＝`<scratchpad>/ctx_pack_r213.md`；兩份執行者報告＝`<scratchpad>/devA_report.md`、`<scratchpad>/devB_report.md`（他包回報，零信任：數字要自己重跑才算）。
PRD＝`docs/01_requirements/AutoClaude_Token_監控與喚醒機制_PRD_v2.1.md` §16（結案表 §16.2 本輪改動：16 列 ⏸→➖ 帶「v2.1.20」落款、N 列 ⏸／📎→✅ 帶落款；修訂表新列 v2.1.20）。
程式改動＝工作樹相對 HEAD（`git diff HEAD --stat`；新檔 `git status --short | grep '^??'`）。

## 鐵律（唯讀鏡）
- 一律繁體中文；絕對路徑；禁任何 git 寫入；禁改任何檔（含 scratchpad 以外）；禁 `--pace`／`--arm*`／`--issue`／`--revoke`；禁打真 usage 端點；禁刪逐字稿；突變／對抗實驗只准在 scratchpad 的隔離副本做（`cp -R` 子集），不准就地突變工作樹。
- 「量、不挖」（根 CLAUDE.md〈守衛面准入〉）：跑既有指標與重測；不構造變體去守衛面找新缺陷；構造性命中不計 P≤2，登 P4。
- 數字只准引用你本次真跑的輸出並逐字貼；轉述他包標 `[他包回報]`。
- 嚴重度：P1 錯誤行為／資料損毀／守衛失效；P2 需求未被滿足卻被標 ✅、或 ➖ 理由不成立（＝掌舵者要求「不合理就全部完成」的觸發）；P3 提交前應改的文字／測試牙口／設計瑕疵；P4 只登記。
- 交件：寫到 `<scratchpad>/review_<角色>.md`（純文字 markdown；首行逐字 `VERDICT: APPROVE|CONDITIONAL|REJECT`；第二行 `P1=<n> P2=<n> P3=<n> P4=<n>`；之後〈一〉逐列判定表、〈二〉findings（每條：ID／嚴重度／座標 file:line／一句事實／一句修法）、〈三〉你實跑的指令與逐字輸出、〈四〉對主控文字（證據檔、PRD 落款）的訂正清單）。回覆只貼前兩行＋≤8 行摘要＋路徑。
- 判決規則：P1 或 P2 任一 ⇒ REJECT 或 CONDITIONAL（可一輪修完＝CONDITIONAL）；只有 P3／P4 ⇒ APPROVE。
```

### B-brief_review_architect

```markdown
# Architect 鏡（先讀 brief_review_common.md）
你的專屬題：
A1 「依設計退役」合理性：PRD §16.2 現有全部 ➖ 列（原 33＋本輪再判 16＝49）逐列獨立判「合理／不合理」並給一句理由（合理＝PRD 自身指定替代路線、功能等價物真的存在於 HEAD〔要 grep 到座標〕、或前提在本 repo 不存在；不合理＝有真實需求場景且無等價物）。任一「不合理」＝P2 並寫出最小實作方案。主控已自標兩列邊界（施工圖 A3／§4.2.5 bursting_ok、A5b 無主處置）請特別審。
A2 新碼架構：T3 statusline 後備的優先序（端點新鮮 > statusline 新鮮 > unmeasured）、週軸→FRESH 的方向鎖、kernel 的 limit-retry 機制與 plugin 決策的邊界、redaction filter 的單一樣式表、`gitignore_verdict` 的爆炸半徑（DEV-B 報告〈異議〉1）、DEV-B 多加的「額度已撞硬線不退避」（〈異議〉2）是否該留。
A3 ADR-XPLAT-005 由 Proposed→Accepted 的追認依據（檔頭狀態行）是否站得住；證據檔〈二〉主控裁決 R1～R5 是否有邏輯洞。
```

### B-brief_review_sa

```markdown
# SA 鏡（先讀 brief_review_common.md）
你的專屬題：
S1 需求↔實作追溯：主控把 29 列 ⏸ 分成【做】11／【再判 ➖】16／【保留 ⏸】2（證據檔〈二〉R3）。對【做】的每一列，把 PRD 原條文要求逐句對上實作座標與測試，判「滿足／部分／未滿足」；被標 ✅ 卻未滿足＝P2。三列因守衛面待掌舵者核准而仍 ⏸（§4.3、§8 列 12、§12 寫入範圍）：審主控寫法是否誠實。
S2 📎 八列：§11.1／§11.2／§11.3／§11.7 的補件是否真的滿足 PRD §11 各判準（讀原文逐句）；§11.8 保留 📎 的理由；CLI 清單三列以家族判定結案是否成立。
S3 PRD 文字：v2.1.20 修訂表列、§16.1「做完」註記、各列落款的用語有無過樂觀（例：把「單元測試」寫成「E2E」、把「他包回報」寫成親驗）；逐條給訂正句。
S4 三本帳：證據檔〈六〉對結構性長債 6 列／外部阻塞 5 列的處置是否與解鎖條件原文一致（DEF-101-701 headroom、DEF-101-980 ADR、其餘為何保留）。
```

### B-brief_review_sd

```markdown
# SD 鏡（先讀 brief_review_common.md）
你的專屬題：
D1 逐檔讀 `git diff HEAD`（含新檔）：LOC 預算（`.venv/bin/python AutoClaude/tools/check_loc_budget.py` 自跑）、跨平台鐵律三（naive 時間戳、encoding、平台專屬 API 守衛、路徑分隔符）、fail-open 語意是否被改掉、知識是否住兩個家（例：T3 讀端的單位正規化是否重用既有函式、PreCompact 若有）、例外處理是否吞掉不該吞的、注入點是否可測。
D2 史料搬遷：`tools/run_root_unittests.py` 搬出的 15 行與 `SPECIAL_FILES` 重釘 777→765 是否只搬敘事不搬判準；quota_gate／planner 的史料搬遷（`<scratchpad>/lore_moved_*.md`）同判。
D3 簡化建議（P3）：能刪的旋鈕、能合併的函式、過寬的測試替身；不構造變體。
D4 tools/tests 棘輪：自跑 `.venv/bin/python tools/tests/test_adr_xplat001_c1c2_lock.py --print-guard-lines | head -3`，貼淨額行；評估主控的抵銷／重釘方案。
```

### B-brief_review_qa

```markdown
# QA 鏡（先讀 brief_review_common.md）
你的專屬題（每條指令 rc 單獨讀：`cmd > <scratchpad>/qa_x.log 2>&1; echo rc=$?`，再 `tail` 看）：
Q1 根層全套：`env -u AUTOSDD_PARALLEL_TESTS AUTOSDD_SENTINEL_OFF=1 .venv/bin/python tools/run_root_unittests.py`（慢）；AutoClaude 全套：`(cd AutoClaude && ../.venv/bin/python -m pytest tests/ -q -p no:cacheprovider)`；`(cd AutoClaude && PYTHONUTF8=1 ../.venv/bin/lint-imports)`；`.venv/bin/ruff check $(git diff HEAD --name-only -- '*.py'; git ls-files --others --exclude-standard -- '*.py')`；`.venv/bin/python AutoClaude/tools/check_loc_budget.py`。逐字貼每條 rc 與結尾摘要行；任何紅都要指出是誰造成（對照兩份報告的自述）。
Q2 零信任重跑兩份報告的關鍵數字：devA 的三支探針（`tools/probe/pacing_simulator.py --selftest`、`tools/probe/zero_token_telemetry_window.py`、`tools/probe/two_project_fanout_probe.py`）與 devB 的 `AutoClaude/tests/integration/test_freeze_timing_prd11_3.py -s`（貼實測秒數）；對不上＝P2。
Q3 牙口抽查（隔離副本）：把 `tools/lib/resume_route.py`、`AutoClaude/autoclaude/utils/redaction.py`、`AutoClaude/autoclaude/plugins/token_guard/policy.py` 各 `cp` 到 scratchpad 隔離目錄做 ≤3 處語意突變後，用 `PYTHONPATH` 指向副本跑對應測試，記錄殺／存活；存活的突變＝P3（測試牙口）。不准就地改工作樹。
Q4 真機單次觀測：`.venv/bin/python tools/session_resume_planner.py --check` rc；statusline producer 餵含 `rate_limits` 的 payload（見證據檔〈三〉A1 的指令）rc 與 feed 檔鍵；`tools/lib/quota_burndown.py --status` rc（只讀）。
Q5 平台標籤略過數與 skip census 行逐字貼（根層全套輸出末段）。
```

### B-brief_devC

```markdown
# 任務書 DEV-C：結構性長債四筆（Sonnet；先讀 ctx_pack_r213.md 全文）
報告落檔：`<scratchpad>/devC_report.md`。你**不寫**任何帳本／證據檔／R68 檔（結案單線＝主控）；你交的是「程式碼改動＋逐列結案提案表」。

## C1 DEF-101-702：`docs/06_quality/CrossPlatform_R68_Scan_Findings.md` 的 28 筆 open／partial（第 46 行表頭；「狀態@R69」欄）
對每一筆 open／partial 列：讀「缺陷／座標／修復方向」三欄，到 HEAD 現查該方向是否已由後續輪落地（grep 具名機制、檔案、測試類；`git log -S` 可用）。產出 `<scratchpad>/r68_closure_proposals.md` 表：`編號 | 現判（fixed@HEAD／closed-by-decision／仍 open）| 座標或理由（一句，附 file:line 或指令輸出）`。判「仍 open」且修法 ≤40 行、不碰 LOC 貼頂檔者 ⇒ 你直接實作並附測試（先紅後綠），改判 fixed@R213；修法更大者保留 open 並寫明預估規模。已知由本輪其他包落地的三筆請標「本輪他包：R68-38 root ruff.toml（DEV-D）／R68-41 hotkey register（DEV-B）／R68-67 keyboard 平台條件（請你查 `AutoClaude/pyproject.toml` 現況，若未加平台條件就由你補，屬 ≤40 行）」。目標：表上 28 筆每筆都有明確現判，open 殘量越少越好、但不准假結案。

## C2 DEF-101-701：`tools/run_root_unittests.py` headroom 0（777/777）
把檔內「史料型」註解／docstring 沿革（只搬敘事，不搬任何判準或指令）搬 ≥12 行到 `<scratchpad>/lore_moved_run_root_unittests.md`，使 loc ≤765；再把 `AutoClaude/tools/check_loc_budget.py` 的 `SPECIAL_FILES` 該列門檻重釘為新現值（棘輪只准往下）；跑 `.venv/bin/python AutoClaude/tools/check_loc_budget.py` rc=0 與 `tools/tests/test_run_root_unittests.py` 綠；報告貼 headroom 新值。

## C3 DEF-101-398：`tools/dev_start.py`（1951 行）拆出兩支模組（純搬移、行為逐位元不變）
1. `tools/lib/nightly_heartbeat.py`：搬 `_NIGHTLY_POSIX_LOCK`、`_nightly_running()` 及其專屬 helper（約 :646～698）。
2. `tools/lib/bootstrap_lock.py`：搬 `LOCK_FILE` 相關的 `_acquire_bootstrap_lock`／`_pid_alive`／`_lock_target_alive`／`_list_pid_ppid_pairs_windows`／`_collect_descendant_pids`／`_DescendantWatcher`（約 :956～1150，依實際內聚邊界）。
3. dev_start.py 以 `from lib.xxx import …`（照檔內既有 import `tools/lib` 的寫法）重新匯出**同名**符號，讓 `tools/tests/test_dev_start.py` 既有的 `mock.patch.object(dev_start, "_nightly_running")` 等 patch 點全部不變；跑 `(cd tools/tests && AUTOSDD_SENTINEL_OFF=1 ../../.venv/bin/python -m unittest test_dev_start -v 2>&1 | tail -5)` 必須全綠。
4. 兩支新檔各 ≤400 行；新檔要補進 `.github/workflows/macos-compat-ci.yml` 與 `windows-compat-ci.yml` 的 push／pull_request 兩份 `paths`（各放在 `tools/lib/quota_env_layers.py` 那行旁），然後跑 `(cd AISDLC_SDD && ../.venv/bin/python -m pytest scripts/tests/test_ci_paths_cover_root_consumers.py -q)` 綠。
5. `SPECIAL_FILES` 的 dev_start.py 門檻重釘為新現值；`check_loc_budget.py` rc=0。
6. 報告明寫：Windows 側未實跑（mac 無法驗證 Windows bootstrap 路徑），哪些函式含平台分支。

## C4 DEF-101-980：ADR-XPLAT-005 §5 機械物 M1～M14 的 HEAD 現查
`docs/04_planning/ADR/ADR-XPLAT-005-quota-aware-throttling-and-fanout-resume.md` :366～392 的表，逐列現查指名的測試類／檔／符號是否存在（grep 命中貼行號）；M8「endpoint-authoritative 白名單」、M10「quota_throttle_pct＋兩欄不共用」、M11「importlinter 規則 9」三個「未落地」半邊現在是否已落地（貼證據）。產出 `<scratchpad>/adr005_mtable_verdict.md`（表：M# | 現況 landed/partial/missing | 證據行）。不改 ADR 本文（主控改狀態行）。

## 收尾
`.venv/bin/ruff check <改到的檔>`、`check_loc_budget.py` rc、`--print-guard-lines | head -2` 淨額行（你若動了 tools/tests 就要抵銷）、根層全套 `tools/run_root_unittests.py` rc 與結尾三行逐字。報告列：file:line、先紅後綠 rc、三份提案表路徑、未完成與原因、〈異議〉。
```

### B-brief_devD

```markdown
# 任務書 DEV-D：DEF-101-018 ruff 存量債清零（Sonnet；先讀 ctx_pack_r213.md 全文）
報告落檔：`<scratchpad>/devD_report.md`。解鎖條件（帳本原文）：在 repo 根 `.venv/bin/ruff check . 2>&1 | tail -1` 印 `All checks 通過(英)!`。

## 事實（主控已量）
`ruff check .` 共 3566 筆：AutoClaude 656；`AISDLC_SDD/AISDLC_SDD_v0.01`～`v0.29` 凍結版各約 96～97（**不可編輯**，掌舵者裁決：只有 LATEST=`AISDLC_SDD_v0.30` 可原地改）；v0.30 共 96（E731 31／F401 26／F541 22／E702 12／E402 2／F841 2／E401 1）。AutoClaude 規則分佈：UP045 257、E501 134、F401 71、I001 70、UP037 54、E702 18、UP035 13、F841 10、UP017 10、E741 5、UP042 5、E402 4。ruff 設定：`AutoClaude/pyproject.toml [tool.ruff]`（SSOT）、`tools/ruff.toml`（逐字對齊前者；E501 中文算 2 欄、行寬 100）；repo 根與 AISDLC_SDD 無設定（走出廠預設）。

## D1 凍結版排除（結構上不可修的那 ~2800 筆）
新增 repo 根 `ruff.toml`：只做 `extend-exclude`，排除 `AISDLC_SDD/AISDLC_SDD_v0.0*`、`AISDLC_SDD/AISDLC_SDD_v0.1*`、`AISDLC_SDD/AISDLC_SDD_v0.2*`（v0.30 與未來版留在掃描面；LATEST 以 `python AISDLC_SDD/scripts/sdd_version.py` 現查，不寫死），檔頭註解寫 WHY（凍結版不可編輯＝掌舵者裁決，不是放水）。加一支鎖 `AISDLC_SDD/scripts/tests/test_ruff_root_config_excludes_only_frozen.py`：斷言根 ruff.toml 的排除樣式**不**匹配 LATEST 目錄、且匹配 v0.01；LATEST 變動時該鎖會紅。確認根 ruff.toml 不影響 AutoClaude（`AutoClaude/pyproject.toml` 更近）與 tools/（`tools/ruff.toml` 更近）：改前改後各跑 `ruff check AutoClaude --statistics` 與 `ruff check tools --statistics` 必須逐字相同。

## D2 AutoClaude 656 → 0
1. 先 `(cd AutoClaude && ../.venv/bin/ruff check . --fix)`（只用安全 fix；**不加** `--unsafe-fixes`），再看殘量。`__init__.py` 的 F401 若是刻意 re-export，改成 `__all__` 或 `from x import y as y` 形態，不要刪。
2. 殘量手修：E501 換行（不改語意，中文註解行拆句）；E702 分行；UP035／UP042／E741／E402／F841 逐筆；E402 若是刻意的 sys.path 操作後 import，加 `# noqa: E402` 並留一句 WHY。禁止在 pyproject 加 ignore 規則（那是改政策，不是還債）。
3. 每修完一個子目錄跑該目錄測試；最後 `(cd AutoClaude && ../.venv/bin/python -m pytest tests/ -q -p no:cacheprovider)` 全套 rc 與結尾摘要行逐字、`PYTHONUTF8=1 ../.venv/bin/lint-imports` rc、`../.venv/bin/python tools/check_loc_budget.py` rc（UP 修法會改行數，超 tier 就拆）。

## D3 v0.30 96 → 0
同 D2 作法（E731 的 31 支 lambda 改 def，保留同名與簽章）。驗證：`(cd AISDLC_SDD/AISDLC_SDD_v0.30 && ../../.venv/bin/python -m pytest tools/fsm_runtime/tests -m "not chaos" -q -p no:cacheprovider)` rc 與摘要行；`(cd AISDLC_SDD && bash scripts/ci-gate.sh)` rc（慢；最後跑一次，rc 讀 `echo $?` 不接管線）。

## D4 終驗
repo 根 `.venv/bin/ruff check . 2>&1 | tail -3` 逐字貼；`git diff --stat | tail -1` 貼檔數。若某子集真的修不到 0，報告逐條列出剩餘筆數、規則、原因（不准靜默）。

## 禁區
不動 `.claude/`、PRD、三本帳、`tools/tests/test_adr_xplat001_c1c2_lock.py`、凍結版目錄；不改 `tools/` 的 E501 存量（那條有自己的棘輪，不在本包）。改到 `AutoClaude/tests/`、`AISDLC_SDD_v0.30/tools/fsm_runtime/tests/`、`AISDLC_SDD/scripts/tests/` 屬指紋樹——允許，主控會回填。
```

