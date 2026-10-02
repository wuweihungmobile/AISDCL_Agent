# CrossPlatform R191 — 掌舵者五問驗證輪（第十三次四方覆核；家族級結構審計＋R190 七列修法回歸＋同輪根因修復）證據檔

> 日期 2026-10-02；平台 macOS（Darwin 25.6.0 arm64）；Claude Code 2.1.287；主控 Fable 5.1，四方（Architect／SA／SD／QA）、Developer-W2／B 兩棒與複審鏡皆 Sonnet 5.5（掌舵者指令：子 agent 一律 Sonnet）。
> 起點 HEAD `933f0b16`（R190 收尾 docs 回填）＝origin/main，工作樹乾淨。掌舵者原話：「沒有收斂繼續收斂，請查根因，別盲目實作！」＋「派出 Architect／SA／SD／QA 四方專家獨立審查，請確認以上都已經修好！」＋五問原文。依 R189〈八〉A 案與 R190〈八〉：R191＝四方驗證輪；審查窗口關閉後才開修復棒（並行派工防互踩檢查表第 3 格）。
> 本檔屬帳本級治理文件（登記於 `tools/lib/governance_docs.py`），承擔完整證據的可讀性義務。

## 〇、一句話結論

五問第十三次驗（Mac，驗證輪）：四個活體探針**連續第 4 輪全綠**（Q1 黑盒 2 探針零阻斷、Q2 主控第 3 個工具呼叫現查（第 2 個被判準④正確擋下）、Q3 三方同瞬差=0、Q4 `--status` installed 且相符）；R190 七列修法在 HEAD **全部重現**（SA 單檔 319／218／9／60／56／123／8 OK，197／457 含修前紅燈對照；QA 雲端 run id 逐一相同）。但家族級審計挖到**家族內新 P2＝1**：DEF-200-460（＝Architect ARCH-01／QA QA-01，Architect 發現、QA 獨立重現並獨立評級 P2）——哨兵 GC 以**呼叫者本地**的逐字稿目錄判**使用者全域**的 launchd 工作是否孤兒，目錄存在但缺檔即 bootout 全機活哨兵（含本窗）；R190 的 455 P0 只擋「目錄不存在」那一扇門，且其 e2e「對照組」把錯形狀釘成預期。另 P3×5（461／462／463 如下；464／465 見〈四〉）：461（新視窗首呼叫撞判準④的**行動點缺口**：簡報只給指令不給安全形態，Windows 孿生＝`cd` 開場撞 PowerShell lint）、462（statusLine 未安裝的提示只進模型 context、**人看不到**＝Q4 在 Windows 持續的成因之一）、463（`mask_inert()` 未登記漏判類別，皆合成形態、真實語料零實例）。**依 R188〈八〉原判準②仍 0／2 未收斂**——本輪 0／2 取決於 460 判 P2（計入）這**一個**裁決：Architect 原文「若主控判它屬 455 拆殘或降 P3，則為 0」、QA 原文「若只認已驗生產觸發才計入則為 P3、本輪 NEW＝0，我不採此口徑（455 本身就是 P2）」；主控採較嚴口徑；若採保守口徑則 R191 記 1／2、R192 零新即 2／2。四方＋主控對 Q5 的結構性根因與替代判準見〈八〉。本輪同輪修 460／461／462（Developer-W2／B 兩棒並行、檔案面除 cbg 測試檔外互斥——W2 的夾具 hunk 在 B 收工後才動、區間不重疊），463 登記檔頭；L1-γ：主控採 Architect 建議**追認**（QA 重現其數字；SA／SD 本輪未覆核 γ）。Windows 真機連續第 5 輪零觸及。

## 一、五問第十三次判定（Mac；驗證輪）

| 問 | R191 判定 | 一句話（主控親測或他包實跑） | 與 R190 的差異 |
|---|---|---|---|
| Q1 新視窗就說被擋 | **活體 PASS；但「首呼叫被擋」那一半在真實主 session 2/2 重演＝行動點缺口（DEF-200-461，P3，本輪修）** | 主控本場：#1 `git status … \| head -20; echo "--- HEAD ---"` 放行（管線後接的不是讀 `$?`）、#2 `--pace … \| head -40; echo "rc=$?"` 被判準④**正確**擋下、#3 起放行。SA 黑盒 2 探針（haiku）：`92c24142`「只回 OK」回 `OK`、`78aea710` Write＋Bash 回 `DONE`（Write 成功 10 bytes）；`Hook SessionStart.*success`=2、`posix_spawn`=0、`ENOENT`=5 良性、`hook_system_message`／`hook_non_blocking_error`／`permission_denials` 皆 0 `[他包回報]`。QA：真「鎖死」來源＝09-08～09-10 SDD-FSM ESCALATION 21 筆，最後 2026-09-10T02:11:44Z 後 22 天零筆 `[他包回報]`。SD：頂層互動 session 10-01 起 5 個，前 5 個 Bash 25 條中壞形態 2 條皆被活擋、3/3 下一呼叫自癒；三個新成因（簡報自陳「Bash 不受影響」卻另有形態守衛、CC 前綴像載具壞掉且一行解法在第 4 行、規則在 CLAUDE.md 第 241 行不在行動點）`[他包回報]`。SA 另計 auto-mode 分類器拒絕 12 筆（皆 tool#14 後的高風險動作）＝Q1 另一個「被擋」來源（非 hook）。SD-04：現行 Q1 探針（haiku、Bash 0～1 次）**沒有鑑別力**，下輪改 PA／PB／PC。 | R190「活體 PASS＋修漏擋」→ R191 把「主控自己第 1 個呼叫被擋」從「正確攔截、非缺陷」改判為**行動點缺口 P3 並修** |
| Q2 不用真實數據 | **PASS（n=1）** | 主控第 3 個工具呼叫＝`--pace`＋`--check`（第 2 個同內容被判準④擋下、重寫為導檔形態）；SA／QA 各自重算 6 個舊 session 首次現查序號 452cab3f=12／718ff654=2／96df659c=1／ba149f52=1／e1a2d13c=1／16692980=31 逐一相同 `[他包回報]`。 | 無變化 |
| Q3 數字與 /context 不符 | **NOT-A-DEFECT（連續第 3 輪差=0）；🔴 但「差=0」只是同一份 API usage 兩個副本互比（QA），對 /context 的真證據是面板對帳 14 筆** | 主控親測 `used 82,140 … 水位 8.2% … harness used=82,140 逐字稿 used=82,140 差=0`；SA 21:35:43 三方 176,860／176,860／176,860、21:52:08 再量相同；QA 250,232 三方相同 `[他包回報]`。面板對帳：QA 獨立重算 2 對（452cab3f `543.7k / 1m (54%)` vs 543,652＝+48；96d7f386 `366.4k` vs 366,397＝+3）；SA 重算 14 筆／13 有前值／12 筆 \|差\|≤48（＝面板 0.1k 解析度）、離群 −6,759（09-08 回合中途打）、10-02 後新增 0 筆 `[他包回報]`。QA 提出「明顯不符」的可能來源 `[假設]`：面板 Free space 已扣 Autocompact buffer（452cab3f：Tokens 54%、Free 42.3%、Buffer 3.3%），人以 `1−Free` 讀會多 3.3 點。 | 母體不變；多一個對掌舵者體感的解釋假設 |
| Q4 Windows 沒有 ctx 行 | **NOT-A-DEFECT（連續第 6 輪）；但「未安裝時人看不到提示」＝DEF-200-462（P3，本輪修）；Windows 仍零觸及** | SA／QA 親跑 `install_statusline.py --status` rc=0 `installed: true`／`matches_current_checkout: true`／`python_basis: repo-venv`；合成 stdin 底列 `ctx 18% 175.2k/1.0m \| Fable 5.1`、`ctx n/a of 1.0m (until next reply) \| Fable 5.1`、`!ctx 90% …`、`ctx ? (feed error)`；`18.0%` 為 DEF-200-416 前舊格式（`statusline_context_feed.py:158` 現 `{used_pct:.0f}%`）`[他包回報]`。未安裝臂逐字（Mac 實跑）`statusLine：未安裝（貼上即安裝；先預覽就在尾端加 --dry-run："<venv python>" "<repo>/tools/install_statusline.py"）`——只走 `additionalContext`；SD 讀 CC 2.1.287 內嵌 JS：`hook_system_message` 渲染成「<hookName> says: <content>」、`additionalContext` 無渲染分支、`systemMessage` 適用 all hooks `[他包回報]`。SD D2(c)：repo 層 statusLine 不建議（schema 只有 shell form、Windows 閃窗方案 B 管不到、首次 clone 127 靜默空白）。 | 由「設計如此（使用者層安裝）」進到「人看不到要裝＝修」 |
| Q5 收斂了嗎 | **依原判準②仍 0／2（家族內新 P2＝1：DEF-200-460）；樞紐＝460 的 P2 裁決（Architect／QA 皆附保守口徑 P3 ⇒ 1／2）** | 四方計數：Architect 1（ARCH-01）、QA 1（QA-01＝ARCH-01）、SA 1（SA-01 可議，QA／SD 皆判 P3，主控採 P3）、SD 0。評估全文與替代判準提案見〈八〉。 | R190「0／2（修復輪不計）」→ R191「0／2（審計輪，新 P2＝1）」 |

## 二、主控親測事實（本場 tool_result 逐字）

