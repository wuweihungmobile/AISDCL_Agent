# CrossPlatform R180 — 掌舵者五問第二次四方獨立覆核／DEF-200-411 新立即結、DEF-200-410 結案證據檔

> 輪次：2026-09-28，Windows 11 Pro 10.0.26200（Koala-MSI），Claude Code 2.1.283；主控 Fable 5.1，子 agent 皆 Sonnet 5。
> 流程：AISDLC 精簡版（掌舵者指示「省去非必要文件，只留一定需要文件」）——主控親測落事實包 → 四方（Architect／SA／SD／QA）唯讀獨立審查（Workflow，19 agent）→ 每項發現兩位反駁鏡（A 重現正確性／B 範圍治理）→ 完整性批評者 → 主控裁決 → 兩位 Developer 並行修法（鎖持有面互斥）→ 每件一位唯讀對抗複審 → 收尾單人窗口。
> 前輪：`CrossPlatform_R179_SessionGate_Windows_Recheck_Evidence.md`（同五問的第一次 Windows 真機覆核）。掌舵者本輪原話：「派出 Architect／SA／SD／QA 四方專家獨立審查，請確認以上都已經修好！」＋「請清 146 支」（`.bak-*` 殘留）。

## 一、五問第二次判定（含與 R179 的差異）

| 問 | R180 判定 | 一句話 |
|---|---|---|
| Q1 新視窗就說被擋、不查真實數據 | **NOT-A-DEFECT（機制面 FIXED）** | SA 掃 63 份頂層逐字稿（全部 slug，排除本 session）：前 10 則 assistant 自述命中 4 筆、逐字核對全部不是「自稱被擋」（兩筆是主動避免語氣、兩筆是 R179 本人在描述本任務）；前 5 次工具呼叫 hook 阻斷 0、`permissionDecision:deny` 0、原生阻擋 1 筆為 git log 內歷史 commit 訊息（假陽性）。Architect 靜態排除：`context_budget_guard.py:172` `BLOCKING_TOOLS` 只含 Task／WebFetch／WebSearch／Agent／Workflow；`sdd_hook_router.py` 在 `SDD_ACTIVE_VERSION` 空時 no-op；`block_destructive_git.py` 治理面只在 `AUTOSDD_UNATTENDED` 有設才 rc=2。本場活體證據：主控派第二支 Workflow 時被額度守衛以 band=notice 擋下（rc=2、指路逐個派 Agent），Read／Edit／PowerShell 全程照常——這正是 `_RC2_CLARIFY` 那句話描述的形態。 |
| Q2 不用真實 /context 或 API 查數據 | **PARTIAL（機制 FIXED、行為傾向不可機械證明）** | 完整性批評者指出 ARCH／QA 頂層標 FIXED 但 honest_limits 都承認「程式碼審查證明不了模型每次都真的去查」，依鐵律十二把字面降為 PARTIAL。機制面：`session_brief.py` 三行皆讀真實資料（`quota_gate.read_quota()`／`scan_transcript()`／`install_statusline.status()`），由 `context_budget_guard.py:989-992` 在 SessionStart 自動呼叫；本 session 開場簡報逐字印出「本 session 尚無量測」「額度量不到（reason=stale-cache…）」與兩條查證指令，主控第一動作即 `--check`／`--pace` 現查。SA 判準(5)：63 份逐字稿第一則回覆含「水位／額度／%」的 7 筆全是「我先現查」句，0 筆不查就編數字。 |
| Q3 印出的數字與 /context 不符 | **NOT-A-DEFECT** | 主控 `--check`：`harness used=87,807 逐字稿 used=87,807 差=0`；SD 三次：差 0 → 差 19,659（行尾附 DEF-200-408 的 `DIFF_HINT`）→ 差 0；feed 檔 `ts 11:52:55→11:54:50`、`used_percentage 17→21` 隨訊息更新。官方文件（Sonnet 查證，code.claude.com/docs/en/statusline〈Troubleshooting〉逐字）：「Context percentage may differ from `/context` output due to when each is calculated」——瞬間差值是官方承認的計算時機差。 |
| Q4 Windows 沒有 ctx 行 | **PARTIAL → 本輪修 DEF-200-411 後 FIXED（機制面）** | 部署缺口 R179 已補（本 session feed 檔 `used_percentage: 13`、`display_name: Fable 5.1`、`version: 2.1.283` 隨訊息更新 ⇒ Claude Code 正在呼叫進料器）。官方文件：statusLine 在 `"tui": "fullscreen"` 下照樣渲染於 footer badges 上方獨立一列（fullscreen 只讓通知另起一行），所以掌舵者的 fullscreen 設定不是缺席原因。**本輪新抓**：`install_statusline.py --status` 用 pyenv python 跑回 `matches_current_checkout: false`、rc=1，用根層 `.venv` 跑回 true、rc=0 ⇒ 期望值綁呼叫者 `sys.executable`（Architect／SD／QA 三方獨立重現、六位反駁鏡皆未駁倒）；`--dry-run` 用 pyenv 跑會 would-install 一條指向 pyenv 目錄 `pythonw.exe` 的 command（違反 DEF-200-301 單一 .venv）。立 DEF-200-411 同輪結案。剩掌舵者肉眼確認新視窗最下方有無 `ctx` 行。 |
| Q5 收斂了嗎 | **CONVERGED_AFTER_LISTED_FIXES → 本輪修完** | 批評者判定：R179 三筆（407／408／409）逐字落地、雲端五支 success 是真收斂；但本輪浮出 411（可重現、與 Q4 同因果鏈）且 410 本就 open ⇒ 修完才算。本輪兩件皆修畢結案；剩 DEF-200-341（解鎖改 CI runner，屬掌舵者治理裁決）。 |

