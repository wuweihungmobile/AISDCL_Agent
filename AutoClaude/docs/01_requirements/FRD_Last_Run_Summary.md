# FRD_Last_Run_Summary：最近一次執行摘要（`python -m autoclaude --last-run-summary`）

| 項目 | 內容 |
|------|------|
| 功能編號 | F-LRS-001 |
| 版本／日期／狀態 | v1.0／2026-10-10／已實作（2026-10-10） |
| 角色 | SA（系統分析）兼 SD（系統設計） |
| 文件性質 | **單一文件**：需求、驗收準則、設計決策、RTM 骨架、實作順序、事實附錄全在本檔。依掌舵者「省去非必要文件，只留一定需要的」裁示，本功能不另產 SRD／Test Plan／ADR |
| 路徑慣例 | 本檔內相對路徑一律相對於 `AutoClaude/`（子專案根），指令在 `AutoClaude/` 下執行 |
| 閘門對照 | SCG-0 需求＝§1＋§2；SCG-1/2 設計＝§3；SCG-4 實作與規格一致＝§5＋§4 驗證指令；SCG-5 RTM＝§4（每條 AC 至少一支新測試或一道既有機械鎖） |
| 調查基準 | 2026-10-10；macOS Darwin 25.6.0；Python 3.11.15；claude CLI 2.1.296；工作樹基線＝`lint-imports` rc=0（9 kept, 0 broken）、`snapshot_sync.py --check` rc=0、`ruff check autoclaude/main.py` rc=0（以上為量測值，Developer 動工前須自己重跑，不採信本檔） |

> **三個結論（細節與證據見 §3、§6）**
>
> 1. 現況**沒有任何可靠的「上一次執行結果」持久化**。成功與 ESCALATION 兩種結果跑完後，磁碟上只有 `logs/autoclaude.log` 內一行 `KernelResult(...)` 字串；checkpoint 只在 halt 時才寫、成功後也不會被清。所以設計一份**最小落檔** `<log_dir>/last_run_summary.json`（schema v1），由 `main()` 在拿到 `KernelResult` 後原子寫入；新程式碼住 `autoclaude/execution/run_summary.py`，`main.py` 只接線。
> 2. `--last-run-summary` 與既有三種呼叫形態（`<playbook>`、`<playbook> --config`、`<playbook> --fresh`）相容：`playbook` 改 `nargs="?"`，由 `main()` 手動補回修前一字不差的錯誤訊息與 rc=2。
> 3. 另查（§6）：引擎**沒有** per-step／playbook 層的 model 欄位；但 `config.yaml` 的 `claude.extra_args` 與環境變數 `ANTHROPIC_MODEL` 都能**全域**釘住 `claude` 的模型（已實測）。

---

## 1. 功能定義

### 1.1 功能編號與一句話

**F-LRS-001**：新增 CLI 旗標 `--last-run-summary`，以人話印出「最近一次 playbook 執行」的結果：哪個 playbook、何時跑的、成功還是失敗、通過幾步／共幾步、token 峰值（百分比）、有沒有發生 ESCALATION；它是唯讀查詢，不執行任何 playbook。

### 1.2 使用者故事

- **US-LRS-001（操作者）**：身為操作 AutoClaude 的人，我要在 playbook 跑完之後（或隔天回來時）用一行指令看到上一次跑得怎樣，以便不用翻 `autoclaude.log` 就能決定要不要處理。
- **US-LRS-002（上層流程）**：身為驅動 AutoClaude 的上層流程（AISDLC_SDD 端到端鏈的下游步驟），我要有一份機器可讀、帶 schema 版本的結果檔與穩定的退出碼，以便走**檔案契約**取用結果，而不是解析 log 文字。

### 1.3 非目標

| # | 非目標 | 理由／邊界 |
|---|--------|-----------|
| N1 | 不做歷史多筆查詢 | 只留「最近一筆」；不寫 JSONL 歷史、不輪替、不分頁 |
| N2 | 不做 PG 後端專屬查詢 | 紀錄是本機檔案，與 `storage.mode` 無關（`db_only` 也寫本機檔，因為 `log_dir` 一律存在） |
| N3 | 不改引擎執行路徑的語意 | Kernel／AutoResumeService／plugins／EventBus／Port 零改動；`main()` 的 rc 語意（成功 0、其餘 1）不變；寫紀錄失敗不得影響 rc |
| N4 | 不從舊 log 回補紀錄 | 本功能上線前的執行沒有紀錄；`--last-run-summary` 只認新檔（見 §3.2 相容性） |
| N5 | 不記逐步明細 | 不存 `step_log`、各步 token、步驟 id 清單；要逐步細節請翻 `autoclaude.log` |
| N6 | 不處理並行多行程的歷史 | 兩個行程同寫一檔時後寫者勝（寫入原子，不會讀到半份） |
| N7 | 不以 rc 反映「上一次是否成功」 | 查詢 rc 只表示「這次查詢成不成功」；上一次成敗請看輸出或讀 JSON |
| N8 | 不記錄「啟動前失敗」 | Brain 初始化失敗、開機自檢失敗（`main.py:204,209,233` 的提前 `return`）、playbook 格式驗證失敗都不算一次 playbook 執行，不覆寫既有紀錄 |
| N9 | 不提供 `--json` 輸出與清除指令 | 機器請直接讀 `last_run_summary.json`（schema v1 即檔案契約）；要清除就刪檔 |
| N10 | 不修 `KernelResult.escalated_()` 缺 `peak_token_pct` 的缺口 | 屬 core 改動（見 §3.1 發現 F3、§3.7 決策 D-3）；本功能如實顯示「未記錄」 |
| N11 | 只反映 `service.run()` 回傳的**最終**結果 | 同一行程內的自動續跑（halt 後等待再跑）只留最後一輪的 `KernelResult`；此時 `completed_steps` 是最後一輪口徑（見 AC-LRS-012） |

---

## 2. 驗收準則

> 通用規則：stdout 只放摘要；錯誤一律 stderr；錯誤訊息前綴 `錯誤：`。stderr 在非 Windows 平台會多一行 import 期 warning（`wexpect 未安裝…`，`autoclaude/perception/pty_wrapper.py:33`），所以測試對 stderr 一律用**子字串**斷言，不得斷言 stderr 為空。測試 config 的路徑一律 `tmp_path.as_posix()`（Windows YAML 反斜線）。

### 2.1 CLI 形態與相容（A 組）

| AC | 前置／動作 | 期望（可機械驗證） |
|----|-----------|-------------------|
| **AC-LRS-001** | `log_dir` 內有一份有效 finished 紀錄；執行 `python -m autoclaude --last-run-summary --config <cfg>` | rc=0；stdout 第一行逐字 `最近一次執行摘要`；**唯讀**：不執行 playbook、不呼叫 `setup_logger`，執行前後 `log_dir` 與其上層目錄的檔案清單相同（不建立目錄／log／checkpoint） |
| **AC-LRS-002** | `--last-run-summary <playbook.yaml>`（不論該檔存不存在） | rc=2；stderr 含 `--last-run-summary` 與 `不可與`；stdout 為空；不執行 playbook（不產生 `log_dir`） |
| **AC-LRS-003** | `--last-run-summary --fresh` | 同 AC-LRS-002（rc=2、同一訊息） |
| **AC-LRS-004** | (a) 無任何引數；(b) `<不存在的 playbook>`、`<不存在的 playbook> --config <cfg>`、`<不存在的 playbook> --fresh` 三形態；(c) 既有 CLI 測試 | (a) rc=2，stderr 含逐字 `the following arguments are required: playbook`（修前訊息，已實測 `__main__.py: error: …`）；(b) rc=1、輸出含 `找不到`、`--config`／`--fresh` 不觸發 argparse rc=2（行為同修前）；(c) `tests/cli/test_cli_compatibility.py`、`tests/cli/test_cli_compatibility_v2.py` **不修改**且全綠 |
| **AC-LRS-005** | `python -m autoclaude --help` | rc=0；stdout 含 `usage:`、`playbook`、`--config`、`--fresh`、`--last-run-summary` |
| **AC-LRS-006** | 兩份 config 各指向不同 `log_dir`（各放一份不同紀錄）；以 `--config` 分別查詢；另測 `--config` 指向不存在檔 | 各讀各的；config 檔不存在時採預設 `logs`（相對 cwd，`load_config` 回預設值，`autoclaude/utils/config.py:451-454`），且「查無紀錄」訊息印出**實際搜尋的完整路徑** |

### 2.2 輸出內容（B 組）

**輸出版型（逐字；各行以單一 `\n` 分隔，整段尾端由 `print` 補一個 `\n`）**：

```
最近一次執行摘要
Playbook：<playbook 絕對路徑>
開始時間：<YYYY-MM-DD HH:MM:SS+HH:MM>（耗時 <N.N> 秒）
結果：<結果行>
步驟：通過 <completed_steps> / 共 <total_steps> 步<續跑註記>
token 峰值：<token 行>
ESCALATION：<是|否>
可續跑時刻：<時間>            ← 僅 TOKEN_HALT 且 scheduled_resume_at 非空時才有這一行
```

**結果行（逐字）**：

| outcome | `結果：` 後面接 |
|---------|----------------|
| `success` | `成功（SUCCESS）` |
| `escalation` | `失敗（ESCALATION）；原因：<reason>` |
| `token_halt` | `暫停（TOKEN_HALT）；<說明>` ，說明＝reason 對照（`halted`→`context 用量達 halt 門檻，已存檢查點`；`external_resume_required`→`等待時間超過行程內上限，需於可續跑時刻後由外部重啟`；`interrupted_during_wait`→`等待期間被中斷`；其他→原字串）；若 `halt_step_idx` 非空再接 `；停在第 <halt_step_idx+1> 步` |
| `failed` | `失敗（FAILED）；原因：<reason>`；若 `veto_reasons` 非空再接 `；否決原因：<各項以「；」相接>` |

**token 行**：`peak_token_pct > 0` → `<peak:.1f>%`；否則 outcome 為 `escalation`／`failed` → `未記錄（此結果型態不攜帶 token 峰值）`；否則（`success`／`token_halt`）→ `未觀測（本次無 token 訊號）`。

**續跑註記**：僅當 outcome 為 `success` 且 `0 <= completed_steps < total_steps` 時，步驟行尾接 `（本次為續跑：其餘 <total-completed> 步已於先前執行完成）`。

