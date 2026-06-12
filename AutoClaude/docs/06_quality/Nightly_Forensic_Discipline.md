# Nightly / CI 取證紀律（SD_09 W0 教訓 — 16 條強制紀律 + 採樣統計）

| 項目 | 內容 |
|------|------|
| 來源 | SD_09 W0 教訓 + W3 Round 1~42 zero-trust audit 累積 |
| 上層 ADR | [ADR-SD08-001](../04_planning/ADR/ADR-SD08-001-claude-md-budget.md) §2.1 規範性內容可外移細節 |
| 對應實作 | [tools/run_local_nightly.ps1](../../tools/run_local_nightly.ps1)（707 行）+ [tools/](../../tools/)（10 helper + unit test）|
| 行號註記 | 本檔 file:line 引用為 commit 當下取證；ps1 變動後行號漂移屬正常，以錨點關鍵字（如 `AUTOCLAUDE_*_P95_THRESHOLD_MS` / `F2 OK` / `ac4_junit.xml`）為準（R42 audit 校正）|
| 對應根因報告 | [SD09_W0_Nightly_RootCause_Report.md](../05_development/SD09_W0_Nightly_RootCause_Report.md) |
| 維護 | 任一條紀律違反 → P0 audit；新增紀律由 audit 發現 → 編號累加，**不可重排** |

---

## 1. 紀律的由來

前 3 輪 W0 修復都「載具修了根因沒修」，第 4 輪二次 audit 打中載具根因，第 5 輪三次 audit 才打中**判定邏輯**根因，第 6 輪 W3 audit 打中**跨 stage 一致性**根因。下列 13 條為**強制紀律**，CLAUDE.md §「Nightly / CI 取證紀律」維持編號清單摘要 + 連結至本檔。

---

## 2. 16 條強制紀律（完整版）

### 紀律 #1 — stage rc 必須區分「真實失敗」vs「工具標準回報」

工具 exit code 可能是 bitmask（如 mutmut 2.4.x：`bit0=exception, bit1=survived, bit2=timeout, bit3=suspicious`），**不可單純用 `rc != 0` 判 fail**。先查工具文件 / source 確認 exit code 語義，再決定哪幾個 bit / 哪幾個值才算「真 crash」（mutmut：`rc & 1 != 0`）。

對應實作：[tools/mutmut_exit_code.py](../../tools/mutmut_exit_code.py)（bitmask classify + 33 unit case）。

### 紀律 #2 — log 必須包含完整統計，不可信任預設 dump

如 `mutmut results` 預設只列 Survived 區段，缺 `Killed (N)` → 下游 baseline_lock 算出 kill_rate=0% **假象**。需直接 query 工具的 raw data store（如 `.mutmut-cache` sqlite Mutant 表）寫出完整 counts。

對應實作：[tools/run_mutmut_in_docker.sh](../../tools/run_mutmut_in_docker.sh)（sqlite3 query Mutant 表）+ [tools/mutmut_counts_parser.py](../../tools/mutmut_counts_parser.py)（marker section 擷取）。

### 紀律 #3 — PASS 聲稱必須引用 RunId log 行號

文件 / 報告寫「✅ 修復後綠燈」必須附 `logs/nightly_YYYY-MM-DD_HHMMSS.log:L行號`；不接受「歷史某輪綠燈快照」概括表述。`logs/nightly_latest.log` 為單一真相。

### 紀律 #4 — 驗證鏡子自身要被驗證

任何 `validate_*` / 真實性判定工具必須有單元測試（如 `tests/tools/test_validate_mutmut_log.py` 15 case），測試「假 PASS 場景能被拒絕」而非只測通過路徑。延伸：ps1 複雜分支邏輯也要被驗證（如 ps1:492-521 `F2 OK`/`F2 ALERT` AC4 解析分支 ↔ [tools/ac4_nightly_alert_parser.py](../../tools/ac4_nightly_alert_parser.py) SSOT 同構樣板）。

