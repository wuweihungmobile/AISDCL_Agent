# Nightly / CI 取證紀律（SD_09 W0 教訓 — 19 條強制紀律 + 採樣統計）

| 項目 | 內容 |
|------|------|
| 來源 | SD_09 W0 教訓 + W3 Round 1~42 zero-trust audit 累積 |
| 上層 ADR | [ADR-SD08-001](../04_planning/ADR/ADR-SD08-001-claude-md-budget.md) §2.1 規範性內容可外移細節 |
| 對應實作 | [tools/run_local_nightly.ps1](../../tools/run_local_nightly.ps1)（行數快照已移除防漂移，見下列行號註記）+ [tools/](../../tools/)（10 helper + unit test）。R9（2026-07-16）三變更：前置新增 local-ci-gate 全套 stage（對齊 windows-nightly-full）；pg-e2e 加跑 PG contract 測試（獨立 pytest 呼叫，不寫 .ac4_junit.xml 防污染 AC4 取證）；終端 exit code 帶訊號（任一 stage 失敗→exit 1，SKIP=-1/WARN=2 不計）——schtasks「上次結果」從此可反映 stage 健康，取證時不可再假設其恆 0x0。R10（2026-07-17）五變更：mutmut log 驗證失敗 rc 2→1（QA-3，防「假 pass 守門自身觸發」被 WARN 綠出場）；recall pytest rc 以 [ref] 捕捉（QA-4）；新增 sdd-fsm-chaos stage（QA-6，Rule 9.9.4 本地補償）；Docker 連續 ≥3 次 SKIP 升級 exit 1（QA-11，`.docker_skip_streak`）；END mutation 進度改 unique-sha 分子（SA-2）——全部由 test_run_local_nightly_static.py 24 錨點鎖住。mac 薄聚合器對等（R15，2026-07-20）：[tools/run_local_nightly.sh](../../tools/run_local_nightly.sh)（四 stage：macos_smoke／root_unittests／autoclaude_gate／sdd_ci_gate；成功失敗皆寫心跳 `logs/nightly_mac_latest.log`＋RunId log `logs/nightly_mac_<ts>.log` 14 天輪替＋launchd RunAtLoad 當日去重補跑；靜態錨點由 `tools/macos_smoke_local.sh` [7/7] 鎖住）。R16（2026-07-21，DEF-101-225）兩項強化：① BEGIN 行加印 `TRIGGER_SRC`（`manual-force`／`launchd(XPC_SERVICE_NAME=...)`／`manual-interactive`／`non-interactive-unknown` 四態，供事後歸因同日多輪 PASS 是合理手動重跑還是去重漏洞）；② 心跳 mtime 當日去重前置一道 POSIX `mkdir` atomic lock（`AutoClaude/logs/.nightly_mac.lock`，修復原判斷本身 check-then-act 的 TOCTOU 競態；陳舊死 PID 鎖以 `kill -0` 判活性後清除重試，`trap EXIT` 確保釋放） |
| 行號註記 | 本檔 file:line 引用為 commit 當下取證；ps1 變動後行號漂移屬正常，以錨點關鍵字（如 `AUTOCLAUDE_*_P95_THRESHOLD_MS` / `F2 OK` / `ac4_junit.xml`）為準（R42 audit 校正）|
| 對應根因報告 | [SD09_W0_Nightly_RootCause_Report.md](../05_development/SD09_W0_Nightly_RootCause_Report.md) |
| 維護 | 任一條紀律違反 → P0 audit；新增紀律由 audit 發現 → 編號累加，**不可重排** |

---

## 1. 紀律的由來

前 3 輪 W0 修復都「載具修了根因沒修」，第 4 輪二次 audit 打中載具根因，第 5 輪三次 audit 才打中**判定邏輯**根因，第 6 輪 W3 audit 打中**跨 stage 一致性**根因。下列 19 條為**強制紀律**（R9 訂正：本句與標題計數隨 #14~#19 新增未同步，長期停在舊值），CLAUDE.md §「Nightly / CI 取證紀律」維持編號清單摘要 + 連結至本檔。

---

## 2. 19 條強制紀律（完整版）

### 紀律 #1 — stage rc 必須區分「真實失敗」vs「工具標準回報」

工具 exit code 可能是 bitmask（如 mutmut 2.4.x：`bit0=exception, bit1=survived, bit2=timeout, bit3=suspicious`），**不可單純用 `rc != 0` 判 fail**。先查工具文件 / source 確認 exit code 語義，再決定哪幾個 bit / 哪幾個值才算「真 crash」（mutmut：`rc & 1 != 0`）。

對應實作：[tools/mutmut_exit_code.py](../../tools/mutmut_exit_code.py)（bitmask classify + 33 unit case）。

### 紀律 #2 — log 必須包含完整統計，不可信任預設 dump

如 `mutmut results` 預設只列 Survived 區段，缺 `Killed (N)` → 下游 baseline_lock 算出 kill_rate=0% **假象**。需直接 query 工具的 raw data store（如 `.mutmut-cache` sqlite Mutant 表）寫出完整 counts。