## 二、主控親測事實（本場 tool_result 逐字）

- HEAD=`6369db4`、工作樹 clean；`--check`：`used 87,807／window 1,000,000〔harness 回報〕／水位 8.8%／harness used=87,807 逐字稿 used=87,807 差=0`；`--pace`：`現在可派 8 個 agent｜band=free｜最緊的一條＝seven_day 17%`。
- `~/.claude/settings.json`：`statusLine.command`＝`D:/CursorProject/AISDCL_Agent/.venv/Scripts/pythonw.exe D:/CursorProject/AISDCL_Agent/tools/statusline_context_feed.py`、`"tui": "fullscreen"`、掌舵者以 `/auto-mode-setup` 新寫入 `autoMode.environment`（29 行）＋`autoMode.soft_deny`（`$defaults`＋`git stash`／`reset --hard`／`clean`）。本檔本輪未動（Length 4474、LastWriteTime 11:39:09 前後相同）。
- 本 session feed 檔 `~/.autosdd/context_feed/ab9d77f0-….json`：`mtime 11:47:22`、`"used_percentage": 13`、`"context_window_size": 1000000`、`"version": "2.1.283"`。
- 🔴 `python tools/install_statusline.py --status`（PowerShell 工具內 `python`＝`C:\Users\wuwei\.pyenv\pyenv-win\versions\3.11.9\python.exe`）：`"matches_current_checkout": false`、`STATUS_RC=1`；`.venv\Scripts\python.exe` 同指令：`true`、`VENV_STATUS_RC=0`。pyenv 3.11.9 目錄 `pythonw.exe` 存在（`Test-Path` True）。
- 環境：`CLAUDE_CONFIG_DIR`／`SDD_ACTIVE_VERSION`／`AUTOSDD_UNATTENDED`／`CLAUDE_PROJECT_DIR`／`HOME` 在 PowerShell 工具內皆空；`USERPROFILE=C:\Users\wuwei`；載具 `.venv\Scripts\pythonw.exe` True；`claude --version` 2.1.283。
- `.bak-*` 清理（掌舵者本輪指示）：`before=146 after=1`，保留 `settings.json.bak-20260928T005957Z`（609 bytes，R179 真安裝備份），其餘 145 支 DEF-200-409 測試殘留已刪；`settings.json` 未動。
- 額度守衛活體：第二支 Workflow 被 PreToolUse 擋下——`kind=five_hour 53% 剩 32 分鐘 band=notice … ⇒ cap=3 recommended=3 band=notice binding=five_hour`、`Workflow 本次不執行 … 請改逐個派 Agent（每 300s 最多 3 個）`。收斂型工具全程未受影響。

## 三、四方分析、反駁鏡與完整性批評（摘要；完整 JSON 住 session workflow journal `wf_f837808b-f27`）

