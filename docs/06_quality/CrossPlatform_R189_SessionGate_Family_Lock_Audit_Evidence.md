# CrossPlatform R189 — 掌舵者五問家族級結構鎖審計輪（第十一次四方覆核；硬上限輪）證據檔

> 日期 2026-10-01；平台 macOS（Darwin 25.6.0 arm64，Mac Studio）；Claude Code 2.1.286；主控 Fable 5.1，四方（Architect／SA／SD／QA）、Developer 四棒與複審鏡皆 Sonnet（掌舵者指令：子 agent 一律 Sonnet 5.5）。
> 起點 HEAD `9fb0a604`（R188 收尾），工作樹乾淨。掌舵者原話：「選Ａ，還沒收斂就繼續！」＋「派出 Architect／SA／SD／QA 四方專家獨立審查，請確認以上都已經修好！」＋五問原文。R188〈八〉把 R189 定位為 Windows 硬上限輪；實際在 Mac 執行，Windows 真機零觸及（見〈五〉）。

## 〇、一句話結論

五問在 Mac 第十一次驗：四個活體探針全綠（Q1 新視窗黑盒零阻斷 `[他包回報]`、Q2 主控第 1 個工具呼叫即 `--pace`＋`--check`（主控親測）、Q3 `--check` 差=0 且歷史 `/context` 對帳 12／13 ≤48 tokens `[他包回報]`、Q4 `--status` installed 且相符（主控親測）），R188 的三個修法在 HEAD 全部重現、零回歸 `[他包回報]`。但家族級結構鎖審計挖到 **1 筆家族內新 P2**（DEF-200-451：額度補量名額的輸家被當「量不到」⇒ PostToolUse 假警報＋平行 Agent／Workflow 誤擋 rc=2；真實逐字稿 2 筆誤擋、真實痕跡 57 筆假「取數失敗」零筆真失敗）與 3 筆 P3（452／453／454）：452／453／454 本輪修復結案，451 的 M2（在飛贏家）與 M1（次秒 TTL 視窗）兩個成因皆修（M1 由修補棒 Developer-E 補上，見〈四〉E 列）；另把四次改派的 P1 DEF-200-086 真的修掉、DEF-200-231 的 ①時刻修掉並結案（手動路徑醒來不做事的既有半邊拆成 DEF-200-456）、DEF-200-286 拆殘成 DEF-200-455。依 R188〈八〉**原判準**：R189 家族內新發現 P≤2＝**2**（451 由 Architect 挖出、456 由複審鏡 B 挖出；兩者皆 HEAD 既有、皆非本輪引入——「既有」不是排除條件，R187～R188 的 445／449／450 也都是既有）⇒ 計數歸零（**0／2，未收斂**）；「硬上限不開第三輪」是主控自訂規則，掌舵者原話「還沒收斂就繼續」優先——選項見〈八〉。

## 一、五問第十一次判定（Mac）

| 問 | R189 判定 | 一句話（主控親測或他包實跑） | 與 R188 的差異 |
|---|---|---|---|
| Q1 新視窗就說被擋 | **活體 PASS；另找到第二類「模型被告知受限」的真實來源（額度配速 M2／M1 已修；DEF-200-197 429→halt 仍 open）** | 主控本場：SessionStart 印退化政策值 `cap=2 recommended=2 band=unmeasured`（stale-cache 4059s）後 Bash 全 rc=0、四個 Agent 派工成功。SA 黑盒 `claude -p --debug hooks`：根 `Hook SessionStart.*success`=2、`posix_spawn`=0、error-ish 9 行逐條良性（ENOENT 5 筆為可選目錄探測）；AutoClaude 子專案 success=0（無 SessionStart hook＝設計）；兩探針逐字稿 `hook_system_message`=0、`hook_non_blocking_error`=0 `[他包回報]`。SA 逐字稿普查 09-27 起 16 份（真工作窗 5、IDE 舊窗 1、headless 探針 10〔根 4＋AutoClaude 6，含他包 3〕）：hook 造成、模型宣稱被擋 **0 例**；命中 18 筆＝3 筆「子 agent 改 `.claude/settings.json` 被 Self-Modification 分類器拒」（事實屬實、非 Q1 形態）＋15 筆後設引述；`[SDD-FSM][BLOCK]` 只剩 09-08 舊窗 cd33883f 2 筆 `[他包回報]`。Architect：新視窗首 Write 被 deny 的充要條件＝鏈啟動∧¬DISABLE∧¬DRY_RUN∧bootstrap 成功∧(S∈{ESCALATION, ESCALATION_FINAL, TOKEN_BUDGET_CRITICAL, TERMINATED}∨(目標含 docs/01｜02｜03 前綴∧S∉7 態允許集))；今日 S=SPEC_DRAFTING、狀態檔 mtime 09-11 ⇒ 假（live 矩陣 A 欄六格全 pass）；**「FSM 殘留態是唯一機制」不成立**——第二類來源＝額度配速的 F1／F2／F3（擋的是扇出型工具、對模型講「量不到／只有人去提額」）與 DEF-200-197 的 429→halt `[他包回報]`。 | 由「機制面 PASS」進到「找到第二類來源：M2／M1 已修、197 仍 open」 |
| Q2 不用真實數據 | **PASS** | 主控第 1 個工具呼叫即 `--pace`＋`--check`（SA 腳本證實 20:14:20.778）。SA 普查真工作窗：96df659c #1、ba149f52 #1／#2、718ff654 #2、452cab3f #12（前 11 步＝切換 SOP 的 git 同步／dev_start）`[他包回報]`。 | 無變化 |
| Q3 數字與 /context 不符 | **NOT-A-DEFECT** | `--check` `harness used=152,422 逐字稿 used=152,422 差=0`（SA 20:32 跑，子 agent 讀到的是父 session 的 sid，數字是主控窗的）`[他包回報]`。歷史 `/context` 面板 14 筆：13 筆有前一筆 usage、12 筆差 ≤48 tokens、本輪新增 0 筆；09-08 離群（-6,759）仍唯一，且是 13 筆中唯一在回合中途打的 `[他包回報]`。Architect：context 兩實作對拍＋真實 234 份逐字稿 0 不一致 `[他包回報]`。 | 母體再擴、結論不變；離群的成因有了方向（回合中途） |
| Q4 Windows 沒有 ctx 行 | **NOT-A-DEFECT（連續第 4 輪）；補一個 P4 洞** | SD：`--status` `installed: true, matches_current_checkout: true, python_basis: repo-venv` rc=0；合成 stdin 印 `ctx 18% 175.2k/1.0m | Fable 5.1`，`d67da1de^` 版同 payload 印 `ctx 18.0% …`（掌舵者原文逐字＝舊版格式、2026-09-28 起已改）；**Windows 機自 R179 起已裝、掌舵者於 R181／R182／R186 三度肉眼見過（前輪證據，最近一次 R186＝2026-09-30；本輪 Windows 零觸及）**；repo settings 從未帶 statusLine（兩份各 0 筆，裁決出處 DEF200275 證據檔 :1459）；待驗假設「pythonw 無 stdout／python.exe 必閃窗」兩邊皆不成立（R179 Windows 實跑＋讀 **Mac 版**二進位 `windowsHide`，Windows 屬推論）；dev_start 六檔不自動裝（0 命中）；SessionStart 簡報未安裝時印的安裝指令是「預覽版＋裸 python＋相對路徑」、且走 additionalContext 人看不到 ⇒ 本輪只把指令修成絕對路徑可貼（Developer-C；仍走 additionalContext，人仍看不到，靠模型轉述）`[他包回報]`。 | 新增「Windows 早已裝好」的事實與簡報指令修法 |
| Q5 收斂了嗎 | **依原判準 0／2＝未收斂** | 四個活體探針全綠（規則 2 後半）；家族內新發現 P≤2＝2（DEF-200-451 P2：SA 評 P3、Architect 評 P2，主控採 P2——同類先例 DEF-200-437 即 P2；DEF-200-456 P2：手動排程醒來不做事，複審鏡 B 挖出）⇒ 規則 2 前半不成立、計數歸零。455 為 286 既有列的新證據拆殘、不計；家族內 open P1 197／198／199 仍在。「硬上限不開第 3 輪」是主控自訂規則、掌舵者原話優先。評估與選項見〈八〉。 | R188「1／2」→ R189「0／2、未收斂」 |

## 二、主控親測事實（本場 tool_result 逐字）

- 新視窗 SessionStart：`額度：額度量不到（reason=stale-cache（資料在，但已 4059s > TTL 180s ⇒ 重量一次即可，不是取數壞掉））⇒ cap=2 recommended=2 band=unmeasured … statusLine：已安裝`；`[SDD-FSM] … current_state: SPEC_DRAFTING … ℹ️ 以下 DECISION-TRACE 為歷史紀錄…阻斷已於 2026-09-10T16:44:57+00:00 解除`。
- 第 1 個工具呼叫＝`--pace`＋`--check`：`現在可派 8 個 agent（硬上限 cap=不設限）｜band=free｜最緊的一條＝weekly_scoped 31% 剩 3225 分鐘 … ⏱ 扇出視窗：300s 內帳上 0 筆 ⇒ **視窗全空** … 來源=cache 量測於=2026-10-01T20:14:24+08:00` rc=0；`--check`：`新視窗：逐字稿還沒有任何帶 message.usage 的 assistant 記錄 … harness 回報 used=77,116（feed，尚無逐字稿可交叉比對）` rc=0。派 Developer 前再查：`現在可派 8 個 agent … weekly_scoped 33% 剩 3169 分鐘 … kind=session 43% 剩 109 分鐘`。
- **本場親歷 F1／F3**：`--pace` 刷新（20:14:24）後約 180 秒，某次 Bash 的 PostToolUse 印 `⚠️ 額度水位**量不到**（source=stale-cache）⇒ 本次扇出硬上限收到 2（量不到 ⇒ 收緊，不是放行）。這不是「額度很寬鬆」：取數失敗，且逐字稿裡沒有未復原的撞線可以當地板`——與同 session SessionStart 對同一 source 的「不是取數壞掉」逐字矛盾。SA 時序重建：實際間隔 180.2s，落在「快取已過 TTL、刷新名額未過期」的次秒視窗 `[他包回報]`；Architect 以 hook `durationMs=87`（含 HTTP 的補量 ≥330ms）推定該支 hook 根本沒去補量（搶輸） `[他包回報]`。
- **本場親歷 DEF-200-197（既有 P1 open，非新發現）**：SA 探針以 TMPDIR 隔離沙箱繞過 180s 名額、連打 usage 端點約 40 次（確定 200 的 10 次、其餘約 30 次為 429），真實共享快取兩度被寫成 429 地板（20:41:45→resets_at 20:44:22；20:47:52→20:50:12），即 `~/autosdd_quota.json` 兩度被寫成 `rate_limited 100%`（`http_status:429`、`via:http-429-floor`），QA／Architect 窗各收到一次「額度到達**停止**水位…換模型沒有用…只能等 reset 或提額」＋「已武裝喚醒」通知，當時真實額度 30～34% `[他包回報]`；主控當即下令停打、通知三包勿立案，20:50:53 真實快取回 200。**審查探針打真端點無規範**＝DEF-200-198 已記載的同型重演，列入〈八〉。
- `git status --short` 空；HEAD `9fb0a604`；`sdd_version.py`＝`AISDLC_SDD_v0.30`；`~/.zshrc:9` `export SDD_ACTIVE_VERSION=0.30`；FSM-STATE `current_state: SPEC_DRAFTING`；`claude --version` `2.1.286`；`install_statusline.py --status` `installed: true … matches_current_checkout: true … python_basis: repo-venv` rc=0。
- ListAgents peer `aisdcl-agent-40`（idle 11h）＝`ps` 認身分 `~/.antigravity-ide/extensions/anthropic.claude-code-2.1.286-darwin-arm64/resources/native-binary/claude --output-format stream-json`（IDE 擴充套件閒置行程）⇒ 不需協調。
- 今晨 nightly `nightly_mac_20261001_020000.log`：`PASS=4 FAIL=0`，`grep 'git context:|SAMPLE VALIDITY:'` 0 筆（02:03 跑在 DEF-200-450 修法 commit 18:46 之前，預期）；`nightly_mac_20261002_020000.log` 尚不存在。

## 三、四方摘要 `[他包回報]`

