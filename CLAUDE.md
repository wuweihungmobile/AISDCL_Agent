# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> **🔴 回覆語言**：本 workspace 下所有對話回覆**必須使用繁體中文**（專有名詞如 AISDLC、SDD、API、Docker、pytest 保持原文）。兩個子專案的 CLAUDE.md 皆以此為 override 級規範，絕不可用英文／簡體／日韓文回覆。

---

## 雙專案 monorepo

monorepo 根目錄（`AISDCL_Agent/`，各機器 checkout 路徑不同）＝**兩個獨立子專案 ＋ 一層根整合層**（根 `docs/`，承載兩者深度整合的迭代計畫，見〈三條改進軌道〉，勿與子專案內部的改進系列混淆）。

| 子目錄 | 性質 | 權威指引 |
|--------|------|---------|
| [AutoClaude/](AutoClaude/) | Python 3.11+ 應用程式 — Claude Code 多步驟 Playbook 自動執行引擎（微核心 + Plugin 體系 + DAL 三後端） | [AutoClaude/CLAUDE.md](AutoClaude/CLAUDE.md) |
| [AISDLC_SDD/](AISDLC_SDD/) | 規格先行（Spec-First）SDLC 框架 — Markdown 模板／Agent／Workflow + FSM runtime（Python）+ TLA+ 形式化驗證 | [AISDLC_SDD/CLAUDE.md](AISDLC_SDD/CLAUDE.md) |

🔴 **進入任一子專案前的第一動作＝先讀該子專案的 `CLAUDE.md`**。兩份皆宣告其指令 OVERRIDE Claude Code 預設行為，內含大量「違反即停機」禁令（尤其 AISDLC_SDD 的 Rule 9 自動化閉環防護）。本根檔只負責導航與跨專案鐵律，不重複子專案細則。

### 路徑陷阱

- 子專案 CLAUDE.md 內的相對路徑**相對於該子專案目錄**，不是相對於 monorepo 根；AISDLC_SDD 的 CLAUDE.md 把根稱為 `d:/CursorProject/AISDLC_SDD/`，實際對應本 repo 的 `AISDLC_SDD/`。
- 跑指令前讓工作目錄落在正確子專案——但 **Windows 側禁用裸 `cd`**（鐵律二）：改絕對路徑，或 `Push-Location <絕對路徑>` … `Pop-Location` 在**同一次呼叫內**成對。
- 🔴 **AISDLC_SDD 數十個版本目錄中只有 LATEST 可原地改**（掌舵者裁決）：`AISDLC_SDD_v0.01`（ci-gate 凍結基線）與其後到 LATEST 之間的中間歷史版一律**不可原地改**（ci-gate 只測「凍結基線 + LATEST」兩軌）。**LATEST 是哪一版一律現查** `python AISDLC_SDD/scripts/sdd_version.py`（本檔刻意不寫版號）。Copy-on-Evolve（`AISDLC_SDD/scripts/copy_on_evolve.sh`）**只**在需要保留可回歸對照快照時開新版，不是每次改動都開新版。

---

## 🔴 三條改進軌道（動工前先用本表對齊「本輪在哪一柱（A/B/C）、下一份檔名」）

| 軌道 | 計畫文件（驅動器） | 性質 / scope | 下一份 |
|------|------------------|-------------|--------|
| **① 整合迭代**（範本唯一驅動器） | 根層 [docs/04_planning/AutoSDD_improving_NN.md](docs/04_planning/) | 三柱對齊北極星：**A 軌**＝雙向協作橋接（SDD→Playbook）；**B 軌**＝手腳框架 dogfooding v0.0X 並回流缺陷；**C 軌**＝指揮官 AutoClaude 自身能力。由 [docs/04_planning/AutoSDD_Iteration_Prompt_Template.md](docs/04_planning/AutoSDD_Iteration_Prompt_Template.md) 驅動，每輪四件套（improving_NN + ZeroTrust_Audit_NN + Defect_Log 累積 + 框架改進落 `v0.0(X+1)/`） | `docs/04_planning/` 現存最大號＋1（動工前以 `ls` 實查；本欄不快照號次——快照必 stale） |
| **② 框架內部 RFC**（AISDLC_SDD 自身演進） | `AISDLC_SDD/AISDLC_SDD_v0.01/build/planning/active/SDD_improving_Automation_NN.md` | ①B 軌缺陷回流路徑之一；迭代的**下游帳本，不是驅動器** | 隨缺陷回流產生（非定期遞增） |
| **③ AutoClaude 內部能力**（＝① 的 **C 軌工作流帳本**） | `AutoClaude/docs/04_planning/AutoClaude_Improving_0NN.md` + `SD_Improving_NN.md` | 2026-06-15 起納入①範本 C 軌統籌驅動；本欄檔案為 C 軌工作流帳本（沿用 AutoClaude 自身 docs/ 編號與 G0~G6 Gate） | 以 `AutoClaude/docs/04_planning/` 現存最大號實查 |

**鐵律**：
- 要「推進整合／開新一輪迭代」→ **走軌道①**：複製範本、續 `AutoSDD_improving_NN`。**絕不**把 `SDD_improving_Automation_NN`（軌道②）當迭代計畫。
- 軌道② 只在 ①B 軌發現框架缺陷時作回流 RFC 帳本；缺陷先入根層累積帳本 [docs/06_quality/AutoSDD_Defect_Log.md](docs/06_quality/)。
- 軌道③ 由①範本 C 軌統籌；三柱同源不代表可混指，動工前先對齊本表。
- 三軌的 `docs/` 各自獨立編號（01~08）：軌道① 用**根層** `docs/`、軌道②③ 用各**子專案**的 `docs/`（見〈路徑陷阱〉）。

---

## 兩專案共通的工程紀律

1. **繁體中文回覆**（見頂部）。
2. **開發-編譯-測試循環（強制）**：每完成一支程式立即編譯＋跑單元測試，**絕不累積開發**；編譯／測試失敗立即停下修復，禁止跳過或註解掉失敗測試。
3. **文檔目錄編號制**：產出文件寫入 `docs/0[1-8]_*/`（01_requirements ～ 08_deployment）對應子目錄，不可亂放。
4. **規格先行**：寫程式前先有規格／通過閘門（AISDLC_SDD 的 SCG-0~6；AutoClaude 的 G0~G6 Gate）。

> hook 射程結論：根 session 生效的守衛見下方〈機械守衛總表〉；`enforce_docs_path.py`／`loc_budget_check.py`／`check_lang.py`／`claude_md_freshness.py` 四支僅 AutoClaude 子專案 session 生效，在根 session 一行都不會跑。

---

## 🔴 機械守衛總表（根 session；SSOT＝`.claude/settings.json`，總表一律現查）