- 新視窗 SessionStart：`額度：額度量不到（reason=stale-cache（資料在，但已 22072s > TTL 180s ⇒ 重量一次即可，不是取數壞掉））⇒ cap=2 recommended=2 band=unmeasured binding=- … statusLine：已安裝`；`[SDD-FSM] … current_state: SPEC_DRAFTING`。
- 第 2 個工具呼叫被 PreToolUse hook 擋下（逐字節錄）：`PreToolUse:Bash hook error: [${CLAUDE_PROJECT_DIR}/.venv/Scripts/pythonw.exe … block_destructive_git.py]: 🔴 這條指令的**等待／確認機制自己會靜默壞掉**，已擋下（鐵律六／DEF-200-044）。… 管線尾節是 rc 遮蔽型濾器：… \| head 之後讀 $? …（DEF-200-086）`。
- 第 3 個工具呼叫 `--pace`：`現在可派 2 個 agent（硬上限 cap=4，本視窗已用 0 次）｜band=converge｜最緊的一條＝seven_day 75% 剩 1723 分鐘 … ⇒ cap=4 recommended=2 band=converge binding=seven_day … 來源=cache 量測於=2026-10-02T21:16:34+08:00`、`⚠️ 落款樣本有斷層：最近 5 列間最大間隔 494.8 分鐘（> 6 小時可等視界）`（DEF-200-203 修法第一次在生產出聲）；`--check`：`used 82,140 … window 1,000,000〔harness 回報（status line context_window.context_window_size；model=claude-fable-5-1；釘值 967,000 未採用）〕 水位 8.2% … harness used=82,140 逐字稿 used=82,140 差=0`。
- 派工前每次現查 `--pace`：21:59 `可派 2（cap=4）band=converge`；22:08 `可派 1（cap=2）band=prepare 最緊 five_hour 20% 剩 48 分鐘`；23:01 `可派 2（cap=3）band=converge seven_day 80%`（量測於時間戳各列）。
- 基線：`--unresolved-count` `未結列數＝33／全部 160 列｜warn=86 fail=98`；`--print-guard-lines`（tools/tests 下）`# _GUARD_LINES_REPIN_LOG 新列：("R<n>", 112168, 112168, +0, "<理由>")`、`_REPIN_LOG_FROZEN_PREFIX_LEN = 322`、sha `22765c3a1d2f8e46…`；nightly `nightly_mac_20261002_020001.log` `===== nightly 彙總：PASS=4 FAIL=0 =====`（跑在 R189 樹 5b0ac5c1，早於 R190 修法；R190 修法首次 launchd 真跑＝10-03 02:00，本輪不可驗）。
- peer session：`ListAgents` 1 個 idle；`ps` 認身分＝`.antigravity-ide/extensions/anthropic.claude-code-2.1.286-darwin-arm64/resources/native-binary/claude --output-format stream-`（etime 01-13:01:34）＝IDE 擴充套件自啟行程，非真人視窗 [推論：ListAgents 無 PID，以唯一 idle 行程對應]。
- 主控親讀根因點位：`tools/lib/session_brief.py:71-72` `_VERIFY_HINT` 只含兩條指令、無安全形態（同檔已有 DEF-200-412 的 `_RC2_CLARIFY_WINDOWS` 先例）；`tools/lib/sentinel_lifecycle.py` `gc()` 以 `_transcript_dir()`＝`planner.project_transcript_dir(planner._REPO_ROOT)` 判 `base / f"{sid}.jsonl"` 是否存在、`reap_verdict` ③ `if not transcript_exists: return True, "逐字稿不存在"`；任務書狀態塊本就記錄 `state["transcript"]` 絕對路徑（`session_resume_planner.py:1180／1322／1448`）卻未被 GC 當所有權證明。
- 護欄行數棘輪射程親讀：`guard_lines_in_worktree()`＝`tools/tests/*.py` 非遞迴；登記 `governance_docs.py` 不計入。主軌＝淨額−回歸鎖軌申報（上限 309）；R191 主軌必須 ≤0。

## 三、四方摘要 `[他包回報]`

- **Architect（PARTIAL；新 P≤2＝1）**：A γ：自寫 4096 組方向掃描 γ 收緊 624／相等 3472／放寬 0／加速被壓 0；L1 原文 1422／2674／0／798（R190 文件「36」＝可見加速子集，定義差非矛盾）；400 隨機合法 Policy×4096＝1,638,400 組放寬 0；真落款 134 列（帶 resets_at）：γ>L1 25 列中 **17 列由零煞車力軸造成（L1 會復發 R84 後門煞車）**、762 型 8 列（6.0%）皆被 cap 夾住 ⇒ P3；退 L1 ⇒ `Ran 319 failures=16`（含 helm 16→4、S4-1、S4-3、M1b）；**建議追認 γ**＋三條文件義務；第三方案 γ-C 備而不用。B：197 反向風險不成立（429 連續 Agent#1..#5 rc=0,0,2,2,2、每 TTL 一次；逐字稿撞線時 halt 照接；先 halt 後 429 cap 停 0）；198 出廠無 `cap==max_fanout` 格；203 邊界 21600 不判／21601 判；456 `--print-schtasks-command` 假 launchctl 0 呼叫但仍寫任務書骨架（「零副作用」措辭訂正）；457 明列假設全抓到、漏判為檔頭已登記類＋未登記 `${#…}`／光桿引號執行檔／載具／混淆（P3）。**ARCH-01（P2）**見〈四〉。C Q5 根因與 D 承接裁決見〈八〉。
- **SA（PARTIAL；新 P≤2＝1 可議）**：Q1～Q4 活體見〈一〉；七列單檔 319／218／9／60／56／123／8 OK；197 修前樹（`5a4ce864^`）stale 快取＋429 ⇒ rc=2 `band=halt cap=0` → HEAD rc=0 `source=http-429-unmeasured`、連續第 3 次 Agent rc=2 含 `UNMEASURED_HORIZON_LINE`＋「遙測通道（usage 端點）被限流…與模型額度無關」；456 `--print` 前後 ~/.autosdd／launchctl／TMPDIR／LaunchAgents diff rc=0、無 `--at` 時 rc=1 拒絕；455 隔離 HOME 時「量不到 ≠ 不存在，一律拒絕回收」；457 修前 rc=0 → HEAD rc=2。真實 `autosdd_sentinel_unloads.jsonl` 2 列（14:09 自卸、21:26:40 `bootstrap` 6880f760 caller=`_arm_sentinel`）無測試洩漏。**SA-01**（P2 可議）／SA-02（P3）／SA-03（P4）見〈四〉。訂正主控任務書兩處：SessionStart **不**補量額度（只讀快取，補量在扇出型 PreToolUse 與 PostToolUse）；主控 #1 放行、#2 被擋。
- **SD（PARTIAL；新 P≤2＝0）**：SD-01（=SA-01，P3）三個新成因＋逐字修法草案＋副本原型（test_session_brief 60 OK、r83 218 OK、提案鎖 4 支中 2 支舊紅新綠）；SD-02（=SA-02，P3）CC 內嵌 JS 證據＋最小方案原型 E2E 通過（hook 0 行、atexit 單點鎖 72 測全綠）；SD-03 595 格矩陣：HEAD caught 346／MISS 125／false-block 8，OLD→NEW 24 格修好回歸 0，MISS 十家族 F1～F10 中 F7(①)／F8／F9／F10 未登記、真實語料 5,264 條零實例 ⇒ P3；誤擋 P05×4（PS 反引號跳脫引號內獨立成段 `git stash`）P4；假紅普查 `[transcripts] 母體 5439 筆／去重後 5264 種唯一字面 判準 git: 命中 13 種唯一／13 次 判準 waitform: 命中 70 種唯一／70 次` 全真陽；SD-04 Q1 探針無鑑別力（PA／PB／PC 提案）。`hook_non_blocking_error` 全逐字稿 4,607 筆、最後一天 09-26、09-27 起 0（方案 B 生效的正面證據）；Mac 有 pwsh 7.6.3（主控任務書寫「Mac 無 pwsh」有誤）。D4 vR190 29 行 lint 0 命中、負向 3 條各 1、SA-01 的 PowerShell 形態 `\| Select-Object -First 40; "rc=$LASTEXITCODE"` hits=1 被擋 ⇒ Windows 同坑；D5 vR190 仍有效不升版，D1／D2 落地後加 [12][13]；一鍵驗收值得但 R192 之後、不新寫 .ps1（`tools/session_gate_acceptance.py` 最小方案）。
- **QA（PARTIAL；新 P≤2＝1）**：T1 閘門全綠（crossref rc=0、unresolved 33/160、handoff rc=0、archive rc=0、`check_loc_budget` violations=[]、`sync_onboarding_baselines.py --check-snapshot` rc=0、`ruff check tools/` All checks passed、`--print-guard-lines` +0）；LOC 餘裕 session_brief 231/400、sentinel_lifecycle 355/400、platform_utils 96/400、block_destructive_git 708/750、**context_budget_guard raw 1087/1089（餘 2）**；T2 雲端 32e9f395 四支 success run id 逐一相同、5a4ce864 root-infra／windows failure 相符、933f0b16 push 事件只 root-infra-ci success、nightly-full 為 compat-ci 內 job 最近 09-28（**尚未跑過 R189／R190 樹**，下次 10-05）；T3 Developer-F 922／806 以多重集合比對 **922／922 逐字命中**；a5 重現 gamma 0／l1 16／gamma_c 6（解讀：16 多為 R190 為 γ 寫的鎖）；T4 ARCH-01 (a)(b)(c) 逐字吻合、生產可達性逐項標已驗／假設、時序 131／143 ms vs GC 73–77 ms；**QA-04 帳本時鐘陷阱證實**（情境欄含 `R191`（含檔名）⇒ `current_round` 100→191 ⇒ 六列舊 backlog 孤兒；零輪號新列安全）；QA-05 判準②數學與 Architect 逐位一致並補欠散布／Garwood 區間（E 4.5～80 輪）。

- **Developer-W2（DONE）**：見〈四〉460 列；新鎖 69 行；紅→綠：新鎖對 pristine HEAD `Ran 124 … FAILED (failures=4)`＋非 darwin 分支 `Ran 2 … FAILED (failures=2)` → 修後 `Ran 124 OK`；替身 launchctl `--apply --keep probe`：HEAD bootout 2 次 → 修後 0 次；cbg `_apply_once` 夾具同步後 `Ran 789 OK (skipped=11)`；E501 存量 147→139 折行回 HEAD。
- **Developer-B（DONE）**：見〈四〉461／462 列；7 檔、新鎖 119 行；紅：`Ran 6 … FAILED (errors=6)`／`Ran 7 … FAILED (failures=1)`／`Ran 3 … FAILED (errors=3)` → 綠 `Ran 66 OK`／`Ran 219 OK`／cbg `Ran 789 OK`（只含 B 檔的 clone；真樹在 W2 夾具同步後 789 OK）；`emit_to_model` 無訊息輸出 sha256 與 HEAD 相同；端到端未安裝 startup `top_level_keys=['hookSpecificOutput','systemMessage']`、裝進隔離 HOME 後只有 `hookSpecificOutput`；突變 10/10 轉紅。設計決策：採 `emit_to_model(system_message=)`＋guard +1 行而非 SD 的 `emit_to_user` 進 session_brief（後者在無 statusLine 機器會污染單元測試全域緩衝）。
- **複審鏡 A（APPROVE；P≤2 新問題 0）**：十項全 CONFIRMED；自己重做紅→綠（git archive 鏡像，不用 stash）、新舊 `gc()` 對 22 支合成哨兵的判決對照（HEAD 收 20／NEW 收 9，真孤兒 7 格 HEAD 與 NEW 皆收、waiting／量不到皆留）、W2 鎖突變 4 種皆紅、CC 2.1.287 二進位 schema 實查（`source` 五值 startup／resume／clear／compact／fork；`systemMessage` all hooks）、根層全套 `發現 5058 個測試` 恰 5 紅皆收尾義務（護欄行數 3＋淨額 2）。非阻擋訂正：P3-a `gc()` 殭屍前提、P3-c 任務書三個家無鎖、P3-d statusLine 句無靜音鈕、P3-e 檔頭「pwsh -Command」不精確、P3-f 既有測試衛生（三處 `addCleanup(os.environ.pop, TRACE_DIR_ENV)` 拆圍籬 ⇒ 真實 traces 漏 3 列 `sid-f1`，含鏡 A 自己的 2 列）。

