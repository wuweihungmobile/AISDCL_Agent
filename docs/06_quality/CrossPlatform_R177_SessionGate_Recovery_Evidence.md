# CrossPlatform R177 — 掌舵者五問四方審查／SessionGate 恢復指令自我阻斷結案證據檔

> 輪次：ctx5（2026-09-27，mac，Apple M1 Max；主控 Fable 5.1，子 agent 皆 Sonnet 5）。
> 流程：AISDLC 精簡版——四方（Architect／SA／SD／QA）唯讀分析 → 每方兩位反駁者（重現正確性／範圍治理）
> 對抗式覆核 → 主控裁決 → 兩個 Developer 包（檔案互斥並行）＋ QA 探針 → 兩鏡複審 → 主控收尾單人窗口。
> 前輪：`CrossPlatform_R158_SessionGate_Statusline_Evidence.md`（DEF-200-333～344）。本檔為 DEF-200-340 結案、
> DEF-200-401 新立、DEF-200-342 釐清的詳情面。

## 一、掌舵者五問（逐字）與結論

1. 「我用終端 claude 都會出現以下問題，才開新視窗，就說他被擋不能寫檔案用工具了，然後也不去查真實的數據」
2. 「模型都不用真實的 /context 或 API 去查真實數據」
3. 「印出的 context 數字與 /context 明顯不符，直接告訴我，那就是新缺陷。==> 好像沒有，請確認！」
4. 「`ctx 18.0% 175.2k/1.0m | Fable 5.1` ==> 為何 Windows 11 都沒有這個資訊」
5. 「是否修復已經收斂，不用再進行？」

| 問 | 判定 | 一句話 |
|---|---|---|
| Q1 | **CONFIRMED（歷史）＋ 本輪修一條 Windows 端最合理因果鏈** | mac 上 2026-09-09～10 真發生過（QA T3：5 份逐字稿，根因＝舊語意 hook 寫入專案級 `TOKEN_BUDGET_CRITICAL`／`ESCALATION`，09-10 人工解除，DEF-200-275 R4 已修），之後 mac 零重現。Windows 端最合理鏈：FSM-STATE 殘留阻斷態 → 新視窗全工具 deny → SessionStart 印恢復指令 → 模型走 PowerShell 工具跑它（Windows 禁 Bash；FSM 不擋 PowerShell）→ **恢復指令自己被 `lint_powershell_command.py` 擋下**（`Set-Location "<root>"; & …` 命中 naked-cd）→ 模型自述「被擋」。本輪修 `recovery_hint.py`（DEF-200-340）。 |
| Q2 | **部分成立 → 修措辭級缺口（DEF-200-401）** | SessionStart 簡報（R158 P6）已印真實 context／額度／FSM；本輪補：feed reason 不再靜默丟棄、簡報直說 statusLine 有沒有裝＋安裝指令、stale-cache 時講清楚 `cap=2` 是退化政策值且 PreToolUse 會自動補量。**不加 SessionStart 網路補量**（見〈四〉）。 |
| Q3 | **NOT-A-DEFECT** | 主控＋SA 各三次 `--check`：`harness used＝逐字稿 used 差=0`；status line % 與 `/context` 計算時機不同係官方文件明文。 |
| Q4 | **NOT-A-DEFECT（部署缺口）** | Windows 從未安裝 statusLine；安裝器 `tools/install_statusline.py`（R158 P5）已在。本輪起新視窗簡報會直接告訴模型「statusLine：未安裝（安裝：…）」。閃窗風險仍待 Windows 親驗。 |
| Q5 | **未完全收斂** | 本輪結案 340、新立並結案 401；341／342 結構上待 Windows；S1(d) 測試零鑑別力補一支純函式格（不立帳）。 |

## 二、主控親測事實（本場 tool_result 逐字）