| Hook | 事件／matcher | 作用 | 逃生口 |
|------|--------------|------|--------|
| `sdd_hook_router.py` | SessionStart；PreToolUse（Write／Edit／Read／Bash／NotebookEdit／Task）；PostToolUse（Write／Edit／Read／Bash／NotebookEdit） | SDD 治理橋接：`SDD_ACTIVE_VERSION` 未設＝休眠 no-op | `SDD_ROUTER_QUIET=1` 靜音 |
| `block_bash_on_windows.py` | PreToolUse／Bash | Windows 上禁用 Bash 工具（鐵律一）；非 Windows 一律 exit 0 | 無（掌舵者直接指令） |
| `lint_powershell_command.py` | PreToolUse／PowerShell | 擋「管線後讀 `$LASTEXITCODE`」、行首裸 `cd`／`Set-Location` 帶相對路徑、裸 `bash` + `.sh`（鐵律一、二） | 行尾 `# ps-lint-ok: <WHY>`（獨立註解行無效） |
| `block_destructive_git.py` | PreToolUse／Bash、PowerShell、Write、Edit、NotebookEdit | 毀滅性 git 形態阻斷（鐵律五）＋等待壞形態 `waitform_hits()`（鐵律六）＋治理檔禁寫（PRD §15.5 紅線 10：`AUTOSDD_UNATTENDED` 下保護面唯讀） | `AUTOSDD_GIT_GUARD_OFF`（模型碰不到，須在啟動 claude 前設）；`AUTOSDD_GOVWRITE_GUARD_OFF`（治理面唯讀專屬，與 git 族開關互不相通）；行內 `# git-guard-ok: <理由>`／`# waitform-ok: <WHY>`（`AUTOSDD_UNATTENDED` 有設時行內豁免無效） |
| `context_budget_guard.py` | SessionStart（自動武裝額度哨兵）；PostToolUse（Read／Task／Grep／Glob／WebFetch／WebSearch／Bash／PowerShell：水位出聲）；PreToolUse（Task／WebFetch／WebSearch／Agent／Workflow：高水位**真的擋下**展開型工具） | context 三段式水位的機械物（見下節）；matcher 刻意不含 Read／Edit／PowerShell——收斂本身需要它們 | `AUTOSDD_CONTEXT_GUARD_OFF`（context 阻斷）／`AUTOSDD_SENTINEL_OFF`（額度哨兵）——**刻意兩個開關**，關掉的是不同的東西 |
| `check_claim_provenance.py` | Stop | 鐵律四的機械物：量化判決宣稱（`N passed`／`rc=N`…）必須在本場自己的 tool_result 出現過；**只出聲、永不阻斷**；轉述別包交件標 `[他包回報]` | `AUTOSDD_CLAIM_GUARD_OFF`；`AUTOSDD_UNATTENDED` 有設時詞表縮到只認方括號標記 |
| `check_ps1_encoding.py` | PostToolUse／Write、Edit | `.ps1` 寫入當下就地補回 CRLF（橋接自 AutoClaude tools/hooks） | 無 |
| `check_sh_eol.py` | PostToolUse／Write、Edit | `.sh`／`.bash` 行尾守門（非 `.sh`／`.bash` → exit 0；橋接自 AutoClaude tools/hooks） | 無 |

文件宣稱 ↔ 註冊實況由 `tools/tests/test_doc_loc_baseline_freshness_r60.py::TestR74RootClaudeMdHookClaimsMatchRegistration` 與 `tools/tests/test_doc_loc_baseline_freshness_r60.py::TestR79EveryRegisteredHookIsNamedInClaudeMd` 雙向＋第三向機械釘住（已註冊未點名、未註冊卻寫成會跑，皆紅）。

### hook 載具（鐵律一之二：exec form）

- 根層 hook 條目一律 **exec form**（帶 `args`，Windows 載具指向 GUI 子系統 `pythonw.exe`）——shell form 在 Windows 每觸發一次就閃一個 console 視窗。
- 🔴 **不對稱風險**：exec form 載具解析不到時 Claude Code **fail-open**（只記 ERROR、工具照跑）⇒ 全部守衛靜默失效，表徵與「修好了」完全相同。**「不閃窗了」永遠不算驗收通過**，正負兩面一起看：

```powershell
Test-Path (Join-Path $env:CLAUDE_PROJECT_DIR '.venv\Scripts\pythonw.exe')   # 載具在不在，必須 True
claude -p --model haiku --debug hooks --debug-file h.log "ok"
Select-String -Path h.log -Pattern 'Hook SessionStart.*success'             # 正面現查：有 success 才算活著
```

- 佈線解析唯一真相源＝`tools/lib/hook_wiring.py`（`SHELL_FORM_CENSUS` 登記「哪一份 settings 還剩幾條沒轉」，相等判準：退回 shell form 紅、轉好沒回來改表也紅；凍結歷史面走 `FROZEN_SHELL_FORM_MAX` shrink-only 豁免）。格數與值一律現查該檔。
- `AISDLC_SDD/<LATEST>/.claude/settings.json`（真的會被載入的活躍檔）已轉 exec form，以版本中性鍵進普查表（LATEST 走 SSOT `tools/lib/sdd_latest.py` 現查）。誠實劃界：形態判準 A~F 與載具存在性的掃描面**只有根檔**，其餘各份只被 shell form 條目數守著。
- 機械物：`tools/tests/test_check_hooks_liveness.py`（形態判準 A~F ＋ 啟動器契約 ＋ 載具存在性，含紅綠自證；不斷言機器狀態）；`tools/check_hooks_liveness.py`＝開發機上會出聲的那一層（CI 刻意跳過：CI 從不執行 Claude Code hook）。

---

## 🔴 Token 將耗盡時的「無害暫停 → reset 後重啟」SOP

### 三段式水位（context 尺）

| Token 水位 | 動作 |
|-----------|------|
| ~84% | 收斂前置訊號。機械 autocompact 已由 repo settings 釘在 auto-compact window 的 90%（`autoCompactEnabled: true` ＋ `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=90`，不靠人記得 `/compact`）。此時仍可開新工作 |
| ~94% | 「壓縮沒發生」失效警報＋停止開新戰場，收斂到「可重啟點」（見下）並寫任務書。**只做收斂，不做展開** |
| 撞上限 | 記下 CLI 印出的 **reset 時間**＋**本 session ID**；reset 後 `claude -r <sessionId>`。額度哨兵（見下）已機械接手，不只靠人記得 |

🔴 **這張表量 context 水位；額度是另一把尺**：額度四道門檻（注意／收斂／準備／停止）住 `tools/lib/quota_policy.py`，**百分比一律現查** `python tools/lib/quota_policy.py --print-env-example`，本檔不複寫數字。兩者分母不同、守衛不同，**不要互相換算**（兩把尺不得同值，有測試釘住）。「準備」帶會動作：進帶後第一次工具呼叫出聲一次＋把可重啟點任務書寫到磁碟，一個 reset 視窗只做一次、不改 rc。機械物＝`context_budget_guard.py`（見機械守衛總表）。

### 額度哨兵（額度尺；設計全文 ADR-XPLAT-004 §2.6／§2.7）

