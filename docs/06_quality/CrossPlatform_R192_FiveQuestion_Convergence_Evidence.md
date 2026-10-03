# CrossPlatform R192 — 掌舵者五問系列第十四次四方覆核（判準②′ 生效第 1 輪；根因修 QA-01 zsh 漏攔＋②′ 機械化＋丙案）證據檔〔R193 鏡 B 事後零信任稽核：REJECT（1 P1／6 P2／11 P3）→ 訂正清單已套用於本檔與帳本，清單全文見 CrossPlatform_R193 證據檔〕

> 日期 2026-10-03；平台 macOS（Darwin 25.6.0 arm64）；Claude Code 2.1.288（R191 記 2.1.287）；主控 Fable 5.1，四方（Architect／SA／SD／QA）、Developer-A／B／C 三棒皆 Sonnet（掌舵者指令：子 agent 一律 Sonnet；本輪未派複審鏡，見〈五〉——R193 鏡 B 訂正）。
> 起點 HEAD `d337e3f6`（R191 docs 回填）＝origin/main，工作樹乾淨。掌舵者原話：三問逐字＋「沒有收斂繼續收斂，請查根因，別盲目實作！」＋「派出Architect / SA / SD / QA 四方專家獨立審查,請確認以上都已經修好！」＋對 R191〈八〉裁決「依照建議 Ａ」（採判準②′＋縮庫存；γ 未否決＝維持追認）。
> 本檔屬帳本級治理文件（登記於 `tools/lib/governance_docs.py`）。

## 〇、一句話結論
三問第十四次驗（Mac；判準②′ 生效第 1 輪）：Mac 側 Q1／Q2 修法後**看不到症狀**——修法後唯一真實 session（本窗）前 5 呼叫零阻斷、第 2 個呼叫即現查；SA 凍結探針 9/9 零阻斷、零「被擋」宣稱、PA 3/3 在 #1 現查且形態安全 `[他包回報]`；但真實母體 n=1、探針模型 Sonnet≠使用者預設 Fable、Windows 連續第 6 輪零觸及 ⇒ 只能說「本機看不到」。四方家族級審計挖到 **1 個新 P2＝DEF-200-467**（判準④對大寫 `PIPESTATUS` 一律豁免，但 Bash 工具殼是 zsh ⇒ 15～16 處真實站點印空 rc＝假綠 `[他包回報]`；DEF-200-086 同根變體）同輪根因修；另 P3×5（468 量測器子字串判定與只認 Bash、469「不受影響」8 出口、470 Stop hook 跨軸誤綁定、471 逐字稿目錄輸入兩套、472 假紅普查母體只含頂層 15%），468～470 同輪修、471／472 open。Architect 通道普查：與掌舵者原話最吻合的形態是 **harness auto-mode 分類器暫時不可用**（唯讀可用、Bash／寫檔被拒，而查真實數據的載具正是 Bash ⇒ Q1＋Q2 同時出現；本機 1 筆、非我方）⇒ 本輪給簡報加**唯讀退路**（Read 工具讀 feed JSON 與額度快取的絕對路徑），讓「查真實數據」不再依賴 Bash。②′ 已**部分**機械化（協定凍結 11 檔、sha `e0ec9c35…`、輪帳本首列、`audit_session.py --five-question` 五量／`--protocol-status` 窗口計數；完整性閘與 Q4′ 當時仍人供，`--protocol-status` 的評估只含窗口長度與 P 計數、不含 Q1′～Q4′——R193 鏡 B 訂正，原寫「已機械化」）；丙案 `tools/session_gate_acceptance.py` 落地＝Windows 一條指令即可供 Q4′ 證據。**依②′：NOT-EVALUABLE(1/6)、本輪 new_p_le2=1**，不能宣告收斂（評估見〈八〉）。

## 一、三問第十四次判定（Mac）

| 問 | 判定 | 一句話（主控親測或他包實跑） | 本輪動作 |
|---|---|---|---|
| Q1 新視窗就說被擋不能寫檔案用工具 | **Mac 側看不到；Windows 未驗** | 主控本窗 #1 `git status …\| head -20`（管線後接的不是讀 `$?`）放行、#2 `--check`＋`--pace` 放行、全程 0 阻斷；QA 真實母體（修法後）1/1 前 5 呼叫零阻斷 `[他包回報]`；SA 凍結探針 9/9 零阻斷零宣稱、PD 3/3 正確攔截＋#2 自癒＋如實回報 `[他包回報]`；Architect 通道普查 15 列：我方 Mac 側只剩判準④正確攔截＋措辭 priming，`hook:Write／Edit`＝0，最吻合原話的是 harness 分類器不可用 `[他包回報]` | 467（zsh 漏攔）根因修；469 單一導出＋Δ1～Δ5 措辭；T3 唯讀退路；丙案腳本 |
| Q2 不用真實 /context 或 API 查數據 | **未見症狀（Mac；修法後 n=1，Q2′ NOT-EVALUABLE(1/5)；修法前基線 Q2′ FAIL 2／15；Windows 未驗）——R193 鏡 B 訂正，原寫「PASS（Mac）」牴觸〈〇〉〈五〉〈六〉** | 主控本窗第 2 個工具呼叫＝`--check`＋`--pace`（rc=0、`差=0`）；SA PA 3/3 在 tool_use #1 現查且指令形態 3/3 安全 `[他包回報]`；Dev-B `--five-question --since 2026-09-20`：Q2′ FAIL 2／15 皆修法前（序號 31／12）、修法後 c00d202a＝#2（主控親驗，見〈六〉） | T3：Bash 被拒時仍可用 Read 讀 `~/.autosdd/context_feed/<sid>.json` 與 `~/autosdd_quota.json`（簡報印絕對路徑，主控親驗） |
| Q3 是否已收斂 | **否：②′ NOT-EVALUABLE(1/6)、本輪 new_p_le2=1** | `--protocol-status`：`window_len=1`、`NOT-EVALUABLE(1/6)`（主控親驗，見〈六〉）；Q4′ Windows 缺席＝FAIL | 詳〈八〉 |

## 二、主控親測事實（本場 tool_result 逐字）
- 開場現查（第 2 個工具呼叫；第 1 個是 `git status`／`git log`／`ls`）：`--check` rc=0 `used 78,597`、`window 1,000,000〔harness 回報…〕`、`水位 7.9% → 低於 84%`、`harness used=78,597 逐字稿 used=78,597 差=0`；`--pace` rc=0 `現在可派 1 個 agent（硬上限 cap=2，本視窗已用 0 次）｜band=prepare｜最緊的一條＝seven_day 88% 剩 1015 分鐘`、`來源=cache 量測於=2026-10-03T09:04:50+08:00`、`⚠️ 落款樣本有斷層：最近 5 列間最大間隔 514.3 分鐘`。三位 agent 收工後第二次 `--pace`：`現在可派 1 個 agent（硬上限 cap=1，本視窗已用 0 次）｜band=prepare｜最緊的一條＝seven_day 91% 剩 970 分鐘`、`本窗餘裕 -6.5pp`、`來源=cache 量測於=2026-10-03T09:48:00+08:00`（三位 Sonnet 合計約 99 萬 token ⇒ weekly_all 88%→91%）。
- 同機 peer：`ListAgents` 列 `aisdcl-agent-fe [5f4df7] idle`；`ps` PID 48075（父 47816）＝`.antigravity-ide/extensions/anthropic.claude-code-2.1.288-darwin-arm64/…/claude --output-format stream-json`（IDE 擴充套件自啟，忽略）；本窗 PID 48515。
- `claude --version` ⇒ `2.1.288 (Claude Code)`。`git log -1 --format='%ci %h' 7931ced2` ⇒ `2026-10-03 01:21:56 +0800 7931ced2`。
- 主控任務書的母體宣稱**錯誤**（QA EV-01 訂正）：主控以 mtime 與首則 user 列判 `cd33883f` 為修法後 Sonnet 純問答，QA 查該 session 唯一 user prompt 是 2026-09-08、mtime 被無時戳 cost-state 列改寫 ⇒ 修法後真實母體只有 `c00d202a`（本窗，N=1）＋`6880f760` 切點後尾巴 9 個呼叫。
- `--unresolved-count`：`未結列數＝37`（起點）。棘輪常數 `_REPIN_NET_CAP_DUE_ROUND = 192`／`_REPIN_NET_CAP_DUE_TARGET = 521`（`test_adr_xplat001_c1c2_lock.py:3135-3136`）、`_ROOT_TOOLS_OLD_SCALE_DEBT_DUE_ROUND = 193`（:3050）。
- `claude_home` 出口：`tools/lib/platform_utils.py:53`（SSOT）＋`.claude/hooks/context_budget_guard.py:78`（fallback，標 `claude-home-fallback-ok`）；逐字稿目錄沒有跨模組共用的函式，僅 `tools/probe/audit_session.py:266` 有一份 `project_transcript_dir`（`tools/session_gate_acceptance.py:100` 借用；R193 鏡 B 訂正，原寫「函式不存在」）。`quota_messages.py:310／:319／:443` 仍有「不受影響」句。`~/autosdd_quota.json` schema `autosdd.quota/2`、`source=endpoint`、`http_status=200`。
- 本窗被守衛擋下：0 次（截至派工時）。