- **複審鏡 B（CONDITIONAL；文件訂正 21 條，見〈六〉）**：零信任對帳主控全部文件；嚴重度裁決判非自利；判準②′ 提案補規格與成本；γ 措辭訂正；詳〈六〉末條與〈八〉。

## 四、新發現、嚴重度裁決與修法

| DEF | P（四方各判 → 主控裁決） | 來源 | 根因（有證據） | 修法（Developer；主控親驗見〈六〉） |
|---|---|---|---|---|
| **DEF-200-460**（新立；＝ARCH-01／QA-01） | Architect 發現 P2、QA 獨立重現並獨立評級 P2 → **P2，計入** | Architect 替身 launchctl 重現 (d)；QA 三形狀 (a)(b)(c) 獨立重現、時序量測 | `sentinel_lifecycle.gc()` 的證據＝**呼叫者**的 `platform_utils.claude_home()/projects/<slug>/<sid>.jsonl`（`claude_home()` 吃 `CLAUDE_CONFIG_DIR` 否則 `Path.home()/.claude`），目標＝**使用者全域**的 launchd／schtasks 工作；目錄存在但缺檔 ⇒ `reap_verdict` ③「逐字稿不存在 ⇒ 收」（③ 無閒置門檻、不讀任務書 state：`plan_state(plan) if exists else None`）⇒ `--apply` bootout 全機活哨兵（含本窗）。自動路徑 `context_budget_guard.py:794 arm_sentinel → :804 spawn_sentinel_gc → :821 [python, sentinel_lifecycle.py, "--apply", "--keep", sid]` 每次 SessionStart 無條件起。R190 P0 只擋「目錄不存在 ⇒ 量不到」；R190 e2e「對照組：目錄在、兩支皆孤兒 ⇒ 必須 bootout」把錯形狀釘成預期。可達：[已驗] 隔離 HOME＋目錄已存在＋未設 `AUTOSDD_SENTINEL_OFF`；[讀碼] `CLAUDE_CONFIG_DIR` 走同一路徑（`claude_home()`）；[有先例] 10-01 452cab3f 事故（subagent 隔離 HOME 跑模組迴圈第 2 輪起目錄已存在）；[假設] 多 profile／第二棵 checkout／worktree；[已驗·時序] 新隔離 HOME 的 `claude -p`：hook 完成→逐字稿 birth 相隔 131／143 ms，GC dry-run 73–77 ms（今日靠 60–70 ms 餘裕沒出事）。 | **Developer-W2**（主控裁決原則：**證據必須和目標一樣全域**＝所有權證明——每支哨兵的任務書狀態塊本就記錄逐字稿絕對路徑 `state["transcript"]`，GC 改以它判存在／閒置／state；任務書缺席／無欄 ⇒ `None`＝量不到 ⇒ ② 絕不收（不留殭屍：任務書缺席的哨兵醒來 `parse_relay()` 回 None ⇒ `_abort_and_unregister`，DEF-200-456 修法已釘）；記錄路徑真不存在 ⇒ ③ 收但 state 在 `REAPABLE_WHEN_IDLE` 外仍不收；`--keep`／`_newest_session()` 保護與 dry-run 預設原樣）。結果：新鎖 69 行；對 pristine HEAD `Ran 124 … FAILED (failures=4)`＋非 darwin 分支 `FAILED (failures=2)` → `Ran 124 OK`；替身 launchctl `--apply --keep probe` HEAD bootout 2 次→0 次；cbg `_apply_once` 夾具同步後 `Ran 789 OK`。行為差（鏡 A P3-b）：任務書缺席的孤兒由「GC 在下個 SessionStart 靜默收」變「該 job 下次 tick（≤15 分）自己 abort 並走 escalation.alert」——無殭屍但不再靜默。 |
| **DEF-200-461**（新立；＝SA-01／SD-01／QA-02） | SA P2（可議）、QA P3、SD P3 → **P3，不計入**（傷害類別＝守衛**正確**攔截一條模型自寫的壞形態、一次呼叫內恢復、無錯誤決策、無漏攔；對照 P2 先例 451／457 皆為判斷錯誤，P3 先例 452／453／454 皆為訊息誤導；主控本窗親歷：#2 被擋、#3 恢復，耗時 11 秒） | SA 逐字稿普查；SD 前 5 個 Bash 普查（25 條中壞形態 2 條皆活擋、3/3 自癒、9ea68d33 #40 再犯）；QA 獨立重讀 | **行動點缺口**：(1) `session_brief.py:71-72` `_VERIFY_HINT` 只給 `--check`／`--pace` 兩條指令、沒給安全形態，模型反射加 `2>&1 \| head -40; echo "rc=$?"`；(2) 簡報 `_RC2_CLARIFY` 斷言「Bash…不受影響」卻沒說 Bash 另有指令形態守衛（鐵律五／六）＝自相矛盾（同型 DEF-200-412 在 Windows 的處理）；(3) 擋下時第一行是 CC 前綴 `PreToolUse:Bash hook error: [${CLAUDE_PROJECT_DIR}/.venv/Scripts/pythonw.exe …]`（Mac 上像 Windows 載具壞掉），一行解法在第 4 行；(4) 規則住根 CLAUDE.md 第 241 行（51,471 bytes／433 行）不在行動點；(5) Windows 孿生：`_VERIFY_HINT` 平台中性，而 `\| Select-Object -First 40; "rc=$LASTEXITCODE"` 與行首裸 `cd <repo>` 皆被 `lint_powershell_command.py` 擋（SD D4 實測 hits=1）。 | **Developer-B**：`verify_hint(windows)` 平台感知（POSIX：「輸出很短，直接跑；要 rc 先導檔再讀，別在 `\| head`／`\| tail` 之後讀 rc」；Windows：「不要用 `cd` 開場（絕對路徑或 `Push-Location …; Pop-Location` 同呼叫成對）；要 rc 先存變數或導檔，別在管線之後讀 `$LASTEXITCODE`」）；`_RC2_CLARIFY` 兩平台各補一句「壞寫法的 Bash／PowerShell 另由指令形態守衛／lint 擋下，訊息附一行解法，照改重跑即可」；hook ④ 單獨命中時 `_RCPIPE_LEAD` 一行解法**置前**、原總綱整段後移（混合命中沿用總綱）；判準④邏輯零改動。結果：7 檔、新鎖 119 行；紅 `Ran 6 … FAILED (errors=6)`／`Ran 7 … FAILED (failures=1)` → 綠 `Ran 66 OK`／`Ran 219 OK`。殘餘：`quota_messages.py` 姊妹句 `HALT_CONVERGENT_CLARIFICATION`（:310）與 :443 仍寫「Bash…不受影響」未動（登記 461 列，R192）；效果待量（下輪 SD-04 基線）。 |
| **DEF-200-462**（新立；＝SA-02／SD-02／QA-03） | SA P3、QA P3（Windows `--status` 若 `installed:false` 則升 P2）、SD P3 → **P3，不計入；但直接治 Q4 的持續成因，本輪修** | SA S4 端到端；SD 讀 CC 2.1.287 內嵌 JS；QA grep | 未安裝提示（`session_brief.py:289`）只經 `platform_utils.emit_to_model` 的 `hookSpecificOutput.additionalContext` 進模型 context；CC TUI 對 `additionalContext` **無渲染分支**、對 `hook_system_message` 渲染成「<hookName> says: <content>」；`systemMessage` 適用 all hooks、不進模型、上限 4000 字元／20 行；`.claude/hooks`／`tools/lib` 零 `systemMessage`（AutoClaude `check_lang.py` Stop hook 有、逐字稿留 3 筆結構化附件＝CC 支援證據）。Windows 使用者沒跑安裝器時，沒有任何**人**看得到的提示 ⇒ Q4 連續多輪重問。 | **Developer-B**：`platform_utils.emit_to_model(event, msg, system_message=None)`＋`_USER_MSGS`，`flush_to_model` 併頂層 `systemMessage`（單一 JSON；atexit 登記恰一處；無訊息時輸出位元組與 HEAD 相同，sha256 對照）；`session_brief.statusline_system_message()` 在未安裝／已安裝但不符且 `source != "compact"` 時回一句人看得到的話＋可貼安裝指令（startup／resume／clear／fork 出聲、compact 靜音；B 採任務書 C／D 而非 SD 的 `emit_to_user` 進 session_brief——後者在無 statusLine 機器會污染單元測試全域緩衝）；`context_budget_guard.py` +1 行（raw 1087→1088 ≤1089）。結果：紅 `Ran 3 … FAILED (errors=3)` → 綠；端到端未安裝臂 `top_level_keys=['hookSpecificOutput','systemMessage']`、裝進隔離 HOME 後只有 `hookSpecificOutput`。TUI 呈現與「Windows 實際未安裝」前提皆未驗 ⇒ 是否為 Q4 成因待 [13]。 |
| **DEF-200-464**（新立；鏡 A P3-f） | 鏡 A P3 → **P3，不計入（既有測試衛生債、非本輪 diff）** | 鏡 A 實證：隔離 HOME＋`AUTOSDD_TRACE_DIR` 下跑 cbg 全模組仍把 `sid-f1` 列寫進隔離 HOME 的 `.autosdd/traces`；真實檔 3 列（B 的 clone 全模組 1 列、鏡 A 鏡像全模組 2 列） | cbg :7296／:7455／:8255 `self.addCleanup(os.environ.pop, endurance_env.TRACE_DIR_ENV, None)` 把外部設的圍籬變數**吃掉而非還原** ⇒ 其後 `RunResumeWritesHandbackPathIntoStateTest` 走 no_progress 路徑時寫進 HOME 預設目錄；與 DEF-200-455 同族（測試拆自己的圍籬）。 | 主控：真實 `autosdd_unattended_outcome.jsonl`（3 列皆 `sid-f1`）與 `.cursor` 一起刪除復原（鏡 A 已備份原文）；修法承接 R192（三處改還原原值＋圍籬鎖補「pop 不得取代 restore」）。 |
| **DEF-200-465**（新立；鏡 A P3-c） | 鏡 A P3 → **P3，不計入（保守側；「同一事實兩出口」型）** | 鏡 A 讀碼 | 任務書位置三個家：GC 認 `tempfile.gettempdir()/autosdd_resume_plan_<sid>.md`、hook 武裝端同目錄（同函式、detached 子行程繼承）、planner 手動 `--arm-sentinel` 預設 `endurance_env.plan_dir()`（~/.autosdd/plans）⇒ 手動哨兵 GC 恆量不到（不收，安全）；日後 hook 改家 GC 會靜默變永不收。 | 承接 R192：跨檔鎖「武裝端目錄＝GC 預設目錄」。 |
| **DEF-200-466**（新立；＝ARCH-05） | Architect P3 → **P3，不計入** | Architect B1 沙箱實跑（b1b／b1c） | `quota_stability.stabilize` 量不到時回前值 ⇒ 舊 halt 的 cap=0 可在遙測持續缺口下跨視窗保留（PRD §8 列 6「≥1 禁止靜默鎖死」長尾）；首則降級訊息由 `degraded_posture()` 印「硬上限收到 2」而 stabilize 後實際 cap 可為 0。本機歷史「取數失敗」真失敗 0 筆。 | 承接 R192：持久 cap 加年齡上限；首則訊息改印 stabilize 後的值。 |
| **DEF-200-463**（新立；＝ARCH-02／SD-03） | Architect P3、SD P3／P4、QA 同意 P3 → **P3，不計入；檔頭登記，不另開修復** | Architect 差分模糊 3062 指令（bash 3.2＋zsh）；SD 595 格矩陣（＋pwsh 7.6.3、拋棄式 git repo 狀態 oracle）；QA 餵真 hook 抽驗屬實 | `mask_inert()` 未登記漏判：`${#…}` 的 `#` 被當註解吃掉同行尾巴、引號包住的光桿執行檔 `"git" stash`／`& 'git' stash`、載具 `iex`／`cmd /c "…"`／`Start-Process`／`pwsh -Command`、`-c`／`eval` operand 內 `nohup … &`（判準①看不到）、`-c` operand `\"` 跳脫與 `'"'"'` 拼接、`bash <<< 'git stash'`、`trap 'git stash' EXIT`；誤擋 P05：PS 反引號跳脫引號內獨立成段的 `git stash`。真實語料 5,264 條唯一指令：`-c`／`eval` live operand 13 個零含漏判、`${#` 零筆 ⇒ 合成形態。457 修法本身零回歸（OLD→NEW 24 格 MISS→caught、回歸 0、真實前綴 1 條舊版失同步新版接住）。 | **Developer-B**（順手）：hook 檔頭〈誠實劃界〉逐類登記；建議（R192）：Architect `b5_fuzz_leaks.py`／SD `d3/matrix.py` 類「對真 shell 的絕對漏判」模糊進 nightly 棘輪（已知漏判類別只准縮）。 |