- **Architect（PARTIAL）**：A1 註冊面母體完整——三份活躍 settings 21 條註冊→15 支腳本＋載具＝16 檔，結束碼鎖逐支重放皆 `[]`；但鎖深度有洞（7 個突變只抓 2、移除 `enforce_docs_path` 註冊鎖仍綠＝P4 F5）；pace 的鎖只釘「搶名額原子性」、輸家行為零覆蓋；context 兩實作對拍＋234 份真實逐字稿 0 不一致；statusLine 結構上 USER-ONLY；喚醒鏈「假 halt 不得武裝」無鎖（即 DEF-200-197）。A2 `main()` 回 1 僅 3 支且皆帶 `# degraded-payload` 標記；PostToolUse rc=2「BLOCK」殘留 3 檔 4 站（R188 已登記，P4 F6）；449 只有 2 個消費者、資料源皆 payload 優先；450 SAMPLE VALIDITY 欄位名逐字對稱、但 `git context` 行與 72h 陳舊 WARN 在 .ps1 側缺（P4 F8，家族外）。**A3＝F1／F2／F3**：`claim_refresh_slot()` 的 `O_CREAT|O_EXCL` 原子性正確，缺「搶輸者怎麼辦」——輸家直接落 unmeasured→`degraded_cap=2`；隔離重現 18 輪：4 平行 `PreToolUse Agent` 6/6 輪恰 1 支 rc=2、3 平行 `PostToolUse Bash` 6/6 輪恰 1 支假警報，贏家 refresh 皆成功；真實逐字稿（315 檔）throttle 誤擋 2 筆（UTC 09-19T17:02:33Z Agent `已 187s`、09-20T16:38:36Z Workflow `已 180s`，痕跡檔同秒對得上，模型重派延遲 3.5 分鐘／93 秒）；真實痕跡 159 筆中 `stale-cache` 50＋`expired-window` 7 全帶固定「取數失敗」而同步取數失敗痕跡 0 筆。F2：`binding is None` 落入 `reset_branch(None)` 印「沒有 reset 可以等…只有人去提額…不會自己解除」。假設(2)「TTL 太短」**不成立**（第一支碰到邊界的 hook 自己補量，快取不是常態過期）。A4 見〈一〉Q1；F4＝PENDING 殘留橫幅對非 owner 新視窗寫「必須立即 stage-compaction」而 D11／D19 實際放行（P3）。A5：449 屬前輪修法姊妹、450 不嚴格是、F1 非姊妹故規則 4 不豁免。
- **SA（PARTIAL）**：S1／S2／S3 見〈一〉。S4 帳本 09-27～10-01 新立 6／13／15／10／6 列（P≤2 為 2／1／3／3／1）；435～450 十六列全 fixed；家族內 open P1（197／198／199／086／231／286）在本輪前仍在。S5 反駁「--pace 後第 181 秒必印」：沙箱 +181s 探針 4/4 靜默；訊息只在 M1「快取已過 TTL 但刷新名額未過期」的次秒視窗或 M2「他人刷新進行中」出現（沙箱 22 探針：視窗內 6/6 出訊、視窗外 0/16；M2 hermetic 4 hook 同時到達恰 1 刷新者＋1 訊息）；曝光率每 100 次 tool_use 0.23～0.72 次（0.72 含 SA 自造 2 筆，自然 0.36）；PostToolUse 48 次曝光，其後 4 個 assistant 記錄內零次受限類陳述 ⇒ SA 建議 P3（主控採 Architect 的 P2，理由見〈一〉Q5）。S5-附：兩次 429 判定為 DEF-200-197 活體證據、非新發現，並列放大因子（假 halt 會寫任務書並重武裝哨兵、名額檔在 TMPDIR 而快取在 HOME、expired-window 尾巴）。P4：子 agent 的 `--check`／`--pace` 讀的是父 session 的 sid；`/context` 驗收應在回合結束後打。
- **SD（PASS）**：見〈一〉Q4。D3 四候選：(i) 簡報印可貼絕對路徑指令（推薦、本輪做）；(ii-寫) dev_start 自動安裝＝違反 R177〈四〉／R183 QA-1「不得自動代寫使用者層」（否決）；(ii-報) dev_start 只報不寫（次選，`dev_start.py` 餘裕 1 行須先搬史料）；(iii) repo 層 settings 加 statusLine＝唯一 0 步驟方案，但要掌舵者重開 R158 A3／DEF200275 §1459 並先做 Windows 最小親驗（本輪不做）。D4 R188 P4「`--status` 不含腳本版本」駁回為設計邊界（現行 checkout 看舊設定回 `matches:false` rc=1；只有舊 checkout 自己跑才假相符）。D5 R188〈八〉五條 PowerShell 以 pwsh 7.6.3 Parser 解析 `parse_errors=0`；repo 的 PowerShell lint hook 在 Mac 是 no-op（`os.name!="nt"`，陽性對照也 rc=0 ⇒ 假綠識破，改呼叫純函式 `lint_command`：陽性 2 hits、七行 0 hits）。P4：F3 `_quote_token` 對 PowerShell＋含空白路徑 `parse_errors=1`（latent）；F4 ONBOARDING §4「閃窗尚待親驗」已過時；F7 清單 `$repo` 佔位符與硬寫 v0.30。
- **QA（PASS）**：T1 R188 量化宣稱在 HEAD 零差異：AutoClaude hooks `94 passed`、nightly static `40 passed`、合跑 `134 passed`；根層 `test_block_destructive_git_r83` Ran 172 OK、`test_check_hooks_liveness` Ran 185 OK (skipped=5)、`test_context_budget_guard`＋`test_quota_policy` Ran 1051 OK (skipped=11)、`test_platform_utils_dedup` Ran 43 OK、`test_defect_id_reference_integrity` Ran 11 OK。T2 449 活體：同 prompt 兩次，第 1 次（8cfcb3ed）haiku 走拒答分支 hook 合法靜默、第 2 次（3e9531f5）`hook_system_message`=1／`hook_non_blocking_error`=0／`hookErrors` 空、對照組 16d96c53 為 0；447 真 CLAUDE.md（400 行）rc=0 單行 additionalContext、沙箱製造漂移後 `stop_hook_active` false 出單行 JSON／true 靜默、401 行兩支 rc=2；450 對真 repo 只跑 `print_tree_identity` 印 `git context: branch=main sha=9fb0a604 … behind_origin_main=0`／`SAMPLE VALIDITY: tree_state=clean dirty_entries=0 … head=9fb0a604`、`.git/index` md5 前後相同。T3 `archive --check`／crossref／`--unresolved-count`（37／151）／handoff_carriers 全 rc=0。T4 承接列現查見〈四〉末兩列與〈八〉；286 的新證據：macOS unified log `10:53:43.605 launchd … removing service: AutoSDD_Sentinel_452cab3f-…`（一個 live 哨兵被未知行程卸載，stamp 仍在），`11:01:41` hook 側 relatch 補回（DEF-200-269 F4 實戰自癒一次，缺口約 8 分鐘）；卸載者未歸因（同窗 10:40～11:03 有測試 fixture 的 `removing service` 成對出現，只是時間相鄰）；`_write_marker` 以 `"w"` 覆寫，原始 `sentinel_armed` 事件被 relatch 蓋掉。

## 四、新發現與修法

| DEF | P | 來源 | 修法（Developer 四棒並行、檔案面互不重疊 `[他包回報]`；主控收尾親驗見〈六〉） |
|---|---|---|---|
| DEF-200-451 | P2 | Architect A3（隔離重現＋逐字稿回溯） | **Developer-A**：`quota_ledger.py` 新 `await_winner`（+27）、`quota_gate.py` `settled_quota`＋hook 路徑／`pace_state` 兩站（+36／−20）——搶輸且快取不可用時，名額戳記仍在飛（年齡 < 同步逾時）就有界輪詢重讀快取，逾時才落 unmeasured；輸家最壞多等 ≈ 4s − 戳記年齡（PreToolUse hook timeout 10s、PostToolUse 30s 皆在內）；「每個 TTL 只有一次補量嘗試」設計不變。鎖：`test_context_budget_guard.py` 14139→14415（+276，15 條）——N 並發零 rc=2、零 degrade 痕跡、贏家恰 1 次 urlopen。修前紅 `Ran 21 tests … FAILED (failures=10, errors=2)`→修後 `Ran 22 tests … OK`；合跑 `test_context_budget_guard test_quota_policy` `Ran 1066 tests in 55.041s OK (skipped=11)`（修前 1051）；a3_repeat 4 平行 PreToolUse Agent×6 輪 rc=2 6/6→0/6、三場景假警報 6/6→0/6、18/18 輪贏家 urlopen 恰 1 次；9 種突變全被抓。全程替身、未打真端點。`quota_gate.py` LOC 499→500（餘裕歸 0）。 |
| DEF-200-452 | P3 | Architect A3.4／SA S5 | **Developer-A**：`quota_messages.py` +43——unmeasured 專句（等下一次補量或現查 `--pace`、與 reset 無關）＋3 個渲染函式，不再落入 `reset_branch(None)`；`ThrottleBandSaysHowLongItLastsTest` 補 unmeasured 案。 |
| DEF-200-453 | P3 | 主控本場親歷＋Architect 痕跡普查 | **Developer-A**：`note_degraded` 改傳 `state.reason`（stale-cache／expired-window 印原句「不是取數壞掉」），真失敗路徑（meter-unreachable）才保留「取數失敗」；PostToolUse 退化通知補收斂型工具澄清句——**偏離規格一處**：不照抄 HALT 全句（其「只有扇出型…暫停」對量不到為假），改取 halt 同源函式前半句（平台分支仍只有一個家）。 |
| DEF-200-454 | P3 | Architect A4 live 矩陣 | **Developer-D**（只動 LATEST v0.30 兩支既有檔）：`session_start.py` PENDING 橫幅改依「本視窗實際會被怎麼對待」分態、與 PreToolUse 判準同構、零放行邏輯改動——owner／查無 owner 且 ≥85% 保留「🔴 必須立即 stage-compaction」並先印實測 used／window／比例；owner 且 <85% ⇒「第一次工具呼叫自動釋放」（主控任務書漏的第四態，採納）；量不到 usage ⇒「首擊放行（UNMETERED）」；非 owner ⇒「他窗殘留、不受限、工具照常放行（規格檔 Write/Edit 仍受 SPEC-GUARD）」。「查無 owner 記錄」不歸非 owner（`assert_tool_allowed` 保守視同 owner，≥85% 時 pre hook 真的 deny，parity 實測）。`test_session_start_rules.py` 9→25，含 7 格「橫幅寫必須 ⇔ 真跑 `context_ledger_pre.main()` 對 Edit deny」parity；修前 `14 failed, 11 passed`→`25 passed`；8/8 變異變紅；`bash scripts/ci-gate.sh` rc=0「✅ 本機 CI 閘門全數通過」逐軌 `v0.01:1475 v0.30:1979 scripts/tests:362`（v0.30 +16）；真實 FSM-STATE 前後 `2026-09-11T00:44:57 4008 bytes sha256=155cd5e7c78ff6f3` 相同。 |
| DEF-200-086（結案） | P1 | 帳本第 4 次改派「末次」；QA T4 現查仍 `[]` | **Developer-B**：`block_destructive_git.py` `waitform_hits` 新增 `tool="Bash"` 參數與判準④（rc 遮蔽型濾器 tail／head／tee／sed／awk／cut／sort／uniq／wc／cat／tr／column／less／more 接 `$?` 讀取；grep／rg／test／jq 刻意不判；`PIPESTATUS`／`pipestatus`／`pipe_?fail`／`# waitform-ok:` 豁免；行程替換 `<( … )` 內管線不判；「其後讀 $?」＝管線結束後緊接的下一個指令），docstring 三條→四條，`main()` 傳 tool 並分流頁尾；hook 以同目錄暫存檔＋mv 原子安裝、`py_compile` rc=0，count_loc 583→643（預算 750）。鎖：`test_block_destructive_git_r83.py` 172→189 測試（2663→2873 行）；修前 `Ran 189 tests … FAILED (failures=26, errors=16)`→修後 `OK`。活 hook 實證：`true | tail -1; echo "live-probe rc=$?"` 被已註冊 PreToolUse 真擋，訊息含 DEF-200-086／先導檔／PIPESTATUS／zsh pipestatus／waitform-ok。假紅普查：transcripts 母體 5149（去重 4974）既有探針 waitform 4→67，多出 63 筆逐筆判讀＝真陽 63／假陽 0（tail 48／head 12／cut 3），獨立 oracle 65 vs 63 差 2 筆皆已解釋；tracked 逐行 14 筆皆在 hook 輸入域外、.sh 23 檔 0 命中、yml run 區塊 215 段 7 段命中全在 `AISDLC_SDD_v0.30/docs_template` 範本（真陽、未改）。根 CLAUDE.md 鐵律六誠實劃界 bullet 1 增 1 減；`test_doc_loc_baseline_freshness_r60` `Ran 281 tests … OK`。仍未涵蓋：背景完成通知的 exit code、`-c` operand／ssh 引號內管線、zsh `$status`、sudo／xargs 前綴、整條豁免會漏同條另一處誤用（transcripts 1 例）。 |
| DEF-200-231（結案；①） | P1 | QA T4 拆項 | **Developer-C**：`session_resume_planner.py` `--at` 預設 None；缺席時取額度快取實測 `resets_at`（`read_quota`→`decide`→`halt_resets_at`→`reset_branch==arm`＋既有 `RESET_SKEW_SECONDS`），解不出 rc=1 拒絕（stdout 不印腳本、底層註冊呼叫 0 次）；INV5 仍先於解析；顯式 `--at` 不變；`schtasks_command(at_expr=)` 改必填；`DEFAULT_AT_EXPR` 保留（無程式碼 import，只剩註解／docstring／ADR 引用）——主控裁決保留為「被禁止形態」的對照常數。真 repo `--print-schtasks-command`（22:10）：快取 resets_at 22:59:59 ⇒ `-At '2026-10-01 23:01:59'`、無 AddHours；空快取 ⇒ rc=1 拒絕語。Developer-A 另在 `PlannerCliTest` 三支補顯式 `--at`（planner 零改動）。 |
| SD F1（P4，不立帳；引 DEF-200-411） | P4 | SD D2(c)／D3 | **Developer-C**：`session_brief.py` 新 `_install_command()`（絕對路徑＋本 checkout `.venv` 直譯器，無則 `sys.executable`；Windows 前綴 `& `；fail-open），`statusline_line()` 兩處文案改用；cwd=/ 貼上加 `--dry-run` rc=0；`test_session_brief.py` 三處斷言就地改＋新格。 |
| Architect A4 建議（不立帳） | — | Architect A4 | **Developer-C**：`--check` 末行印 `SDD FSM：current_state=SPEC_DRAFTING（狀態檔 …/FSM-STATE-AISDLC_SDD.yaml，mtime 2026-09-11T00:44:57+08:00）`；未設印「休眠（SDD_ACTIVE_VERSION 未設）」；只印原值、不判阻斷（阻斷態清單 SSOT 在 SDD 側，不複寫第二份）。 |

Developer-C 三件合計：舊碼副本跑最終版測試 `Ran 108 tests … FAILED (failures=9, errors=21)`→真樹 `Ran 108 tests in 0.432s OK`；11 個變異全被抓；整檔 `test_context_budget_guard` 773 OK(skipped=11)、`test_doc_loc_baseline_freshness_r60` 281／`test_platform_neutral_paths` 177／`test_subprocess_encoding_hygiene` 39／escape 12 皆 OK；`check_loc_budget` 四清單空（planner 740→743／750、session_brief 142→215／400）；`wc -l` `test_session_brief` 559→698（+139）、`test_wake_chain_halt_r278` 791→1032（+241）`[他包回報]`。

**DEF-200-086 原列描述（瘦身前逐字，供帳本索引列回查）**：
| DEF-200-086 | 2026-08-12 | R84 收斂（F4；`DEF-200-068` 第③條的實測） | `DEF-200-068` 宣稱三條已上 lint，實測只有兩條：③**讀 rc 接管線**零 lint——`waitform_hits()` 對「`sh -c 'exit 7'` 接 `tail -1` 再讀 rc」回 **0 命中**；唯一守該形態的 `lint_powershell_command.py` matcher 實查＝`PowerShell`（未含 Bash）⇒ **Bash／zsh 側零攔截器**，今天只有根 CLAUDE.md 鐵律六那段散文在守 | P1 | 併入 `waitform_hits()`（已讀 Bash 指令字串、平台中立），上線前先量假紅（母體一律 transcripts） | open（承接：R189 末次改派；出口＝Bash 攔截附自證，或 wontfix＋鐵律六劃界） |


**補列（複審鏡 B 訂正 10／20）**：

| DEF | P | 來源 | 處置 |
|---|---|---|---|
| DEF-200-286（結案；拆殘 → DEF-200-455） | P1→（殘餘 P2） | QA T4 unified log 對帳 | 一致性現查：`launchctl list` 三筆 `AutoSDD_Sentinel_{e1a2d13c,452cab3f,718ff654}` 與三份 armed stamp 一一對應、`launchctl print` rc=0×3（負對照不存在 label rc=113）；20:52 後重查一致。「mismatch 無自癒」那一半＝DEF-200-269 F4 relatch 已於 10-01 11:01:40 實戰自癒一次（10:53:43 launchd `removing service` 由未知行程觸發，缺口約 8 分鐘）⇒ 286 fixed。殘餘＝卸載者未歸因＋`_write_marker` 以 `"w"` 覆寫原始 `sentinel_armed` 事件 ⇒ DEF-200-455（P2，降級理由：自癒把損害界住在約 8 分鐘；根因未歸因）。對照：452cab3f 於 21:16:59 自行 disarm 並留下 bootout log（複審鏡 B）⇒ repo 自己的 bootout 路徑會留痕，佐證 10:53 那次非 repo 路徑 `[他包回報]`。 |
| DEF-200-456（新立，231 拆殘；**平台無關**——Mac launchd job 同樣跑 `--resume-tick` 而 abort，複審鏡 B 複核訂正） | P2 | 複審鏡 B F1／F4 | 手動 `--register-schtasks` 只寫任務書骨架、不寫續航狀態塊 ⇒ 排程醒來 `--resume-tick` 的 `parse_relay()` 回 None ⇒ `_abort_and_unregister`（真 CLI 任務書 RELAY 字樣 0 命中；in-process 真跑 `_resume_tick`（`_schtasks_remove` 替身）rc=1「❌ 任務書裡沒有狀態塊 ⇒ 拒絕動作」；HEAD 同形，`git log -S` 指向 R79／R95）。ADR-XPLAT-014 §2.2 L2／L3、A1／A4／A5、檔頭「尚未動工」與約束 1「整支刪除 `DEFAULT_AT_EXPR`」皆未同步——本輪保留該常數與 ADR A1「`.AddHours(` 零命中」衝突，偏離須回寫 ADR。承接含 ADR A6／F1 同步刷新；R190 承接 `[他包回報]`。 |