### 紀律 #5 — 跨工具數字對齊 assertion

同一來源被多工具 parse 時（如 `mutation_analysis.py` vs `mutation_baseline_lock.py` 同一 log），不一致時印 WARN 並以 summary 為單一真相，不可悄悄產生兩套數字。

### 紀律 #6 — 採集寬鬆 vs 升級嚴格必須分軌

env override（如 `AUTOCLAUDE_TEST_P95_THRESHOLD_MS`）若同時影響「採集容忍」與「升級判定」即等於放棄 PM 拍板門檻。雙軌：採集容忍 + 升級嚴格分別設定。對應 ps1:310-312：`AUTOCLAUDE_COLLECTOR_P95_THRESHOLD_MS=80` / `AUTOCLAUDE_STRICT_P95_THRESHOLD_MS=60` / `AUTOCLAUDE_OBSERVATION_P95_THRESHOLD_MS=50`。

### 紀律 #7 — cache 路徑必須強制 fresh baseline

任何依賴 `.mutmut-cache` / `.pytest_cache` / `.ac4_junit.xml` / `perf_results.json` 等本地 cache 的 nightly stage，每次跑前 `rm -rf` 強制 fresh；避免「舊資料 + 當次 crash → 老 summary 騙過驗證」。對應 ps1:462（`.ac4_junit.xml`）、ps1:534（`perf_results.json`）、run_mutmut_in_docker.sh:67（`.mutmut-cache`）。

### 紀律 #8 — 載具腳本（.sh）必須 LF 行尾

跨 Docker container 執行的 `.sh` 若被 Windows git autocrlf 轉成 CRLF → Linux `bash` 噴 `$'\r': command not found` + `syntax error`，視為 P0。專案根層 `.gitattributes` 強制 `*.sh text eol=lf`；新增 `.sh` 後 `file path/to/script.sh` 驗證為「Bourne-Again shell script ... text executable」（無 `with CRLF`）。SD_09 W0 P0-AUDIT-31 修復項。對應 hook：[tools/hooks/check_sh_eol.py](../../tools/hooks/check_sh_eol.py)。

### 紀律 #9 — 依賴 Docker / 外部服務的 stage 必須維持跨 stage SKIP 一致性

同一個 nightly run 中，若 Docker daemon 不可用，**所有**依賴 Docker 的 stage 必須以**相同方式**標 SKIP（外層 `$rc='SKIP'` + WARN log + 寫一筆 N/A jsonl record），**不可有 stage 跑空殼跳過 if 區塊回 rc=0 偽報「綠燈」**。違反 → summary 顯示 `drift=0` 等綠燈但實際完全未驗證 → 觀察期 #3 累計被假象污染。SD_09 W3 P0-DRIFT-1 修復項（drift stage 對齊 mutation/pg-e2e SKIP 模式）。

### 紀律 #10 — fallback 路徑與真實路徑必須 jsonl 可區分

任何 `try/except` 後 mock fallback（如 LocalLogger import 失敗回 `count=1`）若與真實 emit 1 次數字相同，即等於假象綠標。**必須**在 jsonl 同時寫入布林標記欄（如 `observability_emit_real: bool`），讓升級判定工具（如 `observability_ga_check.py`）拒絕 `=False` 紀錄。SD_09 W3 zero-trust audit F1 修復項。

### 紀律 #11 — latest log pointer 必須引用完整 run

`logs/nightly_latest.log` 必須由 nightly script 末段 `Copy-Item` 自完整當次 run 寫入；不可在 stage 中段更新或從 partial buffer 取。partial / stale latest 會讓「綠燈聲稱」對應到的 log 行號失效（紀律 #3 RunId log:L 取證失敗）。同時 Windows file lock 場景下 log 寫入須用 `FileShare.ReadWrite` + retry（見紀律 #8 延伸），避免 tail -F 干擾寫入。SD_09 W3 Round 2 audit P0-2 修復項。對應實作：[run_local_nightly.ps1](../../tools/run_local_nightly.ps1) `Add-LogLineSafe` + 末段 `Copy-Item`。