**其餘不立列（主控裁決）**：ARCH-03（762 型殘餘＝DEF-200-199 partial 拆殘，P3，寫進 199 狀態欄）；ARCH-04（γ 非加速臂把零煞車力軸 ×0.5 算進逐軸 min：4096 格 6 格、落款 1 列，方向偏緊、只影響諮詢值，P4）；ARCH-05 改立列 **DEF-200-466**（P3，open，R192；見表）；197 反向風險「不成立」的限制（Architect 自陳）：落款只收成功讀數、不能證明耗盡時從不 429，P4：Retry-After 只顯示無退避、「這與模型額度無關」是無條件斷言；198：ENV 無上界可造出 `cap==max_fanout`（3498 格，出廠 0 格）；203：僅 2 列時訊息仍寫「最近 5 列」（P4）；B3：人工／模型在 shell 敲 `launchctl bootout` 無任何 hook 攔＝455 型「無主卸載」仍開著的一扇門（P4，記名）；SA-03（`--print-schtasks-command` Mac 標頭措辭與 launchd 路徑不符，P4 文件債）；SD-04（Q1 探針無鑑別力＝流程，寫進〈八〉下輪義務）；QA-04（帳本時鐘陷阱＝操作警告，寫進〈八〉機械義務）。

**複審鏡 A 非阻擋項的主控裁決**：P3-e 檔頭已訂正為「`pwsh -Command` 只漏 operand 內再包 `iex`／`-EncodedCommand`」；P3-a `gc()` docstring 補前提「該 job 自己醒得來」、`_transcript_dir` 交叉引用同步；P3-f 漏出的 3 列已刪並立 DEF-200-464；P3-c 立 DEF-200-465；**resume 維持出聲**（resume／clear／fork 都是人在看的新畫面，未安裝就該被告知；只有 compact 靜音）；statusLine 一句**無靜音鈕＝已知取捨**（自訂 statusLine 的使用者會在每個非 compact SessionStart 被提示；若困擾，R192 加 `CLAUDE_CODE_ENTRYPOINT`／`CLAUDE_CODE_SESSION_ATTENDED` 判準），記入 462 列。

**L1-γ（DEF-200-199）＝主控採 Architect 建議追認 γ**（QA 重現其數字並註明 16 紅多為 R190 為 γ 寫的鎖；SA 僅間接觀察；SD 未覆核——**不是四方確認**）（主控代掌舵者決；否決窗口＝R192 開場一句話）：Architect 真落款 134 列實證 L1 原文與 γ 的 25 列差異中 17 列來自零煞車力軸（L1 會讓 R84／SA-01 已治好的後門煞車在 rec 通道復發、`test_a_toothless_null_axis_no_longer_vetoes_acceleration` 在 L1 下 `4 != 16`）；退 L1 ⇒ `Ran 319 failures=16`（QA 重現；QA 註：16 多為 R190 為 γ 寫的鎖，是「鎖多緊」不是獨立證據——主控採 Architect 真落款那條為決定性證據）；γ 硬安全性質（零放寬、水位單調、rec≤cap）在出廠＋400 隨機合法 Policy×4096 成立；762 型殘餘實測頻率 4.5～6.0%、皆被 cap 夾住 ⇒ P3 校準。三條文件義務（Architect (i)(ii)(iii)）：施工圖 §6.1 補「加速臂為同軸聚合與加軸單調的設計內例外、代價 203／4096」；199 狀態欄寫入 762 實測頻率與今日觸發（5h 窗最後 30 分 γ 顯示 cap=4 rec=4，L1／γ-C 為 2）；R190 證據檔「加速被壓 36」註明＝可見加速子集（測試定義下 L1 為 798）——本輪落地 (iii)（R190 證據檔檔尾）與 (ii) 的頻率半邊（帳本 199 列）、今日觸發描述只在本節；(i) 與 γ-C（備而不用）承接 R192。

## 五、誠實劃界與未驗

- **Windows 真機連續第 5 輪零觸及**（R187～R191）：Q4 的 Windows 結論仍是讀碼＋前輪證據；本輪 460／461／462 修法在 Windows 的呈現（pythonw 下 systemMessage、`verify_hint(windows=True)` 字面、GC 所有權證明對 schtasks 工作）皆未驗；SD D5 判 vR190 清單仍有效、修法落地後加 [12][13]（見〈八〉）。QA：Q1 的 FSM 狀態檔 untracked＋git-ignored、每機一份，Mac 的 PASS 不能外推 Windows——Windows 診斷一句：跑 `--check` 看末行 `SDD FSM：current_state=…`。
- **Q3 的「差=0」不是對 /context 的獨立證據**（QA）：三方皆源自同一份 API usage；真證據是面板對帳 14 筆（12 筆 ≤48 tokens、離群 1 筆回合中途打、本輪新增 0 筆）。`/context` 在 subagent 內叫不起來；QA 的「人以 1−Free 讀會多 3.3 點」是**假設**，未見掌舵者原始數字。
- **探針環境≠使用者新終端**（SA）：`claude -p` 探針繼承 `CLAUDECODE=1`／`CLAUDE_CODE_CHILD_SESSION=1`，auto mode 下 `--allowedTools Bash` 被忽略、Bash 由分類器放行。
- **Q1 活體探針鑑別力不足**（SD-04）：兩探針 Bash 呼叫 0／1 次、模型 haiku；真實習慣者是 Fable／Sonnet 且阻斷發生在儀式化開場。R188 規則 2 的「Q1 新視窗黑盒零阻斷」本輪仍記 PASS，但其統計力偏低——下輪 SA 改 PA／PB／PC 各 ≥5 次並先量基線。
- **SessionStart 的 `systemMessage` 在 TUI 的實際呈現未驗**（只有內嵌 JS 讀碼＋Stop 事件活體；探針名額已用完）；首次人眼確認＝Windows 清單 [13]。
- **主控任務書兩處錯誤由 SA 訂正**：(i)「SessionStart hook 會自行補量額度一次」不成立（只讀快取；補量在扇出型 PreToolUse 與各工具 PostToolUse，每 TTL≤1 次）；(ii)「主控 #1 被擋」差一格（#1 放行、#2 被擋）。本檔〈二〉已照實寫。
- **nightly**：10-02 02:00 跑在 R189 樹（`sha=5b0ac5c1`），R190／R191 修法首次 launchd 真跑＝10-03 02:00；GitHub nightly-full（compat-ci 內 job）最近 09-28、下次 10-05，**尚未跑過 R189／R190 樹**。
- **`[他包回報]` 未親跑**：QA 的 922／922 多重集合比對、SD 595 格矩陣、Architect 134 列落款重放與 1,638,400 組掃描、SA 兩探針；主控親跑範圍＝〈二〉〈六〉。
- **DEF-200-199 仍 partial**；ARCH-04／ARCH-05／SA-03 不立列（理由見〈四〉）。
- **副作用自陳**：SA 兩探針留下 2 份逐字稿（`92c24142`／`78aea710`，依鐵律 7 不刪；累計 R189 5＋R190 3＋R191 2＝10 份，普查母體請排除）、`~/.autosdd/traces/autosdd_quota_stability_haiku.json` 新檔、TMPDIR boot log；SD 沙盒事故 1 次（PATH 替身 git 被 `bash -lc` path_helper 繞過、真 git 清掉拋棄式 repo 的符號連結，真 repo 零影響；作廢改狀態型 oracle）；Architect／QA／SD 的隔離 HOME 與舊樹複本留在 scratchpad 未清（session 結束自消）。各角色真端點呼叫皆 0。
- **CC 契約由二進位字串佐證、非官方文件**（鏡 A 實查 CC 2.1.287：`source:B(["startup","resume","clear","compact","fork"])`、`systemMessage … "Warning message shown to the user"`）；SessionStart `systemMessage` 的 TUI 畫面未截圖。
- **鏡 A 未重做 Developer-B 的 10 條突變**，改以 HEAD 對照紅綠＋位元組對照（五種空值 sha 皆同）＋AST 比對交叉；W2 鎖突變 4 種鏡 A 親做皆紅。
- **鏡 A 自陳副作用**：鏡像全模組執行向真實 `~/.autosdd/traces/autosdd_unattended_outcome.jsonl` 漏 2 列（＝DEF-200-464 的活體重演；主控已連 `.cursor` 一起刪除復原）；root runner 的 `.last_failure_*` gitignored 檔已備份後刪。
- **Developer 側自陳**：B 以 Bash 內 Python 精確取代修改 `_GOV_EXACT` 保護面的 `platform_utils.py` 與兩支 hook（有人值守允許、無守衛擋）；B 新增測試毛額 123 行略超任務書 120（淨 119）；W2 原則 6 的 stderr 出聲未做、記錄路徑 `stat` 拋 OSError 時 GC 中止（沿舊行為）；鏡 A P4：缺 `state` 鍵得字串 "None" 使 `reap_verdict` 的 `state is None` 分支經 `gc()` 不可達。
- **偏離鐵律自陳**：SA 5 段、QA 3 次用系統 python3 讀 JSON（無 repo import）；Architect／SA／QA／Developer-B 各撞判準④ 1 次、鏡 A 2 次、鏡 B 1 次，SD／W2 0 次（皆正確攔截、立即改正；鏡 B 自陳任務書明寫仍撞＝「規則在 context ≠ 行動點」的 n=1 旁證）。