**時間**：`開始時間` 以 `datetime.astimezone(tz).isoformat(sep=" ", timespec="seconds")` 顯示（`tz=None`＝本機時區，已實測形如 `2026-10-10 18:11:07+08:00`）；耗時 `f"{duration:.1f}"`。

| AC | 前置／動作 | 期望 |
|----|-----------|------|
| **AC-LRS-007** | finished、outcome=success、3/3、peak 41.5 | 輸出**逐字等於** §2.6 範例 E1（`format_summary(record, tz=UTC+8)`）；CLI 層 rc=0 |
| **AC-LRS-008** | finished、outcome=escalation、1/3、peak 0.0、reason=`[T02] 輸出未符合期望 regex: 'OK_T02'` | 逐字等於範例 E2；`ESCALATION：是`；token 行為「未記錄…」 |
| **AC-LRS-009** | finished、outcome=token_halt：三種 reason × 有／無 `scheduled_resume_at` × 有／無 `halt_step_idx` | 逐字符合結果行對照表；有 `scheduled_resume_at` 才出現 `可續跑時刻：…` 行；範例 E3（halted）、E4（external_resume_required） |
| **AC-LRS-010** | finished、outcome=failed（vetoed：reason=`vetoed_at_pre_run`、veto_reasons 一項） | 逐字等於範例 E5 |
| **AC-LRS-011** | token 行三態 | `peak>0`→`41.5%`／`95.0%`；`peak<=0` 且 success／token_halt→`未觀測（本次無 token 訊號）`；`peak<=0` 且 escalation／failed→`未記錄（此結果型態不攜帶 token 峰值）` |
| **AC-LRS-012** | success：(2,3)、(3,3)、(0,0)、(5,4)（GOTO 重做使 completed>total） | 只有 (2,3) 的步驟行附續跑註記，其餘三組不附；範例 E6 |
| **AC-LRS-013** | `status=running` 的紀錄 | 輸出逐字等於範例 E7（只有四行：標題、Playbook、開始時間、結果；**不印**步驟／token／ESCALATION 行）；CLI 層 rc=0 |
| **AC-LRS-014** | 同一份紀錄以 UTC 與 UTC+8 兩個 `tz` 格式化 | 偏移逐字出現（`+00:00`／`+08:00`）且時刻換算正確；`tz=None` 時等於 `astimezone()` 的本機表示；耗時顯示一位小數 |

### 2.3 異常狀態（C 組）

| AC | 前置／動作 | 期望 |
|----|-----------|------|
| **AC-LRS-015** | `log_dir` 內無 `last_run_summary.json` | rc=1；stderr 含 `尚無執行紀錄` 與完整搜尋路徑（範例 E8a）；stdout 為空；**不建立任何檔案或目錄** |
| **AC-LRS-016** | 損毀五型：(a) 空檔／非 JSON；(b) 根節點非物件（如 `[]`）；(c) 缺必要欄位（缺 `started_at`）；(d) 欄位型別錯（`total_steps` 為字串；finished 缺 `outcome`）；(e) `schema_version` 不是 1 | 全部 rc=1；stderr 含 `損毀` 與紀錄路徑，並含該型關鍵字（(a)`JSON`／(b)`物件`／(c)`started_at`／(d)`total_steps`／`outcome`／(e)`schema_version`）；stdout 為空；stderr **不含** `Traceback`（範例 E8b） |
| **AC-LRS-017** | `--config` 指向無法解析的 YAML（或 pydantic 驗證失敗） | rc=1；stderr 含 `設定檔`；stderr 不含 `Traceback`（修前的執行路徑是 traceback，本旗標屬新增行為，改為可讀訊息） |
| **AC-LRS-018** | 以 `PYTHONIOENCODING=ascii`、`PYTHONUTF8=0` 啟動子行程（嚴格 ASCII 主控台）查詢有效紀錄 | rc=0（不得 `UnicodeEncodeError`）；stdout 含字面 `\u6700\u8fd1`（即「最近」經 `backslashreplace` 轉義成的 ASCII 字面，不是中文字元）而非崩潰（已實測：未防呆時同環境 rc=1，`UnicodeEncodeError`） |

### 2.4 寫入側（D 組）

| AC | 前置／動作 | 期望 |
|----|-----------|------|
| **AC-LRS-019** | 以 stub 組裝的 `main()` 跑一次成功 run（`KernelResult.success_`） | `<log_dir>/last_run_summary.json` 存在；可用 `json.loads(read_text(encoding="utf-8"))` 解析；欄位齊全（§3.2 全表）且值與 `KernelResult` 一致；`schema_version==1`、`status=="finished"`、`outcome=="success"`；`started_at`／`finished_at` 可由 `datetime.fromisoformat` 解析且**帶 offset**；檔案位元組中**無** `\r`（LF 行尾） |
| **AC-LRS-020** | 四種 `KernelResult` 形態＋兩種 AutoResumeService 衍生形態 → `build_finished_record` | outcome 映射：`success_`→`success`；`escalated_`→`escalation`；`halted_`→`token_halt`；`replace(halted, reason="external_resume_required", scheduled_resume_at=…)`→`token_halt`（保留 `scheduled_resume_at`／`halt_step_idx`）；`vetoed`→`failed`（保留 `veto_reasons`）；判定順序＝success→escalated→halted→failed；`reason` 單行化且 ≤500 字（超過以 `…` 收尾） |
| **AC-LRS-021** | stub service 的 `run()` 被呼叫當下讀檔；另一個 stub 的 `run()` 拋 `RuntimeError` | 呼叫當下檔案已存在且 `status=="running"`、`outcome` 等為 `null`；`run()` 拋例外時**例外照常往外傳**（不被吞），檔案停在 `running`；其後 CLI 查詢輸出符合 AC-LRS-013 |
| **AC-LRS-022** | 同一 `log_dir` 連跑兩次（先失敗、後成功） | 檔案只剩第二次的內容（最新覆蓋舊） |
| **AC-LRS-023** | 寫入失敗兩型：(a) patch `os.replace` 拋 `PermissionError`；(b) patch `os.fsync` 拋 `OSError`（模擬磁碟滿；此時 tmp 檔已建立） | `main()` 的 rc 與沒有此功能時相同（success→0、非 success→1）；log 含 WARNING 且含 `last_run_summary`；無 traceback；不影響 `logger.info("Playbook 結束 \| …")` |
| **AC-LRS-024** | 成功寫入後；以及 AC-LRS-023 的 (a)(b) 兩型失敗後 | `log_dir` 下無殘留 `*.tmp`（成功時 tmp 已換名；失敗時 tmp 被清除） |
| **AC-LRS-025** | `run_boot_self_check` 回非零；另測 playbook 格式驗證失敗（`SystemExit`） | `main()` 回該 rc／拋該 `SystemExit`；`last_run_summary.json` 維持原狀（原本不存在則仍不存在；原本存在則位元組相同）——守住「`start()` 緊貼 `service.run()` 之前」 |
| **AC-LRS-026** | stub service 回 success／escalation／halt 三種結果 | `main()` 回 0／1／1（與既有語意相同），且 `logger.info("Playbook 結束 \| %s", result)` 仍在 |

### 2.5 護欄（E 組：由既有機械鎖與指令承擔，Developer 須實跑證明）

| AC | 內容 | 驗證 |
|----|------|------|
| **AC-LRS-027** | importlinter 全 kept | `PYTHONUTF8=1 lint-imports` rc=0（契約條數以輸出為準；動工前基線 9 kept） |
| **AC-LRS-028** | LOC 無違規 | `python tools/check_loc_budget.py --json` 的 `absolute_violations`、`tier_violations`、`total_violation` 皆空／false |
| **AC-LRS-029** | 既有跨平台掃描全綠（新檔不得新增欠債） | §3.4.4 連鎖鎖表第 1～5 列所列測試全綠；**不得**修改任何棘輪常數或欠債表 |
| **AC-LRS-030** | 風格與快照 | `ruff check` 對改到的三檔 rc=0；`python tools/snapshot_sync.py --check` rc=0 |

### 2.6 逐字範例

以下範例的 `Playbook` 路徑與時間為示意；測試以固定 `tz=timezone(timedelta(hours=8))` 比對。

**E1（AC-LRS-007，成功）**

```
最近一次執行摘要
Playbook：/work/proj/scripts/example_playbook.yaml
開始時間：2026-10-10 18:11:07+08:00（耗時 3.2 秒）
結果：成功（SUCCESS）
步驟：通過 3 / 共 3 步
token 峰值：41.5%
ESCALATION：否
```

**E2（AC-LRS-008，ESCALATION）**

```
最近一次執行摘要
Playbook：/work/proj/scripts/example_playbook.yaml
開始時間：2026-10-10 18:15:01+08:00（耗時 1.0 秒）
結果：失敗（ESCALATION）；原因：[T02] 輸出未符合期望 regex: 'OK_T02'
步驟：通過 1 / 共 3 步
token 峰值：未記錄（此結果型態不攜帶 token 峰值）
ESCALATION：是
```

**E3（AC-LRS-009，TOKEN_HALT；auto_resume 關閉或次數用盡）**

```
最近一次執行摘要
Playbook：/work/proj/scripts/example_playbook.yaml
開始時間：2026-10-10 18:11:08+08:00（耗時 0.8 秒）
結果：暫停（TOKEN_HALT）；context 用量達 halt 門檻，已存檢查點；停在第 2 步
步驟：通過 1 / 共 3 步
token 峰值：95.0%
ESCALATION：否
```

**E4（AC-LRS-009，TOKEN_HALT；拒絕行程內長睡）**

```
最近一次執行摘要
Playbook：/work/proj/scripts/example_playbook.yaml
開始時間：2026-10-10 18:11:08+08:00（耗時 0.8 秒）
結果：暫停（TOKEN_HALT）；等待時間超過行程內上限，需於可續跑時刻後由外部重啟；停在第 2 步
步驟：通過 1 / 共 3 步
token 峰值：95.0%
ESCALATION：否
可續跑時刻：2026-10-10 23:40:00+08:00
```

**E5（AC-LRS-010，FAILED／vetoed）**

```
最近一次執行摘要
Playbook：/work/proj/scripts/example_playbook.yaml
開始時間：2026-10-10 18:20:00+08:00（耗時 0.1 秒）
結果：失敗（FAILED）；原因：vetoed_at_pre_run；否決原因：SDD 規格指紋不符
步驟：通過 0 / 共 3 步
token 峰值：未記錄（此結果型態不攜帶 token 峰值）
ESCALATION：否
```