- HEAD=`cdae9028`，工作樹 clean；`SDD_ACTIVE_VERSION=0.30`＝LATEST；mac FSM-STATE `current_state=SPEC_DRAFTING`。
- 本 session SessionStart hook 原文含：`額度：額度量不到（reason=stale-cache（資料在，但已 30280s > TTL 180s ⇒ 重量一次即可，不是取數壞掉））⇒ cap=2 recommended=2 band=unmeasured`。
- `python tools/session_resume_planner.py --check`：`used 83,609`／`window 1,000,000〔harness 回報…釘值 967,000 未採用〕`／`水位 8.4%`／`harness used=83,609 逐字稿 used=83,609 差=0`／rc=0。
- `python tools/session_resume_planner.py --pace`：`現在可派 4 個 agent（硬上限 cap=不設限）｜band=free`／`來源=cache 量測於=2026-09-27T09:25:03+08:00`（`--pace` 自己補量了一次；SessionStart 當下沒補量）。
- mac 最近 10 份逐字稿「前 40 則含文字的 assistant 訊息」掃「被擋／不能寫／blocked／無法寫／擋下」：2 命中，皆為「子 agent 改 `.claude/settings.json` 被 Self-Modification 分類器擋」——**不是** Q1 形態。（QA 以「前 40 則 assistant 訊息」口徑複算，同兩筆命中落在第 116／253／280 則；兩種口徑對 Q1 的結論一致：mac 09-10 後零重現。）
- `.claude/settings.json` PreToolUse matcher：`sdd_hook_router`（context_ledger_pre）＝`Write|Edit|Read|Bash|NotebookEdit|Task|Agent|Workflow`（**不含 PowerShell**）；`lint_powershell_command.py`＝`PowerShell`。
- `context_ledger_pre.py`（v0.30）L470-491 D19 釋放分支在 L521 `assert_tool_allowed()` **之前**執行；`_owner_sid is None` 即可釋放（前提 `auto_compact_exit_due(m.used, window)`）；L496-517 D11：量不到 usage 放行一次。

## 三、四方分析與八位反駁者（摘要；全文住 session scratchpad `ctx5/*_analysis.md`、`ctx5/refute_*.md`）

| 方 | 核心發現 | 鏡 A（重現） | 鏡 B（範圍治理） |
|---|---|---|---|
| Architect | A1 七條「新視窗會被擋／自述被擋」來源普查；A2 Windows 根因優先序（#1 owner-缺席 PENDING、#2 `_BLOCKING_STATES` 殘留、#3 Self-Modification、#4 版本落差）；A3 `quota_line()` 用 `read_quota()` 未如 `pace_state()` 補量；A4 不得自動代寫使用者層 settings | 10 CONFIRMED／1 PARTIAL（A3 負向宣稱非窮盡） | A3 修法會打穿 `test_session_brief.py:53` 零網路回歸鎖（CONFIRMED）；A2 未引 D19 反向裁決（PARTIAL）；A4 兩個插入點 LOC 餘裕僅 1（CONFIRMED） |
| SA | S1 P1～P6 皆在 HEAD 落地全綠；S1(d) `test_decision_trace_omits_staleness_note_while_still_blocked` 對 guard clause 零鑑別力（`record_escalation()` 不寫 `decision_trace`，`_build_context` 的 `if trace:` 早退）；S3 三次 diff=0；S4 簡報靜默丟棄 feed reason、從不出現 statusLine 字樣 | 10/10 CONFIRMED（F1 找到更強證據） | S1(d) 定性過度延伸（PARTIAL）、補救應為一行純函式斷言不立帳（CONFIRMED）；342 判 UNVERIFIABLE 過度保守，mac 合成可重現（CONFIRMED） |
| SD | D1 補量 1 行 diff（實測 0.42s）；D2 六案餵 `lint_command()`：絕對／引號絕對／相對／不帶參數皆 BLOCKED，Push/Pop ALLOW ⇒ 裁決改文件不改判準；D3 `build_command()` Windows 組字正確、官方文件 Git Bash 優先；D5 候選 A（owner 缺席併入非 owner 放行） | 7 CONFIRMED／1 PARTIAL（D4 原型 cwd 脆弱） | D5 搶跑在 342 解鎖條件之前且對稱性方向顛倒（CONFIRMED）；D1 漏查 SessionStart hook `timeout=10`＋「每次開 session 都卡是不可接受的代價」（CONFIRMED）；D2 只改文件漏修 `recovery_hint.py` 自產指令被擋（CONFIRMED，比 SD 原判更嚴重） |
| QA | T1 四變體：(a)(b) 全擋、(c) 無 owner 只擋一般檔 Write/Edit、(d) owner 為他 session 且陳舊**完全不擋**；T2 halt 帶重現含「收斂不受影響」句；T3 全庫 80 份掃描：5 份 09-09～10 真 Q1；T4 三支測試鑑別力；T5 四支測試規格 | 8 CONFIRMED／1 PARTIAL（一句引句查無實據） | 自癒 REFUTED（Rule 9／D19）；SessionStart 補量 REFUTED（零網路約定）；naked-cd 放寬 REFUTED（改產生端 `recovery_hint.py:153` 更小）；新診斷腳本 PARTIAL |

