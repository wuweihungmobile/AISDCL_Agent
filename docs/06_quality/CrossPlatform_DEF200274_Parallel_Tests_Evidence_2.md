# DEF-200-274 證據檔：根層 tools/tests 本機平行執行（opt-in）——第二冊

> **WHY 拆冊**：第一冊 `docs/06_quality/CrossPlatform_DEF200274_Parallel_Tests_Evidence.md` 已
> 累積至 255024 bytes，逼近 Read 工具 262144 bytes 上限（該上限為工具硬線，不可調整）；若在第一
> 冊繼續 append，下一次任何角色（複審、收尾親驗、下一輪量測員）用 Read 工具整檔覆核時將觸頂失
> 敗。故自第二十一輪起，後續輪次紀錄改寫入本冊（第二冊），第一冊在其末尾追加一句指針說明接續
> 於本冊。
>
> 第一冊路徑：`docs/06_quality/CrossPlatform_DEF200274_Parallel_Tests_Evidence.md`（第一輪～第
> 二十輪／R168 沿革全數留在該檔，不搬遷、不重寫）。
>
> **命名刻意不帶 `R<N>` 輪號**：沿用第一冊檔頭訂下的理由——本任務不屬於帳本的輪次迭代序列
> （`current_round()` 現查另有其值），是掌舵者直接提問、由 AISDLC 角色化 Workflow 一次性落地
> 與收尾；本冊只是同一份證據檔容量見頂後的接續分冊，因此沿用同一檔名前綴、以阿拉伯數字
> `_2` 作接續尾碼，而非另起一個帶輪號的新檔名。

## 第二十一輪：掌舵者兩問「CPU 只到 34%」「請讓它用到 80%」——量測歸因＋方法級細分＋W 政策校準（2026-09-23，Windows；R169）

掌舵者兩問：「為何 CPU 只用到 34%？」「可以讓機器用到 80% 嗎？請解決」。流程：量測員實測歸因
→ Architect／SD 設計 → Developer 兩棒 → QA W 掃描 → 對抗複審 → 收尾（主控 Fable、鏡全
Sonnet）。

### 34% 從何而來：分段歸因

量測員（W=13 一次真跑，根層 `tools/run_root_unittests.py`）：

| 分段 | 時長／範圍 | 平均 CPU | 備註 |
|---|---|---|---|
| discovery（單行程 import 4551 測試） | 前 20s | 6.3% | 純序列前奏，結構上無法平行 |
| 穩態 | 20–160s（140s） | 77.6% | python 行程數尖峰 30–78：測試自身 fork 子行程，故可超過 13/20=65% 的天真上限 |
| 尾段 | 18.2s | 17.9% | 收尾序列化（merge／report） |
| **整輪（W=13）** | **187.2s** | **63.5%（中位 73–75%）** | wall |

活體快取 `S=2381s`，`ideal=max(S/13=183.2, 最長單位=166.6)=183.2s` ⇒ **S/W-bound**（瓶頸是
總工作量除以 worker 數，不是尾段），排程 slot 利用率 97.8%。AutoClaude pytest（loadgroup）另
一組獨立讀數：30.4s 均 61.1%，同樣對不上 34%。

**結論**：34% 對不上量測員本輪能重現的任何整輪或分段平均值——discovery 前 20s（6.3%）太低、
尾段 18.2s（17.9%）也不到，穩態 77.6% 又太高。最可能的解讀：掌舵者當時看到的是 pre-push 全鏈
（快層守門→AutoClaude leg→SDD 三套→py_compile→discovery→unittest）某個工作管理器瞬時讀數
的混合觀感，或是把超執行緒的邏輯核總數當分母而低估了實際可用並行度。原始 34% 觀測情境本身
未被記錄，本節是本輪能做到的最佳事後覆核，不是對該次觀測的逐點重現。

Architect 修正：現況瓶頸是 S/W 而非尾段；W 越過交叉點 `W*=S/max_unit≈14.3` 後，最長單位才會
成為天花板 ⇒ 方法級細分（讓 max_unit 變小）與拉高 W（讓 S/W 變小）互為前提，單獨做其中一項效
益有限。

### 設計裁決（Architect）