**修補棒 Developer-E（兩鏡 P3／P4 收口）`[他包回報]`**：E1 M1 次秒視窗——`quota_ledger.claim_once_within`（戳記 ≤1s 內到期就等換屆再搶；gate 只換呼叫端，`quota_gate.py` 仍 500／500）＋6 個搶輸者同刻換屆的短鎖（無鎖多行程 300 輪 {1:260, 2:40}、加鎖 {1:300}）；真 hook 端到端（隔離＋替身）修前 notice 1991B／urlopen 0 → 修後 notice 0B／urlopen 1。E2 補「贏家成功但重讀仍不可用（expired-window 邊界）」測試格（突變 `failed≡won` 下只有它紅）。E3 `await_winner` 期限改單調鐘（修前 `400 not less than 400`）。E4 判準④索引前掃：8 萬條管線 19291.7ms→575.8ms（HEAD 366.9）、65 案例差集 0、20000 筆 fuzz 差集 0。E5 FP 劃界 docstring、①～④ 兩處、`shell_command_corpus.py` 傳 tool（transcripts 67 種唯一／67 次，同 Developer-B）。E6 UTC＋(+14／−12) 時區格（拿掉 `.astimezone()` 本機 4 格紅、TZ=UTC 2 格紅）。E7 fail-open 文案、Windows 單引號形態、顯式 `--at` 標頭。E8 根 CLAUDE.md 速查表「reset 後自動重啟排程」列加註 DEF-200-456；`test_doc_loc_baseline_freshness_r60` `Ran 281 OK`。E9 `test_context_budget_guard test_quota_policy` `Ran 1073 OK (skipped=11)`、hook 193 OK、wake_chain＋session_brief 112 OK、a3_repeat 三組 0/6；`wc -l` 14415→14578、2873→2938、1032→1066、698→726。**兩鏡複核**：鏡 A `RECHECK: APPROVE-WITH-FIXES`（65 條＋15 萬 fuzz 差集空；`claim_once_within` 10 突變 8 殺 2 存活皆 P4；次秒視窗真 hook 4 平行 Agent rc 全 0、urlopen 恰 1；P3＝效能測試 2.0s 上界在慢 CI 太薄，建議比值 t(80k)/t(10k) < 24——收尾棒改）；鏡 B `RECHECK: APPROVE-WITH-FIXES`（23／23 訂正落實；F2／F3／F6 獨立重驗成立；新抓 456「只影響 Windows」不實已訂正）。

## 五、誠實劃界與未驗

- Windows 真機零觸及：R188〈八〉清單仍待掌舵者在 Windows 跑；SD 對 Windows 的所有結論皆為讀碼／前輪證據（R179／R181／R182／R186），非本輪實測。
- Q1「零重現」仍是小樣本（真工作窗 5 份）；DEF-200-451 的真實誤擋 2 筆是對逐字稿 `tool_result is_error` 的回溯，不是對那支並行 hook 的直接觀測（Architect 以 `durationMs` 推定，自陳「高度吻合的推論」）。
- DEF-200-450 的 launchd 真排程憑證要到明晨 `nightly_mac_20261002_020000.log`；今晨那份跑在修法前（預期 0 筆）。
- DEF-200-286 殘餘：卸載者未歸因（unified log 保存期有限，趁早取證）；armed stamp 住系統暫存（`/var/folders/…/T`，重開機即失）而非 `~/.autosdd/traces`（R188 題面不精確）。
- DEF-200-193 第 0 步只驗了窗數（67 個完整窗）與峰值，R95 §2.2 真正要的「per-window 超支」樣本未重建。
- SA 探針副作用：連打真端點兩度誘發 429，真實快取兩度被寫成 `rate_limited 100%`、兩個 agent 窗收到假 halt 通知；已於 20:50:53 自然復原、`--pace` 20:53:54 band=free、launchd 無新 job。**審查探針不得打真端點**自本輪起寫進〈八〉。
- 子 agent 數字一律 `[他包回報]`；子 agent 跑 `--check`／`--pace` 讀到的是父 session 的 sid（SA P4）。
- SD 探針在真實 feed 目錄留下 `~/.autosdd/context_feed/r189-sd-synth.json`（SD 自述 0 污染，複審鏡 B 實查在）：主控收尾已刪（`ls | grep -c` 0）。
- 探針逐字稿**未刪**：主控嘗試刪除本輪 5 份探針（根目錄 ca169496〔只回 OK〕；AutoClaude 目錄 fa2b3ad2〔只回 OK〕、8cfcb3ed／3e9531f5〔韓文探針〕、16d96c53〔只回 OK〕）被 auto mode 分類器以「Session Transcript Tampering」拒絕，不繞過；之後任何逐字稿普查母體請排除這 5 個 session（首則 prompt 皆為探針字樣，機械可辨），刪不刪由掌舵者決定。R188 保留的 407fd30d／7b2b065f／8d5ce015 不動。

## 六、收尾親驗（主控親跑，最後一次程式碼寫入之後）

- **帳本**：`check_defect_log_crossref.py` rc=0；`--unresolved-count` `未結列數＝36／全部 157 列`（R188 收尾 37 → 36：086／231／286 結案、455／456 新立 open、451～454 新立即結 ⇒ 淨 −1，**不需** `AUTOSDD_NET_RATCHET_OFF`）；`archive_defect_log.py --check` rc=0；`check_handoff_carriers.py` rc=0；`test_defect_id_reference_integrity test_check_defect_log_crossref` OK。帳本列位元組（皆 ≤700）：451＝692、452＝649、453＝675、454＝669、455＝683、456＝697；086 瘦身成索引列（原描述逐字見〈四〉末）；231／286 狀態欄改寫；193／197／198／199／242 承接欄改 R190（197 列只剩 4 bytes 餘裕，探針規範落本檔〈八〉）。主控第一版 456 列「只影響 Windows」不實，依複審鏡 B 複核訂正為「平台無關」。
- **收尾棒 Developer-F `[他包回報]`**：護欄行數棘輪——本輪四測試檔毛增 +1156（效能測試改比值後 +1164）→ 搬 64 處史料（451 行逐字入本檔〈九-F〉，淨減 371；四檔剝 docstring 後 AST 比對 SAME×4）→ 對 HEAD 累計 `110563 → 111383（+820）`；回歸鎖軌申報 309、主軌 511 ≤ 523（實測 +832 綠、+833 紅，餘裕 12 行）；凍結表 `test_block_destructive_git_r83` 2663→2851、`test_context_budget_guard` 14139→14302、`test_session_brief` 559→726、`test_wake_chain_halt_r278` 791→1066、`test_windowsapps_guard_cross_consistency` 2092→2096、`test_adr_xplat001_c1c2_lock` 8955→8978；凍結前綴 319→320；`_REPIN_LOG_HISTORY_SHA256` `a2fe4b152479…`→`c326e2f45237…`；分桶 prose 4454→4194（凍結 4311）、guard_self 3073→3031。到期義務：`(190, 522)` 不在本輪；`_PHASE2_REVIEW_LOG` 已逾期，追加 `(189, "[提案]")` 一列（內容＝重新登記 R129 既存提案的未決狀態、不對 ADR-XPLAT-013 方向 (c) 做新判斷）——**主控親讀後背書**。效能測試改 `t(80k)/t(10k) < 24 且 t(80k) < 10s`（線性 hook ratio=6.8 綠；鏡 A 平方版 19507.9ms ratio=59.0 紅）。超出白名單三處主控**接受**：`test_windowsapps_guard_cross_consistency.py` +4（E7(a) 單引號形態觸發裸 python 註冊表）、`CrossPlatform_R145_Scan_Findings.md` +4（guard-total 第二站點，缺它 c1c2 報 [未登記]）、`test_wake_chain_halt_r278.py` 一個 docstring 補受測模組字面（prose 桶分類修正）。
- **表② 回填 `[他包回報]`**（`tools/lib/clean_venv_carrier.py`，樹外乾淨 venv、Docker 未啟動、探針 psycopg2／sqlalchemy ABSENT、CARRIER_RC=0、venv 已自刪）：`cigate-v030` 1963→1979（指紋 `4d902e4a743a`→`6d46814f9084`），其餘三格不變（Developer-D 所見 autoclaude 漂移在 Windows 欄、非 macOS 欄）；`sync_onboarding_baselines.py --check-snapshot` rc=0。
- **根層全套 `[他包回報]`**：第一次 `REAL_RC=1` 恰 1 紅（windowsapps 裸 python 註冊表，E7(a) 單引號形態造成）；補註冊後第二次（主控親讀 `root_full2.out`）：`✅ unittest 數量下限釘選通過：發現 4960 個測試（下限 4876）`、`[cpu_budget] root-unittest workers=9`、`S=813.1s … slot 利用率=99.7%｜最長單位：test_dev_start 44.0s`、`[skip census] tools/tests@darwin 共 47 支：platform=47／…／untagged=0`、`[M6 id 集合] … ✅`、`✅ 真實 TEMP 圍籬 … 零變動（前 2／後 2 份）`、**`REAL_RC=0`**。
- **形態（主控親跑）**：`git diff --check` rc=0；`git diff --stat` 21 檔 `2135 insertions(+), 578 deletions(-)`；`wc -l AutoClaude/CLAUDE.md`＝400；guard-total:R189 落 `AutoSDD_improving_112.md:163` 與 `CrossPlatform_R145_Scan_Findings.md:766`（兩站點同文）。
- **清理**：`~/.autosdd/context_feed/r189-sd-synth.json` 已刪（`ls | grep -c` 0）；本輪 5 份探針逐字稿**未刪**（auto mode 分類器拒絕，見〈五〉）；Docker 未啟動、暫存 venv 已刪、無殘留行程（Developer-F）；launchd 哨兵 `AutoSDD_Sentinel_e1a2d13c-…` 由 hook 自動武裝（20:23:45，正常 28 回合判準），未動。

## 七、根層全套、push 與雲端驗收

（push 後回填）

## 八、交棒／掌舵者側待辦

### Q5 評估（硬上限輪的結果；先講依原判準的答案，再講選項）

- **依 R188〈八〉原判準：未收斂（0／2）。** 規則 2 後半（四個活體探針）全綠 `[他包回報]`：Q1 新視窗黑盒零阻斷、Q2 主控第 1 個工具呼叫即現查（主控親測）、Q3 `--check` 差=0、Q4 `--status` installed 且相符。規則 2 前半不成立：家族內**新發現** P≤2＝**2**——DEF-200-451（P2；SA 評 P3、Architect 評 P2，主控採 P2：它讓額度決策被誤執行（rc=2 擋 Agent／Workflow），與 DEF-200-437「遲滯狀態多擋一格」同類；曝光率低與模型兩次都讀對是「傷害小」不是「等級低」）與 DEF-200-456（P2；手動 `--register-schtasks` 排出的工作醒來不做事，複審鏡 B 挖出；平台無關）。計數規則明寫：「HEAD 既有」不是排除條件（R187～R188 的 445／449／450 也都是既有），只有「既有 open 列的新證據拆殘」不計——DEF-200-455 即此型（286 的新證據，P1→P2 因 relatch 自癒把缺口界住約 8 分鐘）。另 DEF-200-197／198／199 三筆**家族內 open P1**（197 本輪活體重演）仍在：五問家族還有有名有姓的未結結構性問題。
- **「規則 3：R189 硬上限、不開第 3 輪」是主控於 R188 採納 SA 建議自訂的停損規則，不是掌舵者指令**；掌舵者本輪原話是「選Ａ，還沒收斂就繼續！」。依掌舵者常駐指示，未收斂就該繼續。主控在草稿第一版曾建議「修憲判準②讓 R188／R189 算收斂」——複審鏡 B 指出那是看到結果後為 451 量身改規則，且四個活體探針（haiku「只回 OK」）結構上碰不到 451～454 這類缺陷，不能當收斂證據。**主控撤回該建議。**
- **十一輪的結構性讀法**：每輪四方審計都仍挖到家族內新缺陷，子軸各不同——R187 P2（445，配速契約目錄分家）、R188 P3（449／450，hook 出聲／nightly 取證）、R189 P2×2（451 額度補量 M2＋M1，單一 hook 即可觸發、主控本場 20:17:24 親歷 M1；456 喚醒鏈手動路徑）＋P3（452／453 配速措辭、454 SDD 橫幅）。**誠實說**：這些與 Pacing 五列（193／197／198／199／242）沒有一筆重疊，不能宣稱「Pacing 沒修所以審計挖不完」；能說的是：帳本現有家族內 open P1×3（197／198／199）＋P2×2（455／456）有名有姓，修復它們是確定有產出的事，而再開一輪審計能不能零新發現沒有人能保證。
- **誠實劃界**：Windows 真機自 R187 起三輪零觸及，判準②也沒有平台條款——Mac 連兩輪探針全綠不等於 Windows 全綠；本輪修法在 Windows 的呈現全未驗；DEF-200-450 要 2026-10-02 02:00 那晚的 launchd 憑證（寫本檔時尚未到）。成本〔主控估算，來源＝本場 Agent 工具回報的 subagent_tokens〕：四方審查 440k＋488k＋665k＋566k ≈ 2.16M、四棒 Developer 560k＋460k＋694k＋371k ≈ 2.09M、修補棒 675k、兩鏡初審 498k＋630k 與複核 580k＋743k ≈ 2.45M，合計 ≈ 7.4M，全 Sonnet；主控 Fable 另計。

### 掌舵者裁決題（二選一；主控推薦 A）

- **A（推薦）：繼續，下一輪改「修復輪」。** R190＝單人串行修 Pacing 落地包（DEF-200-193／197／198／199／242）＋DEF-200-455／456，**且 Windows 真機驗收列為 R190 必做項**（不再「都不急」）；R191 四方家族級審計＝驗證輪。判準②**不改**（收斂＝連續 2 輪家族內零新 P≤2 且探針全綠），R189 之後計數從 0 起算 ⇒ **最快 R192 才收斂**：至少再 3 輪、其中 2 次四方審計（每次 ≈2.2M Sonnet）＋1 次修復輪。理由：帳本裡有名有姓的 open P1／P2 是確定有產出的工作；審計輪的零新發現沒人能保證，但沒修就審一定不會零。
- **B：現在停五問系列。** 帳本未結列（36）照常由結案輪驅動（197／198／199／455／456 仍會被修，只是不再以「五問」命名、不再開四方驗證輪）；Windows 清單由掌舵者自行跑。成本最低；「未收斂」就是事實，不塗綠。兩案的差別只在要不要再花 2 次四方審計買「連續 2 輪零新發現」這個統計信心。

### Windows 11 掌舵者清單（R188〈八〉五條仍有效；本輪零觸及；**選 A 則為 R190 必做項**）

- 照 CrossPlatform_R188_SessionGate_Hook_Voice_Evidence.md〈八〉五條 PowerShell 指令跑一次（Q4 的憑證是第 1 條 `install_statusline.py --status` 的 `installed`／`matches_current_checkout`，不是看簡報——簡報走 additionalContext 人看不到）。本輪新增的可貼安裝指令只在模型轉述時有用。
- 231① 驗時刻：`& $py (Join-Path $repo 'tools\session_resume_planner.py') --print-schtasks-command`：有實測 resets_at 時應印 `-At '<本機時間>'`、沒有時應拒絕而不是印 `AddHours(5)`。🔴 **這只驗「醒在對的時刻」**：手動路徑排出的工作醒來仍會因無狀態塊 abort 並自我解除（DEF-200-456，HEAD 既有），不可據此宣稱「會自動續跑」；要自動續跑用 `--arm-endurance`／`--arm-sentinel`。

### Mac 側

- 2026-10-02 02:00 nightly：`grep -nE 'git context:|SAMPLE VALIDITY:|真實 TEMP 圍籬' AutoClaude/logs/nightly_mac_20261002_020000.log` 應各 ≥1（DEF-200-450／445 憑證）。
- `~/.zshrc:9` `export SDD_ACTIVE_VERSION=0.30`：維持 R188 建議，使用者層檔案，本輪未動。

