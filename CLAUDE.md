# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> **🔴 回覆語言**：本 workspace 下所有對話回覆**必須使用繁體中文**（專有名詞如 AISDLC、SDD、API、Docker、pytest 保持原文）。兩個子專案的 CLAUDE.md 皆以此為 override 級規範，絕不可用英文／簡體／日韓文回覆。

---

## 這是一個「雙專案 monorepo」

monorepo 根目錄（`AISDCL_Agent/`，各機器 checkout 路徑不同）底下是**兩個獨立子專案** + **一層 monorepo 根整合層**（根 `docs/`）。兩子專案各自有一份 override 級的 `CLAUDE.md`，互為姊妹：`AISDLC_SDD` 是**方法論框架**，`AutoClaude` 是能驅動該方法論的**執行引擎**（AutoClaude 的 Playbook `workflow_type` 支援 `aisdlc` / `aisdlc_sdd`）。**根整合層**（根 `docs/`）不屬於任一子專案，承載「兩者深度整合」的迭代計畫——見下方〈🔴 三條改進軌道〉，**勿與子專案內部的改進系列混淆**。

| 子目錄 | 性質 | 權威指引 |
|--------|------|---------|
| [AutoClaude/](AutoClaude/) | Python 3.11+ 應用程式 — Claude Code 多步驟 Playbook 自動執行引擎（微核心 + Plugin 體系 + DAL 三後端） | [AutoClaude/CLAUDE.md](AutoClaude/CLAUDE.md) |
| [AISDLC_SDD/](AISDLC_SDD/) | 規格先行（Spec-First）SDLC 框架 — 以 Markdown 模板／Agent／Workflow 為主 + FSM runtime（Python）+ TLA+ 形式化驗證 | [AISDLC_SDD/CLAUDE.md](AISDLC_SDD/CLAUDE.md) |

### 🔴 進入任一子專案前的第一動作

**先讀該子專案的 `CLAUDE.md`**，再開始工作。兩份子 CLAUDE.md 都宣告其指令 **OVERRIDE Claude Code 預設行為**，內含嚴格的目錄／命名／閘門規範與大量「違反即停機」的禁令（尤其 AISDLC_SDD 的 Rule 9 自動化閉環防護）。本根檔只負責導航，**不重複**子專案的細則。

### ⚠️ 路徑陷阱（務必注意）

子專案的 CLAUDE.md 是在「以自己為根」的前提下撰寫的：
- 它們文件內的相對路徑（如 `docs/05_development/...`、`autoclaude/core/...`）是**相對於該子專案目錄**，不是相對於本 monorepo 根。
- AISDLC_SDD 的 CLAUDE.md 把根稱為 `d:/CursorProject/AISDLC_SDD/`，實際對應到本 repo 的 `AISDLC_SDD/` 子目錄。
- 跑指令前要讓工作目錄落在正確的子專案。🔴 **但 Windows 側禁用裸 `cd`**（見下方〈鐵律二〉：PowerShell 工具的 cwd 會跨呼叫持續，R71 單輪因此失誤 3 次）——改用絕對路徑，或 `Push-Location <絕對路徑>` … `Pop-Location` 在**同一次呼叫內**成對。本節先前逐字寫「先 `cd`」，與鐵律二直接抵觸（R72 訂正）。

---

## 🔴 三條改進軌道（迭代方向總圖 — 勿搞錯方向）

> **為何特立此節**：本 repo 的改進/迭代以**軌道① 範本為唯一驅動器**，其下分 **A 協作／B 手腳（AISDLC_SDD）／C 指揮官（AutoClaude）三柱**；軌道②（框架 RFC）是 B 柱下游帳本、軌道③（AutoClaude 內部）是 C 柱工作流帳本——**三者同源於範本，但檔名相似極易混指**（曾有 session 把「整合迭代」誤指向子專案內部的 `SDD_improving_Automation_NN`，方向全錯）。**動工前先用本表對齊「本輪在哪一柱（A/B/C）、下一份檔名是什麼」。**