對應實作：[tools/run_mutmut_in_docker.sh](../../tools/run_mutmut_in_docker.sh)（sqlite3 query Mutant 表）+ [tools/mutmut_counts_parser.py](../../tools/mutmut_counts_parser.py)（marker section 擷取）。

### 紀律 #3 — PASS 聲稱必須引用 RunId log 行號

文件 / 報告寫「✅ 修復後綠燈」必須附 `logs/nightly_YYYY-MM-DD_HHMMSS.log:L行號`；不接受「歷史某輪綠燈快照」概括表述。`logs/nightly_latest.log` 為單一真相。

**mac 註記（R15，2026-07-20 / DEF-101-201②）**：mac 薄聚合器 RunId log＝`AutoClaude/logs/nightly_mac_<ts>.log`（`run_local_nightly.sh` 開頭 exec 改道、BEGIN 首行帶 run_id；保留 14 天）——本輪起 mac 側 PASS 聲稱同樣可（且必須）引 RunId log:L。心跳檔 `logs/nightly_mac_latest.log` 為 latest **指標**（前 2 行三站點契約；彙總行後〔FAIL>0 時多一行失敗 stage〕以 `log=` 末行指向當輪 RunId log），取證一律以 RunId log 為準（同 TD-N04 pointer 語意）。

**mac 註記補充（R16，2026-07-21 / DEF-101-225）**：BEGIN 行自本輪起同時印 `trigger=<TRIGGER_SRC>`（`manual-force`／`launchd(XPC_SERVICE_NAME=...)`／`manual-interactive`／`non-interactive-unknown` 四態），使 RunId log 本身可歸因「同日兩輪皆 PASS」是合理的手動重跑還是真正的去重漏洞（R16 掃描時實測遇過同日兩輪完整 PASS=4 但缺此欄無法歸因）。同輪並在心跳 mtime 當日去重判斷之前補一道 POSIX `mkdir` atomic lock（鎖目錄 `AutoClaude/logs/.nightly_mac.lock`，`mkdir` 同路徑具原子性；陳舊死鎖以鎖檔內 PID 是否仍存活〔`kill -0`〕判斷後清除重試一次；`trap EXIT` 確保正常/異常結束皆釋放鎖），修復原「心跳 mtime 判斷」本身是 check-then-act、launchd RunAtLoad 與 StartCalendarInterval 兩觸發源或手動重跑時間重疊時可能同時通過去重檢查、重複跑整套 4-stage gate 的 TOCTOU 競態窗口。

### 紀律 #4 — 驗證鏡子自身要被驗證

任何 `validate_*` / 真實性判定工具必須有單元測試（如 `tests/tools/test_validate_mutmut_log.py` 21 case，含 TD-N02 version-marker 4 case），測試「假 PASS 場景能被拒絕」而非只測通過路徑。延伸：ps1 複雜分支邏輯也要被驗證（如 ps1:492-521 `F2 OK`/`F2 ALERT` AC4 解析分支 ↔ [tools/ac4_nightly_alert_parser.py](../../tools/ac4_nightly_alert_parser.py) SSOT 同構樣板）。

**2026-06-12 強化（AutoClaude_Improving_012 Phase 0 TD-N02 / TD-N03）**：
- **TD-N02 mutmut 版本標記**：[run_mutmut_in_docker.sh](../../tools/run_mutmut_in_docker.sh) 於版本檢查通過後寫入 `[run_mutmut_in_docker] mutmut version OK: 2.4.3` 標記行；nightly 呼叫 [validate_mutmut_log.py](../../tools/validate_mutmut_log.py) 加 `--require-version-marker`（缺標記 exit=3，與「非真實 run」exit=2 可區分）— 防 mutmut 換版後輸出格式漂移仍被統計 regex 誤判通過。flag 預設關閉，其他呼叫端零破壞。
- **TD-N03 observability 整合驗證**：observability stage 於 snapshot 成功後驗證 `.observability_history.jsonl` 末筆 ts 之 UTC 日期 = 今日（snapshot 工具以 UTC ISO timestamp 寫入、同日去重後 append 至末行），否則 stage rc=1 — 防「snapshot 印 OK 但實際未落盤」假綠。對應 ps1 observability-snapshot stage（錨點關鍵字 `TD-N03`）。

### 紀律 #5 — 跨工具數字對齊 assertion

同一來源被多工具 parse 時（如 `mutation_analysis.py` vs `mutation_baseline_lock.py` 同一 log），不一致時印 WARN 並以 summary 為單一真相，不可悄悄產生兩套數字。

### 紀律 #6 — 採集寬鬆 vs 升級嚴格必須分軌

env override（如 `AUTOCLAUDE_TEST_P95_THRESHOLD_MS`）若同時影響「採集容忍」與「升級判定」即等於放棄 PM 拍板門檻。雙軌：採集容忍 + 升級嚴格分別設定。對應 ps1:310-312：`AUTOCLAUDE_COLLECTOR_P95_THRESHOLD_MS=80` / `AUTOCLAUDE_STRICT_P95_THRESHOLD_MS=60` / `AUTOCLAUDE_OBSERVATION_P95_THRESHOLD_MS=50`。