## 三、四方摘要 `[他包回報]`
- **Architect（APPROVE；新 P≤2＝0；P3×4＋資訊×1；約 34 萬 token／50 次呼叫）**：A1 通道普查 15 列——我方 Mac 側只剩判準④正確攔截＋簡報／DECISION-TRACE 措辭 priming；全母體「擋」類 71 筆＝sdd-deny 21／hook:Workflow 16／hook:Bash 13／auto-classifier-deny 13／hook:Agent 4／no-such-tool 3／classifier-unavailable 1，**hook:Write／Edit＝0**；與掌舵者原話最吻合的形態＝harness 分類器不可用（`claude-sonnet-5[1m] is temporarily unavailable … auto mode cannot determine the safety of Bash right now … read-only operations … can still be used`，本機 1 筆 2026-09-11）：唯讀可用、Bash／寫檔被拒，而查真實數據的載具正是 Bash ⇒ Q1＋Q2 同時出現 [推論]。ARCH-01（量測器 `blocked` 子字串判定被證據檔引文汙染：全母體 5,533 筆 Bash tool_result 中 audit 式 15／嚴格式 13／假陽 2 皆在修後窗；只認 Bash，58/71 事件不可見）；ARCH-02（「不受影響」≥6 出口 4 檔、461 殘餘無人擁有）；ARCH-03（`plan_evidence` 缺 state 回字串 "None"，保守側）；ARCH-04（slug 規則單份且 100/100 與 harness 落點相符、無鎖；啟動目錄變體 7 支對 `_REPO_ROOT` 讀者失明）；ARCH-05（`~/.zshrc:9 export SDD_ACTIVE_VERSION=0.30` 非 repo ⇒ 通道集合隨機器而異）。單模組：test_session_brief `Ran 66 tests OK`、cbg 子集 `Ran 16 tests OK`。
- **QA（CONDITIONAL；新 P≤2＝1＝QA-01；約 29 萬 token／43 次呼叫）**：回歸 460 `Ran 124 tests … OK REAL_RC=0`（點路徑與 cd 兩形態皆生效）、e2e r145 `Ran 8 tests OK`、session_brief `Ran 66 tests OK`、cbg `Ran 789 tests in 53.538s OK (skipped=11)` 全 `[WINDOWS-NATIVE-ONLY]`；對照組 `test_the_same_harness_does_unload_a_true_orphan` 通過。母體校正 EV-01（見〈二〉）。c00d202a：29 tool_use、前 5 全放行、硬阻斷 0、首次 planner #2、宣稱被擋 0 句；基線 9ea68d33 #1 被擋／6880f760 #2 被擋皆判準④。Q1′：誤擋 0（3 次真阻斷於 HEAD 重放皆壞形態）、宣稱≠阻斷 0、前 5 呼叫被擋比例修後 0/1、基線 2/2、全史 11/54（ESCALATION-router 6／context 守衛擋 Workflow 3／判準④ 2）；Q2′ c00d202a #2、歷史 17/21 在 10 內；Q3′ `harness used=190,059 逐字稿 used=190,059 差=0`、6 session 差皆 0；Q4′ Mac `--status` rc=0 installed/matches true。**QA-01（P2 候選）**：`_RCMASK_SAFE_RE`（`block_destructive_git.py:1065`）對大寫 `PIPESTATUS` 一律放行，但 Bash 工具殼是 zsh（`ZSH_VERSION=[5.9]`、`PIPESTATUS0=[] pipestatus1=[7]`）⇒ 真實逐字稿 19～20 站點中 15～16 處印空 rc、一處 `${PIPESTATUS[0]:-$?}` 印被遮蔽的 0＝假綠；DEF-200-086 同根變體。QA-02＝ARCH-01；QA-03（`--exclude-self` 在 subagent 讀到父窗 sid、只掃頂層、0 工具 session 觸發 rc=1）。INFO：subagent `Write` 被 harness 擋 9 次、`No such tool available` 5 次。
- **SD（APPROVE；新 P≤2＝0；P3×5；約 36 萬 token／40 次呼叫）**：D1 ②′ 可判定化（母體＝`entrypoint∈{cli,claude-vscode}`、`sdk-cli` 全排除——探針全是 `-p`，首則 prompt 口徑只抓到 4/90；互動且≥1 tool_use＝53；阻斷證據＝`is_error`＋`toolDenialKind`，值域 permission-rule 54／user-rejected 14／automode-blocked 13／automode-unavailable 1；Q1′a oracle 重放 13/13 壞形態＝誤擋 0；Q1′b v3 正則 13/13/0 全在 09-07～10 鎖定期；Q1′c 建議 gate ≤25%（n≥20）／target ≤10%，n=20 約需 10 個活躍日；Q2′ 正則須 `(?![-\w])`、`/context` 是 `system/local_command` 非 tool_use 不計；Q3′ N=10、|差|≤100、實測 24/24 差=0；Q4′ Windows 須丙案 JSON）；審計錨 F-1（帳本無 family 欄，字面規則只解 22 列中 15、漏 455／456／460 ⇒ 登記制＋完整性閘）、F-2（任務書 R190↔R192 逐行重疊 0% ⇒ 須輪不變模板）、F-3（PA／PB／PC 文本不在 repo）、**manifest 落地那一輪才是第 1 輪**。D2 丙案建議本輪做最小形態（原型 Mac rc=0、13 鍵、765 bytes；hygiene 樹 198 下限 186 不撞；`tools/tests` 檔數 86 對下限 68 壓線 ⇒ 測試併入既有檔）。D3「不受影響」8 出口兩組各自維護、⑤⑥為字串手術；Δ1～Δ5 逐字措辭。D4 writer==reader 矩陣親試即紅（子目錄啟動時 planner／sentinel 錯、gate 對；`--check` rc=0 靜默讀他窗）、slug 對 harness 125/125 吻合、最小修法 `harness_feed.pick_transcript` 加跨 slug sid 搜尋（≈+5 LOC）＋48 格性質測試併入既有檔。F-A（逐字稿目錄輸入兩套 `_REPO_ROOT` vs `CLAUDE_PROJECT_DIR`；7 支 AutoClaude-slug session 0/7 呼叫根 planner）、F-B／F-C／F-D／F-E（措辭）。被判準④正確擋 1 次。
- **SA（APPROVE；新 P≤2＝0；P3×1＝F1；約 32 萬 token／30 次呼叫）**：凍結探針 9 支（PA／PB／PC 各 3；模型 claude-sonnet-5-5；`claude -p`；真 HOME、不隔離額度快取）：真阻斷（`PreToolUse:Bash hook error`）0、permission_denials 0、InputValidationError 0、hook_non_blocking_error 0、宣稱被擋 0（PA2 regex 命中「沒辦法判斷守衛指哪個數字」人工裁定非宣稱）、rc 全 0、`Hook SessionStart.*success`＝2×12；PA 3/3 在 tool_use #1 現查 `--check`（＋`--pace`）且指令形態 3/3 安全；PC 3/3 先真的 Write＋cat 再答「能」；簡報「要 rc 先導檔再讀」句 12/12 在場。探索 PD×3（餵壞形態 `… --check | head -20; echo "rc=$?"`）：3/3 在 #1 被判準④正確攔截（訊息開頭即一行解法）、#2 導檔形態自癒、最終回覆如實說「原指令被守衛擋下、我改了寫法」。**F1（P3，新）**：`check_claim_provenance.py:519` `_PACE_READING_RE` 把軸名綁到其後第一個百分比、跨過另一軸名（`seven_day…；session 是 13%` ⇒ `axis=seven_day value=13` ⇒ `unanchored` 誤報並強制多跑一回合；PA 3 支中 2 支重現；本機 346 逐字稿 28 筆綁定中 4 筆跨軸、命中 1 筆非跨軸 ⇒ 真實頻率低）；附 P4 docstring :555「不出聲」與 :1111 實際出聲不一致。F2 任務書訂正：cd33883f 非修法後樣本（同 QA）；**使用者預設模型是 `claude-fable-5-1[1m]`（`~/.claude/settings.json`），不是 Sonnet** ⇒ 探針母體≠使用者母體；12 支中 10 支簡報為真實讀數、PC3／PD3 是 stale-cache 形態。S2 獨立重算（嚴格判準）：修法前 n=8 前 5 呼叫被擋 2/8、全程 3/8、planner 首次現查序號 `[1,1,1,1,2,2,12,31]`（皆 Fable）；修法後 n=1 阻斷 0、現查 #2 ⇒ Q1′c 不可評估。S3 假 HOME 直餵 SessionStart：rc=0、頂層鍵 `['hookSpecificOutput','systemMessage']`、字面「ℹ️ 畫面最下方沒有 `ctx NN% …` 狀態列（statusLine 未安裝或與本 checkout 不符）。貼上即安裝：…」；真 HOME 12 支 `hook_system_message` 0/0（預期）；`--status` rc=0 installed／matches true＝Mac Q4′ 一筆。S4 額度快取 mtime 基線後 7 次刷新全 endpoint／200、無 429；探針視窗內變動 2 次（PC3／PD3 的 hook 補量）；從未呼叫 `--pace`；哨兵前後各 2 無差異；`claim_freshness.jsonl` 因 F1 +2 列（不可還原）；12 支 sid 列於其報告〈九〉未刪。效度威脅：Sonnet≠使用者預設 Fable、`-p`≠互動 TUI、引導式提示、n=3／型（0/9 的 95% 單尾上界 28.3%）、Windows 零觸及。

- **Developer-A（Sonnet；約 53 萬 token／132 次呼叫，超過上限 60）**：T1 `_tool_shell_is_zsh()`＋zsh 下大寫讀取偵測（`mask_inert(keep_status)`）、`_RCZSH_LEAD` 一行解法置前；紅 `Ran 44 tests … FAILED (failures=14, errors=13) REAL_RC=1` → 綠 `Ran 44 tests … OK REAL_RC=0`、整模組 `Ran 233 tests … OK`；真 hook 行程 zsh rc=2／bash rc=0／zsh 小寫 rc=0；假紅普查頂層 `命中 71 種唯一／73 次`→`72 種／74 次`（新增 1 真陽、消失 0），遞迴普查 `NEWLY hit under zsh (unique)=28`（27 真空 rc、1 一般④真陽）、`regress=0`，差分 34,635 種指令 `new(bash)!=old: 0`。T2 `convergent_tools_clause()`、字串手術拆除、Δ1～Δ5；在 quota_messages.py＋session_brief.py 兩檔（鎖 `ConvergentToolsClauseSingleHomeTest` 的射程）內 `grep "不受影響"` 只剩 `quota_messages.py:308`（R193 鏡 B 訂正：全 repo 排除 docs／tests 另有數百處其他語境的同字串，不在鎖射程）。T3 `verify_hint(windows=None, *, feed=None, quota=None)` 唯讀退路（路徑走 `statusline_context_feed.context_feed_path()` 與 `quota_gate.quota_cache_path()`，不第二次拼路徑）。兩模組 `Ran 285 … OK`→`Ran 314 … OK`；cbg 整檔 `Ran 789 tests … OK (skipped=11)`；鄰近 6 模組 `Ran 684 … OK (skipped=6)`；`test_platform_neutral_paths` 首跑 2 紅（殼路徑字面）改具名常數後 `Ran 177 … OK`；ruff 5 檔 `All checks passed!`；LOC hook 714→737（≤750）。發現 472（corpus glob 盲區）。
- **Developer-B（Sonnet；約 64 萬 token／140 次呼叫，超過上限 60）**：`audit_session.py` 阻斷判準改 `is_error`＋`toolDenialKind`＋前綴分類、全工具；`--five-question`／`--protocol-status`／`--entrypoint`／`--exclude-sid`；`--selftest` `新判準判錯 0 / 10；舊判準判錯 6 / 10`、`②′ 量測自證…判錯 0 組`；legacy 阻斷 `c00d202a blocked_true=0`／`6880f760 1`／`9ea68d33 2`（與 QA 嚴格式一致）；協定目錄 11 檔 `protocol_sha256=e0ec9c35…d93`、輪帳本首列、改一字→`PROTOCOL-CHANGED`→改回 cmp 相同；`check_loc_budget` 斷言行 533→713（≤750）、`root_tools_violations: []`；史料搬出淨 181 行；偏離：legacy `pending_bash` 未推廣（斷言行上限）、`[SDD-CTX]` 併入 sdd-router、探針 prompt `R{{ROUND}}-PROBE` 槽位、`severity.md` 補 P1 定義（主控接受）、起點以 session 首筆時戳判。
- **Developer-C（Sonnet；約 33 萬 token／56 次呼叫）**：C1 `tools/session_gate_acceptance.py` 201 行／計價 134（≤150）、15 鍵、零 subprocess、`reject_unknown_argv`（`--bogus` rc=2）；Mac 實跑 `platform='darwin'`、`cc_version='2.1.288'`、`statusline={'installed': True, 'matches_current_checkout': True, …}`、`hook_carrier={'exists': True, 'is_symlink': True}`、`check={'rc': 0, 'diff_line': 'harness used=307,459 逐字稿 used=307,459 差=0', …}`；測試 `SessionGateAcceptanceTest` 10 格零 skip 併入 `test_session_brief.py`（紅 `FAILED (errors=10)`→綠 `Ran 10 tests OK`；全模組 91 OK；薄層鎖 `count = 25` 掃到新檔）。C2 464 三處改 `patch.dict`＋`addCleanup(stop)`：修前 `PIN_SURVIVES=False`→修後 True、三 class `Ran 21 tests OK`、共用 helper 13 class `Ran 118 tests OK`；訂正任務書：傷害在模組內部（舊 `pop` 吃掉圍籬自己釘的值）、同型殘留 `test_mac_endurance_r83.py:1803` 未動。C3 綁定跨度改 `(?:(?!任一軸名)[^\n]){0,40}?`，新類別 4 格紅 `FAILED (failures=3)`→綠 OK、全模組 94 OK；本機 102 支逐字稿重放 90 筆讀數 2 筆差異皆跨軸句式；已知取捨：`session` 也是日常詞。

