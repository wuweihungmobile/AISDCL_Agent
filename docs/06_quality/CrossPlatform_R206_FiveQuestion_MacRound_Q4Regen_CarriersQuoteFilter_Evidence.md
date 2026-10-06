# CrossPlatform R206 — 他機輪次（Mac；不計次）＋ Mac Q4′ JSON 重產（DEF-200-504 第一項）＋ carriers 判準① 引號轉述濾網（方案 A；DEF-200-505 born-fixed）證據檔

> R 系列證據檔（根 CLAUDE.md〈三條改進軌道〉附列）。目標路徑 `docs/06_quality/CrossPlatform_R206_FiveQuestion_MacRound_Q4Regen_CarriersQuoteFilter_Evidence.md`。上輪 R205：`docs/06_quality/CrossPlatform_R205_FiveQuestion_WinEval_T3_Recheck_Evidence.md`；上一次 Mac 他機輪次 R201：`docs/06_quality/CrossPlatform_R201_FiveQuestion_MacRound_Q4Darwin_Evidence.md`。協定 `docs/06_quality/FiveQuestion_Audit_Protocol/`（sha 5c9aadf2…，本輪未改、凍結維持）；輪帳本 `docs/06_quality/FiveQuestion_Round_Ledger.jsonl`（本輪 +1 列＝R206，`symptom_streak` 依〈四〉D1 寫 0）。標記：`[主控提供]`＝主控本場 tool_result；`[他包回報]`＝子代理回報、主控未必重驗；`[前輪]`＝承前輪證據。

## 〇、一句話結論
Mac 這一輪（他機、不計次）做完三件事，並因真實層 Q2′ FAIL 依協定計次條款把 `symptom_streak` 由 3 歸 0（〈四〉D1）。
- **Mac Q4′ JSON 重產（DEF-200-504 第一項）`[主控提供]`**：darwin 1180 bytes、sha256 `4873c58c…`、`generated_at` 2026-10-06T23:46:47+08:00（效期至 2026-10-20T23:46:47+08:00）、`repo_head` 0da65578；`--protocol-status` darwin 行 PASS 九格 ✓；**尚未拷回評估機**（〈八〉(1)；帳本載體 DEF-200-504）。
- **三項字面評估（Mac＝他機、不計次）`[主控提供]`**：項 1 合併層 NOT-EVALUABLE（Q1′a／Q1′b PASS、Q1′c／Q3′ NOT-EVALUABLE、無 FAIL）；項 2 真實層 **FAIL**（母體 1 支＝R201 主控窗 35be7e5b，首查 #11，已知成因）；項 3 兩平台 Q4′ 各一行 PASS 九格 ✓。
- **carriers 判準① 引號轉述濾網（方案 A）**：SA 推薦、主控裁決動工；`_narrative_hit()` 加第二條件（命中落在成對「」／『』內＝轉述）、工具 +23／−2、測試 22 增 22 刪（淨 0 行）；DEF-200-505 當輪 born-fixed、DEF-200-504 卸下「兼任承接列」。SA 規格 `[他包回報]`；Developer 驗收全綠、QA APPROVE／NEW_P_LE_2 0（〈三〉）。
- **D1**：`symptom_streak` 寫 0（README 計次條款「任一機任一輪任一行 FAIL ⇒ 寫 0」；對立讀法〔他機條款沿用 streak〕登記 P3、不採）；R203 的收斂宣告為歷史事實、README 無撤回條款；評估機下次達標從 0 起算；再評仍只由〈守衛面准入〉觸發。

## 一、判定（Mac＝他機、不計次）
| 問 | 本輪判定 | 依據 |
|---|---|---|
| 1「開新視窗就說被擋、不查數據」 | **NOT-EVALUABLE**：合併層（5 支）Q1′a PASS 0／hook 阻斷 0、Q1′b PASS 0／0、Q1′c NOT-EVALUABLE(5/10) 0／5（首呼叫被擋 0／5）、Q3′ NOT-EVALUABLE(1/3) 1 對 max\|差\|=0 ⇒ 四行未全 PASS、無 FAIL；真實層（1 支）Q1′a PASS 0／0 | 〈二〉指令 1／2 |
| 2「不用真實 /context 或 API 查」 | **FAIL**：真實層 Q2′ 逾期或從未 1／1 `[('35be7e5b', 11)]`、有簡報 1；母體 1 支＝R201 主控窗 35be7e5b（首查 #11；已知成因：掌舵者貼入的啟動提示詞為舊副本、缺 useMacWin.md 第 0 步）；n=1 ＜ `q2_min_n` 5，但工具 FAIL 優先 | 〈二〉指令 2；〈四〉D2 |
| 3「是否已收斂」 | **維持「是（協定上）」，但 `symptom_streak` 歸 0（3→0）**：R203 宣告為歷史事實、README 無撤回條款；評估機下次達標從 0 起算；他機條款沿用 streak 的對立讀法登記 P3、不採 | 〈四〉D1；〈五〉 |
| 與 R201（上一次 Mac 他機輪次；探針落地後口徑）逐項差 | 合併層母體 4→5 支、真實層 0→1 支（R201 主控窗 35be7e5b 於該輪自我排除，本輪起入母體）；Q1′b NOT-EVALUABLE(4/5)→PASS 0／0、Q1′c NOT-EVALUABLE(4/10) 0／4→(5/10) 0／5、Q3′ NOT-EVALUABLE(0/3)→(1/3) 1 對、Q1′a 仍 PASS 0／0；**Q2′ NOT-EVALUABLE(0/5)→FAIL 1／1**（R201〈四〉4.3 #4 預告的排程風險）；Q4′ 兩輪皆兩平台 PASS 九格 ✓，darwin JSON 由 R201 版（1180 bytes、0a412725…、`generated_at` 2026-10-05T21:38:15+08:00、cc 2.1.289、`repo_head` d2b16c6d）重產為本輪版（1180 bytes、4873c58c…、2026-10-06T23:46:47+08:00、cc 2.1.291、0da65578），win32 JSON 原封未動；主控窗首查由 #11（舊提示詞）變 #1（提示詞含第 0 步）。 | R201〈二〉〈四〉；本檔〈二〉 |