## 四、主控裁決（做／不做＋理由）

**做**
1. `recovery_hint.py` PowerShell 模板 `Set-Location "<root>"; & <tail>` → `Push-Location "<root>"; & <tail>; Pop-Location`（同句成對，鐵律二放行形態；`Pop-Location` 不改 `$LASTEXITCODE`）＋跨專案鎖 `tools/tests/test_recovery_hint_passes_ps_lint.py`（正向零命中／負向舊模板命中非空）。
2. `session_brief.py` G1（statusLine 三態出聲、feed reason 接進 context 行）＋ G2（stale-cache 追加「退化值非量測值、PreToolUse 自動補量」文案）；零網路。
3. 根 CLAUDE.md L62／L174 鐵律二字面改「不論路徑形態一律擋；Push/Pop 不在此列」。
4. S1(d)：`test_session_start_rules.py` 加一支純函式格（`current_state="ESCALATION"`＋非空 trace ⇒ `None`；砍 guard clause ⇒ 非 None）。

**不做**
- SessionStart 網路補量：`test_session_brief.py:53` 零網路回歸鎖＋`context_budget_guard.py` SessionStart 條目 `timeout=10` 的登記註解「每次開 session 都卡是不可接受的代價」＝兩條明文裁決；PreToolUse 已會在第一次扇出型工具前補量（`quota_gate.py:1064`）。
- DEF-200-342 自癒／候選 A：D19 明文 fail-closed（`fsm_runtime.py:633-636`）、帳本自訂解鎖條件＝Windows 實值、三位反駁者 REFUTED；且 QA 探針證明新視窗形態本就不會被它擋（〈六〉）。
- naked-cd 判準放寬：R78/R79 兩輪加嚴皆為「放寬一格即繞過口」的實測教訓；修產生端更小。
- 新診斷腳本 `tools/probe/session_gate_diagnose.py`：既有 `--check`／`--pace`＋R158 §七清單＋本輪簡報已覆蓋（Rule 2）。
- 自動代寫使用者層 `~/.claude/settings.json`：越界。

## 五、修法與紅→綠證據（`[他包回報]`＝子 agent 本場真跑、主控以〈十一〉全套覆核）

### P1 dev-sdd（`recovery_hint.py`／`test_recovery_hint.py`／`test_session_start_rules.py`／新檔 `tools/tests/test_recovery_hint_passes_ps_lint.py`）
- 先紅：暫還原生產碼為舊字面 ⇒ 新／改動測試 3+1 失敗；套用修法 ⇒ 全綠 `[他包回報]`。
- `test_recovery_hint.py`＋`test_session_start_rules.py`：`46 passed` rc=0；新檔 `2 passed` rc=0；`test_check_hooks_liveness.py -k "naked or cd or lint"`：`15 passed`（判準零改動）；ruff 四檔 rc=0 `[他包回報]`。
- 既有 `test_command_neutralises_shell_metacharacters_in_reason` 剝掉已知 `; Pop-Location` 後綴再比對（意圖只驗 reason 中和）。
- S1(d) 鑑別力：真實碼回 `None`；砍 guard clause 複本回非 None `[他包回報]`；鏡 A 獨立重現一致。
- 主控收尾改寫新檔載入手法：Developer 原版 `sys.path.insert(0, str(_SDD_ROOT))`＋`from tools.fsm_runtime import recovery_hint` 讓 SDD ci-gate 的 `scripts/tests/test_ci_paths_cover_root_consumers.py` 兩支紅（靜態解析面對 `sdd_latest.resolve_latest_root()` 解不出目標、import 解析不出檔案）⇒ 改為子行程在 LATEST 根匯入真套件印回產物（比照 `test_component_sanitizer_shared_layer_lock.py` 既有手法），新檔 86→101 行；改寫後 SDD 側鎖 `49 passed`、新檔 `2 passed`（主控親跑）。