## 四、新發現、嚴重度裁決與修法

| 列 | 裁決（主控） | 來源 | 修法（本輪落地） |
|---|---|---|---|
| **DEF-200-467**（新立；＝QA-01） | **P2，計入**（傷害類別＝漏攔＋假綠：模型讀到空 rc 或退路印出的被遮蔽 0；與 086 同根、086 為 P1；QA 建議 P2 候選、主控採嚴口徑） | QA 工具殼實測 `PIPESTATUS0=[] pipestatus1=[7]`＋真實逐字稿 19～20 站點 15～16 處空 rc；Dev-A 先驗 `zsh -c 'false \| true; echo "upper=[${PIPESTATUS[0]}] lower=[${pipestatus[1]}]"'` → `upper=[] lower=[1]` | `_tool_shell_is_zsh(env, platform)`（SHELL basename 恰為 zsh；缺席且 darwin ⇒ True；其餘 False）；小寫／pipefail 一律豁免、大寫只在非 zsh 殼豁免、zsh 下讀大寫即命中（`_RCZSH_LEAD` 一行解法置前）；`mask_inert` 雙引號內保留大寫讀取；鎖 44 支中 27 支紅（14 failures＋13 errors；R193 鏡 B 訂正算術）→綠、整模組 233 OK；假紅普查頂層 71→72 種（新增 1 真陽、消失 0）、遞迴普查 28 新命中（27 真空 rc、1 一般④真陽）、差分回歸 0；主控親驗替身 hook：zsh rc=2／bash rc=0／zsh 小寫 rc=0 |
| **DEF-200-468**（新立；＝ARCH-01／QA-02／QA-03） | P3（量測器缺陷；被 ②′ 消費前修掉） | Architect 全母體重算 5,533 筆：audit 式 15／嚴格式 13／假陽 2；QA 重現 c00d202a #19、6880f760 #26 引述假陽 | 阻斷＝`is_error`＋`toolDenialKind`＋前綴分類（hook／sdd-router／非 hook）、全工具；母體改 `entrypoint∈{cli,claude-vscode}`；`--five-question`／`--protocol-status`／`--entrypoint`／`--exclude-sid`；`--selftest` 新舊判準 0/10 vs 6/10；legacy 阻斷計數 c00d202a 1→0、6880f760 2→1（與 QA 嚴格式一致） |
| **DEF-200-469**（新立；＝ARCH-02／SD F-B～F-E；461 殘餘） | P3（訊息不一致；R191 已點名的「點鎖漏兄弟」） | SD 8 出口表；Architect ≥6 出口 4 檔 | `quota_messages.convergent_tools_clause(windows)` 單一導出、⑤⑥字串手術拆除；Δ1（判準④首行加主語）、Δ2、Δ3、Δ4、Δ5（UNATTENDED 分支句）；grep 鎖「不受影響」只剩函式本體；主控親驗兩平台字面 |
| **DEF-200-470**（新立；＝SA F1） | P3（誤報多跑一回合，無錯誤決策） | SA 離線重現＋346 逐字稿重放 | 綁定跨度不得含另一軸名（Dev-C；見〈三〉） |
| **DEF-200-471**（新立；＝SD F-A／D4） | P3，open（潛伏：子目錄啟動 0/7 呼叫根 planner） | SD writer==reader 矩陣親試即紅、slug 125/125 吻合無鎖 | 承接 R193：`harness_feed.pick_transcript` 跨 slug sid 搜尋＋48 格性質測試併入既有檔 |
| **DEF-200-472**（新立；Dev-A 發現） | P3，open | Dev-A 遞迴普查：全樹 37,212 列 vs 探針 5,562 列 | 承接 R193：glob 改遞迴＋重跑基線 |
| DEF-200-464（結案） | fixed | 鏡 A R191 立列 | Dev-C 三處 `addCleanup` 改還原（見〈三〉；同型殘留 `test_mac_endurance_r83.py:1803` 未動，R193 補修） |

**不立列（主控裁決）**：ARCH-03（`plan_evidence` 缺 state 回字串 "None"，`reap_verdict` 對它不收＝保守側、無錯誤決策；Architect 自判 P3「方向保守」；記名）；ARCH-04（slug 規則單份且 100/100 相符，鎖的缺口併入 471）；ARCH-05／SA F2（資訊：通道集合隨機器而異；使用者預設模型是 Fable）；SD F-D／F-E（併入 469 的 Δ1／Δ3）；SA 附 P4（docstring 不一致，Dev-C 一行修）；Dev-A 指出 Δ3「這次寫入已完成」在 PreToolUse 時點不準 ⇒ 主控收尾改「這次寫入會照常執行」（見〈六〉）。

**harness 通道（非我方缺陷，不立列）**：auto-mode 分類器拒絕 13 筆（`[Self-Modification]`／`[Session Transcript Tampering]`）、分類器不可用 1 筆（2026-09-11）、子 agent `Write` 報告檔名被擋 9 次、`No such tool available` 5 次 `[他包回報]`。對策只有 T3 唯讀退路（讓查真實數據不依賴 Bash）與簡報措辭「不要宣稱被擋」。

## 五、誠實劃界與未驗

- **Windows 真機連續第 6 輪零觸及**：467／469／T3／丙案在 Windows 的呈現皆未驗；Q4′ 依字面 FAIL。丙案腳本本身只在 Mac 跑過（Dev-C）。
- **修法後真實母體 n=1**（主控本窗；QA／SA／Dev-B 三方獨立確認；主控任務書誤把 `cd33883f` 當修法後樣本——它的唯一 user prompt 是 2026-09-08，mtime 被無時戳列改寫）⇒ Q1′a／b 的 PASS 是空洞成立、Q1′c／Q2′／Q3′ `NOT-EVALUABLE`；n=20 約需 10 個活躍日（SD）。
- **探針效度**：模型 Sonnet≠使用者預設 `claude-fable-5-1[1m]`；`claude -p`≠互動 TUI；引導式提示；n=3／型（0/9 的 95% 單尾上界 28.3%）；PD 標籤洩題。
- **T3 唯讀退路的效果未量**：本輪沒有分類器不可用的活體（本機史上 1 筆）；只驗了簡報字面與絕對路徑在位。
- **協定 manifest 不含量測器本身**（Dev-B 指出）：`audit_session.py` 的「前 5」「<10」「往回看 3」是碼內常數，量測器定義變更不會重置窗口——主控裁決：本輪不納入（量測器會隨缺陷修正而動，納入會讓窗口永遠歸零）；判準常數由 `params.json` 承載。
- **oracle 與守衛同一份碼**（SD／Dev-B）：抓得到接線漂移、抓不到判準本體誤判；假紅普查正解仍是 `shell_command_corpus.py --corpus transcripts`，而它的母體只含頂層 15%（472）。
- **工具呼叫超標**：Dev-A 132 次（〈三〉交件自陳；本行原寫 123，R193 鏡 B 指出不一致、Mac 逐字稿本機不可驗，以 132 為準）、Dev-B 約 140 次（上限 60）；兩棒皆未略過驗證，如實記錄。
- **`[他包回報]` 未親跑**：四方全部數字、三棒的紅綠與普查；主控親跑範圍＝〈二〉〈六〉〈七〉。
- **nightly**：10-03 02:00 跑在 R191 樹；本輪修法首次 launchd 真跑＝10-04 02:00。
- **副作用自陳**：SA 12 支探針逐字稿（依鐵律 7 不刪；累計探針 22 份，普查母體請以 `entrypoint` 排除）、`claim_freshness.jsonl` +2 列、`~/.autosdd/traces` 新檔 `autosdd_quota_stability_sonnet_pace.json`；Dev-A 臨時舊版 hook 鏡像已刪；各角色真端點呼叫皆 0（SA 探針視窗內 hook 補量 2 次、全 200）。
- **複審鏡未派**：四方＋三棒收工時額度守衛已進 halt 帶（`--pace`：`kind=weekly_all 95% … band=halt … cap=0`），機械守衛判不可再扇出，主控不以模型判斷推翻 ⇒ 本輪零複審鏡（R189～R191 皆有兩鏡）；主控文字（本檔〈〇〉〈一〉〈四〉〈五〉〈八〉與六筆帳本新列）**未經零信任稽核**，R193 第一件事＝鏡 B 零信任稽核本檔並出〈文件訂正清單〉。
- **本機 hook 已改且立即生效**：zsh 下 `${PIPESTATUS[0]}` 會被判準④擋下（設計如此）。

## 六、收尾親驗（主控親跑；本場 tool_result 逐字；全套與 push 見〈七〉）

- **Developer-A 交件後親驗**：替身 hook（stdin PreToolUse JSON）`SHELL=/bin/zsh`＋`ls | tail -3; echo "rc=${PIPESTATUS[0]}"` ⇒ `rc=2`，stderr 首行 `🔴 這一次呼叫沒有執行（只擋這條指令字串，Bash／Write／Edit 本身都能用）：\`${PIPESTATUS[0]}\` 在 zsh（本機 Bash 工具殼）展開成空字串，讀到的不是 rc。zsh 要寫 \`${pipestatus[1]}\`（下標從 1 起）；最穩：…`；同指令 `SHELL=/bin/bash` ⇒ `rc=0`；zsh＋`${pipestatus[1]}` ⇒ `rc=0`。`convergent_tools_clause(False)` ⇒ `收斂型工具（Read／Write／Edit／Bash／git，寫壞的 Bash 只擋那一次呼叫）不受影響`、`(True)` ⇒ `…PowerShell…`。真 SessionStart hook（本窗 payload）附件含 `context 水位讀 \`/Users/wuweihong/.autosdd/context_feed/c00d202a-….json\`…額度讀 \`/Users/wuweihong/autosdd_quota.json\``（絕對路徑在位）；直呼 `verify_hint()` 不帶注入時退成「本 session 的 statusLine feed 檔」措辭（設計如此）。
- **Developer-B 交件後親驗**：`--protocol-status` rc=0 `protocol_sha256=e0ec9c359df43598eb33a138d8597984d9cd891bb9079f148037a0dedf215d93（manifest 11 檔）`／`輪帳本 1 列；window_len=1；評估: NOT-EVALUABLE(1/6)`；`--five-question --since 2026-09-20` rc=0：`母體 15 支`、`Q1′a 誤擋 PASS 0／hook 阻斷 8`、`Q1′b 宣稱≠阻斷 PASS 0／0`、`Q1′c 前5呼叫被擋 NOT-EVALUABLE(15/20) 2／15（≤0.25）；首呼叫被擋 1／15`、`Q2′ 首查序號 FAIL 逾期或從未 2／15 [('16692980', 31), ('452cab3f', 12)]`、`Q3′ feed 差 PASS 10 對；max|差|=0`、`非 hook 阻斷…{'automode-blocked': 3}`；`--since 2026-10-03T01:21:56+08:00`：`母體 1 支`、Q1′a／b PASS（空洞）、Q1′c `NOT-EVALUABLE(1/20) 0／1`、Q2′ `NOT-EVALUABLE(1/5) 0／1`、Q3′ `NOT-EVALUABLE(1/3) 1 對；max|差|=0`。
- **主控親手（收尾單人窗口）**：Δ3 字面改 `這次寫入會照常執行、不需處理（有人值守只提醒）`（hook＋鎖同改）⇒ `test_block_destructive_git_r83` `Ran 233 tests in 9.091s OK REAL_RC=0`、ruff 兩檔 `All checks passed!`；根 CLAUDE.md 鐵律六誠實劃界句改「小寫 `pipestatus`／`pipefail`／`# waitform-ok:` 豁免，大寫 `PIPESTATUS` 只在非 zsh 殼豁免」；`governance_docs.py` 登記本檔。
- **帳本三閘門（親跑）**：`check_defect_log_crossref.py` 無逃生口 rc=1 且只剩 `淨額棘輪違反：本輪新增未結 2 筆 > 結案 1 筆 … 新增：DEF-200-471、DEF-200-472`（本輪四方審計＝發現輪，依該判準自述的出口②以 `AUTOSDD_NET_RATCHET_OFF=1` 單次放行、理由寫進 commit 訊息）；`AUTOSDD_NET_RATCHET_OFF=1` 單次 rc=0 `✅ 缺陷帳本跨文件狀態一致：帳本 173 筆有效狀態紀錄、19 份掃描目標皆無矛盾 … 具名治理文件 144 份皆已登記`；`check_handoff_carriers.py` rc=0 `✅ 每一筆前瞻延後宣稱都有帳本承接載體`；`archive_defect_log.py --check` rc=0 `✅ 帳本保全稽核通過（70 檔／1582 個 ID…）`；`git diff --check` rc=0；`check_loc_budget.py --json` rc=0。被格式鎖擋：新列 467 初稿 802 bytes >700 ⇒ 瘦身至 663；既有列 R192→R193 改派八列逐列等長（grew: []）；464 改 fixed 兩次超過 HEAD 位元組（774／715 > 633）⇒ 改以預算內候選句；`governance_docs.py` 註解 E501 103>100 ⇒ 縮短。
（棘輪重釘、MIN_TESTS、根層全套見〈七〉）