## 六、收尾親驗（主控親跑；本場 tool_result 逐字；全套與 push 見〈七〉）

- **Developer-B 交件後親驗**：`session_brief.verify_hint(windows=False)` ⇒ `查證指令（輸出很短，直接跑；要 rc 先導檔再讀，別在 \`| head\`／\`| tail\` 之後讀 rc）：context 現查 …；額度現查 …`；`verify_hint(windows=True)` ⇒ `…不要用 \`cd\` 開場（用絕對路徑或 \`Push-Location …; …; Pop-Location\` 同呼叫成對）；要 rc 先存變數或導檔，別在管線之後讀 \`$LASTEXITCODE\`…`；`rc2_clarify(windows=False)` 尾句 `（壞寫法的 Bash 另由指令形態守衛擋下，stderr 附一行解法，照改重跑即可。）`、`rc2_clarify(windows=True)` 尾句 `…壞寫法的 PowerShell 指令會被 lint 擋下，訊息附出口，照改重跑即可）`。hook stdin 餵 `python x --pace 2>&1 | head -40; echo "rc=$?"` ⇒ `hook rc=2`，stderr 首行 `🔴 已擋下：\`… | head\`／\`… | tail\` 之後讀 \`$?\`，讀到的是 head／tail 的 rc。正解：\`cmd > /tmp/o.log 2>&1; echo rc=$?; tail -n 20 /tmp/o.log\`（輸出很短就直接跑，別接管線；鐵律六／\`DEF-200-086\`）`，第二行起為原總綱。
- **Developer-W2 交件後親驗（全部 dry-run，不帶 `--apply`）**：(a) 真 HOME `sentinel_lifecycle.py` ⇒ `✅ 留 AutoSDD_Sentinel_6880f760-…／protected（指名保留或逐字稿仍在寫）`、`✅ 留 AutoSDD_Sentinel_9ea68d33-…`；(b) `HOME=<沙箱>`＋既存空的 `.claude/projects/-Users-wuweihong-Antigravity-AISDCL-Agent/` ⇒ **兩支皆 `✅ 留`**（修前 Architect／QA 同形狀為「🗑 收／逐字稿不存在」）；(c) 沙箱 HOME 無目錄 ⇒ 兩支皆 `✅ 留`；每步後 `launchctl list | grep -c AutoSDD_Sentinel_` ＝ `2`。
- **帳本三閘門（親跑）**：`check_defect_log_crossref.py` 無逃生口 rc=1 且**只剩**一道 `淨額棘輪違反：本輪新增未結 4 筆 > 結案 0 筆 … 新增：DEF-200-463／464／465／466`（驗證輪＝發現輪，依該判準自述的出口②以 `AUTOSDD_NET_RATCHET_OFF=1` 單次放行並在 commit 訊息寫明理由）；`AUTOSDD_NET_RATCHET_OFF=1` 單次 rc=0 `✅ 缺陷帳本跨文件狀態一致：帳本 164 筆有效狀態紀錄、19 份掃描目標皆無矛盾 … 具名治理文件 143 份皆已登記且未逾體積上限`；`--unresolved-count` `未結列數＝34／全部 164 列`（33→34：460／461／462 新立即結、463 新立 open）；`check_handoff_carriers.py` rc=0 `✅ 每一筆前瞻延後宣稱都有帳本承接載體`（新證據檔以 `git add -N` 納入 tracked 面後才跑——未 tracked 會假綠）；`archive_defect_log.py --check` rc=0 `✅ 帳本保全稽核通過（70 檔／1575 個 ID（464／465 立列後）…）`。過程中被三道格式鎖各擋一次並照改：狀態欄不得出現合法狀態詞的連字號變體（`wontfix-by-design`）、既有列不得改長（六列承接列壓回 ≤ HEAD 位元組：199 662→552、242 700→700、193 636→624、246 694→691、458 478→470、459 620→620）、新列 ≤700 bytes（460～466＝531／553／618／505／633／597／見下；462 含鏡 A 補句後）。
- **文件治理測試**：`test_doc_loc_baseline_freshness_r60` rc=0（含輪號鎖 `TestR71CodeRoundLabelsNeverExceedLedgerCurrentRound` 與治理文件登記面；證據檔已登記 `tools/lib/governance_docs.py:575`）。
- **鏡 A 訂正套用後親驗**：`ruff check .claude/hooks/block_destructive_git.py tools/lib/sentinel_lifecycle.py` ⇒ `All checks passed!` rc=0；真實 `autosdd_unattended_outcome.jsonl` `grep -c sid-f1`＝3 → 連 `.cursor` 刪除後 `ls | grep -c unattended_outcome`＝0；帳本新立 464／465 後 `AUTOSDD_NET_RATCHET_OFF=1` 單次 crossref rc=0、`--unresolved-count` `未結列數＝36／全部 166 列`、`check_handoff_carriers.py` rc=0。
- **護欄行數棘輪重釘（主控親手，結構編修→print→填數→print→填 sha 一次收斂）**：`--print-guard-lines` 改前 `淨額 112168→112331 (+163)`、`逐檔漂移 4 支`（r83 +9／cbg +61／mac_endurance +42／session_brief +51）；追加重釘列、回歸鎖軌同輪列、接鏈列後 `淨額 112168→112344 (+176)`，填數後 `112344→112344 (+0)`，sha `e5dd2c337e82…` 填入後再 print 仍 `+0` 且 sha 不變；`_REPIN_LOG_FROZEN_PREFIX_LEN` 321→322、接鏈 `22765c3a1d2f→e5dd2c337e82`（載體 DEF-200-460）；回歸鎖軌申報 176（全額 ≤309，R188 先例）⇒ **主軌 0 ≤ 0（款(11) 連續上升歸零）**；文件側站點 `<!-- guard-total:R191 -->` 寫入 `AutoSDD_improving_112.md` 與 `CrossPlatform_R145_Scan_Findings.md`〈附記（R191）〉兩份相異檔；`test_adr_xplat001_c1c2_lock` 單模組 `OK`、`[Scan-H triplet] UEP=5 AC=47 GLC_FILES=88 GLC_LINES=112344`。
- **MIN_TESTS 重釘**：`5046 → 5058`（全套 discovery 實印 `發現 5058 個測試`）；前兩次重釘（4697→4876、4876→5046）的原文補登進 `CrossPlatform_Guard_Line_History_MinTests.md`（沿革缺口追溯）；`sync_onboarding_baselines.py --write` 回填表① `[rootunit-baseline-live:] → {'tests': 5058}`、`--check` rc=0；`--check-snapshot` rc=0（表② 四棵指紋樹未動，不需乾淨 venv 回填）。
- **根層全套（主控親跑，背景阻塞）**：第一次 `REAL_RC=1` 9 紅＝ONBOARDING 表① stale 6 支（三個平台 meta-test 包同一個 `rootunit-baseline-live 5046≠5058`）＋`TestR71CodeRoundLabelsNeverExceedLedgerCurrentRound`（主控在 hook 檔頭寫了「R191 鏡 A 實測」⇒ 改「複審鏡實測」）＋淨額棘輪 2 支；修後第二次 `REAL_RC=1` **恰 2 紅**＝`test_check_defect_log_crossref.TestEarlyExitAnnouncesUnrunChecks.test_the_real_gate_still_reaches_the_late_checks`／`TestMain.test_main_against_real_repo_is_clean`（皆為「淨額棘輪違反：本輪新增未結 3 筆 > 結案 0 筆」，commit 後 HEAD＝工作樹差集為空即轉綠——R190 同型先例）；兩次皆 `發現 5058 個測試（下限 5058）`、`workers=9`、`S=831.9s`／`S=843.5s`、`[skip census] tools/tests@darwin 共 47 支：platform=47／…／untagged=0`、`[M6 id 集合] ✅`、`✅ 真實 TEMP 圍籬 … 零變動`。
- **複審鏡 B（CONDITIONAL → 21 條文件訂正全數套用，零程式問題）**：事實對帳 41 處（FOUND 33／ALTERED 6／NOT-FOUND 2，皆已改）；關鍵訂正＝〈八〉「症狀面已穩定」改寫（Windows 零觸及、Q1 探針無鑑別力、真實 session 2/2 被擋）、λ 序列改用 R189 官方計數 2（E 12.6→15.7 輪、結論改「幾乎不可達」）、②′ 補六處規格缺口與成本面、「四方確認追認 γ」改為「Architect 建議、QA 重現、SA／SD 未覆核」、〈四〉修法欄改為實作、ARCH-05 立列 DEF-200-466、460 樞紐揭露；鏡 B 驗證 460 判 P2 **非自利**（選了較嚴一側）、「即使 461 判 P2 仍 0／2」成立；帳本純函式實算 `current_round=100`、`orphan_backlog_problems=[]`、新列情境欄 R-label 皆空；鏡 B 自己也撞判準④ 1 次。