- **額度 ≠ context 水位**：撞額度那一刻水位可能很低，context 守衛全數放行。「額度耗盡」是 API 層失敗，**hook 體系沒有任何觸發點** ⇒ 只能**預防性**武裝：SessionStart 自動 `--arm-sentinel`（Windows schtasks，巡邏**只讀逐字稿、零 token**；讀到未處理撞線才轉續航排程）。「撞了沒」寫在逐字稿裡讀檔即知；「額度回來了沒」只能問伺服器——這個不對稱是哨兵成立的原因。
- **reset 時刻是滾動視窗，只能觀測不能算**：解不出時刻一律**拒絕武裝**，不准退回「假設 5 小時」；分佈現查 `python tools/probe/reset_window_distribution.py`。
- 兩條閾值的方向鎖具名測試：`test_the_patrol_interval_bounds_the_post_reset_dead_time`（巡邏間隔＝reset 後最壞死等時間的上界，只准調小）／`test_the_idle_threshold_outlives_a_whole_quota_window`（自我解除門檻須大於一個完整額度視窗）。註冊面與四分支判定＝`tools/tests/test_context_budget_guard.py::SentinelWiringTest`／`tools/tests/test_context_budget_guard.py::SentinelDecisionTest`。
- 現查哨兵（**平台各一條，不要照抄另一邊**）：Windows 用 `Get-ScheduledTask`（見下方取證規則，憑證＝NextRunTime 值）；macOS 用 `launchctl list` 過濾 AutoSDD_Sentinel_（**憑證是 rc，不是時間值**——launchd 從不報下次幾點跑）。
- 痕跡兩處、壽命不同：事件檔 `autosdd_resume_log_*.jsonl` 住系統暫存（重開機即消失，「查不到」≠「沒發生」）；分支／等待痕跡落持久目錄 `~/.autosdd/traces`（逃生口 `AUTOSDD_TRACE_DIR`，唯讀時退回暫存；SSOT＝`tools/lib/endurance_env.py`）。兩處皆「沒觸發＝檔不長大」，可偵測。
- 🔴 **mac 已知邊界（不是待修 bug）**：睡著的 Mac 不會被喚醒；`pmset repeat` 需 sudo、本專案刻意不碰。交付的是「失效可偵測」：武裝路徑現查 `pmset -g custom`，任一電源段睡眠設定不是「永不睡」即在 stderr 出聲並落痕跡。該值不在 repo、不隨 clone 走，**一律現查、不得寫成常數**。機械物＝`tools/lib/endurance_env.py`＋`tools/tests/test_mac_endurance_r83.py::MacSleepPostureIsSaidOutLoudTest`。

### 「可重啟點」四條件（缺一就不算安全暫停）

1. **工作樹狀態確定**：要嘛已 commit 且閘門全綠，要嘛 `git stash create` ＋ `git tag <輪次>-wip-preserved` 保全。**絕不留半套 edit 就走**。
2. **任務書落在磁碟**（對話會被 compact、session 會換）：正式的寫 `docs/04_planning/` 或缺陷帳本；臨時的放 scratchpad 並在回覆中給出**絕對路徑**。
3. **任務書必含四項**：已驗證什麼（附實測數字與 rc）／還沒做什麼／下一步的**確切指令**／**禁止事項**（例：不准 `--no-verify`、不准 `AUTOCLAUDE_SKIP_HOOKS=1`）。
4. **重啟後第一件事是重驗**，不採信任務書裡任何「已通過」宣稱（zero-trust 雙向，對自己上一段的宣稱亦然）。

### 重啟指令（`claude --help` 實查）

```bash
claude -r <sessionId>   # 帶回完整 context 續跑 ← 推薦：高風險動作（commit/push）仍有人在
claude -c               # 續接最近一次對話
```

- session ID＝`~/.claude/projects/<專案 slug>/` 下**最後修改**的那支 `.jsonl` 檔名。**暫停前務必寫進任務書**。
- 要全自動才加 OS 排程（schtasks 叫 `claude -p -r <sessionId> "<任務書>"`），必須寫 log 取證、只允許低風險動作。`claude -p` 這種非互動 subprocess spawn 在 `CLAUDECODE=1` 下可於 session 內驗；仍掛住的是 wexpect pty spawn 那一條（DEF-101-913，見 `docs/06_quality/CrossPlatform_R79_Debt_Audit.md`）。

### 工具選型（別再選錯）

| 需求 | 工具 | 邊界 |
|------|------|------|
| **Token reset 後重啟** | **磁碟任務書 ＋ `claude -r`** | 唯一不依賴 session 存活的路 ← 本節主線 |
| session 開著、人離開一下要它自己做完 | `/loop`／`ScheduleWakeup` | 同 session、同一個 Token 池；單次上限 1 小時、終端全程不能關；🔴 **沒有任何憑證**（不寫磁碟、無登錄、拿不到 NextRunTime）⇒ 失效是靜默的，**不是 token reset 的方案** |
| 開工前先掛額度哨兵 | `python tools/session_resume_planner.py --arm-sentinel` | SessionStart 已自動做；此列是手動補武裝／驗證用。憑證同為 NextRunTime |
| **派工前問「現在能派幾個 agent」** | `python tools/session_resume_planner.py --pace` | 零 token。🔴 值是 (水位%, 距 reset) 的函式——**每次派工前現查，不得記住上次的值** |
| 跨 session／機器會睡的定時工作 | `schtasks`（照 `tools/install_windows_nightly.ps1` 的 `New-ScheduledTaskSettingsSet` 建法；該安裝器住 monorepo 根層 `tools/`） | 四項設定缺一即漏跑：`WakeToRun=True`／`StartWhenAvailable=True`／`DisallowStartIfOnBatteries=False`／`StopIfGoingOnBatteries=False`（cmdlet 參數名與物件屬性名**不同**，見該檔檔頭 DEF-101-249） |
| ❌ 不要用 | `CronCreate` | `CronList` 印 `[session-only]`＝session 關掉就沒了，**不是離線排程** |

### 🔴 反「事後諸葛」取證規則

- **宣稱「已排程／會自動繼續」的同一則回覆裡，必須貼出排程器自己回報的下次執行時間實測輸出**；貼不出來就不准宣稱，只能說「我做不到，請你改用 X」。排程也是一種 PASS 聲稱。
- 🔴 **憑證是 `NextRunTime` 這個「值」，不是指令的 rc**：`Get-ScheduledTask` 對不存在的工作回 rc=0（非終止錯誤）。工具側已機械化：`next_run_time()` 取不到非空字串即回非零 rc；`relay_problems()` 禁止空 NextRunTime 寫成 armed／waiting。
- 查排程一律用 `Get-ScheduledTask`（`schtasks /query /fo CSV` 實測假陰性）；工作清單是會漂移的量測值，一律現查：