**E6（AC-LRS-012，續跑後成功）**

```
最近一次執行摘要
Playbook：/work/proj/scripts/example_playbook.yaml
開始時間：2026-10-10 18:28:34+08:00（耗時 0.4 秒）
結果：成功（SUCCESS）
步驟：通過 2 / 共 3 步（本次為續跑：其餘 1 步已於先前執行完成）
token 峰值：未觀測（本次無 token 訊號）
ESCALATION：否
```

**E7（AC-LRS-013，`status=running`；`log_dir` 為 `logs`）**

```
最近一次執行摘要
Playbook：/work/proj/scripts/example_playbook.yaml
開始時間：2026-10-10 18:30:00+08:00
結果：未完成（本次執行未正常結束）；可能仍在執行、被中斷（Ctrl+C／kill），或行程崩潰；詳見 logs/autoclaude.log
```

（E7 內 `詳見` 後的路徑由 `os.path.join(log_dir, "autoclaude.log")` 組出，Windows 會是反斜線；測試以同一式子組期望值。）

**E8a（AC-LRS-015，無紀錄；stderr；rc=1）**

```
錯誤：尚無執行紀錄：找不到 /work/proj/logs/last_run_summary.json（請先執行過一次 playbook；紀錄位置由 --config 的 log_dir 決定）
```

**E8b（AC-LRS-016，損毀；stderr；rc=1）**

```
錯誤：最近一次執行紀錄損毀或無法讀取：/work/proj/logs/last_run_summary.json（JSON 解析失敗：Expecting value: line 1 column 1 (char 0)）。可刪除該檔，下次執行 playbook 會重建。
```

**E8c（AC-LRS-002／003，並用衝突；stderr；rc=2）**——argparse 標準格式，訊息本文固定為：

```
__main__.py: error: --last-run-summary 為唯讀查詢，不可與 playbook 位置參數或 --fresh 並用
```

---

## 3. 設計決策

### 3.1 資料來源（最關鍵的決策）

**調查方法**：逐檔讀碼（下表附 file:line）＋探針實測。探針＝在 scratchpad（不入庫）以 `main()` 於 tmp 目錄、假 executor 跑 3 步 playbook，列出各結果跑完後磁碟上的檔案；全程 `PYTHONDONTWRITEBYTECODE=1`、cwd 在 tmp、`MINIMAX_API_KEY` 未設。

#### 3.1.1 探針實測：跑完後磁碟上留下什麼

| 情境 | main() rc | `log_dir` | `checkpoint_dir` |
|------|-----------|-----------|------------------|
| 成功（首跑，`--fresh`） | 0 | `autoclaude.log` | `.kb_metrics_local.jsonl`、`goal_progress.jsonl`；**沒有 checkpoint** |
| ESCALATION（T02 regex 不符，重試用盡） | 1 | `autoclaude.log` | **空**（連 `escalation_alert.log` 都沒有） |
| TOKEN_HALT（T02 回報 95%） | 1 | `autoclaude.log` | `pb.checkpoint.json`（另有保留版 `.v1`；`step_idx=1`、`peak_token_pct=95.0`） |
| halt 後**非 fresh** 續跑成功 | 0 | 同上 | `pb.checkpoint.json` **仍在**（`step_idx=1` 沒被清）；再跑一次非 fresh 又從 `step_idx=1` 續跑（第二次結果 `completed_step_ids=['T02','T03']`） |
| 缺欄位的 playbook（有 `tasks` 鍵但 task 欠 `name`／`prompt`） | 例外外洩 | `autoclaude.log`（只有「Playbook 模式啟動」，**沒有**「Playbook 結束」） | 空；例外為 `pydantic ValidationError`，從 `service.run()` 內拋出（`auto_resume.py:220` 的 `load_playbook`），`_validate_playbook_format`（`main.py:48-64`）只驗到 `tasks` 鍵 |

#### 3.1.2 候選來源比較

| # | 來源 | 成功 | ESCALATION | TOKEN_HALT | 裁決 | 證據（file:line） |
|---|------|------|-----------|-----------|------|-------------------|
| S1 | checkpoint（`PlaybookCheckpoint`／`FileStateRepository`） | 不寫（殘留舊檔） | 不寫 | 寫（但是「續跑點」不是結果） | **否決** | 寫入只發生在 halt／interrupt／evolution：`plugins/checkpoint/plugin.py:90-100` 的訂閱清單、`core/services/auto_resume.py:433-487`；`clear_checkpoint` 在 production 路徑零呼叫（見 F2）；`file_state_repository.py:306-310` 只是 `unlink`；一個 playbook_id 一檔、不是「全域最近」；`db_only` 無檔 |
| S2 | `KernelResult`（記憶體） | 有 | 有 | 有 | 資料夠，但**不落盤** | `main.py:253-256`：只 `logger.info` 然後回 rc；全 `autoclaude/` 無其他消費端把它寫到磁碟 |
| S3 | `logs/autoclaude.log` ＋ `parse_e2e_log` | 有（repr 字串） | 有 | 有 | **否決** | 見 F6 |
| S4 | 可觀測性（`IObservabilityPort`／`LocalLogger`） | 無 run 級事件 | 無 | 無 | **否決** | 見 F5 |
| S5 | `goal_progress.jsonl`（`GoalProgressPlugin`） | 只有 `progress_pct` | 無 | 無 | **否決** | `plugins/goal_progress_plugin.py:7-9`：POST_RUN 只在正常走完時發布；`kernel.py:112-128` 的 ESCALATE／HALT 提前 return，`:133` 才 emit POST_RUN |
| S6 | `token_usage.jsonl`（`TokenUsageLogger`） | production 無 | 無 | 無 | **否決** | 唯一建構點 `execution/playbook_runner.py:44,121`；`autoclaude/` 內 `PlaybookRunner(` 零建構點（grep 實查） |
| S7 | 其他 plugin：`playbook_persistence`、`goal_synthesis` | — | — | — | **否決** | 前者只寫 `<stem>.mutated.yaml`（突變後的 playbook，與結果無關）；後者只諮詢 Brain、不寫檔（`plugins/goal_synthesis_plugin.py` 全檔無寫檔） |
| S8 | **新增** `<log_dir>/last_run_summary.json` | 是 | 是 | 是 | **採用** | 本節 3.1.4 |

#### 3.1.3 關鍵發現

- **F1 checkpoint 是「下次從哪開始」，不是「上次怎麼了」。** 成功與 ESCALATION 兩種結果都不寫（3.1.1）。把結果塞進 checkpoint 還會改變續跑語意（成功後存一份＝下次非 fresh 直接從終點開始、什麼都不跑），故不可行。
- **F2 `clear_checkpoint` 在 production 路徑零呼叫。** 呼叫者只有 `execution/playbook_runner.py:434` 與 `execution/boot_helper.py:46,55`，而它們都掛在 `PlaybookRunner` 上，該類別在 `autoclaude/` 內沒有建構點（`kernel.py:430-434` 的 R85 註記亦同）。常見認知「checkpoint 會在步驟完成或 `--fresh` 時被清掉」只適用舊 runner 路徑（`AutoClaude/CLAUDE.md` 的正式措辭只有「`--fresh` 忽略 checkpoint 重跑」，與實況相符）；`--fresh` 在 Kernel 路徑只讓 `_resolve_start` 忽略 checkpoint（`auto_resume.py:162-163`），不刪檔。**附帶發現（既有缺口，非本功能範圍，建議主控另案登帳）**：halt 後續跑成功，stale checkpoint 仍在，下次非 fresh 會再從舊斷點重跑（3.1.1 第四列）。
- **F3 ESCALATION 路徑的 `KernelResult` 不帶 token 峰值。** `kernel.py:102,106` 累積了 `run_peak_token_pct`，但 `:112-119` 的 escalate 回傳沒傳它（`:121-128` 的 halt 與 `:142-149` 的 success 有傳）；`core/kernel_state.py:114-128` 的 `escalated_()` 簽名也沒有此參數。探針：T01 觀測到 55%、T02 失敗 ⇒ `KernelResult(… escalated=True … peak_token_pct=0.0)`。因此版型必須有「未記錄」一態，不能把 0.0 印成 `0.0%`。
- **F4 ESCALATION 在磁碟上沒有痕跡。** `config.yaml:96` 寫「ESCALATION 仍永遠寫 checkpoints/escalation_alert.log」，但那個檔由 `utils/notifier.py:51-65` 寫，觸發點是 `ON_ESCALATION`，而 kernel 不派發該 phase（`plugins/sdd_governance_plugin.py:86` 註解「kernel 現況不派發」；`kernel.py` 在這組結果相關 phase 中只 emit ON_FAILURE `:299` 與 POST_RUN `:133`，從不 emit ON_ESCALATION）。探針實測 ESCALATION 跑完 `checkpoint_dir` 為空。
- **F5 可觀測性路徑沒有 run 結束事件。** `kernel.py:46,55` 只存取 `observability`、從不呼叫；`LocalLogger` 只轉 stdlib logging（`infra/adapters/observability/local_logger.py:24`），而 log formatter 只印 `%(message)s`（`utils/logger.py:62-65`），`extra` 結構欄位不進檔；`wiring.py:428-430` 預設注入的就是它。`utils/` 下沒有 `observability*` 模組（只有 `knowledge_base_metrics.py`、`trace_context.py`）。`AutoResumeMetrics`（`core/services/_auto_resume_metrics.py`）只存在行程記憶體。
- **F6 解析引擎 log 不可靠，且 `parse_e2e_log` 不可複用。**（1）`main.py:255` 的 `Playbook 結束 | KernelResult(...)` 是唯一帶結果的行（探針實測 repr 含 `success`／`completed_steps`／`total_steps`／`reason`／`step_log`／`escalated`／`halted`／`halt_step_idx`／`peak_token_pct` 等）；（2）`autoclaude.log` 是 10MB×5 的 `RotatingFileHandler` 追加檔（`logger.py:67-72`），多次執行混在一起，得自己以「Playbook 模式啟動」切段；（3）崩潰時沒有 `KernelResult` 行（3.1.1 最後一列）⇒ 解析會把**上一次**的結果當成這一次；（4）欄位只靠 dataclass repr 的字面，欄位更名即靜默壞；log 時間戳是 naive 本地時間（`logger.py:62-65`）；（5）`setup_logger` 第二次以不同 `log_dir` 呼叫會沿用舊 handler（`logger.py:51-57`），log 不一定落在 `cfg.log_dir`；（6）`parse_e2e_log` 住 `tools/run_bridge_e2e.py:92-134`（regex 錨點 `:58-73`，取「最後一個」KernelResult `:118-120`，只適用「每次一個全新 workdir」的 E2E 場景），而 **`AutoClaude/tools/` 正是 importlinter Rule 9 的 harness**：`.importlinter:19-21` 把 `tools` 加入 root_packages、`:289-295` 禁止 `autoclaude` import `tools`、`:277-279` 的實測註記逐字點名 `AutoClaude/tools/` 下的模組會令契約 broken。該檔還依賴 `click` 與 `three_tier_to_playbook`，並在 `:44-52` 動 `sys.path`。要共用只能把 regex 抽進 `autoclaude/` 再讓 tool 反向 import（方向合法），但那會動 `run_bridge_e2e.py` 與其測試；本設計不走解析 log 這條路，故不需要。
- **F7 兩階段寫入的動機是真的。** 3.1.1 最後一列：格式「看似合法」的壞 playbook 會在 `service.run()` 內崩潰，沒有任何結果物件；只在結束時寫的設計會讓使用者讀到上一次的舊結果（stale-as-fresh）。