### 下輪的機械義務（收尾棒提醒，主控記名）

- 護欄行數棘輪：R190 須兌現到期義務 `(190, 522)`（上限由 523 步進到 522）；R189 主軌 +511 為正 ⇒ 連續上升計數 1，R190 可再正一次，**R191 主軌必須 ≤ 0**（淨減法：刪／合併等量舊鎖檔或搬史料；承接列＝DEF-200-207，ADR-XPLAT-013 治理面）。
- `_PHASE2_REVIEW_LOG` 的 R129 既存提案（ADR-XPLAT-013 方向 (c) 觀測→阻斷）本輪以 `[提案]` 重新登記未決狀態；下一次合法出路只剩 [提案]／[落地]，主控須排定四方複審（承接列＝DEF-200-207）。

### 本輪未做（不塗綠）

- Pacing 落地包 DEF-200-193／DEF-200-197／DEF-200-198／DEF-200-199／DEF-200-242：整包改派 R190 單人串行（同持有面 `quota_policy.py`／`quota_meter.py`／`quota_gate.py`／PRD；PRD v2.1.10 已落款、不需新修憲，但 W0～W6 七批實作零落地；193 第 0 步現查 `quota_burn.jsonl` 354 列／67 個完整窗 ⇒ 足併包，per-window 超支樣本未重建）。本輪 429 事件是 197 的活體重演。**審查探針打真 usage 端點無規範**（本輪 SA 誘發兩次 429 地板寫入、DEF-200-198 曾記載同型）：規範自本檔起生效——探針一律隔離 `AUTOSDD_QUOTA_CACHE_DIR`＋TMPDIR＋urlopen 替身、禁打真端點；帳本 197 列已滿（696 bytes）故規範落本檔不落列。
- DEF-200-455（286 拆殘：卸載者歸因＋stamp append-only）與 DEF-200-456（231 拆殘：手動路徑狀態塊＋ADR-XPLAT-014 §2.2 L2／L3、A1／A4／A5／A6、F1 同步刷新、檔頭「尚未動工」改寫、`DEFAULT_AT_EXPR` 整支刪除與 A1 零命中；平台無關）：改派 R190。
- SD 的 (iii) repo 層 statusLine（唯一 0 步驟方案，須重開 R158 A3 並先做 Windows 最小親驗）與 (ii-報) dev_start 只報不寫：掌舵者裁決題，本輪不做。
- P4 觀察（不立帳）：`schedule_backend.py:407` 註解仍提 `DEFAULT_AT_EXPR`、`--at ""` 空字串行為（複審鏡 B）；`claim_once_within` 的 `sleep(left)` 無 +0.05 緩衝與 `stale_after=3600` 孤兒鎖回收無測試（複審鏡 A）；454 橫幅三處邊緣（payload 無 session_id 時橫幅說「必須」而 hook 放行；他窗且本窗 ≥95% 首句「照常放行」為假；84,999 進位顯示）；`schtasks_trigger` 的「觸發時刻已過」分支為死碼；階段二 AST 擴充判準、`claude_md_freshness` rc=2 不讀 `stop_hook_active`、PostToolUse rc=2「BLOCK」殘留 3 檔 4 站（R188 已登記）本輪未動。

## 九、搬遷史料（Developer 各棒以 append 模式落此；原位置以一行指針代替）
### 九-A　Developer-A（額度配速家族 DEF-200-451／452／453）搬遷史料與修前修後實測

原位置（`tools/lib/quota_ledger.py::await_winner`、`quota_gate.py::settled_quota`、`quota_messages.py::degraded_detail`）只留一行指標指到本節；以下是被擋在程式外的史料。凡標 `[他包回報]` 者來自 Architect 報告 A3（本包未重跑，不得當成本包的實測）。

**一、DEF-200-451（P2）補量名額的輸家被當「量不到」**

- 機制（讀碼）：`claim_refresh_slot()` ＝ `quota_ledger.claim_once()`（`O_CREAT|O_EXCL`），每個 TTL（`QUOTA_CACHE_TTL_SECONDS`＝180）只有一人搶到；贏家去 `refresh_quota_blocking()`（HTTP 逾時上界 `QUOTA_SYNC_TIMEOUT_SECONDS`＝4）。輸家此前**沒有任何分支**：直接以過期快取判定 → `degraded_cap=2` ⇒ 平行 Agent 第 3 個起被擋（rc=2）、PostToolUse 印假警報。原子性是對的，缺的是「輸家怎麼辦」。
- 端點 RTT 三次實測 0.33／0.36／0.41 秒（`refresh_quota_blocking` 修前 docstring 已有此數字；本包未重量）。
- `[他包回報]` Architect A3.3：真實痕跡 159 筆（取證 21:03）裡 stale-cache 50＋expired-window 7＝57 筆全帶固定「取數失敗」，而零筆同步取數失敗痕跡；真實逐字稿 2 筆誤擋（UTC 2026-09-19T17:02:33Z `PreToolUse:Agent` 已 187s；UTC 2026-09-20T16:38:36Z `PreToolUse:Workflow` 已 180s，兩筆都落在 TTL 邊界上）。09-19 那筆前情：17:02:22 的 `--pace` 還印「現在可派 1 個（cap=4）」，11 秒後快取跨 TTL，第 4 個 Agent 就被擋。
- 修法：`quota_ledger.await_winner(stamp, budget, ready)`＝戳記年齡 < 預算（贏家還在飛）才以 50ms 步進輪詢 `ready()`，剩餘時間以 `min(budget, left)` 封頂；`quota_gate.settled_quota(won)`＝補量那一步之後的重讀（贏家不等、輸家等）；hook 路徑與 `pace_state()` 兩個站點都接。零 token、零新增 HTTP（只重讀贏家寫下的快取）。
- 「TTL 剛跨過時退化值蓋掉 11 秒前剛量到的寬鬆值」（A3.3 第 2 點）：由同一機制自然涵蓋——輸家等到贏家的新讀數後才判定，沿用新讀數而非退化值；贏家真失敗時落 unmeasured 仍是 SA-B4 的設計（過期值不採信），不另做。
- 修前修後（本場實測；harness＝Architect `a3_repeat.py` 的複本，隔離 HOME／TMPDIR／AUTOSDD_TRACE_DIR、`urlopen` 替身 RTT 0.4s、假 `security`，對真實 usage 端點零請求；修前＝把三支 quota lib 還原成 HEAD 的副本，輸出檔 `scratchpad/r189/devA/a3_repeat_BEFORE.out`／`a3_repeat_AFTER.out`）：
  - 修前：R4（3 平行 PostToolUse Bash×6）`runs_with_false_alarm=6/6`；R5（4 平行 PreToolUse Agent×6）`runs_with_rc2=6/6 total_rc2=6`、`runs_with_false_alarm=6/6`；R5b（2 平行×6）`runs_with_rc2=0/6`、`runs_with_false_alarm=6/6`。與 Architect 原數字逐筆相同。
  - 修後：R4／R5／R5b 皆 `runs_with_rc2=0/6 total_rc2=0; runs_with_false_alarm=0/6`；18 輪每輪 `urlopen_done=1`（贏家恰打一次）。
- 鎖：`RefreshSlotConcurrencyTest::test_a_losing_hook_never_reads_a_refresh_in_flight_as_unmeasurable`（4 行程 barrier ＋ 0.4s 慢替身；修前 `['0','0','0','2'] != ['0','0','0','0']`）、`RefreshSlotConcurrencyTest::test_a_loser_waits_only_while_the_winner_is_in_flight`（等待的條件與上界，時鐘注入）、`RefreshSlotLoserWaitsTest`（同行程版，贏家以執行緒模擬；含 PostToolUse、有界性、`pace_state`）。

**二、DEF-200-452（P3）`unmeasured` 被印成「沒有 reset 可以等」**

- 修前渲染逐字（`[他包回報]` A3.4／C-10，本包在修前副本上以 `--pace` 同型輸入重現過 `提額` 字樣）：`⏳ 這一條**沒有 reset 可以等**（例：月度支出上限）；只有人去提額：https://claude.ai/settings/usage ⇒ 這道節流不會自己解除。`——與同一輸出另一行「重量一次即可，不是取數壞掉」自相矛盾。
- 成因：`binding_resets_at()` 在 `binding is None` 回 `None` → `reset_branch(None)` ＝ `escalate` → `reset_horizon_phrase()`／`throttle_horizon_line()`；那句是為「量到的軸沒有 reset（spend）」寫的。
- 修法：`throttle_horizon_line()` 對 `band == BAND_UNMEASURED` 另走 `UNMEASURED_HORIZON_LINE`（等下一次補量或現查 `--pace`，與 reset 無關），不得落入 `reset_branch(None)`；`--pace`、Agent／Workflow 節流訊息共用這一個出口。

**三、DEF-200-453（P3）`note_degraded` 固定寫「取數失敗」並丟掉 `state.reason`**

- 修前：`quota_gate()` 對所有不可用來源硬寫「取數失敗，且逐字稿裡沒有未復原的撞線可以當地板」，stale-cache／expired-window 的原句（本來就寫「不是取數壞掉」）被丟掉；PostToolUse 退化通知沒有「收斂型工具不受影響」澄清（SessionStart 有 `rc2_clarify`、halt 有 `halt_convergent_clarification`）。
- 修法：`quota_messages.degraded_detail(reason, refresh_failed)`——本行程補量真的失敗（`refresh_quota_blocking()` 回 False）才說「取數失敗」，否則引快取自己的 reason；後半句「且逐字稿裡沒有未復原的撞線可以當地板」恆真所以保留。本行程補量失敗時第二則 `source=stale-cache` 通知若引「不是取數壞掉」會與第一則「同步取數失敗」同輸出自相矛盾，所以這條路維持原句（`QuotaDegradationIsAudibleTest::test_each_failure_shape_names_itself` 仍要兩個 source 都在痕跡裡）。
- PostToolUse 澄清句：`degraded_convergent_clarification()` 取 `halt_convergent_clarification()` 的「…不受影響」前半句（平台分支與工具清單只有那一個家），**不照抄**後半「只有扇出型…暫停」——量不到是收緊到 `degraded_cap`，不是停用；PreToolUse 不借用（被評估的就是扇出呼叫本身，「已正常執行完成」是假話）。
- 全文組字（`degraded_message()`）由 `note_degraded()` 搬到人話面 `quota_messages`；閂鎖、痕跡、發射仍在 `quota_gate`。

**四、LOC 計價（`check_loc_budget.py`，本場實測）**

- `quota_gate.py`（`guardrail_hub`，預算 500）：修前 499 → 修後 500（餘裕 1 → 0；三處補償：全文組字搬出 −4、兩個早退併成一個 −1、`unmeasured`／`failed` 併行初始化 −1）。`quota_ledger.py` 147 → 160、`quota_messages.py` 320 → 340（皆在 `guardrail_lib` 400 內）。`absolute_violations`／`tier_violations`／`special_violations`／`root_tools_violations` 四清單皆空，`rc=0`。
- count_loc 只計斷言行（敘事與空白免費）：本節搬遷的是敘事，對該計價零影響；`quota_gate.py` 的餘裕靠搬「程式」（組字函式）換來，不是搬史料。

### 九-C、Developer-C 搬遷史料（DEF-200-231①；`tools/session_resume_planner.py`）

`DEFAULT_AT_EXPR` 常數上方的 R79 立案註解，改動前逐字如下（原位已改為現行說法並指向本節；常數本身刻意留著，
因為 ADR-XPLAT-004／005／014、`ResetArithmeticTest`、`schedule_backend`／`quota_limits` 的註解都以這個名字指稱
「假設 5 小時」缺陷，刪掉會讓這些引用變成幽靈符號）：

```text
#: 預設觸發時刻運算式。留成 PowerShell 運算式而不是寫死時間：使用者要改成 CLI 印的
#: reset 時間時，改的是同一個字串，印出來的與真的註冊出去的**不會分岔**。
#:
#: 🔴 R79：這個預設**只在 `--register-schtasks` 手動路徑上還算數，且它是猜的**。
#: `--arm-endurance` 一律不使用它——那條路的觸發時刻只能從逐字稿觀測（見
#: `guard.parse_reset_at` 的 WHY：全庫 7 個相異 reset 值沒有一個落在 5 小時格點上，
#: 本檔實測 `3:50am`／`12:20pm` 這種值就是反證）。把「當下機器的偶然事實寫成常數」
#: 是本 repo 反覆判過的形態（R73 同型）；此處保留它只是為了不動既有手動路徑的行為，
#: 並在下面這個常數旁把它的地位講清楚：**它不是 reset 時刻，是一個預設猜測**。
```

同一改動中被換成現行說法的另兩處（逐字）：`schtasks_command()` 標頭「`{at_expr}` 是**猜的**，不是 reset 時刻。
要正確的觸發時刻請改用 --arm-endurance（它從逐字稿原文觀測，見 ADR-XPLAT-004 §2.1）；還沒撞線就想掛著請用
--arm-sentinel。」；`_ps_single_quote` 旁註解「（預設值 `(Get-Date).AddHours(5)` 就是）」。兩者在 `--at`
預設改為 `None` 之後都已不是真話（缺 `--at` 時觸發時刻取自額度快取的實測 resets_at，解不出就拒絕）。

**五、附帶（Developer-A）：他棒 planner 修法造成 `test_context_budget_guard::PlannerCliTest` 三支紅，已在測試側補 `--at`**

- 現象（本場實測）：他棒同輪的 `session_resume_planner.py`／`session_brief.py` 修法（`--at` 預設改 `None`；省略時取額度快取實測 reset、解不出即拒絕，rc=1）落地後，`PlannerCliTest` 的 `test_schtasks_command_is_printed_never_executed`／`test_the_printed_task_name_is_per_session_not_the_fixed_default`／`test_it_never_claims_a_schedule_was_created` 三支以 rc=1 紅（stderr：「未給 --at，額度快取也給不出可等的 reset 時刻（額度快取不可用：no-cache）」）。
- 歸因實驗（scratch 副本，repo 零改動）：副本內只把他棒的 `session_resume_planner.py`／`session_brief.py` 還原成 HEAD、其餘保留本包修改 ⇒ `PlannerCliTest` `Ran 9 tests … OK`；故非本包的 F1／F2／F3 造成。
- 處置：這三支測的是「印出的指令內容」，與觸發時刻的來源無關 ⇒ 三處呼叫顯式帶 `--at "(Get-Date).AddHours(1)"`（常數 `_AT_EXPLICIT`），planner 零改動。省略 `--at` 的新行為不在這三支的射程，由 `test_session_brief` 側的測試負責。處置後 `PlannerCliTest` `Ran 9 tests … OK`。

訂正（Developer-C，同節上一段）：上段「刪掉會讓這些引用變成幽靈符號」是一般語意的**懸空引用**，不是全庫「幽靈符號鎖」
（`TestR78GhostSymbolClaims`）會抓的東西——該鎖的 `_SYMBOL_CLAIM_RE` 形狀刻意只認前導底線的 ALLCAPS、`Test*`、
`test_*` 三種反引號識別字，`DEFAULT_AT_EXPR` 不在其內（scratch 副本實測：刪常數前後，該鎖輸出中含此名字的指控行數
皆為 0）。保留常數的依據只有一個——掌舵者任務書「有引用就保留」，且確實查無任何程式碼 import（引用面＝
`test_context_budget_guard.py` 兩處 docstring、`schedule_backend.py`／`quota_limits.py` 各一處註解、ADR／裁決書／
交棒書數處）。ADR-XPLAT-014 §2.2 約束 1 原訂「整支刪除」，是否在階梯全數落地時刪，留待掌舵者裁決。

### 九-E　Developer-E（修補棒：DEF-200-451 次秒視窗／DEF-200-086 判準④效能與劃界／DEF-200-231 時區鎖／簡報安裝指令）搬遷史料與實測