```powershell
Get-ScheduledTask | Where-Object TaskName -like 'AutoClaude*' | Select-Object TaskName,State
Get-ScheduledTask -TaskName '<名稱>' | Get-ScheduledTaskInfo |
  Select-Object TaskName,LastRunTime,LastTaskResult,NextRunTime   # NextRunTime 就是憑證
Get-ScheduledTask | Where-Object TaskName -like 'AutoSDD_Sentinel_*' | Get-ScheduledTaskInfo
```

- 排出去的 job 必須留下可稽核痕跡（log 檔＋時間戳），讓「沒觸發」是**可偵測**而非靜默假設。

---

## 🔴 Windows 側單一載具原則（鐵律一～七；五～七平台無關）

> 失誤歸因是量測值不是常數：每輪重跑 `python tools/probe/misstep_attribution.py`（輸出可 diff 的 `.jsonl`），百分比不得引用為常數。結構性根因＝雙 shell 決策負荷＋鎖射程失明＋宣稱先於查證，三層各有機械物（見各鐵律）。

### 鐵律一：Windows 上**禁用 Bash 工具**，一律走 PowerShell 工具

> 掌舵者 2026-08-03 直接指令（原文：「只使用 PowerShell 5.1, 不用 Git Bash ==> 請遵守」）。「兩個載具擇優」這個選項已被移除——擇優本身就是要付注意力的決策。機械物＝`block_bash_on_windows.py`（見機械守衛總表；非 Windows 一律 exit 0，mac/Linux 上 bash 才是正確載具）。

- **引擎差異**：PowerShell 工具跑的是 pwsh 7.x（Core）；凡標的是 **PS 5.1 語意**者（`tools/windows_smoke_local.ps1`、`tools/install_windows_nightly.ps1`、任何 schtasks Action）**一律顯式外呼** `powershell.exe -NoProfile -ExecutionPolicy Bypass -File <絕對路徑>`。
- **讀 rc 不接管線**：提前結束管線的元素會污染 `$LASTEXITCODE`，且污染值隨引擎而異（pwsh 7.x 保留前值＝真紅讀成綠；5.1 寫入 -1）——沒有一個方向可以靠記憶避開。要看輸出就先接到變數，或讓 Python 用 `subprocess.run(...).returncode` 取。機械物＝`lint_powershell_command.py`。
- **執行 `.sh`**：PowerShell 內用 repo SSOT 解析 Git Bash ＋ 正斜線路徑：`. "$(git rev-parse --show-toplevel)/tools/lib/Find-GitBash.ps1"; & (Find-GitBash) -n '<正斜線腳本路徑>'`。❌ 不可裸 `bash <script>`（`Get-Command bash` 解析到 system32 的 WSL 佔位版、反斜線分隔符會被吃掉）；❌ 不可寫死安裝路徑（一台機器的偶然事實不得成為本檔常數，`Find-GitBash` 才是 SSOT）。
- **讀檔／搜尋／算行數用 Read／Grep 工具**，不經 shell：編碼邊界**雙向**都會出錯（CP950↔UTF-8 兩向皆有實證假數字）；要在 shell 內讀就必須指名 `-Encoding utf8`。

### 鐵律二：一律絕對路徑，禁用裸 `cd`

PowerShell 工具的 cwd **跨呼叫持續**。✅ 絕對路徑；✅ `Push-Location <絕對路徑>; …; Pop-Location` 同呼叫成對；❌ 先 `Set-Location` 下一個呼叫再用相對路徑。機械物＝`lint_powershell_command.py`（行首裸 `cd`／`Set-Location` 帶相對路徑當場擋下；行尾豁免 `# ps-lint-ok: <WHY>`）。事後量測的另一半＝`tools/probe/audit_session.py`（不接任何閘門的 rc）。

### 鐵律三：寫跨平台程式碼時，強制自問「**這在另一個平台是什麼值？**」

觸發清單（出現任一就必須自問）：`$env:*` 讀取／副檔名判斷／路徑分隔符／`Get-Command` 解析／console 編碼／行尾／大小寫敏感度／`$IsWindows` 這類 PS 6+ 專屬自動變數（5.1 恆 `$null`，需 `# ps7-ok: <WHY>` 行尾豁免，**獨立註解行無效**）。

> 下游消費者：`AISDLC_SDD/<LATEST>/agent/core/05.sd-architect-zh.yaml` 的 ADR 自動觸發清單以**本表**為單一真相源；SD agent 端不得自行維護第二份清單。

🔴 哪幾項有掃描器**一律以下表為準**（本段不複寫覆蓋數字，判準讀的就是這張表本身）：