## 七、根層全套、push 與雲端驗收

- 全套與重釘見〈六〉；commit／push／雲端 run 結論由 push 後的 docs 回填 commit 補上（本 commit 內不預寫宣稱）。

## 八、交棒／掌舵者側待辦

### Q5 評估（掌舵者原話：「請詳細回覆是否已經收斂？給我評估說明！」——先講依原判準的答案，再講根因，再講提案）

- **依 R188〈八〉原判準②：未收斂（0／2）。** 四個活體探針連續第 4 輪全綠（規則 2 後半成立）；規則 2 前半不成立：家族內新發現 P≤2＝**1**（DEF-200-460，Architect 發現、QA 獨立重現並獨立評級 P2；455 已結案故非拆殘——**樞紐揭露**：Architect 原文「若主控判它屬 455 拆殘或降 P3，則為 0」、QA 原文「若只認已驗生產觸發才計入，則為 P3、本輪 NEW＝0，我不採此口徑（455 本身就是 P2）」；主控採較嚴口徑；採保守口徑則 R191 記 1／2、R192 零新即 2／2）。R191 本是「零新即 1／2」的驗證輪，計數歸零。
- **症狀面（Mac 側）Q2／Q3／Q4 連續 4 輪穩定；Q1 只能說「黑盒 2/2 零阻斷」——該探針無鑑別力（SD-04），且判準④落地後真實主 session 2/2 在首／次呼叫被擋（DEF-200-461；本窗 #2 親歷）；Windows（Q1／Q4 實際症狀所在的機器）連續第 5 輪零觸及＝未驗**：R190 七列修法全部在 HEAD 重現、零回歸。依本節提案的 ②′甲（含 Windows 證據）今天就過不了——所以**不能說「症狀已穩定」**。沒收斂的另一半是「家族內結構缺陷的發現率」：R187 445、R188 449／450、R189 451／456、R190 457、R191 460——每輪四方都挖到東西。
- **根因（Architect C＋QA-05 獨立數學，主控採納）**：
  1. **判準②量的是審計靈敏度的函數，不是症狀**：每輪新 P≤2 序列（第 183～190 輪；R189 依其證據檔官方計數 2＝451／456）＝1,1,1,3,1,0,2,1 ⇒ λ̂＝1.25／輪（含本輪 460 為 11 事件／9 輪＝1.22；Architect 把 456 當拆殘記 1 得 1.125——口徑與 R189 官方不同、也與本輪對 460 的處理不一致，故本文採官方序列）⇒ 單輪零發現機率 0.287、「連續 2 輪零」期望 **15.7 輪**（Garwood 95% 區間 λ∈[0.60, 2.30] ⇒ E 在 5～109 輪；QA：樣本欠散布、經驗零輪頻率只有 1/8，以此算 E＝72 輪）⇒ **判準②在今天的 λ 下幾乎不可達**（任意兩輪皆零的機率 0.082——這是檢定力數字，推不出「通過者多半是運氣」）。λ 又隨審計強度升降（加強審計→更難、弱化審計→假通過＝Goodhart）。帳本統計（Architect 自陳關鍵字偏廣、只看趨勢）：家族列新立速率 09-28 起由 2.25／天升到 8.8／天、結案中位 0 天（same-day 51／61）⇒ 瓶頸是發現不是修復；但 QA 以全部 DEF-200 列算的 P≤2 **率**反向：09-20～27 6.3／日（占 68%）→ 09-28～10-02 2.4／日（占 23%）——母體不同（家族關鍵字 vs 全列），並陳不互抵。
  2. **「同一事實被兩個出口各自導出」型庫存，點狀鎖縮不掉**：09-28 起 12 條 P≤2 中 8 條屬此型（Architect 依帳本文字粗分類、未逐條 blame）（409 USERPROFILE vs HOME、420 CLI vs hook 各推 active_model、437 guard vs pace 共用遲滯鍵、438 攤提 vs gate 軸成員、445 契約寫端 vs 引擎讀端目錄、451 補量贏家 vs 輸家、455 GC 本地逐字稿 vs 全域 launchd、456 armed 路徑 vs 手動路徑）；本輪 460 就是 455 的兄弟形狀、463 是 457 的兄弟形狀——**R190 兩個點鎖各漏一個兄弟**。Chao1 粗估（f1＝9、f2＝3：420／429／445；無原始腳本、主控未抽查三列）未見庫存約 9～13.5 條。護欄層近 10 輪 +4,459 行、近 30 輪無淨減輪、回歸鎖軌 4 輪吃滿 309 ⇒ 鎖在長、庫存沒縮。
  3. **判準②可以在零觸及 Windows 下通過**：規則 2 的 Q4 探針只在 Mac 量，而掌舵者的 Q4 症狀在 Windows 11；Windows 連續 5 輪零觸及。
- **這輪為什麼不是「盲目實作」（鏡 B 校正後）**：460 的證據扎實（Architect 替身重現＋QA 三形狀＋主控親讀 `gc()`／`reap_verdict`／任務書 `state["transcript"]`＋W2 e2e 紅綠＋鏡 A 22 格新舊對照）；461 的證據證明**問題存在**（三方逐字稿普查 2/2、25 條中 2 條、3/3 自癒＋主控親讀 `_VERIFY_HINT`），但**未證明修法降低重犯**——習慣早於守衛（ba149f52 09-27 首指令即 `--check 2>&1 | head -60; echo "=== rc=$? ==="`）、9ea68d33 被擋後 #40 再犯、鏡 B 自陳任務書明寫仍撞 ⇒ 效果待量（下輪 SD-04 基線），且 `quota_messages.py` 姊妹句 :310／:443 仍寫「Bash…不受影響」未動（＝根因 2「點鎖漏兄弟」的活例，登記 461 列）；462 的證據是通道機制（SD 讀 CC 內嵌 JS 渲染分支＋QA grep＋Stop 事件活體附件），TUI 呈現與「Windows 實際未安裝」前提皆未驗 ⇒ 它是否為 Q4 成因待 [13]。463／ARCH-03～04／SA-03 有證據但不值得動程式，只登記；ARCH-05 立列 466。
- **主控對掌舵者的建議（提案，須掌舵者一句話裁決）**：
  - **甲、修憲判準②→②′**（R188 規則 3 已預留「交掌舵者修憲改判準②」）：以 Architect 提案為底、經鏡 B 補規格——**症狀錨**（真實工作 session、排除探針）：Q1′ **誤擋**＝0（正確攔截不計；鏡 B／QA：原字面「非破壞性指令被 hook 阻斷＝0」會被 461 型正確攔截永久踩線）且「助理宣稱被擋但無阻斷」＝0 且「前 5 個工具呼叫內被擋的 session 比例」≤ 掌舵者設定值；Q2′ 每 session 首次 planner 現查 ≤ 第 10 個 tool_use；Q3′ 最近 N 次 feed 與逐字稿 used 差 ≤0.1k；**Q4′ 每個平台（含 Windows）至少一筆 `--status` installed 且相符的證據，缺席＝不通過**。**審計錨**：審計協定（角色＋探針集合）雜湊凍結、期間更動即重算，**窗口須累滿 6 輪才可評估**（否則乾淨起算第 1 輪就過的機率約 90%）；**近 6 輪家族內新 P≤2 合計 ≤2、P1＝0、且最近一輪零新**（沒有最後一條會比原②寬）；拆殘定義＝「既有 **open** 列的新證據」，已結案列的同根變體（如 460 對 455）**計入**。可判定性＝**半機械**：Q2′／Q3′／乙 可由 `tools/probe/audit_session.py` 加彙總器算（該檔檔頭明寫只能當量測器、不得接閘門），Q1′ 的「宣稱被擋」是啟發式、Q4′ 的 Windows 證據需人供。**成本面並陳**（鏡 B 40,000 次模擬／點）：λ=1.125 時原② 平均 12.5 輪首次通過、②′ 平均 61.9 輪（中位 45；8 輪內 7.9% vs 47.3%）；λ=0.5（比現況好 2.25 倍）時 ② 4.4 輪、②′ 9.2 輪，單次評估通過率 42%；最早可能通過：② R193（R192 若為修復輪則 R194）、②′ R195（461 若計 P2 則 R196）；通過時 λ 的 95% 上界：② ≤1.50、②′ ≤1.05——②′ 較嚴但仍容許每輪約 1 個新 P≤2，**不宜形容為「嚴格」**。不自利：甲含 Windows 證據，今天就過不了；②′ 單次假通過約 2%（官方序列 λ=1.25）。
  - **乙、停止用「每輪再派四方挖」當收斂路徑**：在 ②′ 之下，收斂的工作是**縮庫存**不是**抓到零**——R192 起每輪固定做一件「單一導出＋環境矩陣 writer==reader 性質測試」（對 active_model／契約路徑／遲滯鍵／gate 成員／逐字稿目錄／home 這六個事實，各留一個導出函式），以及「全域副作用需擁有權證明」（本輪 460 的修法就是第一例）；絕對漏判模糊（Architect `b5_fuzz_leaks.py`／SD `d3/matrix.py`）進 nightly 棘輪、已知漏判類別只准縮。
  - **丙、Windows**：清單 vR190 仍有效，請跑 [0a]～[11]（R190 證據檔〈八〉）＋本輪新增 [12][13]（見下）。或接受 SD 的 R192 之後方案：`tools/session_gate_acceptance.py`（Python、只查不改、dev_start advisory 呼叫、JSON 落 `~/.autosdd/traces`，讓 Windows session 的模型自己執行並落檔，Mac 主控直接讀）。
- **A 案時程更新與本輪偏離**：R190〈八〉寫明「R191＝驗證輪、不改程式」，本輪**偏離**——四方挖到 460 後依掌舵者原話「若有請徹底解決」同輪根因修 460／461／462（R189 同型先例：451～454 同輪修）。原「R191 零新 ⇒ 1／2、R192 零新 ⇒ 2／2」已不成立。若不採甲：R192 若為修復輪（本節議程全是程式變更）則最快 **R194** 才可能 2／2，且依上述數學期望約 15 輪；若採甲：②′ 最早可能通過 R195（461 若計 P2 則 R196），Windows 證據到位前結構上不通過。