原位置（`quota_ledger.py::claim_once_within`／`await_winner`、`quota_gate.py::claim_refresh_slot`、`block_destructive_git.py::_rcmask_filter`）只留說明與指標；以下是被擋在程式外的史料與本場實測（腳本與原始輸出在 scratchpad `r189/devE/`；全程隔離 HOME／TMPDIR／TRACE_DIR、urlopen 替身，對真實 usage 端點零請求）。

**一、DEF-200-451 次秒視窗（單一 hook 即可觸發）**

- 機制：名額戳記 mtime 是 ns 且在取數**之前**落款，快取 `measured_at` 截斷到秒且在取數**之後**落款；兩者落在同一牆鐘秒時，快取比名額早 0～0.8 秒過期。視窗內「快取已 stale、名額仍被持有、沒有人在飛」，`await_winner()` 只等在飛的贏家（戳記年齡 < 4 秒），此時戳記年齡約 179.2～180 秒、直接落「量不到」。
- 修法：`quota_ledger.claim_once_within()`＝戳記將於 `grace`（1.0 秒＝該視窗的結構性上界，非調參）內到期就等到期再搶一次；搶到者自己補量（`failed` 語意不變），搶輸者走在飛輸家的原路。仍每個 TTL 一次補量（等的是換屆）。
- **驚群與鎖**：一群輸家在同一刻醒來搶時，`claim_once` 的 stat→unlink→create 之間可被插隊。6 個同時搶換屆（ttl 1.0 秒、戳記 0.12 秒後到期、隔離暫存目錄）：無鎖版執行緒 400 輪 `{1: 379, 2: 21}`、多行程 300 輪 `{1: 260, 2: 40}`（兩個補量者＝同一 TTL 打兩次端點）；最後一搶改在短鎖（`with_lock`，`stale_after=1.0`／`max_wait=1.5`）內：執行緒 400 輪 `{1: 400}`、多行程 300 輪 `{1: 300}`。`RefreshSlotConcurrencyTest::test_the_final_claim_after_the_wait_runs_under_the_short_lock` 是確定性的牙（搶的當下鎖檔必須在）；驚群版的選舉測試對「拿掉鎖」只有機率鑑別力，只作端到端不變式。
- **端到端（真 `context_budget_guard.py` 子行程、PostToolUse Bash、單一 hook、快取 measured_at 已過 TTL 0.2 秒）**：修前鏡像（只把 quota_gate／quota_ledger 換成修前版）戳記差 0.5 秒到期 ⇒ `rc=0 elapsed=0.03s notice_bytes=1991 urlopen_done=0`、痕跡 `stale-cache`（即本場親歷的假警報）；修後 ⇒ `rc=0 elapsed=1.01s notice_bytes=0 urlopen_done=1`、零痕跡（多等的 0.55 秒＝等換屆，加補量 0.4 秒替身 RTT）。對照：戳記 100 秒前 ⇒ 修前修後皆 `elapsed=0.03s notice_bytes≈2000 urlopen_done=0`（不在視窗內＝原行為）；戳記 181 秒前／無戳記 ⇒ 皆 `elapsed≈0.45s notice_bytes=0 urlopen_done=1`（一般贏家，未變）。
- `await_winner` 期限改單調鐘：複審鏡實測牆鐘等待中途倒退 1 小時 ⇒ 72,080 次輪詢對正常 81 次（`[他包回報]`）；本包 `test_a_wall_clock_step_back_cannot_unbound_the_wait` 修前 `AssertionError: 400 not less than 400`、修後綠。

**二、DEF-200-086 判準④：成本線性化與劃界**

- 成因：`next((t for _s, t in parts[i + 1:] if t.strip()), "")` 每個濾器命中複製一次整串尾巴，n 條管線 O(n²)；`itertools.islice` 要走過前 i 項，同樣平方（複審鏡實測無效）。改索引前掃（只掃到第一個非空段，各命中的掃描區間互不重疊 ⇒ 總成本線性）。
- 同一輸入 `'a | tail -1; ' * n`（毫秒；HEAD＝尚無判準④）：n=20,000 HEAD 91.8／修前 1181.3／修後 160.5；n=40,000 183.4／4359.2／318.2；n=80,000（約 1MB）366.9／19291.7／575.8。測試 `TestIronLaw6RcMaskedByPipeScalesLinearly` 修前 `AssertionError: 19.420729582896456 not less than 2.0`。
- 判決不變：鏡 A 的 65 條邊界指令對修前／修後 hook 逐條比對 `cases=65 differing_verdicts=0`；另以 53 種殼 token 隨機拼 1～16 個、N=20,000 比對兩版 `differing_verdicts=0`。
- 誤擋方向的劃界（寫進 `waitform_hits` docstring）：`sort -c`（未排序回 1）、`awk '{exit 3}'`、`sed '/x/q1'` 這類濾器以 `exit` 傳有語意 rc 者命中；出口＝行內 `# waitform-ok: <WHY>` 或改讀 `${PIPESTATUS[0]}`；transcripts 母體零例。
- 普查探針改把逐字稿**工具名**帶進判準（hook 對 PowerShell 不判④）：`--summary`／`--corpus transcripts --summary` 改後 transcripts 母體 5176 筆／5001 種唯一、`waitform` 命中 67 種唯一／67 次（`run_in_background=true` 281 種唯一／290 次、命中 3／3）、tracked 母體 5695 筆／5337 種唯一、`waitform` 10／10、`git` 203 種唯一／220 次；同一批逐字稿列分工具 `per_tool={'Bash': 5176}`，預設工具與真實工具的命中數 67 對 67（差 0）——本機母體沒有 PowerShell 列，改動只在含 PowerShell 的母體（Windows 機）才會改變數字。

**三、DEF-200-231 時區鎖與簡報安裝指令**

- `schtasks_trigger()` 的 `.astimezone()` 此前沒有任何測試釘住（夾具用本機 offset 字串）。新測試用 UTC（`+00:00`、`Z`）加固定的非 UTC offset（+14／-12）：本機時區至多等於其中一個，任何時區的機器上拿掉 `.astimezone()` 都至少一格紅——本機（+0800）4 格皆紅、`TZ=UTC` 下 2 格紅；該變異此前在兩支測試檔共 108 測全數存活。
- `_install_command()` 的 Windows 形態改 PowerShell 單引號字串（雙引號內 `$`／反引號會被內插或跳脫而靜默改寫路徑；內嵌單引號寫成兩個）；POSIX 維持雙引號。fail-open 退回的提示改為裸指令（外層文案已說「貼上即安裝；先預覽就在尾端加 --dry-run」，退回提示不得再自帶 `--dry-run`）。`--print-schtasks-command` 標頭只說這次真的走的那條路（依據句住 `session_brief.trigger_basis()`）。

**四、LOC 與桶（本包量到的數字）**

- `check_loc_budget.py --json` 四個違規清單皆空、rc=0。`quota_gate.py` 500／500 不變（只換一個呼叫端）；`quota_ledger.py` 160→177、`session_brief.py` 215→222、hook 643→644、`shell_command_corpus.py` 154→158、planner 743→743。
- 四個測試檔 `wc -l`：`test_context_budget_guard.py` 14415→14578（+163）、`test_block_destructive_git_r83.py` 2873→2938（+65）、`test_wake_chain_halt_r278.py` 1032→1066（+34）、`test_session_brief.py` 698→726（+28）；分桶（chunk／exclusive）本包貢獻：`prose` +34（全在 `test_wake_chain_halt_r278.py` 的 `RegisterSchtasksTimeIsObservedNotGuessedTest`——該類別因提到一次根 CLAUDE.md 整類歸 prose）、`guard_self` 0、`selfcontained` +205、`root_infra` +48、`mixed` +3。

### 九-F　Developer-F（收尾棒）搬遷史料（護欄層行數棘輪重釘的淨減法；逐字原文，原位以一行指針代替）
以下每一節是從 `tools/tests/` 四支鎖檔搬出的 docstring 尾段／註解塊**逐字原文**；搬遷只動註解與 docstring，不動任何可執行行（`ast` 比對與行為測試見〈六〉）。節號 §N 與原位指針一一對應。

#### §1　`test_block_destructive_git_r83.py`　comment L74-85（搬出原 L74-85，12 行）
```text
# 🔴 模組級釘住（本輪缺陷修復）：`is_foreign_tree()`（`.claude/hooks/
# block_destructive_git.py`）以 `os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()`
# 決定專案根。本檔多支測試直接呼叫 `G.destructive_git_hits()`／`G.is_foreign_tree()`
# （不經 `run_hook()` 的 subprocess——那條路徑另外用 `cwd=str(_REPO_ROOT)` 釘死子行程，
# 不受本段影響），因此在同一行程內執行時會共用**呼叫者**（`tools/run_root_
# unittests.py`、`Start-Job` 等驅動器）的 cwd。呼叫者 cwd 一旦落在 repo 外，root 就
# 解析成別的目錄，讓「檔案系統根含著專案根」一類判準靜默算錯——從非 repo 目錄單獨跑
# 本模組時，字面固定 9 支測試同時變紅。生產路徑（Claude Code 呼叫 hook）一律會設
# `CLAUDE_PROJECT_DIR`，這不是 hook 的缺陷，是本檔測試對呼叫者 cwd 的隱含依賴。
# 釘在模組層級而非逐一補在受影響的 class：本檔沒有任何測試依賴 `CLAUDE_PROJECT_DIR`
# 缺席時的 fallback 行為（已逐一核對既有 setUp／inline patch 慣例），個別測試裡既有
# 的 `mock.patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": ...})` 疊在這層之上值不變。
```

#### §2　`test_block_destructive_git_r83.py`　TestDestructiveFormsAreBlocked.test_a_backslash_line_continuation_does_not_smuggle_it_past (doc L174-181)（搬出原 L175-181，7 行）
```text

        WHY 這條值得一支具名測試：`_SEP_RE` 把 `\\n` 當語句邊界，所以在折回去之前，
        立案的那條指令只要在 `git` 後面換行就整條漏擋——**繞過方式不需要任何巧思，
        把長指令排版一下就會自然發生**。獨立驗證輪實測：本機 60 份逐字稿的 4,087 條
        shell 指令裡有 30 條用了行接續、其中 17 條是 git 指令，不是假想形態。
        這一向壞掉時是靜默的（守衛照跑、照回 0），故不能只靠 BLOCKED 那張單行清單守。
        """
```

#### §3　`test_block_destructive_git_r83.py`　TestDegradedPayloadIsLoudButNotBlocking (doc L300-307)（搬出原 L300-307，8 行）
```text
    """壞 JSON／空 stdin／缺欄位 ⇒ rc=1（出聲但不阻斷），**不是** rc=0 也不是 rc=2。

    WHY 不硬擋：Bash（mac）／PowerShell（Windows）是這台機器上唯一的 shell 載具，
    對一份根本讀不出內容的 payload 硬擋它，等於用一個讀不懂的輸入換掉整個工作面。
    WHY 不靜默：守衛失效必須看得見——靜默放行是本 repo 一再判紅的那個方向。
    （`tools/tests/test_check_hooks_liveness.py::degraded_payload_verdict` 是同一條
      判準的通用版；本檔負責證明**這一支**真的落在它允許的那一格。）
    """
```

#### §4　`test_block_destructive_git_r83.py`　TestScopeIsNotWidened.test_own_tools_are_the_ones_this_harness_actually_emits (doc L444-451)（搬出原 L446-451，6 行）
```text

        本條刻意**不**去掃逐字稿（那是機器狀態、CI 上不存在，會讓全新 clone 必紅），
        改釘「兩個平台各自的 shell 載具都在射程內」這個結構事實：mac 送指令的工具是
        `Bash`，Windows 因鐵律一禁用 Bash ⇒ 一律走 `PowerShell`。少任一個，就有一整個
        平台不受守。
        """
```

#### §5　`test_block_destructive_git_r83.py`　TestTheRelaxationOpensNoNewHoles.test_the_filesystem_root_contains_the_project_too (doc L644-654)（搬出原 L648-654，7 行）
```text

        🔴 本輪訂正：舊寫法 `os.path.abspath(os.sep)` 解析的是**呼叫者行程 cwd**
        所在磁碟機的根，不是專案所在磁碟機的根——呼叫者 cwd 若落在跟 repo 不同的
        磁碟機（例如從 `C:\\` 驅動、repo 在 `D:\\`），量到的 fs_root 根本不含專案，
        斷言本身就錯了。改用 `_REPO_ROOT.anchor`：同樣是「當前平台的根」，但錨定在
        專案自己的磁碟機，不隨呼叫者 cwd 漂移（posix 上兩種寫法等價，恆為 `/`）。
        """
```

#### §6　`test_block_destructive_git_r83.py`　TestTheCriterionItselfCanFail.test_the_root_boundary_fix_is_load_bearing (doc L812-824)（搬出原 L814-824，11 行）
```text

        這一支的存在理由與上面三支不同：它守的不是「判準會不會恆真」，而是
        「**已知會漏的那個寫法不准回來**」（舊寫法下的實測 rc＝R89 收尾證據檔）。

        🔴 `fs_root` 改用 `_REPO_ROOT.anchor`（理由同
        `test_the_filesystem_root_contains_the_project_too`）：舊寫法
        `os.path.abspath(os.sep)` 量的是呼叫者 cwd 所在磁碟機的根，呼叫者若跟
        repo 不同磁碟機，這裡的 `command` 根本沒有落在專案所在磁碟機，下面兩個
        `assertTrue` 會各自因為不同的錯誤原因巧合為真／假，鎖不到本測試真正要釘的
        那個字。
        """
```

#### §7　`test_block_destructive_git_r83.py`　TestIronLaw6BadFormsAreBlocked (doc L899-905)（搬出原 L900-905，6 行）
```text

    WHY 這一族值得一道阻斷臂：失敗的表徵與「還在正常進行」**完全相同**——R83 收輪實帳
    00:39 → 01:27 共 48 分鐘零工作，靠掌舵者來問才發現。而 `until ! pgrep -f <字面>`
    的兄弟互匹在**單支試跑下永遠是綠的**（`man pgrep` 只排除自己與祖先），所以它連
    「試一次就知道」都做不到。
    """
```

#### §8　`test_block_destructive_git_r83.py`　TestIronLaw6CriteriaHaveTeeth.test_the_wait_carve_out_is_load_bearing (doc L1040-1046)（搬出原 L1041-1046，6 行）
```text

        🔴 探針選擇是本輪實測訂正過的：第一版拿 SD-02 那條唯一假陽性
        （`nohup true; python … & BGPID=$!; wait $BGPID`）當探針，結果注入後**仍然放行**
        ⇒ 那條假陽性其實是被**切段**收掉的，不是被 `wait` 豁免收掉的。兩道收窄各救哪一族
        不能用直覺分配——注入測試當場把它量了出來（同 SD-02「需兩道收窄」的兩道各自成立）。
        """
```

#### §9　`test_block_destructive_git_r83.py`　TestTheHookStaysInsideItsLocTier (doc L1562-1576)（搬出原 L1568-1576，9 行）
```text

    🔴 ADR-XPLAT-013 之後本鎖的**語意變了，鑑別力也變了**，照實記：`count_loc` 已改為
    只算斷言行（docstring／裸字串／整行 `#` 一律免費），該檔的計價因此一次性大幅下降，
    本鎖從「幾乎貼著上限」變成「離上限很遠」。⇒ 它現在守的不再是「再加一行就破線」，
    而是「這支 hook 的**判斷邏輯量**不得長到 tier 之外」——那才是 tier 本來想守的東西，
    但它作為早期預警的靈敏度確實下降了。距上限的實測餘裕現查
    `python AutoClaude/tools/check_loc_budget.py --json` 的 `root_tools_warn_band`
    （本檔刻意不寫死那個數字：它是量測值，寫下去下一輪就過期）。
    """
```

#### §10　`test_block_destructive_git_r83.py`　TestR84TheNewCriteriaHaveTeeth.test_the_first_literal_must_be_git_check_is_load_bearing (doc L1769-1777)（搬出原 L1770-1777，8 行）
```text

        拿掉它，一張**命令字串表**會被整串攤平成一段假指令而命中。逐字用普查裡真的
        撞到的那一筆（一支探針在列舉 `-p` 家族要不要擋），不是好寫測試的簡化版。

        🔴 注入形態是**收窄前的實作本體**，不是去戳 `_GIT_EXE_RE`：那個 regex 同時是
        `git_invocations()` 找執行檔用的（改它會連掃描器一起弄壞，於是注入後反而不命中
        ——本輪第一版就是這樣寫的，測試紅了才發現注的不是同一個零件）。
        """