| 軌道 | 計畫文件（驅動器） | 性質 / scope | 下一份 |
|------|------------------|-------------|--------|
| **① 整合迭代**（AISDLC-SDD × AutoClaude 深度整合，**範本唯一驅動器**） | 根層 [docs/04_planning/AutoSDD_improving_NN.md](docs/04_planning/) | **三軌**（對齊北極星三點：指揮官 AutoClaude × 手腳 AISDLC_SDD × 雙向協作）：**A 軌**＝雙向協作橋接（SDD→Playbook）；**B 軌**＝手腳框架 dogfooding v0.0X 並回流缺陷；**C 軌**＝指揮官 AutoClaude 自身能力（含 SD_09／Improving_NN，2026-06-15 全收納入）。由 [docs/04_planning/AutoSDD_Iteration_Prompt_Template.md](docs/04_planning/AutoSDD_Iteration_Prompt_Template.md) 驅動，每輪四件套（improving_NN + ZeroTrust_Audit_NN + Defect_Log 累積 + 框架改進落 `v0.0(X+1)/`） | `docs/04_planning/` 現存最大號＋1（動工前以 `ls` 實查；本欄不快照具體號次——R13 曾抓到快照 stale 差 100 號） |
| **② 框架內部 RFC**（AISDLC_SDD 自身演進） | `AISDLC_SDD/AISDLC_SDD_v0.01/build/planning/active/SDD_improving_Automation_NN.md` | **①B 軌 dogfooding 的缺陷回流路徑之一**（框架程式/模板/hook 缺陷提案）；是迭代的**下游產物，不是驅動器**。active 為 26 號 | 隨缺陷回流產生（非定期遞增） |
| **③ AutoClaude 內部能力**（＝軌道① 的 **C 軌工作流帳本**） | `AutoClaude/docs/04_planning/AutoClaude_Improving_0NN.md` + `SD_Improving_NN.md` | AutoClaude 自身能力升級（Improving_012＝Agentic 三能力；SD_Improving_09＝PG production／觀察期）。**2026-06-15 起納入整合範本 C 軌（柱①「指揮官」），由 AutoSDD 範本統籌驅動**；本欄檔案降為該柱工作流帳本（沿用 AutoClaude 自身 docs/ 編號與 G0~G6 Gate） | 以 `AutoClaude/docs/04_planning/` 現存最大號與 C 軌帳本現況為準（本欄不快照具體進度——R13 曾抓到快照 stale） |

**鐵律**：
- 要「推進整合 / 開新一輪迭代」→ **走軌道 ①**，複製 `AutoSDD_Iteration_Prompt_Template.md`、續 `AutoSDD_improving_NN`。**絕不**把 `SDD_improving_Automation_NN`（軌道 ②）當迭代計畫。
- 軌道 ② 只在軌道 ①B 軌發現框架缺陷時，作為回流 RFC 帳本使用；缺陷先入根層累積帳本 [docs/06_quality/AutoSDD_Defect_Log.md](docs/06_quality/)。
- 軌道 ③（AutoClaude 自身能力）**自 2026-06-15 起納入軌道① 範本 C 軌（柱①「指揮官」）統籌驅動**（範本定位＝精進 AutoClaude＋AISDLC_SDD＋兩方協作；指揮官 AutoClaude、手腳 AISDLC_SDD）；其 `AutoClaude_Improving_0NN`／`SD_Improving_NN` 檔保留為 C 軌工作流帳本。**防混淆鐵律不變且更重要**：每輪動工前先用本表對齊「本輪在哪一柱（A 協作／B 手腳／C 指揮官）、下一份檔名」，三柱同源不代表可混指。
- 三軌的 `docs/` 都各自獨立編號（01~08）：軌道 ① 用**根層** `docs/`、軌道 ②／③（C 軌帳本）用各**子專案**的 `docs/`（見〈路徑陷阱〉）。

---

## 兩專案共通的工程紀律

兩個子專案明文共享以下規範（細則見各自 CLAUDE.md）：

1. **繁體中文回覆**（見頂部）。AutoClaude 另有 Stop hook `check_lang.py` 事後偵測韓／日／簡體字並 warn。
2. **開發-編譯-測試循環（強制）**：每完成一支程式立即編譯＋跑單元測試，**絕不累積開發**；編譯／測試失敗立即停下修復，禁止跳過或註解掉失敗測試。
3. **文檔目錄編號制**：產出文件寫入 `docs/0[1-8]_*/`（01_requirements ～ 08_deployment）對應子目錄，不可亂放。AutoClaude 以 PreToolUse hook `enforce_docs_path.py` 強制。
4. **規格先行**：寫程式前先有規格／通過閘門（AISDLC_SDD 的 SCG-0~6；AutoClaude 的 G0~G6 Gate）。

---

## 🔴 Token 將耗盡時的「無害暫停 → reset 後重啟」SOP