## 二、主控親測事實與起草員唯讀核對（Mac 本機；時刻皆 +08:00；指令 1～3 的時刻取主控 `date` 戳記 2026-10-06T23:47:12～14+08:00，非推定）
- **開場 `[主控提供]`**：sid a8f667b5-de3b-4e2f-a049-aee757d3e64f、darwin（host wuweihongdeMac-Studio.local）、`claude --version` ⇒ `2.1.291 (Claude Code)`、`python --version` ⇒ `Python 3.11.15`。第 1 個工具呼叫＝`python tools/session_resume_planner.py --check`（23:37；新視窗尚無 usage 記錄、harness used=85,462；掌舵者貼入的啟動提示詞含 useMacWin.md 第 0 步），第 2 個＝`--pace` ⇒「現在可派 4 個 agent（cap=不設限）band=free｜最緊 weekly_scoped 8% 剩 5902 分鐘」（量測於 2026-10-06T23:37:32+08:00）；派 SA 前重查（量測於 23:51:04）可派 4、weekly_scoped 10%；派 Developer 前（量測於 2026-10-07T00:44:34+08:00）可派 4、weekly_scoped 11%；派 QA 前（量測於 2026-10-07T01:22:58+08:00）可派 4、weekly_scoped 12%（三次皆 band=free；「量測於」＝額度快取時刻、非呼叫時刻）。
- **平台切換 SOP（useMacWin.md B 段；Windows → Mac）`[主控提供]`**：`git branch --show-current` ⇒ `main`、`git status --porcelain --untracked-files=all` ⇒ 0 行 rc=0；`.venv/bin/python tools/dev_start.py --check-nightly` ⇒「idle：沒有 nightly 在跑，可以安全同步」rc=0；`git fetch origin` rc=0（`18adf468..0da65578 main -> origin/main`）、`git rev-list --left-right --count origin/main...main` ⇒ `10 0`、`git merge --ff-only origin/main` rc=0（18adf468→0da65578，11 檔 +655／−66，新增 R202～R205 四份證據檔）；HEAD＝origin/main＝`0da655787699b337af5a4afec0d6531b90753b11`（掌舵者交接說「三個新 commit」是相對 Windows 側；Mac 上次停在 R201〈七〉回填 18adf468，故實拉 10 個）。指紋監測面 `git diff --name-only ORIG_HEAD HEAD -- AutoClaude/tests AISDLC_SDD/scripts/tests 'AISDLC_SDD/*/tools/fsm_runtime/tests'` ⇒ 空（四棵樹零變動 ⇒ 免回填）；`tools/tests/test_claim_provenance_r86.py` 與 `.claude/hooks/check_claim_provenance.py` 有變（R204），不在指紋面。
- **dev_start、表②、statusLine `[主控提供]`**：`source tools/dev_start.sh` rc=0：「環境：windows → mac（跨機切換，git 判定）」「GitHub 同步：已是最新（origin/main）」「venv／依賴：依賴新鮮（hash 未變）」「git hooks：正常」「平台健檢：無需調整；nightly 心跳新鮮；CI 活性正常；表② 指紋相符」；⚠️ 1 件＝GitHub 排程軌 `ci_liveness` 警告（含 1 句實測「aisdlc-sdd-drift-daily.yml 最近成功於 14 天前」＋結構宣告；與 R205〈五〉7 同形、非本輪新增；a7a3080 2026-08-07 起既有）；[6/7] 另印「nightly 心跳新鮮（AutoClaude/logs/nightly_mac_latest.log，距今 0.9 天）」「GitHub CI 活性正常（最新 run：AutoClaude CI=success）」「ONBOARDING §7 表② 指紋相符（--check-snapshot rc=0）」。`--check-snapshot` rc=0「§7 表② 指紋相符 macOS 欄（v001=8ffe3c3dabbd, v030=6d46814f9084, scripts=ec35ee2838d0, autoclaude=69fdad8c334d）」、provenance measured-at 2026-10-05／docker down／pgextras absent／self-recorded ⇒ 免回填；`.venv/bin/python tools/install_statusline.py --status` ⇒ installed true、matches_current_checkout true、python_basis repo-venv rc=0。
- **hook 載具正負兩面 `[主控提供]`**：`test -x .venv/bin/python` ⇒ carrier-ok；`readlink .venv/Scripts/pythonw.exe` ⇒ `../bin/python`；`claude -p --model haiku --debug hooks --debug-file h.log "ok"`（在 repo 根）rc=0 ⇒ `grep -c 'Hook SessionStart.*success'`＝2（context_budget_guard 與 sdd_hook_router 各一）、`grep -ci ENOENT`＝5（逐筆皆 Claude Code 自身選配目錄 `/Library/Application Support/ClaudeCode/.claude/{agents,commands,output-styles}`、`~/.claude/{agents,commands}`，非 hook 載具）、另一行 `[ERROR] NON-FATAL: Lock acquisition failed for ~/.local/share/claude/versions/2.1.291`＝CC 多行程鎖、非 hook（起草員對該 h.log 唯讀重數：success 2、ENOENT 5、鎖行 1 `[他包回報]`）。**誠實劃界**：主控第一次把 `claude -p` 跑在 scratchpad 目錄（專案 hook 不載入、SessionStart success 0、ENOENT 6）＝無效量測，已在 repo 根重做；第一次的 h.log 已刪、不作數。hook 活性的另一證據＝本窗第 5 個工具呼叫（對 `git status` 輸出接管線後讀 rc）被 `block_destructive_git.py` 判準④ 正確擋下（見 T5 條）。
- **雲端對帳與切換驗證全套 `[主控提供]`**：`gh run list --commit <完整 sha>`：0da65578 ⇒ root-infra-ci 37482841122 success、AutoClaude CI 37482841213 success（皆 push、completed）；3f164979 ⇒ root-infra-ci 37475531716 success（docs-only）；短 sha `--commit 3f164979` 回 `[]`（已知陷阱）；最近 10 支 run 皆 completed success（含 3a7e590 四支 push run、2d5c06b 三支排程 run）；缺席＝未驗證、非通過。根層全套（HEAD 0da65578、套用本輪任何變更之前；`tools/run_root_unittests.py` 背景、23:40:56 啟動、23:42:54 完成〔逐字稿轉錄，QA 核對〕）⇒ `ROOT_RC=0`、「unittest 數量下限釘選通過：發現 5179 個測試（下限 5101）」「[M6 id 集合] tools/tests@darwin：✅ 集合關係成立（本次 skip 47 支）」「真實 TEMP 圍籬 … 零變動（前 3／後 3 份）」＝R204 hook 修法與 r86 測試首次在 Mac 本機跑全套的結果；**收尾全套另見〈七〉**。
- **Mac Q4′ JSON 重產 `[主控提供]`**：重產前為 R201 產、R202 拷入評估機的那份（1180 bytes、sha256 0a412725…、mtime 10-05 21:38:15）；`.venv/bin/python tools/session_gate_acceptance.py`（2026-10-06T23:46:47+08:00）rc=0、stderr 0 bytes ⇒ 落檔 `~/.autosdd/traces/session_gate_acceptance_wuweihongdeMac-Studio.local.json` 1180 bytes、sha256 `4873c58c5f35c6f25cc9d9c79e0d467297061c4e95ed21f6ed6c320727ed3516`，stdout 與落檔 `cmp` rc=0（逐位元相同）、`LC_ALL=C grep -c '[^[:print:][:space:]]'`＝0（純 ASCII）、結尾一個 LF（`tail -c 1 | xxd -p` ⇒ 0a）。關鍵格：platform darwin、cc_version 2.1.291、`repo_head` `0da655787699b337af5a4afec0d6531b90753b11`、statusline.installed／matches_current_checkout true、hook_carrier.exists／is_symlink true、verify_hint.default_push_location false／default_lastexitcode false（darwin 期望 False）、check.rc 0、check.diff_line「harness used=219,297 逐字稿 used=219,297 差=0」。原文逐字見附錄 A。

| 檔（平台） | bytes | sha256 | `generated_at` | 效期至 | `repo_head` |
|---|---|---|---|---|---|
| `session_gate_acceptance_Koala-MSI.json`（win32；Mac trace_dir 內的拷入檔，本輪未動） | 1221 | `5a600543dc31c9f75c5bce18fe65c9d621be614444a909d45ea5a88565127b36` | 2026-10-03T22:16:53+08:00 | 2026-10-17T22:16:53+08:00 | 7efc4c06 |
| `session_gate_acceptance_wuweihongdeMac-Studio.local.json`（darwin；本輪重產） | 1180 | `4873c58c5f35c6f25cc9d9c79e0d467297061c4e95ed21f6ed6c320727ed3516` | 2026-10-06T23:46:47+08:00 | 2026-10-20T23:46:47+08:00 | 0da65578 |

起草員唯讀現查 `[他包回報]`：兩檔 bytes／sha256／`generated_at`／`repo_head` 與本表相同（win32 列與 R205〈二〉表同值），darwin 檔與附錄 A 來源檔 `cmp` rc=0；效期＝`generated_at`＋14 天（`q4_max_age_days`）。Windows 評估機 trace_dir 內的 darwin 檔仍是 10-05 那份（0a412725…、2026-10-19T21:38:15+08:00 到期；R205〈二〉量得，之後未再動 `[前輪]`、現況未重驗）。
- **三條指令（主控親跑；輸出檔逐字；stdout／stderr 分收；基線以 params.json 的 `symptom_baseline_since` 原字串代入）`[主控提供]`**：stderr 兩次皆為同一行 96 bytes「ℹ️ --exclude-self 剔除 a8f667b5-de3b-4e2f-a049-aee757d3e64f（subagent 內＝父窗 id）」（sha256 `2f51eed47dac…`）；三個 stdout 檔皆 LF、無 BOM。指令 3 依 R205〈四〉#4 摘錄（保留表頭四行、round=205 列、完整性閘、Q4′ 兩行；省略「窗口內登記」一行與 round=193～203 十一列）。