### 掌舵者追認題（主控代決、請在下輪開場一句話追認或否決）

1. **L1-γ**（DEF-200-199）：主控採 Architect 建議追認（QA 重現數字；SA／SD 未覆核；理由見〈四〉）。否決 ⇒ 退 L1 原文並簽收錨點①降級 `(16,16)→(16,4)`。
2. **判準②′ 修憲**（甲）：採／不採。
3. **Windows**：跑清單 vR190＋[12][13]，或接受 R192 之後的一鍵驗收腳本方案（丙）。

### 掌舵者 Windows 清單 vR190 增補（SD D5；其餘條目見 CrossPlatform_R190_FixRound_Evidence.md〈八〉，仍有效）

```powershell
# [12] 461：新視窗 SessionStart 簡報含新措辭（人看不到簡報，用 hook 直跑取證；全程不用 cd）
$repo = 'C:\<該機 checkout 絕對路徑>\AISDCL_Agent'; $py = Join-Path $repo '.venv\Scripts\python.exe'
$env:AUTOSDD_SENTINEL_OFF = '1'
'{"hook_event_name":"SessionStart","source":"startup","session_id":"win-probe","transcript_path":"C:\\nonexistent\\x.jsonl"}' | & $py (Join-Path $repo '.claude\hooks\context_budget_guard.py') > (Join-Path $env:TEMP 'r191_ss.json') 2>&1; $LASTEXITCODE
Select-String -Path (Join-Path $env:TEMP 'r191_ss.json') -Pattern 'Push-Location' -Encoding utf8   # PASS＝有輸出
Select-String -Path (Join-Path $env:TEMP 'r191_ss.json') -Pattern 'LASTEXITCODE' -Encoding utf8    # PASS＝有輸出（兩條都要有＝Windows 版安全形態）
# [13] 462：人眼。在 statusLine 未安裝的 Windows 使用者層（或先 & $py tools\install_statusline.py --uninstall 若有此旗標；沒有就跳過本條、標 USER-ONLY），新開 claude 終端：第一屏應出現「SessionStart:startup says: … statusLine 未安裝 …」；安裝後新視窗不再出現。沒出現＝紅（請貼截圖文字）。
```

### 下輪的機械義務（主控記名）

- 護欄行數棘輪：本輪結果見〈七〉；`_REPIN_NET_CAP_DUE_ROUND=192／TARGET=521` 是 **R192 的到期義務**；`_ROOT_TOOLS_OLD_SCALE_DEBT_DUE_ROUND=193`；`_PHASE2_REVIEW_LOG` 視窗到 R194。
- 帳本時鐘（QA-04 證實）：新列情境欄**一律零輪號且不得含 `R<數字>` 檔名**（檔名只放狀態欄）；六列舊 backlog（DEF-200-118／124／129／134／188／207；另 DEF-101-938／974 承接 R83 同屬過期、crossref 只翻六列）承接輪次早於真實輪號、只因時鐘凍結在 R100 才過閘——下一次**結案輪**逐列追加「改派」附記或回執，否則任何推時鐘的新列都讓它們當場轉紅。
- 帳本體積：`CrossPlatform_Guard_Line_History.md` 250,457／262,144、`CrossPlatform_DEF200274_Parallel_Tests_Evidence.md` 255,168、R190 證據檔 243,179——**別再 append**，史料改落 `CrossPlatform_Guard_Line_History_2.md` 或本檔〈九〉。
- 下輪 SA 的 Q1 探針改 SD-04 的 PA／PB／PC（模型與真實習慣者一致、各 ≥5 次、先量基線）；探針母體排除 10 份探針逐字稿。
- 承接列（Architect D，主控裁決）：**DEF-200-242 → R192 首包**（`quota_stability.evaluate()` 釋放梯：存在持久有限 cap 且 `target=None` 時先回 `cap_notice` 並保留 `min_dwell_seconds`，之後才回 None；免修憲；assertion 97 餘裕足）；**DEF-200-193 → R193 以後**（R192 只做「超支」定義與樣本重建腳本，不進護欄層）；**DEF-200-246 → R192 PRD 債軌 doc-only**（wontfix-by-design 候選，與 459 同窗、須四方同意）；**DEF-200-458 → 未指派（Pacing 第二期；W6 碰錨點①須掌舵者先裁）**；**DEF-200-459 → R192 PRD 債軌 doc-only**（PRD §8 **增補列 1b**「遙測端點自身 429：unmeasured、永不 halt、Retry-After 只做顯示」，不改寫列 1——Architect 讀 PRD 全篇 429 皆推論端，平息 QA F12 與 Architect A7 之爭）；**DEF-200-199 殘餘 → R192**（施工圖 §6.1 加速臂例外註記、762 寫入已於本輪、P16、`TestTheTableIsProducedByTheRuleNotByHand` 舊律、L2／L3）。
- R192 建議議程（若掌舵者採甲／乙）：①單一導出性質測試第一件（逐字稿目錄／home：`claude_home()`＋`project_transcript_dir()` 兩個出口；載體 DEF-200-460 結案後的結構性對策，無獨立列）；②絕對漏判模糊進 nightly（DEF-200-463）；③釋放梯（DEF-200-242）；④PRD 債軌（DEF-200-246／DEF-200-459）；⑤`tools/session_gate_acceptance.py`（丙，無列、待掌舵者裁決）；⑥測試衛生（DEF-200-464）與任務書目錄跨檔鎖（DEF-200-465）；⑦決策：statusLine 一句是否加 ENTRYPOINT／ATTENDED 判準（DEF-200-462 已知取捨）。

### 本輪未做（不塗綠）

- Windows 真機：全部未驗（連續第 5 輪），清單 vR190＋[12][13] 在上。
- SessionStart `systemMessage` 的 TUI 人眼呈現（[13]）。
- DEF-200-242／193／246／458／459／199 殘餘：承接如上，本輪零落地。
- 463 的程式修法（只登記）；ARCH-04／ARCH-05／SA-03 不立列；γ-C 備而不用；施工圖 §6.1 (i) 註記承接 R192（載體 DEF-200-199）。
- Q1 探針升級（SD-04）：下輪 SA。

## 九、搬遷史料（Developer 各棒以 append 模式落此；原位置以一行指針代替）

### 九-W2　Developer-W2（DEF-200-460 哨兵 GC 所有權證明）被取代的原文與重現摘要（逐字 append）

# lore.md — Developer-W2 (ARCH-01) 搬出／被取代的史料（逐字；來源＝git HEAD 933f0b16 的被刪／被改寫行）

本檔只收「HEAD 有、工作樹已不在」的散文與舊測試原文，供收尾窗口寫證據檔時引用。沒有為了抵銷行數而額外搬動任何無關史料（lib `count_loc` 355→359，仍在 guardrail_lib 400 之內，見交件〈行數帳〉）。

## A. tools/lib/sentinel_lifecycle.py 被取代的原文

### A-1 `plan_state()` 原全文（現為 `plan_evidence()` 的薄包裝；解析／lazy import 的 WHY 原文已逐字保留在 `plan_evidence` docstring）
```python
def plan_state(plan: Path) -> str | None:
    """任務書狀態塊裡的 `state`；讀不出來回 `None`（＝「量不到」，不是「終態」）。

    解析走 planner 的 `parse_relay`（**唯一的家**，本檔不抄第二份格式知識）。
    lazy import：planner 會把 `.claude/hooks` 接進 `sys.path` 並 import 整條 hook 鏈，
    而本模組被那條鏈 import ⇒ 放在模組層會成環。放在函式內，hook 路徑一次都碰不到它。
    """
    planner = _planner_module()
    if planner is None:
        return None
    try:
        state = planner.parse_relay(plan.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 — 讀不到就當「量不到」，判準那一側自己會保守處理
        return None
    return str(state.get("state")) if isinstance(state, dict) else None
```

### A-2 `reap_verdict` docstring ①～⑥ 全文（HEAD；② ③ 兩行是被改寫的部分）
```python
    順序即優先序，**最保守的先判**：
      ① 受保護（呼叫端指名 or 它是最近仍在寫的那一支）⇒ 絕不收。這一條擋在最前面，
         是因為誤收一支活著的哨兵＝把那個 session 的續航靜默弄丟，而弄丟是看不見的。
      ② `transcript_exists is None`（＝**量不到**：逐字稿目錄根本定位不到）⇒ 絕不收。
      ③ 逐字稿不存在 ⇒ 收（session 連檔都沒了，哨兵醒來也只會 fail-loud 空轉）。
      ④ 還在寫（閒置未達門檻）⇒ 不收。
      ⑤ 閒置達門檻 **且** 任務書是終態／根本讀不出來 ⇒ 收。
      ⑥ 其餘（閒置達門檻但狀態是 `waiting`／`sentinel`）⇒ **不收**：等額度的那段期間
         逐字稿本來就不會更新，這一格就是「不要在它最需要的時候把它拆掉」。

```

### A-3 `reap_verdict` ② ③ 的原回傳（HEAD）
```python
    if transcript_exists is None:
        return False, ("逐字稿目錄定位不到 ⇒ **量不到 ≠ 不存在**，一律拒絕回收"
                       "（請先確認 tools/session_resume_planner.py 可 import）")
    if not transcript_exists:
        return True, "逐字稿不存在"
```

### A-4 `gc()` 原證據來源（以**呼叫者** HOME 下的專案目錄判每支哨兵＝缺陷本體；HEAD 原文）
```python
    base = _transcript_dir()
    if base is not None and not base.is_dir():  # 目錄不在＝量不到（HOME 被隔離／換機），不是檔被刪
        base = None
    tmp = Path(tmp_dir or tempfile.gettempdir())
    protected_ids = set(keep) | {_newest_session(base)}
    now = time.time()
    rows: list[dict] = []
    for task in tasks:
        sid = session_of(task)
        # 🔴 `base is None` 一律傳 `None`（＝量不到），**不得**塌成 `False`：
        # 那個塌陷正是本檔第一版實跑 dry-run 時把三支哨兵全判成可收的原因。
        transcript = (base / f"{sid}.jsonl") if base is not None else None
        exists = None if base is None else bool(transcript and transcript.is_file())
        idle = (now - transcript.stat().st_mtime) if exists else None
        plan = tmp / f"autosdd_resume_plan_{sid}.md"
        state = plan_state(plan) if exists else None
```