> **為何特立此節**：R59 收尾撞到 Token 99%，當時用 `CronCreate` 排 45 分鐘後續跑並向使用者宣稱「會自動繼續」——時間到完全沒觸發，因為 `CronList` 對它的標記就是 **`[session-only]`**。**承諾兌現不了比不承諾更糟**：使用者以為工作在推進，實際整段停擺，事後才發現＝事後諸葛。本節把暫停／重啟定成可執行程序，並訂一條取證規則讓「沒排到」當場就被抓到。

### 三段式水位（照 AutoClaude 自己的 Token Guard 同構 — 對自己 dogfooding）

| Token 水位 | 動作 |
|-----------|------|
| ~75% | `/compact`。此時仍可開新工作 |
| ~90% | **停止開新戰場**，把狀態收斂到「可重啟點」（見下）並寫任務書。此後只做收斂，不做展開 |
| 撞上限 | 記下 CLI 印出的 **reset 時間** ＋ **本 session ID**；等 reset 後 `claude -r <sessionId>` |

> 對照：`autoclaude/` Kernel 的 Token Guard 是 ≥80% `/compact`、≥90% 存 checkpoint 並排程恢復（`scheduled_resume_at`）——**同一個形狀，只是這次套在自己身上**。

### 「可重啟點」四條件（缺一就不算安全暫停）

1. **工作樹狀態確定**：要嘛已 commit 且閘門全綠，要嘛 `git stash create` ＋ `git tag <輪次>-wip-preserved` 保全。**絕不留半套 edit 就走**（R59 靠這招保住 56 檔零損失）。
2. **任務書落在磁碟**，不是只留在對話裡（對話會被 compact、session 會換）。正式的寫 `docs/04_planning/` 或缺陷帳本；臨時的放 scratchpad 並在回覆中給出**絕對路徑**。
3. **任務書必含四項**：已驗證什麼（附實測數字與 rc）／還沒做什麼／下一步的**確切指令**／**禁止事項**（例：不准 `--no-verify`、不准 `AUTOCLAUDE_SKIP_HOOKS=1`）。
4. **重啟後第一件事是重驗**，不採信任務書裡任何「已通過」宣稱（同 Nightly 取證紀律 #17 zero-trust 雙向：對自己上一段的宣稱也要 zero-trust）。

### 重啟指令（`claude --help` 實查，v2.1.218）

```bash
claude -r <sessionId>   # 帶回完整 context 續跑 ← 推薦：高風險動作（commit/push）仍有人在
claude -c               # 續接最近一次對話
```
- **session ID 取得**：`~/.claude/projects/<專案 slug>/<sessionId>.jsonl`，當前 session 即該目錄下**最後修改**的那支。**暫停前務必把它寫進任務書**。
- 要**全自動**才加 OS 排程（`schtasks` 叫 `claude -p -r <sessionId> "<任務書>"`），且必須寫 log 取證、只允許低風險動作。⚠️ 此路**無法從 Claude Code session 內部試跑驗證**——巢狀 spawn 會死結（DEF-101-089，`CLAUDECODE=1`），須由人在 session 外先驗一次。

### 工具選型（別再選錯）

| 需求 | 工具 | 邊界 |
|------|------|------|
| **Token reset 後重啟** | **磁碟任務書 ＋ `claude -r`** | 唯一不依賴 session 存活的路 ← **本節主線** |
| session 開著、人離開一下要它自己做完 | `/loop`／`ScheduleWakeup` | 同 session、**同一個 Token 池**；`ScheduleWakeup` 單次上限 1 小時，要撐過數小時 reset 得靠多次醒來且終端全程不能關 → **不是 token reset 的方案** |
| 跨 session／機器會睡的定時工作 | `schtasks`（照 `AutoClaude/tools/install_windows_nightly.ps1` 的 `New-ScheduledTaskSettingsSet` 建法） | 四項設定缺一即漏跑：`WakeToRun=True`／`StartWhenAvailable=True`／`DisallowStartIfOnBatteries=False`／`StopIfGoingOnBatteries=False`（建構 cmdlet 的參數名與物件屬性名**不同**，見該檔檔頭 DEF-101-249） |
| ❌ 不要用 | `CronCreate` | `CronList` 印 `[session-only]`＝session 關掉就沒了，**不是離線排程** |

### 🔴 反「事後諸葛」取證規則（本節重點）

**宣稱「已排程／會自動繼續」的同一則回覆裡，必須貼出排程器自己回報的下次執行時間實測輸出**；貼不出來就不准宣稱，只能說「我做不到，請你改用 X」。這與 Nightly 取證紀律 #3（PASS 聲稱必須引 log 行號）**同型——排程也是一種 PASS 聲稱**，「我下了指令」不等於「它真的排進去了」。