| 觸發項 | 機械物 | 違反時什麼會紅 |
|--------|--------|----------------|
| 路徑分隔符 | `tools/tests/test_platform_neutral_paths.py` | 根層 unittest 閘門 |
| console 編碼 | `tools/tests/test_subprocess_encoding_hygiene.py` | 同上 |
| 行尾（`.sh`／`.bash` 方向） | `tools/tests/test_pre_commit_dispatcher_sigpipe.py::TestPreCommitBlocksCrOnShellScripts` ＋ `AutoClaude/tools/hooks/check_sh_eol.py`（射程**只有** `.sh`／`.bash`，非此二者 → exit 0） | 同上 ＋ PostToolUse hook |
| 行尾（**`.ps1` 方向**，政策要求工作樹為 CRLF） | `AutoClaude/tools/hooks/check_ps1_encoding.py`（PostToolUse，寫入當下就地補回 CRLF）＋ `tools/tests/test_platform_neutral_paths.py::TestWorktreeEolMatchesPolicy`（事後兜底） | 同上 ＋ PostToolUse hook。CI 那道結構上恆綠（checkout 必定重新 smudge），只有本機工作樹看得到漂移 |
| 行尾（**`.py` 方向**，`.gitattributes` 宣告 `text eol=lf`） | `tools/tests/test_platform_neutral_paths.py::TestActiveSourceEolIsRatchetedSeparatelyFromTheFrozenSurface`（活躍面止血：新漂移必紅；凍結面只登記不判） | 根層 unittest 閘門。`git status` 與 CI 對此漂移結構上看不見 |
| `#!` shebang ＋ 非 LF 行尾（`\r` 會黏進直譯器名） | `tools/tests/test_platform_neutral_paths.py::TestShebangImpliesLfLineEndings` | 根層 unittest 閘門。判準取「shebang × CRLF × exec bit」的交集（兩個各自正確的動作合起來才炸） |
| naive 本地時間戳被持久化（不帶 offset 的 ISO 字串） | `tools/tests/test_platform_neutral_paths.py::TestNaiveLocalTimestampsAreNotPersisted` | 根層 unittest 閘門。跨 DST 的 naive 相減完全靜默；本機時區不實施 DST ⇒ 本機結構上重現不了 |
| `shell=True` 的原生殼差異（Windows 走 `cmd.exe`、POSIX 走 `/bin/sh`） | `AutoClaude/tests/execution/test_shell_portability_contract_r85.py`（執行期診斷 ＋ 兩個執行面的射程普查 ＋ 以真實 playbook 為母體的假紅普查） | AutoClaude pytest 閘門。判準刻意只出聲不阻擋。🔴 兩個看似正確的修法已被實測否決：`shell=False`＋argv（CONDITIONAL 慣用 shell builtin，殼在這條路上承重）；改白名單語意（那是 Gap-046 資安過濾器，兩軸一起壞） |
| hook 行程生出來的子行程配到 console 視窗（`subprocess` spawn 外部 console 執行檔） | `tools/tests/test_context_budget_guard.py::ConsoleFreeSpawnTest`（掃 `.claude/hooks/`）＋ `tools/tests/test_check_hooks_liveness.py::TestAutoClaudeHookSpawnsAreConsoleFree`（掃 `AutoClaude/tools/hooks/`） | 根層 unittest 閘門。與「hook 條目形態」是兩件事：exec form 治載具視窗；載具 spawn `git.exe` 時 OS 另配新 console。判準只判「argv[0] 不是 `sys.executable`」那些，避免假紅 |
| exec bit／git 索引檔案模式 | `tools/tests/test_platform_neutral_paths.py::TestExecBitIsGovernedViaTheGitIndex` | 根層 unittest 閘門。誠實劃界：Windows Git Bash 的 `[ -x ]` 是檔首內容猜測，判準只守 tracked 100755 檔的檔首形態，安裝產物那一半仍無人守 |
| Windows 檔案鎖：會改動目錄項的原語（`os.replace`／`rename`／`move`） | `tools/tests/test_platform_neutral_paths.py::TestDirEntryPrimitivesAreAccountedFor` | 根層 unittest 閘門。換一個原語（`os.replace` 覆寫被開著的目的檔 → WinError 5）就整片失明，不只 `unlink`／WinError 32 |
| `$IsWindows` 等 PS 6+ 專屬 | `tools/tests/test_ps51_compat.py` | 根層 unittest 閘門 |
| `$env:*` 讀取 | `tools/tests/test_platform_neutral_paths.py::TestPowerShellPlatformSensitiveSites`（站點級：`$env:TEMP`／`$env:TMP` 的讀取逐檔登記，新增即紅）＋ `tools/tests/test_platform_neutral_paths.py::TestPathextReadsAreePlatformGuarded`（`PATHEXT` 專屬） | 根層 unittest 閘門。判準刻意只判這兩個變數：全判會製造大批要逐一辯護的假紅，那種鎖活不過一輪 |
| 副檔名判斷 | **無機械物** | 同上（DEF-101-766 的另一半）。缺的是**寫入面**判準：存量已近乎清空，今天蓋存量掃描會回 0 命中而給假安心 |
| `Get-Command` 解析 | `tools/tests/test_platform_neutral_paths.py::TestPowerShellPlatformSensitiveSites`（站點級：裸 `Get-Command bash` 只能出現在 SSOT `tools/lib/Find-GitBash.ps1`，別處寫出即紅）＋ `tools/tests/test_find_git_bash_parity.py` | 根層 unittest 閘門。裸解析拿到 system32 的 WSL 佔位版（DEF-101-617/618） |
| 大小寫敏感度 | `tools/check_ntfs_paths.py`（tracked 路徑正規化鍵 NFC→lowercase 的大小寫碰撞判準）＋ `tools/git-hooks/pre-commit`（同一判準的 commit 期版本） | pre-commit hook ＋ 四支 CI workflow 皆呼叫該腳本 |
| `git 路徑列舉`（非 ASCII 引號化） | `tools/lib/git_paths.py`（取數層 SSOT）＋ `tools/tests/test_platform_neutral_paths.py::TestGitPathEnumerationIsQuotepathSafe`（新站點漏帶 `-c core.quotepath=false`／`-z` 即紅，行尾豁免出口 `quotepath-ok:`） | 根層 unittest 閘門。判準不依賴本機 `.git/config`（那個檔不隨 repo 走） |
| BSD/GNU `coreutils` 分歧 | `tools/tests/test_bash32_compat.py`（`.sh`／git-hooks 六棵樹）＋ 同檔 `::TestWorkflowInlineRunIsBsdSafe`（workflows 的 inline `run:`，以 `runs-on` 當判準輸入） | 根層 unittest 閘門。macos-capable workflow 零容忍；ubuntu/windows-only 走 shrink-only 棘輪 |
| 單平台專屬**外部執行檔的 argv[0] 字面**（`powershell.exe`／`osascript`／`launchctl`／`taskkill`…） | `tools/tests/test_platform_neutral_paths.py::TestForeignExecutableArgvIsGuarded`（詞彙表 SSOT＝`tools/probe/xplat_hazard_census.py`；含 transitive 可達性，深度上界 3） | 根層 unittest 閘門。與下一列**不是同一族**：外部執行檔名不是 Python 符號。transitive 刻意不回頭套到下一列（那張債表是雙向精確比對） |
| 單平台專屬 API 詞彙表（`os`／`signal`／`ctypes`／`subprocess`／`preexec_fn`） | `tools/tests/test_platform_neutral_paths.py::TestForeignPlatformApiIsGuarded`（站點級守衛五種罩法）＋ 同檔 `::TestForeignApiVocabularyOnlyGrows`（表驅動 owner／attr 數只准上升的後設鎖） | 根層 unittest 閘門。刻意不判 `creationflags=` kwarg 本身：現行站點一律傳 `getattr` 兜底常數＝正解，判它就是整批假紅 |
| 排序鍵影響雜湊（`sorted(Path)` 的平台相依序） | `tools/tests/test_platform_neutral_paths.py::TestDigestSortKeyIsPlatformNeutral`（`for … in sorted(<glob/rglob/iterdir>)` 且迴圈體餵 digest 卻沒帶 `key=` 即紅） | 根層 unittest 閘門。判準刻意只判「餵 digest」形態：全面判是上百筆假紅 |
| 文字模式檔案 I/O 的預設編碼（`open`／`read_text`／`write_text`） | `tools/tests/test_platform_neutral_paths.py::TestTextIoDeclaresEncoding`（AST 判準＋`_ENCODING_DEBT_RATCHET` shrink-only 存量棘輪） | 根層 unittest 閘門。與「console 編碼」列不同軸——那一列的射程是 subprocess 與 stdio |

上表由 `tools/tests/test_doc_loc_baseline_freshness_r60.py::TestR74IronLawMechanismAccounting` 釘住：**分子（有機械物列數）與分母（已登記危害類數）皆只准上升**，floor 落後現值超過容忍即紅；「還有幾類沒人守」＝分母−分子，刻意不設上限（誠實登記新危害不得有代價）。補了掃描器改該列機械物欄（不刪列）；表內每個具名檔案必須存在且**真的在守該列主題**（`TestR75IronLawMechanismSubstance` 關鍵詞實質判準）；自陳「無機械物」的列必須登記證偽探針（`tools/tests/test_platform_neutral_paths.py::TestIronLaw3NoMechanismClaimsAreFalsifiable`）。