| 發現 | 來源 | 鏡 A（重現） | 鏡 B（範圍治理） | 主控裁決 |
|---|---|---|---|---|
| 直譯器綁定（ARCH-1／SD-1／QA-1 同一件） | 三方獨立 | 三鏡皆親跑 pyenv vs venv `--status` 重現 rc=1／0 翻轉，成立 | ARCH-1／SD-1 成立（帳本零登記、docstring 190-191 自稱「本 checkout」與實作矛盾、修法不違鐵律）；QA-1 鏡 B 以「本輪任務唯讀、非五問射程」駁回 | 批評者判三個掛名的處置互打是實質分歧：技術事實三方一致、只在「這輪做不做」不同；主控採 SD-1 amended_fix（區域延遲 import＋fail-open 退回），立 **DEF-200-411** 同輪修 |
| ARCH-2 既有測試只驗腳本路徑半段 | Architect | 成立 | 駁回（併入 411 的新測試即可） | 併入 411 四格測試 |
| SA-1 R179 TOTAL-by-hook 表未含 PostToolUse 出聲事件（64 筆，非阻斷） | SA | 成立 | 駁回（根 CLAUDE.md 機械守衛總表已明寫「水位出聲」是設計內非阻斷；不回頭改已發布證據檔） | 只在本檔登記：該表只統計 PreToolUse 真阻斷 |
| SA-2 literal 普查 Agent／Workflow guard 各差 1（10 vs 11） | SA | 成立（兩種計數法皆重現 10） | 駁回（貪婪／非貪婪 regex 就有 2 倍以上漂移，±1 在雜訊內；R179〈九〉已自陳掃描窗口邊界） | 登記：下次掃描把腳本原始碼＋檔案清單一起存，讓數字可 diff |
| SD-2＝DEF-200-410 | SD | 成立（`--plan` 逐字列 676 為可搬） | 駁回「本輪射程」 | 主控裁決仍修：帳本本就 open、修法已寫在解鎖條件、能當場修就不延後 |

完整性批評者五項缺口：①411 是本輪收斂敘事唯一破口（採納、已修）；②Q2 字面應降 PARTIAL（採納）；③SA 對逐字稿母體給了 55／58／63 三個數字（55＝R179 引用值、63＝SA 全 slug 掃描、58＝主 slug 非遞迴；本檔登記、不影響方向性結論）；④JSON 內數則鏡的 reasoning 被截斷（主控以 journal 原文補讀後裁決）；⑤Q5 只有 QA 一方頂層表態（本檔〈一〉明寫）。

## 四、修法與紅→綠證據（Developer `[他包回報]`；主控收尾窗口親驗見〈六〉）

**DEF-200-411**（`tools/statusline_context_feed.py`＋`tools/install_statusline.py`＋`tools/tests/test_install_statusline.py`）
- 新增 `_repo_venv_python(repo_root)`：區域延遲 import `tools/lib/platform_utils.py::venv_python_path()`（整段 `except Exception` 回 `None`，維持本檔「絕不讓 status line 空白」紀律）；`settings_snippet(repo_root=None)` 用 `venv_python or Path(sys.executable).resolve()`，回傳多一鍵 `_python_basis`（`repo-venv`／`sys.executable`）；`install_statusline.status()` 報告加 `python_basis`。WHY 要 fallback：windows-compat-ci 的根層 unittest 步驟在 `bootstrap.ps1` 之前、根層無 `.venv`；root-infra-ci／macos-compat-ci 用 setup-python。
- 四格測試 `DesiredInterpreterIsRepoVenvTest`：兩個不同假 `sys.executable` 下帶假 `.venv` 的 root 結果相同且落在 fake root；無 `.venv` 退回；無參數呼叫確定性；`status()` 含 `python_basis`。紅端＝拿掉 `venv_python or` 即第一格紅。
- 複審 should-fix（主控採納親改）：`_repo_venv_python` 原以 `repo_root/tools/lib` 找 SSOT，合成 root 只有 `.venv` 沒有 `tools/lib` 時靜默退回，新測試綠燈靠測試檔頂部 `import platform_utils` 的 `sys.modules` 快取偶然過。改為 `Path(__file__).resolve().parent / "lib"`（本檔自己的 tools/lib）。主控探針（不預先 import、fake root 只有 `.venv`）：`basis= repo-venv`／`token= …/tmpf8dmyuch/.venv/Scripts/pythonw.exe`／`under_fake= True`／`platform_utils_from= D:\…\tools\lib\platform_utils.py`／`no_venv_basis= sys.executable`、`PROBE_RC=0`。
- 修後探針（Developer 與複審各跑一次）：pyenv python `--status` ⇒ `matches_current_checkout: true`、`python_basis: repo-venv`、rc=0；pyenv `--print-settings-snippet` 第一 token＝根層 `.venv/Scripts/pythonw.exe`；venv `--dry-run` ⇒ `noop`（真實 settings 不變）。