```powershell
Get-ScheduledTask -TaskName '<名稱>' | Get-ScheduledTaskInfo |
  Select-Object TaskName,LastRunTime,LastTaskResult,NextRunTime   # NextRunTime 就是憑證
```
- 排出去的 job 必須留下**可稽核痕跡**（log 檔＋時間戳），讓「沒觸發」是**可偵測**而非靜默假設。
- ⚠️ **查詢載具自己也會騙人**：`schtasks /query /fo CSV | grep AutoClaude` 在本機回**空**（假陰性），而 `Get-ScheduledTask` 對同一批工作查得到、且回報 `State=Ready`。**查排程一律用 `Get-ScheduledTask`**（同「驗證載具本身要被驗證」紀律 #4）。
  🔴 **本條刻意不寫死「本機現有哪幾支工作」**（R71 訂正）：原文以 `AutoClaude_Nightly`／`AutoClaude_SD09_G0_GateCheck` 兩支具名舉例，而後者已於 R71 從本機移除（腳本保留；該移除即本輪 S-4 處置，非過往輪），使**這段教人取證的文字自己拿過期事實當證據**——正是本節在防的「事後諸葛」。工作清單是會漂移的量測值，一律現查：

  ```powershell
  Get-ScheduledTask | Where-Object TaskName -like 'AutoClaude*' | Select-Object TaskName,State
  ```

---

## 🔴 Windows 側單一載具原則（R71 訂立 — 低級錯誤的結構性根因與解法）

> **為何特立此節**：R71（Windows 真機輪）實測記錄到 8 筆操作失誤，逐筆歸因後 **5 筆是平台相關、3 筆無關**。掌舵者觀察「在 Windows 常犯低級錯誤、在 mac 好像不會」屬實，但根因**不是**「Windows 上比較不小心」——是**同時操作兩個 shell 造成的決策負荷**。每下一個指令要同時決定：用哪個 shell／什麼編碼／哪種路徑格式／cwd 現在在哪／這支腳本拒不拒絕這個載具。mac 側這六項全部不存在。**被這些決策擠掉的注意力，正是「查權威源再宣稱」那類紀律失守的原因**——所以連平台無關的錯，密度也在 Windows 側偏高。

### 鐵律一：Windows 上**禁用 Bash 工具**，一律走 PowerShell 工具

> 🔴 **這是掌舵者 2026-08-03 的直接指令**（原文：「只使用 PowerShell 5.1, 不用 Git Bash ==> 請遵守」），
> 不是建議、不是預設值。**「兩個載具擇優使用」這個選項已被移除**——因為擇優本身就是那個要付出注意力的決策，
> 而它換來的效率遠不及它造成的失誤。掌舵者原話：「常常做錯誤的事，並不會比較有效率」。

| 需求 | 載具 | 理由 |
|------|------|------|
| **一切 shell 指令** | **PowerShell 工具** | schtasks／生產環境跑的就是 `powershell.exe`（PS 5.1），載具對齊＝驗證條件對齊 |
| `.sh` 腳本 | **PowerShell 內**用 repo 既有 SSOT 解析 Git Bash ＋ **正斜線**腳本路徑：<br>`. "$(git rev-parse --show-toplevel)/tools/lib/Find-GitBash.ps1"; & (Find-GitBash) -n '<正斜線腳本路徑>'` | 這是「執行一支 .sh」不是「用 Bash 當載具」，兩者別混淆。同 `tools/git-hooks/pre-push` 既有作法。<br>🔴 **不可寫裸 `bash <script>`**——`Get-Command bash` 解析到 `C:\WINDOWS\system32\bash.exe`（WSL 佔位／真 WSL），且反斜線路徑會被吃掉。R72 實測逐字：`/bin/bash: D:CursorProjectAISDCL_Agenttoolsinstall_mac_nightly.sh: No such file or directory`（rc=127，注意 `D:` 後的分隔符全部消失）。**與 DEF-101-617/618 的 WSL 佔位版誤解析同源**。<br>🔴 **R73 訂正（DEF-101-778）**：本欄 R72 版改成寫死 `C:\Program Files\Git\bin\bash.exe`——治好了裸 `bash`，卻把**一台機器的安裝路徑寫成了本檔的常數**，Git 裝在別處的 checkout 一律照著失敗；而 repo 自己早就有 `tools/lib/Find-GitBash.ps1`（含 system32/WSL 逐段排除，R60 P10-2 加固）。**同一份知識住兩個家、只有一個家被鎖**——而它發生在專門用來防這件事的這一節自己身上。R73 雙引擎實測：`Find-GitBash` → `C:\Program Files\Git\bin\bash.exe`（5.1 與 7.6.4 皆同），對照 `Get-Command bash` → `C:\WINDOWS\system32\bash.exe`（兩引擎皆誤），SSOT 版 `-n` 語法檢查 rc=0 |
| 讀檔／搜尋／算行數 | **Read／Grep 工具**，不經 shell | 🔴 **編碼邊界雙向都會出錯**，不是只有「Bash 讀 PS 輸出」那一向。R71 同輪兩次實證：① Git Bash `grep` 讀 CP950 的 PS 輸出 → 命中 0、誤判「沒有失敗行」；② PowerShell `Get-Content` 以 CP950 讀 UTF-8 的 `CLAUDE.md` → 回報「237 行／最長 962 codepoints」，python 實際「324 行／無任何行 >800」——**兩個數字都假，且假在會讓人誤以為破閘的方向**。要在 shell 內算就必須指名 `-Encoding utf8`，但更省事的是根本不用 shell |
| ❌ **Bash 工具** | **禁用** | R71 實測兩次事故：① `windows_smoke_local.ps1` 被 MSYS 守衛擋下（rc=1，DEF-101-511 刻意設計）；② Git Bash 去 grep CP950 編碼的 PS 輸出 → 命中 0、**誤判「沒有失敗行」** |