**指令 1（合併層）** `.venv/bin/python tools/probe/audit_session.py --five-question --exclude-self --record-since 2026-10-03T23:26:09+08:00 --entrypoint cli,claude-vscode,sdk-cli`；2026-10-06T23:47:12+08:00、rc=0；輸出 760 bytes、sha256 `a0e724efe40513f2e5f2251953238b29fe3938671ac5de82ed5866516e7bea51`。母體 5 支＝R201 的 SA 四支探針（958d8c42／83317bd2／84bc2a3b／f0d839c4，sdk-cli）＋R201 主控窗 35be7e5b（cli、auto）；今日 23:03／23:04／23:37 的三支頂層逐字稿（566e677f／5c2b78fc／d95b05f6）與主控兩次 `claude -p`（90193303 等）未入母體（零 tool_use 或非母體入口）`[主控提供]`。
```text
### ②′ 五問量測：母體 5 支（['claude-vscode', 'cli', 'sdk-cli']・起點≥2026-10-03 23:26:09+08:00）
  母體 permissionMode：{'auto': 3, 'acceptEdits': 2}
  Q1′a 誤擋  PASS  0／hook 阻斷 0；無 oracle 0
  Q1′b 宣稱≠阻斷  PASS  0／0 []
  Q1′c 前10呼叫被擋  NOT-EVALUABLE(5/10)  0／5（≤0.25）；首呼叫被擋 0／5
  Q2′ 首查序號  FAIL  逾期或從未 1／1 [('35be7e5b', 11)]；有簡報 1
  Q3′ feed 差  NOT-EVALUABLE(1/3)  1 對；max|差|=0 [0]；NOT-QUIESCENT 0
  Q4′ 本檔不量；九格見 --protocol-status（讀本機 trace_dir 的丙案 JSON；別台的先拷來）
  非 hook 阻斷（auto-mode／人拒絕，不入 Q1′）：無
  hook 阻斷逐筆（oracle＝HEAD 判準重放）：無
```

**指令 2（真實層，不帶 `--entrypoint`）** `.venv/bin/python tools/probe/audit_session.py --five-question --exclude-self --record-since 2026-10-03T23:26:09+08:00`；2026-10-06T23:47:13+08:00、rc=0；輸出 745 bytes、sha256 `8ca70444d1644f6232b6e577f8029960feccff533f8ff1ae94f8bc5b13ad0778`。
```text
### ②′ 五問量測：母體 1 支（['claude-vscode', 'cli']・起點≥2026-10-03 23:26:09+08:00）
  母體 permissionMode：{'auto': 1}
  Q1′a 誤擋  PASS  0／hook 阻斷 0；無 oracle 0
  Q1′b 宣稱≠阻斷  NOT-EVALUABLE(1/5)  0／0 []
  Q1′c 前10呼叫被擋  NOT-EVALUABLE(1/10)  0／1（≤0.25）；首呼叫被擋 0／1
  Q2′ 首查序號  FAIL  逾期或從未 1／1 [('35be7e5b', 11)]；有簡報 1
  Q3′ feed 差  NOT-EVALUABLE(1/3)  1 對；max|差|=0 [0]；NOT-QUIESCENT 0
  Q4′ 本檔不量；九格見 --protocol-status（讀本機 trace_dir 的丙案 JSON；別台的先拷來）
  非 hook 阻斷（auto-mode／人拒絕，不入 Q1′）：無
  hook 阻斷逐筆（oracle＝HEAD 判準重放）：無
```

**指令 3（Mac JSON 重產之後）** `.venv/bin/python tools/probe/audit_session.py --protocol-status`；2026-10-06T23:47:14+08:00、rc=0；輸出 13555 bytes、sha256 `65503075ab8ed75c6c0d29c9e7f74bc904ea971a31552ab97aa4ce7a148b6e36`（darwin 行讀的是 23:46:47 重產的新檔）。
```text
### ②′ 協定狀態
  protocol_sha256=5c9aadf258efbc64f7236c8b4862152c1238edeb99b8fc960c58347acdf90750（manifest 11 檔）
  輪帳本 13 列；window_len=5；評估: NOT-EVALUABLE(5/6)
  （評估僅含家族計數與 p1；Q1′～Q4′ 不在內，見 --five-question 與下列各行）
  …（「窗口內登記」一行與 round=193～203 十一列省略；原文見 `docs/06_quality/FiveQuestion_Round_Ledger.jsonl`）
  輪帳本 round=205 選填欄 {"q1a": "PASS 0/7（合併層 36 支，基線 2026-10-03T23:26:09+08:00；7 筆 hook 阻斷與 R202／R203 同七筆、oracle 皆 correct；+2 支＝R203／R204 主控窗 d60a16cb／9f77189b 入母體；真實層 PASS 0/3；子代理獨立複跑 sha256 逐檔相同）", "q1b": "PASS 0/8（合併層；真實層 PASS 0/0、母體 9 ≥ q1b_min_n；+2 支新窗皆開於 R204 修法 commit 607e804（2026-10-06T14:07:34+08:00）之前＝修法後才開的窗進母體 0 支）", "q1c": "PASS 2/10（合併層；分子仍＝5b4d68fb／cffee7ae 兩支 sdk-cli 探針 seq2 的 Bash 被 block_bash_on_windows.py 正確擋下、餘裕 0；首呼叫被擋 0/10；視窗＝7 支真實＋3 支探針；真實層 NOT-EVALUABLE(9/10) 0/9）", "q2": "PASS 逾期或從未 0/9（真實層 9 支＝R203 的 7 支＋R203 主控窗 d60a16cb 與 R204 主控窗 9f77189b 入母體，逾期 0；有簡報 9；本窗 f6597175 自我排除、下一列起入母體）", "q3": "PASS 9 對 max|差|=0（NOT-QUIESCENT 0）", "q4_win": "PASS（九格全 ✓；JSON generated_at 2026-10-03T22:16:53+08:00，效期至 2026-10-17T22:16:53+08:00；1221 bytes、sha256 5a600543…原封未動）", "q4_mac": "PASS（darwin 九格全 ✓；R202 拷入檔原封未動：1180 bytes、sha256 0a412725…；generated_at 2026-10-05T21:38:15+08:00，效期至 2026-10-19T21:38:15+08:00）", "symptom_streak": 3}
  完整性閘 ✓
  Q4′ session_gate_acceptance_Koala-MSI.json（win32）  PASS  platform✓ statusline.installed✓ statusline.matches_current_checkout✓ hook_carrier.exists✓ verify_hint.default_push_location✓ verify_hint.default_lastexitcode✓ check.rc==0✓ generated_at<=14d✓ repo_head_is_ancestor_of_HEAD✓
  Q4′ session_gate_acceptance_wuweihongdeMac-Studio.local.json（darwin）  PASS  platform✓ statusline.installed✓ statusline.matches_current_checkout✓ hook_carrier.exists✓ verify_hint.default_push_location✓ verify_hint.default_lastexitcode✓ check.rc==0✓ generated_at<=14d✓ repo_head_is_ancestor_of_HEAD✓
```