## 七、根層全套、push 與雲端驗收

- **棘輪重釘（主控親手，結構編修→print→填數→print→填 sha 一次收斂）**：`--print-guard-lines` 改前 `淨額 112344→112921 (+577)`、`逐檔漂移 4 支`（bdg +153／claim +37／cbg +9／session_brief +378）；追加重釘列、回歸鎖軌同輪列（申報 309）、`(192, 521)` 兌現列、接鏈列後 `淨額 112921→112937 (+16)`；填數後 `112937→112937 (+0)`、sha `8b3ab8b64522…` 填入後再 print 仍 `+0` 且 sha 不變；`_REPIN_LOG_FROZEN_PREFIX_LEN` 322→323、接鏈 `e5dd2c337e82→8b3ab8b64522`（載體 DEF-200-467）；重新武裝 `_REPIN_NET_CAP_DUE_ROUND=194`／`TARGET=520`；`<!-- guard-total:R192 -->` 寫入 `AutoSDD_improving_112.md` 與 `CrossPlatform_R145_Scan_Findings.md`；`test_adr_xplat001_c1c2_lock` 單模組 `OK`、`[Scan-H triplet] UEP=5 AC=47 GLC_FILES=88 GLC_LINES=112937`、`LOCK_RC=0`。
- **根層全套（主控親跑，背景阻塞）**：第一次 `REAL_RC=1` 3 紅＝`test_windowsapps_guard_cross_consistency…test_zero_guard_bare_python_sites_match_registry_exactly`（新檔 `tools/session_gate_acceptance.py:168` 的 JSON 鍵名 `"python"` 被裸 python 站點掃描命中 ⇒ 改名 `python_version`，鎖同改；該模組＋`test_session_brief` 重跑 `Ran 167 tests … OK (skipped=1) RC=0`）＋淨額棘輪 2 支（預期）；`發現 5101 個測試（下限 5058）`。MIN_TESTS 重釘 `5058 → 5101`（被取代原行補登 `CrossPlatform_Guard_Line_History_MinTests.md`）、`sync_onboarding_baselines.py --write` ⇒ `✅ 已回填 [rootunit-baseline-live:] → {'tests': 5101}`、`--check` rc=0、`--check-snapshot` rc=0。第二次 `REAL_RC=1` **恰 2 紅**＝`test_check_defect_log_crossref.TestEarlyExitAnnouncesUnrunChecks.test_the_real_gate_still_reaches_the_late_checks`／`TestMain.test_main_against_real_repo_is_clean`（皆「淨額棘輪違反：本輪新增未結 2 筆 > 結案 1 筆」，commit 後 HEAD＝工作樹差集為空即轉綠——R190／R191 同型先例）；`發現 5101 個測試（下限 5101）`、`[skip census] tools/tests@darwin 共 47 支：platform=47／…／untagged=0`、`[M6 id 集合] ✅`、`✅ 真實 TEMP 圍籬 … 零變動`。
- **commit／push（主控親跑，背景阻塞）**：`git add -A`（32 檔，`2430 insertions(+), 421 deletions(-)`）→ `AUTOSDD_NET_RATCHET_OFF=1 git commit`（理由在訊息內）`COMMIT_RC=0` ⇒ `5a502fc0`；`git push origin main` ⇒ `[pre-push dispatcher] ✅ 本次 push 觸發的所有 leg 皆通過（rc=0）`、`d337e3f6..5a502fc0  main -> main`、`PUSH_RC=0`；`git rev-parse HEAD origin/main` 皆 `5a502fc05a9a5450b56983345ad7e54bc2055b58`、工作樹 0 行。
- **雲端第一次（`5a502fc05a9a5450b56983345ad7e54bc2055b58`；背景輪詢 11 次至全部 completed）**：root-infra-ci 37092521054 **success**、AutoClaude CI 37092521076 **success**、macos-compat-ci 37092521219 **failure**、windows-compat-ci 37092521064 **failure**（non_success 2）；aisdlc-sdd-ci／shellcheck-ci 依 paths 白名單未觸發。**紅因（兩支同一根因，`gh run view --log-failed`）**：AISDLC_SDD `scripts/tests/test_ci_paths_cover_root_consumers.py:1233` `AssertionError: 根層消費檔未列入 macos-compat-ci.yml paths（只改該檔時其回歸鎖不會跑，DEF-101-042 同構）：['tools/session_gate_acceptance.py']`（windows-compat-ci.yml 同句；mac `2 failed, 360 passed, 2 skipped`、win `2 failed, 361 passed, 1 skipped`）＝新根層消費檔（被 `test_session_brief.py` import）沒進兩支 compat workflow 的 `paths:`；本機 pre-push 看不到它（該鎖只在 compat-ci 的 smoke leg 跑）。**修法**：兩支 workflow 的 push／pull_request 兩個 paths 區塊各加 `- "tools/session_gate_acceptance.py"`（4 行）；本機 `cd AISDLC_SDD && python -m pytest scripts/tests/test_ci_paths_cover_root_consumers.py -q` ⇒ `49 passed in 12.98s` RC=0；根層 workflow 讀取測試三模組 RC=0。雲端第二次見下。
- **雲端第二次（`c1ca2d2fe9c00097a1f32f511fbc21034b80a29b`＝workflow paths 補列＋〈七〉回填；pre-push `✅ 本次 push 觸發的所有 leg 皆通過（rc=0）`、`5a502fc0..c1ca2d2f  main -> main`、`PUSH2_RC=0`、HEAD＝origin/main）**：root-infra-ci 37093332661 **success**、macos-compat-ci 37093332660 **success**、windows-compat-ci 37093332671 **success**（push 事件 3 支，non_success 0）；AutoClaude CI／aisdlc-sdd-ci／shellcheck-ci 依 paths 白名單未觸發（本次只改 workflow 與 docs；缺席＝未驗證、非通過——AutoClaude CI 對主修法 `5a502fc0` 已 success）。本節為 push 後回填，以 docs commit 再 push 一次（HEAD＝origin/main 以該次 push 回報為準）。

## 八、交棒／掌舵者側待辦

### Q5 評估（掌舵者原話：「請詳細回覆是否已經收斂? 給我評估說明!」）

- **依判準②′（掌舵者本輪採納）：NOT-EVALUABLE(1/6)**——窗口從協定 manifest 落地的本輪起算，第 1 輪；最早可評估 **R197**。本輪 `new_p_le2=1`（467），依②′「近 6 輪合計 ≤2、P1=0、最近一輪零新」，467 佔掉 2 個名額中的 1 個；若 R193～R197 每輪零新 P≤2 且 Windows 證據到位，R197 可首次通過。
- **症狀面**：Mac 上 Q1／Q2 在修法後真實 session n=1 與探針 9/9 下**看不到**；但這不是「不存在」——真實母體太小、探針模型不同、Windows 未驗。Q4′ Windows 缺席＝FAIL 是本輪結構上過不了的那一條。
- **根因面有進展（縮庫存真的開始了）**：①「哪些工具不受影響」8 出口→1 導出；②殼判定抽成純函式（zsh／bash 差異第一次進守衛）；③量測器從子字串判定改成 harness 欄位判定、全工具可見；④「查真實數據」不再只有 Bash 一條路（Read 退路）；⑤協定凍結讓「審查協定變了」成為要寫理由的動作。
- **為什麼還不能停**：(a) 本輪又挖到 1 個同根變體（467＝086 的 zsh 面），證明「同一事實兩個出口」型庫存還在（SHELL 這個事實：hook 訊息知道、豁免不知道）；(b) Windows 零證據；(c) 471／472 是兩個已知的量測盲區，沒修之前「0 誤擋」只對頂層成立。
- **建議**：R193 做「結案輪」（471／472／463／466 四件程式修法＋Windows 證據），不派四方挖；R194 起每輪四方審查按凍結協定跑、只量不挖新面。

### 掌舵者側一條指令（Windows 11；取代十餘項手動清單；貼回 JSON 即為 Q4′ 證據）

```powershell
$repo = 'C:\<該機 checkout 絕對路徑>\AISDCL_Agent'   # 唯一要改的一行；先 git pull 到本輪 commit
& (Join-Path $repo '.venv\Scripts\python.exe') (Join-Path $repo 'tools\session_gate_acceptance.py')
```
PASS 判式（主控讀 JSON）：`platform=="win32" ∧ statusline.installed ∧ statusline.matches_current_checkout ∧ hook_carrier.exists ∧ verify_hint.default_push_location ∧ verify_hint.default_lastexitcode ∧ check.rc==0 ∧ generated_at≤14 天 ∧ repo_head 為本輪 commit 的祖先（無距離上限；R193 鏡 B 訂正：params.json 曾有的 q4_max_commits_behind 無消費者）`。沒有 `.venv` 就先跑 `tools\dev_start.py`（或貼出錯誤原文）。