### 紀律 #7 — cache 路徑必須強制 fresh baseline

任何依賴 `.mutmut-cache` / `.pytest_cache` / `.ac4_junit.xml` / `perf_results.json` 等本地 cache 的 nightly stage，每次跑前 `rm -rf` 強制 fresh；避免「舊資料 + 當次 crash → 老 summary 騙過驗證」。對應 ps1:462（`.ac4_junit.xml`）、ps1:534（`perf_results.json`）、run_mutmut_in_docker.sh:67（`.mutmut-cache`）。

**2026-06-12 強化（AutoClaude_Improving_012 Phase 0 TD-N01）**：perf stage 除跑前 fresh 外，pytest 跑完後必須**強制驗證 `perf_results.json` 確實產出**（由 `tests/perf/conftest.py` pytest_sessionfinish hook 寫出；對齊 `autoclaude-ci.yml`「Verify perf_results.json present」step），缺檔 stage rc=1 並記 ERROR — 防「fresh 清掉舊檔 + hook 未寫出 → regression check 走『baseline 或 results 不存在』WARN 分支假綠」。對應 [run_local_nightly.ps1](../../tools/run_local_nightly.ps1) perf-baseline stage（錨點關鍵字 `TD-N01`）。

### 紀律 #8 — 載具腳本（.sh）必須 LF 行尾

跨 Docker container 執行的 `.sh` 若被 Windows git autocrlf 轉成 CRLF → Linux `bash` 噴 `$'\r': command not found` + `syntax error`，視為 P0。專案根層 `.gitattributes` 強制 `*.sh text eol=lf`；新增 `.sh` 後 `file path/to/script.sh` 驗證為「Bourne-Again shell script ... text executable」（無 `with CRLF`）。SD_09 W0 P0-AUDIT-31 修復項。對應 hook：[tools/hooks/check_sh_eol.py](../../tools/hooks/check_sh_eol.py)。

### 紀律 #9 — 依賴 Docker / 外部服務的 stage 必須維持跨 stage SKIP 一致性

同一個 nightly run 中，若 Docker daemon 不可用，**所有**依賴 Docker 的 stage 必須以**相同方式**標 SKIP（外層 `$rc='SKIP'` + WARN log + 寫一筆 N/A jsonl record），**不可有 stage 跑空殼跳過 if 區塊回 rc=0 偽報「綠燈」**。違反 → summary 顯示 `drift=0` 等綠燈但實際完全未驗證 → 觀察期 #3 累計被假象污染。SD_09 W3 P0-DRIFT-1 修復項（drift stage 對齊 mutation/pg-e2e SKIP 模式）。

### 紀律 #10 — fallback 路徑與真實路徑必須 jsonl 可區分

任何 `try/except` 後 mock fallback（如 LocalLogger import 失敗回 `count=1`）若與真實 emit 1 次數字相同，即等於假象綠標。**必須**在 jsonl 同時寫入布林標記欄（如 `observability_emit_real: bool`），讓升級判定工具（如 `observability_ga_check.py`）拒絕 `=False` 紀錄。SD_09 W3 zero-trust audit F1 修復項。

### 紀律 #11 — latest log pointer 必須引用完整 run

`logs/nightly_latest.log` 必須由 nightly script 末段 `Copy-Item` 自完整當次 run 寫入；不可在 stage 中段更新或從 partial buffer 取。partial / stale latest 會讓「綠燈聲稱」對應到的 log 行號失效（紀律 #3 RunId log:L 取證失敗）。同時 Windows file lock 場景下 log 寫入須用 `FileShare.ReadWrite` + retry（見紀律 #8 延伸），避免 tail -F 干擾寫入。SD_09 W3 Round 2 audit P0-2 修復項。對應實作：[run_local_nightly.ps1](../../tools/run_local_nightly.ps1) `Add-LogLineSafe` + 末段 `Copy-Item`。

**TD-N04 補充（2026-06-12，AutoClaude_Improving_012 Phase 0 — pointer 時序語意明文化）**：`logs/nightly_latest.log` 為**每次 run 結束後 `Copy-Item` 覆寫**的 pointer（非歷史累積檔）— 任何後續 run 完成即覆寫前次內容。因此「latest = 最後完成的 run」而非「最後啟動的 run」；多 run 並行或補跑歷史場景下 latest 可能與時間直覺不符。**取證一律以 RunId log（`logs/nightly_YYYY-MM-DD_HHMMSS.log`）為準**（紀律 #3），latest pointer 僅供人工快速 retrieve。

### 紀律 #12 — mutation history 必須有 source_sha256 區分

`.mutation_history.jsonl` 每筆 record 必須含 `source_sha256` 欄位（plugin 目錄 .py 檔合併 sha256 截 16 chars）。`should_lock` 必須驗證 tail 7 筆 `unique source_sha256 ≥ 7`，否則 = 同 commit 重跑 7 次騙過 lock（即使 kill_rate 達標也應拒絕）。舊紀錄缺欄位寬鬆通過（向下相容），但新紀錄必填。SD_09 W3 Round 2 audit P0-5 修復項。對應實作：[tools/mutation_baseline_lock.py](../../tools/mutation_baseline_lock.py) `should_lock` line 226-307 雙分支邏輯。