## B. tools/tests/test_mac_endurance_r83.py 被改寫的原測試（HEAD 原文）

### B-1 單元「對照組」——目錄在、檔不在 ⇒ 收（這個預期正是 ARCH-01 缺陷本身）
```python
    def test_gc_still_reaps_a_true_orphan_when_the_dir_exists(self) -> None:
        """對照組：目錄在、該 session 的檔不在＝真孤兒，仍要收（不得把 GC 鈍化成永不收）。"""
        scratch = tempfile.TemporaryDirectory(prefix="r83_gc_orphan_")
        self.addCleanup(scratch.cleanup)
        tmp = Path(scratch.name)
        base = tmp / "projects"
        base.mkdir()
        (base / "live.jsonl").write_text("{}\n", encoding="utf-8", newline="\n")
        removed: list[str] = []
        with mock.patch.object(sentinel_lifecycle, "_transcript_dir", return_value=base), \
                mock.patch.object(sentinel_lifecycle, "sentinel_task_names",
                                  return_value=["AutoSDD_Sentinel_orphan",
                                                "AutoSDD_Sentinel_live"]), \
                mock.patch.object(sentinel_lifecycle, "_remove_task",
                                  side_effect=lambda task: removed.append(task) or 0), \
                mock.patch.object(sentinel_lifecycle, "_record_reap", return_value=""):
            rows = sentinel_lifecycle.gc(apply=True, tmp_dir=str(tmp))
        self.assertEqual(removed, ["AutoSDD_Sentinel_orphan"])
        self.assertEqual({row["session_id"]: row["reap"] for row in rows},
                         {"orphan": True, "live": False})
```

### B-2 e2e helper 簽名與 docstring（HEAD）
```python
    def _gc_launchctl_rows(self, *, projects_dir: bool) -> list[str]:
        """隔離 HOME、不設逃生口、真 hook SessionStart ⇒ 回假 launchctl 收到的每一行。

        PATH 前置假 launchctl（只記錄）⇒ 無論紅綠都碰不到真排程器。回收行程是 detached 的，
        所以輪詢到它退場（以它對假 launchctl 的 ppid 為準）才回傳；沒跑完就 fail。
        `projects_dir`＝逐字稿目錄是否存在（False＝HOME 被隔離的真實情境）。
        """
        scratch = tempfile.TemporaryDirectory(prefix="r83_gc_iso_")
        self.addCleanup(scratch.cleanup)
        tmp = Path(scratch.name)
        for sub in ("bin", "home", "tmp", "traces", "cfg"):
            (tmp / sub).mkdir()
```

### B-3 兩支 e2e 測試（HEAD）
```python
    def test_session_start_in_an_isolated_home_never_unloads_a_live_sentinel(self) -> None:
        """🔴 DEF-200-455 進程級 e2e：HOME 被隔離（逐字稿目錄不存在）時，真 hook SessionStart
        spawn 的回收行程不得對活哨兵發出任何寫類 launchctl（macOS）；其他平台以行程內同判準跑。"""
        rows = self._gc_launchctl_rows(projects_dir=False)
        self.assertEqual(self._writes(rows), [],
                         "隔離 HOME 下 GC 對活哨兵發了寫類 launchctl（DEF-200-455）")

    def test_the_same_harness_does_unload_a_true_orphan(self) -> None:
        """對照組（e2e 版）：逐字稿目錄在、兩支哨兵的檔都不在＝真孤兒 ⇒ 假 launchctl 必須看到
        bootout。少了它，上一支的「零寫類」可能只是替身壞了（本檔曾因 printf 選項誤判空轉）。"""
        rows = self._gc_launchctl_rows(projects_dir=True)
        outs = [r.split("argv=", 1)[1] for r in self._writes(rows)]
        for label in ("AutoSDD_Sentinel_live-a", "AutoSDD_Sentinel_live-b"):
            self.assertTrue(any(o.startswith("bootout ") and o.endswith(label) for o in outs),
                            f"真孤兒 {label} 沒被 bootout ⇒ 本 harness 看不見卸載：{rows}")
```

## C. 缺陷（ARCH-01）敘述與本包實測摘要（供證據檔引用；Architect 部分標 `[他包回報]`）

- `[他包回報]` 根因：`gc()` 以 `_transcript_dir()`＝`planner.project_transcript_dir(_REPO_ROOT)`（呼叫者 HOME 下的專案 slug 目錄）判每支哨兵逐字稿是否存在；目錄存在但沒有 `<sid>.jsonl` ⇒ `reap_verdict` ③ ⇒ `--apply` 時 bootout 使用者全機的活哨兵（launchd／schtasks 工作是 per-user 全域）。證據是本地的、目標是全域的。前一輪的 P0 只擋了「目錄不存在」，且把「目錄在、兩支皆孤兒 ⇒ 必須 bootout」釘成預期行為。
- 本包自己重現（HEAD 933f0b16，dry-run，真 launchd 前後皆 2）：(a) 真 HOME 兩支皆「✅ 留」；(b) `HOME=<沙箱>` ＋ 既存空專案目錄 ⇒ 兩支皆「🗑 收／逐字稿不存在」（缺陷）；(c) 同 (b) 不建目錄 ⇒ 兩支皆「✅ 留／逐字稿目錄定位不到」。逐字輸出＝`step1_repro_HEAD.out`。
- 本包 (d)：替身 launchctl（PATH 前置、`list` 回兩個真 label）＋ `--apply --keep probe`：pristine HEAD lib bootout ×2（有任務書／無任務書皆然）；修後 bootout ×0。逐字輸出＝`step_d_repro.out`。
- 修法三刀（主控裁決的原則 1～6）：`plan_evidence()` 取任務書狀態塊的 `(transcript, state)`；`reap_verdict` ③ 補狀態閘；`gc()` 改取該證據，`_newest_session`／`--keep`／dry-run 預設／`None` 語意原樣。額外一處零行數成本：`gc_reaped` 痕跡多帶 `transcript=`（判定依據的路徑），事後可歸因。

## D. tools/tests/test_context_budget_guard.py::SentinelReapVerdictTest._apply_once 被同步的原夾具（主控授權只動該 class 範圍；HEAD 原文）

這個夾具編碼的正是 ARCH-01 的缺陷形狀（任務書是不含狀態塊的 `state: disarmed` 單行 ＋ 呼叫者專案目錄「在、卻沒有該 sid 的檔」＝可收）。新語意下它的任務書沒有逐字稿路徑 ⇒ 量不到 ⇒ 不收 ⇒ 兩支依賴它的測試（`test_reaping_a_sentinel_leaves_an_audit_trace`、`test_a_trace_that_never_landed_is_not_reported_as_landed`）的 `row["reap"]` 預期 True 變 False，why＝「取不到這支哨兵任務書記的逐字稿路徑…」。
```python
        逐字稿目錄刻意「定位得到、那支檔不存在」＝可收那一條路；殘骸也真的落在磁碟上，
        所以掃殘骸與寫痕跡的先後順序是被真的走過一次的，不是靠讀原始碼推論的。
        ...
        plan.write_text("state: disarmed\n", encoding="utf-8", newline="\n")
```

### 九-B　Developer-B（DEF-200-461／462 行動點缺口與 statusLine 出聲）候選史料（逐字 append）

# Developer-B 搬出的史料（append-only）

## 本包搬出現有註解／docstring 的行數：0
- `.claude/hooks/context_budget_guard.py` raw 行 1087 → 1088（淨 +1，落在任務書 0～+2 內；special 棘輪預算 1089，headroom 2 → 1）。
  未搬出任何既有史料，因此不需要「搬史料抵銷」，SPECIAL_FILES 無須重釘（`special_stale_slack`=32，1088 vs 1089 不構成過期）。
- 其餘三支 source 檔（session_brief／platform_utils／block_destructive_git）屬 count_loc tier（assertion 計數）：
  session_brief 231→255／400、platform_utils 96→101／400、block_destructive_git 708→714／750；新增敘事（註解／docstring）不計入 count_loc。

## 候選史料（給主控入證據檔；不是從程式碼搬出，而是本包在實作中親眼取得的事實）
1. 活體 dogfood（本包自己撞上）：改完 hook ④ 之後，本包下一條 Bash 指令（`git diff … | grep …; echo "grep_rc=$?"`）被**剛改好的**
   `block_destructive_git.py` 擋下，stderr 首行即新解法（逐字）：
   `🔴 已擋下：`… | head`／`… | tail` 之後讀 `$?`，讀到的是 head／tail 的 rc。正解：`cmd > /tmp/o.log 2>&1; echo rc=$?; tail -n 20 /tmp/o.log`（輸出很短就直接跑，別接管線；鐵律六／`DEF-200-086`）`
   下一個呼叫即照此導檔重跑成功（rc=0）——SA-01 想要的「被擋後一眼拿到出口」在生產 hook 上實測成立（單次觀察，不是統計）。
2. 跨 lane 失敗歸屬（Developer-W2 的 `sentinel_lifecycle.gc` 證據來源改動所致，非本包）：
   · `test_context_budget_guard` 真樹 `Ran 789 … FAILED (failures=2)`：`SentinelReapVerdictTest.test_reaping_a_sentinel_leaves_an_audit_trace`
     與 `…test_a_trace_that_never_landed_is_not_reported_as_landed`（`reap` 由預期 True 變 False，why＝「取不到這支哨兵任務書記的逐字稿路徑」）。
     這兩支住在本包持有的 `test_context_budget_guard.py`（約 :11270～:11320）——W2 改的是 gc 語意，夾具要由 W2 同步（本包不碰）。
   · 歸屬實證：本機 `git clone --local` 出一份、只覆蓋本包 7 支檔（W2 的檔留 HEAD）→ 同檔 `Ran 789 … OK (skipped=11)`；
     同一個 `SentinelReapVerdictTest` 類別在該 clone 內 `Ran 11 … OK`、真樹 `Ran 11 … FAILED (failures=2)`。
   · `test_subprocess_encoding_hygiene.TestRootToolsLintPolicy.test_e501_debt_only_shrinks` 真樹 `147 not less than or equal to 139`：
     過長行（EAW>100）由 W2 的 `test_mac_endurance_r83.py` 新增（逐檔量：本包三支測試檔 delta=0；W2 該檔 1→11）；clone 內該檔 `Ran 39 … OK`。