#### 3.1.4 選擇與理由

**選 S8：新增 `<log_dir>/last_run_summary.json`，由 `main()` 寫。** 理由：

1. 唯一能同時覆蓋三種結果、又能用「開始標記」辨識崩潰的來源。
2. 零耦合引擎核心：寫入點只在 `main()`（組裝根，單一出口）；若改在 `AutoResumeService.run()` 內寫，要改 4 個 return 站點（`auto_resume.py:239,280,300,304`），且該層是 core 服務、受 core-purity 約束。
3. 檔案契約而非文字解析：schema 版本化，下游走檔案（同 `file_quota_meter` 的 file contract 先例，`.importlinter:270-272`）。
4. 放 `log_dir` 而非 `checkpoint_dir`：`log_dir` 與 `storage.mode` 無關，且 `setup_logger` 保證它存在（`main.py:175`）；`checkpoint_dir` 是續跑狀態、`db_only` 不一定有檔；放前者也不會被 `*.checkpoint.json` 的 glob 掃到（`file_state_repository.py:331`）。`AutoClaude/.gitignore:26` 已忽略 `logs/`，不必改 `.gitignore`。
5. 成本小：一個新模組（預估 ≤260 計價行）＋ `main.py` 約 +20 行。

**新舊兩種都要能讀嗎？只讀新的。** 本功能上線前沒有任何「結果檔」，舊執行無紀錄即回「尚無執行紀錄」（N4）。

### 3.2 紀錄檔設計

**位置**：`<cfg.log_dir>/last_run_summary.json`。`cfg.log_dir` 是相對路徑時隨 cwd 解析（與 `autoclaude.log`、checkpoint 同一慣例；已知限制：換個 cwd 查詢會看到「尚無執行紀錄」，訊息已印出搜尋路徑）。

**schema v1（欄位全表；`running` 與 `finished` 兩種狀態共用同一組鍵，未知值為 `null`）**

| 欄位 | 型別 | `running` | `finished` | 來源 |
|------|------|-----------|------------|------|
| `schema_version` | int | 1 | 1 | 常數 `SCHEMA_VERSION` |
| `status` | str | `"running"` | `"finished"` | recorder |
| `playbook` | str | 絕對路徑 | 同 | `os.path.abspath(args.playbook)`（不解 symlink，與使用者輸入一致） |
| `started_at` | str（ISO 8601，**帶 offset**） | 值 | 值 | `datetime.now(UTC).isoformat(timespec="seconds")`，於 `start()` |
| `finished_at` | str｜null | null | 值 | 同上，於 `finish()` |
| `duration_seconds` | number｜null | null | 值 | `time.monotonic()` 差，`round(…, 1)` |
| `outcome` | str｜null | null | `success`｜`escalation`｜`token_halt`｜`failed` | `outcome_of(result)` |
| `success` | bool｜null | null | 值 | `result.success` |
| `escalated` | bool｜null | null | 值 | `result.escalated` |
| `halted` | bool｜null | null | 值 | `result.halted` |
| `reason` | str｜null | null | 值 | `result.reason`，空白折成單行、≤500 字（超過以 `…` 收尾） |
| `total_steps` | int｜null | null | 值 | `result.total_steps` |
| `completed_steps` | int｜null | null | 值 | `result.completed_steps`（**本次 run 口徑**，`kernel.py:130-132` 註記） |
| `halt_step_idx` | int｜null | null | 值或 null | `result.halt_step_idx`（0-based） |
| `peak_token_pct` | number｜null | null | 值 | `round(result.peak_token_pct, 2)`；單位 0–100（`token_tracker.py:49-78`）；`0.0`＝無訊號或該路徑不攜帶（F3） |
| `scheduled_resume_at` | str｜null | null | 值或 null | `result.scheduled_resume_at` |
| `veto_reasons` | list[str] | `[]` | 值 | `result.veto_reasons` |

`finished` 範例（成功）：

```json
{
  "schema_version": 1,
  "status": "finished",
  "playbook": "/work/proj/scripts/example_playbook.yaml",
  "started_at": "2026-10-10T10:11:07+00:00",
  "finished_at": "2026-10-10T10:11:10+00:00",
  "duration_seconds": 3.2,
  "outcome": "success",
  "success": true,
  "escalated": false,
  "halted": false,
  "reason": "success",
  "total_steps": 3,
  "completed_steps": 3,
  "halt_step_idx": null,
  "peak_token_pct": 41.5,
  "scheduled_resume_at": null,
  "veto_reasons": []
}
```

`running` 範例：同一組鍵，`status` 為 `"running"`，`finished_at`／`duration_seconds`／`outcome`／`success`／`escalated`／`halted`／`reason`／`total_steps`／`completed_steps`／`halt_step_idx`／`peak_token_pct`／`scheduled_resume_at` 皆 `null`，`veto_reasons` 為 `[]`。

**寫入時機（兩階段）**

1. `start()`：`main.py` 在建好 `AutoResumeService`（`:249-252`）之後、`result = service.run(...)`（`:253`）**之前**寫 `running`。緊貼 `service.run` 是刻意的：`:204,209,233` 的提前 `return`（啟動前失敗）因此不會碰紀錄（N8、AC-LRS-025）。
2. `finish(result)`：緊接 `logger.info("Playbook 結束 | %s", result)`（`:255`）之後、`return` 之前，用同一個檔名**原子覆寫**成 `finished`。
3. 崩潰／Ctrl+C／kill／斷電：`finish` 沒機會執行，檔案停在 `running`，查詢時顯示「未完成（本次執行未正常結束）」（範例 E7）。不另外捕捉例外（只能涵蓋 Python 例外；開始標記是超集合，涵蓋 kill -9 與斷電）。**不用 PID 存活探測**（Windows／POSIX 語意不同，鐵律三），所以 `running` 只說「未正常結束」，不判斷是否仍活著。

**讀取與驗證（`summary_problems`，純函式，回傳問題字串清單；空清單＝有效）**

- 所有狀態必備：`schema_version` 為 int（非 bool）且**等於 1**；`status` ∈ {`running`,`finished`}；`playbook` 非空 str；`started_at` 為可 `fromisoformat` 解析且**帶 offset**的 str。
- `finished` 另必備：`finished_at`（同上格式）；`duration_seconds` 為非負數；`outcome` ∈ 四值；`success`／`escalated`／`halted` 為 bool；`total_steps`／`completed_steps` 為非負 int（非 bool）；`peak_token_pct` 為非負數；`reason` 為 str｜null；`halt_step_idx` 為 int｜null；`scheduled_resume_at` 為 str｜null；`veto_reasons` 為 list[str]。
- 多餘的未知鍵一律忽略（向前相容）。問題字串格式：`JSON 解析失敗：<例外>`、`根節點必須是物件（實際為 <型別>）`、`缺少必要欄位：<名稱>`、`欄位型別錯誤：<名稱> 需為 <型別>`、`schema_version=<值> 不受支援（本版只認 1）`；多個問題以 `；` 相接。
- **演進規則**：新增選配欄位不升版；改名／刪除／語意變更才升 `schema_version`，舊讀者會以 `schema_version=… 不受支援` 明確拒絕，而不是靜默誤讀。

### 3.3 CLI 解析設計

`main()` 的 parser（`main.py:161-170`）只做三處修改，其餘 `--config`／`--fresh` 一字不動：

| 修改 | 內容 |
|------|------|
| `playbook` | 加 `nargs="?"`、`default=None`；`help` 字串不變 |
| 新旗標 | `--last-run-summary`，`action="store_true"`、`default=False`，`help` 說明「唯讀；不可與 playbook／--fresh 並用」 |
| 分派 | `parse_args()` 之後、`_validate_playbook_format` 之前（`:170` 與 `:172` 之間）插入下列兩段 |

分派語意（偽碼，僅表達順序與逐字訊息）：

```
if args.last_run_summary:
    if args.playbook is not None or args.fresh:
        parser.error("--last-run-summary 為唯讀查詢，不可與 playbook 位置參數或 --fresh 並用")   # rc=2
    return show_last_run_summary(args.config)
if args.playbook is None:
    parser.error("the following arguments are required: playbook")                          # rc=2，與修前逐字相同
# 以下與修前相同：_validate_playbook_format(args.playbook) → load_config → …
```

形態總表：

| 呼叫形態 | 行為 | rc |
|----------|------|----|
| `<playbook>`、`<playbook> --config c`、`<playbook> --fresh`（既有三形態） | 執行，與修前相同 | 0／1 |
| `--last-run-summary [--config c]` | 查詢（唯讀） | 0（有紀錄，含 `running`）／1（無紀錄、損毀、設定檔讀不了） |
| `--last-run-summary <playbook>` | 拒絕 | 2 |
| `--last-run-summary --fresh` | 拒絕 | 2 |
| 無任何引數 | 拒絕（訊息逐字沿用） | 2 |

console script `autoclaude`（`pyproject.toml:153`，`autoclaude.main:main`）走同一個 `main()`，`autoclaude --last-run-summary` 行為相同。