- **D1（採用）**：互動式 `cpu_budget` 公式從「實體核−1」改為「(實體核−1)+(邏輯−實體)//2」，
  把部分 SMT 邏輯核納入預算（本機 14P/20L：13→16；M1 Max 10P/10L 仍算 9；headless／CI 路徑
  不變）。QA 的 W 掃描顯示 W=16 是 wall 與利用率的雙贏點，與此公式算出的值一致，兩者互為佐證。
- **D2（本輪不做）**：動態 ρ（目標使用率）回饋機制——讓 W 依觀測 CPU 使用率朝掌舵者要求的
  80% 動態收斂，而非靠一次性靜態公式決定。本輪不做的理由：需要額外一輪先驗證回饋迴圈在單次
  wall≈163~198s 的短命行程上是否有意義的收斂視窗，且會與既有 `cpu_budget` 快取／環境變數覆
  寫語意衝突；先用 D1 的靜態公式打底，動態機制留待下一輪評估。
- **D3（本輪不做）**：pre-push 三 leg（快層守門→AutoClaude leg→SDD 三套）改並行執行——理論
  上可省時，但需先量測各 leg 隨並行數的 `T_leg(w)` 曲線，並重新設計 `per_leg_budget(n_legs>1)`
  這條現行死路徑的序列契約，屬另案（見〈下一輪候選〉）。
- **D4（採用）**：測試派工粒度從模組／類別再往下切到方法級，附五道安全網＋fail-closed 兜底
  （遇不支援細分的 fixture 形態直接跳過，不中斷整體派工）。解決「單一重量級類別成 makespan
  天花板」的問題，並讓 S/W-bound 與 max_unit-bound 兩種瓶頸能分開觀測（📊 摘要行標註瓶頸類
  型）。

### W 掃描（QA 六輪交錯，中位數）

QA 量測法：W 序列 13→16→20→20→16→13（每個 W 兩輪取中位數，交錯排序以抵銷機器暖機／降頻
等隨時間趨勢的干擾）。

| W | wall（中位） | 平均 CPU | 穩態 CPU | S（估，隨 W 競爭膨脹） | 備註 |
|---|---|---|---|---|---|
| 13 | 189.4s | 58.8% | 74.9% | ≈1967s | 基準 |
| 16 | 163.7s | 74.0% | 88.9% | ≈2240s | **本輪最佳**：wall 最短、利用率次高 |
| 20 | 176.5s | 72.2% | 98.9% | ≈2675s | 利用率最高，但 wall 比 16 慢；被 `test_context_budget_guard`（`setUpModule`，當時尚在自動細分白名單外）卡成 max_unit-bound（134.9→154s） |
| 14／15／17／18 | 未測 | — | — | — | **HYPOTHESIS**，未實跑，不可引用為結論 |

同輪掃描亦發現 DEF-200-368 殘餘：計時快取父鍵不隨子類別鍵回填，與逐輪變動的 `fair_share`
比較在門檻附近反覆翻轉，`test_run_root_unittests` 同 W 同樹兩次執行拆／不拆不一致（詳見下節
缺陷修復）。

### 改動與鎖（Developer 兩棒）

- `tools/lib/dispatch_granularity.py`：新增方法級自動細分（五安全網＋`try/except` fail-closed
  兜底）；白名單新增 `test_context_budget_guard`／`test_run_root_unittests`／
  `test_platform_neutral_paths`；新增 `_MODULE_FIXTURE_SAFE_EXCEPTIONS` 兜底 `@staticmethod`
  形式 `setUpClass`（對抗複審 P0 發現並修正）。承 DEF-200-370。
- `tools/lib/dispatch_imbalance.py`：新增 `📊 派工摘要` 輸出行（worker／S／ideal／瓶頸類型／
  loss／slot 利用率／最長單位）。承 DEF-200-370 的可觀測性配套。
- `tools/lib/cpu_budget.py`：互動式預算公式改 `(實體核−1)+(邏輯−實體)//2`；headless／CI 路徑
  不變。承 DEF-200-369。
- `tools/lib/parallel_timing_cache.py`：`save_live_cache` 補父模組前綴加總回填。承 DEF-200-368。
- `tools/lib/parallel_shard.py`：新增 `[cpu_budget] root-unittest workers=N source=…` 標籤
  行。承 DEF-200-371。
- `tools/tests/test_run_root_unittests.py`：+416 行，涵蓋上述四缺陷新鎖與對抗複審 P0 負向測
  試。
- `tools/tests/test_cpu_budget.py`：+31 行，涵蓋 DEF-200-369 公式鎖。