### P2 dev-root（`session_brief.py`／`test_session_brief.py`）
- 先紅：暫還原生產碼至 HEAD ⇒ `12 failed`（新測試）／`12 passed`（舊）；換回 ⇒ `24 passed` `[他包回報]`。
- `test_session_brief.py`＋`test_context_budget_guard.py`：`680 passed, 11 skipped, 232 subtests passed` rc=0 `[他包回報]`。
- 真跑 SessionStart（`echo payload | python .claude/hooks/context_budget_guard.py`）：additionalContext 含「…statusLine：已安裝。查證指令…」；鏡 A 以空 fakehome 重跑印「未安裝＋安裝指令」`[他包回報]`；`launchctl list | grep -i ctx5-devroot` 零殘留。
- `sessionstart_brief()` 新增 keyword-only `check_statusline`（帶預設值）⇒ `context_budget_guard.py` 呼叫零改動（該檔 LOC 餘裕 1 行）。

### P3 主控親手：CLAUDE.md L62／L174（無測試釘住「帶相對路徑」四字，鏡 B grep 證實）。

## 六、QA 探針（釘住 DEF-200-342 與 Windows 因果鏈）`[他包回報]`，鏡 A 獨立重跑一致

| 變體 (c)：`AUTO_COMPACT_PENDING`、`auto_compact_state={}` | 餵 PreToolUse Write 一般檔 | 結果 |
|---|---|---|
| used=20,000／window=1,000,000（新視窗形態） | D19 釋放 | `[SDD-CTX][AUTO-COMPACT][DONE] … resume→SPEC_DRAFTING`（放行） |
| used=None（量不到） | D11 | `[UNMETERED] … 依 C3 放行一次`（放行） |
| used=900,000／window=1,000,000（對照） | gating | `permissionDecision:"deny"` |

⇒ 342 只在「usage 量得到且仍高」時擋，**不是**「才開新視窗」的形態。

- 變體 (a) ESCALATION → `recovery_command(shell="powershell")` 產物餵 `lint_command()`：**1 命中**（naked-cd）；新形態 `Push-Location "<root>"; & <tail>; Pop-Location`：**0 命中**。
- 鏡 A 本機 pwsh 實測：`Push-Location /tmp; & /usr/bin/false; Pop-Location; exit $LASTEXITCODE` ⇒ rc=1（`Pop-Location` 不覆蓋 `$LASTEXITCODE`）。

## 七、Windows 端待辦（掌舵者親跑；本輪起新視窗簡報會自己講 statusLine 狀態）

```powershell
# <repo> 換成 Windows 上的 checkout 絕對路徑；一律絕對路徑、零裸 cd
& "<repo>\.venv\Scripts\python.exe" "<repo>\tools\install_statusline.py" --dry-run     # 1) 預覽
& "<repo>\.venv\Scripts\python.exe" "<repo>\tools\install_statusline.py"               # 2) 安裝（先備份 settings.json.bak-<UTC>）
& "<repo>\.venv\Scripts\python.exe" "<repo>\tools\install_statusline.py" --status; "rc=$LASTEXITCODE"   # 3) rc=0 才算裝好
```
- 開新 claude 視窗：看有無 `ctx` 行、有無閃 console 視窗（閃窗即 `--uninstall` 復原並回報）。
- 若新視窗仍被擋：把 SessionStart 印的 `[SDD-FSM][BLOCK]` 段與恢復指令整段貼回；恢復指令現已是 `Push-Location …; & …; Pop-Location` 形態，PowerShell 工具可直接執行。R158 §七 7.1/7.2 清單仍有效（342／341 解鎖條件）。