**為何手動 `parser.error` 而不用 `add_mutually_exclusive_group`**：互斥群組的錯誤訊息是 `argument …: not allowed with argument …`，且「兩者皆無」要另加 `required=True`，其訊息會與修前的 `the following arguments are required: playbook` 不同——而既有行為要求逐字不變；另外 `--fresh` 也要一併拒絕，手動規則才寫得出來。**為何拒絕而非忽略**：靜默忽略 playbook 會把「想跑」讀成「只是看」（fail-loud 原則）；查詢指令絕不能因並用而啟動真實 claude 呼叫。

**既有測試怎麼釘住 CLI**：`tests/cli/test_cli_compatibility.py:75-80` 的 `_build_parser()` 是 parser 的**手抄複本**（in-process 測試對 `main()` 真 parser 的改動結構上不敏感）；真正釘住 `main()` 行為的是 subprocess 測試（S1 `--help` `:98-105`、S7 無引數 rc=2 `:233-236`、S2～S6 的 rc 斷言、`:268-273` 的 `main()` 簽名；v2 檔 K1～K5）。所以 AC-LRS-004／005 一律用 subprocess 重釘。

### 3.4 模組放置、importlinter、LOC、既有測試

#### 3.4.1 新模組與公開介面（名稱為契約，內部可自由實作）

**`autoclaude/execution/run_summary.py`**（`from __future__ import annotations`；`KernelResult` 只在 `TYPE_CHECKING` 下 import）：

| 名稱 | 種類 | 職責 |
|------|------|------|
| `SCHEMA_VERSION = 1`、`SUMMARY_FILENAME = "last_run_summary.json"`、`REASON_MAX_CHARS = 500` | 常數 | |
| `RunSummaryMissingError`、`RunSummaryCorruptError` | 例外 | 檔案不存在／其餘一切讀不了或不合格（損毀、無法讀取、schema 不符） |
| `summary_path(log_dir) -> Path` | 純函式 | `Path(log_dir) / SUMMARY_FILENAME` |
| `outcome_of(result) -> str` | 純函式 | 判定順序 success→escalated→halted→failed |
| `build_started_record(playbook, started_at) -> dict`／`build_finished_record(started, result, finished_at, duration_seconds) -> dict` | 純函式 | 組 §3.2 全表的 dict |
| `summary_problems(data) -> list[str]` | 純函式 | §3.2 驗證 |
| `load_summary(path) -> dict` | I/O | `read_text(encoding="utf-8")`＋`json.loads`＋`summary_problems`；不存在→`RunSummaryMissingError`，其餘→`RunSummaryCorruptError` |
| `format_summary(record, *, tz=None, log_dir="logs") -> str` | 純函式 | §2.2 版型；`tz` 供測試固定時區 |
| `show_last_run_summary(config_path) -> int` | CLI 入口 | `load_config`（失敗→stderr `錯誤：設定檔讀取失敗：…`、rc=1）→`load_summary`→印出；`_escape_unencodable(sys.stdout)`（helper 內 `stream.reconfigure(errors="backslashreplace")`，`try/except (AttributeError, OSError, ValueError)`，非 TextIOWrapper 時略過；receiver 不得寫成字面 `sys.stdout.`，見 §3.4.4 第 11 列）；**不呼叫 `setup_logger`、不建目錄** |
| `RunSummaryRecorder(log_dir, playbook, *, now=None, monotonic=None)` | 類別 | 建構子**不做 I/O**；`start() -> bool`、`finish(result) -> bool`；兩者 best-effort、永不拋（內部 `except Exception`，WARNING 訊息含 `last_run_summary`，且說明「`--last-run-summary` 將顯示過期或缺少的紀錄」）；`now`／`monotonic` 為可注入時鐘（預設 `datetime.now(UTC)`／`time.monotonic`） |

**`main.py` 的變更面**（約 +20 計價行）：import 一行（`from .execution.run_summary import RunSummaryRecorder, show_last_run_summary`，放在 `.execution.boot_self_check` 之後以符合 isort）、parser／分派（§3.3）、recorder 三行（建構＋`start()` 在 `service.run` 前；`finish(result)` 在 `logger.info` 後）、模組 docstring（`:4-8`）加一行 `python -m autoclaude --last-run-summary [--config config.yaml]`。**不改**：`autoclaude/core/**`、`AutoClaude/CLAUDE.md`（已 400 行滿，改它會被 hook exit 2 擋）、任何既有測試。`AutoClaude/README.md` 加一行用法為選配、非驗收項。

**為何放 `execution/` 而非 `utils/`／新 Port**：`execution/boot_self_check.py` 就是「只由 `main.py` 消費的行程入口級模組」的先例（`main.py:28-35`）；`execution → core`／`utils` 的 import 方向合法（`execution/types.py:35` 先例）。**為何不做 Port＋Adapter＋Plugin**：`main.py` 本身就是 Hexagonal 的組裝根（已直接 import infra，`main.py:36-41`）；Port 會動 `core/ports/`（Port 清單進 `CLAUDE.md` Snapshot，須重生）與 `wiring.py`（contract tier ≤400）；Plugin 看不到 ESCALATE／HALT（它們提前 return，`kernel.py:112-128`，POST_RUN 只在 `:133` 成功路徑才發）。為單一 CLI 便利功能付這些成本不值得。

#### 3.4.2 importlinter 逐條影響（`.importlinter`）

| # | 契約 | 影響 |
|---|------|------|
| 1 | plugin-isolation | 無（不碰 plugins） |
| 2 | core-purity（`:59-75`） | 無：source_modules 為 `core.kernel／kernel_state／event_bus／hookspec／ports／services`，新模組在 `execution/`，且**不被 core 引用**（只有 `main.py` 引用）；新模組也**不 import infra** |
| 3 | runner-internals-isolation | 無 |
| 4／5 | brain／executor isolation | 無 |
| 6 | runner-no-checkpoint-logic | 無：不 import checkpoint 內部模組 |
| 7 | plugin-no-utils-observability | 無（新模組不在 plugins） |
| 8 | no-direct-kb-metric-store | 無 |
| 9 | no-harness-import | **關鍵**：不得 import `tools.*`（含 `AutoClaude/tools/run_bridge_e2e.py`）；不得以 `sys.path` 洗白。另有語法判準 `tests/test_r82_quota_axis_and_shipped_defaults.py:896` 起的 `TestNoHarnessImport`（含 `test_no_module_under_autoclaude_imports_the_harness`）逐檔掃 `autoclaude/**` |

新模組只依賴：標準庫（`json`、`os`、`uuid`、`time`、`logging`、`datetime`、`pathlib`、`collections.abc`）＋ `autoclaude.utils.config.load_config`（`show_last_run_summary` 用）。

#### 3.4.3 LOC 分級（動工前量測值；`python tools/check_loc_budget.py --json` 與 `classify_file`／`count_loc` 實查）

| 檔 | tier／預算 | 現況計價行 | 預估 | 判定 |
|----|-----------|-----------|------|------|
| `autoclaude/main.py` | unclassified → 絕對紅線 750（`check_loc_budget.py:122,434-444`） | 153 | ≈ 175（動工前預估；實測 170） | 餘裕約 575，無風險 |
| `autoclaude/execution/run_summary.py`（新） | unclassified → 750（該目錄僅 `goal_decomposer.py`、`types.py`、`steps_orchestrator/`、`playbook_runner.py` 有專屬 tier，`:73-120`） | — | ≤ 260（動工前預估；實測 300） | 計價只算**斷言行**（docstring／註解免費，`check_loc_budget.py:316-340`）；若實作逼近 400 請**停下回報主控**（視為設計過度，應砍欄位而非拆檔） |
| 總量 | total ≤ cap | total=17434、cap=20438、baseline=17079（`--json` 實測） | +≈280（動工前預估；實測 +339：17434→17773，其中本功能自身 main.py +17、run_summary.py +300；其餘 +22 非本功能所有，未逐行核對） | 遠低於 cap；**不需** `--update`／`--repin-cap` |

#### 3.4.4 連鎖鎖（既有機械鎖；新檔必須服從，不得改常數或欠債表）