### 下輪的機械義務（主控記名）
- 護欄行數棘輪：本輪 `(192, 521)` 已兌現（見〈七〉）；下一到期輪見 `_REPIN_NET_CAP_DUE_ROUND`；`_ROOT_TOOLS_OLD_SCALE_DEBT_DUE_ROUND=193`；`_PHASE2_REVIEW_LOG` 視窗到 R194。
- 承接列：**DEF-200-471／DEF-200-472 → R193**；**DEF-200-463／DEF-200-465／DEF-200-466 → R193**（本輪零落地，改派）；**DEF-200-242／DEF-200-246／DEF-200-459／DEF-200-199 殘餘／DEF-200-193 → R193**（同上）。
- ②′ 輪帳本：每輪收尾追加一列 `FiveQuestion_Round_Ledger.jsonl`（`--protocol-status` 先跑、sha 不同就帶 `window_reset:true`＋理由）；帳本內該輪新立 P≤2 列全部要出現在 `new_p_le2` 或 `excluded_p_le2`。
- 下輪 SA 探針沿用凍結協定 `probes/PA.txt`／`PB.txt`／`PC.txt`；模型是否改 Fable（效度 vs 成本）交掌舵者裁決。
- Δ3 字面（`_GOVWRITE_NOTE_MSG`）主控收尾已改為 PreToolUse 時點正確的措辭（見〈六〉）。

### 本輪未做（不塗綠）
- Windows 真機：全部未驗（第 6 輪）；丙案指令在上。
- DEF-200-471／472／463／465／466／242／246／459／199 殘餘／193：零落地，承接如上。
- T3 退路效果量測、探針模型與使用者一致：未做。

## 九、搬遷史料
（Developer 各棒 lore 併入）

### A. Developer-A 搬出的原文（T1／T2／T3；逐字）

# r192 Developer-A 史料（被改掉的原文；主控搬進證據檔〈九〉，程式碼只留一句摘要）


## tools/lib/quota_messages.py（被取代的原文）

### 常數＋halt_convergent_clarification（原樣）

```python
# 🔴 R158（反駁者 refute_q1q2.md §S4／§0 本場實測；Q1／Q2 誤讀「被擋」的合理成因 round-label-ok
# 之一）：halt 帶第二次以後、**每一次** Read／Bash 都印的那則重複訊息（見 `quota_gate.py`
# 1140 行附近的既有註解）此前沒有帶「收斂不受影響」的澄清——而它偏偏是撞牆期間人唯一
# 持續看得到的版本。首則訊息（下面 `quota_halt_message()` 的 head）與重複訊息現在共用
# 同一句，人話面 SSOT 收斂到這裡，避免兩處各自遣詞再度漂移。
# Windows 版見 `_HALT_CONVERGENT_CLARIFICATION_WINDOWS`（DEF-200-413：Windows 上
# Bash 工具另由鐵律一 hook（`block_bash_on_windows.py`）整支停用，「Bash…不受影響」
# 對模型是假話，與 `session_brief.py::_RC2_CLARIFY_WINDOWS`＝同一句話的姊妹站點）。
HALT_CONVERGENT_CLARIFICATION = (
    "你剛才那次工具呼叫已正常執行完成；收斂型工具（Read／Write／Edit／Bash／git）"
    "不受影響，只有扇出型（Task／Agent／Workflow／WebFetch／WebSearch）暫停；"
    "真實數字現查：`python tools/session_resume_planner.py --pace`"
)

# DEF-200-413：Windows 上 `HALT_CONVERGENT_CLARIFICATION` 那句「Bash…不受影響」對模型
# 是假話——`block_bash_on_windows.py`（鐵律一）對 Bash 工具整支 exit 2。改列 PowerShell，
# 並比照 `session_brief.py::_RC2_CLARIFY_WINDOWS` 補上同一句括號說明。
_HALT_CONVERGENT_CLARIFICATION_WINDOWS = (
    "你剛才那次工具呼叫已正常執行完成；收斂型工具（Read／Write／Edit／PowerShell／git）"
    "不受影響，只有扇出型（Task／Agent／Workflow／WebFetch／WebSearch）暫停；"
    "（Windows：Bash 工具另由鐵律一 hook 停用，跑指令用 PowerShell 工具、"
    "改檔用 Write／Edit，不要先試 Bash——那個阻斷不是「不能寫檔」）"
    "真實數字現查：`python tools/session_resume_planner.py --pace`"
)


def halt_convergent_clarification(windows: bool | None = None, event: str = "PostToolUse",
                                  tool: str = "") -> str:
    """halt 帶「收斂不受影響」澄清句，平台感知版（DEF-200-413）。

    `windows=None` 時以同目錄 SSOT `platform_utils.is_windows()` 現查——本檔不得
    自己寫 `os.name`／`sys.platform` 分支（根 CLAUDE.md〈Windows 側單一載具原則〉
    鐵律三）。import 失敗時一律 fail-open 回 POSIX 版
    （`HALT_CONVERGENT_CLARIFICATION`）：hook 行程不保證 `tools/lib` 以外的模組在
    `sys.path` 上，簡報失敗不得反過來擋住 halt 訊息本身。

    DEF-200-435：`event="PreToolUse"`＝扇出工具根本沒執行，首句「你剛才那次工具呼叫已正常
    執行完成」對它是假話（且與同則訊息的「扇出型工具一律不執行」互相矛盾）⇒ 只換首句，
    其餘（收斂工具清單、Windows 括號、`--pace` 指令）與預設值同源；預設值輸出逐字不變。
    """
    if windows is None:
        try:
            windows = bool(platform_utils.is_windows())
        except Exception:  # noqa: BLE001 — 見上：fail-open 回 POSIX 版
            windows = False
    text = _HALT_CONVERGENT_CLARIFICATION_WINDOWS if windows else HALT_CONVERGENT_CLARIFICATION
    if event == "PreToolUse":
        return f"這次 {tool or '扇出型'} 呼叫已被擋下、沒有執行；" + text.split("；", 1)[1]
    return text


```

### degraded_convergent_clarification（原樣）

```python
def degraded_convergent_clarification(windows: bool | None = None) -> str:
    """量不到通知（PostToolUse）的「收斂型工具不受影響」澄清句（DEF-200-453）。

    與 halt 版同源——平台分支與工具清單住 `halt_convergent_clarification()`，本檔不得有第二份：
    只取它「…不受影響」那半句；後半的「只有扇出型…暫停」是 halt 專屬，量不到時扇出型只是被
    收緊到硬上限（`degraded_cap`）而不是停用，照抄會叫模型停派。"""
    head = halt_convergent_clarification(windows).partition("，只有扇出型")[0]
    return head + "，扇出型工具只受上面那個硬上限約束，量到讀數就依真實水位重判。"


```


## tools/lib/session_brief.py（被取代的原文片段，原樣）

```python
#: halt 帶反覆出現的 rc=2 紅字容易被誤讀成「全部工具被擋」（refute_q1q2.md §0 實測）；
#: 這句話固定跟簡報一起送出，讓模型從第一時間就有正確的心智模型。POSIX 版原文；
#: Windows 版見 `_RC2_CLARIFY_WINDOWS`（DEF-200-412：這句話在 Windows 上對模型是假話
#: ——Bash 另由鐵律一 hook 停用，見 `rc2_clarify()` 的平台判準）。
_RC2_CLARIFY = ("hook 的 rc=2 紅字只代表扇出型工具（Task／Agent／Workflow／WebFetch／"
                "WebSearch）暫停；Read／Write／Edit／Bash／git 這類收斂型工具不受影響。"
                "（壞寫法的 Bash 另由指令形態守衛擋下，stderr 附一行解法，照改重跑即可。）")

#: DEF-200-412：Windows 上 `_RC2_CLARIFY` 那句「Bash…不受影響」對模型是假話——
#: `block_bash_on_windows.py`（鐵律一）對 Bash 工具整支 exit 2。新視窗的模型先被
#: 這句安撫、下一步撞牆後又把「Bash 被擋」誤讀成「寫檔被擋」（掌舵者 Q1 原話：
#: 「才開新視窗，就說他被擋不能寫檔案用工具了」）。改列 PowerShell，並點破那個誤讀。
_RC2_CLARIFY_WINDOWS = (
    "hook 的 rc=2 紅字只代表扇出型工具（Task／Agent／Workflow／WebFetch／"
    "WebSearch）暫停；Read／Write／Edit／PowerShell／git 這類收斂型工具不受影響。"
    "（Windows：Bash 工具另由鐵律一 hook 停用，跑指令用 PowerShell 工具、"
    "改檔用 Write／Edit，不要先試 Bash——那個阻斷不是「不能寫檔」；"
    "壞寫法的 PowerShell 指令會被 lint 擋下，訊息附出口，照改重跑即可）"
)

# ----
def rc2_clarify(windows: bool | None = None) -> str:
    """rc=2 誤讀澄清句，平台感知版（DEF-200-412）；平台判準見 `_windows()`。"""
    return _RC2_CLARIFY_WINDOWS if _windows(windows) else _RC2_CLARIFY


def verify_hint(windows: bool | None = None) -> str:
    """查證指令＋安全形態，平台感知版（SA-01；模式同 `rc2_clarify()`）。"""
    return _VERIFY_HINT_WINDOWS if _windows(windows) else _VERIFY_HINT

# ----
    try:
        tools_dir = str(Path(__file__).resolve().parent.parent)
        if tools_dir not in sys.path:
            sys.path.insert(0, tools_dir)
        import install_statusline  # noqa: PLC0415 — 見上：刻意延遲到呼叫當下

# ----
           f"{verify_hint()}{rc2_clarify()}")
```


## .claude/hooks/block_destructive_git.py

### hook：判準④豁免／首行／治理檔提醒（被取代的原文行，HEAD 版）

```diff
@@ -149,4 +149,7 @@ mac 清掉的檔案與 Windows 一模一樣，而事故就發生在 macOS——
-  的 exit code**（不在任何指令字串裡）。豁免是**整條指令**粒度：任一處有 `PIPESTATUS`／
-  `pipefail` 就不判，一句用對、另一句用錯會漏——此為漏擋方向。誤擋方向：白名單濾器以
-  `exit` 傳有語意的 rc（`sort -c`／`awk '{exit N}'`／`sed '/x/q1'`）照樣命中，走
-  `# waitform-ok:`。