**如何檢核**：看工具呼叫名稱即可，不需要相信任何宣稱——出現 `Bash` 就是違規。

🔴 **本條已有機械物，不靠自律**：`.claude/hooks/block_bash_on_windows.py`
（PreToolUse／`matcher: Bash`，在根 `.claude/settings.json` 註冊）。
**為何非上機械物不可**：本節由 session **開場**載入，session 中途訂立的規則對「當下的模型」
只能靠主動記得，而主動記得正是決策負荷會擠掉的東西——R71 實證：**寫完本節的同一個回合仍用了 Bash 工具**，
掌舵者兩度指出「你還是沒有遵守」之後才改上阻斷。這正是 `DEF-101-757`「已知的鎖射程缺口不得只以劃界結案」
的又一個實例，只是這次的缺口在模型自身的行為上。
守衛四種輸入皆實測：`Bash`→exit 2 阻斷／`Read`→exit 0（射程不擴大）／壞 JSON 與空輸入→exit 2（fail-closed）；
**非 Windows 一律 exit 0**（mac/Linux 上 bash 才是正確載具，單平台判準不可無條件外推——`DEF-101-766` 同型教訓）；
任何非預期例外 fail-open（`settings.json` 記載過的 P0：hook 誤觸 deny 會把所有工具硬鎖死）。
端到端實證：故意呼叫 Bash → `PreToolUse:Bash hook error` 攔下。

### 鐵律二：**一律絕對路徑，禁用裸 `cd`**

PowerShell 工具的 cwd **會跨呼叫持續**（工具說明明載），但人容易假設它會重置。R71 單輪就因此失誤 **3 次**（`cd AutoClaude` 之後的指令全部找錯路徑，其中一次還誤判成「檔案不存在」）。

- ✅ `& 'D:\CursorProject\AISDCL_Agent\.venv\Scripts\python.exe' <絕對路徑腳本>`
- ✅ 需要切目錄時用 `Push-Location <絕對路徑>; …; Pop-Location`（同一次呼叫內成對，不遺留狀態）
- ❌ 先跑 `Set-Location AutoClaude`，下一個呼叫再用相對路徑

### 鐵律三：寫跨平台程式碼時，強制自問「**這在另一個平台是什麼值？**」

R71 最諷刺的一筆：在修一個 Windows 專屬缺陷（DEF-101-759）時，寫出了另一個只在 Windows 成立的判準——`$env:PATHEXT` 在 macOS/Linux 的 PS Core 上不存在、POSIX 執行檔也不帶副檔名，兩個原因各自都足以讓函式恆回 `$null`，**會讓 macos-compat-ci 與 root-infra-ci(ubuntu) 必紅**（DEF-101-766）。成因是當下整個思考脈絡都泡在 Windows 語境裡。

觸發清單（出現任一就必須自問）：`$env:*` 讀取／副檔名判斷／路徑分隔符／`Get-Command` 解析／console 編碼／行尾／大小寫敏感度／`$IsWindows` 這類 PS 6+ 專屬自動變數（5.1 恆 `$null`，需 `# ps7-ok: <WHY>` 行尾豁免，**獨立註解行無效**——掃描器只認行尾）。