- **起草員複跑 `[他包回報]`**：2026-10-07T01:05:31～32+08:00 同三條指令（stdout／stderr 分收、rc 皆 0；`--exclude-self` 剔除父窗 a8f667b5…）⇒ stdout sha256 與主控三檔**逐位元相同**（a0e724ef…／8ca70444…／65503075…；指令 3 此時尚未 append 本輪列）——輸出決定論與母體零漂移的旁證、非量測器獨立驗證。
- **三項字面評估（主控；Mac＝他機、不計次）**：項 1 合併層 Q1′a PASS、Q1′b PASS、Q1′c NOT-EVALUABLE、Q3′ NOT-EVALUABLE ⇒ **NOT-EVALUABLE**（四行未全 PASS、無 FAIL）；項 2 真實層 **FAIL**（母體 1 支＝35be7e5b，首查 #11）；項 3 兩平台各一行 PASS 九格 ✓、`generated_at<=14d` ✓ ⇒ **PASS**。params.json（起草員唯讀現查）：`symptom_baseline_since`＝`2026-10-03T23:26:09+08:00`、`symptom_streak_required`＝2、`q1b_min_n`＝5、`q1c_gate`＝0.25、`q1c_n`＝10、`q2_min_n`＝5、`q2_max_index`＝10、`q3_min_pairs`＝3、`q4_max_age_days`＝14。
- **T5 本窗單窗量測 `[主控提供]`**（`--five-question --transcript <本窗 jsonl>`，23:53；不入正式母體）：母體 1 支 {'auto': 1}；Q1′a PASS 0／hook 阻斷 1；Q1′b NOT-EVALUABLE(1/5) 0／1；Q1′c NOT-EVALUABLE(1/10) **1／1**（首呼叫被擋 0／1）；Q2′ NOT-EVALUABLE(1/5) 逾期或從未 0／1（首查 #1）、有簡報 1；Q3′ NOT-EVALUABLE(0/3)、NOT-QUIESCENT 1（在途）；hook 阻斷逐筆 1 筆＝`{"date": "2026-10-06", "sid": "a8f667b5", "seq": 5, "tool": "Bash", "kind": "hook", "by": "block_destructive_git.py", "oracle": "correct"}`（主控自己在 `git status` 之後接管線讀 rc，判準④ 正確攔截）。

## 三、子代理摘要 `[他包回報]`（token／呼叫取自 harness 完成通知面值，主控未另算；子代理皆 Sonnet）
- **SA**（唯讀；只動 scratchpad 內臨時 clone；約 569,016 token／148 次呼叫／52.2 分鐘）：**推薦方案 A、建議動工**。① 根因＝歷史 commit `db4a542` 於引號內轉述一句被修掉的承接句 `「193／199／242 承接 R198」`，命中帳本 SSOT 承接樣式、n=198 ≥ cur=100（帳本「發現情境」欄時鐘凍結）、段落無已結 DEF-ID（`DEF-200-xxx` 非 ID、`193／199／242` 為裸數字）⇒ 帳本須恆留一列未結承接 ≥198（490→499→501→503→504 五列接力）；以 `main()` 同款取數重現：現況 0 筆、504 結案且不補後繼列＝恰 1 筆（db4a542d；主控粗重現的 29 筆＝done_ids 誤傳空集合的假象）。② 全史（`_DEFER_RES` 8 樣式 × 732 則 commit 全部段落）61 命中／47 commit，首個有效出口 done_ids 45／n<cur 10／carriers 6，落在「」內 9 筆；併 193 份載體後引號內命中共 38 筆（commit 9＋載體 29），逐筆讀原文 38／38 為敘事轉述、0 筆真交派。③ 否決：B（sha／日期祖父化）——落地 commit 7fbdf9b5（2026-08-24）早於 db4a542d（2026-10-04）304 commit／41 天，不解本案，B2 後移錨＝708／732 永久免檢＝具名豁免換名；C（裸數字＋家族前綴）——真倉庫過度授予 19 段、真交派被吃 1 筆；D（承接族回顧）——真交派被吃 12／16（`<ID 或數字列> 承接 R<N>` 正是真宣告的標準句型）；E 系列（慣例／git 推時鐘／常設錨列／閘門名放行）——不解歷史、或撤銷 DEF-200-241 的不讀時鐘裁決、或可被一個詞繞過。④ 成本：工具 +23／−2（651→672 行）、測試 22 增 22 刪（3904→3904 行）、`--print-guard-lines` 淨額 114350→114350（+0）、self-test 30→34 PASS、零新檔。⑤ 全新 clone（HEAD 0da65578）套兩份 diff 後：self-test PASS=34／FAIL=0、全史 gate rc=0、模擬 504 結案不補後繼列 rc=0（未修版 rc=1 恰 db4a542d）、crossref 269 OK、c1c2 192 OK、ruff `All checks passed!`、LOC 該檔 assertion 405（上限 750）；r60 281、platform_neutral_paths 177、subprocess_encoding_hygiene 39、check_wrapper_thinness 45、pre_push_dispatcher 37、root_infra_parity 13、check_script_parity 124、guard_line_taxonomy_r99 8、defect_id_reference_integrity 11 共 9 模組逐一 OK。⑥ 殘餘：2a74853d p#1 與 5c724baa p#10 的段落無已結 DEF-ID，靠 DEF-200-129／DEF-200-207 撐著（〈四〉4.x #3）。
- **Developer**（Sonnet；單人串行、只套 SA 兩份定稿 diff；harness 完成通知 119,655 token／29 次呼叫／7.0 分鐘）：`git apply --check` 兩份 rc=0、`git apply` rc=0、numstat 23/2 與 22/22、`wc -l` 3904、`git diff --check` rc=0；紅→綠：以 `git show HEAD:… >` 暫還原 HEAD 版工具後對 TestDef200241＋TestDef200212 兩類 Ran 10 ⇒ rc=1、恰 1 FAIL＝`test_a_quoted_narrative_is_not_a_deferral_claim`，重套 diff 後 Ran 10 OK；self-test 34 PASS／0 FAIL；全史 rc=0、census 85／34；模擬 504 結案 problems=0；crossref＋c1c2 Ran 461 OK；`--print-guard-lines` 淨額 +0；ruff All checks passed；LOC root_tools_violations=[]、該檔 assertion 405；r60 Ran 281 OK（104 s）；鄰近 8 模組 OK（pre_push_dispatcher 37／root_infra_parity 13／check_wrapper_thinness 45／platform_neutral_paths 177／subprocess_encoding_hygiene 39／guard_line_taxonomy_r99 8／defect_id_reference_integrity 11／check_script_parity 124）；工作樹兩檔 diff 與 SA 定稿 `cmp` 相同；唯一非 diff 寫入＝紅面暫還原、已重套。輸出 `dev_*.txt` 33 支 `[他包回報]`；主控親驗見〈六〉。
- **QA**（Sonnet 唯讀零信任鏡；434,114 token／145 次呼叫／30.3 分鐘；零 git 寫入）：**APPROVE、NEW_P_LE_2 0**。A 三條指令複跑 sha256 與主控逐位元相同（母體 5／1 無漂移）、append 後 `--protocol-status` 14 列／window_len 6／round=206 streak 0／完整性閘 ✓／Q4′ 兩行 PASS；B darwin JSON 三處一致、`q4_cells` 9/9 True、附錄 A 抽取＝1180／4873c58c…；C numstat 23/2、22/22，staged diff 與 SA 定稿 `cmp` 相同，self-test 34（HEAD 版 30），全史 rc=0 census 88／34（含本檔 3 筆），spec_sim 0，guard-lines +0，ruff／LOC／crossref 269／c1c2 192／r60 281 OK，紅面（HEAD 工具記憶體注入、零檔案寫入）恰 1 FAIL，引號普查複現 38；D 史料 7 段 22 行逐段在附錄 B；E 新增行零裸輪號、r71 類 10 OK；F 505 列 692 bytes／504 列 688、crossref 未結 29→29、淨額 新增 0／結案 0、前瞻延後句 2 行皆帶 DEF-200-504；G 主控文字逐項對原始檔無造假、P4→P3 六處一致、D2／D3 前提屬實、〈八〉配方 Python 原字串實跑＝1180／4873c58c…；H T5 與主控一致；I 全套 log 複核 ROOT_RC=0、5180 支、TEMP 圍籬 advisory 真因＝主控 01:25:57 的 `--pace`（非 QA、非測試洩漏）。訂正 10 條（P3×2：TEMP 圍籬真因、D1 引文省略「宣告前」限定；P4×8）本輪全數處置（〈六〉）。意見：R1′ 文本上同樣自洽、建議下次 PROTOCOL-CHANGED 視窗消歧（已登 P3）；決策卡「暫不再排 Mac 他機輪」正確；引號濾網殘餘風險屬構造性、計 0。
- 主控（Fable 5.1）兼 Architect；子代理皆 Sonnet（SA、Developer、QA、本檔起草員）；派工前皆先 `--pace`（可派 4，見〈二〉）。