| # | 鎖 | 何時紅 | Developer 要做的事 |
|---|----|--------|-------------------|
| 1 | `tests/infra/adapters/test_rtm_file_sink_newline.py::test_no_new_text_write_sites_without_explicit_newline`（AST 掃整個 `autoclaude/`） | 新檔任一文字模式寫入（`open("w")`／`Path.open("w")`／`write_text`）缺 `newline=` | 一律 `encoding="utf-8", newline="\n"`；**不得**把新檔加進 shrink-only 的 `_KNOWN_MISSING_NEWLINE`（`:30-45`） |
| 2 | 根層 `tools/tests/test_platform_neutral_paths.py::TestDirEntryPrimitivesAreAccountedFor::test_unguarded_site_census_matches_the_ledger`（雙向精確比對 `_DIRENT_UNGUARDED_DEBT = {"live": 37}`，`:3697`） | `os.replace`／`Path.replace`／`rename` 站點**未被** `try/except OSError`（或 `PermissionError`） 包住 ⇒ 多 1 筆即紅 | 把 `os.replace` 包在 `try … except OSError`（本設計「寫檔失敗不得影響 rc」本來就要求）；已用該檔的 `dirent_primitive_sites()`、`scan_naive_timestamp_persist()`、`scan_missing_encoding()` 對設計寫法的合成片段做紅綠驗證：有包 `try/except OSError`＝handled、沒包＝未處置；`datetime.now(UTC)` 零命中而 `datetime.now()` 命中 1 筆；有 `encoding=` 零命中、缺漏命中 1 筆 |
| 3 | 同檔 `TestNaiveLocalTimestampsAreNotPersisted`（`:4994` 起） | 持久化 naive 本地時間戳 | 一律 `datetime.now(UTC)`（`from datetime import UTC`；先例 `utils/goal_progress.py:17,45`）；ruff `UP017` 也不准 `timezone.utc`（已實測會報） |
| 4 | 同檔 `TestTextIoDeclaresEncoding`（`:2135` 起，shrink-only 棘輪） | 文字讀寫未指名 `encoding` | 全部 `encoding="utf-8"`（**含測試檔**） |
| 5 | `tests/test_r82_quota_axis_and_shipped_defaults.py::TestNoHarnessImport` | import `tools.*` | 不 import |
| 6 | `tests/conftest.py` 的 `_PG_SOURCE_INDICATORS` | 測試原始碼含 `docker`、`alembic`、`psycopg`、`Pg[A-Z]…` 等字樣 | 避免；否則整檔被歸入 `pg_serial` 序列群組（只影響平行度，不紅） |
| 7 | ONBOARDING §7 表①（live）LOC `total` | 新增計價行使 total 變動 ⇒ 根層 unittest 閘門紅並印應填值 | **收尾**：`python tools/sync_onboarding_baselines.py --write`（repo 根）→ `--check`；寫入 `ONBOARDING.md` 屬機械回填 |
| 8 | ONBOARDING §7 表②（dated；指紋涵蓋 `AutoClaude/tests/` 的 `*.py`） | 新增測試檔改變指紋 ⇒ pre-push 的 `--check-snapshot` 判本機欄 presumed stale 而紅 | **收尾（主控／單人窗口）**：commit 前最後一步 `python tools/sync_onboarding_baselines.py --write --with-slow`（須乾淨 venv、分鐘級）；Developer 不做 |
| 9 | `tools/check_pytest_baseline_sites.py`（掃全 repo tracked `.md`／`.py`） | 同一行同時含 `passed`／`skipped` 字樣與 4 位數以上數字（或 `NNN/NN` 配測試脈絡字） | 本 FRD 與新程式碼的註解／docstring **不得**寫此類行 |
| 10 | `AutoClaude/CLAUDE.md` 的 400 行硬上限（hook：超過即 exit 2） | 任何新增行 | 不改它；CLI 說明只改 `main.py` docstring 與 `--help` |
| 11 | 根層 `tools/tests/test_platform_utils_dedup.py::TestR74InlineCopyRatchetForStdioSsot`（純文字窄判準 `(sys.)?std(out\|err).reconfigure(`；shrink-only 凍結表 `_FROZEN_INLINE_STDIO_SITES`，雙向精確）。同檔寬判準 `TestR75StdioUtf8HasOneImplementation` 只認 `reconfigure(encoding…` 與 `TextIOWrapper(sys.std*.buffer`，本功能不碰 | 新檔（含註解與測試內嵌字串）出現字面 `sys.stdout.reconfigure(`／`stderr.reconfigure(`，**不論引數為何**；初版實作的 `sys.stdout.reconfigure(errors="backslashreplace")` 即實測紅（「行內 stdio-UTF-8 複本 1 處 > 凍結值 0 處」；本表初稿漏列此鎖） | 把 `reconfigure` 收進接收串流參數的 helper（`_escape_unencodable(stream)`，receiver 不是 `sys.stdout`／`sys.stderr` 字面）；**不得**改凍結表；harness 的 SSOT `tools/_stdio_utf8.py` 因 Rule 9 不可 import，且語意不同（強制 UTF-8 vs 只改 errors） |

#### 3.4.5 既有測試受影響面（讀碼盤點）

| 測試 | 如何碰到 `main()` | 新功能後的行為 |
|------|-------------------|----------------|
| `tests/cli/test_cli_compatibility.py`、`_v2.py` | subprocess `python -m autoclaude …` | 不修改、須全綠（AC-LRS-004） |
| `tests/integration/test_def_200_205_production_wiring.py:311-333`（`_run_main`，`_FakeService` 回 `KernelResult(success=True, completed_steps=0, total_steps=0, reason="fake")`） | in-process `main()`，log_dir 在 tmp | recorder 會寫 tmp 的 `logs/last_run_summary.json`；不影響斷言（以 `listdir`／`iterdir`／`glob` 對 `log_dir` 做 grep，只命中與本功能無關的 nightly 日誌 glob，零個測試逐檔斷言 `log_dir` 內容） |
| `tests/execution/test_r85_subtraction_locks.py:158-195`（`_run_example_playbook`，真 Kernel＋DryRun 風格替身） | 同上 | 同上；Windows 的 log handler 釋放慣例（`_release_autoclaude_log_handles`）沿用 |
| `tests/test_main_build_executor.py` | 只 import `build_executor` | 不受影響 |
| `tests/test_r100_boot_self_check.py` | `main.run_boot_self_check` 的接線鎖 | 不受影響（本功能不動該函式） |

### 3.5 錯誤處理與跨平台

- **寫入 best-effort**：`start()`／`finish()` 內部 `try/except Exception`（本功能是附屬便利，任何失敗——含 `result` 缺欄位的測試替身——都不得影響 rc 與引擎流程）；失敗即 WARNING（`logger.warning`，訊息含 `last_run_summary` 與後果）並回 `False`；成功只記 DEBUG，不增加 console 噪音。
- **原子寫入**：沿用 checkpoint 的寫法（`file_state_repository.py:195-212`）去掉保留版本與重試：tmp 檔名 `<name>.<pid>.<uuid4 hex>.tmp`（避免併發共用同一 tmp，該檔 `:188-195` 註記的缺陷）→ `tmp.open("w", encoding="utf-8", newline="\n")` 寫入 → `flush()`＋`os.fsync()` → `os.replace(tmp, path)`；整段在 `try … except OSError`，失敗時 `tmp.unlink(missing_ok=True)`（包 `suppress(OSError)`）後回 False。**刻意不重用**：`utils/logger.py:181-199` 的 `write_text_with_fallback`（固定 `.tmp` 檔名會讓兩個並行行程互踩；失敗時改寫到系統暫存目錄，會讓讀者找不到檔）與 `file_state_repository._replace_waiting_out_readers`（私有函式、住 infra adapter 層，且 Windows 讀者重試對「下次執行就會覆寫」的便利檔不值得）。寫入前 `path.parent.mkdir(parents=True, exist_ok=True)`。
- **讀取**：`Path.read_text(encoding="utf-8")` 一次讀完即關（縮短 Windows 上與寫端 `os.replace` 的握把重疊窗口）；`FileNotFoundError`→`RunSummaryMissingError`，其餘 `OSError`、`UnicodeDecodeError`、`json.JSONDecodeError`、驗證問題一律→`RunSummaryCorruptError`；**絕不 traceback**。
- **編碼與換行**：JSON 用 `json.dumps(record, ensure_ascii=False, indent=2) + "\n"`；檔案 UTF-8、LF（`newline="\n"`，Windows 不被翻成 CRLF）；stdout 以 `reconfigure(errors="backslashreplace")` 防呆（Windows 重導向時預設 code page 可能無法編碼中文；已實測嚴格 ASCII 下未防呆 rc=1、防呆後 rc=0）。輸出用全形標點與 ASCII，不使用破折號與 emoji（cp950 無法表示）。
- **時間戳**：持久化一律 aware UTC；只在顯示時換算成本機時區（鐵律三「naive 本地時間戳」）；顯示偏移以 `isoformat` 產生，不依賴 `%z`／`%:z` 的平台差異。
- **路徑**：全程 `pathlib`；`playbook` 欄存 `os.path.abspath`；不做路徑分隔符字面比對；tmp 檔與目的檔同目錄（`os.replace` 不跨檔案系統）。
- **Windows 檔案鎖**：不加重試；讀端握把極短，寫端失敗只 WARNING，下一次執行即覆寫。
- **隱私**：紀錄含絕對路徑與 reason 文字；落在 gitignored 的 `log_dir`，不入庫；repo 為 public，貼進證據檔前須先檢視。
- **唯讀查詢零副作用**：不呼叫 `setup_logger`（它會建目錄與 log handler）、不建任何目錄／檔案；`load_config` 對不存在的檔回預設值（`config.py:451-454`）。

### 3.6 考慮過並否決的方案

| 方案 | 否決理由 |
|------|----------|
| 擴充 checkpoint 存結果 | 改變續跑語意（F1）；成功後根本不寫 checkpoint |
| 解析 `autoclaude.log`／複用 `parse_e2e_log` | F6 六點；Rule 9 禁止 import harness；崩潰時讀到舊結果 |
| 新 Plugin 訂閱 POST_RUN | 只在成功路徑發布（`kernel.py:133`），ESCALATE／HALT 看不到；新增 phase 要動 core `hookspec`（contract tier） |
| 新 Port＋Adapter（如 `IRunSummarySink`） | 動 `core/ports/` 與 Snapshot、`wiring.py`；`main.py` 即組裝根，直接組裝符合 Hexagonal |
| 在 `AutoResumeService.run()` 內寫 | 4 個 return 站點（`auto_resume.py:239,280,300,304`）、core-purity 約束、service tier 預算（現況 295／500） |
| 只在結束時寫一次 | 崩潰時讀到舊結果（F7）；兩階段僅多一次小寫入與一個 `running` 狀態（決策 D-2） |
| 追加式歷史 `run_history.jsonl` | 超出需求（N1）；需輪替；與「最近一筆」查詢語意不同 |
| 改 `KernelResult.escalated_` 帶 peak | core 改動＋equivalence 風險（N3、N10；決策 D-3） |
| 互斥群組／子命令（`autoclaude summary`） | 會改變既有錯誤訊息或位置參數語意（§3.3） |
| 並用時忽略 playbook 或照常執行 playbook | 違反 fail-loud；後者會誤啟動真實 claude 呼叫 |

### 3.7 決策紀錄（[確認]＝建議主控確認；皆可低成本反轉）

| # | 決策 | 預設選擇 | 反轉成本 |
|---|------|----------|----------|
| D-1 [確認] | 查詢 rc 約定 | 有紀錄（含 `running`）→0；無紀錄／損毀／設定檔讀不了→1；並用衝突／無引數→2；**不以 rc 反映上一次成敗**（N7） | 改「無紀錄→0」＝改一行（AC-LRS-015） |
| D-2 [確認] | 兩階段寫入（`running` 開始標記） | 採用，動機＝F7 實測的崩潰案例 | 若要最小形態：刪 `start()`、`status`／`running` 分支、AC-LRS-013／021 |
| D-3 [確認] | ESCALATION 的 token 峰值 | 如實顯示「未記錄」，不動 core | 若要真值：`kernel.py:113-119` 傳 `peak_token_pct=run_peak_token_pct`＋`kernel_state.py:114-128` 的 `escalated_()` 加參數（約 3 行）；須跑 `tests/equivalence` 與 core 測試，並改 AC-LRS-008／011 |
| D-4 | 檔名與位置 | `<log_dir>/last_run_summary.json` | 低 |
| D-5 | 並用衝突的處理 | 拒絕（rc=2），含 `--fresh` | 低 |
| D-6 | 「跑了幾步、過了幾步」的詮釋 | 「過了幾步」＝`completed_steps`（本次口徑）、「跑了幾步」＝`total_steps`（playbook 總步數），合成 `通過 M / 共 N 步`；不推算「實際嘗試步數」（KernelResult 沒有此量） | 低；續跑時以註記補足語意（AC-LRS-012） |
| D-7 | 時間顯示 | 本機時區＋offset，持久化為 UTC | 低 |
| D-8 | 模組放置 | `execution/run_summary.py`，單檔 | 若實作逼近 400 計價行再議 |