**DEF-200-410**（`tools/lib/defect_ledger_index.py`＋`tools/archive_defect_log.py`＋`tools/tests/test_archive_defect_log.py`）
- 設計：一支只讀主檔找 `DEF-101-676` 的機械鎖，就是判準⑥「外部居所指針宣稱本列現居主檔」（硬擋、不接受 `--ack`／`--keep`）⇒ `LOCK_TARGETS: dict[str, str]`＋`lock_target_claims()` 住 lib，`plan()` 只把 `claims = residence_claims.get(v["id"], [])` 原地改為 `… + _ledger_index.lock_target_claims(v["id"])`（主檔 1507 行是 SPECIAL_FILES 餘裕 0 ⇒ 淨增 0）。
- 五格測試 `TestLockTargetIsExemptFromMigration`：676 在 blocked 且理由含 DEF-200-410；不在 movable；每個鎖標的在主檔有列；`patch.object(_ledger_index, "LOCK_TARGETS", {})` 後 676 回到 movable（紅端）；`--plan` 子行程 stdout 同含兩個 ID。
- 行為變更：`--plan --keep DEF-101-676` 由合法排除變 fail-loud 拒收（複審親跑 rc=1，訊息「該列本來就被某項判準擋著」）；全 repo 只有 archive_68 標頭的歷史紀錄用過此組合。
- 連帶：新測試的 `--plan` 子行程讓 `test_subprocess_encoding_hygiene.py` 的 child 編碼站點數 67→68 過腐化上界，判準逐字給值 `_CHILD_SITE_FLOOR` 54→65（收緊）。

## 五、誠實劃界

- Q2「模型每次都真的去查」是跨 session 行為傾向，只有掌舵者長期觀察能建立信心；本輪能證明的是機制把真數字與查證指令塞到模型眼前，且 63 份逐字稿第一則回覆零筆「不查就編數字」。
- `ctx` 行是否真的顯示在掌舵者新視窗最下方、以及有無閃窗，只有掌舵者看得到；主控能證明的是進料器在本視窗被 Claude Code 成功呼叫、feed 隨訊息更新。
- 四方與鏡的數字皆 `[他包回報]`；主控親驗了 `--status` 兩種直譯器的 rc、探針、四支針對性測試與全套（〈六〉）。
- SA 逐字稿母體三個數字（55／58／63）在本檔登記、原因未逐一對帳；不影響 Q1 的方向性結論（0 筆命中原文所述事件）。
- DEF-200-341 維持 open（解鎖改 CI runner）是治理裁決，掌舵者可重開。

## 六、收尾親驗（主控本場真跑，rc 逐字）

- 四支針對性測試（DEF-200-411 修正 should-fix 後）：`test_install_statusline.py` `Ran 30 … OK` rc=0（R179 為 26）；`test_statusline_context_feed.py` `Ran 19 … OK`；`test_session_brief.py` `Ran 24 … OK`；`test_subprocess_encoding_hygiene.py` `Ran 39 … OK` rc=0（修前該檔 1 failure＝child 站點 68 > 上界 67，重釘 65 後綠）。
- DEF-200-410：`test_archive_defect_log.py` `Ran 188 … OK` rc=0（R179 為 183）；`archive_defect_log.py --check` rc=0；`--plan` rc=0（主檔 99,844 bytes、112 列；可搬 6 筆不含 676；676 落在不可搬段、理由含 DEF-200-410）；`check_defect_log_crossref.py` rc=0；`test_check_defect_log_crossref.py` `Ran 268 … OK`；`test_check_archive_required.py` `[他包回報] Ran 9 … OK`。
- 護欄棘輪：`--print-guard-lines` 三次收斂至 `淨額 107709→107709 (+0)`／`逐檔漂移 0 支`；`test_adr_xplat001_c1c2_lock.py` `Ran 192 … OK`、`[Scan-H triplet] UEP=5 AC=47 GLC_FILES=87 GLC_LINES=107709`；`test_doc_loc_baseline_freshness_r60.py` `Ran 281 … OK`。逐檔：`test_install_statusline.py` 297→377、`test_archive_defect_log.py` 4032→4076、`test_subprocess_encoding_hygiene.py` 1584→1585、本表自身 8959→8983。
- ruff：根層快層 `ruff check tools/ .claude/hooks/` `All checks passed!` rc=0；`--isolated --select E501 --line-length 100` 對改到的六支 .py 皆 0 筆新增命中。
- 帳本：`DEF-200-411` 列 683 bytes、`DEF-200-410` 列 671 bytes（皆 ≤ 700）；主檔 99,844 bytes 在安全區、未觸發輪替。
- 工作樹：`git status --short` 十二支 M ＋本證據檔 untracked，無其他殘留；`git stash list` 空。
- 根層全套與 push／雲端：見〈七〉（追記）。