```

#### §11　`test_block_destructive_git_r83.py`　TestR84WorktreeRemoveForce._as_windows (doc L2124-2136)（搬出原 L2125-2136，12 行）
```text

        🔴 P0-1：識別邏輯搬到 `tools/lib/worktree_paths.py`
        （`is_under_disposable_worktree()`）後，正規化不再只靠 `normcase`——`realpath`
        才是解掉 `..` 那一半（見該模組測試 `test_worktree_paths.py`）。兩者都要注入
        `ntpath` 語意才能讓 mac／Linux 也真的走進混合分隔符／大小寫這兩格：
        `ntpath.realpath` 在沒有 `nt` 模組時（POSIX）退化成純字面 `normpath`／
        `abspath`，不摸磁碟（CPython `ntpath.py` 原始碼確認），所以在假造的
        Windows 語意下兩平台結果一致。

        🔴 整包換而非逐個換（R98）：漏掉分隔符那一格＝混血平台（mac 假紅／Windows
        恆綠）；WHY 全文見 `tools/lib/worktree_paths.py` 模組 docstring。
        """
```

#### §12　`test_block_destructive_git_r83.py`　TestR84WorktreeRemoveForce.test_the_mixed_separator_shape_is_judged_on_every_platform (doc L2140-2149)（搬出原 L2141-2149，9 行）
```text

        此前唯一在守它的是上一支放行清單裡那一行
        `f"…{_REPO_ROOT}/.claude/worktrees/agent-ac3ed"`——只有在 `_REPO_ROOT` 渲染成
        反斜線（Windows）時才合成得出混合分隔符；macOS／Linux 上 `_REPO_ROOT` 是純正
        斜線 ⇒ 混合形態**結構上造不出來** ⇒ 把正規化整個刪掉，mac 全綠。也就是說，R96
        對「單平台專屬判準在對面平台失效」的修法，它自己的回歸鎖犯了同一個錯。
        修法＝顯式注入 Windows 語意（`ntpath.normcase`／`ntpath.realpath` 就是 Windows
        上真正在跑的那份實作），於是 mac 上也真的比到同一條判準。
        """
```

#### §13　`test_block_destructive_git_r83.py`　TestR84WorktreeRemoveForce.test_the_windows_case_insensitive_shape_is_judged (doc L2164-2170)（搬出原 L2165-2170，6 行）
```text

        NTFS 大小寫不敏感 ⇒ `…\\.CLAUDE\\WORKTREES\\agent-x` 與小寫寫法指的是**同一棵
        樹**，而 `.replace("/", os.sep)` 版本比不到 ⇒ 同一類 routine teardown 只要換個
        大小寫寫法就又被誤擋。改用 `normcase` 之後兩種寫法同判——「改了沒人守」是本
        repo 反覆判過的形態，所以這一支與換法同輪落地。
        """
```

#### §14　`test_block_destructive_git_r83.py`　TestR84WorktreeRemoveForce.test_dotdot_traversal_disguised_as_disposable_worktree_is_blocked (doc L2195-2202)（搬出原 L2197-2202，6 行）
```text

        R96 版判準是 `_DISPOSABLE_WT in normcase(victim)`，不解析 `..` ⇒
        `.claude/worktrees/../../AutoClaude` 字面上仍帶著 `.claude\\worktrees\\` 這段
        子字串而被誤判放行；同一招甚至能繞出 `.claude/worktrees/../..`＝repo 根自己。
        兩例當回合唯讀實測見 P0-1 修復前的 `_worktree_hit()` 註解（已隨修復移除）。
        """
```

#### §15　`test_context_budget_guard.py`　_write_jsonl (doc L165-173)（搬出原 L166-173，8 行）
```text

    D27（DEF-200-275 第七輪）：預設 model 原為 `claude-opus-5`——它恰好是
    `known_model_windows.json` 裡的真實表項（window=1,000,000）。D27 補齊 ⑥ 查表階
    後，`window_evidence()` 無條件查表，這個「巧合的真名字」會讓大量以此預設值間接
    測試 FLOOR／WIDE 推斷分支（⑦⑧）的既有案例被查表階攔截、改用真實表值，測到的
    東西跟斷言的意圖對不上。改用不在表裡的合成模型名，讓那些案例繼續測它們原本要
    測的下界推論；真的要測查表階的案例改用表內真名（見 `test_context_window_
    parity.py::KnownModelLookupStageParityTest`）。"""
```

#### §16　`test_context_budget_guard.py`　_hook_invocations (doc L189-194)（搬出原 L190-194，5 行）
```text

    🔴 呼叫字串＝`command` **加上** `args` 全部串起來，不是只看 `command`。
    這裡改為委派（唯一真相源＝`tools/lib/hook_wiring.py`），回傳形狀逐字不變
    （呼叫端不受影響）。兩段 R80 立案原文＝Resume 證據檔 §L-3.2。
    """
```

#### §17　`test_context_budget_guard.py`　SchedulerHygieneTest (doc L270-284)（搬出原 L276-284，9 行）
```text
    🔴 判準**按 tick 種類不對稱**（這正是 :4816 `_resume_tick` 與 :4854 `_sentinel_tick` 患患
    相同——只 patch `register_endurance`——卻只有後者洩漏的原因）：
      · `_sentinel_tick`／`patrol_housekeeping` 可達 `_heal_armed_drift` 的**第二接縫**
        （直呼 `schedule_backend.select().arm`，不經 `register_endurance`），in-process 只有
        控制 `sb.select`（或整支 stub 掉 `patrol_housekeeping`／`_heal_armed_drift`）擋得住
        ⇒ 只 patch `register_endurance` 不夠。
      · `_resume_tick` **不**呼叫 `patrol_housekeeping`（唯一站點在 `_sentinel_tick` 內），
        其武裝／拆除全走第一接縫（`_TICK_DISPOSALS` ∪ arm 進入點），patch 任一即隔離。
    """
```

#### §18　`test_context_budget_guard.py`　_isolated_env (doc L405-411)（搬出原 L406-411，6 行）
```text

    🔴 `USERPROFILE`／`HOME`／`HOMEPATH`／`TMPDIR` 族一起改指 `tmp`＝R79 補的隔離，
    `CLAUDE_PROJECT_DIR` 反而必須指向**真的 repo 根**（hook 要靠它找 planner）。
    立案敘事（1m 標記污染讓 e2e 在開發機靜默、在別人機器上綠）逐字保全於
    `docs/06_quality/CrossPlatform_R91_Scan_Findings.md` §I-1（R92 搬出）。
    """
```

#### §19　`test_context_budget_guard.py`　_run_hook3 (doc L447-452)（搬出原 L448-452，5 行）
```text

    走子行程而非 import＋呼叫 `main()`：hook 的契約是「獨立行程、讀 stdin、以 exit
    code 表態」。R91 stdout 通道沿革（§L-3.4）與「`_run_hook()` 保留 `[:2]` 投影、
    不就地改三元組」的取捨全文＝Resume 證據檔 §L-4.13。
    """
```

#### §20　`test_context_budget_guard.py`　HookExitContractTest.test_unreadable_payload_is_loud_but_never_blocking (doc L656-662)（搬出原 L657-662，6 行）
```text

        判準出處：`test_check_hooks_liveness.py::degraded_payload_verdict`——rc=0
        ＝「送壞 payload 就能讓守衛整支消失，而且沒人看得見」；rc=2 ＝硬擋，爆炸半徑
        由註冊面的 matcher 決定。rc=1 兩者皆非。這一條與下一條刻意分開寫：把「輸入
        壞掉」和「量測不可得」混成同一個桶，正是本 repo 反覆踩到的 fail-open 形狀。
        """
```

#### §21　`test_context_budget_guard.py`　_tree (doc L699-705)（搬出原 L700-705，6 行）
```text

    🔴 為什麼是 `rglob` 而不是 `iterdir`：`sorted(p.name for p in tmp.iterdir())` 只看
    頂層、且比的是**檔名**——只要新增物落在任何一個 `setUp` 當下就已存在的子目錄底下，
    它就結構上看不見。planner 的持久痕跡居所正是這一型（`endurance_env.trace_dir()`
    ＝`Path.home()/.autosdd/traces`，`quota_gate.burn_ledger_path()` 建在它底下）。
    """
```

#### §22　`test_context_budget_guard.py`　comment L720-724（搬出原 L720-724，5 行）
```text
        # 家目錄與被觀測目錄分開（R96），但**觀測面仍是整棵 `self.tmp`**——R96 第一版把
        # HOME 搬進 `self.tmp/home` 之後沿用非遞迴的頂層檔名快照，而 `home` 這個名字在
        # `setUp` 就已存在並被快照 ⇒ 寫進 HOME 底下的任何東西都看不見了（方向與該版文件
        # 宣稱的「恢復完全相等」相反：盲區從「幾個被列舉的檔名」擴大成整棵子樹）。
        # 修法＝全樹快照 ＋ `_HOME_ARTIFACT_DIRS` 這一組具名例外。
```

#### §23　`test_context_budget_guard.py`　PlannerCliTest.test_the_write_check_can_actually_see_under_the_home (doc L747-755)（搬出原 L748-755，8 行）
```text

        這一條就是 B-4 的全部價值。R96 那版的快照是
        `sorted(p.name for p in self.tmp.iterdir())`（非遞迴、只比檔名），而 HOME 被搬成
        `self.tmp/home`、`home` 又在 `setUp` 就存在 ⇒ 「planner 開始在家目錄下寫 burn
        ledger／續航痕跡」這一類真回歸在它底下結構上恆綠。合成的這個檔案就是那一類回歸
        的最小樣本（路徑逐字取自 `endurance_env.TRACE_HOME_PARTS` ＋
        `quota_gate.BURN_LEDGER_NAME`，不是隨手挑的名字）。
        """
```

#### §24　`test_context_budget_guard.py`　PreToolUseBlockTest.test_the_registered_matcher_matches_the_scripts_own_scope (doc L1252-1258)（搬出原 L1253-1258，6 行）
```text

        🔴 計數的是**註冊（block）數**而不是條目數：exec form 下每個邏輯 hook 佔兩個
        條目（Windows／POSIX 載具各一、各平台恰好一條 spawn 得起來），那不是重複註冊
        也不會雙跑；刪掉其中一條才是真缺陷（另一平台整支消失且 fail-open 不轉紅，
        `hook_wiring` 判準 E 在守）。R80 production 實測佐證逐字見證據檔 §I-9（R92 搬出）。
        """
```

#### §25　`test_context_budget_guard.py`　comment L1268-1272（搬出原 L1268-1272，5 行）
```text
    # 🔴 SA-R80-02：上面那條把 matcher 與射程釘成**相等**，於是它保證的是「兩個都寫錯
    # 時也一致」——鑑別力的方向錯了。掃描 S7-02 實測：`Task`／`WebFetch`／`WebSearch`
    # 這三個名字在本 harness 的 **8,106 次 tool_use 裡出現 0 次**（派子代理叫 `Agent`、
    # 批次編排叫 `Workflow`）⇒ S1「不要爆」的阻斷臂命中面是 0，蓋好了卻永遠不會觸發。
    # 下面三條補的是**有效性**那一向：圈了一組永遠不出現的名字必須當場轉紅。
```

#### §26　`test_context_budget_guard.py`　PatrolHandbackIsItsOwnOutcomeTest.test_the_rearmed_sentinel_carries_the_sentinel_prefix (doc L1660-1667)（搬出原 L1661-1667，7 行）
```text

        `sentinel_task_name()` 只在 `--task-name` 是預設值時才套
        `sentinel_lifecycle.TASK_PREFIX`，而本路徑的 `args.task_name` 是**續航**工作的
        名字（schtasks Action 帶進來的）⇒ 不歸位就會掛在續航名下，而 GC／`liveness_line()`
        正是用那個前綴篩「哨兵那一種」工作。失效外觀＝哨兵在，但沒有人看得到它（R80
        整晚失明的同一個形狀）。本包實作時就是靠一次手動 smoke 才發現，故補這道鎖。
        """
```

#### §27　`test_context_budget_guard.py`　comment L2177-2181（搬出原 L2178-2181，4 行）
```text
        # 立案是本包當回合的注入實測——把 `quota_gate(payload)` 塞進 `block_verdict()` 的
        # 早退分支時，這條鎖與新增那條**都判綠**（注入 rc=0）。而那個形態正是 SA-B1 描述的
        # 死碼：`block_verdict()` 只在 context ≥90% 才到得了，額度耗盡時 context 只有 ~18%。
        # 「額度看起來有人守，實際上那段程式跑不到」比沒有機制更糟。
```

#### §28　`test_context_budget_guard.py`　SentinelDecisionTest.test_no_caller_passes_the_reserved_keys_any_more (doc L2462-2470)（搬出原 L2463-2470，8 行）
```text

        兩條都要有——只擋後果的話，下一個人仍會寫出讀起來像在設定時間戳、實際被
        默默忽略的呼叫；只擋成因的話，`append_log` 自己被改回去時沒有人會知道。

        🔴 判準走 AST 而不是整份原始碼的字串搜尋：後者只要註解或 docstring
        **合法地**提到那個字樣就假紅（`test_archive_defect_log` 有一條同名紀律在守
        這件事，Pkg-P12 已實際發生過並導致帳本改寫自己的缺陷描述）。
        """
```

#### §29　`test_context_budget_guard.py`　SentinelWiringTest._posttooluse (doc L2755-2762)（搬出原 L2756-2762，7 行）
```text

        🔴 R96：`real_scheduler=True` 是**必要條件、不是放寬**——預設的
        `AUTOSDD_SENTINEL_OFF=1` 會讓 `arm_when_earned()` 直接 `return "disabled"`，
        本組三支於是全部由「哨兵被整個關掉」滿足（1 真紅 ＋ 2 假綠）。安全性由
        `_fake_repo()` 的替身 planner 保證（見其 docstring），一支真排程都不會註冊。
        十三輪無人發現的成因見 `CrossPlatform_R96_Closure_Evidence.md` §2②。
        """
```

#### §30　`test_context_budget_guard.py`　SentinelWiringTest.test_sessionstart_no_longer_spawns_the_arming_run (doc L2773-2779)（搬出原 L2774-2779，6 行）
```text

        這一條原本斷言相反的事（「SessionStart 真的把 planner 叫起來」）。它當時是對的，
        但那個形狀的代價是掌舵者當場截圖的東西：排程器裡三支哨兵，兩支屬於活了 5 秒與
        12 秒的 session。餵的逐字稿刻意是**夠格**的那一種——所以這條紅不了的唯一方式，
        是武裝真的不在這個事件上發生，而不是「這次剛好不夠格」。
        """
```

#### §31　`test_context_budget_guard.py`　SentinelWiringTest.test_an_earned_session_actually_spawns_the_arming_run (doc L2791-2797)（搬出原 L2792-2797，6 行）
```text

        只斷言 rc=0 會恆綠（fail-open 的守衛對任何輸入都回 0）。這裡改看**副作用**：
        替身被執行後留下的 argv。把 `arm_when_earned()` 從 `main()` 拿掉時這條會紅——
        而少了它，上一條（SessionStart 不武裝）可以靠「哪裡都不武裝」滿足，那是把
        續航整個關掉，且外觀與修好完全相同。
        """