### 鐵律四：本節之外的三筆「平台無關」失誤，共同形態是**宣稱先於查證**

R71 實例：輪號 R70／R71 全程講錯（採信提示詞而未查 `current_round()` 權威源）／宣稱「資訊零損失」但帳本實際沒有該站點／豁免標記形態靠猜而未讀掃描器實作。**這三筆在 mac 側同樣會發生**，只是 Windows 的決策負荷讓它們更容易漏。對策不是「更小心」，而是套用既有紀律 [[no-fabricated-tool-output]]：**任何「已驗證／已達標／零損失」的宣稱，都要附當回合真跑的輸出**——貼不出來就改寫成「未驗證」。

---

## AutoClaude — 常用指令與架構

> 完整內容見 [AutoClaude/CLAUDE.md](AutoClaude/CLAUDE.md)。以下指令請在 `AutoClaude/` 目錄下執行。

### 安裝 / 執行

> 🔴 `tools/bootstrap.*` 偵測到 `uv` 時一律用 `uv venv` + `uv pip install` 建置 `.venv`（`dev_start` 預設路徑），這種 venv **內部沒有 `pip` 模組**（`python -m pip` 會報 `No module named pip`，Mac/Windows 四方複審實機驗證重現），故下列指令一律用 `uv pip install`（uv 已安裝時對任何已啟用的 venv皆可用，不論該 venv 是否由 uv 建立）；只有走 `bootstrap` 的傳統 `python -m venv` 回退路徑（未裝 uv）時，才會有 `pip` 模組可直接用 `pip install`。

> 🔴 **R57 修正：extras 一律加單引號 `'.[...]'`**——macOS 預設 shell 是 zsh，未加引號時 zsh 會對 `.[dev,notifications]` 做 filename generation、repo 內無匹配即以 `zsh: no matches found: .[dev,notifications]` **中止整條指令**（uv／pip 根本沒被執行，使用者看到與套件無關的怪錯）；bash 與 PowerShell 下不加引號雖可跑，加引號則三種 shell 皆正確，故統一加。雷區對照見 [ONBOARDING.md](ONBOARDING.md) §5。

```bash
uv pip install -e '.[dev,notifications]'   # 開發環境（pytest, ruff, hypothesis…）
uv pip install -e '.[lint]'                # import-linter（架構約束檢查）
uv pip install -e '.[postgres,pgvector]'   # PostgreSQL + 向量查詢後端（選配）

python -m autoclaude <playbook.yaml> [--config config.yaml] [--fresh]
autoclaude <playbook.yaml> --config config.local.yaml   # 安裝後 entrypoint
```

### 測試 / Lint
```bash
python -m pytest tests/ -q                       # 全套（🔴 基線數字唯一出處＝根層 ONBOARDING.md §7：出廠環境定義、巢狀 session 變因、選配差異皆載於該節，本檔不重複數字）
python -m pytest tests/test_playbook_runner.py -v # 單檔
python -m pytest tests/ -k <substring> -v         # 單一測試
python -m pytest tests/ -m pg_real                # 需 SD07_REAL_PG_E2E_ENABLED=true + PG DSN
PYTHONUTF8=1 lint-imports                          # import-linter（8 kept / 0 broken）
ruff check .                                       # lint（line-length=100, py311；含 E,F,I,UP）
```
- 🔴 上列為 **bash 形態**。PowerShell **沒有** `VAR=value <指令>` 前綴語法，`PYTHONUTF8=1 lint-imports` 照抄會得到 `The term 'PYTHONUTF8=1' is not recognized`；Windows 須寫 `$env:PYTHONUTF8=1; lint-imports`（雙平台完整對照見 [ONBOARDING.md](ONBOARDING.md) §7；DEF-101-513）。
- pytest markers：`pg_real`（真 PG e2e）、`perf`、`benchmark`。
- `pytest-randomly` **未啟用**，順序由 collection 決定。