## 四、裁決與落地
| # | 裁決 | 落地 |
|---|---|---|
| D1 | **`symptom_streak` 寫 0（採讀法 R2）**：README〈窗口規則與收斂判定〉有兩句字面各自成立——他機條款（結果入 `note`、不計次、streak 沿用上一列）與計次條款（任一機任一輪任一行 FAIL ⇒ 寫 0），碰在他機輪次出現 FAIL 的情形。**R2（採）**＝FAIL 不被他機條款吸收：R201〈四〉4.3 #4 於 FAIL 出現前已載明『排程風險＝若 R203 宣告前再排 Mac 五問輪，指令 2 會對本窗印 FAIL（…）並依 README「任一機任一輪任一行 FAIL ⇒ 寫 0」歸零 ⇒ 決策卡 #2 明寫「R203 前不排 Mac 五問輪；之後若排，先讀本條」』（該句的情境限定是「宣告前」；本輪屬宣告後：歸零不撤回已宣告的收斂、只影響評估機下次起算），DEF-200-499 的「現象與證據」欄亦寫「會讓下次 Mac 指令 2 判 FAIL 並歸零 streak」——先例預先公開、非事後挑選。**R1′（不採）**＝他機條款是他機專條、「任一機」只指 Q4′ 的 win32／darwin 兩行；字面同樣成立，且與宣告範圍（評估機行為面＋兩平台 Q4′、Mac 行為面未驗）更自洽，但在 FAIL 出現當下換讀法保住 streak＝自利解釋。兩句字面衝突登記 P3（沿用 R201 SD-201-04 的分級；協定凍結、不改；下次 PROTOCOL-CHANGED 視窗一併修，〈四〉4.x #1）。**效果**：R203 的宣告為歷史事實、README 無撤回條款；再評仍只由〈守衛面准入〉觸發；評估機下次達標從 0 起算 | 輪帳本 R206 列 `symptom_streak` 0、`window_reset` false；README 原文如下 |
| D2 | **FAIL 的升級判定＝零 Developer、零守衛碼（五問面）**：FAIL 樣本＝35be7e5b（R201 主控窗）首查 #11；成因＝掌舵者貼入的啟動提示詞為舊副本、缺 useMacWin.md 第 0 步（R201〈四〉4.3 #4 三方同向裁決「已知成因真陽性、協定不改」，成因在 repo 外；第 0 步自 a5d2c9fc 2026-10-03 起已在 SOP `[前輪]`）⇒ 無碼面修法對象；操作面補救已生效（本窗首查 #1，〈二〉T5）。該樣本離開逐字稿保留期前，Mac 真實層指令 2 結構上恆 FAIL（`audit_session.py:869-870`：`show("Q2′ 首查序號", …)` 以 `bool(late)`〔:870〕為 bad、無 n≥`q2_min_n` 守門；`show()` FAIL 優先 :851-855；Q1′c 的 n 守門在 :868）⇒ 決策卡：期間不再排 Mac 他機輪次，或掌舵者修憲改他機 FAIL 處置（〈八〉(2)；帳本載體 DEF-200-504） | 輪帳本 R206 列 q2 欄與 note |
| D3 | **DEF-200-499 不重開**：其狀態欄「重開＝掌舵者 Mac 真機回報症狀 sid，或 Mac 一般窗指令 1／2 FAIL」字面被本輪指令 2 FAIL 命中，但命中樣本正是該列「現象與證據」欄點名、立列時已知的 35be7e5b（非新 Mac 真實窗、零新資訊）⇒ 不重開；本檔明載、帳本 499 列不動 | 帳本 499 列（不動） |
| D4 | **DEF-200-504 維持 open、承接輪次 R206→R207（同長度替換）**：第一項（darwin JSON 重產）完成；餘兩項（win32 JSON 效期 2026-10-17T22:16:53+08:00、ONBOARDING §7 表③ nightly 錨 2026-10-20T09:57:51+08:00 起轉紅）未到期。主控已於工作樹編修 504 列：darwin 效期字串 2026-10-19T21:38:15+08:00→2026-10-20T23:46:47+08:00、承接輪次 R206→R207（皆同長度）；方案 A 落地後「兼 carriers 判準① 承接列」改「carriers 承接義務已解除」（HEAD 版 690→688 bytes，縮短 2 bytes、≤700 合規；起草員現查工作樹該列為 688 bytes）。殘餘非引述型長期義務由 DEF-200-129／DEF-200-207 撐著（〈四〉4.x #3） | 帳本 504 列 |
| D5 | **carriers 判準① 方案 A 動工**（SA 推薦、主控裁決）：理由＝零時鐘（不違 DEF-200-241 裁決）、零具名豁免、沿用既有 SSOT `CORNER_QUOTE_RE`、38 筆引號內命中逐筆皆轉述（0 真交派）、全新 clone 紅→綠與逐項驗收（含 9 模組）皆通過 `[他包回報]`、碼面單函式可逆。落地＝兩份 diff：`tools/check_handoff_carriers.py` +23／−2（import 一行＋7 行 WHY 註解＋`_narrative_hit()` 第二條件＋self-test +4 條〔30→34 PASS〕）、`tools/tests/test_check_defect_log_crossref.py` 22 增 22 刪（3904→3904 行；新測試 `test_a_quoted_narrative_is_not_a_deferral_claim`＋附錄 B 所列 7 段史料壓縮／改字（含移除 R102 座標列））；不碰守衛面、`main()`、`_DEFER_RES`、gate。測試走淨 0 行以免動整條護欄行數重釘鏈（SA clone 實測：不淨 0 而加 35 行＝c1c2 3 支紅）。**DEF-200-505 當輪 born-fixed**（出生即已結，未結存量不增、淨額 0；以〈六〉crossref 實測為準）；史料壓縮的原文逐字搬附錄 B。SA 動工時踩的三個陷阱（零裸輪號、保留路徑 token 以免翻進 prose 桶、只套兩份 diff 不碰帳本）已吸收進定稿 diff | 工具＋測試兩檔；帳本 505 列；附錄 B |

D1 引文（README〈窗口規則與收斂判定〉逐字，含原換行；第二句括號內的 HUMAN-REVIEW 處置略）：
```text
他機輪次照跑三項，結果以
`[他機:<host>] PASS|FAIL|NOT-EVALUABLE（母體 N 支）` 寫入該列 `note`、不計次、`symptom_streak` 沿用上一列。
計次只在評估機輪次：三項同時成立＝一次評估達標 ⇒ `symptom_streak`＝上值 +1；任一機任一輪任一行 FAIL ⇒ 寫 0（…）
```