```

#### §32　`test_context_budget_guard.py`　comment L2952-2956（搬出原 L2952-2956，5 行）
```text
        # 🔴 v2.1.13 G3：`_run_resume()` 現在也在 spawn 前後各跑一次
        # `git status --porcelain`（`relay_machine.git_status_snapshot`，判準④取數）。
        # 那條路一樣經過同一個（模組級單例）`subprocess.run`，本類的 mock 若不分流，
        # 三次呼叫會全部落進 `self.calls`，而本類要證的只是**續跑那一次**的 argv/env
        # 形狀——git 呼叫讓它落回真實 `subprocess.run`（唯讀查詢，安全）。
```

#### §33　`test_context_budget_guard.py`　UnattendedPermissionPostureTest.test_va1_both_routes_carry_permission_mode_and_settings (doc L3169-3180)（搬出原 L3170-3180，11 行）
```text

        缺旗標＝G1 原事故形態：spawn 出去的無頭窗口落在預設權限牆後、寫不了新檔。
        旗標值也一併釘住（acceptEdits／姿態檔絕對路徑），且必須排在變長的
        `--add-dir` 之前——排在其後會被那個變長參數吃掉（同姊妹鎖的立案缺陷）。

        🔴 2026-09-07 掌舵者裁決（INV2＋INV3 拆除）：姿態檔**只有一份**——
        `UNATTENDED_SETTINGS`。此前 M-06 分窗立檔、後併回本條的沿革全文搬至
        CrossPlatform_R151_Guard_Prose_Migration.md
        〈test_va1_both_routes_carry_permission_mode_and_settings〉節。
        故本條一併釘住「兩路指向同一份檔」與「那一份檔的 deny 不含 fan-out 三工具」。
        """
```

#### §34　`test_context_budget_guard.py`　comment L3889-3896（搬出原 L3892-3896，5 行）
```text
# 立案＝額度 23:00 回來後，喚醒鏈自動叫醒 3 次 headless 全量視窗（19:53/23:02/23:09），
# 每次都撞無人核准權限牆做不了事、卻還先去重跑一個 34-agent 的 Workflow（上一輪 F3 修法
# 造成）＝純燒 token。掌舵者親定邏輯：「哨兵先叫醒主 agent；要先判斷主 agent 是否**成功**
# 起來，才能跑後續。主 agent 沒成功，哪來的後續；沒起來就不要浪費 token。」
# 五條不變量各自紅綠自證；雙後端（Windows＝SchtasksBackend、macOS＝LaunchdBackend）各驗一遍。
```

#### §35　`test_context_budget_guard.py`　Fix2ResumeCallScriptPathIsJsSafeTest (doc L4077-4087)（搬出原 L4081-4087，7 行）
```text

    🔴 為何樣本走 `str(PureWindowsPath(...))`（不是裸字面）：(a) 跨平台都能造出**反斜線**字串
    （POSIX 直譯器上 `Path` 不把反斜線當分隔符，裸 `\\` 樣本 `str()` 與 `as_posix()` 逐字相同、
    測不出差異——這正是本 bug 在 mac/CI 上的結構性失明）；(b) 滿足根層 `scan_drive_literal`
    的顯式平台語意豁免。思想突變：把生產碼 `PureWindowsPath(script_path).as_posix()` 退回
    `str(script_path)`（或裸 `script_path`）⇒ 下面 `assertNotIn(反斜線)` 轉紅。
    """
```

#### §36　`test_context_budget_guard.py`　comment L5533-5537（搬出原 L5534-5537，4 行）
```text
        # ——後者自己會呼叫 `write_relay()` 把 state 落盤，整支 mock 掉會讓本測試要驗的
        # 「state['handback_path'] 有沒有真的寫回磁碟」失去鑑別力（實測：mock 掉
        # `_register_and_record` 時，即使生產碼把 handback_path 塞進 state，最終讀出來的
        # plan.md 仍是 `_resume_tick()` 呼叫前寫入的舊內容，因為沒有任何東西再寫過它）。
```

#### §37　`test_context_budget_guard.py`　comment L5798-5804（搬出原 L5800-5804，5 行）
```text
#: R84／C3-A 上修 10→11：具名納入 `tools/lib/schedule_backend.py`（兩個 glob 都罩不到，
#: 理由見 `ConsoleFreeSpawnTest._sources`）。
#: console_qa 事故輪上修 11→30（本輪實測 `len(_sources())`）：新增
#: `AISDLC_SDD/scripts/sdd_version.py`／`tools/lib/sdd_latest.py`／`tools/lib/git_paths.py`／
#: `tools/lib/platform_utils.py`／`tools/_stdio_utf8.py` 五支，理由同見 `_sources`。
```

#### §38　`test_context_budget_guard.py`　ConsoleFreeSpawnTest.test_the_duplicated_no_window_expression_still_equals_the_ssot (doc L6099-6106)（搬出原 L6100-6106，7 行）
```text

        🔴 為什麼是**值**相等而不是文字比對：兩份的意義是「同一組 Windows 旗標」，
        而那件事只有值說得準；文字比對會在有人換個等價寫法時給出假紅。

        `sentinel_lifecycle` 已於 R83／PD 由兩份名冊移除（不是鎖被放寬），沿革原文＝
        Resume 證據檔 §L-3.7。仍在守的兩端逐一具名，射程縮小時會指名道姓地紅。
        """
```

#### §39　`test_context_budget_guard.py`　NoWindowBehaviourTest.test_the_shipped_flag_really_suppresses_the_console (doc L6346-6365)（搬出原 L6351-6365，15 行）
```text

        DEF-200-396 延伸：「none」負對照套的 `STARTUPINFO(SW_HIDE)`（見
        `_BEHAVIOUR_PROBE` 檔頭註解）此前只手動驗證過三次沒有把 console 升級成
        Windows Terminal 分頁，沒有任何測試覆蓋。本測試重用
        `PlannerCheckIsConsoleFreeTest` 的即時 WMI 監看模式（`_LIVE_CONSOLE_WATCH_
        PS1`）全程武裝監看，斷言量測期間 0 筆 OpenConsole.exe／WindowsTerminal.exe
        建立事件——且監看器必須真的武裝成功，沒武裝就不能算綠（否則是空洞通過）。

        🔴 審查訂正：`Seconds` 這個 deadline 從腳本啟動（含 PowerShell 冷啟動與
        `Register-CimIndicationEvent` 武裝耗時）就開始算，不是從量測開始算——慢機器
        上量測還沒結束監看器已先收工，屆時「0 筆事件」是監看器沒在看，不是真的沒
        觸發（空洞通過）。`Seconds` 給寬裕值（60），量測結束後改主動核對監看器
        `poll()` 仍是 `None`（還活著）才採信 0 筆事件，再顯式 `terminate()`，不依賴
        它跑滿 60 秒才退場——測試總時間不會因此變長。
        """
```

#### §40　`test_context_budget_guard.py`　NoWindowBehaviourTest.test_the_quiet_carrier_needs_no_flags_at_all (doc L6410-6416)（搬出原 L6411-6416，6 行）
```text

        兩層各自成立才是本修復的設計：任一層被未來的人改掉，另一層仍撐得住。
        🔴 這一條同時是 R80 訂正的憑據——我第一版把「`DETACHED_PROCESS` 抵銷
        `CREATE_NO_WINDOW`」寫成旗標語意，實際上翻面的是**載具**（uv trampoline），
        真直譯器那一列 `DET|CNW` 是 0。
        """
```

#### §41　`test_context_budget_guard.py`　comment L6439-6445（搬出原 L6441-6445，5 行）
```text
#: 🔴 為什麼不用「呼叫前後 PID 快照差集」：注入自證實測過——git.exe 這種瞬發子行程
#: 觸發的 OpenConsole.exe／WindowsTerminal.exe 常在快照間隔內就已消失（"生得快、死得快"，
#: 不像哨兵長跑續航那樣會孤兒累積），快照差集因此漏掉過一次真事故（拿掉 `sdd_version.py`
#: 的 creationflags 後，快照法仍回報「無新增」；同一秒改用本監看器立刻抓到
#: `WindowsTerminal.exe`＋`OpenConsole.exe` 建立事件）。即時事件訂閱不受「活多久」影響。
```

#### §42　`test_context_budget_guard.py`　comment L6505-6509（搬出原 L6505-6509，5 行）
```text
        # DEF-200-392 覆審：`resolve_transcript(None, None)` 在乾淨 CI runner 上解不到
        # 逐字稿會令本測試整支 [ENV-DISABLED] skip，而它正是防 console 洩漏事故
        # （DEF-200-389）再犯的行為鎖。事故路徑不因逐字稿真假而改變（見本 class
        # docstring：`measure()` 無條件走到 `window_evidence()` 的裸 git 子行程），
        # 改用合成逐字稿 ＋ 顯式 `--transcript`，不再依賴機台上是否真有逐字稿。
```

#### §43　`test_context_budget_guard.py`　FanoutCasualtyRecordTest.test_the_record_states_when_resume_from_run_id_is_invalid (doc L6997-7005)（搬出原 L6998-7005，8 行）
```text

        DEF-200-270 舊措辭（「同 session only／沒有任何排程器按得到」）為何 stale 的沿革
        全文搬至 CrossPlatform_R151_Guard_Prose_Migration.md
        〈test_the_record_states_when_resume_from_run_id_is_invalid〉節。
        現行劃界＝**session 已死且無法 `-p -r` 續跑時**才無效；無頭窗口
        可自行呼叫 `Workflow(resumeFromRunId)`（掌舵者 2026-09-05 裁決）。「`-p -r` 內
        resumeFromRunId 是否有效」為前提待實測，產物要說出這件事。
        """
```

#### §44　`test_context_budget_guard.py`　_fresh_transcript (doc L7206-7212)（搬出原 L7207-7212，6 行）
```text

    專門給 `ArmedDriftSelfHealTest` 用：讓 `_main_transcript_idle_seconds` 算出來的
    閒置秒數遠小於 `SENTINEL_INTERVAL_SECONDS`，`_idle_prepare_watch` 會在第一格
    （閒置未達門檻）就短路返回，不去碰額度快取——漂移自癒的測試才不會被 R-4.5.7-2
    那條路徑的副作用（讀真額度快取）干擾。
    """
```

#### §45　`test_context_budget_guard.py`　comment L8032-8038（搬出原 L8032-8038，7 行）
```text
        # 🔴 R93：`fetch_usage` 回 3-tuple（見 `(status, payload, headers)`），第三格
        # 在這些失敗形狀下皆為 `{}`——本測試不驗帳號識別，headers 內容零意義。
        # 🔴 R100：**`HTTP 429` 已從本母體移出**（PRD §8 第 1 列）。它不再是「失敗形狀」
        # ——429 現在回一份 pct 下界 100 的單軸**地板讀數**（`rate_limited_reading()`）並
        # 落進 halt。判為**鎖過時該同步**：把 429 留在這裡等於把「額度吃緊最強的直接證據」
        # 鎖死成「量不到」，而量不到在本 repo 的語意是**放寬**（`degraded_cap`）。
        # 那一格由 `RateLimitIsAFloorNotAnUnknownTest` 承接，且它比本列更嚴（驗到 halt）。
```

#### §46　`test_context_budget_guard.py`　QuotaStaleCacheTest.test_a_stale_high_value_also_stops_throttling (doc L8369-8375)（搬出原 L8370-8375，6 行）
```text

        這是刻意的取捨，不是漏洞：斷網時保留一個舊的高值會讓守衛在網路壞掉時
        無限期停機，而那與「額度真的滿了」外觀完全相同。地板由逐字稿撞線偵測提供。
        （「量不到」本身仍有 `degraded_cap`，見 `QuotaUnmeasurableTest`——不採信舊值
        與不設限是兩件事，R82 只推翻了後者。）
        """
```

#### §47　`test_context_budget_guard.py`　foreign_trace_growth_problems (doc L8473-8489)（搬出原 L8475-8489，15 行）
```text

    WHY（2026-09-20；DEF-200-346）：`quota_trace_path()` 指的是
    **machine-wide** 的生產痕跡——同機任何並行 Claude Code session 的 hook 呼叫
    `note_degraded()` 都會在這個視窗裡對同一份檔案追加自己的紀錄（每筆已含
    `"pid": os.getpid()` 欄），那些行不是本測試寫的，容忍它們才是誠實的判準；
    分不清是誰寫的（解析失敗／缺 `pid` 欄）則 fail-loud，不假造一個「反正不是我」
    的寬容去掩蓋真正的歸因缺口。
    劃界（複審 Architect）：pid 歸因只涵蓋**本行程直接寫入**；巢狀測試若自己 spawn
    子行程去寫真檔，其 pid≠own_pid 會被當外來而放行——今日兩個巢狀類別皆走
    `_TRACE_ISOLATION` 沙箱故不觸發，但那是沙箱在守，不是本函式。

    輪替判準：`after` 以 `before` 為前綴時取尾端差集當「新增區段」；若不是前綴
    （視窗內檔案被輪替／截斷），視整份 `after` 為新增——這種情況下也只看 `after`
    裡的行，不回頭比對已經輪替掉、無從歸因的舊內容。
    """
```

#### §48　`test_context_budget_guard.py`　TraceIsolationTest.test_the_real_production_trace_is_untouched_by_this_module (doc L8581-8593)（搬出原 L8583-8593，11 行）
```text

        🔴 這一條刻意讀**真的**路徑（不是沙箱）——它問的正是「生產那一份有沒有被寫到」，
        而那件事只有真路徑回答得出來。它只讀不寫。

        🔴 R84／SA84-01：巢狀 runner 一律走 `_run_nested_suite`（見該函式的 WHY——這一支
        就是把整個模組的哨兵 pin 沖掉的那一支）。

        2026-09-20（DEF-200-346）：`quota_trace_path()` 是 machine-wide 的
        生產痕跡，同機並行 session 的 hook 也會在這個視窗裡對它追加自己的紀錄——用
        `pid` 歸因（見 `foreign_trace_growth_problems` WHY），只容忍別人 pid 的行。
        """
```

#### §49　`test_context_budget_guard.py`　ZSentinelPinOutlivesEveryNestedRunnerTest.test_red_a_raw_nested_runner_really_does_flush_the_module_cleanups (doc L8618-8634)（搬出原 L8619-8634，16 行）
```text

        載荷刻意就用上面那一格（字母序在本格**之前**，所以它量到的是真狀態）：它在巢狀
        suite 執行**當下**仍然是綠的（flush 發生在 suite 收尾，不是執行中）⇒ 這一條同時
        釘住「失效的時間點在 teardown」這個機制。
        本條若哪天轉紅，代表載具的 module fixture 語意變了，`_run_nested_suite` 的立案
        前提消失——那時要重讀它的 WHY 再決定它還要不要存在，而不是把這一格刪掉。

        🔴 M-03（leak_fence）之後不能再硬編 `assertIsNone`：`run_root_unittests.main()`
        現在會在整套測試最外層先幫這個環境變數 `setdefault` 成 `"1"`（見
        `sentinel_lifecycle.leak_fence`），所以「`setUpModule` 進來前的原值」（真跑一次
        全套時）可能本來就是 `"1"`，跟 `_sentinel_off_lifted()` 那句「開發機 shell 常年
        帶 `AUTOSDD_SENTINEL_OFF=1`」是同一種情況——這支測試需要一個「flush 後會變成的值」
        跟「目前 pin 住的值」可以互相區分，因此改成暫時把 `_SENTINEL_PIN_ORIGINAL` 換成
        一個不可能是真環境值的哨兵字串，flush 有沒有發生就看還原值是不是這個哨兵字串，
        不受外圍環境（有沒有 leak_fence／開發機 shell 慣例）影響。
        """
```

#### §50　`test_context_budget_guard.py`　FanoutLedgerConcurrencyTest.test_the_counter_is_actually_sensitive_to_a_lost_record (doc L8842-8848)（搬出原 L8843-8848，6 行）
```text

        刻意用「刪掉 K 個目錄項」而不是「跑一次舊實作看它掉多少」：舊實作的掉行率是
        **平台相依**的（POSIX 的 `O_APPEND` 是核心層原子的，同一段程式在 Linux 上
        LOST=0）⇒ 拿它當注入組會讓這支鎖在 CI 上必紅。判準要綁被守的性質，不要綁一台
        機器的偶然行為（鐵律三）。
        """