### 本機 CI 對等 / Nightly（push 前全綠，PowerShell）
```powershell
powershell -ExecutionPolicy Bypass -File tools/install_git_hooks.ps1   # 裝 git hooks
powershell -ExecutionPolicy Bypass -File tools/local_ci_gate.ps1       # 一鍵本機 CI 閘門（鏡像 autoclaude-ci.yml）
powershell -ExecutionPolicy Bypass -File tools/run_act.ps1 -Job test   # act：Linux 容器跑真 CI（於 monorepo 根執行、讀根層 .actrc）
powershell -ExecutionPolicy Bypass -File tools/run_local_nightly.ps1   # nightly 7 stage（local_ci_gate/mutation/pg-e2e/perf/drift/obs/sdd-chaos）
docker compose -f docker-compose.ci.yml up -d                          # CI 對等 PG（pg17）
```
- **macOS/Linux 對等腳本已存在**：AutoClaude 側 `tools/install_git_hooks.sh`、`tools/local_ci_gate.sh`、`tools/run_act.sh`、`tools/run_local_nightly.sh`（mac 薄聚合器，非 .ps1 對等移植）；monorepo 根層另有 `tools/bootstrap.sh` 與 `tools/integration_gate.sh`。完整雙平台對照表見根層 [ONBOARDING.md](ONBOARDING.md) §6。
- git hooks 為**根層 dispatcher**（monorepo 根 `tools/git-hooks/`）：任一支安裝腳本（`.sh`/`.ps1`）執行後**兩子專案閘門同時生效**，裝一次即可（詳見 ONBOARDING.md §6）。
- CI（**根層** `.github/workflows/autoclaude-ci.yml`；兩子專案 workflows 已全數上移 monorepo 根層並加子專案前綴，對照見 ONBOARDING.md §6.1）push 閘門 jobs（另有 nightly jobs 見 workflow 檔）：`test`（pytest + LOC budget + lint-imports）、`claude-md-budget`（**僅指 `AutoClaude/CLAUDE.md`**——ADR-SD08-001 射程，根層與 AISDLC_SDD 兩份不受此閘；≤ 400 行 + snapshot 新鮮度）、`equivalence`、`pg-contract`（**硬閘**；DEF-101-051 補完三層 goal_task_id 接線後由 continue-on-error 轉阻塞）。
- DB migrations：`alembic upgrade head`（同步 DSN／psycopg2；PostgreSQL 17 + pgvector）。

### 架構大圖
**Hexagonal / 微核心**：`core/`（Kernel + EventBus + HookSpec + `ports/` 抽象介面）只依賴 ports；`infra/adapters/` 提供具體實作（MinimaxBrain / PtyExecutor / ShellEvaluator / LocalLogger）；`infra/repositories/` 是 DAL 三後端（File / InMemory / Pg + Dual）；`plugins/` 為橫切關注點，彼此**不可互 import**，協作一律走 EventBus。`execution/playbook_runner.py` 是無業務邏輯的 thin facade。**Plugin／Port 清單與計數一律見 AutoClaude/CLAUDE.md 的機械生成 `[Architecture Snapshot]`**（本檔不重複數字，免漂移——與 AISDLC_SDD 數字指向 FRAMEWORK_STATUS.md 同政策）。

**狀態機閉環**：INIT → PRE_RUN_VALIDATE → EXECUTE(step) →（Token Guard：≥80% `/compact`、≥90% checkpoint）→ EVALUATE →（失敗則 Minimax CORRECTION / 超限則 ESCALATION → MinimaxEvolver→PlaybookEvolver 自演化）→ DONE → GOAL_SYNTHESIS。

**架構約束以 `.importlinter` 8 條 contract 機械強制 + LOC 分級政策**（data ≤150 / plugin_entry ≤250 / strategy ≤300 / adapter ≤400 / contract ≤400 / service ≤500 / 絕對紅線 ≤750；`tools/check_loc_budget.py` 強制）。`CLAUDE.md` 內含自動生成的 `[Architecture Snapshot]` 區段（由 `tools/snapshot_sync.py` 產生，**勿手動編輯**）。

### 新增 Plugin 的 SOP
1. 建 `autoclaude/plugins/<feature>_plugin.py`（繼承 HookSpec，PascalCase 類別）；2. 實作對應 hook；3. 加入 `wiring._REGISTER_ORDER`，相依走 constructor 注入 ports（**禁止直接 import infra**）；4. 寫 `tests/plugins/test_<feature>.py`（coverage ≥ 90%）；5. 遵守 LOC 分級；6. Plugin 間禁止互相 import（走 EventBus）。

---

## AISDLC_SDD — 常用指令與架構

> 完整內容見 [AISDLC_SDD/CLAUDE.md](AISDLC_SDD/CLAUDE.md)。使用框架前**必讀** [AISDLC_SDD/AISDLC_SDD_v0.01/AISDLC_SDD_INIT.md](AISDLC_SDD/AISDLC_SDD_v0.01/AISDLC_SDD_INIT.md)。

這是一個 **~85% Markdown（模板／Agent／Workflow／治理規則）+ ~15% Python runtime** 的框架。