@@ -504,3 +512,3 @@ def mask_inert(text: str, *, keep_comments: bool = False,
-    `keep_status=True`（判準④，DEF-200-086）：**雙引號**字串內的 `$?`／`${?}` 原樣保留
-    ——`echo "rc=$?"` 的 `$?` 會被殼展開，整段遮掉就看不見最常見的讀法；單引號內不展開，
-    照遮。

@@ -567 +575 @@ def _mask_pass(text: str, keep_comments: bool, keep_status: bool,
-                for m in _STATUS_READ_RE.finditer(text, i, j):

@@ -1064 +1072,2 @@ _PIPE_OPS_RE = re.compile(r"[<>]&|&>>?|(\|&|\|\||&&|[|;&\n()`])")
-#: 豁免（指令任一處出現即整條不判）：這三個是 rc **不被**遮蔽的正解，不是遮蔽。

@@ -1067 +1076 @@ _RCMASK_SAFE_RE = re.compile(r"pipestatus|pipe_?fail", re.IGNORECASE)
-#: 長篇指引）。

@@ -1216,4 +1240,7 @@ def waitform_hits(command: str, *, run_in_background: bool = False,
-      的。豁免：指令內任一處有 `PIPESTATUS`／`pipestatus`／`pipefail`（行內
-      `# waitform-ok:` 走 `main()` 的共用豁免）。🔴 刻意**不判** `grep`／`rg`／`test`／
-      `jq`（rc 有語意，`ls | grep x; echo $?` 合法）與「只有管線、沒讀 rc」。PowerShell
-      側的 `$LASTEXITCODE` 另由 `lint_powershell_command.py` 守。

@@ -1222,2 +1249,4 @@ def waitform_hits(command: str, *, run_in_background: bool = False,
-      語意（transcripts 母體零例）。出口：行內 `# waitform-ok: <WHY>`（理由必填；
-      `AUTOSDD_UNATTENDED` 有設時無效），或改讀 `${PIPESTATUS[0]}`。

@@ -1268,3 +1297,8 @@ def waitform_hits(command: str, *, run_in_background: bool = False,
-    if tool == "Bash" and not _RCMASK_SAFE_RE.search(command):
-        name = _rcmask_filter(_fold(command, keep_status=True))
-        if name:

@@ -1293 +1329 @@ _RCPIPE_LEAD = (
-    "🔴 已擋下：`… | head`／`… | tail` 之後讀 `$?`，讀到的是 head／tail 的 rc。"

@@ -1319 +1360 @@ _RCPIPE_FOOTER = (
-    "  `pipefail` 也放行。\n"

@@ -1439,2 +1480,2 @@ _GOVWRITE_NOTE_MSG = (
-    "這只是提醒，這次寫入已放行（有人值守 ⇒ 只出聲不阻斷）；"
-    "無人值守回合對它是唯讀的，改完請跑對應守衛測試。")

@@ -1577,2 +1618,3 @@ def main() -> int:
-            rc_only = all(h.startswith(_RCPIPE_TAG) for h in wait_hits)
-            message += ((_RCPIPE_LEAD if rc_only else "") + _WAITFORM_HEADER
```


## tools/tests/test_block_destructive_git_r83.py

### hook 測試：被取代的原文行（HEAD 版）

```diff
@@ -1183 +1183 @@ _RCPIPE_ALLOW: tuple[str, ...] = (
-    "cmd | tail -1; echo ${PIPESTATUS[0]}",  # bash 正解

@@ -1217 +1241,2 @@ class TestIronLaw6RcMaskedByPipe(unittest.TestCase):
-        """假紅是這道鎖的生死線：擋到讓人無法工作的守衛會被整個關掉。"""

@@ -1219 +1244,2 @@ class TestIronLaw6RcMaskedByPipe(unittest.TestCase):
-            with self.subTest(command=command[:60]):

@@ -2455 +2602,2 @@ class TestGovernanceFilesAreReadOnlyWhenUnattended(unittest.TestCase):
-                for word in ("治理檔", "有人值守", "這只是提醒，這次寫入已放行"):
```


## tools/tests/test_session_brief.py

### 簡報測試：被取代的原文行（HEAD 版）

```diff
@@ -238,5 +240,5 @@ class Rc2ClarifyTest(unittest.TestCase):
-    def test_posix_variant_is_unchanged(self) -> None:
-        self.assertEqual(
-            sb.rc2_clarify(windows=False), sb._RC2_CLARIFY,
-            "POSIX 版必須逐字等於既有 `_RC2_CLARIFY`——不得順手改動 mac/Linux 讀到的句子",
-        )

@@ -269 +271,2 @@ class VerifyHintTest(unittest.TestCase):
-            self.assertIn(sb.verify_hint(windows=windows), got)
```


## tools/lib/quota_messages.py（其餘被取代的原文行）

### quota_halt_message 的 PostToolUse 抬頭（原樣；循環定義：「照常可用的工具」未列名）

```python
            f"🟡 額度到達**停止**水位（{subject}）——這是一次性提醒，不是錯誤；照常可用的工具"
            "都不受影響。\n")
```

### pace_line 附近註解（原樣；與收斂型工具無關，只為讓「不受影響」字面只剩函式本體一處）

```python
#: 那條軸不被本行悄悄繞過）。`live == cap` 時 min 的結果仍是 0，QA 指名的跨層對帳鎖不受影響。
```


### B. Developer-B 從 `tools/probe/audit_session.py` 搬出的原文（逐字）

# audit_session.py 搬出的沿革敘事（原文逐字；程式碼端各留一句摘要）

共 28 段；搬出 303 行、程式碼端改留 122 行，淨搬出 181 行。

## K1 模組 docstring（WHY／R78 崩塌逐支／R78 逐工具／判準性質／R79 量測窗汙染／R80 分期兩個坑）（107 行 → 留 45 行）

```text
"""每輪收尾的 session 逐字稿稽核器 —— PowerShell 工具面第一個觀測者。

WHY（本輪掃描的立案量測）
--------------------------
「Windows 上常犯低級錯誤」的機械層根因不是紀律不夠：本輪逐字稿實測顯示，
**有觀測者的那條規則違規 1 次且被當場擋下，沒有觀測者的那些規則違規率 20~35%**。
而整個 PowerShell 工具面在本輪之前**零觀測者**——鐵律二（禁裸 cd）、鐵律四
（宣稱先於查證）、以及「在對的 shell 裡現寫一段沒驗過的碼」，這三類的違規面
全部在**指令字串的內容**裡，而那個字串從來不會變成 repo 裡的檔案，於是全庫
所有靜態掃描器結構上都看不見它們。

但它們並非不可觀測：Claude Code 把每一次工具呼叫逐字寫進 session 逐字稿
（PreToolUse payload 的 `transcript_path` 欄就是那份檔案的權威路徑，本輪以
一支拋棄式 dump hook 實測確認）。repo 內此前**零消費者** ⇒ 這把「徹底解法」
從「要改 Claude Code」降級成「寫一支讀 jsonl 的稽核腳本」。本檔就是那支。

🔴 邊界：只能當量測器，不得接成閘門
------------------------------------
逐字稿是 **untracked、機器本地、隨時會被清掉**的資料。所以本檔：
  · **只能當每輪收尾的量測器**——跑一次、把四個數字與宣稱清單記進帳本；
  · **不得接成 push 閘門或 CI 閘門**。別台機器（或清過快取的同一台）上那個
    目錄根本不存在，接成硬閘在結構上恆紅，而恆紅的閘門會被整個關掉，比沒有
    鎖更糟（本 repo 的 ARCH-R59-NB4 判例逐字記載過這件事）。

它自己失效的偵測：**逐支逐字稿**檢查「有記錄、卻一支帶 command 的 shell 呼叫都
抽不到」⇒ fail-loud（rc=1）。掃描面崩塌（目錄搬家／欄位改名／正則失效）不得靜默
通過成「本輪零違規」——那個失效方向看起來正好像「變乾淨了」，比紅更危險。

🔴 為何崩塌判準必須是 per-session（R78 修 SD-03）
--------------------------------------------------
R77 版把這個判準建在**跨 session 合計**的 `shell_calls == 0` 上，而預設用法會把整個
逐字稿目錄（本機實測 51 支／109 MB）一起加總——那是一個**只會單調增長的歷史總量**。
於是「今天格式改了、今天起的每一支都抽不到東西」這個唯一要防的失效，被昨天以前的
四千多筆蓋掉，分支結構上打不出來。它識別了正確的危險方向，卻把判準建在打不到的
地方。改成逐支之後，格式一變，**當天新生的那一支就會讓 rc=1**。
搭配 `--since`／`--latest` 把量測窗縮到本輪那幾支，才是「本輪零違規」該有的分母。

誠實劃界：一支「真的整場沒用過 shell」的逐字稿（純問答／純讀檔）會被判成崩塌訊號。
本機 51 支實測是 0 支，但它是真實的假陽性面。處置是**去看那一支**並在交件寫明理由，
不是把判準關掉——沉默的方向比誤報危險。

🔴 為何計數必須逐工具（R78 修 SD-04）
--------------------------------------
四個形態全部是**PowerShell 工具面**的規則：鐵律二的裸 cd 講的是「PowerShell 工具的
cwd 跨呼叫持續」、`$LASTEXITCODE` 是 PS 概念、「不要寫裸 bash」講的是在 PS 指令裡
寫。R77 版把 Bash 與 PowerShell 兩個工具的指令混在同一個分母裡數，實測訊噪比慘烈：
裸 cd 43︰1820、裸 bash 0︰80（後者 100% 假陽性——在 Bash 工具裡寫 `bash x.sh`
本來就是對的）。更糟的是**方向性偏誤**：Bash 工具已被 `block_bash_on_windows.py`
擋掉 ⇒ 未來輪的 Bash 呼叫歸零 ⇒ 這兩個數字會自己「變好看」，而那不是真的改善。
`COMMAND_PATTERNS` 因此是 `{工具名: {形態: 正則}}` 二維結構，報表逐工具印、
每一列都標明分母是**哪一個工具**的呼叫數。`Bash` 的形態集合刻意是空的：這個工具
本身就是違規（鐵律一），量它的指令內容沒有意義，它只出現在 `bash_tool_attempts`。

判準的性質（誠實劃界）
----------------------
· 四個計數是**字串形態偵測**：量的是「出現過幾次這種寫法」，不是「有幾次真的
  造成了錯誤結果」。數量級可信，**確切值不可被引用成常數**。
· 宣稱對帳是**啟發式**：比對一句宣稱與它前面 N 個 tool_result 的內容有無可佐證
  字樣。它抓得到「完全沒有對應輸出的宣稱」，抓不到「有輸出但輸出被誤讀」。
  列出的每一筆都是**待人工看一眼的線索，不是判決**。

用法
----
    python tools/probe/audit_session.py                 # 本專案全部 session
    python tools/probe/audit_session.py --json
    python tools/probe/audit_session.py --transcript <某支 .jsonl>
    python tools/probe/audit_session.py --since 2026-08-06   # 只掃本輪那幾支
    python tools/probe/audit_session.py --latest 5           # 只掃最近改動的 5 支
    python tools/probe/audit_session.py --latest 5 --exclude-self   # 把自己剔出分母
    python tools/probe/audit_session.py --parity             # 兩端對拍，有分歧即 rc=1

🔴 量測窗會被「量測這件事本身」汙染（R79）
------------------------------------------
`--latest N` 是 **mtime 排序的浮動窗**，而每一支同期跑的 agent 都會在同一個逐字稿目錄
開一支新檔 ⇒ 派愈多 agent，窗裡就愈全是 agent、愈少是掌舵者本人，而 Q4 問的是掌舵者。
本輪實測：同一條指令在一小時內量到三組數字（PowerShell 分母 349→281→182）、rc 由 0
翻成 1，最後窗裡 5 支有 3 支是本輪自己派出去的掃描 agent，真正在做事的那支已被擠出去。
所以：
  · 報表**開頭固定印出量測窗清單**（檔名／mtime／PowerShell 呼叫數／開場白），
    帳本引用任何數字時必須連它一起記，否則下一個人重跑會拿到別的數字。
  · 要排除就用 `--exclude <子字串>`／`--exclude-self`（讀 `CLAUDE_CODE_SESSION_ID`）。
  · 誠實劃界：逐字稿裡**沒有**欄位能自動分辨「掌舵者 session」與「派出去的 agent」
    （`isSidechain`／`entrypoint`／`origin`／`userType`／`promptSource` 本輪逐欄實查，
    兩者取值相同），所以本檔不猜——它只把資訊攤開讓人一眼認得。

🔴 「觀測者上線前 vs 上線後」的分期：**兩個坑，都要繞開**（R80／S7-08）
------------------------------------------------------------------
上一版在這裡逐字給出三期的現查指令，讀起來像是照著跑就得到答案。它有兩個獨立的
結構性問題，兩個都會讓那組數字比它看起來的更沒有意義：

**① 切片單位是「檔案」而不是「記錄」，誤差是兩個數量級。** `--since`／`--until` 篩
的是檔案 mtime（＝**最後**寫入時間），於是一支橫跨分界點的長 session 會**整支**落在
後段。本輪實測這件事的量級：以檔案 mtime 切「Bash 阻斷上線後」得到 **3,284** 次 Bash
呼叫，以每一筆記錄自己的 `timestamp` 切得到 **7** 次——前者把該工具整個歷史都算進了
「上線後」，而結論正是要從那個分母算出來的。⇒ 分期一律用 `--record-since`／
`--record-until`（逐筆 `timestamp`），`--since`／`--until` 只適合「挑本輪那幾支檔」。

**② 判準是向 live hook 借的，而那支 hook 的判準改過 4 次**（`a7a3080` 建立、
`cf11cd9`、`60904df`、`b07432c`）。所以分期比較答得出來的是「**同一把今天的尺**量
不同時期的行為有沒有變」，答**不**出「當時那個觀測者實際擋下了什麼」——當時在崗的
是另一個版本的判準。這兩個問題不同，先前的寫法把它們混成同一句話。報表因此固定印出
**判準指紋**（借來那支 hook 的內容雜湊）：換了指紋的兩組數字不可以放在一起比。

    --record-until 2026-08-03T16:26:15                             # 兩面皆無觀測者
    --record-since 2026-08-03T16:26:15 --record-until 2026-08-07T00:05:53
    --record-since 2026-08-07T00:05:53                             # PowerShell 面也有
"""
```

## K2 攔截端純函式向 hook 借的依賴方向註解（9 行 → 留 3 行）

```text
# 🔴 攔截端的**純函式**（遮蔽器與規則①的順序敏感判準）直接向 hook 借，不再抄第二份。
# 依賴方向是 `tools/probe → .claude/hooks`，與 `tools/session_resume_planner.py`
# 同一條理由且不可反向：那支 hook 由 `runpy.run_path` 起、`sys.path` 上既沒有
# `tools/` 也沒有 `.claude/hooks/`，它 import 誰都會在 import 期爆掉，而模組層爆掉
# 會破壞它的 fail-open 契約 ⇒ 它永遠只能是被借的一方。
# 這也是為什麼 `SHARED_PATTERN_SOURCE` 那張表只能留複本（它在 hook 的模組層被用到），
# 而**函式**不必：本檔是 import 的一方，借得到就不該再抄。
# 🔴 這段刻意住在檔案最前面（R79 由下方上移）：規則①的量測端現在就是攔截端那支
# 函式，形態表在定義時就要用得到它。
```

## K3 `_rc_after_pipe` docstring（12 行 → 留 5 行）

```text
    """規則①的量測端＝**攔截端那支函式本身**（R79；不再自寫第二份判準）。

    🔴 為何非借不可：上一版是一條扁平正則 `\\|…[^\\n]*\\n?[^\\n]*LASTEXITCODE`，
    它與攔截端在**兩個相反方向**同時失準，而兩個方向都會污染 Q4 的結論：
      · 低報——`\\n?` 把視窗硬綁在「最多跨一個換行」，於是「管線與 rc 之間隔 ≥1 行」
        的多行指令整類看不見；攔截端的污染則是延續到某句真的重設 rc 為止。多行指令
        在本 repo 極常見 ⇒ 系統性低估，而低估的樣子看起來像「變乾淨了」。
      · 高報——它不切語句、不比位置、不認 rc 重設，於是把根 CLAUDE.md 逐字教的正解
        （先接變數 → 立刻讀 rc → 再用管線篩那個變數）算成違規。**方向是「越遵守規則、
        違規率越高」**，用它做的歸因符號相反。
    借過來之後，這個欄位的語意才真的等於「攔截器會擋的那件事」，兩端也不可能再漂移。
    """
```

## K4 R80 兩欄拆分區塊註解（7 行 → 留 2 行）

```text
# ══════════════════════════════════════════════════════════════════════════
# 🔴 R80／S7-01＋S7-09：把「攔截端會擋什麼」與「真的會量到假 rc 幾次」拆成兩欄
# ══════════════════════════════════════════════════════════════════════════
# 判準本體、pwsh 7.6.4 逐形態實測表與紅綠自證語料住 `tools/lib/rc_after_pipe_real.py`
# （R80 收尾包移出：本檔受根層 `guardrail_cli<=750` LOC 分級管，該分級的合法出口逐字
# 寫著「先拆職責／抽共用模組」——不得為了讓它留在原地而調高上限）。下面兩支是**薄殼**，
# 只負責把已載入的 hook 模組餵進去（hook 只能是被借的一方，理由見上方 _HOOK_PATH 段）。
```

## K5 `_POWERSHELL_PATTERNS` 表頭註解（8 行 → 留 2 行）

```text
#: PowerShell 工具面的形態偵測器。鍵即報表欄名。值是 `str -> truthy/falsy` 的**可呼叫**
#: （正則就用它的 `.search`）——規則①借的是攔截端的函式，不是正則，所以型別必須放寬。
#:
#: 🔴 R79 把 `inline-loop` 拆成兩欄，舊欄名**刻意不保留**：實測 latest-5 窗的 30 筆
#: 命中裡有 20 筆是 `| ForEach-Object { $_.Name }` 這種一行投影（慣用管線），與註解
#: 宣稱要抓的「現寫一段沒人驗過的控制流」不是同一種風險。混在同一個分子裡，那個
#: 百分比既不能解讀也不能拿來判斷有沒有變好。舊名沿用新語意才是真正的陷阱（同一個
#: 名字兩種意思），所以直接改名：帳本上的舊 `inline-loop` 數字與新兩欄**不可比較**。
```

## K6a rc-after-pipe 欄註解（3 行 → 留 2 行）

```text
    # 🔴 **對拍錨，不是違規次數**（R80／S7-01）：這一欄逐字等於攔截端會擋的那件事，
    # 存在的理由是讓 `--parity` 與字面／行為一致鎖證明兩端沒漂移。攔截端刻意偏擋，
    # 所以這個數字**不得**被引用成「違規了幾次」——全母體實測 91.4% 是誤報。
```

## K6b rc-after-pipe-real 欄註解（3 行 → 留 2 行）

```text
    # 🔴 **唯一可引用為「量到幾次真風險」的那一欄**（R80／S7-01＋S7-09）：三個條件
    # 同時成立才算（上游原生指令 × 實測會提前結束的管線元素 × 之後才讀 rc）。
    # 逐形態實測依據見上方 `_TRUNCATING_PIPE_RE` 之前的區塊註解。
```

## K6c pipeline-foreach 欄註解（3 行 → 留 2 行）

```text
    # 慣用管線投影（`| ForEach-Object { … }`／`| % { … }`）。與上一欄分開記：它是
    # PowerShell 的日常寫法，不是「現寫的沒驗過的碼」，而且**沒有攔截端**（見
    # `_INTERCEPTED_KEYS`）⇒ 結構上不可能被壓到 0。
```

## K6d naked-cd 欄註解（4 行 → 留 3 行）

```text
    # 鐵律二：PowerShell 工具的 cwd 跨呼叫持續，裸 cd 之後的相對路徑全部會找錯地方。
    # 🔴 R78／SD-01：邊界由 `(?:^|;)` 擴成與 hook 同一組「下一個指令從這裡開始」的
    # 入口（`&&`／`||`／`|`／`{`／`(` 之後）。上一版兩邊邊界不同 ⇒ 同一段違規
    # 「攔得下、卻量不到」，正是這兩份複本要被綁在一起的理由。
```

## K6e bare-bash-sh 欄註解（3 行 → 留 3 行）

```text
    # 裸 bash：Get-Command bash 解析到 system32 的 WSL 佔位版，且反斜線分隔符被吃掉。
    # 共用字面只到動詞為止（見上）＝這裡只認**指令位置**；「跑的是不是 .sh」交給
    # `_CORROBORATORS`，理由與 hook 同一條：路徑常寫在引號裡，遮蔽面上看不到 `.sh`。
```

## K7 `COMMAND_PATTERNS` 註解（5 行 → 留 3 行）

```text
#: `{工具名: {形態: 正則}}`。逐工具是刻意的——見檔頭〈為何計數必須逐工具〉：
#: 這四個形態全部只約束 PowerShell 工具，混進 Bash 的指令會得到 97.7%／100% 的假陽性，
#: 而且那組數字會隨「Bash 工具被擋掉」自己變好看，方向性偏誤比雜訊更糟。
#: `Bash` 的形態集合刻意留空且**不得刪除這個鍵**：它同時是 `SHELL_TOOLS` 的來源，
#: 少了它 `bash_tool_attempts` 的分母（Bash 帶 command 的呼叫數）就沒人數。
```

## K8 `EVIDENCE_RE` 註解（7 行 → 留 3 行）

```text
#: 佐證字樣。🔴 R79 收窄，理由是實測：上一版在本輪那個窗判出率 **0/72**、全史
#: **17/706（2.4%）**，而報表最後一行的那個 `0` 讀起來就是「這一輪沒有失實宣稱」——
#: 正是本檔自己警告的「看起來變乾淨」方向，比紅更危險，因為沒有人會去追一個 0。
#: 逐句追出讓它放行的字樣：`✅` 18 次、裸 `ok`／`OK` 7 次——一個是純裝飾字元、一個是
#: 英文常用詞，兩者零鑑別力（`ok` 甚至會被中文說明裡的英文字命中）。現在只留下
#: 「真的是某次執行的輸出」才會有的形狀；`OK` 保留但**必須自成一行的行首**
#: （＝unittest 終端那個 OK），這樣散文裡的 ok 不再構成佐證。
```

## K9 `DEFAULT_WINDOW` 註解與敏感度表（13 行 → 留 4 行）

```text
#: 宣稱往回看幾個 tool_result。🔴 R79 由 12 改為 3。往回看 12 個再把它們**拼成一坨**
#: 去比對，等於「前面任何一支測試印過 rc=0，之後 12 個回合內的任何宣稱都自動獲得
#: 佐證」——佐證與那句宣稱指的是哪一次執行毫無關聯，條件近乎恆真。
#:
#: 選 3 不是拍腦袋，是對全史 707 句宣稱做過敏感度掃描（新的 `EVIDENCE_RE` 之下）：
#:     window= 1 → 398 判無佐證（56.3%）    window= 6 →  99（14.0%）
#:     window= 2 → 299（42.3%）             window=12 →  34（ 4.8%）
#:     window= 3 → 227（32.1%）
#: 兩端都沒有用：1 會把「連續講兩句、佐證在第一句前面」全部誤判（清單長到沒人看），
#: 12 則回到近乎恆真。3 的量級是「一句宣稱通常指的是它前面那一兩次執行」。
#: 🔴 這個數字是**判準的一部分**，不是常數：報表會把它與分子分母一起印，任何人引用
#: 那個百分比時必須連窗一起引，否則換一個窗就是另一個數字。
#: 誠實劃界：這仍是啟發式，列出的每一筆是**待人工看一眼的線索，不是判決**。
```

## K10 `EXEMPT_RE` 註解（7 行 → 留 4 行）

```text
#: 兩處與攔截器同義的**放行**面。量測器若不跟著放行，同一段指令會「攔截器說沒事、
#: 量測器記一筆違規」——那個差距會直接灌進 Q4 的違規率，而 Q4 是拿來下結論的。
#: （放行不等於消失：豁免另計在 `exempted_calls`，靜默丟掉才是「看起來變乾淨」。）
#: 🔴 這兩個字面**不進 `SHARED_PATTERN_SOURCE`**：那張表是「違規長什麼樣」，
#: 放行條件是另一件事，混進去會讓字面相等鎖的語意變成兩種東西的混合。
#: 它們與 hook 的對應項是否同步，由行為一致鎖（同一批指令兩邊判定必須一致）覆蓋。
#: 🔴 R79：比對面與攔截端一起改成「**只認住在真註解裡**的標記」（見 `_exempt`）。
```

## K11 `_exempt` docstring（5 行 → 留 1 行）

```text
    """行內豁免是否成立——與攔截端同一個判準（同一支遮蔽器、同一個模式）。

    比對的是「註解原樣留、字串照樣遮」那一面：任何在字串裡**引述**這個標記的指令
    （寫文件、寫探針、在訊息裡舉例違規形態）不再一次關掉全部檢查。
    """
```

## K12 `comparison_surfaces` docstring（9 行 → 留 2 行）

```text
    """`形態 key -> 該餵哪一面給它的偵測器`。

    · **結構面**（引號／here-string／註解全遮）給「指令位置」類的形態：`cd`／`bash`
      寫在字串或註解裡都不是指令，計進去就是純雜訊（R78／SD-02：hook 那邊同一批
      形態實測三條規則全誤擋）。
    · **原文**給 `rc-after-pipe`：R79 起這一欄的偵測器就是攔截端那支函式，它自己要
      同時用到結構面與展開面**比位置**（管線在前還是 rc 在前），所以只能拿到原文。
      上一版在這裡只餵展開面、再由本檔自寫的扁平正則判，那正是兩端判定分歧的來源。
    """
```

## K13 `parity_divergences` docstring（10 行 → 留 3 行）

```text
    """攔截端 × 量測端對**同一批真實指令**的判定分歧（`[]`＝沒有分歧）。

    🔴 為何要有這支：R78 宣稱兩端「修之後判定分歧 0 例」，而守那句話的鎖餵的是十來條
    手寫短指令——那組語料裡沒有一條跨三行、沒有一條在管線之後另起一次呼叫，於是它
    **結構上**看不到分歧，永遠是綠的。真實逐字稿上當時的分歧是兩位數。這支讓那個
    宣稱變成可重跑的量測，語料是真的流量而不是自己挑的樣本。

    只比三條「兩端都有」的規則（`_HOOK_RULE_BY_HINT`）：其餘欄位只有量測端，對拍
    無意義。行內豁免兩端一致放行，直接跳過。
    """
```

## K14 `criterion_fingerprint` docstring（7 行 → 留 2 行）

```text
    """借來那支攔截端 hook 的內容雜湊（前 12 碼）。

    🔴 為何必印（R80／S7-08）：本檔規則①的判準**不是自己的**，是 import 進來的
    live hook 函式，而那支檔的判準已經改過 4 次。於是「上一輪量到 X、這一輪量到 Y」
    可能整個來自判準換版，而不是行為變了。指紋讓那件事**看得見**：指紋不同的兩組
    數字不可以放在一起比較，指紋相同才是同一把尺。
    """
```

## K15 `scan_transcript` docstring（6 行 → 留 2 行）

```text
    """單支逐字稿的量測結果（純資料，報表與 rc 由呼叫端決定）。

    `record_since`／`record_until` 是**逐筆**時間切片，見檔頭〈分期〉①：以檔案 mtime
    切片會把跨越分界點的長 session 整支算進後段，本輪實測誤差達兩個數量級。沒有
    時戳的記錄在有切片時**一律排除**（不猜；把來歷不明的記錄算進某一期正是要防的事）。
    """
```

## K16 Bash 嘗試逐筆攤開註解（6 行 → 留 2 行）

```text
    # 🔴 R80／S7-07：Bash 嘗試要**逐筆攤開**，不能只留一個總數。
    # 本輪實測：阻斷落地後全庫只有 7 次 Bash 嘗試、7 次全被擋（攔阻率 100%），
    # 但其中 5 次的 description 逐字是「Verify bash-block hook is live」「Confirm
    # Bash tool is blocked」「Probe hook execution marker」——**是這道鎖自己的探針**。
    # 一個以自己的探針當分子的攔阻率是自我實現的：只要多驗幾次就會更好看，而那與
    # 「有沒有人真的誤用」無關。分子攤開才看得出這件事，所以本欄記的是清單不是計數。
```

## K19 窗可回查性註解（4 行 → 留 2 行）

```text
        # 🔴 窗的可回查性（R79）：帳本記的每一個數字都必須能指回「是哪幾支、什麼時候、
        # 誰在講話」。`--latest N` 是 mtime 排序的浮動窗，而每一支同期跑的 agent 都會
        # 在同一個目錄開一支新逐字稿 ⇒ 同一條指令隔一小時就給不同答案（本輪實測：
        # 同一條交棒書指令三次量到三組數字、rc 由 0 翻 1）。這三個欄位讓那件事**看得見**。
```

## K22 collapsed 前提註解（15 行 → 留 6 行）

```text
        # 逐支崩塌訊號（見檔頭〈為何崩塌判準必須是 per-session〉）：**有記錄**卻
        # 一支帶 command 的 shell 呼叫都抽不到。用 `records` 而不是 `tool_use_total`
        # 當前提，是因為「連 tool_use 都認不出來」正是最徹底的那種格式變更——
        # 拿它當前提會讓最該紅的情形自己把判準關掉。
        # 🔴 逐筆切片下前提要換（R80／S7-08）：切片是使用者自選的子窗，「這一段時間
        # 內這支 session 根本沒跑 shell」是**正常**狀態而不是掃描面崩塌。沿用
        # `records>0` 當前提會讓這個 fail-loud 在分期用法下幾乎必然觸發（本輪實測
        # 73 支裡 14 支中招），而一個永遠在響的警報等於沒有警報——那正是本檔自己
        # 反覆記載的「恆紅的閘門會被整個關掉」。切片時改用「tool_use 認得出來、
        # 卻一條指令都抽不到」＝格式真的變了的那個訊號。
        # 切片下的前提＝「**shell 工具真的被叫過**、卻一條指令都抽不到」，那正是
        # 「欄位改名／格式變更」的長相，也只有它在子窗裡仍然是異常。用「有任何
        # tool_use」當前提還是太寬（只用 Read／Grep／Agent 的窗會照樣中招，實測 2 支）。
        # 誠實劃界：切片下若連工具名都認不出來（`PowerShell` 被改名），本判準看不到；
        # 那個最徹底的失效仍由合計面的 `shell_calls == 0` 與非切片用法兜底。
```

## K24 `collapse_verdict` docstring（6 行 → 留 3 行）

```text
    """`None`＝掃描面健在；回字串＝掃描面崩塌的理由（純函式，供注入自證）。

    三款，由窄到寬：掃不到檔／**某幾支**抽不到 shell 呼叫／整批合計為零。
    第二款是 R78 補上的那一款，也是唯一一款在預設用法下真的打得到的
    （前一版只有第一、三款，而第三款是歷史總量 ⇒ 結構上不可達，見檔頭 SD-03）。
    """
```

## K25a `_print_window_manifest` docstring（13 行 → 留 4 行）

```text
    """🔴 報表**開頭**固定印出「這一次到底量了哪幾支」（R79）。

    為何是必印而不是選項：`--latest N` 的窗由 mtime 排序決定，而每一支同期跑的 agent
    都會在同一個目錄開一支新逐字稿 ⇒ **量測這個動作本身會改變下一次的量測值**。
    本輪實測：同一條交棒書指令在一小時內給出三組數字、rc 由 0 翻成 1，而窗裡最後
    只剩掃描 agent、真正在做事的那支已被擠出去。任何人照著重跑都會拿到與帳本不同的
    數字，然後去找一個不存在的原因。把窗的定義印出來，那件事至少**看得見**。

    誠實劃界：逐字稿裡**沒有**任何欄位能區分「掌舵者的 session」與「派出去的 agent」
    （本輪逐欄實查 `isSidechain`／`entrypoint`／`origin`／`userType`／`promptSource`
    在兩者上取值相同）。所以本函式不做自動分類，只把 `first_prompt` 印出來讓人一眼
    認得；要排除就用 `--exclude` / `--exclude-self`，那是明示而非猜測。
    """
```

## K25b 判準指紋與切片註解（2 行 → 留 1 行）

```text
    # 🔴 判準指紋與逐筆切片同屬「這個數字是用哪一把尺、量哪一段」的定義，必須跟著
    # 數字走（R80／S7-08）：規則①的判準是向 live hook 借的，那支檔改過 4 次。
```

## K26 分子攤開註解（3 行 → 留 2 行）

```text
        # 🔴 逐筆印出（R80／S7-07）：攔阻率的分子若幾乎全是這道鎖自己的探針，
        # 那個 100% 是自我實現的。只有把分子攤開，讀的人才分得出「真的有人誤用」
        # 與「我們自己去驗了幾次它還活著」。分辨的線索是 description。
```

## K27 `select_paths` docstring（16 行 → 留 6 行）

```text
    """把量測窗縮到「本輪那幾支」。**沒有這個，崩塌判準就只能對著歷史總量說話**。

    `since`／`until` 吃 ISO（`2026-08-07` 或 `2026-08-07T00:05:53`），以檔案 mtime 篩；
    `latest`＝只留最近改動的 N 支；`exclude`＝檔名含任一子字串者剔除。四者可疊加。
    窗篩空時**不吞掉**——回空清單讓 `collapse_verdict` 說「量不到」。

    🔴 `until` 存在的理由不是對稱美感：「觀測者上線**前** vs **後**」這種分期比較
    需要一個右界，沒有它就只能靠下游腳本自己切，而下游腳本下一輪不會有人重跑。
    誠實劃界：mtime 是**最後寫入**時間，跨越分界點的長 session 會整支落在後段。

    🔴 `exclude` 存在的理由（R79）：`latest` 是 mtime 浮動窗，而**量測者自己**與同期
    跑的每一支 agent 都在同一個目錄開新逐字稿 ⇒ 派愈多 agent，窗裡就愈全是 agent、
    愈少是掌舵者本人，而問題問的是掌舵者。剔除**必須是明示的**：逐字稿裡沒有任何欄位
    能可靠地區分兩者（本輪逐欄實查），猜錯的代價是把真正在做事的那支丟掉。
    `exclude` 在 `latest` **之前**套用，否則被剔掉的那幾支仍會先把別人擠出窗外。
    """
```

## K29 `project_transcript_dir` docstring（10 行 → 留 3 行）

```text
    """`repo_root` 對應的 Claude Code 逐字稿目錄。

    slug 規則＝把路徑裡每個非英數字元換成 `-`（本機實測：`d:\\CursorProject\\
    AISDCL_Agent` → `d--CursorProject-AISDCL-Agent`）。這是**觀察到的**編碼方式，
    不是官方契約，所以 `--project-dir` 一律可覆寫，而目錄不存在時 fail-loud。

    DEF-200-421：家目錄一律經 `platform_utils.claude_home()` 取得，尊重
    `CLAUDE_CONFIG_DIR`（設了即整個 `~/.claude` 目錄被該目錄取代）——此前本函式
    硬寫 `Path.home() / ".claude"`，對這個官方變數視而不見。
    """
```