```

#### §51　`test_context_budget_guard.py`　QuotaGateIsIndependentOfContextTest.test_denied_calls_do_not_leak_into_the_real_ledger (doc L9316-9322)（搬出原 L9317-9322，6 行）
```text

        `FanoutLedgerTest` 那幾條是自己呼叫 `append_dispatch` 造帳，所以把 deny 路徑上
        那一行 `undo` 拿掉時它們照樣全綠——鎖在守的是輔助函式，不是**真的走過的那條路**。
        這一條改成真跑 hook：節流帶裡先用滿預算、再被擋 K 次，然後直接量真實帳檔。
        洩漏時它會讀到 cap+K（＝一旦到 cap 就永遠回不來，即使 quota 掉回 50）。
        """
```

#### §52　`test_context_budget_guard.py`　comment L9786-9791（搬出原 L9787-9791，5 行）
```text
        # `policy_env()` 的合併視圖是 env > `.env`，本類判準要的是「檔案那一半」，而
        # 行程級 env 是活體——同行程較早的測試經 `planner.main()` →
        # `apply_env_defaults(os.environ)` 會把真 `.env` 的鍵（如 HALT_PCT=95）永久
        # 灌進來（pytest 定義序下污染類在本類之前 ⇒ 紅；unittest 字母序相反 ⇒ 綠），
        # 開發機 shell 也可能自帶這些鍵。不刷掉，本類量到的是機器姿態不是程式行為。
```

#### §53　`test_context_budget_guard.py`　_cred_kwargs (doc L10105-10110)（搬出原 L10106-10110，5 行）
```text

    兩欄都**不碰主機真正的憑證**：檔案欄一律指到 `mkdtemp` 下的路徑，Keychain 欄一律
    走注入的 runner。R83 立案敘事（判準不得讀會隨機器變的外部狀態）原文＝Resume 證據檔
    §L-3.20。
    """
```

#### §54　`test_context_budget_guard.py`　comment L10183-10188（搬出原 L10183-10188，6 行）
```text
        # 🔴 R100：**429 已從本母體移出**（PRD §8 第 1 列）。它現在走專屬分支回一份地板
        # 讀數，不再是 `(None, "http-429")`。這支鎖此前把「429 折成量不到」寫成了規格
        # ——判為**鎖過時該同步**而不是我改錯：條文逐字要求「必須把 429 視為遙測低估的
        # 證據，將 U5h 推估值上修」，而舊斷言鎖死的正好是它的反面（折成量不到 ⇒
        # `degraded_cap` ⇒ 比量到 70% 那一帶更寬鬆）。429 那一格由
        # `RateLimitIsAFloorNotAnUnknownTest` 承接，覆蓋面不減。
```

#### §55　`test_context_budget_guard.py`　RateLimitIsAFloorNotAnUnknownTest._fake_429 (doc L10252-10257)（搬出原 L10253-10257，5 行）
```text

        刻意打在 `urlopen` 這一層：本修法有一半住在 `fetch_usage()` 的 `HTTPError`
        分支（此前第三格寫死 `{}` ⇒ 錯誤回應的標頭被丟掉），替掉 `fetch_usage` 會把
        那一半整個跳過而仍然全綠。
        """
```

#### §56　`test_context_budget_guard.py`　comment L10939-10947（搬出原 L10940-10947，8 行）
```text
    #: 允許的處置＝拆掉自己／重排下一次／交棒給另一支受本判準約束的 tick；第四個名字
    #: （`_abort_and_unregister`）是委派而非新語意，強度由
    #: `test_the_abort_delegate_really_disposes` 補齊。全文＝Resume 證據檔 §L-4.9。
    #: 🔴 v2.1.13 G3：第五個名字（`settle_window`）住 `tools/lib/relay_machine.py`（跨檔
    #: 委派，經 `relay_machine.settle_window(...)` 這種 attribute call 呼叫，而不是同檔
    #: 裸名），`names_in()` 因此同輪擴到也認 `ast.Attribute` 的 `.attr`——強度由
    #: `test_the_settle_window_delegate_really_disposes` 補齊（同 `_abort_and_unregister`
    #: 判例：委派進了清單就必須釘住它真的拆排程，不能只是好聽的名字）。
```

#### §57　`test_context_budget_guard.py`　comment L11149-11153（搬出原 L11149-11153，5 行）
```text
# 🔴 WMI `Win32_Process` 欄位的**逐字語料**（`classify()` 對它們只做字串比對，不經任何
# pathlib join）⇒ 磁碟機字面值在這裡是被測資料本身，不是「假路徑」，故走 `platform-ok`
# 具名豁免而非 `ABS_FAKE_REPO`（換成後者會讓 repo 根與命令列裡的路徑在 POSIX 上對不上，
# 判準會從「比對命令列」變成「永遠不命中」＝把回歸鎖靜默掏空）。集中成常數的第二個理由
# 是它們被多支測試共用，散寫時每一處都要各自帶一個豁免標記。
```

#### §58　`test_context_budget_guard.py`　comment L11500-11506（搬出原 L11503-11506，4 行）
```text
# 修法是**一次前置填充**（`quota_gate.apply_env_defaults`，由 hook 的 `main()` 呼叫），
# 不是把每個讀取點改寫成 `policy_env()`。理由是射程：`SENTINEL_OFF_ENV` 有一個讀取點
# 住在 `arm_sentinel()` 裡，逐點改寫必然留下一個改不到的縫，而那個縫**正是本條在治的
# 靜默失效**。填充之後，每一個 `os.environ.get(<ENV_SPEC 宣告過的鍵>)` 都看得到 `.env`。
```

#### §59　`test_context_budget_guard.py`　comment L12469-12476（搬出原 L12472-12476，5 行）
```text
# 立案實測（80 站點僅 10 帶旗標；擴面後命中 1 筆真陽性）原文＝Resume 證據檔 §L-3.28。
# 第三條路＝本 repo 既有的 **shrink-only 存量棘輪**：
# 新站點一律紅，已登記的那一筆放行**但必須仍然真的違規**——有人修好了它，這張表就會
# stale 而轉紅，逼人把它拿掉。分子只准降。
# 🔴 錨用**函式名**不用行號：行號會隨那支檔的任何一次編輯漂掉，而漂掉的方向是靜默放行。
```

#### §60　`test_context_budget_guard.py`　QuotaPaceOutletIsReachableTest.test_it_says_why_an_empty_short_window_still_cannot_be_burned (doc L12711-12718)（搬出原 L12713-12718，6 行）
```text

        🔴 R93／DEF-200-122：`SEED_OBSERVATIONS` 已永久排除在任何指紋池外（見
        `quota_pace.filter_by_signature`），故本測試改為**先落兩筆同指紋的真實歷史列**
        （取代舊版單靠 SEED_OBSERVATIONS 提供先驗的假設），維持「攤提真的套用時說明必須
        完整」這個原意，同時對齊新的指紋過濾語意。
        """
```

#### §61　`test_context_budget_guard.py`　FanoutWindowRemainingSecondsTest.test_an_empty_ledger_says_the_window_is_empty_instead_of_zero_seconds (doc L13061-13067)（搬出原 L13062-13067，6 行）
```text

        `0` 在這一行的語意剛好相反：它讀起來是「視窗滿了、正要放行」，而真相是「視窗
        完全是空的、現在派不必等」。兩者要求 operator 做的事恰好相反 ⇒ 用一個獨立的
        字面（`視窗全空`）承接，而不是讓 `None` 靜默塌成 `0`。
        本格也一併覆蓋「派發帳目錄還不存在」（`scandir` OSError）那一支。
        """
```

#### §62　`test_context_budget_guard.py`　FanoutWindowRemainingSecondsTest.test_an_entry_past_the_window_neither_holds_it_open_nor_anchors_it (doc L13077-13084)（搬出原 L13078-13084，7 行）
```text

        🔴 順序是刻意的：**先**問 `fanout_window_left()`、**後**才 `live_dispatches()`。
        反過來的話 `live_dispatches()` 會先把超期項 prune 掉，於是「本函式自己有沒有套
        `floor`」這件事就測不到了（帳目變空之後，漏套 floor 的實作也會回 `(None, None)`）。
        第二格（超期 ＋ 兩筆還算數）才是真的鑑別力所在：漏套 floor 會錨到 350 秒那筆、
        算出 `max(0, 300−350)` ＝ `(0, 350)`——一個「剩 0 秒」的假話。
        """
```

#### §63　`test_context_budget_guard.py`　HarnessFeedStageTest.test_measure_marks_a_fresh_window_only_when_the_feed_side_is_readable (doc L13999-14006)（搬出原 L14000-14006，7 行）
```text
        真格：TUI 剛開（feed 的 current_usage 為 null）；第一則回應到手但逐字稿還沒落盤
        （feed 已有值——首輪自己的 `--check` 實際遇到的形狀：本機頂層逐字稿裡兩次真跑出 ❌
        的首輪 `--check`，`check_lines()` 都回空，那只有 `harness_used` 非 None 才會發生）。
        假格：沒有 feed（分不出新視窗還是欄位格式漂移）、別人的 feed、compact 空窗
        （逐字稿留有舊 usage）、逐字稿見到 model 卻沒有可用 usage（格式漂移的警報要留著）、
        assistant 記錄整個沒有 usage 鍵（複審鏡 S1：`scan_transcript` 的 usage 預篩會讓 model
        也讀不到，只靠 `model is None` 會把欄位改名誤判成新視窗）。DEF-200-425。"""
```

#### §64　`test_context_budget_guard.py`　tearDownModule (doc L14565-14571)（搬出原 L14566-14571，6 行）
```text

    立案同 `_tmpdir` 的 SA84-06：測試不得在使用者的環境留下真實副作用。這裡的副作用是
    「一則假的額度降級通報，在跑測試的人的 stdout 上出現」——`platform_utils.emit_to_model`
    只累積、由 `atexit` 送出，而好幾個 in-process 呼叫 `qg.quota_gate()` 的類別會把訊息
    排進去卻不讀它。排掉而不是關掉：真正在斷言送達的那幾組自己會先 flush。
    """
```

#### 九-F 收尾事實（Developer-F 本場實測；供〈六〉引用，全套結果另見〈七〉）

- **搬遷的機械證明**：四檔 `ast.dump`（剝掉 docstring 後）與搬遷前逐字相同，`SAME` ×4；`py_compile` 四檔 OK。comment 區塊搬遷前以 `tokenize` 驗證區間內每一行都是真正的 COMMENT token——第一版計畫有一處 9 行「註解」其實住在 `_BEHAVIOUR_PROBE` 探針腳本的字串字面值裡，AST 比對當場抓出 `Constant differs`，已退回並從計畫移除（工具現在對這種區間直接 `AssertionError`）。
- **為何必須搬舊史料**：本輪新增的 1169 行（F1 之前量）裡只有 187 行 docstring＋14 行註解（約 17%），其餘是測試本體；要讓主軌 ≤ 523（回歸鎖軌上限 309 ⇒ 淨額 ≤ 832）只能同時搬舊敘事。共搬 451 行原文、原位 64 處各留一行指針（其中 9 處附 1～2 行濃縮摘要），淨減 371 行。
- **分桶棘輪（`guard_bucket_policy`，chunk／exclusive）**：Developer-E 收口後 `prose` 4454／`guard_self` 3073（凍結 4311／3163）；搬遷＋下一條的分類修正後 `prose` 4194／`guard_self` 3031，`bucket_ratchet_problems` 為空（過時下限 4095／3004，`guard_self` 餘裕 27 行）。`prose` 超出凍結值 143 行，主因是 `test_wake_chain_halt_r278.py::RegisterSchtasksTimeIsObservedNotGuessedTest` 整類 215 行被歸成純散文桶——該類 docstring 只點名了根 `CLAUDE.md`、沒點名受測模組 `tools/session_resume_planner.py`；它的 docstring 敘事僅 43 行可搬（< 143），故採先例做法（`guard_bucket_policy._FROZEN_SHRINK_ONLY_BUCKET_LINES` 註解〈系列收斂後四方重驗收尾單人窗口：`prose` 4469→4311〉同型：補上受測模組字面，屬分類缺口非成長），使其由 `prose` 轉 `mixed`；docstring 行數不變（5 行）、AST 比對 SAME。
- **到期義務**：`_PHASE2_REVIEW_LOG` 末列 R183＋視窗 5 輪＝R188，稽核痕跡走到 R189 即 `[時效逾期]`——追加 `(189, "[提案]", …)`（體例同 R141／R153／R165／R177：末列 `[維持觀察]` 名額已用罄）。`_REPIN_NET_CAP_DUE_ROUND=190` 不在本輪。（承接列＝DEF-200-207：ADR-XPLAT-013 仍 Proposed 而機械物在生產跑，方向 (c) 提案的命運由該列承載）
- **doc-total 對帳需要兩個站點**：`<!-- guard-total:R189 -->` 除了 `AutoSDD_improving_112.md` 還必須出現在 `CrossPlatform_R145_Scan_Findings.md`〈附記（R189）〉（`doc_guard_total_problems` 款(1) 要相異檔 ≥ 2，R188 同型）。
- **表② 回填**（`tools/lib/clean_venv_carrier.py`，樹外乾淨 venv `autoclaude_cleanvenv_20261001T172018Z`、Docker down、探針 `psycopg2 ABSENT`／`sqlalchemy ABSENT`、`CARRIER_RC=0`、venv 已自刪）：`cigate-v030` 1963→1979（+16）、指紋 `v030=4d902e4a743a`→`6d46814f9084`；`autoclaude-pytest-snapshot` `{'passed': 4680, 'skipped': 222}`、`cigate-v001` 1475、`cigate-scripts` 362 與三棵指紋皆不變；`--check-snapshot` rc=0 `✅ §7 表② 指紋相符 macOS 欄`。（Developer-D 看到的 autoclaude 指紋「漂移」是 Windows 欄的 `35adf49caea0→186afd1b2239`，macOS 欄不動。）
- **全套第一次 `REAL_RC=1`，恰 1 紅**（`發現 4960 個測試（下限 4876）`、workers=9、S=815.5s）：`test_windowsapps_guard_cross_consistency.TestZeroGuardBarePythonSitesAreEnrolled.test_zero_guard_bare_python_sites_match_registry_exactly`——Developer-E 的 E7(a) 把 `_STATUSLINE_INSTALL_HINT` 改成以 `python ` 開頭的裸指令字串（`tools/lib/session_brief.py:240`，HEAD 零命中），成為註冊表外的第 14 個「零 guard 裸 python 名稱」站點。它是 `_install_command()` 組不出絕對路徑時退回的**顯示用提示字串**（本檔不 spawn），依該鎖失敗訊息的指示登記進 `_ZERO_GUARD_BARE_PY_SITES`（附角色註記，+4 行；不改生產碼、不弱化判準）。Developer-E 的針對性鎖清單沒有這支檔，所以只有全套看得到；其餘測試當次零 failure／零 error（47 支 Windows 專屬 skip）。