## 八、帳本異動
- DEF-200-340 → fixed（643 bytes）；DEF-200-342 狀態欄補 D19 釐清、維持 open（621 bytes）；新立 DEF-200-401 → fixed（700 bytes）。皆 ≤700。

## 九、誠實劃界
- Windows 真機零觸及：因果鏈的「模型跑恢復指令被 lint 擋」在 mac 以 `lint_command()` 直接餵字串證得；Windows 上 FSM-STATE 實值、statusLine 閃窗、CI #250 競態（341）仍待掌舵者親驗。
- S1(d) 純函式格證明 guard clause 有鑑別力，但 `_build_context()` 的 `if trace:` 早退仍讓「全新專案、trace 空」路徑不呼叫該函式（鏡 B 對 SA：真實專案 trace 不會空，屬人造情境）——未改生產碼。
- 主控 FACTS 的逐字稿掃描口徑為「前 40 則**含文字**的 assistant 訊息」，與 QA「前 40 則 assistant 訊息」不同；兩者結論相同，此處如實登記口徑差。
- 子 agent 數字皆標 `[他包回報]`；主控只採信〈十一〉自己跑的全套與 rc。

## 十、複審登記（登記不修）
- 鏡 A P3｜`recovery_hint.py`｜`Push-Location` 對不存在路徑是非終止錯誤，續跑 `-m` 在錯誤 cwd 可能 ImportError——修法前 `Set-Location` 同型，非本輪回歸。
- QA T1 副作用｜`context_budget_guard.py::arm_quota_wakeup`｜對任意（含合成、不存在的）session_id 皆無條件武裝一支真 launchd 排程，無「是否真實 session」防呆；QA 已 bootout 清空。
- QA T1 變體 (d)｜owner 為他 session 且陳舊時 `assert_tool_allowed` 完全不擋（D19 判準只看 `session_id != owner_sid`）——與 342 描述一致（只寫 owner 缺席），此否證路徑此前未登記。
- 鏡 B P2（已修）｜新測試檔 docstring 曾寫 `R84` 未帶 `round-label-ok`，主控收尾改寫為不含輪號措辭。

## 十一、收尾親驗（主控本場真跑，rc 逐字）
- SDD ci-gate（`bash scripts/ci-gate.sh`，第二次；第一次因 Developer 原版新檔的 `sys.path.insert(LATEST)` 讓 `test_ci_paths_cover_root_consumers.py` `2 failed`，改寫後重跑）：`AISDLC_SDD_v0.30: 1961 passed（not chaos）`／`共享 infra scripts/tests/: 362 passed`／`SDD_CI_GATE_RC=0`。
- ruff：本輪改到的 8 支 .py（recovery_hint／兩支 v0.30 測試／session_brief／test_session_brief／governance_docs／鎖檔／新檔）`All checks passed!` `RUFF_RC=0`。
- 鎖檔 `tools/tests/test_adr_xplat001_c1c2_lock.py`：`192 passed, 406 subtests passed`（重釘後）；針對性五檔（鎖檔＋platform_neutral＋doc_loc＋session_brief＋新檔）首跑 `2 failed, 674 passed`——紅的兩支＝Phase2 五輪視窗到期（依 §6 追加 `[提案]` 列）與新檔 Windows 磁碟機字面（三處加 `# platform-ok:` 豁免），修後各自 `1 passed`。
- ONBOARDING §7 表② mac 欄乾淨 venv 回填（`tools/lib/clean_venv_carrier.py`，探針 psycopg2／sqlalchemy 皆 ABSENT，finally 已刪、殘留 0）：`autoclaude 4638 passed／222 skipped`、`v001 1475`、`v030 1961`、`scripts 362`；指紋 `v030 c410f3a1862c→bd1b59bf56e6`（其餘三棵不變）；`BACKFILL_RC=0`；`--check-snapshot` `CHECK_SNAPSHOT_RC=0`。
- crossref（最後一次改帳本與證據檔之後）：`帳本 330 筆有效狀態紀錄、19 份掃描目標皆無矛盾`／`未結存量 37 列`／`CROSSREF_RC=0`。
- SessionStart 簡報真跑（假 sid `ctx5-helm-probe`＋本 session 真逐字稿直接餵 `context_budget_guard.py`）：`HOOK_RC=0`、stderr 0 bytes、額度已補量後 `recommended=8 band=free`、`statusLine：已安裝`、launchd 零殘留。
- 正面現查 `claude -p --model haiku --debug hooks`：`claude -p rc=0`、`Hook SessionStart.*success`＝2、`non_blocking_error`＝0、`.venv` ENOENT＝0（h.log 僅有 Claude Code 自身 stat `~/.claude/agents` 等目錄的 5 筆 ENOENT，與載具無關）、`readlink .venv/Scripts/pythonw.exe`＝`../bin/python`。
- 根層全套 `python tools/run_root_unittests.py`（第三跑；第一跑在靜態標籤掃描早退、第二跑 4 failures 皆棘輪，見〈十二〉）：`✅ unittest 數量下限釘選通過：發現 4662 個測試（下限 4543）`／`[cpu_budget] root-unittest workers=9 source=cpu_budget`／`派工摘要：worker=9｜S=766.9s｜…｜slot 利用率=99.7%`／`[M6 id 集合] tools/tests@darwin：✅ 集合關係成立（本次 skip 47 支）`／`REAL_RC=0`。