🔴 動這張表（合併／刪除鎖檔）有「跨檔參照稅」：git-tracked 缺檔的 fail-loud 只有 `git rm`／stage 能消除，而並行包禁止 git 操作 ⇒ **淨減法只能由收尾單人窗口做**（鐵律七的同型結論）。

### 鐵律四：宣稱先於查證是最大失誤桶——**任何「已驗證／已達標／零損失」宣稱都要附當回合真跑的輸出**

貼不出來就改寫成「未驗證」。機械物＝`check_claim_provenance.py`（Stop 事件，見機械守衛總表）：判準收在**值域**上——量化判決數字必須在本場自己的 tool_result 出現過；自己跑的必然對得上，轉述別包標 `[他包回報]`。誠實劃界：**不帶值**的判決（「全綠」「已驗證」「零損失」）本 hook 結構上看不見，那一面由事後量測器 `tools/probe/audit_session.py` 覆蓋（依其檔頭自述不得接成閘門）。

### 🔴 鐵律五：毀滅性 git 指令已由 PreToolUse 阻斷（平台無關）

立案＝多包並行**共用工作樹**上的 `git stash` 真實事故（禁令沒涵蓋到的動詞就是被踩的那個）⇒ 修法是**列舉毀滅形態**機械阻斷，不是加長動詞清單。機械物＝`block_destructive_git.py`（PreToolUse／Bash、PowerShell），回歸鎖 `tools/tests/test_block_destructive_git_r83.py`。

| | 形態 |
|---|---|
| **擋** | `git stash`（含裸 stash＝push／`push`／`pop`／`apply`／`drop`／`clear`／`save`）／`git checkout -- <path>`／`git checkout -f`／`git restore <path>`／`git reset --hard`｜`--merge`｜`--keep`／`git clean`／`git switch -f`｜`--discard-changes` |
| **放行** | 🔴 `git stash create`（〈可重啟點四條件〉第 1 條**指定**的保全手法）／`git stash list`｜`show`／`git reset`（mixed）與 `--soft`／`git restore --staged`（只動 index）／`git clean -n`／純切分支（`-b`／`-c`／不帶 `--` 路徑）／所有唯讀查詢 |

- 判準必須精準是設計約束：擋到讓人無法工作的守衛會被整個關掉，比沒有守衛更糟。假紅普查一律現跑 `python tools/probe/shell_command_corpus.py --summary`；🔴 **兩個母體不能互相替代**——hook 類判準的假紅普查一律以 `--corpus transcripts`（真實輸入面）為母體，tracked 面只回答「repo 內寫死的腳本會不會被擋」。
- 逃生口兩個、刻意分層且不與既有變數共用：`AUTOSDD_GIT_GUARD_OFF`（模型碰不到——hook 讀自己行程的環境，指令字串裡寫 `VAR=1 git stash` 無效；須在啟動 claude 前設）；行內 `# git-guard-ok: <理由>`（理由必填、須住真註解；`AUTOSDD_UNATTENDED` 有設時無效）。
- **擋不到什麼的唯一真相源＝該 hook 檔頭的〈誠實劃界〉節**（本檔刻意不複寫清單），現查：`grep -n "擋不到" .claude/hooks/block_destructive_git.py`。
- 射程外另案：`git rm`｜`branch -D`｜`push --force`（毀的不是未提交的工作樹內容）。

### 🔴 鐵律六：等待／確認機制自己靜默壞掉 ⇒ 無做工空轉（平台無關；DEF-200-044）

**總則（掌舵者 2026-08-11 直接要求）**：除了「等額度 reset」與「等人介入」兩種合法停等，任何停等都必須有一個**會主動叫醒我的事件源**；掛不掛得上是**派工前**就要決定的事，掛不上就換形態派工。

| | 形態 | 為什麼 |
|---|---|---|
| ✅ | `run_in_background: true` 搭一個**會阻塞到真的做完**的指令 | 有契約的事件源：Bash 工具說明逐字寫 `it keeps running across turns and re-invokes you when it exits` ⇒ 該行程必須一直活到工作真的做完 |
| ✅ | 掛 Monitor／until-loop，且**條件的比對面不含自己**（字元類自我否定）：`until ! pgrep -f 'run_root[_]unittests'; do …; done` | 只否定自己、不減損鑑別力 |
| ❌ | `nohup <cmd> > log 2>&1 &` | 工作脫離 harness 的完成追蹤：外層殼 0 秒返回 rc=0，通知講的是外層殼 |
| ❌ | 裸 `pgrep -f <字面>`／`pgrep -f "python.*X"` | 兩支並行時兄弟互匹 ⇒ `until ! …` 永不退出；單支試跑永遠是綠的，死鎖只在並行時現形 |
| ❌ | 讀 rc 時接管線 | 真 rc 被吃掉（接 `tail -1` → rc=0）。mac 工具殼是 zsh：`${PIPESTATUS[0]}` 回空字串、要寫 `${pipestatus[1]}`——機制與修法住 `useMacWin.md` §C，本節不複寫 |

- 機械物＝`block_destructive_git.py` 的 `waitform_hits()`（行內豁免 `# waitform-ok: <WHY>`）。**判準有哪幾條、各判什麼，唯一真相源＝該函式 docstring**（本段刻意不複寫條列），現查：`sed -n "/^def waitform_hits/,/\"\"\"$/p" .claude/hooks/block_destructive_git.py`。
- 誠實劃界：攔截器接得住「寫出壞形態」，接不住「該掛的沒掛」（Monitor 掛沒掛不在任何指令字串裡）；「讀 rc 接管線」在 Bash／zsh 側零攔截器（唯一守它的 `lint_powershell_command.py` matcher 是 PowerShell）——DEF-200-086。逐筆座標見 [docs/06_quality/AutoSDD_Defect_Log.md](docs/06_quality/) 的 DEF-200-044／045／086。

### 🔴 鐵律七：並行派工前，先切「鎖的持有面」（平台無關；DEF-200-049）

一道機械鎖的**常數／史料／消費端**常住在不同檔；切給不同的包，那件事在任何單包手上都做不完，該包只能回報 `not_done`。**派工紀律**（與「並行修復波先對配額做預算」並列的前置檢查）：任務書要對每個包列出「你要動的鎖，其常數／史料／消費端分別住哪幾支檔」；三者不在同一持有面時不得派給並行包——淨減法只能由收尾單人窗口做。

---

## AutoClaude — 快查（完整見 [AutoClaude/CLAUDE.md](AutoClaude/CLAUDE.md)；指令在 `AutoClaude/` 下執行）

### 安裝 / 執行

> 🔴 `uv` 建的 `.venv` **內部沒有 `pip` 模組** ⇒ 一律用 `uv pip install`；extras 一律加單引號 `'.[...]'`（zsh 會對未引號的 `.[dev,notifications]` 做 filename generation 而中止整條指令）。雷區對照見 [ONBOARDING.md](ONBOARDING.md) §5。

```bash
uv pip install -e '.[dev,notifications]'   # 開發環境；另有 '.[lint]'、'.[postgres,pgvector]'
python -m autoclaude <playbook.yaml> [--config config.yaml] [--fresh]
```