### 紀律 #12 — mutation history 必須有 source_sha256 區分

`.mutation_history.jsonl` 每筆 record 必須含 `source_sha256` 欄位（plugin 目錄 .py 檔合併 sha256 截 16 chars）。`should_lock` 必須驗證 tail 7 筆 `unique source_sha256 ≥ 7`，否則 = 同 commit 重跑 7 次騙過 lock（即使 kill_rate 達標也應拒絕）。舊紀錄缺欄位寬鬆通過（向下相容），但新紀錄必填。SD_09 W3 Round 2 audit P0-5 修復項。對應實作：[tools/mutation_baseline_lock.py](../../tools/mutation_baseline_lock.py) `should_lock` line 226-307 雙分支邏輯。

**SD_09 W3 Round 31 強化（P1-R31-2 修復）**：同 sha multi-run kill_rate variance > 3pp 時必須印 WARN（mutmut suspicious 半確定性風險）。對應 [tools/mutation_baseline_lock.py compute_consistency_warning](../../tools/mutation_baseline_lock.py)。避免單次 outlier（如 R30 85.57% vs 同 sha 復跑 74.83%）被當作真實 baseline 而誤鎖定。

### 紀律 #13 — 觀察期 jsonl 累計進度必須可見

`tools/run_local_nightly.ps1` 末段必須印 `END observation progress: mutation=N/7 ac4=N/14 obs=N/30 drift=N/30 (jsonl records; same UTC-date dedup per M-05)`。jsonl 採同 UTC date dedup（防同日多 run 灌水偽造觀察期）→ user 連跑 N 次 nightly jsonl 只進帳 1 筆；缺進度可見性 → user 誤判「跑了 N 次都進帳」實際只進帳 1（紀律 #3 取證可見性延伸）。SD_09 W3 Round 5 audit P1-AUDIT-R4-2 修復項。

**SD_09 W3 Round 19 強化（P1-AUDIT-R18-2）**：除 `N/門檻` 外，須同時印 `delta=N; stage=R` 雙印 — `delta=0; stage!=0` 即明示「本次未進帳因 stage crash」，避免 `ac4=4/14` 持平讓 user 誤以為觀察期未進帳是 dedup 結果（實際是 stage exception）。對應 ps1 跑前 `Get-JsonlCount` pre-snapshot + 跑後 delta 比對。

### 紀律 #14 — schtasks 自動跑 vs 互動跑必須 PATH 等價 + StrictMode 3.0 嚴格保護 $null.Property

**背景（SD_09 W3 Round 19 nightly 第 14 跑首次自動跑 P0）**：02:00 schtasks 自動跑（SYSTEM 帳號）vs 互動 PowerShell（user 帳號）**PATH 不等價** — pyenv-win 互動 hook 動態注入 `versions/<ver>/Scripts/` 但 schtasks spawn 的 powershell **不繼承** → `Get-Command alembic.exe` 回 `$null`。配合 StrictMode 3.0 開啟（紀律 #11 後續落地），任何 `(Get-Command X -ErrorAction SilentlyContinue).Source` 鏈式存取在 `$null.Source` 時拋 PropertyNotFoundException → 整個 stage 36ms 內 crash（[logs/nightly_2026-05-26_020001.log:172-174](../../logs/nightly_2026-05-26_020001.log)）。互動模式因 pyenv hook 注入 Scripts 路徑而 14 輪躲過此 BUG，直到首次 schtasks 自動跑曝光。

**強制條款**：