**SD_09 W3 Round 31 強化（P1-R31-2 修復）**：同 sha multi-run kill_rate variance > 3pp 時必須印 WARN（mutmut suspicious 半確定性風險）。對應 [tools/mutation_baseline_lock.py compute_consistency_warning](../../tools/mutation_baseline_lock.py)。避免單次 outlier（如 R30 85.57% vs 同 sha 復跑 74.83%）被當作真實 baseline 而誤鎖定。

**TD-N06 補充（2026-06-12，AutoClaude_Improving_012 Phase 0 — 向下相容語意明文化）**：`source_sha256` 欄位於 SD_09 W3 Round 2 audit P0-5 修復時引入；引入前 `.mutation_history.jsonl` 已存在 2 筆 legacy 紀錄（2026-05-20 / 2026-05-21）缺此欄位。向下相容語意：`should_lock` 在 tail 7 筆中允許**至多 `MAX_BACKWARD_COMPAT_MISSING=2` 筆**缺欄位（常數定義於 [tools/mutation_baseline_lock.py](../../tools/mutation_baseline_lock.py)，SD_09 W3 Round 21 Architect P1 #2 自 ceil(N/2)=4 收緊為 N-2=5 unique 下限），上限 2 恰等於 legacy 筆數 — 即只豁免歷史既存缺欄位紀錄，P0-5 修復後寫入的新紀錄一律必填；缺欄位筆數 > 2 即拒絕鎖定。

### 紀律 #13 — 觀察期 jsonl 累計進度必須可見

`tools/run_local_nightly.ps1` 末段必須印：

```
END observation progress: mutation=<locked|observing|unavailable> (should_lock 權威判定; tail unique-sha U of T; records=N; delta=…; stage=…) ac4=D/14 rolling-window-days (ready=…; records=N; delta=…; stage=…) obs=S/W green_streak (records=N; delta=…; stage=…) drift=S/W green_streak (records=N; delta=…; stage=…)
```

上列 fence 是**契約本體**（形狀），ps1 實際輸出會在其後以 em dash 再接一行語意說明（四軌分子取自哪支權威工具、`records=` 僅供 delta 取證、去重鍵語意），那段是說明不是契約。符號讀法：`U`＝tail 視窗內 unique sha 數、`T`＝tail 視窗大小（**兩者皆由 `mutation_baseline_lock` 回報，不是本檔寫死的 7**）、`D`＝滾動 14 日曆天窗天數、`S`＝green_streak、`W`＝工具回報的 window 門檻、`N`＝jsonl 原始列數。**分母寫法本身就是契約的一部分**：`ac4` 的 `/14` 是常數所以逐字寫死；`obs`／`drift` 的分母來自工具回報，所以這裡**刻意不得填具體數字**（填了就是把「工具改門檻、nightly 仍報舊門檻」那個假進度裝回來）；`mutation` 軌**沒有分母**（分子是 should_lock 判定詞，不是分數）。

obs/drift 兩軌採同 UTC date dedup（M-05，防同日多 run 灌水偽造觀察期）→ user 連跑 N 次 nightly jsonl 只進帳 1 筆；缺進度可見性 → user 誤判「跑了 N 次都進帳」實際只進帳 1（紀律 #3 取證可見性延伸）。SD_09 W3 Round 5 audit P1-AUDIT-R4-2 修復項。

**R10 訂正（SA-2 / DEF-101-142——mutation 軌語意分軌）**：mutation 去重鍵自 ADR-SD09-011 起改為 `source_sha256`（同日多 sha 全計入、同 sha 留最新，見紀律 #12 與 `mutation_baseline_lock._dedup_key` SSOT）——「同日多 run 不進帳」對 mutation 已**反轉**（同日不同 sha 會進帳、跨日同 sha 不進帳），且進度分子必須是 **unique-sha 證據數**、不可用原始列數（R10 實測：live 檔 29 列僅 5 unique sha，原格式會虛報 29/7；並揭露 improving_101 宣稱的方案 A 壓縮從未在本機落盤＝DEF-101-148，R10 已補跑 `--migrate-compact-sha` 29→7 筆）。靜態錨點：`tests/tools/test_run_local_nightly_static.py` case 24。

**SD_09 W3 Round 19 強化（P1-AUDIT-R18-2）**：除 `N/門檻` 外，須同時印 `delta=N; stage=R` 雙印 — `delta=0; stage!=0` 即明示「本次未進帳因 stage crash」，避免 `ac4=4/14` 持平讓 user 誤以為觀察期未進帳是 dedup 結果（實際是 stage exception）。對應 ps1 跑前 `Get-JsonlCount` pre-snapshot + 跑後 delta 比對。