**對抗複審**：APPROVE-WITH-FIXES；P0——`_class_has_only_base_fixtures` 遇 `@staticmethod` 形
式 `setUpClass` 會拋 `AttributeError` 且無兜底（已修＋負向測試）；14 支新測試全過 Rule 9；
E501／輪號字面零命中。

### 驗證數字

**Developer 第二棒（新公式生效、不設覆寫）全套兩次**：

- `[cpu_budget] root-unittest workers=16 source=cpu_budget`；派工單位 460 個兩次一致（父鍵回
  填後不再震盪）。
- 第一次：`📊 派工摘要：worker=16｜S=2423.1s｜ideal=151.4s（S/W-bound）｜loss=1.00x｜slot利
  用率=99.8%｜最長單位：TestPlanRejectsRowsWithExternalResidencePointers 121.0s`。
- 第二次：`S=2375.9s／ideal=148.5s`（其餘欄位同型態）。
- `test_context_budget_guard` 已拆成約 90 個類別鍵（模組鍵回填 211.12s）。
- rc=1，僅剩護欄棘輪 3 支待收尾單人窗口重釘（非功能性紅）。

**雲端驗收**（commit `ff91997`，五支 push 管線＋mutation dispatch 全 success）：

| 缺陷 | 驗收管道 | 證據（逐字摘錄） |
|---|---|---|
| DEF-200-363 | root-infra／windows-compat／macos-compat CI | 根層 unittest 4551 個測試（下限 4543）worker=4／4／3，皆見 `source=cpu_budget` 標籤 |
| DEF-200-364 | aisdlc-sdd-ci v0.30 | `1962 passed, 5 skipped`（前次 `1949 passed, 8 skipped`：+13＝10 支新測試＋3 支 docker 測試 `:283`／`:296`／`:314` 由 skip 轉 pass，殘差 0）；log 見 `[sdd-docker-probe] controller docker_available=True` |
| DEF-200-365 | `autoclaude-mutation-on-change` run `35861043538` | artifact marker 段 `Killed (107)`／`Survived (59)` ⇒ `kill_rate=64.46%`（前次 `0.00%`） |
| DEF-200-366 | 三平台 CI | 皆未裝 `psutil` ⇒ live smoke 走 `[1, cpu_count]` 弱判準；win32 ctypes 分支的跨值交叉比對只在本機真機驗證過 |
| DEF-200-367 | 併入 DEF-200-364 同批 v0.30 驗收 | 撞名解除後三支 docker 測試計入 `1962 passed`，未個別分列 |

**本輪 commit `f3f3425`＋`933e53e` push 後雲端（主控親抓 log）**：五支 push 管線（AutoClaude CI／
root-infra-ci／aisdlc-sdd-ci／windows-compat-ci／macos-compat-ci）全 success；根層 unittest 三平台皆印新
標籤行 `[cpu_budget] root-unittest workers=4 source=cpu_budget`（ubuntu run 35885129655／windows run
35885129561）與 `workers=3 source=cpu_budget`（macos run 35885129451），三平台皆 `發現 4577 個測試
（下限 4543）`；ubuntu 另印 `📊 派工摘要：worker=4｜S=2601.7s｜ideal=650.4s（S/W-bound）｜loss=1.00x｜
slot 利用率=100.0%`（刷新後的種子檔在無活體快取的 runner 上直接給出滿排程）。DEF-200-369／370／371 的
新程式碼在三平台 CI 真跑通過（unittest 非 -v，憑證＝總數＋job success）。