1. **PATH 補強**：ps1 開頭必須偵測 `$env:USERPROFILE\.pyenv\pyenv-win` 並自動 append `versions/<latest>/Scripts/` 至 `$env:PATH`（idempotent wildcard 比對防重複）；對應 [ps1:56-87](../../tools/run_local_nightly.ps1#L56)。
2. **禁止鏈式 .Source 存取**：任何 `(Get-Command X -ErrorAction SilentlyContinue).<Prop>` 或 `(... -EA SilentlyContinue).<Prop>` 模式違規 → P0；改兩步式：
   ```powershell
   $cmd = Get-Command X -ErrorAction SilentlyContinue
   if ($cmd) { $val = $cmd.Source } else { ... }
   ```
3. **靜態檢查鏡子**：[tests/tools/test_run_local_nightly_static.py](../../tests/tools/test_run_local_nightly_static.py) 6 case grep 檢查（紀律 #4 雙向延伸 — ps1 自身也算鏡子）— 包含 StrictMode 必存在、`.Source` 鏈式絕跡、PATH 補強區塊存在、pre-snapshot 存在等。
4. **Pester 行為測試 backlog**：完整 PS 行為驗證（mock Get-Command 回 $null → stage 不 crash）為 SD_10 W0 backlog。

對應實作：[ps1:427-445](../../tools/run_local_nightly.ps1#L427) 兩步式 + [ps1:56-87](../../tools/run_local_nightly.ps1#L56) PATH 補強。

### 紀律 #15 — 呼叫端工具路徑分隔符相容性（Bash 反斜線吞噬根治）

**背景（SD_09 W3 Round 40 audit P2-R40-2）**：Windows 環境下若以 git-bash / Linux-style Bash 工具呼叫 PowerShell 腳本（如 `bash tools\run_local_nightly.ps1`），**反斜線 `\` 會在 shell tokenize 階段被視為 escape character 吞噬** → 變成 `toolsrun_local_nightly.ps1` → `command not found` exit code 127。腳本本身沒執行，所有 ps1 內部防禦（紀律 #14 PATH 等價、`Test-Path` 預檢）**完全失效**（檔案找不到 = 腳本根本沒啟動）。

**強制條款**：

1. **CLAUDE.md / SOP 範例**必須使用正斜線 `tools/run_local_nightly.ps1`（不要 `tools\run_local_nightly.ps1`），PowerShell + Bash + cmd 三 shell 一致解析。
2. **背景啟動命令**：使用 PowerShell 工具直接呼叫 `powershell.exe -NoProfile -ExecutionPolicy Bypass -File tools\run_local_nightly.ps1`（PowerShell 工具不會吞反斜線；或用正斜線在 Bash 工具中呼叫 `tools/run_local_nightly.ps1`）。
3. **schtasks Action 命令**：作業排程使用絕對 Windows 路徑（如 `D:\CursorProject\AutoClaude\tools\run_local_nightly.ps1`），不經 Bash 中介。
4. **失敗診斷流程**：見 exit 127 立刻檢查呼叫端是否反斜線在 Bash 工具中被吞，**不是** ps1 內部問題。
5. **單元測試鏡子（紀律 #4 雙向延伸）**：[tests/tools/test_run_local_nightly_static.py](../../tests/tools/test_run_local_nightly_static.py) 新增 1 case 驗證 CLAUDE.md / Round*_NextAction.md 範例片段一律 `tools/` 正斜線。

對應實作：本檔紀律條款 + CLAUDE.md §「Nightly / CI 取證紀律」摘要更新；ps1 本身無變動（問題在呼叫端不在腳本內）。

### 紀律 #16 — pytest 數字 SSOT 必須註記隨機性與 fixture 前提

**背景（SD_09 W3 Round 40 audit P1-R40-1 偽陽性 + 預防）**：QA Agent 在外部環境裝 pytest-randomly 觀察到 3-8 個 fail bounce，但本 repo 未裝 pytest-randomly（`pip show pytest-randomly` → not found）→ 數字 2,716 在本 repo 環境穩定。**為防止未來有人安裝 pytest-randomly 後混淆 SSOT**，必須在 NextAction / sprint_history.md 引用 pytest 數字時註明隨機性前提。

**強制條款**：

1. **pyproject.toml 鎖定**：`[tool.pytest.ini_options]` 不安裝 `pytest-randomly`（避免引入測試隔離污染變數）；若未來引入需先補完所有跨 fixture 隔離問題。
2. **SSOT 註記前提**：sprint_history.md / NextAction / CLAUDE.md 引用 pytest 數字時加註「（pytest-randomly 未啟用，順序由 collection 確定）」；亦可採用「依 pyproject.toml [tool.pytest.ini_options] 設定下」一句註明。
3. **驗證方式**：`pip show pytest-randomly 2>&1 | grep -E "WARNING.*not found"` 必須命中；若未來引入 pytest-randomly，nightly 跑 3 次連續對齊 SSOT 才能更新數字。
4. **跨工具一致性（紀律 #5 延伸）**：pytest 跑「-q --tb=no」與 nightly stage `pg-e2e + AC4 collector` 內測試數字 SSOT 必須一致。

對應實作：本紀律 + pyproject.toml 維持不含 pytest-randomly；未來引入需經 PM 拍板 + 補測試隔離。

---

### 紀律 #17 — zero-trust 須雙向：agent audit 結論本身亦須複核（檔案存在性勿單憑 `fd`）

**背景（SD_09 W3 Round 57 audit）**：四方並行 audit 中 SD agent 聲稱「commit 註解引 `tests/infra/test_pg_memory_store_security.py:14` 該檔不存在」，主 agent 複核發現**該檔存在且 L14 確有 `pytest.importorskip("sqlalchemy")`，引用準確**——agent 的 `fd` 工具未安裝，其 file-existence 檢查靜默失準產生**誤報**（false positive）。zero-trust 不僅驗「系統 / 前輪結論」，亦須驗「本輪 audit agent 自身結論」，否則誤報會污染 backlog 與 NextAction。

**強制條款**：

1. **檔案存在性聲稱複核**：任何 agent（含 subagent）聲稱「某檔案 / 路徑不存在」時，主 agent 必須以 `find` / `rg -l` / `ls` 至少一種**獨立工具**複核後才採信；嚴禁單憑 `fd`（環境可能未安裝，`fd` 缺失時不報錯而回空 → 易誤判為「不存在」）。
2. **agent 結論分級**：subagent audit 之 P0/P1/P2 finding 在落入 backlog / NextAction 前，主 agent 須對「可機械驗證」者（檔案存在、數字驗算、行號）親跑複核；複核失敗者標記為「誤報」並記錄根因（如本輪 `fd` 未安裝）。
3. **取證對稱**：誤報與真實缺陷同樣需在 sprint_history / NextAction 留證（紀律 #1 / #3 延伸），證 audit 為真實挑戰而非橡皮圖章。

對應實作：R57 NextAction §3 誤報-1 + 本紀律；後續 zero-trust audit SOP 沿用。

---

## 3. 採樣統計紀律

baseline lock 必須 `samples ≥ 20`；< 20 印 warning「statistical noise high; not blocking」；同時 `perf_regression_check.py` 在 baseline samples<20 時自動將 BLOCK 退化為 WARN（語意一致，SD_09 W0 P0-AUDIT-perf-followup 修復）。對應 ADR-SD08-003 §2.6 v1.1。

`perf_regression_check.py` rc 三態：
- `0` = 綠
- `2` = warn（含 BLOCK→WARN 退化）
- `1` = block

`Invoke-Stage` rc=2 視為 WARN 不算 fail（SD_09 W3 Round 2 audit P0-6 修復項）。

---

## 4. CLAUDE.md ↔ 本檔 cross-reference

CLAUDE.md §「Nightly / CI 取證紀律」維持 16 條編號標題清單（一行一條）+ 連結至本檔 §2。**任何紀律新增 / 修訂必須先改本檔，再同步 CLAUDE.md 摘要**。

---

**文檔元數據**：v1.2（SD_09 W3 R40 — 新增紀律 #15 呼叫端反斜線吞噬根治 + #16 pytest SSOT 隨機性前提註記）| 建立 2026-05-26 | 最後更新 2026-05-28 | 維護者：Tech Lead