## 十二、棘輪重釘（R177，到期輪）
- `_GUARD_LINES_REPIN_LOG`：主列 `("R177", 107216, 107418, 202)`（新檔 `test_recovery_hint_passes_ps_lint.py` 101＋`test_session_brief.py` +101）＋自身漂移列 `("R177", 107418, 107452, 34)`；`_FROZEN_GUARD_LINES` 以 `--print-guard-lines` 逐檔照貼三次收斂（最終 `淨額 107452→107452 (+0)`）。
- `_REGRESSION_LANE_LOG`：`("R177", 236, …)` 全額申報回歸鎖軌（236 ≤ 軌上限 309），主軌 0。
- `_REPIN_NET_CAP_SCHEDULE`：到期義務兌現列 `(177, 528)`；重新武裝 `_REPIN_NET_CAP_DUE_ROUND=179`／`_REPIN_NET_CAP_DUE_TARGET=527`（步伐 1）。`_PHASE2_REVIEW_LOG` 依 §6 追加 `(177, "[提案]", …)`（上一列 R171 為維持觀察、名額已用罄，體例同 R165）。
- `_REPIN_LOG_FROZEN_PREFIX_LEN` 297→299；`_REPIN_LOG_HISTORY_SHA256` → `8f0be6de014b…`；`_FROZEN_PREFIX_REWRITE_LEDGER` 追加 `("R177", "439d33eed981", "8f0be6de014b", "DEF-200-340")`。
- doc-total 對帳兩站點：`CrossPlatform_R145_Scan_Findings.md`〈附記（R177）〉＋`AutoSDD_improving_112.md` `guard-total:R177`。
- `tools/lib/governance_docs.py` 登記本檔。
- 根層全套第二跑 `4 failures`（皆棘輪，逐項照判準指示處置）：① `test_e501_debt_only_shrinks` 139→141——新檔兩條帶 `# platform-ok:` 的行 119 欄，折行；② `TestScanRootsConfigPinning`／`test_repo_trees_have_no_unencoded_text_subprocess`——`tools` 掃描檔數 196 > 腐化上界 195，`(_REPO_ROOT / "tools", 156)` 依判準重釘 186；③ `test_zero_guard_bare_python_sites_match_registry_exactly`——`_STATUSLINE_INSTALL_HINT` 字面以 `python ` 開頭命中裸 python 判準，改為反引號包住（同檔既有 `_VERIFY_HINT` 體例），不動登記表。修後三檔針對性 `3 passed`／`1 passed`／`24 passed`。
- `tools/lib/skip_tag_policy.py::_TREE_FILE_FLOORS["tools/tests"]` 67→68：根層全套首跑在「靜態標籤掃描」階段早退（`一支測試都沒有執行（rc=1）`；實測 85 支、67 只剩 79% < 80%），掃描器逐字指示重釘為 68 ⇒ 照填，重跑全套。