---

## 4. RTM 骨架與驗證指令

測試檔（**只有這一支新測試檔**）：`AutoClaude/tests/cli/test_last_run_summary.py`（`tests/cli/__init__.py` 已存在）。

### 4.1 測試組裝配方（照既有先例，不重造）

| 輔助 | 作法 | 先例 |
|------|------|------|
| `_run_cli(*args, env_extra=None, timeout=60)` | `subprocess.run([sys.executable, "-m", "autoclaude", *args], capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=PROJECT_ROOT, env=…)`；env 取 `os.environ` 副本、`setdefault("PYTHONIOENCODING","utf-8")`／`("PYTHONUTF8","1")`、`pop("MINIMAX_API_KEY")`；`env_extra` 後蓋（AC-LRS-018 用 `PYTHONIOENCODING=ascii`＋`PYTHONUTF8=0`）；timeout 取 60（匯入期較慢） | `tests/cli/test_cli_compatibility.py:49-69` |
| `_write_cfg(tmp_path)` | 寫 `log_dir: <as_posix>/logs\ncheckpoint_dir: <as_posix>/ckpt\n`，一律 `write_text(..., encoding="utf-8", newline="\n")`；回 `(cfg_path, log_dir)` | `tests/integration/test_def_200_205_production_wiring.py:316` |
| `_finished_record(**over)`／`_running_record()` | 以 `build_started_record`／`build_finished_record` 組出合法 dict 再覆寫欄位；損毀案例直接寫字串／錯型別 | — |
| `_run_main(tmp_path, service_cls, …)` | in-process `main()`：`patch.object(main_mod, "build_executor", lambda *a, **k: _NoopExecutor())`、`patch.object(main_mod, "AutoResumeService", service_cls)`、`patch.object(main_mod, "run_boot_self_check", lambda *a, **k: 0)`（hermetic：不 spawn 真 `claude --version`、不碰 cwd 的 git）、`patch.object(sys, "argv", […])`、`monkeypatch.delenv("MINIMAX_API_KEY", raising=False)`、`os.chdir(tmp_path)`；`finally` 呼叫本檔**唯一一份**的 `_release_autoclaude_log_handles()`（關閉並卸下 `autoclaude` logger 的 handler，避免 Windows 清 tmp 時 WinError 32）。stub service 的 `run(self, path, fresh=False)` 回 `KernelResult.success_/escalated_/halted_/vetoed(...)` 或拋例外 | `tests/integration/test_def_200_205_production_wiring.py:294-333`；`tests/execution/test_r85_subtraction_locks.py:158-195`（log handle 釋放的 Windows 理由見該檔 `:28-60` 註解） |

測試撰寫注意：stderr 只做子字串斷言（見 §2 通用規則）；不得在 `tests/` 內重寫第二份 handler 釋放迴圈；測試原始碼避免 PG 指標字樣（§3.4.4 第 6 列）；測試檔文字讀寫一律 `encoding="utf-8"`；E501 以顯示寬度計（中文字寬 2），單行 ≤100 欄。

### 4.2 RTM（AC → 驗證）

| AC | 驗證層 | 測試（`tests/cli/test_last_run_summary.py::…`；E 組為既有鎖／指令） |
|----|--------|------------------------------------------------------------------|
| AC-LRS-001 | subprocess | `test_ac_lrs_001_flag_alone_prints_summary_rc0_and_creates_nothing` |
| AC-LRS-002 | subprocess | `test_ac_lrs_002_flag_with_playbook_is_rejected_rc2` |
| AC-LRS-003 | subprocess | `test_ac_lrs_003_flag_with_fresh_is_rejected_rc2` |
| AC-LRS-004 | subprocess＋既有 | `test_ac_lrs_004a_no_args_keeps_the_original_message_rc2`、`test_ac_lrs_004b_playbook_forms_still_reach_validation`（3 組參數）；(c) 既有 `tests/cli/test_cli_compatibility.py`、`test_cli_compatibility_v2.py` 全綠 |
| AC-LRS-005 | subprocess | `test_ac_lrs_005_help_lists_new_flag_and_keeps_old_ones` |
| AC-LRS-006 | subprocess | `test_ac_lrs_006_location_follows_config_log_dir` |
| AC-LRS-007 | 純函式 | `test_ac_lrs_007_success_summary_verbatim` |
| AC-LRS-008 | 純函式 | `test_ac_lrs_008_escalation_summary_verbatim` |
| AC-LRS-009 | 純函式（參數化） | `test_ac_lrs_009_token_halt_variants` |
| AC-LRS-010 | 純函式 | `test_ac_lrs_010_failed_vetoed_summary_verbatim` |
| AC-LRS-011 | 純函式（參數化） | `test_ac_lrs_011_token_peak_three_states` |
| AC-LRS-012 | 純函式（參數化） | `test_ac_lrs_012_resume_note_only_for_partial_success` |
| AC-LRS-013 | 純函式＋subprocess | `test_ac_lrs_013_running_record_verbatim`、`test_ac_lrs_013_cli_prints_running_record_rc0` |
| AC-LRS-014 | 純函式 | `test_ac_lrs_014_times_render_in_requested_timezone` |
| AC-LRS-015 | subprocess | `test_ac_lrs_015_no_record_rc1_names_path_and_creates_nothing` |
| AC-LRS-016 | subprocess（5 組參數） | `test_ac_lrs_016_corrupt_record_rc1_without_traceback` |
| AC-LRS-017 | subprocess | `test_ac_lrs_017_unreadable_config_rc1_without_traceback` |
| AC-LRS-018 | subprocess | `test_ac_lrs_018_stdout_survives_strict_ascii_console` |
| AC-LRS-019 | in-process `main()` | `test_ac_lrs_019_successful_run_leaves_a_valid_v1_record` |
| AC-LRS-020 | 純函式（參數化） | `test_ac_lrs_020_outcome_mapping_for_every_kernel_result_shape` |
| AC-LRS-021 | in-process `main()` | `test_ac_lrs_021_start_marker_precedes_the_result`、`test_ac_lrs_021_crash_leaves_running_and_propagates` |
| AC-LRS-022 | in-process `main()` | `test_ac_lrs_022_second_run_overwrites_the_first` |
| AC-LRS-023 | in-process `main()`（2 組參數） | `test_ac_lrs_023_write_failure_never_changes_the_run_rc` |
| AC-LRS-024 | in-process `main()` | `test_ac_lrs_024_no_tmp_orphans_after_success_or_failure` |
| AC-LRS-025 | in-process `main()`（2 組參數） | `test_ac_lrs_025_pre_start_failures_do_not_touch_the_record` |
| AC-LRS-026 | in-process `main()`（3 組參數） | `test_ac_lrs_026_main_rc_semantics_unchanged` |
| AC-LRS-027 | 指令 | `PYTHONUTF8=1 lint-imports`（§4.3） |
| AC-LRS-028 | 指令 | `python tools/check_loc_budget.py --json`（§4.3） |
| AC-LRS-029 | 既有鎖 | `tests/infra/adapters/test_rtm_file_sink_newline.py::test_no_new_text_write_sites_without_explicit_newline`；`tests/test_r82_quota_axis_and_shipped_defaults.py::TestNoHarnessImport`；根層 `TestDirEntryPrimitivesAreAccountedFor`、`TestNaiveLocalTimestampsAreNotPersisted`、`TestTextIoDeclaresEncoding` |
| AC-LRS-030 | 指令 | `ruff check …`、`python tools/snapshot_sync.py --check`（§4.3） |

**反向追溯**：§3.2 全表的每個欄位由 AC-LRS-019（全欄位齊備與值一致）與 AC-LRS-020（映射）覆蓋；§3.3 形態總表六列由 AC-LRS-001～004 覆蓋；§3.5 的每條跨平台規則由 AC-LRS-019（LF、offset）、AC-LRS-018（stdout 編碼）、AC-LRS-023／024（寫入失敗與 tmp）與 AC-LRS-029（既有掃描）覆蓋。

### 4.3 Developer 必跑的驗證指令

在 `AutoClaude/` 下執行（需已啟用 venv；除錯加 `-n 0`）：

```bash
python -m pytest tests/cli -q
python -m pytest tests/infra/adapters/test_rtm_file_sink_newline.py \
  tests/test_r82_quota_axis_and_shipped_defaults.py tests/test_main_build_executor.py \
  tests/integration/test_def_200_205_production_wiring.py \
  tests/execution/test_r85_subtraction_locks.py -q
ruff check autoclaude/main.py autoclaude/execution/run_summary.py tests/cli/test_last_run_summary.py
PYTHONUTF8=1 lint-imports
python tools/check_loc_budget.py --json
python tools/snapshot_sync.py --check
# 根層既有掃描（unittest 必須在 tools/tests 下載入；隔離環境單跑前先設 AUTOSDD_SENTINEL_OFF=1，
# 本三類為純掃描、設了無害）：
(cd ../tools/tests && AUTOSDD_SENTINEL_OFF=1 python -m unittest \
  test_platform_neutral_paths.TestDirEntryPrimitivesAreAccountedFor \
  test_platform_neutral_paths.TestNaiveLocalTimestampsAreNotPersisted \
  test_platform_neutral_paths.TestTextIoDeclaresEncoding)
# 同一棵根層測試樹的 stdio 行內複本棘輪（§3.4.4 第 11 列；Developer 實測漏列於初稿）：
(cd ../tools/tests && AUTOSDD_SENTINEL_OFF=1 python -m unittest test_platform_utils_dedup)
python -m pytest tests/ -q          # 收尾全套：預期 rc=0、無 failed／error（略過數由環境決定，數字見根層 ONBOARDING §7，本檔不複寫）
```

PowerShell 形態（Windows 沒有 `VAR=value` 前綴語法，也禁用裸 `cd`）：`$env:PYTHONUTF8=1; lint-imports`；根層三類改為 `Push-Location ../tools/tests; $env:AUTOSDD_SENTINEL_OFF=1; python -m unittest test_platform_neutral_paths.TestDirEntryPrimitivesAreAccountedFor test_platform_neutral_paths.TestNaiveLocalTimestampsAreNotPersisted test_platform_neutral_paths.TestTextIoDeclaresEncoding; Pop-Location`（同一次呼叫內成對）。