**R69 訂正（S-1b — ac4 軌分子語意，與 mutation 軌 R10 SA-2 同型）**：ac4 分子原本取 `Get-JsonlCount` 的**整檔原始列數**（實測 41）→ 印成 `ac4=41/14`，讀起來像超標三倍、像早就達標；但 AC4 的真實閘門是 [tools/ac4_progress_check.py](../../tools/ac4_progress_check.py) `filter_recent()` 的**過去 14 日曆天滾動窗**，同日實測 `observation_days=7`、`ready_for_labeled_pr=false`。方向性是重點：這個假數字偏向「看起來已達標」，會誘發錯誤的升級動作，比少印一天的漏報更危險。強制三項：① 分子＝呼叫既有權威工具 `ac4_progress_check --json` 取 `observation_days`，**不得**在 ps1 內自造第二套滾動窗邏輯（那就是新的漂移點）；② 必須加印 `rolling-window-days` 語意標記與 `ready=<ready_for_labeled_pr>`，原始列數改以 `records=` 併印保留取證；③ 取不到閘門值時印 `unavailable`，**不得**靜默退回原始列數（退回＝把剛拔掉的假達標裝回去）。對應 ps1 `Get-Ac4Gate`。

**R69/R71 補充（S-4 / A-2 — obs 軌：`obs=N/30` 不是 GA 判準）**（**描述 R71 G-3 前的狀態**，該格式已於 R71 拔除，現行契約見上方 fence 與下方 G-1/G-2/G-3 訂正）：END 進度的 `obs=N/30` 是 jsonl 原始列數，obs 軌**真實 GA 判準**是 [tools/observability_ga_check.py](../../tools/observability_ga_check.py) 的 `green_streak >= 30`（ps1 `Get-ObsGaPass`）。兩者今天剛好都是 41 純屬巧合（尚未中斷過），一旦中間出現一筆非綠就分岔，屆時拿列數當閘門會重演 S-1b 的假達標。同輪並把 SD_09 W0 **G0 三軌綜合判定**（`[G0-READY]` / `[G0-NOT-READY]`）自一次性排程任務搬到每晚都會跑的 nightly（原任務 2026-06-29 觸發一次後 NextRunTime 永遠空白 → 此後零檢查），判定**不進 exit code**（觀察期未滿是預期狀態，接進 `finalFailures` 會讓每晚都紅，違反紀律 #1）。

**R71 訂正（A-2 — 閘門 helper 必須看退出碼，且「量不出來」要與「未達標」可區分）**：`Get-ObsGaPass` 初版只做 `$raw -match '[PASS]'` 而**完全不看 rc**——工具 rc≠0 但輸出裡出現 `[PASS]` 字樣即回 `Pass=$true` → nightly 印出**假的 [G0-READY]**（本節整套紀律要消滅的正是這種假達標數字，卻在活載體上自種一個）。另一半同樣壞：工具真的壞掉（rc≠0 且輸出無判定）時回 `Ok=$true/Pass=$false`，被讀成「觀察期未達標」——「還沒到」要等、「量不出來」要修工具，處置完全不同。強制三項：① 閘門 helper 改走工具的 `--json` 結構化輸出，不刮人類可讀文字；② 必須取 `$LASTEXITCODE` 並做 **rc ↔ status 一致性檢查**（`observability_ga_check.main` 契約為 `return 0 if passed else 1`，兩者對不上即代表輸出與 rc 不同源 → 判工具壞掉，fail-closed）；③ 呼叫端 gap 敘述必須把 `Ok=$false` 印成 `TOOL-UNAVAILABLE` 而非「未達標」。行為層鑑別力（含「rc=2 + `[PASS]` 文字」這個舊實作原形）由 `tests/tools/test_run_local_nightly_static.py::TestObsGaPassBehavior` 真跑 PowerShell 鎖住，非靜態 grep。

**R71 訂正（G-1 / G-2 / G-3 — 四軌分子與分母一律向權威工具現場提問；上方 fence 已同步）**：R69 只修了 ac4 一軌，其餘三軌仍是「分母是判準門檻、分子卻是 jsonl 原始列數」。R71 實測：obs 42 列 vs green_streak 42（**巧合相等**）、drift 35 列 vs green_streak 26（**已經分岔**）、mutation 整檔 unique-sha vs 權威只看 tail 7 筆。三軌全部改接權威實作——mutation 分子改印 [tools/mutation_baseline_lock.py](../../tools/mutation_baseline_lock.py) `should_lock` 的**判定詞**（`locked`／`observing`／`unavailable`），unique-sha 降為括號內的取證子欄位且 tail 視窗大小改由工具回報（本檔不再寫死 7）；該軌因此**沒有分母**（分子不是分數）。obs／drift 分子改取 [tools/observability_ga_check.py](../../tools/observability_ga_check.py)／[tools/drift_log_ga_check.py](../../tools/drift_log_ga_check.py) 的 `green_streak`、**分母改取工具回報的 window**（不再寫死 30）。同輪 drift_ga 首次接進 G0 綜合判定成為第四軌。分子/分母的**來源變數**由 `test_run_local_nightly_static.py::test_all_progress_numerators_come_from_authority_gates` 解析 `-f` 綁定逐軌鎖住（不是位置無關的字串比對）。