### 測試 / Lint

```bash
python -m pytest tests/ -q      # 全套（🔴 基線數字唯一出處＝根層 ONBOARDING.md §7，本檔不重複數字）
PYTHONUTF8=1 lint-imports        # import-linter（契約條數 SSOT＝AutoClaude/.importlinter 的 name = 行；rc=0 即全 kept）
ruff check <改到的檔>            # 規則集 SSOT＝AutoClaude/pyproject.toml 的 [tool.ruff]；只 lint 改到的檔（整棵樹有存量債，另案）
python -m pytest tests/ -m pg_real   # 真 PG e2e（需 SD07_REAL_PG_E2E_ENABLED=true + PG DSN）
```

- 🔴 上列為 bash 形態。PowerShell **沒有** `VAR=value <指令>` 前綴語法，Windows 須寫 `$env:PYTHONUTF8=1; lint-imports`（雙平台對照見 [ONBOARDING.md](ONBOARDING.md) §7；DEF-101-513）。

### 本機 CI 對等 / Nightly（push 前全綠）

```powershell
powershell -ExecutionPolicy Bypass -File tools/install_git_hooks.ps1   # 裝 git hooks（根層 dispatcher，兩子專案閘門同時生效）
powershell -ExecutionPolicy Bypass -File tools/local_ci_gate.ps1       # 一鍵本機 CI 閘門
powershell -ExecutionPolicy Bypass -File tools/run_local_nightly.ps1   # nightly 7 stage
docker compose -f docker-compose.ci.yml up -d                          # CI 對等 PG＝第一步
python -m alembic upgrade head                                         # 🔴 第二步，缺它等同沒起 PG
```

- macOS/Linux 對等腳本已存在（`tools/local_ci_gate.sh` 等；完整雙平台對照見 [ONBOARDING.md](ONBOARDING.md) §6）。CI workflows 全數住根層 `.github/workflows/`（對照見 ONBOARDING.md §6.1）；`claude-md-budget` 閘**僅指 `AutoClaude/CLAUDE.md`**（≤400 行＋snapshot 新鮮度），根層與 AISDLC_SDD 兩份不受此閘。
- 🔴 **容器 healthy ≠ DB 已 migrate**：容器是 tmpfs，每次重建都要再 migrate，漏了時 PG 測試整批 skip、表徵近似「沒起 PG」。**憑證＝`local_ci_gate.pg_autodetect()` 回出 DSN，不是 `docker ps` healthy**；失效會在 pytest 摘要印醒目段（SSOT＝`AutoClaude/tools/local_ci_gate.py` 的 `PG_UNMIGRATED_HINT`）。

### 架構大圖（約束）

**Hexagonal／微核心**：`core/`（Kernel + EventBus + HookSpec + `ports/`）只依賴 ports；`infra/adapters/` 具體實作；`infra/repositories/`＝DAL 三後端（File／InMemory／Pg + Dual）；`plugins/` 彼此**不可互 import**（協作走 EventBus）；`execution/playbook_runner.py` 是無業務邏輯 thin facade。Plugin／Port 清單與計數一律見 AutoClaude/CLAUDE.md 的機械生成 `[Architecture Snapshot]`（本檔不重複數字）。
狀態機閉環：INIT → PRE_RUN_VALIDATE → EXECUTE(step) →（Token Guard：≥80% `/compact`、≥90% checkpoint）→ EVALUATE →（CORRECTION／ESCALATION → 自演化）→ DONE → GOAL_SYNTHESIS。

- 架構約束以 `.importlinter` contract 機械強制（條數現查該檔）＋ LOC 分級政策：**分級表與絕對紅線唯一真相源＝`AutoClaude/tools/check_loc_budget.py`**（`LOC_TIERS`／`ABSOLUTE_LIMIT`），現查 `python AutoClaude/tools/check_loc_budget.py --json`；機械物＝`tools/tests/test_adr_xplat001_c1c2_lock.py::TestLocTierTableHasOnlyOneHome`。
- 🔴 根層護欄層（`tools/` ＋ `.claude/hooks/`）另有**自己一套分級**（SSOT 同檔：`ROOT_TOOLS_TIERS`／`SPECIAL_FILES`／hub tier，hub 成員清單只縮不長）；`SPECIAL_FILES` 棘輪雙邊咬人（門檻明顯高於現值即阻塞並要求重釘為現值）。根層 `tools/tests/` 不受 LOC 分級管轄，但重釘要付代價（`tools/tests/test_adr_xplat001_c1c2_lock.py` 的 `repin_growth_problems()`：單輪淨額上限＋連續上升輪數上限，兩常數只准下修）。數字一律現查，本檔不複寫。

### 新增 Plugin 的 SOP

1. 建 `autoclaude/plugins/<feature>_plugin.py`（繼承 HookSpec，PascalCase 類別）；2. 實作對應 hook；3. 加入 `wiring._REGISTER_ORDER`，相依走 constructor 注入 ports（**禁止直接 import infra**）；4. 寫 `tests/plugins/test_<feature>.py`（coverage ≥ 90%）；5. 遵守 LOC 分級；6. Plugin 間禁止互相 import（走 EventBus）。

---

## AISDLC_SDD — 快查（完整見 [AISDLC_SDD/CLAUDE.md](AISDLC_SDD/CLAUDE.md)；使用框架前必讀 [AISDLC_SDD/AISDLC_SDD_v0.01/AISDLC_SDD_INIT.md](AISDLC_SDD/AISDLC_SDD_v0.01/AISDLC_SDD_INIT.md)）

~85% Markdown（模板／Agent／Workflow／治理規則）＋ ~15% Python runtime；各版目錄結構同構。🔴 **具體版本號與各類資產計數一律見唯一真相源 [AISDLC_SDD/FRAMEWORK_STATUS.md](AISDLC_SDD/FRAMEWORK_STATUS.md)**（機械生成、ci-gate `--check` 守新鮮），本檔不重複數字。

### 測試 / 形式化驗證 / 本機 CI 閘門

```bash
# 在 AISDLC_SDD/ 目錄下（bash 形態；Windows 禁裸 cd，改 Push-Location … Pop-Location 同呼叫成對）：
bash scripts/ci-gate.sh              # 本機 CI 閘門：pytest(not chaos) + arch_fitness --strict
bash scripts/ci-gate.sh --full-tlc   # 另跑五軌 TLA+/TLC（需 Java）
cd AISDLC_SDD_v0.01                  # pytest.ini 位於此（僅 mac/Linux 可裸 cd）
python -m pytest tools/fsm_runtime/tests/ -m "not chaos" -q   # PR 閘門
python -m pytest tools/fsm_runtime/tests/ -m chaos            # nightly（chaos 全套）
bash tools/fsm_runtime/formal/run_tlc.sh                      # TLA+/TLC（自動下載 tla2tools.jar）
```

