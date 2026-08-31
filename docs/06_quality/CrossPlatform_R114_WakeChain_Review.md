# CrossPlatform R114 — 喚醒鏈 PRD 修憲案四方複審 ＋ Windows 實機取證批（證據檔）

> R114（Windows 11 輪；架構輪）唯一逐字證據載體。交接書＝`R114_HANDOFF.md`。
> 本輪零生產碼改動：改動面＝PRD 修憲案一檔＋帳本兩軌＋本檔＋交接書。

## 1. 輪次判型與開場量測（2026-08-31 實跑）

- `check_defect_log_crossref.py --unresolved-count`：未結 **53**／166（warn=86、fail=98）；外部軌 8 筆；長債軌 7 筆。
- 帳本主檔 150,509 bytes（上限 262,144；`check_archive_required.py`＝未觸發）。
- c1c2 守衛線淨額 89592→89592（+0）。
- `--pace`（14:07:46）：band=free、可派 4。
- 判型＝**架構輪**（A 結案輪／帳本壓力皆未觸發；交棒書指定喚醒鏈 PRD 四方複審最優先）。

## 2. 喚醒鏈 PRD 修憲案（批次序 v2.1.13）四方複審記錄

標的＝`docs/04_planning/PRD_Amendment_R113_WakeChain_LastMile.md`（複審前 149 行 → 收斂後 **180** 行；Status 維持 Proposed，落款待掌舵者）。

### 2.1 一輪（四方獨立；Workflow 4 agents，subagent tokens 689,623／tool calls 175）

| 方 | 判決 | blocking |
|---|---|---|
| Architect | REJECT | 6 |
| SA | APPROVE_WITH_CONDITIONS | 3 |
| SD | APPROVE_WITH_CONDITIONS | 4 |
| QA | REJECT | 5 |

去重後 **13 blocking＋6 advisory**。「§0 宣稱三列解鎖條件原指向 R112，但 DEF-200-234 實指 ADR-XPLAT-014 §4」**四方同時獨立命中**。PRD 標的 19 個程式行號座標三方獨立現查全命中（僅兩筆 LOC 快照偏移一格：planner 749/750 餘裕 1、guard raw 1089/1089 餘裕 0）；`--permission-mode acceptEdits` 與 `--settings` 兩個 [需核對] 旗標經本機 `claude --help` 正面解除。

13 筆 blocking（一句話索引；逐字證據＝本 session workflow `wf_3fbcebef-499` 轉錄）：①§0 解鎖條件指向誤述（四方同中）②煞車一被靜默放寬（2 窗 vs R112 即停）③狀態機 16 格中 11 格無次態④§3(d)「下一個 session 武裝不回來」與 SessionStart 清閂現碼不符⑤allow/deny 全 Bash 條目在 Windows 結構性失效⑥deny 漏 Edit 通道＋鎖檔零保險⑦LOC 兩數字偏移⑧G4 無 REQ 錨點⑨§3(e)③ 與 hook docstring 矛盾⑩失敗態不在重掛集合⑪files_changed 事後單量髒樹誤計⑫§3(b)5 落點誤指 quota_escalation⑬V-d1 缺 Windows 憑證＋空字串無鑑別力。

### 2.2 掌舵裁決要點（修訂依據）

煞車一出廠值改 **1**（對齊 R112，上調走 ENV 實測）；狀態機判定序明定 **③→④→②→①**；deny 對 L3 三檔各列 Write/Edit/NotebookEdit；allow/deny 雙平台孿生（PowerShell 條目，[需核對]）；`_GOV_EXACT` 於實作批納管 `.claude/settings.unattended.json` 與 `tools/tests/test_adr_xplat001_c1c2_lock.py`（「紅線 10 一字不改」改寫為「語意不變、成員清單增補」）；失敗態一律進 WINDOW_DONE 且停止次態全重掛；files_changed＝spawn 前後兩次 porcelain 快照差集。

### 2.3 修訂三批（同一修訂 agent）＋二輪複審