**R71 機械鎖（A-4；B-5 升級 — 輸出格式 ↔ 本節契約防漂移）**：本節上方 **code fence** 與 ps1 實際輸出由 `test_run_local_nightly_static.py::test_end_progress_format_contract_matches_discipline_doc` 機械比對，全部素材自 ps1 格式字串擷取（em dash 之後那段語意說明不是契約，先切掉）：① **欄位標籤雙向**——ps1 有而 fence 沒有＝漏記，fence 有而 ps1 沒有＝留著已拿掉的欄位當考古紀錄；② **語意標記**——帶連字號／底線的小寫語彙（現為 `should_lock`／`unique-sha`／`rolling-window-days`／`green_streak`），ps1 新增即自動納管，另設下限集合防 ps1 反向把標記拔掉；③ **分母形狀**——無分母／字面常數／取自工具的動態值三態，fence 必須同態（`mutation` 不得帶 `/`、`ac4` 必須逐字帶 `/14`、`obs`／`drift` 必須有分母且不得填死數字）。
🔴 **本鎖只比對 code fence，不比對本節內文**，並以「內文才有的 markdown 連結語法不得出現在抓到的區塊內」當哨兵自我防呆：本節內文為了解釋 R69/R71 訂正，本來就會出現 `green_streak`／`should_lock`／`rolling-window-days` 字樣——拿整節比對會**巧合通過**＝零鑑別力。B-5 正是這樣被抓到的：初版只比對 `x=` 形狀的標籤集合，而 R71 新增的語意不是 `x=` 形狀，於是 fence 還逐字寫著 `mutation=U/7 unique-sha`、`obs=N/30`（**等於把本輪剛修掉的缺陷寫進契約當成規範**，下一個照文件實作的人會把 7 與 30 原封不動抄回去），鎖卻整路是綠的。**刻意仍不鎖排版與逐字措辭**：鎖逐字會讓任何文案微調都翻紅（脆弱耦合，最後一定被人拿掉），漏欄位／錯分母才是真正會誤導判讀的漂移。

### 紀律 #14 — schtasks 自動跑 vs 互動跑必須 PATH 等價 + StrictMode 3.0 嚴格保護 $null.Property

**背景（SD_09 W3 Round 19 nightly 第 14 跑首次自動跑 P0）**：02:00 schtasks 自動跑（SYSTEM 帳號）vs 互動 PowerShell（user 帳號）**PATH 不等價** — pyenv-win 互動 hook 動態注入 `versions/<ver>/Scripts/` 但 schtasks spawn 的 powershell **不繼承** → `Get-Command alembic.exe` 回 `$null`。配合 StrictMode 3.0 開啟（紀律 #11 後續落地），任何 `(Get-Command X -ErrorAction SilentlyContinue).Source` 鏈式存取在 `$null.Source` 時拋 PropertyNotFoundException → 整個 stage 36ms 內 crash（原始取證：logs/nightly_2026-05-26_020001.log:172-174——`logs/` 為 gitignored 且該檔已不復存在（確切原因不明，Windows 側斯時尚無自動輪替機制——R22 DEF-101-200 ARCH-R15-5 修復前，`run_local_nightly.ps1` 對 dated log 從無刪除邏輯，此前任何機器上的消失皆非「保留策略」所致；R22 起已補 14 天輪替，此後同類引用方可稱「依保留期政策輪替」），任何機器上皆不可復驗，僅存本段文字轉述；R10 SA-7/DEF-101-147 註記：已輪替的關鍵取證一律改文字存證，不留死連結）。互動模式因 pyenv hook 注入 Scripts 路徑而 14 輪躲過此 BUG，直到首次 schtasks 自動跑曝光。

**強制條款**：