### 4.x 登記不修清單（本輪只登記）
| # | 嚴重度 | 內容 | 不修理由 |
|---|---|---|---|
| 1 | P3 | README 他機條款與計次條款字面衝突（D1）；R201〈四〉4.4 以 SD-201-04 登記同一衝突（P3、當時潛伏），本輪實際觸發一次 ⇒ 沿用 P3、不降級 | 協定凍結（sha 5c9aadf2…）、不改；下次 PROTOCOL-CHANGED 視窗一併修 |
| 2 | P4 | Mac 真實層在 35be7e5b 離開逐字稿保留期前，指令 2 結構上恆 FAIL（D2）⇒ 期間任何 Mac 他機輪次都會把評估機累積的 streak 再歸零（排程風險） | 成因在 repo 外；改法（修憲）屬掌舵者；決策卡見〈八〉(2)（帳本載體 DEF-200-504） |
| 3 | P4 | 殘餘非引述型長期義務：commit 2a74853d 段落 #1（無引號轉述閘門訊息）與 5c724baa 段落 #10（真交派 `R109 承接`）的段落無已結 DEF-ID，靠 DEF-200-129（帳本承接輪次 112）與 DEF-200-207（帳本承接輪次 117+）撐著；模擬 504＋129＋207 全結案 ⇒ 判準① 再紅這兩筆 `[他包回報]` | 方案 A 只解引述型；結案 DEF-200-129／DEF-200-207 之前先看本條 |
| 4 | P4 | SA 任務書「232 位元組以上」語病：該量無對應；SA 讀成全史 732 則並預先切兩種讀法——（a）本檔自加三族（留／延後至／交給）命中 9 筆（db4a542d 不在其中）、（b）段落 ≥232 位元組命中 54／61 筆（db4a542d 段落 382 位元組） | 結論不依賴所指為何（方案 A 以語法標記判準、不用位元組門檻）；任務書筆誤、登記 |
| 5 | P4 | 引號濾網誠實劃界（DEF-200-505）：作者把整句真宣告包進「」會被遮（`「皆留 R207」` 這類，`defer_rounds()` 回空；與既有反引號 code span 同級缺口）、commit 段落內跨行成對引號會遮中間句、巢狀只遮最內層、未閉合不遮；載體逐行判、跨行引號不遮；真倉庫 0／38 | 構造性、無暴露；整句真宣告包引號在體例上不自然（SA）；`[他包回報]` |

## 五、誠實劃界與未驗（不塗綠）
1. **Mac 行為面仍「未驗」，且本輪 FAIL 不是行為面症狀樣本**：母體內 Mac 真實窗只有 35be7e5b（R201 的切換與審查窗），其餘 4 支是 R201 的 headless 探針；Q1′a／Q1′b 的 PASS 只證這 5 支零誤擋、零無依據宣稱，不是 Mac 一般窗在修法後已驗證。
2. **Q2′ FAIL 的性質**：n=1 ＜ `q2_min_n` 5 但工具 FAIL 優先；分母只含 ≥ `q2_max_index`（10）個工具呼叫的 session，35be7e5b 首查 #11 ＞ 10 ⇒ 逾期。這是已知成因真陽性、不是新症狀；本窗（首查 #1）只證操作面補救生效、不是修法驗證。
3. **環境類**：第一次 `claude -p` 跑錯目錄（〈二〉hook 條）＝無效量測、已重做，第一次的 h.log 已刪、不作數；dev_start 警告 1 件＝`ci_liveness`（含 1 句實測「aisdlc-sdd-drift-daily.yml 最近成功於 14 天前」＋結構宣告；a7a3080 2026-08-07 起既有、R205 同形，非本輪新增）。
4. **SA 的臨時 clone**：建於 scratchpad 內、已刪（起草員現查目錄不在 `[他包回報]`）；是 SA 唯一的 git 寫入，只動 clone、不動 repo。
5. **收尾才量得的項**：`MIN_TESTS` 零相依 loss 未量（本輪 +1 測試；全套若印「MIN_TESTS 該重釘了」才重釘；SA 規格 §6 `[他包回報]`）；雲端 compat CI 尚未觸發（`windows-compat-ci`／`macos-compat-ci` 的 paths 白名單含 `tools/check_handoff_carriers.py`，改檔會觸發，`fetch-depth: 0` 故 db4a542 取得得到；push 之前＝未驗證；SA 規格 §9 `[他包回報]`）——回填見〈七〉。
6. **Windows 側拷回待做**：新 darwin JSON 尚未進評估機 trace_dir ⇒ 評估機 `--protocol-status` 的 darwin 行讀的仍是 10-05 那份（2026-10-19T21:38:15+08:00 到期）直到拷回；配方見〈八〉(1)（帳本載體 DEF-200-504）。
7. **`[他包回報]` 數字主控未重驗者**：SA 的 token／呼叫、61／47／38 普查、B／C／D 的假陰性計數（B 2＋B2 3＋1、C 1＋1、D 12／16）、clone 驗收各數字。起草員（Sonnet）只對三條指令輸出、Q4′ 兩檔、`h.log`、params.json、既有檔與工作樹做了唯讀重數；Developer／QA 的重驗見〈三〉〈六〉。
8. **本窗 a8f667b5 自我排除**（`--exclude-self`）、不在本輪母體；下次他機輪次若它入母體：Q1′c 分子 +1（正確攔截亦計）、Q2′ 首查 #1 不逾期（T5）。
9. **宣告是協定上的宣告；改動面是計畫**（以〈六〉numstat 為準）；〈三〉〈六〉已回填；〈七〉的 push／雲端由回填 commit 補。