**驗收口徑**：`tests/cli` 內新舊測試全綠（每個 AC 的測試函式逐一出現在輸出中）；上列每條指令 rc=0；`lint-imports` 的「kept」數不得少於動工前基線；任何一道紅都**先停下修復**，不得跳過、不得註解掉測試、不得改棘輪常數或欠債表。

---

## 5. 給 Developer 的實作順序

原則：**先落檔、再讀檔、最後接線**；每寫完一個單元立即跑對應測試與 `ruff check`（開發-編譯-測試循環，不累積）。測試與實作交替：先寫該步的測試（紅），再寫實作（綠）。

| 步驟 | 內容 | 立即驗證 |
|------|------|----------|
| 0 | **動工前基線（唯讀、零信任）**：跑 §4.3 的 `tests/cli`、`lint-imports`、`check_loc_budget.py --json`、`snapshot_sync.py --check`，記下 rc 與數字；不採信本檔的基線宣稱 | 全部 rc=0 才開工；有紅先回報主控 |
| 1 | **落檔側**：`run_summary.py` 的常數、兩個例外、`summary_path`、`outcome_of`、`build_started_record`／`build_finished_record`、`RunSummaryRecorder`（含原子寫入、best-effort）。對應測試：AC-LRS-020、024；recorder 層的 023（patch `os.replace`／`os.fsync`） | `python -m pytest tests/cli/test_last_run_summary.py -q -n 0`；`ruff check autoclaude/execution/run_summary.py`；**立刻**跑 `tests/infra/adapters/test_rtm_file_sink_newline.py` 與根層三類掃描（§4.3），確認新檔沒新增任何欠債（此時發現問題最便宜） |
| 2 | **讀檔側**：`summary_problems`、`load_summary`、`format_summary`、`show_last_run_summary`（含 stdout 防呆、`load_config` 失敗處理）。對應測試：AC-LRS-007～012、014（純函式）、015～018（呼叫 `show_last_run_summary`／子行程） | 同上；§2.6 的逐字範例 E1～E8 必須由測試逐字比對 |
| 3 | **`main.py` 接線**：import、parser 兩處修改、分派、recorder 三行、docstring（§3.3、§3.4.1）。對應測試：AC-LRS-001～006、013（CLI 層）、019、021～026 | `python -m pytest tests/cli -q`（含既有兩檔）；`tests/test_main_build_executor.py`、`tests/integration/test_def_200_205_production_wiring.py`、`tests/execution/test_r85_subtraction_locks.py` |
| 4 | **全面驗證**：§4.3 全部指令；`python -m pytest tests/ -q` 全套 | 全綠；回報格式見下 |
| 5 | **收尾（主控／單人窗口，不屬 Developer）**：`python tools/sync_onboarding_baselines.py --write`（表①，LOC total）→ `--check`；commit 前最後一步 `--write --with-slow`（表②，乾淨 venv）；再跑 pre-push 全套閘門 | 見 §3.4.4 第 7、8 列 |

**禁止事項**：不改 `autoclaude/core/**`、不改任何既有測試、不改 `AutoClaude/CLAUDE.md`、不新增 Port／Plugin／EventBus phase、不 import `tools.*`、不改棘輪常數與欠債表（`_KNOWN_MISSING_NEWLINE`、`_DIRENT_UNGUARDED_DEBT`、`_ENCODING_DEBT_RATCHET`）、不用 `--no-verify`／`AUTOCLAUDE_SKIP_HOOKS=1`、**不做任何 git 寫入**（commit／stash／checkout／reset 一律由主控處理）。若實作中發現本文與現場不符，先回報再改，不得悄悄偏離。

**Developer 回報格式**：(1) 改動檔清單（新增 2、修改 1，多出來的要說明）；(2) §4.3 每條指令的 rc 與關鍵輸出**逐字貼上**（不轉述）；(3) 各 AC 對應測試的綠燈輸出；(4) 任何偏離本文的地方與理由；(5) `main.py`、`run_summary.py` 的實測計價行（`check_loc_budget` 的 `count_loc`）。

---

## 6. 附：引擎呼叫 claude 的方式

> 本節**只記事實與 file:line，不做設計**。實測日 2026-10-10，claude CLI 2.1.296；「實測」指當回合真跑（argv 探針＝以回印 argv 的腳本充當 `claude.command`，零 API 成本；模型探針＝兩次 `claude -p … --output-format json --no-session-persistence --max-budget-usd 0.05`，合計成本約 0.002 美元）。

### 6.1 PTY 後端（出廠預設：`executor.backend: pty`，`utils/config.py:415`、`config.yaml:108`）

| 項目 | 事實 | 位置 |
|------|------|------|
| argv 組裝 | `args = list(claude.extra_args)`；若 `maintain_context and claude.continue_flag` 追加 `--continue`；若 `claude.output_format` 非空追加 `["--output-format", <fmt>]`；最後 `["-p", <prompt>]`。**無任何自動 `--model`** | `autoclaude/infra/adapters/pty_executor.py:72-80` |
| 設定欄位與預設 | `command="claude"`、`extra_args=[]`（預設刻意不多送旗標，歷史見註解）、`continue_flag="--continue"`、`output_format="json"` | `autoclaude/utils/config.py:130,141,142,147`（註解 `:131-140`）；出廠 `config.yaml:2,9,10` |
| 啟動 | POSIX／subprocess 模式：`argv = resolved + self._args`、`Popen(…, env=propagate_to_subprocess_env(dict(os.environ)))`；Windows `.cmd` shim 走 `_build_cmd_shim_line`；wexpect 模式 `wexpect.spawn(exe, args=…)` | `autoclaude/perception/pty_wrapper.py:36-52`（`_resolve_command`）、`:251-271`（`_start_subprocess`，argv `:259`，Popen 與 env `:264-271`）、`:238-243`（wexpect） |
| 每步原始輸出 | `<log_dir>/playbook_<淨化後 step_id>.log` | `pty_executor.py:85` |
| `--continue` 的來源 | `PlaybookTask.maintain_context`（預設 True） | `autoclaude/models/playbook.py:24` |
| 實測 argv | 預設：`--continue --output-format json -p <prompt>`；`maintain_context=False` 時無 `--continue`；`extra_args=["--model","sonnet"]` ⇒ `--model sonnet --continue --output-format json -p <prompt>`（`extra_args` 排最前）；子行程看得到父行程的環境變數（探針設 `ANTHROPIC_MODEL=haiku`，腳本讀得到） | 探針（scratchpad，不入庫） |

舊 runner 路徑（`PlaybookRunner` 在 `autoclaude/` 內沒有 production 建構點）的 `execution/prompt_dispatcher.py:47-50` 同樣是 `extra_args`＋`continue_flag`＋`-p`（無 `--output-format`），由 `playbook_runner.py:271` 呼叫。

### 6.2 SDK 後端（opt-in：`executor.backend: sdk`）

| 項目 | 事實 | 位置 |
|------|------|------|
| 後端選擇 | `build_executor` 依 `cfg.executor.backend` 選 `SdkExecutorAdapter` 或 `PtyExecutor` | `autoclaude/main.py:67-94` |
| 模型欄位 | `ExecutorConfig.model: str \| None = None`（「SDK 模型覆寫」，None＝SDK 預設）；出廠 config 只有註解 `# model: ""` 且註明 pty 後端時忽略 | `utils/config.py:403-424`（`:419`）；`config.yaml:105-111` |
| 傳遞 | `self._model = getattr(ec, "model", None)`；每步 `client_factory(…, model=self._model, continue_conversation=bool(maintain_context))`；值為 None 的 option 不傳 | `infra/adapters/sdk_executor_adapter.py:110`、`:166-172`、`:76-90` |

### 6.3 能否把每一步釘在 `--model sonnet`／haiku（事實表）

| 途徑 | 範圍 | 是否存在 | 證據 |
|------|------|----------|------|
| playbook／task 欄位 | 單步 | **無**。`PlaybookTask`（`models/playbook.py:16-70`）與 `Playbook`（`:79-88`）都沒有 `model` 欄位 | 讀碼 |
| `config.yaml` 的 `claude.extra_args: ["--model", "sonnet"]`（PTY 後端） | **全部步驟**（全域，非逐步） | **有**：引擎原樣透傳 `extra_args`（`pty_executor.py:72`） | 探針 argv；CLI 實測 `--model haiku` ⇒ JSON `modelUsage` 的鍵為 `claude-haiku-5-5` |
| 環境變數 `ANTHROPIC_MODEL`（引擎行程環境） | 全部步驟 | **有效**：引擎不讀不寫 `ANTHROPIC_*`（`autoclaude/` 內 grep 零命中），子行程繼承 `os.environ`（`pty_wrapper.py:269`） | CLI 實測：不帶 `--model`、只設 `ANTHROPIC_MODEL=haiku` ⇒ `modelUsage` 為 `claude-haiku-5-5` |
| SDK 後端 `executor.model` | 全部步驟 | 有，**僅** `backend: sdk`；PTY 忽略 | `config.py:419`、`sdk_executor_adapter.py:110,171` |
| Brain（Minimax）模型 | 非 claude | `minimax.model`（`config.py:88`；env `MINIMAX_MODEL`，`main.py:182`）——與 claude CLI 的模型**無關** | 讀碼 |

附註（事實，不含設計）：

- `claude --help`（2.1.296）：`--model <model>` 說明「Provide an alias for the latest model (e.g. 'fable', 'opus', or 'sonnet') or a model's full name」；help 範例未列 haiku，但實測 `--model haiku` 可用。
- 出廠 config 的 `extra_args` 有機械鎖：`tests/test_r82_quota_axis_and_shipped_defaults.py:49-100`（逐旗標比對 `claude --help`），`--model` 在 help 內，故寫進出廠 config 不會被該鎖擋；個人 `config.local.yaml` 不在該鎖射程。`utils/config.py:140` 註解所引的 `tests/test_claude_cli_flags.py` 現況不存在（全 repo 無此檔，實際鎖在前述檔案）。
- 未驗證（誠實劃界）：`--continue` 跨步驟換模型時的對話延續語意屬 CLI 行為，本次未測；目前**沒有**引擎層「每一步不同模型」的途徑，只有全域（`extra_args`／環境變數／SDK 的 `executor.model`）。