1. **PATH 補強**：ps1 開頭必須偵測 `$env:USERPROFILE\.pyenv\pyenv-win` 並自動 append `versions/<latest>/Scripts/` 至 `$env:PATH`（idempotent wildcard 比對防重複）；對應 [ps1:56-87](../../tools/run_local_nightly.ps1#L56)。
   - **(1b) 直譯器本身也必須等價，且必須可取證**（DEF-101-506，2026-07-27 真機事故；本條是 #1 的漏網面）：#1 只讓「entry-point exe」等價，**直譯器仍是誰啟動就用誰的**。`$script:PyExe = 'python'` 只存字面 token、每處呼叫由 PATH 現場解析 → 同一支 nightly 在 schtasks 下跑 pyenv `python.bat`、在已啟用 monorepo `.venv` 的終端機／agent 下跑 `.venv\Scripts\python.exe`。兩者**依賴集不同**（`.venv` 未裝 `[postgres,pgvector]` 選配 → `pg-e2e` 假紅）、**shim 語意不同**（`.bat` 會做 batch 百分號展開、真 `.exe` 不會）。實測後果：一次 `.venv` launch 產生 `pg-e2e=1`＋`perf=1` 兩個假紅並寫入 `nightly_latest.log`；更隱蔽的是它讓 DEF-101-503（`%` 被 shim 吃掉）的修復**綠得沒有鑑別力**——真 `.exe` 本來就不觸發該 bug，沒修也會綠。強制兩項：**(a) 自我正規化**——ps1 偵測到 `$env:VIRTUAL_ENV` 即自本行程 PATH 移除該 venv 的 `Scripts`，使解析與 schtasks 一致；移除後若已無其他 python 則**還原並警告**（載具正規化不得讓整晚驗證開天窗，同 Mutex 鎖降級哲學）。**(b) 取證**——log 必須印**解析後的絕對路徑 + 版本 + VIRTUAL_ENV 狀態**；只印字面 token（舊寫法 `：$script:PyExe`，值恆為 `python`）等同沒印，兩種啟動方式的 log 長得一模一樣、事後無法歸因。mac 側不受此害因 `run_local_nightly.sh` 早已把直譯器釘成絕對路徑 `$ROOT/.venv/bin/python`（不靠 PATH 現場解析），但同樣補印解析結果以維持兩平台取證對稱。機械鎖：[tools/tests/test_nightly_interpreter_determinism.py](../../../tools/tests/test_nightly_interpreter_determinism.py)（正規化區塊／降級分支／兩平台取證／mac 釘死不得改回現場解析／反向鎖舊 token 寫法）。**跨平台統一直譯器刻意不做**：mac 釘 `.venv`、Windows 走 pyenv 是各自既有且各自綠的政策，本條要根治的是「同一平台上因啟動方式不同而漂移」。
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

### 紀律 #18 — mutation 必須在隔離樹執行，禁止就地突變活體工作樹

**背景（Improving_012 Phase 1 QA audit P1-7，2026-06-13）**：mutmut 2.4.3 以「就地改寫源碼 → 跑測試 → 還原」方式工作；nightly mutation stage 將 repo volume-mount 進 container（`-v repo:/workspace`）就地突變，導致：(a) 與主機並行 pytest / audit 互踩 —— QA audit 親跑 full pytest 時 2 個 token_guard 測試假紅（斷言出現 `XX/compact\nXX` 突變特徵字串，單跑 PASSED），所有「親跑取證」帶噪；(b) mutmut 中途被 kill 時變異源碼可能殘留磁碟。

**強制條款**：

1. **隔離樹執行**：mutation 載具（`tools/run_mutmut_in_docker.sh`）必須先將源碼複製至 container 內 ephemeral 隔離樹（`/tmp/mutwork`，tar 排除 `.git`/`logs`/`backups`/cache），editable install 與 mutmut 全程在隔離樹執行；**主機工作樹全程零寫入**。
2. **import 路徑一致性**：editable install 必須指向隔離樹（裝 `/workspace` 版會使 pytest import 未突變源碼 → 全 survived 假象）。
3. **取證輸出回寫**：log / backlog / `.mutmut-cache` 仍寫回 `/workspace`，維持 validate_mutmut_log / baseline_lock / mutation_history 取證鏈完全相容。
4. **驗證要求**：本紀律落地後首次 nightly mutation stage 必須確認 kill_rate 與隔離前基線同量級（76% 上下），證隔離未破壞突變-測試耦合。

對應實作：QA audit P1-R62-7 修復（2026-06-13）；`run_mutmut_in_docker.sh` 隔離樹段落。

### 紀律 #19 — 驗證載具 import 路徑一致性：一律從專案 cwd 跑，禁 repo 外路徑 python

**背景（Improving_012 Phase 3 F-A1 開發，流程問題 #9）**：`pip show autoclaude` 之 Editable project location 一度指向遷移前舊路徑 `D:\CursorProject\AutoClaude`（舊副本）。從專案 cwd 跑 `python -m pytest` / `python -c` 時 cwd 會 shadow 至正確源碼故無礙；但 `python <repo 外路徑>.py`（sys.path 不含 cwd）會誤命中舊副本 → 一度 ImportError 誤判新符號不存在。屬環境殘留非源碼缺陷，但違紀律 #17 載具一致性精神。

**強制條款**：

1. **cwd 一致**：所有工作樹驗證一律從專案 cwd（`AutoClaude/`）跑 `python -m pytest` / `python -c`；**禁 `python <repo 外絕對路徑>.py`**（sys.path 不含 cwd，易 shadow 至舊 editable 副本）。
2. **editable 哨兵**：`local_ci_gate`（.sh/.ps1）gate 0 + 可選 CI 步驟以 git rev-parse + pathlib **動態比對** `autoclaude.__file__` 位於當前 repo 根之下，殘留舊副本即 fail（流程改善 #9c，2026-06-13 落地；2026-07-09 跨平台修復輪自寫死 `'AISDCL_Agent'` 字串改為動態比對，repo 更名／搬移不誤判）。
3. **殘留清除**：發現舊 `.pth` 指向遷移前路徑時，`pip install -e .` 重指向本 repo 覆蓋，或移除舊副本。

對應實作：NextAction 流程問題 #9（(a) editable 重指向已於 2026-06-13 執行；(b) 本紀律 SOP +(c) `local_ci_gate.ps1` gate 0 哨兵於本輪落地）。

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

CLAUDE.md §「Nightly / CI 取證紀律」維持 19 條編號標題清單（一行一條）+ 連結至本檔 §2。**任何紀律新增 / 修訂必須先改本檔，再同步 CLAUDE.md 摘要**。

---

**文檔元數據**：v1.13（2026-08-03：紀律 #13 契約 fence 與 ps1 實際輸出對齊 — 條數不變仍 19 條。B-5（SA/SD/QA 三方一致）揪出 R71 收尾漏洞：G-1/G-2/G-3 已把 END 進度三軌語意換掉（mutation 分子→`should_lock` 判定詞、obs/drift 分子→權威 `green_streak` 且分母改取工具回報 window），fence 卻仍逐字寫著 `mutation=U/7 unique-sha`／`obs=N/30`／`drift=N/30`＝**把本輪剛修掉的缺陷寫成規範**；更嚴重的是同輪宣稱在防這件事的機械鎖 `test_end_progress_format_contract_matches_discipline_doc` **當時是綠的**——它只比對 `x=` 形狀的標籤集合，新語意（`green_streak`／`should_lock`）不是 `x=` 形狀故完全逃過。本版：① fence 同步到 ps1 現行格式字串形狀並補符號讀法；② 鎖升級為「標籤雙向＋機械擷取語意標記＋分母形狀三態」且**比對範圍收斂到 code fence**（內文本就含 `green_streak` 字樣，比對整節會巧合通過），另加 markdown 連結哨兵防範圍退化；③ 補 R71 G-1/G-2/G-3 訂正段、將已過時的 `obs=N/30` 段標記為 R71 前狀態）。v1.12（2026-08-03：紀律 #13 三項補記，條數不變仍 19 條——① **格式契約同步**：ps1 自 R69 起實際印的是 `ac4=D/14 rolling-window-days (ready=…; records=…)`，本節卻仍寫舊格式 `ac4=N/14`，兩邊互相矛盾且無任何機械鎖會發現；② **S-1b/S-4 語意訂正**：ac4 分子＝`ac4_progress_check` 滾動 14 日曆天窗（非整檔列數）、obs GA 判準＝`observability_ga_check` 而非 `obs=N/30` 列數、G0 三軌判定改掛 nightly 活載體且不進 exit code；③ **A-2 訂正**：閘門 helper 必須看 `$LASTEXITCODE` 並做 rc↔status 一致性檢查，「量不出來」須以 `TOOL-UNAVAILABLE` 與「未達標」區分——初版 `Get-ObsGaPass` 不看 rc，`rc≠0 + [PASS] 字樣` 即回報達標，會印出假的 `[G0-READY]`。同輪新增機械鎖 `test_end_progress_format_contract_matches_discipline_doc`（欄位標籤自 ps1 機械擷取、雙向比對，刻意不鎖排版）。v1.11（2026-07-27：紀律 #14 增列條款 1b「直譯器本身也必須等價，且必須可取證」—— DEF-101-506 真機事故：`$script:PyExe` 存字面 token 由 PATH 現場解析，已啟用 venv 的 launch 與 schtasks 用到不同直譯器，產生 pg-e2e/perf 假紅並讓 DEF-101-503 的修復綠得沒有鑑別力；落地自我正規化＋絕對路徑取證＋機械鎖 test_nightly_interpreter_determinism.py。條數不變仍 19 條，#14 內部增列 1b）。v1.10（R26 跨平台複審 Scan-D 追溯訂正 — R22（`0053f2a`）曾修訂紀律 #14 對 log 消失原因的誤導措辭〔DEF-101-269 rider〕但當時未同步遞增版本號與最後更新日期，本次補記；條數不變仍 19 條）。v1.9：R16 跨平台複審 — 紀律 #3 mac 註記補充＋header 表 mac 薄聚合器現況更新〔DEF-101-225：`run_local_nightly.sh` 新增 ① BEGIN 行印 `TRIGGER_SRC` 四態歸因觸發來源、② 心跳當日去重前置 POSIX `mkdir` atomic lock 修復 TOCTOU 競態〕；條數不變仍 19 條。v1.8：R15 跨平台複審 — 紀律 #3 補 mac RunId log 註記〔DEF-101-201②：`nightly_mac_<ts>.log` 14 天輪替＋心跳降級為 latest 指標〕、header 表補 mac 薄聚合器對應實作現況〔SCAN-D-4：四 stage＋心跳＋RunId log＋RunAtLoad 當日去重補跑〕；條數不變仍 19 條。v1.7：R10 跨平台複審 — 紀律 #13 補 mutation 軌 unique-sha 語意分軌訂正〔SA-2/DEF-101-142，含 DEF-101-148 壓縮未落盤揭露〕、紀律 #14 死 log 連結改文字存證〔SA-7/DEF-101-147〕、header 表載具 R10 五變更註記。v1.6：R9 計數 16→19 訂正＋行數快照移除＋R9 三變更。v1.5：Improving_012 Phase 3 收尾 — 新增紀律 #19）| 建立 2026-05-26 | 最後更新 2026-08-03 | 維護者：Tech Lead