## 六、收尾親驗（主控親跑；本場 tool_result）
- 套用（主控親手、python 腳本、每處斷言恰 1 命中）：證據檔 223 行 43,988 bytes（起草稿三處修訂：README 衝突 P4→P3 六處、〈二〉「推定」改 `date` 戳記）；輪帳本 13→14 列（R206 列 17 鍵、`json.loads` 可解析）；帳本 505 列插於 504 列後（692 bytes）、504 列 688 bytes；`tools/lib/governance_docs.py` 第 634 行後 +5 行；`git add -A` 後 `git diff --cached --numstat`：2/1 帳本、223/0 本檔、1/0 輪帳本、23/2 工具、5/0 governance、22/22 測試；`git diff --cached --check` rc=0；本檔 CR 0。
- `--protocol-status`（append 後）⇒「輪帳本 14 列；window_len=6；評估: PASS」（資訊欄：family 計數 window_len 6 ≥ `rounds_required` 6、`new_p_le2` 合計 0、`p1` 0——自 R197 起非收斂依據，與 `symptom_streak` 0 不矛盾）、round=206 列 `"symptom_streak": 0`、「完整性閘 ✓」、Q4′ win32／darwin 兩行 PASS 九格 ✓；PS_RC=0。
- 閘門（套用後、QA 派出前）：`check_defect_log_crossref.py` rc=0「帳本 206 筆有效狀態紀錄…具名治理文件 158 份皆已登記…未結存量 29 列」（505 born-fixed ⇒ 新增 0 未結、淨額 0，不走 `AUTOSDD_NET_RATCHET_OFF`；warning 15 行＝組成同 R205）；`check_handoff_carriers.py` rc=0「✅ 每一筆前瞻延後宣稱都有帳本承接載體」（194 份載體、前瞻延後行 88、commit 宣告 34）；`check_loc_budget.py --json` rc=0、root_tools_violations=[]；`ruff check tools/ .claude/hooks/ --no-cache` All checks passed；`--print-guard-lines` 淨額 114350→114350 (+0)、逐檔漂移 0；守衛面 `git diff --cached --numstat -- .claude/hooks .claude/settings*.json tools/lib/{session_brief,quota_messages,harness_feed,quota_gate,quota_policy,quota_stability,sentinel_lifecycle}.py tools/session_resume_planner.py` ⇒ 0 行。
- 主控親驗 Developer 成果（不採信回報）：self-test 34 PASS／0 FAIL「✅ 全部通過」；全史 rc=0、census 85／34（登記本檔前）；numstat 23/2＋22/22；`wc -l` 672／3904；紅→綠 log：`dev_2_red.txt` Ran 10 FAILED (failures=1) 恰 `test_a_quoted_narrative_is_not_a_deferral_claim`、`dev_2_green.txt` Ran 10 OK。
- QA 十條訂正處置（主控親改、皆文字面）：#1 〈七〉TEMP 圍籬真因照實寫（主控自己的 `--pace`）；#2 D1 引文還原「宣告前」限定並補「歸零不撤回宣告」；#3 第一次全套時刻改逐字稿轉錄值；#4 T5 23:53；#5 「括號內」；#6 三次 `--pace` 標「量測於」並補 QA 派工前那次；#7 附錄 B 首行去指示語、D5 改「7 段」；#8 dev_start 警告改「含 1 句實測＋結構宣告」；#9 〈八〉配方改絕對路徑＋`AUTOSDD_TRACE_DIR` 並由主控在 Mac 實跑驗證；#10 13 處回填標記全數填實。訂正後本檔由 pre-push 全套重驗（〈七〉）。
- 起草員備稿自驗（唯讀；只動 scratchpad 暫存副本與函式呼叫，未寫 repo、零 git 寫入；2026-10-07 約 01:18）`[他包回報：起草員]`：① 本檔 json 圍欄以〈八〉(1) 的抽取法（同一 Python 內核）還原＝1180 bytes、sha256 `4873c58c…`、與附錄 A 來源檔逐位元相同；② 本檔的 README 引文、附錄 B 全文、三條指令圍欄與原文逐字相同（Python `in` 比對）；③ 以工作樹現行（已套方案 A）的 `check_handoff_carriers` 判：`carrier_doc_problems()` 對本檔（`_REPO_ROOT` 暫指 scratchpad）＋含 505 列的模擬帳本 problems 0，前瞻延後行 2 條（D4 列、〈七〉）皆同行指名 DEF-200-504，關掉引號濾網（HEAD 版行為）重判亦 0；`commit_carrier_problems()` 對現有 732 則 commit：504 open problems 0、模擬 504 結案且不補後繼列 problems 0（HEAD 版濾網＝1 筆 db4a542d），census（不含本檔）85／34；④ 本檔 8 個 DEF-ID 引用皆在帳本家族有列（505 取模擬）、`_RATE_RE` 0 命中、LF／無 BOM／結尾單一換行；⑤ 含 505 列的模擬帳本過 crossref 純函式（欄數、首詞、孤兒承接、未指派承接、狀態變體、逐列 ≤700 bytes、當前輪時鐘、首詞待更新）前後問題數皆 0，`residual_todo_notes` 2→2、未結存量 29→29；輪帳本 R206 列 append 後的模擬 `--protocol-status`＝14 列、window_len=6、完整性閘 ✓、Q4′ 兩行 PASS；⑥ 登記片段插入 `tools/lib/governance_docs.py` 暫存副本後 `ruff check`（tools/ruff.toml）rc=0、`ast.parse` OK；⑦ 工作樹兩檔相對 HEAD 的 diff 與 SA 兩份定稿 diff 逐位元相同（`cmp` rc=0、`--no-optional-locks`）、`wc -l` 672／3904。

## 七、根層全套、push 與雲端驗收（主控親跑；本場 tool_result）
- 根層全套第一次（HEAD 版、套用前；23:40:56～23:42:54）`ROOT_RC=0`、5179 支、M6 skip 47、TEMP 圍籬零變動（〈二〉）。第二次（套用後、QA 派出後；01:25:36～01:27:33）`ROOT_RC=0`「✅ unittest 數量下限釘選通過：發現 5180 個測試（下限 5101）」「[M6 id 集合] tools/tests@darwin：✅ 集合關係成立（本次 skip 47 支）」、無 MIN_TESTS 重釘訊息；**TEMP 圍籬 ❌ advisory（不改 rc）**「autosdd_pace.json（變更）、autosdd_pace_fable.json（變更）」——真因＝主控自己在 01:25:57 跑 `--pace`（派 QA 前現查；`pace_pre_qa.txt` 與兩檔 mtime 同秒），落在全套視窗內；非測試洩漏、非 QA（其首呼叫 01:26:54 在後）`[QA 轉錄]`；主控先前猜「QA 的 hook 在寫契約檔」是錯的（錯誤訊息不是根因，量到時間戳才是）。處置＝全套結束後在真實 session 重跑 `--pace` 覆寫真值（量測於 2026-10-07T01:58:51+08:00、可派 4、weekly_scoped 13%），第三次全套在無並行子代理、無 `--pace` 的條件下重跑：第三次（02:01:00～02:03:05；`AUTOSDD_SENTINEL_OFF=1`、背景阻塞、log 落 scratchpad、rc 寫檔不接管線）`ROOT_RC=0`「✅ unittest 數量下限釘選通過：發現 5180 個測試（下限 5101）」「[M6 id 集合] tools/tests@darwin：✅ 集合關係成立（本次 skip 47 支）」「✅ 真實 TEMP 圍籬 … autosdd_pace*.json 零變動（前 3／後 3 份）」；log 內 FAIL／ERROR 行 0；無 MIN_TESTS 重釘訊息（+1 測試仍在零相依餘裕內）。
- commit／push／雲端：本 commit 的 push（pre-push 各 leg）、`gh run watch` 與 `gh run list --commit <完整 sha>` 由〈七〉回填 commit 補（同 R205 體例；本輪改了 `tools/check_handoff_carriers.py` 與 `tools/tests/**`，兩平台 compat CI 的 paths 白名單會觸發；未觸發或缺席＝未驗證、非通過）。
- 本〈七〉回填 commit 的雲端 run 由下一個 R 輪開場對帳（對帳項、非承接項；帳本載體 DEF-200-504、承接輪次 R207）。

## 八、交棒／掌舵者側待辦
- **(1) Windows 拷回 darwin JSON（帳本載體 DEF-200-504）**：先 `git pull --ff-only` 到含本輪 commit 的 HEAD（0da65578 已在其祖先內）；把本檔附錄 A 的 json 圍欄內文補一個結尾 LF 後，存入 `%USERPROFILE%\.autosdd\traces\session_gate_acceptance_wuweihongdeMac-Studio.local.json`（取檔內**最後一個** json 圍欄；同 R201〈八〉配方，檔名與驗收值換成本輪）：
  ```powershell
  & (Join-Path (git rev-parse --show-toplevel) '.venv\Scripts\python.exe') -c "import sys,os,hashlib,pathlib,re; f=chr(96)*3; root=pathlib.Path(sys.argv[1]); md=(root/'docs'/'06_quality'/'CrossPlatform_R206_FiveQuestion_MacRound_Q4Regen_CarriersQuoteFilter_Evidence.md').read_bytes().decode('utf-8'); m=re.findall(f+r'json\r?\n(.*?)\r?\n'+f, md, re.S)[-1]; b=(m.replace('\r\n','\n')+'\n').encode(); d=pathlib.Path(os.environ.get('AUTOSDD_TRACE_DIR') or (pathlib.Path.home()/'.autosdd'/'traces')); d.mkdir(parents=True, exist_ok=True); t=d/'session_gate_acceptance_wuweihongdeMac-Studio.local.json'; t.write_bytes(b); print(len(b), hashlib.sha256(b).hexdigest(), t)" (git rev-parse --show-toplevel)
  ```
  驗收＝印出 `1180 4873c58c5f35c6f25cc9d9c79e0d467297061c4e95ed21f6ed6c320727ed3516 <落檔路徑>`（snippet 純 ASCII、無反引號字面——PowerShell 雙引號內反引號是逸出字元，故以 `chr(96)` 組出圍欄；repo 根由 `git rev-parse` 當 argv 傳入、證據檔路徑絕對化、trace 目錄先看 `AUTOSDD_TRACE_DIR` 再退 `~/.autosdd/traces`，同 `tools/lib/endurance_env.py`）；主控已在 Mac 以 `AUTOSDD_TRACE_DIR` 指向暫存目錄實跑同一 Python 原字串 ⇒ `1180 4873c58c…`、與本機 trace_dir 檔 `cmp` 相同（PowerShell 外殼未在 Mac 驗）`[主控提供]`；再跑三條指令，指令 3 須印 win32／darwin 兩行 PASS 九格 ✓（darwin 行 `generated_at<=14d` ✓）；Windows JSON 若已過 2026-10-17T22:16:53+08:00 須先重產。