附帶觀察（→DEF-200-372，收尾窗口同輪定根因並修復）：`mutation-on-change` 連兩輪皆 `runs=1/7`，
annotation 顯示「無既往 mutation-history artifact（首輪或已逾 retention）」。主控以 `gh api
/repos/…/actions/artifacts?name=mutation-history` 現查 `total_count=0`，run 35861043538 只上傳了
report artifact；再逐字讀該 run 的 upload step log：`include-hidden-files: false` ＋
`No files were found with the provided path: AutoClaude/.mutation_history.jsonl. No artifacts will be
uploaded.`——`actions/upload-artifact` v4 起預設排除點檔，`.mutation_history.jsonl` 從未上傳，restore
端因此恆空、unique-sha 跨 run 累積自 v4+ 遷移起結構性死亡；同一 run 的 report artifact 也只有 2 檔
（`.mutation_baseline.toml` 被排除）。修法＝五處 upload step 顯式 `include-hidden-files: true`
（`autoclaude-mutation-on-change.yml` history／report 兩處；`autoclaude-ci.yml` AC4 history／
mutation token_guard／perf baseline 三處，皆含點檔）。雲端驗收（push `933e53e` 後兩次 dispatch）：
run 35885321554 首次出現 `mutation-history` artifact（332 bytes；report artifact 1630→2030 bytes，
`.mutation_baseline.toml` 開始入包）；run 35886198015 restore 步驟印 `已還原 history：1 筆`、upload
步驟印 `there will be 1 file uploaded`，`gh api …/artifacts?name=mutation-history` total_count 0→2。
`runs` 仍 `1/7`：兩次 dispatch 的 token_guard 源碼 `source_sha256` 相同，ADR-SD09-011 同 sha 去重留最新
——這是設計行為，不是缺口；遞增要等真實 token_guard 源碼變動觸發 on-change。

**22:30 排程 nightly**（在本輪尚未 commit 的中途樹上跑）：`local_ci_gate=1`（護欄棘輪紅，符合
預期——中途樹本就未收斂，非回歸）；`perf=0` 且 baseline 重鎖（`decide_correction` p95
`2.117→2.091ms`）。

### 🔴 誠實劃界（本輪仍未達成字面 80%，不可宣稱已達標）

- 整輪平均 CPU 63.5%（W=13）／最佳點 W=16 時 74.0%（穩態 88.9%），**皆未達到掌舵者字面要求
  的 80%**。本輪交付的是「歸因清楚＋可調校的機制」，不是「已達 80%」的宣稱。
- 80% 未達的結構性原因：discovery 前 20s（＠6.3%）與尾段 18.2s（＠17.9%）是無法平行的序列
  段，會拉低整輪平均；pre-push 三 leg 目前仍序列執行（D3 本輪不做）；W=20 雖穩態達 98.9%，
  但 wall 反而比 W=16 慢（被單一類別卡住）——**利用率高不等於 wall 快，兩者不可互換宣稱**。
- W=14／15／17／18 四個值本輪未實跑，若要精確定位「wall 最短點」需補測；目前 W=16 只是
  13／16／20 三點掃描中的最佳點，不是全域最佳點的證明。
- 三平台 CI（root-infra／windows-compat／macos-compat／aisdlc-sdd-ci／autoclaude-ci）皆未安
  裝 `psutil` ⇒ DEF-200-366 的 win32 ctypes 分支交叉比對只在本機真機驗證過，雲端這條分支目前
  仍只被舊有弱判準 `[1, cpu_count]` 覆蓋。
- 22:30 排程 nightly 是在中途未 commit 的樹上跑的，`local_ci_gate=1` 屬預期紅、不代表本輪交
  付有回歸，但這份 nightly 產物也不能拿來當本輪的驗收證據。
- DEF-200-372（`mutation-on-change` `runs=1/7`）根因已定、旗標已補、雲端兩次 dispatch 已驗到
  artifact 出現與 restore 讀回；但 `runs` 遞增本身還沒被觀測到（同 sha 去重），要等下一次真實
  token_guard 源碼變動的 on-change run 才看得到 2/7。

### 下一輪候選

1. **三 leg 並行（D3 的後續）**：需先量測 `T_leg(w)` 曲線（AutoClaude leg／SDD 三套／根層各
   自隨並行數的耗時），並重新設計 `per_leg_budget(n_legs>1)` 這條現行死路徑的序列契約，才能
   評估並行是否真的省時、省多少。
2. **S 本身瘦身**（減少總工作量而非只調 W／細分）：候選重量級測試——`CarrierVerdictParityTest`
   （45s）、`ProblemReportItemizationTest`（29s）、`StaticWindowsSkipTagScanTest`（15s）等
   spawn／全樹掃描型測試，耗時多來自跨行程或全樹 I/O，方法級細分對它們效益有限，須從測試本
   體下手。
3. **discovery lazy import**：目前 discovery 前 20s 是單行程 import 4551 支測試、CPU 僅 6.3%
   的純序列段，若能延後或平行化 import，可直接壓縮整輪平均的分母。
4. （附）**D2 動態 ρ 回饋機制**：待 D1 靜態公式與方法級細分（D4）穩定運行數輪後，再評估是否
   值得疊加動態收斂機制。