- 批1：13 blocking＋6 advisory＋追加 §6.9（govwrite 大小寫繞過劃界，見本檔 §4）→ 檔案 149→179 行。
- 二輪波1（Architect＋QA）：**13/13 已落實、零新 blocking**；共同命中 3 minor（`--check` allow 條目缺席、V-c1 痕跡事件字面、證據檔懸空指向）→ 批2 修訂。QA 以獨立探針重證 §6.9 敘述屬實。
- 二輪波2（SA＋SD，依 pace 降級建議帶 sonnet 載具）：SA AWC（1 minor＝證據檔落檔，本檔即閉合）；SD AWC（1 Major＝`_run_resume()` 回傳契約無法區分 REFUSE 與非零 rc）→ 批3 修訂（實作前置句＋V-d4＋quotepath SSOT 句）→ 檔案 180 行。
- SD 定點複核：三處全通過，最終判 **APPROVE**。

### 2.4 收斂判定

四方條件全數閉合（Arch/QA 的 3 minor 已修；SA 的證據檔條件＝本檔；SD 的 Major 已修並定點複核 APPROVE）。**落款仍待掌舵者**（呈報單見 R114_HANDOFF.md）。

## 3. Windows 實機取證批（2026-08-31 本機實跑）

### 3.1 DEF-200-063（headless hook 活性）→ 解鎖條件達成，結案移出外部軌

- `claude -p --model haiku --debug hooks --debug-file h.log "ok"`：log 含逐字 `Hook SessionStart:startup (SessionStart) success:` ＋ `provided additionalContext (191 chars)`（sdd_hook_router 條目）。
- 同 log 兩筆 `EFTYPE: inappropriate file type or format, uv_spawn`＝雙載具佈線的**異平台條目設計性失敗**（`tools/lib/hook_wiring.py:149`「`.py` 直接 spawn 回 `EFTYPE`」／`:166`「Windows 上 .py 不能直接 spawn（實測 EFTYPE）」），非缺陷。
- `Test-Path .venv\Scripts\pythonw.exe` → **True**（載具解析成功）。
- 哨兵 schtasks 值憑證：`AutoSDD_Sentinel_fd8e8794-659b-4303-b057-1730063cf101`，LastRunTime=2026/8/31 14:08:02、LastTaskResult=**0**、**NextRunTime=2026/8/31 14:23:02**（15 分鐘巡邏活著，靜默無視窗）。
- `-WindowStyle Hidden` 機械物實機重跑：`tools/tests/test_check_hooks_liveness.py`＝**170 passed＋132 subtests passed**（11.66s）；`test_context_budget_guard.py -k SentinelWiring`＝**12 passed**（28.36s）。

### 3.2 DEF-200-147（govwrite 三項）→ 解鎖條件達成，結案移出外部軌

- ① 12 列 rc 矩陣 Windows 重跑：`test_block_destructive_git_r83.py -k TestGovernanceFilesAreReadOnlyWhenUnattended`＝**12 passed＋24 subtests passed**（1.74s）。
- ② NTFS 大小寫繞行探針（唯讀，直呼 `govwrite_hit()` 純函式）輸出逐字：

```text
'.env' -> '.env'
'.ENV' -> '.env'
'tools/lib/quota_gate.py' -> 'tools/lib/quota_gate.py'
'Tools/Lib/Quota_Gate.py' -> 'tools/lib/quota_gate.py'
'd:\\CursorProject\\AISDCL_Agent\\.ENV' -> '.env'
'd:\\CursorProject\\AISDCL_Agent\\TOOLS\\LIB\\QUOTA_GATE.PY' -> 'tools/lib/quota_gate.py'
'.claude/SETTINGS.JSON' -> '.claude/settings.json'
'.ENV.nosuchfile' -> None
'.autoclaude/state.json' -> '.autoclaude/state.json'
'.AUTOCLAUDE/state.json' -> None
'.claude/hooks/NEW_GUARD.PY' -> None
realpath(.ENV) -> D:\CursorProject\AISDCL_Agent\.env
.env exists -> True
```

  已存在檔的大小寫變體**全數命中**（`.ENV`／`Tools/Lib/Quota_Gate.py`／`.claude/SETTINGS.JSON`）＝解鎖條件②的原始疑慮解除；「尚不存在目標」兩形態繞過＝**新缺口另立 DEF-200-238**（見 §4）。
- ③ schtasks 取證：哨兵 NextRunTime 值見 §3.1；halt 多軸武裝 argv（`quota_escalation.py:353` 含 `-WindowStyle Hidden`）由 `test_context_budget_guard.py:5996` 斷言、實機 12 passed。誠實留白：真 halt 事件本窗未發生，halt 武裝的**現場** NextRunTime 無從取證（機制面已由測試釘住）。