- **(2) 決策卡（主控依「最理想」代決；無人看管時維持現狀）**：① `symptom_streak` 歸零＝採讀法 R2、對立讀法 R1′ 登記 P3 不採；掌舵者若要改採 R1′ 或讓他機 FAIL 只入 `note` 不歸零，須走修憲（協定 reset＝輪帳本列 `window_reset: true`，streak 已是 0 故無損；協定 sha 5c9aadf2… 凍結中）；② Mac 他機輪次暫不再排——35be7e5b 離開逐字稿保留期前指令 2 結構上恆 FAIL（〈四〉4.x #2；帳本載體 DEF-200-504）；③ DEF-200-504 餘兩項到期日：win32 JSON 2026-10-17T22:16:53+08:00（過期後任何再評先重產）、ONBOARDING §7 表③ nightly 錨 2026-10-20T09:57:51+08:00 起轉紅（須在此前依 SOP 第 6 步回填）；darwin 新檔效期 2026-10-20T23:46:47+08:00（拷回後生效）；④ 新視窗照舊：第一個工具呼叫＝`--check`／`--pace`（useMacWin.md 第 0 步；**啟動提示詞請從 useMacWin.md 現行版複製**），看到「被擋」字樣當下貼畫面原文＋session id＋機器 ⇒ 依〈守衛面准入〉重開。
- **(3) 日曆鎖**：Q4′ JSON 效期——win32 2026-10-17T22:16:53+08:00（最緊）、darwin 新檔 2026-10-20T23:46:47+08:00（拷回評估機後；Windows 現存舊檔 2026-10-19T21:38:15+08:00 到期）；ONBOARDING §7 表③ nightly 錨 2026-10-20T09:57:51+08:00 起轉紅（帳本載體 DEF-200-504）；ruff E501 豁免 11-03 起紅（`tools/ruff.toml` 到期 2026-11-02）、棘輪 `live_repin_round()`＝196、款(12) due 198、Phase 2 due 200（零重釘輪不觸發）`[前輪：R205〈八〉]`；本輪 tools/tests 淨 0 行（SA clone 實測 `--print-guard-lines` 淨額 114350→114350 `[他包回報]`）⇒ 零重釘輪，實況見〈六〉。

## 附錄 A：Mac Q4′ JSON 原文（`~/.autosdd/traces/session_gate_acceptance_wuweihongdeMac-Studio.local.json`，1,180 bytes、純 ASCII、結尾一個 LF；Windows 以同檔名存入 `%USERPROFILE%\.autosdd\traces\`，不得手改；sha256 `4873c58c5f35c6f25cc9d9c79e0d467297061c4e95ed21f6ed6c320727ed3516`；抽取法＝取本圍欄內文＋補一個結尾 LF，與 R199 附錄 A／R201 附錄 B 同法）
```json
{
  "schema": "session_gate_acceptance/1",
  "generated_at": "2026-10-06T23:46:47+08:00",
  "platform": "darwin",
  "os_label": "mac",
  "host": "wuweihongdeMac-Studio.local",
  "python_version": "3.11.15",
  "cc_version": "2.1.291",
  "repo_head": "0da655787699b337af5a4afec0d6531b90753b11",
  "statusline": {
    "installed": true,
    "matches_current_checkout": true,
    "python_basis": "repo-venv",
    "settings_file_exists": true
  },
  "hook_carrier": {
    "path": ".venv/Scripts/pythonw.exe",
    "exists": true,
    "is_symlink": true
  },
  "verify_hint": {
    "default_push_location": false,
    "default_lastexitcode": false,
    "windows_variant_both": true
  },
  "fsm_current_state": "SPEC_DRAFTING",
  "fsm_line": "SDD FSM\uff1acurrent_state=SPEC_DRAFTING\uff08\u72c0\u614b\u6a94 /Users/wuweihong/Antigravity/AISDCL_Agent/AISDLC_SDD/AISDLC_SDD_v0.30/build/reports/fsm/FSM-STATE-AISDLC_SDD.yaml\uff0cmtime 2026-09-11T00:44:57+08:00\uff09",
  "check": {
    "rc": 0,
    "diff_line": "harness used=219,297 \u9010\u5b57\u7a3f used=219,297 \u5dee=0",
    "lines": 13,
    "banner": null,
    "stderr": null
  },
  "trace_dir": "/Users/wuweihong/.autosdd/traces"
}
```

## 附錄 B：〈史料搬遷〉——方案 A 測試 diff 淨 0 行的來源（`test_check_defect_log_crossref.py` 移除的原文，HEAD 行號，逐字保全）
```text
# 史料搬遷清單：方案 A 測試 diff 從 test_check_defect_log_crossref.py 移除的原文（HEAD 行號；逐字保全；已搬入本附錄）

## HEAD L60–L62（3 行）
    合成帳本」在這道鎖下不是中性輸入而是**必紅輸入**：R60 加鎖後既有 4 支 `TestMain`
    就是這樣紅的，紅因（抽不到散文）與各自要驗的行為（含糊列分開計數／輪替預警帶）
    毫無關係，屬 fixture 沒跟上主檔演化，不是被驗行為退化。

## HEAD L1458–L1459（2 行）
    承接載體」真的接進閘門輸出的唯一憑證，不是函式存在就算數（`ledger_def_ids()` 落地
    後、本包接線前的歷史窗口是「函式已落、`main()` 沒接線」的假接線狀態）。

## HEAD L1490–L1492（3 行）
#: DEF-200-241 治本前，具名豁免面承載的五筆真實假陽性座標（DEF-200-212 D4／D8）。
#: 治本後生產表為空，這五筆改由 `done_ids`（帳本已結事實）自然出局；本表在此只當
#: 回歸鎖的**注入母體**：拿掉 done_ids 時它們必須逐筆復發，證明新判準真的在承重。

## HEAD L1494–L1494（1 行）
    ("docs/04_planning/R102_HANDOFF.md", "DEF-200-204"),

## HEAD L1503–L1511（9 行）
    """DEF-200-241 方向 B（R121 裁決卡；R126 四方設計複審 4×APPROVE 後動碼 round-label-ok）：
    受測＝`tools/check_handoff_carriers.py` 判準② 的祖父化改讀**帳本結案事實**——前瞻行指名的
    DEF-ID 一旦在帳本家族內結案（狀態欄首詞分類 ∉ `_UNRESOLVED_CLASSES`）即出局，
    不比輪號、不依賴凍結的時鐘；DEF-200-212 時期的具名豁免面（5 筆，天花板 5）隨之
    清空、天花板降 0。本類鎖住：①真倉庫 strict＋done_ids 零假陽性；②拿掉 done_ids
    時五筆舊假陽性逐筆復發（新判準真的在承重，不是恰好沒用到）；③豁免表清空且天花板 0
    （shrink-only 方向）；④合成：已結出局／未結仍承接／查無列仍紅／版面解析不到不猜；
    ⑤豁免**機制**三性質以合成表驗（精確命中、不整檔放行、理由太短不算登記）——生產表
    為空不代表機制可以退化。

## HEAD L1536–L1536（1 行）
        """🔴 紅綠自證的主牙：拿掉 done_ids（傳空集合）⇒ 五筆舊假陽性座標必須逐筆復發。

## HEAD L1585–L1587（3 行）
        立案實例＝commit `0398226`（「已列 R118 交棒書呈報裁決」段落指名 212） round-label-ok
        212／241 結案後帳本再無承接輪 ≥ R118 的未結列 ⇒ 沒這條，做完事讓判準① 轉紅 round-label-ok
        """
```