- pytest markers：`chaos`（PR 排除、nightly 必跑）、`tlc`（需 `SDD_RUN_TLC=1` + Java）。CI 依賴鎖版於 `AISDLC_SDD_v0.01/requirements-ci.txt`。

### 框架大圖（約束）

**FSM 驅動的閉環治理**：`tools/fsm_runtime/` 是 `SDD_FSM_ENGINE.md` 的可執行狀態機；`governance/` 的 `R-*.yaml` 規則依 FSM 狀態 lazy-load；`.claude/`（hooks + skills，含 `session_start.py`、`context_ledger_pre/post.py`、`post_commit_drift.py`）在 session／tool／commit 各層守門。違反規則＝破壞 FSM invariant → ESCALATION 或被 hook 攔下。五軌 TLA+/TLC 形式化證明有界停機；**改 `_HAPPY_PATH` 必須同步 `formal/SDD_FSM.tla` 並重跑 TLC**。
**SDD 三支柱與 SCG-0~6 閘門**：Spec-First／Design-as-Doc／Contract-Driven；標 🔴 的人工確認點不可自動跳過。
**模板規則**：`docs_template/sdd/` 的模板**不可直接改**；複製到 `docs/` 對應編號子目錄後再填寫。

---

## 現查指令速查表（本檔不複寫數字的統一出口；數字都是量測值）

| 主題 | 現查方式 |
|------|---------|
| SDD LATEST 版本 | `python AISDLC_SDD/scripts/sdd_version.py` |
| 額度門檻百分比 | `python tools/lib/quota_policy.py --print-env-example` |
| context 水位 | `python tools/session_resume_planner.py --check` |
| harness autocompact 姿態 | `python tools/session_resume_planner.py --check-autocompact`（關閉時 rc=1） |
| 可派 agent 數（每次派工前） | `python tools/session_resume_planner.py --pace` |
| reset 後自動重啟排程 | `python tools/session_resume_planner.py --register-schtasks`／`--verify-schtasks`／`--remove-schtasks` |
| reset 視窗分佈 | `python tools/probe/reset_window_distribution.py` |
| 失誤歸因分群 | `python tools/probe/misstep_attribution.py` |
| shell 指令母體普查 | `python tools/probe/shell_command_corpus.py --summary` |
| session 違規率（事後量測，不接閘門） | `tools/probe/audit_session.py` |
| LOC 分級／絕對紅線 | `python AutoClaude/tools/check_loc_budget.py --json` |
| hook 佈線／shell form 普查 | `tools/lib/hook_wiring.py`（`SHELL_FORM_CENSUS`／`FROZEN_SHELL_FORM_MAX`） |
| hook 活性（開發機出聲層） | `tools/check_hooks_liveness.py`；正面現查 `claude -p --debug hooks`（見〈hook 載具〉） |
| 破壞性 git 擋不到什麼 | `grep -n "擋不到" .claude/hooks/block_destructive_git.py` |
| 等待形態判準條列 | `sed -n "/^def waitform_hits/,/\"\"\"$/p" .claude/hooks/block_destructive_git.py` |
| mac 睡眠姿態 | `pmset -g custom`（不隨 clone 走，不得寫成常數） |
| AISDLC_SDD 版本／資產計數 | [AISDLC_SDD/FRAMEWORK_STATUS.md](AISDLC_SDD/FRAMEWORK_STATUS.md) |
| AutoClaude Plugin／Port 計數 | AutoClaude/CLAUDE.md 的 `[Architecture Snapshot]` |

---

## 各專案權威文件快查

| 主題 | 文件 |
|------|------|
| AutoClaude 開發規範 / 模型欄位 / Architecture Snapshot | [AutoClaude/CLAUDE.md](AutoClaude/CLAUDE.md) |
| AutoClaude Sprint 脈絡 / ADR / Nightly 取證紀律 | `AutoClaude/docs/05_development/sprint_history.md`、`AutoClaude/docs/04_planning/ADR/`、`AutoClaude/docs/06_quality/Nightly_Forensic_Discipline.md` |
| AISDLC_SDD 框架入口 / 目錄規則 | [AISDLC_SDD/AISDLC_SDD_v0.01/AISDLC_SDD_INIT.md](AISDLC_SDD/AISDLC_SDD_v0.01/AISDLC_SDD_INIT.md)、`AISDLC_SDD/AISDLC_SDD_v0.01/FILE_DIRECTORY_RULES.md` |
| AISDLC_SDD 治理規則總覽（條數見 FRAMEWORK_STATUS.md） | `AISDLC_SDD/AISDLC_SDD_v0.01/governance/RULES_INDEX.md` |

---

## 12-Rule Template（全域工作規則）

These rules apply to every task in this project unless explicitly overridden.

Bias: caution over speed on non-trivial work. Use judgment on trivial tasks.

### Rule 1 — Think Before Coding
- State assumptions explicitly. If uncertain, proceed with the most reasonable assumption and surface it — never guess silently.
- Present multiple interpretations when ambiguity exists, then pick one and say why.
- Push back when a simpler approach exists.

### Rule 2 — Simplicity First
- Minimum code that solves the problem. Nothing speculative.
- No features beyond what was asked. No abstractions for single-use code.
- Test: would a senior engineer say this is overcomplicated? If yes, simplify.

### Rule 3 — Surgical Changes
- Touch only what you must. Clean up only your own mess.
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor what isn't broken. Match existing style.

### Rule 4 — Goal-Driven Execution
- Define success criteria. Loop until verified.
- Don't follow steps. Define success and iterate.
- Strong success criteria let you loop independently.

### Rule 5 — Use the model only for judgment calls
- Use me for: classification, drafting, summarization, extraction.
- Do NOT use me for: routing, retries, deterministic transforms.
- If code can answer, code answers.

### Rule 6 — Token budgets are not advisory
- Per-task: 4,000 tokens. Per-session: 30,000 tokens.
- If approaching budget, summarize and start fresh.
- Surface the breach. Do not silently overrun.

### Rule 7 — Surface conflicts, don't average them
- If two patterns contradict, pick one (more recent / more tested).
- Explain why. Flag the other for cleanup.
- Don't blend conflicting patterns.

### Rule 8 — Read before you write
- Before adding code, read exports, immediate callers, shared utilities.
- "Looks orthogonal" is dangerous. If unsure why code is structured a way, ask.

### Rule 9 — Tests verify intent, not just behavior
- Tests must encode WHY behavior matters, not just WHAT it does.
- A test that can't fail when business logic changes is wrong.

### Rule 10 — Checkpoint after every significant step
- Summarize what was done, what's verified, what's left.
- Don't continue from a state you can't describe back.
- If you lose track, stop and restate.

### Rule 11 — Match the codebase's conventions, even if you disagree
- Conformance > taste inside the codebase.
- If you genuinely think a convention is harmful, surface it. Don't fork silently.

### Rule 12 — Fail loud
- "Completed" is wrong if anything was skipped silently.
- "Tests pass" is wrong if any were skipped.
- Default to surfacing uncertainty, not hiding it.