### 3.3 DEF-101-693（windows-smoke 22 步）→ 部分覆蓋，列保留、複查日更新

- 先行判準：`test_smoke_ci_sync.py -k test_registered_smoke_groups_exist_in_that_script`＝**1 passed**。
- 實機執行紀錄：`windows_smoke_local.ps1`（`powershell.exe -NoProfile -ExecutionPolicy Bypass -File` 原生 5.1 載具、背景執行落 log）＝**PASS=12 FAIL=0 rc=0**，log 尾行逐字「===== 彙總：PASS=12 FAIL=0 =====／全部通過 ✅（Windows PowerShell 5.1 為本腳本的目標載體）」。
- 誠實劃界（不塗綠）：CI windows-smoke 的 bootstrap 往返（yml :1064/:1092）、dev_start（:1107/:1117）、AutoClaude 子集與 integration_gate（:1203-:1246）、SDD ci-gate 雙軌（:1267-:1278）數列本輪**無獨立實跑紀錄**（其判準面另由收尾窗口全套根層 unittest 部分覆蓋）⇒ 「22 步逐列覆核」未完成，列保留。

## 4. DEF-200-238 立案證據（govwrite 對不存在保護面目標的 Windows 大小寫繞過）

- **機理**：`block_destructive_git.py::govwrite_hit()`（:1160-1176）以 `os.path.realpath` 還原路徑後與 `_GOV_EXACT`／`_GOV_DIR_PREFIX`／`endswith(".py")` 做**字面**比對；Windows realpath 對「已存在的檔」還原磁碟真實大小寫（探針 `realpath(.ENV) -> …\.env`），對「尚不存在的目標」無檔可還原 ⇒ 大小寫變體照字面通過比對。
- **實測繞過兩形態**（§3.2 探針逐字）：`.AUTOCLAUDE/state.json`（`.autoclaude/` 目錄今日不存在，目錄前綴比對失手）→ None；`.claude/hooks/NEW_GUARD.PY`（新檔、大寫副檔名，`endswith(".py")` 大小寫敏感）→ None。含義：無人值守下 agent 寫不進任何**現有**治理檔，但可用大小寫變體**新建**保護面內的檔（NTFS 對後續讀者即同一檔）。
- **三鏡獨立重證**：主控探針（本檔 §3.2）＋二輪 QA（相對與絕對路徑形態皆繞過、已存在檔四變體全命中）＋二輪 SD（`os.path.realpath` 當場覆現兩形態）。
- **修法方向**（已寫入 PRD v2.1.13 §3(a)/§6.9）：比對前大小寫正規化，射程先普查再定（防 R96「normcase 修復加寬 fail-open 面」教訓重演）；與 `_GOV_EXACT` 實作批納管 `.claude/settings.unattended.json` 二檔同批落地。

## 5. DEF-200-212① 接線條件探針（2026-08-31）

唯讀探針（模擬 `main():469` 改接 `unresolved_only=True`）輸出逐字：

```text
current_round = 100
unresolved ids = 56 ; all ids = 1333
strict problems = 3
  - docs/04_planning/R102_HANDOFF.md:45 …（DEF-200-204 在帳本家族內查無列）
  - docs/06_quality/CrossPlatform_R100_Scan_Findings.md:252 …（DEF-200-208 查無列）
  - docs/06_quality/CrossPlatform_R107_Ledger_Closure.md:125 …（DEF-101-559 查無列）
loose problems = 0
```

判定：「等帳本時鐘前進」條件**未熟**（`current_round()` 仍回推 100；三筆歷史交棒行的引用 ID 已結案 ⇒ 嚴格接線今日仍生 3 筆假陽性）。列維持 open；不得為消紅而改寫歷史文件或帳本時鐘輸入。

## 6. 本輪對「量測器／守衛自己」的誠實揭露

- 本檔 §3～§5 全部數字為主控當回合工具輸出逐字轉錄；四方複審與修訂的逐字轉錄住 session workflow/agent 轉錄檔（`wf_3fbcebef-499` 及後續三個 agent），未逐字搬入本檔（量級 68 萬 tokens），本檔只收判決與去重後清單。
- pace 讀數在本輪兩度被 Stop hook 判過期（TTL 135s）並即時重量訂正——守衛工作正常，主控不得引用陳舊額度讀數的紀律經實測有效。