### 結構（各版目錄結構同構；`AISDLC_SDD_v0.01/`＝ci-gate 凍結基線，最新演化版＝ci-gate LATEST，ci-gate 同時測「凍結基線 + LATEST」）
> 🔴 **具體版本號與各類資產計數一律見唯一真相源 [AISDLC_SDD/FRAMEWORK_STATUS.md](AISDLC_SDD/FRAMEWORK_STATUS.md)**（由 `scripts/framework_status_snapshot.py` 自磁碟+權威源生成，ci-gate `--check` 機械守新鮮）。本檔與子 CLAUDE.md **不重複數字**——版本累積亦不再多檔漂移、不靠人工記得改多處。

`agent/`（core + specialized，含數個 `sdd-*` runtime agent）、`scenarios/`、`workflow/`（1 SDD Gate + core + scenario + ADR，另加 FSM/Escalation/Context runtime）、`docs_template/`（SDD 模板＝md + yaml）、`governance/`（`RULES_INDEX.md` + `R-*.yaml`，依 FSM 狀態 lazy-load）、`tools/fsm_runtime/`（FSM 引擎）、`cicd/`、`guides/`、`prompts/`、`.claude/`（hooks + skills）。

### 測試 / 形式化驗證 / 本機 CI 閘門
```bash
# 在 AISDLC_SDD/ 目錄下：
bash scripts/ci-gate.sh              # 本機 CI 閘門：pytest(not chaos, 含 offline reachability BFS) + arch_fitness --strict
bash scripts/ci-gate.sh --full-tlc   # 另跑五軌 TLA+/TLC（需 Java + tla2tools.jar）

# 直接跑 FSM runtime 測試（pytest.ini 位於 AISDLC_SDD_v0.01/，testpaths=tools/fsm_runtime/tests）：
# 🔴 Windows 側禁裸 cd（鐵律二）：改 `Push-Location <絕對路徑>` … `Pop-Location` 同呼叫內成對。
#    本區塊是 bash 形態示範；下行的 cd 僅在 mac/Linux 成立。R72 訂正：原文示範自己就是裸 cd。
cd AISDLC_SDD_v0.01
python -m pytest tools/fsm_runtime/tests/ -m "not chaos" -q   # PR 閘門（排除 chaos）
python -m pytest tools/fsm_runtime/tests/ -m chaos            # nightly（chaos 標記測試全套；另有 chaos_runner 100 輪 sweep，bounded_ratio==1.0）
python -m tools.arch_fitness.arch_fitness --strict --json arch-fitness.json
bash tools/fsm_runtime/formal/run_tlc.sh                      # TLA+/TLC（自動下載 tla2tools.jar）
```
- pytest markers：`chaos`（慢；PR 排除、nightly 必跑）、`tlc`（需 `SDD_RUN_TLC=1` + Java）。
- CI 依賴鎖版於 `AISDLC_SDD_v0.01/requirements-ci.txt`（`pyyaml==6.0.3`、`pytest==9.1.1`）以確保「地端 = Docker = ubuntu-latest」同版。

### 框架運作大圖
**FSM 驅動的閉環治理**：`tools/fsm_runtime/` 是 `SDD_FSM_ENGINE.md` 的可執行狀態機。`governance/` 的 `R-*.yaml` 規則（條數見 FRAMEWORK_STATUS.md）由 `rule_loader.load_for_state()` 依當前 FSM 狀態 lazy-load；`.claude/hooks/`（`session_start.py`、`context_ledger_pre/post.py`、`post_commit_drift.py`）在 session／tool／commit 各層注入守門。違反規則 = 破壞 FSM invariant → ESCALATION 或被 hook 攔下。**五軌 TLA+/TLC**（SDD_FSM / META_FSM / COMPOSITION_FSM / OPTIMIZATION_FSM / FLEET_FSM）以形式化方法證明有界停機；改 `_HAPPY_PATH` 必須同步 `formal/SDD_FSM.tla` 並重跑 TLC。

**SDD 三支柱與 SCG 閘門**：Spec-First Gate（規格先於實作）、Design-as-Doc（決策有 ADR、架構有 C4）、Contract-Driven（OpenAPI 凍結後才實作）。SCG-0~6 閘門逐關卡管需求／設計／架構／契約／PR／RTM／發布；標 🔴 的人工確認點不可自動跳過。

**模板使用規則**：`docs_template/sdd/` 的模板**不可直接改**；複製到 `docs/` 對應編號子目錄後再填寫。

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
