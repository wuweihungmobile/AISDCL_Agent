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

## 第二十二輪：掌舵者六問「帳本多 CPU 問題／功能完備＋CI 多 CPU／全面優化平衡負載／其他可多 CPU 面／是否收斂／完成前輪未完成」——完整 W 掃描定位全域最優帶＋三 leg 並行＋收斂宣告（2026-09-24，Windows）

掌舵者六問：①帳本上還有哪些多 CPU 問題？②多 CPU 功能是否完備、CI 是否也已多 CPU？③能否
全面優化以平衡負載？④還有哪些面向可以多 CPU？⑤這件事是否已可收斂？⑥前一輪承諾但未完成的
項目是否已補齊？流程：SA 盤點 → 量測員完整 W 掃描 → Architect 設計 → QA-1 三 leg 真並行量測
→ Developer 兩棒落地 → QA-2 收尾驗證 → 對抗複審 → 記帳員收斂。鏡全 Sonnet（SA／量測員／
Architect／QA-1／Developer A／Developer B／QA-2／對抗複審／記帳員），主控 Fable 只裁決親驗。
額度守衛 notice→converge→prepare 三帶皆已觸發（Fable 週額度 83→85%），context 守衛全程擋
Workflow，每 300s 只准派 1～2 個 Agent，逐個派完。

### 量測（兩張表）

**表一：完整 W=13~20 逐一交錯掃描**（每 W 取兩輪中位，交錯序列
16,14,15,17,18,18,17,15,14,16 抵銷機器暖機／降頻趨勢；13／20 兩點沿用前一輪掃描值不重測）：

| W | wall 中位 (s) | 整輪 CPU | 穩態 CPU | S (s，估) | 備註 |
|---|---|---|---|---|---|
| 13（沿用前輪） | 189.4 | 58.8% | 74.9% | ≈1967 | 基準 |
| 14 | 180.65 | 71.4% | 78.6% | ≈2208 | |
| 15 | 172.5 | 74.8% | 83.8% | ≈2251 | |
| 16 | 167.5 | 77.5% | 87.8% | 2321 | 第 10 輪；第 1 輪 181.8 為首輪暖機離群，兩輪中位 174.65，與前輪 163.7 差 +6.7% 漂移 |
| 17 | 166.45 | 80.3% | 91.75% | ≈2431 | 本系列首次整輪跨過掌舵者要求的 80% 門檻 |
| 18 | 164.4 | 82.85% | 95.3% | ≈2541 | wall 最短且利用率最高，本輪選定值 |
| 20（沿用前輪） | 176.5 | 72.2% | 98.9% | ≈2675 | 利用率最高但 wall 較慢 |

全部 10 輪 📊 摘要行皆判 S/W-bound、slot 利用率 99.8%、loss 1.00x；最長單位（恆為
`TestPlanRejectsRowsWithExternalResidencePointers`）118～136s；W=18 的 ideal≈141s 已貼近最長
單位，即 S/W-bound 與 max_unit-bound 的交叉點，故 W>18 邊際效益結構上有限。W=18 兩輪中一輪
rc=1（`test_windowsapps_guard_bash_parity.TestPickRepoPythonBehavior.test_ci_env_falls_back_to_path_python`
`mktemp: failed to create directory via template /tmp/tmp.XXXXXXXXXX: Permission denied`，根因與修
復見下）。**discovery 訂正**：前輪誤植「20s＠6.3%」為 discovery 耗時，本輪重測實測
discovery 僅 1.6s——前輪誤讀的低谷其實是 worker 匯入暖機，非序列 import 段。

各 leg 隨並行數的耗時 T_leg(w)：AutoClaude leg（loadgroup，PG 在場，4883 passed／10 skipped）
W=4／8／16 分別 59.3s／36.5s／30.6s；SDD leg（`ci-gate.sh` 雙軌：v0.01 序列 1478 passed≈26.6s
固定＋v0.30 xdist 1956 passed＋`scripts/tests` 364）W=4／8／16 分別 76.2s／71.8s／67.5s；
`compileall -j0` 0.41s（序列 0.70s）；`arch_fitness` 0.54s。序列三 leg 總和（W=16）＝
174.65+30.6+67.5＝272.75s，是三 leg 並行設計的比較基準。

**表二：QA-1 三 leg 真並行量測**（root／AutoClaude／SDD 三 leg 同時起跑）：

| 方案 | root workers | AutoClaude workers | SDD workers | 整組 wall | 省下 | 備註 |
|---|---|---|---|---|---|---|
| E1-a | 14 | 2 | 2 | 208.04s | 23.7% | root 側出現 3 支 `mktemp` flake |
| E1-b | 16 | 2 | 2 | 203.44s | 25.4% | 三 leg 全 rc=0，瓶頸恆在 root |

W=18 三 leg 並行另跑三次，164.1／165.6／165.3s 全綠，flake 出現率 1/5（本階段樣本）。**flake
診斷**：`test_windowsapps_guard_bash_parity` fixture 自行 `mktemp -d`，Git Bash 的 `/tmp` 對應
`C:\Users\<user>\AppData\Local\Temp`（實測約 16 萬個項目、Windows Defender 即時防護開啟），高
並發建立／刪除同一巨大共用目錄時，AV 過濾驅動偶爾讓 `CreateDirectory` 短暫回
`ACCESS_DENIED`；受測腳本本身零 `mktemp` 呼叫，問題全出在測試 fixture。

### 設計裁決

**採用（各附數字）**：

- **W 公式校準**：互動式 `cpu_budget` 公式改為
  `max(1, min(CAP, logical − ceil(logical/physical)))`（保留一顆實體核＋其 SMT 兄弟給前景），
  CAP 由 16 提高到 18。理由：完整 W=13~20 掃描顯示 17／18 整輪 CPU 已達 80.3%／82.85% 且 wall
  不劣（166.45s／164.4s），16 僅 77.5%，未達掌舵者字面要求的 80%。代價：S 從 2321s（W=16）漲
  到 2541s（W=18，+9.5%），16～18 之間是平坦帶。換算：(14,20)→18、(10,10)→9、(4,4)→3、
  (8,16)→14（**HYPOTHESIS**，未實跑）；physical 讀不到時退回 `logical−1`；headless／CI 路徑
  不變。
- **邏輯核偵測優先序**：優先讀 `os.sched_getaffinity(0)`（Linux 容器／cgroup 親和性遮罩場
  景），讀不到才退回既有邏輯核計數。
- **三 leg 並行**（Architect 判準：savings ≥20% 才值得做，QA-1 實測 25.4%，達標）：pre-push
  快層守門後，AutoClaude leg／SDD leg 改背景並行各 `workers=2`、root leg 前景吃滿當次 W；逐
  pid wait；固定順序回放輸出；新增 `[cpu_budget] parallel legs: root=<W> autoclaude=2 sdd=2
  wall=<N>s` 憑證行；逃生口 `AUTOSDD_PREPUSH_SERIAL_LEGS=1`；`mktemp` 建立暫存目錄失敗時退回
  序列執行；`trap` 補上背景行程 `kill` 與暫存目錄 `rm`（原始設計缺口，QA-2 前已修復）。
- **三平台 CI 補 psutil**：`root-infra-ci.yml`／`windows-compat-ci.yml`／`macos-compat-ci.yml`
  三處 pip 安裝步驟加 `psutil`，解除 DEF-200-366 誠實劃界中「win32 ctypes 分支雲端零覆蓋」的
  前置缺口（雲端真跑待下次 dispatch）。
- **收斂判準①落地**：`PytestInvocationSiteCensusTest` 併入
  `tools/tests/test_ci_gate_xdist_allowlist.py`（34 站點普查：PARALLEL 16／SERIAL 15 登記 18
  列／UNGOVERNED 3→0），三處 chaos 凍結基線裸呼叫（`AISDLC_SDD/scripts/ci-gate.ps1`、
  `.github/workflows/aisdlc-sdd-fsm-chaos-nightly.yml`、`AutoClaude/tools/run_local_nightly.ps1`）
  顯式補 `-p no:xdist`。
- **TMPDIR 隔離修 flake**：`tempfile.mkdtemp` 餵子行程 `TMPDIR`，複審實機證實 Git Bash 的
  `mktemp` 尊重 `C:/…` 形式的 `TMPDIR`。

**不值得做（各附數字）**：

- **D2 動態 ρ 回饋**：本輪完整 W=13~20 掃描證實靜態公式落點就是 argmin（鎖
  `abs(公式值−argmin)≤1`），動態回饋機制的邊際價值已無實測支持。
- **discovery lazy import**：訂正後實測僅 1.6s（<1% of wall），投入產出比過低。
- **S 本身瘦身**：三支候選重量級測試合計 89s，除以 W=18 僅貢獻 ≈5s（≈3% of wall，<5% 門
  檻），且會撞 Rule 9（測試鑑別力）風險，本輪判定不值得做。
- **`ci-gate.sh` 凍結基線∥LATEST 重疊並行**：最多省 ≤26.6s（v0.01 序列耗時），且 D3 三 leg
  並行落地後 SDD leg 已被 root leg 遮蔽，不值得在 CI 關鍵腳本上再開一條並行分支。
- **mutation 分片**：mutmut 2.4.3 無原生平行支援，且 nightly 屬無人值守情境，wall 不阻塞人，
  下游 sqlite cache 消費者也要跟著改，投入產出比低。
- **nightly stage 重疊**、**cgroup 配額**、**記憶體上限**：皆屬無人值守或無受害場景（本機
  128GB RAM、CI 固定 4 worker），本輪判定不值得做。

**誤判澄清**：SA 盤點階段一度判定 AutoClaude CI 的 `test`／`equivalence` job 對並行 worker
數「無憑證」，經主控親驗雲端 log 推翻——`AutoClaude/tests/conftest.py` 早有
`pytest_xdist_auto_num_workers` 走 `cpu_budget.py --legs 1`；雲端 run `35885129613` 三個 job
皆印 `[cpu_budget] xdist workers=4 source=cpu_budget`＋`nodes confirmed=4`；`aisdlc-sdd-ci` run
`35885129547` 印 `broadcast workers=4 source=cpu_budget`→`xdist workers=4 source=env`→
`nodes confirmed=4`，即掌舵者第二問（CI 多 CPU 覆蓋完備性）五條 CI 線全部已有可稽核字串。此
案例提醒：SA 的「無憑證」判定必須親抓雲端 log 覆核，不能只憑存量文件推論。

### 改動與鎖（逐檔）

- `tools/lib/cpu_budget.py`：互動式公式改
  `max(1, min(CAP, logical − ceil(logical/physical)))`、CAP 16→18；`os.sched_getaffinity(0)`
  優先序；headless／CI 路徑不變。承 DEF-200-373／DEF-200-374。
- `tools/git-hooks/pre-push`：三 leg 序列改並行段（AutoClaude／SDD leg 背景 workers=2、root
  前景滿 W）＋逐 pid wait＋固定順序回放＋`[cpu_budget] parallel legs:` 憑證行＋逃生口
  `AUTOSDD_PREPUSH_SERIAL_LEGS=1`＋mktemp 失敗退序列＋`trap` 補 kill／rm。承 DEF-200-375。
- `tools/tests/test_pre_push_dispatcher.py`：新鎖驗證並行段行為、逃生口、`trap` 清理。
- `tools/tests/test_ci_gate_xdist_allowlist.py`：併入 `PytestInvocationSiteCensusTest`（34 站
  點普查，PARALLEL 16／SERIAL 15 登記 18 列／UNGOVERNED 3→0）。承 DEF-200-376。
- `AISDLC_SDD/scripts/ci-gate.ps1`、`.github/workflows/aisdlc-sdd-fsm-chaos-nightly.yml`、
  `AutoClaude/tools/run_local_nightly.ps1`：三處 chaos 凍結基線裸呼叫補 `-p no:xdist`。承
  DEF-200-376。
- `tools/tests/test_windowsapps_guard_bash_parity.py`：fixture 改用 `tempfile.mkdtemp` 餵子行
  程 `TMPDIR` 隔離，堵住共用 %TEMP% 的 AV 競爭 flake。承 DEF-200-377。
- `.github/workflows/root-infra-ci.yml`、`.github/workflows/windows-compat-ci.yml`、
  `.github/workflows/macos-compat-ci.yml`：pip 安裝步驟加 `psutil`。承 DEF-200-378。
- `tools/tests/test_run_root_unittests.py`：W 值鎖 `{100:16}`→18 同步（此前漏同步鏡像鎖，
  Developer B 二次重釘補上）。
- `AutoClaude/tests/tools/test_local_ci_gate.py`：字串切片改跟 `_run_autoclaude_leg() {` 函式
  邊界（此前漏同步，Developer B 二次重釘補上；函式化會打斷字串切片型鎖是本輪教訓之一）。
- `tools/tests/test_cpu_budget.py`：新公式與 `os.sched_getaffinity` 優先序鎖；E501 債務改短 5
  行（未觸發重釘）。
- `tools/tests/test_adr_xplat001_c1c2_lock.py`：護欄棘輪重釘 104746→105179（+433，本輪兩次重
  釘）。

### 驗證數字（QA-2，改動落地後、預設 W=18 不覆寫）

- 根層全套 ×3：wall 163.40／164.03／165.71s；整輪 CPU 85.31%／85.46%（第 1 次採樣器失敗未
  測）；發現 4589 個測試（下限 4543）。
- `[cpu_budget] root-unittest workers=18 source=cpu_budget`；📊 `worker=18｜
  S=2552.5～2591.3s｜ideal=141.8～144.0s（S/W-bound）｜loss=1.00x｜slot 99.8%｜最長單位
  130.3～133.3s`。
- mktemp flake 三次未再現。
- **三個決定性回歸**（皆本輪漏同步鏡像鎖，Developer B 已修並二次重釘）：
  `test_subprocess_encoding_hygiene` E501 債務計數 144>139（改短 5 行，未重釘）；
  `test_run_root_unittests.py:294` `{100:16}`→18；
  `AutoClaude/tests/tools/test_local_ci_gate.py:996` 切片改跟 `_run_autoclaude_leg() {` 函式邊
  界。
- 設計缺口：pre-push 並行段原本 `trap` 不清暫存目錄，已補 `rm` 並加文字鎖。
- AutoClaude 全套 `--dist loadgroup`：`1 failed（即上述 test_local_ci_gate，已修）, 4882
  passed, 10 skipped`；`[cpu_budget] xdist workers=18 source=cpu_budget`／
  `nodes confirmed=18`。
- `ci-gate.sh` rc=0，wall 68.41s，`broadcast workers=18`；v0.01 1478／v0.30 1956／
  `scripts/tests` 364；10 道 lint 全綠。
- 本機 `.venv` 實際已有 `psutil` 7.2.2 ⇒ 本機 `test_cpu_budget` 走強判準，46 tests OK。
- **偶發、與本輪 diff 無關**：`test_archive_defect_log.TestArchiveIndexDocIsExternalized.`
  `test_main_ledger_carries_no_leftover_index_bullet` 全套 1/3 紅（`ADL.apply()` 落地前保全不
  變量回報 3 筆），根因未查（見缺陷帳本 DEF-200-380）。

### 複審

**對抗複審**：APPROVE-WITH-FIXES，P0 零；P1——重釘帳缺 `round-label-ok` 標記共 10 列（已
補）；P2——註解誤植（已修）。實機證實：`-p no:xdist` 對未安裝插件只是 `set_blocked`，不影響
既有行為；`ci-gate.sh` 凍結基線∥LATEST 重疊維持序列是決策豁免，不是遺漏；stdin 以
`STDIN="$(cat)"` 先捕捉再 fork，無競態。定向回歸鎖修復後全過：`test_adr_xplat001_c1c2_lock`
192 tests OK、`test_doc_loc_baseline_freshness_r60` 281 tests OK、`test_platform_neutral_paths`
177 tests OK、`test_pre_push_dispatcher` 37 tests OK、`test_cpu_budget` 46 tests OK、
`test_ci_gate_xdist_allowlist` 13 tests OK、AutoClaude 單檔 94 passed。

**Architect 另發現（超出多 CPU 範圍，登記為新缺陷）**：`aisdlc-sdd-fsm-chaos-nightly.yml` 三處
`working-directory` 寫死凍結基線版本，本機 nightly Stage 6 亦鏡射同一版本 ⇒ LATEST（v0.30）
的 `-m chaos` 測試雲端與本機皆零覆蓋。此發現涉及 Rule 9.9.4「連 3 日失敗鎖 main」的閘門治
理，主控裁決登記為 open 交掌舵者排期，不在本輪範圍內逕行落地（見缺陷帳本 DEF-200-379）。

### 收斂宣告

掌舵者第五問「是否已可收斂」——五條收斂判準逐條核對：

1. ✅ **整輪 CPU 利用率達成掌舵者原始要求（≥80%）且 wall 不劣化**：QA-2 收尾全套三次 wall
   163.40／164.03／165.71s，整輪 CPU 85.31%／85.46%（優於掌舵者要求的 80% 門檻，亦優於上一
   輪最佳點 W=16 的 74.0%）。
2. ✅ **W 全域最優帶已由完整逐一掃描定位，不再是局部三點外推**：W=13~20 全部 8 個值皆有實
   測（13／20 沿用前輪、14~18 本輪新測），17／18 兩點構成 ≥80% 的平坦帶；公式改
   `logical−ceil(logical/physical)`、CAP 18，argmin 鎖 `abs(公式值−argmin)≤1` 已固化為回歸測
   試（`test_cpu_budget` 46 tests OK）。
3. ✅ **S/W-bound 與 max_unit-bound 兩類瓶頸的可觀測性已成為標準輸出**：全部 10 輪 W 掃描與
   QA-2 三次收尾全套皆印 📊 摘要行（worker／S／ideal／瓶頸類型／loss／slot 利用率／最長單
   位），方法級自動細分（承 DEF-200-370）與計時快取父鍵回填（承 DEF-200-368）持續生效，本輪
   僅因未同步鏡像鎖短暫回歸，已二次收斂修復。
4. ✅ **本系列累積的偶發 flake 已定位真因並消除**：`test_windowsapps_guard_bash_parity` 的
   `mktemp` ACCESS_DENIED 已由對抗複審實機重現定根因（fixture 落共用 %TEMP%、Defender 即時
   防護與高並發 CreateDirectory 競爭），改用 `TMPDIR` 隔離後 QA-2 三次 W=18 全套未再現（樣本
   數為本輪誠實劃界的已知限制，見下）。
5. ✅ **收斂判準①（pytest 呼叫站點普查覆蓋率）已落地，不留治理死角**：34 站點全普查，原
   UNGOVERNED 3 處（三處 chaos 凍結基線裸呼叫）已顯式補 `-p no:xdist`，UNGOVERNED 歸零。

**宣告**：DEF-200-274 系列（根層 `tools/tests` 本機平行執行 opt-in）自本輪起**收斂**——以上
五條判準皆 ✅ 且各附證據。後續多 CPU／並行相關發現一律以獨立新缺陷列處理（如本輪
DEF-200-379／DEF-200-380），**不再開立新一輪多 CPU 迭代**（本欄刻意零輪號，故以「系列」稱
之，不引用輪號字面）。

### 🔴 誠實劃界

- **拓撲外推屬 HYPOTHESIS**：本輪完整掃描僅在本機 14P/20L 實機上實測；D1' 公式對其他拓撲
  （例如 8P/16L）的推算值（如 (8,16)→14）**未實跑驗證**，不可引用為結論。
- **`ci-gate.ps1` fallback 分支本機執行不到**：凍結基線／LATEST 判準與 mktemp 失敗退回序列
  等 fallback 路徑，在本輪本機真跑環境下結構上不會被觸發，僅由既有靜態／mock 測試覆蓋，未
  經真機分支驗證。
- **三 leg 並行是取捨、非全贏**：僅在多區域 push（快層守門＋AutoClaude leg＋SDD 三套皆需要
  跑）時才省時 25.4%；AutoClaude／SDD 各自被壓到 `workers=2` 後，個別 leg 時長被壓縮空間換取
  的是拉長——QA-1 量測顯示兩 leg 分別被壓到 163～186s／153～178s，相對其獨立跑滿 W 的情境慢
  約 5～6 倍；若只有單一 leg 需要跑，此設計無益甚至更慢。
- **flake 樣本量過小**：本輪對 `mktemp` flake 的觀測樣本僅涵蓋 QA-1 前測 5 次（1 次命中）＋
  QA-2 收尾 3 次（0 次命中），合計 8 次，未達到可給出置信區間的統計量；「三次未再現」只能宣
  稱「目前證據支持該根因」，不能宣稱「已徹底根治」。
- **雲端待驗**：DEF-200-378（三平台 CI 加裝 psutil）與本輪全部改動的雲端 CI 驗收（五支 push
  管線）皆待下次 push 後才有雲端 log 可核；本節數字全部來自本機 Windows 真機。

### 待主控回填

- 收尾全套 rc（主控親跑，DEF-ID 回填後、commit 前）：rc=0（另一次同樹 rc=1 僅為淨額棘輪透過
  `test_check_defect_log_crossref` 兩支活測試浮現，commit 後兩支皆綠、crossref rc=0）；發現 4590 個
  測試（下限 4543）、wall 161.9s、`[cpu_budget] root-unittest workers=18 source=cpu_budget`、
  `📊 worker=18｜S=2534.2s｜ideal=140.8s（S/W-bound）｜loss=1.00x｜slot 利用率=99.8%｜最長單位
  test_archive_defect_log.TestPlanRejectsRowsWithExternalResidencePointers 131.0s`。
- commit sha：`50042dc`（程式碼＋鎖＋帳本＋本冊；以 `AUTOSDD_NET_RATCHET_OFF=1` 提交、理由寫於
  commit 訊息）＋ `0605b37`（ONBOARDING §7 表② Windows 欄回填：第一次 push 被 pre-push root-infra
  leg 的 `sync_onboarding_baselines.py --check-snapshot` 擋下——autoclaude 測試樹指紋
  7e85a94be029→fdbf8bc16a37 presumed stale；以 `tools/lib/clean_venv_carrier.py` 樹外乾淨 venv 量測、
  psycopg2／sqlalchemy 探針 ABSENT、未用 `--allow-pg-extras`，四棵樹計數不變）。
- **pre-push 三 leg 並行首次真跑憑證**（第一次 push，被 ONBOARDING 擋下但三重 leg 皆已跑完）：
  `[cpu_budget] broadcast workers=18 source=cpu_budget` → `AutoClaude／SDD leg 已轉入背景並行
  （workers=2），root-infra leg 續於前景執行` → root 前景 `發現 4590 個測試` → 回放
  `AutoClaude leg（背景並行 workers=2，wall 192s，rc=0）`（內含 `[cpu_budget] xdist workers=2
  source=env`／`nodes confirmed=2`）、`AISDLC_SDD leg（背景並行 workers=2，wall 195s，rc=0）` →
  `[cpu_budget] parallel legs: root=18 autoclaude=2 sdd=2 wall=195s`；整條 push 197.8s。第二次 push
  （`0605b37`）同形態：AutoClaude 193s／SDD 198s 皆 rc=0、`parallel legs … wall=198s`、
  `✅ 本次 push 觸發的所有 leg 皆通過（rc=0）`、整條 203.6s、`3d3cdc1..0605b37 main -> main`。
  對照序列預估 174.65+30.6+67.5=272.75s ⇒ 真實 push 省約 25%，與 QA-1 E1-b 一致。
- push 後雲端驗收（`0605b37`，主控以 `gh run list --commit`＋`gh run view --log` 親抓）：六支 run 全
  success——root-infra-ci 35955161709／windows-compat-ci 35955161751／macos-compat-ci 35955161707／
  AutoClaude CI 35955161742／aisdlc-sdd-ci 35955161727／shellcheck-ci 35955161710。逐字摘錄：三平台
  根層皆 `✅ unittest 數量下限釘選通過：發現 4590 個測試（下限 4543）`；`[cpu_budget] root-unittest
  workers=4 source=cpu_budget`（ubuntu／windows）與 `workers=3 source=cpu_budget`（macos）；📊 ubuntu
  `worker=4｜S=2631.4s｜ideal=657.9s（S/W-bound）｜loss=1.00x｜slot 利用率=100.0%`、windows
  `worker=4｜S=3770.2s｜ideal=942.5s（S/W-bound）｜slot 100.0%`、macos `worker=3｜S=1987.7s｜
  ideal=662.6s（S/W-bound）｜slot 99.9%`（雲端最長單位皆為 `test_archive_defect_log.
  TestMoveSubsetSelectionIsNamedAndTraceable` 309.2／401.5／232.0s）；AutoClaude CI `[cpu_budget] xdist
  workers=4 source=cpu_budget`→`nodes confirmed=4`；aisdlc-sdd-ci `broadcast workers=4 source=cpu_budget`
  →`xdist workers=4 source=env`→`nodes confirmed=4`；macos SDD 軌 `broadcast workers=3`→`xdist workers=3`
  →`nodes confirmed=3`。**psutil（DEF-200-378）誠實劃界**：windows log 逐字可見
  `Using cached psutil-7.2.2-cp37-abi3-win_amd64.whl`；ubuntu／macos 的 tools/tests 相依 pip 行帶
  `--quiet`，安裝成功只能由「該 step 未紅＋job success」間接推得（pip 裝不到會 fail-loud），且根層
  unittest 非 `-v`，交叉比對測試是否走強判準無逐支可見字串——三平台皆綠只證明「裝了 psutil 後
  `_platform_physical_count()` 與 psutil oracle 在 linux／win32／darwin 三分支逐值一致或弱判準成立」
  這個合取，不能拆開宣稱。
- `python tools/check_defect_log_crossref.py` 本輪（記帳員收工時）現查 rc=1，唯一 ❌ 為淨額棘
  輪：本輪新增 DEF-200-379／DEF-200-380 兩筆 open、0 筆結案，淨增 2 筆。此為合法「發現輪」情
  境（出口②）：commit 前需顯式設定環境變數 `AUTOSDD_NET_RATCHET_OFF=1` 並在 commit 訊息寫明
  理由（本輪修復 6 筆＋新發現 2 筆的淨值計算不計入「修復」抵銷，因為新增即結案的列不算「結
  案」）。其餘輸出（⚠️ 第一冊逼近體積上限、外部阻塞／結構性長債複查逾期、已結列殘留待辦）皆
  為本輪之前既有、與本輪無關，不在本輪處置範圍。

## 系列收斂後四方重驗：掌舵者六問重問（2026-09-25，Windows）

DEF-200-274 系列已於第二十二輪宣告收斂（見上節），本輪非新一輪多 CPU 迭代，而是掌舵者對
已收斂系列的六問重問：①帳本上是否還有多 CPU 問題？②多 CPU 功能是否完備、CI 是否也已多
CPU？③能否全面優化、不要頭重腳輕？④還有哪些面向可以多 CPU？⑤這件事是否已可收斂？⑥前
一輪承諾但未完成的項目是否已補齊？

### 流程與分工

四方角色鏡（Architect／SA／SD／QA）全數 Sonnet 執行，主控 Opus 5.5 只裁決親驗——延續第
二十二輪的分工形態。修復棒（Developer）依複審 P0/P1/P2 逐項落地後，交由本收尾單人窗口
（本檔撰寫者）做記帳（缺陷帳本）、護欄棘輪重釘、計時種子刷新與 ONBOARDING §7 回填四件收斂
工作。收尾階段沒有其他 agent 同時動工作樹（12 支未提交檔已保全為 tag
`multicpu-recheck-20260925-wip3-preserved`）。

### 量測（他包回報，QA-2／QA-3 實測；標✔為本收尾窗口／主控親驗）

**效能剖析熱點修復前後對照**：

| 項目 | 修前 | 修後 | 備註 |
|---|---|---|---|
| `archive_defect_log.plan()` 單次呼叫 | 14.1s（占 cumtime 99.6%） | 0.13s（107x） | O(203×196) 重掃 → 單次索引 `_residence_claims_index()`；輸出逐鍵相等，LOC 淨 0 |
| `TestStrayVenvScan`（5 支） | 25s | 0.37s | 原掃真實 %TEMP%（約 100 萬項），隨機器狀態漂移屬正確性風險，非僅效能 |
| `TestPathextReadsAreePlatformGuarded` | 18.7s | 5.5s | 5930 檔內容 sha256 快取（唯一內容約 1200 種） |
| `test_doc_loc_baseline_freshness_r60` `TestR67R3` 單類 | ~45s | ~30s（單機序列）／~58s（本輪並行下，見誠實劃界） | `measure_loc()` 測試側行程內快取，鍵含 `_LOC_TOOL`／`_REPO_ROOT` |

**根層全套 W=18 wall（他包回報）**：修補前 ~162s → 第一批後 124.7／129.9／129.5s → 全部修補
後 118.65／118.91／118.69s。S ~2534s → ~1740s；最長單位 131s → ~58s（並行下）。

**W 掃描（QA-3，兩輪中位）**：

| W | wall (s) | 整輪 CPU | 前景延遲中位 (ms) |
|---|---|---|---|
| 16 | 128.14 | 72.6% | 37 |
| 18 | 119.13 | 78.9% | 44 |
| 19 | 117.08 | 82.8% | 46 |
| 20 | 115.43 | 82.6% | 57 |
| 22 | 114.62 | 82.1% | 72 |

其餘量測（他包回報）：14 次全套 mktemp／archive flake 0 命中；DEF-200-311 CPU 壓力測試
20/20 綠、全套 I/O 負載下 26/26 綠；AutoClaude 全套 4883 passed／10 skipped、
`nodes confirmed=18`；v0.30 chaos 平行 10/10 綠 ~17s（序列 30s）。

**雲端 CI 多 CPU 憑證（SA 親抓，`0605b37` 批）**：root-infra／AutoClaude／aisdlc-sdd／
windows-compat／macos-compat 五線皆有 `workers=4` 逐字（macos 3）；另 6 支次要 workflow 中
4 支不跑 pytest，`mutation-on-change`／`pg-e2e-on-label` 刻意序列已登記（`pg-e2e-on-label`
近 2.5 個月無雲端 run，屬既有事實非本輪劣化）。

✔ 本收尾窗口親驗：`refresh_parallel_timing_seed.py` rc=0（活體快取 474 個派工單位，種子
Top-15 重疊率 43%＜50% 門檻，已覆寫）；種子刷新前後三支代表單位：
`test_archive_defect_log`（模組鍵）807.78s→105.06s；`test_dev_start.TestStrayVenvScan`
65.92s→1.58s；`test_doc_loc_baseline_freshness_r60.TestR67R3NoUnstatedPlatformAssumption*`
三平台各約 75s→61s。`test_run_root_unittests.py`（`unittest discover -s tools/tests -p
test_run_root_unittests.py`，**必須走 discover 而非裸模組路徑呼叫**——後者因
`__name__` 前綴不同導致 4 支自我參照鎖假紅）：223 tests，`Ran 223 tests in
71.360s`，`OK`，rc=0。

✔ 本收尾窗口親驗：`test_ci_gate_xdist_allowlist.py`（`unittest discover`）13 tests OK；
現查 pytest 呼叫站點普查（`_all_sites()` 現場執行）共 **38** 站點——**SERIAL 19／
PARALLEL 19／登記 19 列／UNGOVERNED 0**（普查補掃 `tools/integration_gate_core.py`／
`AutoClaude/tools/run_mutmut_in_docker.sh` 兩處，`run_mutmut_in_docker.sh` 已補
`-p no:xdist`，標示與行為一致）。

✔ 本收尾窗口親驗：`python tools/check_defect_log_crossref.py` rc=0，本輪新引入 ❌ 為零
（詳見下方〈帳本更新〉）。

### 設計裁決

**掌舵者三項裁決（2026-09-25）**：

1. **DEF-200-379**＝LATEST chaos 加軌＋觀察期（紅要出聲、不計入 Rule 9.9.4 連 3 日失敗鎖
   main）：`aisdlc-sdd-fsm-chaos-nightly.yml` 新增 `chaos-latest` job；`track-streak-and-lock`
   的連敗計數改讀**job 層**（`GATING_JOB_NAMES`），排除 run 層被 `chaos-latest` 污染的風
   險（三方複審一致命中的 P0）；觀察期＝首次排程 run 起連續 7 次，最早 2026-10-03 起由掌
   舵者裁決是否把 `chaos-latest` 併入 `GATING_JOB_NAMES`（見缺陷帳本 DEF-200-381）。
2. **護欄棘輪＝核准一次性例外**（名冊上限 3→4）：本輪四方複審要求的結案回歸鎖與自證測試
   ＋測速修補淨額為正，且前兩輪已連續兩次淨額為正（款(11) 要求主軌 ≤0），本輪需要第三次
   例外核准，理由見〈護欄層行數棘輪重釘〉。
3. **整輪 CPU 標準＝70～80% 即符合**（非硬性 ≥80%）：W=18 實測 78.9%，落在此帶內即達標，
   **W 維持 18**、公式不變。

**W 維持 18 的理由**：W 掃描顯示 16→22 之間 wall 差距僅 128.14s→114.62s（−10.6%），而 CPU
利用率在 18～20 一帶已進入平坦帶（78.9%／82.8%／82.6%）；掌舵者本輪明確放寬標準為
70～80%，W=18 的 78.9% 已達標，且 W=18 是第二十二輪已定案、已同步進根層測試鎖
（`test_run_root_unittests.py` 的 W 值鎖）與 nightly baseline 的既有值，改動 W 會牽動已重
釘的護欄棘輪與 nightly perf baseline（commit `f720ca6`），對「不要頭重腳輕」（掌舵者第三
問）而言，維持既有值＋把力氣放在測試熱點修復上，投入產出比更高。

**主控否決「measure_loc 快取放正式碼」**：`tools/tests/test_doc_loc_baseline_freshness_r60.py`
的區塊註解逐字記載理由——`sync_onboarding_baselines.py`（`measure_loc()` 本體所在）在根
CLAUDE.md `SPECIAL_FILES` 精確釘行數，且正式 CLI 每次執行只呼叫一次，放正式碼零效益；快
取只應存在於「本檔測試在同一行程生命期內對同一 repo 內容重複呼叫」這個測試專屬情境，
`measure_loc()`／`measure_all()` 本體維持每次真跑，不引入生產路徑的陳舊風險。

### 逐檔改動（他包回報，主控裁決收斂；詳細診斷過程另見缺陷帳本 DEF-200-381～385）

- `tools/archive_defect_log.py`：`_residence_claims_index()` 單次建索引，取代逐候選列×逐
  稽核檔的 O(203×196) 重掃；LOC 淨 0。
- `tools/tests/test_archive_defect_log.py`：`_stable_snapshot_bytes()`（讀前後 stat＋長度核
  對、重試、fail loud）＋自證測試 4 支；`_residence_claims_index` 正樣本 6 支（(乙) 術語提
  及分支經證明從此呼叫端結構上不可觸發，未寫假樣本，見誠實劃界）。
- `.github/workflows/aisdlc-sdd-fsm-chaos-nightly.yml`：新 job `chaos-latest`（LATEST 由
  `sdd_version.py` 現查、xdist 走 cpu_budget 字串鏈、100 輪 sweep）；
  `track-streak-and-lock` 改讀 job 層。
- `tools/tests/test_workflow_permission_concurrency_lock.py`：
  `TestFsmChaosNightlyStreakReadsJobLayer` 7 支鎖。
- `AutoClaude/tools/run_local_nightly.ps1`：Stage 6b LATEST chaos（`sdd_chaos_latest` 欄位；
  `sdd_version` rc≠0 fail loud；觀察期註記）。
- `AutoClaude/tests/tools/test_run_local_nightly_static.py`：姊妹鎖同步。
- `tools/tests/test_ci_gate_xdist_allowlist.py`：普查補掃 `tools/integration_gate_core.py`、
  `AutoClaude/tools/run_mutmut_in_docker.sh`（現查共 38 站點）。
- `AutoClaude/tools/run_mutmut_in_docker.sh`：加 `-p no:xdist`，標示與行為對齊。
- `tools/tests/test_dev_start.py`：`TestStrayVenvScan` 5 支隔離真實 %TEMP%。
- `tools/tests/test_platform_neutral_paths.py`：`TestPathextReadsAreePlatformGuarded` 內容
  sha256 快取。
- `tools/tests/test_doc_loc_baseline_freshness_r60.py`：`measure_loc()` 測試側行程內快取
  （見上方設計裁決）。
- `tools/tests/test_block_destructive_git_r83.py`：模組級釘 `CLAUDE_PROJECT_DIR`＋`fs_root`
  改 `_REPO_ROOT.anchor`＋回歸鎖 `TestResultDoesNotDriftWithCallerCwd`。

### 驗證數字（彙整）

- 他包回報：根層全套 W=18 wall 修補前後對照與 W 掃描表（見上）；AutoClaude 全套 4883
  passed／10 skipped；v0.30 chaos 平行 10/10 綠。
- ✔ 主控親跑一次收尾全套：rc=1，唯一非預期紅為 `test_adr_xplat001_c1c2_lock` 3 支**預期**
  紅（棘輪重釘前的過渡態）；發現 4607 個測試；wall 129.7s。
- ✔ 主控親自重現：`test_block_destructive_git_r83.py` 從 `C:\` 這類 repo 外 cwd 執行時固定
  9 支假紅（改前）；改後兩種 cwd 下結果一致（他包回報＋回歸鎖 `TestResultDoesNotDriftWithCallerCwd`）。
- ✔ 本收尾窗口親驗：見上方〈量測〉區塊逐項（種子刷新、`test_run_root_unittests.py` 223
  tests OK、`test_ci_gate_xdist_allowlist.py` 13 tests OK、站點普查 38、
  `check_defect_log_crossref.py` rc=0）。

### 四方複審摘要

Architect／SA／SD／QA 四方獨立複審皆 **APPROVE-WITH-FIXES**。所有 P0／P1／P2 已由修復棒
C 處理完畢（含 DEF-200-379 的 job 層連敗隔離 P0、`chaos-latest` LATEST 版本現查 P1 等）。
P3（CI 分片、其餘尚未剖析的熱點）列入下方誠實劃界，不在本輪處置範圍。

### 訂正上一輪（第二十二輪）兩處記載

1. 本檔 L257 與 L296（`tools/tests/test_ci_gate_xdist_allowlist.py` 的站點普查計數）記載有
   誤；正確值以本輪現查為準——現查（`_all_sites()` 現場執行）共 38 站點，SERIAL 19／
   PARALLEL 19／登記 19 列／UNGOVERNED 0（見上方〈量測〉）。
2. 本檔 L361-363 稱「argmin 鎖 `abs(公式值−argmin)≤1` 已固化為回歸測試」——本輪現查
   `tools/` 全樹（`git grep`）找不到任何名為 argmin 的回歸鎖；`test_cpu_budget.py` 實際只
   釘公式輸出值與拓撲輸入的對應關係（換算值鎖），並不存在「與逐一掃描 argmin 做差值比
   對」的鎖。此訂正僅描述兩者的落差，不重述原句字面。

### 收斂判定（掌舵者六問逐一核對）

1. **①帳本多 CPU 問題**：DEF-200-311（偶發 flake，未重現≠已修，維持 open 並補本輪證
   據）、DEF-200-379（已 fixed，觀察期另立 DEF-200-381 追蹤）、DEF-200-380（已 fixed）為
   本輪涉及的三筆；另因本輪工作新增 DEF-200-382～385（4 筆 fixed）與 DEF-200-381（1 筆
   open，觀察期性質，非程式缺陷）。帳本上不再有「未經評估」的多 CPU 問題。
2. **②多 CPU 完備＋CI 多 CPU**：五條雲端 CI 主線（root-infra／AutoClaude／aisdlc-sdd／
   windows-compat／macos-compat）皆有 `workers=N` 可稽核逐字；`chaos-latest` 補上 LATEST
   版本的雲端／本機覆蓋缺口（觀察期中，非「未做」）。
3. **③全面優化、不要頭重腳輕**：本輪明確以「頭重腳輕」為篩選條件抓出 archive_defect_log
   單一熱點（99.6% cumtime）與三支測試熱點並修復，未觸及已平坦（16～22 差距 <11%）的 W
   政策本身，符合掌舵者「不要頭重腳輕」的字面要求。
4. **④其他可多 CPU 面**：普查站點掃描面補齊（38 站點，0 UNGOVERNED）；CI 分片等 P3 項目
   列入誠實劃界，判定「已知、暫不值得做」而非「未評估」。
5. **⑤是否收斂**：**是**——本輪是系列收斂後的重驗，未發現需要重啟系列或推翻第二十二輪收
   斂宣告的證據；六問皆有明確答覆與證據，剩餘唯一 open 項（DEF-200-381）屬觀察期追蹤性
   質，解鎖條件與時間點皆已明定，不構成「收斂宣告不成立」的理由。
6. **⑥完成前輪未完成項**：DEF-200-379／380 兩筆前輪 open 項本輪皆已 fixed；前輪〈待主控
   回填〉已於 commit `50042dc`／`0605b37` 落地（見上節，非本輪工作）。

**廣義收斂條件**：帳本無新增「未評估」多 CPU 問題、CI 多 CPU 覆蓋五線可稽核、效能熱點已
篩選並修復頭重腳輕項、剩餘缺口皆有具名解鎖條件。本輪判定五條皆已滿足，**系列維持收斂狀
態**（不重啟為新一輪多 CPU 迭代），DEF-200-381 觀察期追蹤獨立於系列收斂判定之外。

### 🔴 誠實劃界

- **CI 分片未做**：Architect 本輪重新評估（`gh repo view --json visibility` 現查＝PUBLIC，
  GitHub-hosted runner 免費、無 OS 分鐘倍率），root-infra unittest 切 matrix shard 理論上可把
  雲端該步驟壓到 ideal/N，但需新設每 shard 的 MIN_TESTS 下限與跨 shard 彙總機制，本輪未落地
  （HYPOTHESIS，未實測）；且本輪 S 已降約 31%，收益同比縮小。mutmut 平行被 `pyproject.toml`
  鎖 2.4.3 的 CLI 不相容（3.x 移除 `--paths-to-mutate`／`--tests-dir`）擋住；TLC 已
  `-workers auto`；chaos 100 輪 sweep 規模約 30s，行程池固定成本攤不平——三者維持不做。
- **收尾第一次全套 wall 141.6s／slot 80.3%（loss 1.24x）是一次性排程現象**：單一類別模組
  `test_extras_quoting_zsh_safety` 本輪被細分成類別級單位、換了快取鍵而暫無歷史耗時，依測試
  數排序排得太晚成為尾巴（第 120.9s 完工）；隔一次全套即有基準，第二次全套 wall 119.3s、
  `loss=1.00x`、slot 99.7%。
- **種子過期警告與刷新工具矛盾**（DEF-200-386，open）：剛執行 `refresh_parallel_timing_seed.py`
  後的兩次全套仍印 Top-15 重疊率 36%／43%，兩處重疊率的比較面不同，本輪未修。
- **CI paths 缺口於回填時才被抓到**：修復棒 C 新增的 `TestFsmChaosNightlyStreakReadsJobLayer`
  讀 `aisdlc-sdd-fsm-chaos-nightly.yml`，但 windows／macos-compat-ci 的 `paths:` 未列該檔，由
  `AISDLC_SDD/scripts/tests/test_ci_paths_cover_root_consumers.py` 在 ONBOARDING 回填的
  `--write --with-slow` 步驟擋下；主控補列兩支 workflow 各兩段後該檔 49 passed。本機根層／
  AutoClaude 全套結構上抓不到這類缺口（只在 SDD ci-gate 跑到）。
- **`TestR67R3` 單類在並行下 58s、非單機序列 30s**：測試側行程內快取只消除同一行程內重複
  子行程呼叫的成本；並行環境下多個 worker 各自起一份行程，快取效益不跨行程共享，故並行
  wall 仍高於單機序列量測值。
- **`pg-e2e-on-label` 無雲端 run**：近 2.5 個月無 dispatch 紀錄，本輪未新增驗證，沿用既有
  事實記載。
- **W 掃描只在 14P/20L 本機拓撲**：本輪未對其他拓撲重新掃描，W=18 的決策僅在本機實機拓撲
  上有實測支持。
- **觀察期尚未開始**：DEF-200-381 的 7 次排程 run 判定窗口本輪僅完成程式與鎖落地，尚無任
  何一次 `chaos-latest` 排程 run 的雲端資料。
- **DEF-200-311 未重現≠已修**：CPU 壓力 20/20、I/O 負載 26/26 皆綠僅代表本輪未命中，不構
  成根因已排除的證據，解鎖條件維持不變。
- **(乙) 分支不可觸發**：`_residence_claims_index` 的術語提及分支經證明從現有呼叫端結構上
  不可達，本輪未為其撰寫假樣本測試（避免為不可達路徑製造誤導性的「已覆蓋」假象）。
- **普查站點數僅涵蓋 `_CENSUS_TARGETS` 具名清單**：新增呼叫站點若未同步登記進該常數，仍會
  在普查掃描面外，本輪未做「掃描面本身是否窮盡」的獨立驗證。

### 待主控回填

- 收尾全套 rc（主控親跑，帳本／棘輪／ONBOARDING 回填落地後、commit 前）：兩次皆 rc=0、
  `發現 4608 個測試（下限 4543）`、`[cpu_budget] root-unittest workers=18 source=cpu_budget`；
  第一次 wall 141.6s（一次性排程現象，見誠實劃界）；第二次 wall 119.3s、`📊 派工摘要：
  worker=18｜S=1773.2s｜ideal=max(S/W, 最長單位)=98.5s（S/W-bound）｜loss=1.00x｜slot 利用率=
  99.7%｜最長單位：test_doc_loc_baseline_freshness_r60.TestR67R3NoUnstatedPlatformAssumptionDarwin
  58.4s`。ONBOARDING §7 以 `tools/lib/clean_venv_carrier.py` 回填（psycopg2／sqlalchemy
  ABSENT、pip rc=0、`--write --with-slow` rc=0；autoclaude 4688 passed／172 skipped、v0.01 1478、
  v0.30 1956、scripts/tests 364），`--check-snapshot` rc=0；`check_defect_log_crossref.py` rc=0。
- commit sha：`f720ca6`（2026-09-24 nightly perf baseline 重鎖）＋ `ccd4227`（本節全部改動）。
  push：`d26d4c0..ccd4227  main -> main`，整條 164.2s；pre-push AutoClaude leg `4884 passed, 10 skipped`
  （背景並行 workers=2，wall 153s，rc=0），`✅ 本次 push 觸發的所有 leg 皆通過（rc=0）`。本次 SDD leg
  **未觸發**（本輪未動 `AISDLC_SDD/`），憑證行卻印 `sdd=2` ⇒ 收尾後追加 DEF-200-387（下）。
- push 後雲端驗收（`ccd4227`）：shellcheck-ci 36089796074 success；**AutoClaude CI 36089796062 failure**
  ——`PG Contract Tests` 的 alembic 步驟 `ModuleNotFoundError: No module named 'psycopg'`，同一 job
  安裝行逐字 `sqlalchemy-2.1.0`／`psycopg2-binary-2.9.13`／`alembic-1.20.0`（本機 2.0.51／1.19.0），
  前一次 `0605b37` 同 job success ⇒ 外部依賴漂移，與本節 diff 無關 ⇒ 收尾後追加 DEF-200-388（下）；
  其餘四支 success，主控以 `gh run view --log` 親抓逐字：三平台皆 `發現 4608 個測試（下限 4543）`；
  root-infra 36089796040 `[cpu_budget] root-unittest workers=4 source=cpu_budget`、`📊 派工摘要：
  worker=4｜S=1337.1s｜ideal=max(S/W, 最長單位)=334.3s（S/W-bound）｜loss=1.00x｜slot 利用率=100.0%`；
  windows-compat 36089796089 `worker=4｜S=2125.3s｜ideal=…=531.3s（S/W-bound）｜slot 99.9%`；
  macos-compat 36089796003 `worker=3｜S=1052.2s｜ideal=…=350.7s（S/W-bound）｜slot 99.8%`。對照上一節
  `0605b37`：ubuntu S 2631.4→1337.1s、ideal 657.9→334.3s（−49%）；windows 3770.2→2125.3s、
  942.5→531.3s（−44%）；macos 1987.7→1052.2s、662.6→350.7s（−47%）——雲端 W 只有 3～4，同一個 S
  瘦身換成 wall 的收益遠大於本機（Architect 的雲端重算判斷由此實證）。
- 手動 dispatch `aisdlc-sdd-fsm-chaos-nightly`（run 36090379807，`ccd4227`）：success；
  `fsm-runtime chaos suite` success（凍結基線 `34 passed, 1482 deselected in 25.57s`、
  `bounded=100/100`）；`fsm-runtime chaos suite (LATEST track — observation period, DEF-200-379)`
  success（`Using LATEST version=AISDLC_SDD_v0.30`、`[cpu_budget] broadcast workers=4 source=cpu_budget`、
  `[cpu_budget] xdist workers=4 source=env`、`[cpu_budget] xdist nodes confirmed=4`、`34 passed in 11.41s`、
  `bounded=100/100 avg_tokens=1504.8 max_steps=12`）；`enforce 3-day streak lockdown` skipped（如設計：
  只在 `chaos` 失敗時執行）。此為 workflow_dispatch，不計入 DEF-200-381 的 7 次**排程** run。
- **收尾後追加（第二個 commit）**：
  - DEF-200-387：`tools/git-hooks/pre-push` 憑證行改依觸發狀態印 worker 數（0＝未觸發）；
    `test_pre_push_dispatcher` 兩 leg 測試改逐字斷言 `root=0 autoclaude=2 sdd=2 wall=`，主控突變
    自證：還原舊寫死行 ⇒ 該支 FAIL（37 支中 1 支），改回 ⇒ `Ran 37 tests … OK`。
  - DEF-200-388：`AutoClaude/pyproject.toml` 釘 `sqlalchemy>=2.0,<2.1`（CI 由 pyproject extras 安裝，
    `pip install -e ".[dev,postgres,pgvector]"`）；解除上限前須先把 strip `+asyncpg` 的各處改顯式
    `+psycopg2`（寫在該行註解）。
- `AUTOSDD_NET_RATCHET_OFF` 是否需要設定：不需要（結案 DEF-200-379／380，新增 open 僅
  DEF-200-381／386，其餘新列建立即 fixed；`check_defect_log_crossref.py` rc=0）。

## Windows console 洩漏事故（2026-09-25）

修復棒 F 事故輪：本機累積大量孤兒 console 行程拖垮機器，主控定位根因＋修復＋三道鎖，
收尾單人窗口（本節撰寫者）複審親跑重現並修復複審抓到的兩個 P1。本節事實面（時間線、
量測數字、SD／QA 雙證逐字）由主控彙整交棒；P1-1／P1-2 的重現與修復為本節撰寫者親驗。

### 時間線與症狀

本機累積 **630 個 `OpenConsole.exe -Embedding`**（父行程 svchost）＋**630 個孤兒
`conhost.exe`**（父行程已死）＋一個 **8196 handle** 的 Windows Terminal，約 **9GB**，
機器被拖垮；主控已全數清除（清後 OpenConsole＝0、孤兒 conhost＝0、WT＝0）。成簇時段：
09-25 01:10～01:14、02:22～02:56、08:18、11:06～11:39，每簇約 29～36 個，逐一對得上
當時的根層全套（含主控親跑與兩次 push 的 pre-push 根層 leg）。

### 根因（SD 靜態＋QA 動態雙證）

Windows 11 以 Windows Terminal 為預設終端時，父行程無 console（`pythonw.exe`）而
console 子行程沒帶 `CREATE_NO_WINDOW` ⇒ Windows 替它新配置一個 console ⇒ svchost 起
`OpenConsole.exe` 交接；有 WT 視窗開著時被收成分頁長期不散。

- **SD 靜態**：站點＝`AISDLC_SDD/scripts/sdd_version.py::tracked_version_dirs()` 內
  裸 `subprocess.run(["git", …])` 零 creationflags，經
  `tools/lib/sdd_latest.py::resolve_latest_root_fast()` 以 `importlib.util.
  spec_from_file_location` 動態載入呼叫——這條邊對任何靜態 import 掃描結構性隱形。呼叫
  鏈：`.claude/hooks/context_budget_guard.py` 與 `tools/session_resume_planner.py`（
  `main()` 內 `measure()` 以 `session_id=None` 呼叫，永不快取）→ `harness_feed.measure()`
  → `guard.window_evidence(session_id=None)` → `known_model_windows_path()` →
  `sdd_latest.resolve_latest_root_fast()` → 動態載入 `sdd_version.py` →
  `tracked_version_dirs()` 內那個裸 `subprocess.run`。測試觸發者＝
  `test_context_budget_guard.py::QuotaGateIsIndependentOfContextTest`（真呼叫
  `write_resume_plan()`）與 `NoWindowBehaviourTest` 的 `flags=0` 負對照案例（見下節）。
- **QA 動態**：以 `Register-CimIndicationEvent` 建立即時行程建立事件監看器
  （`__InstanceCreationEvent`，`WITHIN 0.2`），只認 `OpenConsole.exe`／
  `WindowsTerminal.exe`，正反兩例自證：拿掉 `sdd_version.py` 的 creationflags 後監看器
  立即抓到兩者的建立事件；補回旗標後 0 事件。QA 另實測 `pythonw.exe
  session_resume_planner.py --check` **1 秒內**即觸發 OpenConsole＋WT ⇒ 正式 session
  中額度守衛擋扇出、寫任務書／武裝哨兵時**也會中**（`PlannerCheckIsConsoleFreeTest`
  行為鎖鎖住這條路徑，見下節）。

### 主控的兩個錯判與訂正

1. **量存量的假陰性**：第一版逐支實驗只量「每支跑完後存量」，而沒有 WT 視窗開著時，
   交接出的 `OpenConsole.exe` 會隨呼叫端結束而消失，量不到；改用即時事件監看器
   （`_LIVE_CONSOLE_WATCH_PS1`）才抓到——同一支 `sdd_version.py` 缺旗標的缺陷，快照
   差集法回報「無新增」，同一秒改用即時監看器立刻抓到建立事件。
2. **`Start-Job` 推測被推翻**：原推測「`Start-Job` 無 console」，實測 `Start-Job` 與
   本工具殼一樣是「有 console、無視窗」，不是無 console 父行程，推測不成立。

另：QA-1 曾以 `Start-Process -WindowStyle Hidden` 起 16 個燒機行程；WT 為預設終端時
`Hidden` 無效，一樣彈出 16 個分頁——`-WindowStyle Hidden` 這個常見「防彈窗」手法在
WT 預設終端下**不可靠**，不得作為修法。

### 修復與三道鎖

**三處補 `CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP`**：`sdd_version.py`（
`tracked_version_dirs()`）、`sdd_latest.py`（非 fast 版 `resolve_latest_name()`）、
`tools/lib/git_paths.py::run()`——後者為修復棒 F 盤點鄰居站點時新揪出的同型缺陷
（`planner → relay_machine → git_paths` 這條鏈同樣由無 console 的 pythonw 呼叫）。

**負對照改用 `STARTUPINFO(SW_HIDE)`**：`ConsoleFreeSpawnTest` 的內層行為探針
（`_BEHAVIOUR_PROBE`）對本來就刻意不帶 `NO_WINDOW` 的「none」負對照案例額外套
`STARTUPINFO(STARTF_USESHOWWINDOW, wShowWindow=SW_HIDE)`——對 `GetConsoleWindow()`
這個探針要量的存在性訊號零影響，但讓這個負對照不再把 console 升級交給 WT 的
`OpenConsole.exe`／`WindowsTerminal.exe` 承載。實測：不帶時每次跑 flags=0 皆觸發二者
建立事件；帶了之後三次隔離重跑 0/3 觸發（其中一次仍生一個會自行收尾的
`conhost.exe`，非本輪判準射程——射程只守 `OpenConsole.exe`／`WindowsTerminal.exe`）。

**三道鎖**（皆帶改壞會紅自證）：

1. `ConsoleFreeSpawnTest`（`tools/tests/test_context_budget_guard.py`）掃描面擴大到
   pythonw 可達的全部模組（含本次三個新站點，`_CONSOLE_FREE_FLOOR` 由 11 上修到 30），
   並新增 `spec_from_file_location_problems()`：任何 `importlib.util.
   spec_from_file_location` 動態載入目標檔都必須能在掃描面裡找到同名檔，否則獨立紅
   （`test_every_reachable_dynamic_load_target_is_registered`；本輪修復前會紅，因
   `sdd_latest.py` 動態載入 `sdd_version.py` 而後者當時不在掃描面）。
2. `PlannerCheckIsConsoleFreeTest`（同檔）：行為鎖，以即時 WMI 事件監看實跑
   `pythonw.exe session_resume_planner.py --check`，拿掉旗標即紅。
3. `tools/run_root_unittests.py` 經新檔 `tools/lib/console_orphan_census.py` 在全套
   unittest 開始前／結束後各盤點一次孤兒 console（`OpenConsole.exe` 不論父行程是誰；
   父行程已消失的 `conhost.exe`），結束後比開始多即列印 ❌。**advisory（只出聲、不判
   紅 rc）**：使用者自己在執行窗口內開一個新 WT 分頁會被算成「新增」而誤判，這個風險
   不可忽略且無法從外部區分，讓一次巧合操作擋下整條 push 的代價比漏抓一次孤兒累積更
   高（見該檔 docstring 的假紅風險評估）。

**驗收**：三次全套 OpenConsole／WindowsTerminal 建立事件監看＝0。

### 獨立複審與兩個 P1（本節撰寫者親驗修復）

獨立複審結論：**APPROVE-WITH-FIXES**，兩個 P1 已親自重現；P2＝
`AISDLC_SDD/AISDLC_SDD_v0.30/tools/fsm_runtime/{hub_sync,sandbox_runner,tlc_runner}.py`
的 subprocess 呼叫無旗標，不在本次事故的 hook 熱路徑上（登記誠實劃界，本輪不修）。

- **P1-1**（帳本 DEF-200-390）：`tools/lib/git_paths.py` 頂層 `from win_spawn import
  NO_WINDOW`，在僅 `tools/` 於 `sys.path`（未含 `tools/lib`）的消費端下
  `ModuleNotFoundError`。親跑重現：`test_negative_existence_claims_r82.py` 單獨跑
  `Ran 1 test … FAILED (errors=1)`（`ModuleNotFoundError: No module named 'win_spawn'`）。
  修法：移除該 import，改內聯 `getattr(subprocess, "CREATE_NO_WINDOW", 0) |
  getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)`，循 `sdd_version.py`／
  `sdd_latest.py` 既有先例（`win_spawn.py` 檔頭自陳「刻意不提供 fallback stub」，代價
  由此類跨 sys.path 消費端的 import 形態吸收）。修後：
  `test_negative_existence_claims_r82.py` `Ran 12 tests … OK`；
  `test_doc_loc_baseline_freshness_r60.py` `Ran 281 tests in 105.794s … OK`；
  `test_context_budget_guard.py` `Ran 667 tests in 97.856s … OK (skipped=1)`（
  `no_window_problems()` 判準只認字面含 `NO_WINDOW` 子字串，`CREATE_NO_WINDOW` 天然
  命中，鎖本身不需改動）。全庫 Grep 確認 `tools/lib/` 下只有 `git_paths.py`／
  `console_orphan_census.py` 兩處 `from win_spawn import`，後者本就有
  `try/except ImportError: NO_WINDOW = 0` 防禦，無同型漏網。
- **P1-2**（帳本 DEF-200-389 一併登記）：新檔 `tools/lib/console_orphan_census.py`
  未列入 `.github/workflows/windows-compat-ci.yml`／`macos-compat-ci.yml` 的
  `paths:`（push／pull_request 各兩處），而 `tools/tests/test_run_root_unittests.py`
  頂層 `import console_orphan_census`。親跑重現：
  `AISDLC_SDD/scripts/tests/test_ci_paths_cover_root_consumers.py` `2 failed, 47
  passed`（`根層消費檔未列入 {windows,macos}-compat-ci.yml paths`）。修法：兩份
  workflow 的 push／pull_request 區塊各補一行 `tools/lib/console_orphan_census.py`
  （比照 `tools/lib/onboarding_snapshot_note.py` 等相鄰條目的位置與註解風格）。修後：
  同一測試 `49 passed`。

### 🔴 誠實劃界

- **advisory 普查不擋 rc 的理由**：`console_orphan_census.py` 的孤兒偵測在使用者於
  執行窗口內自行開新 WT 分頁時會假紅，且無法從外部區分「使用者操作」與本 repo 的
  bug；讓巧合操作擋下整條 pre-push／CI 的代價高於漏抓一次孤兒累積、留到下次才被發現
  ——見該檔 docstring。若要升級為阻斷級，建議先量測本判準在真實 pre-push 使用下的
  誤判率，而非現在就用直覺猜一個門檻。
- **`STARTUPINFO(SW_HIDE)` 只在本機驗證**：三次隔離重跑皆在本機（有桌面、有 WT）進行；
  CI runner／無 WT 或無桌面環境的機器上是否同樣有效，**未驗**。
- **v0.30 fsm_runtime 三支未修**：`hub_sync.py`／`sandbox_runner.py`／
  `tlc_runner.py` 的 subprocess 呼叫仍缺 creationflags，獨立複審認定其不在本次事故的
  熱路徑（不由無 console 的 pythonw／CC hook 直接觸發），本輪不修、不追加帳本 open
  列——僅在此登記，若未來這幾支被納入無 console 父行程的呼叫鏈，須回頭補旗標。
- **WMI `WITHIN 0.2` 顆粒度**：即時事件監看以 0.2 秒為輪詢粒度，極短命（<0.2s）的
  console 建立-銷毀理論上可能漏抓，本輪未針對此邊界另行驗證。
- **`test_install_windows_nightly` 的 WhatIf 那支測試曾在並行下紅一次**：單獨重跑
  3/3 綠，未深入根因；與本次事故的因果關係未確認，僅記錄不追加缺陷列。
- **全套層普查成功時不出聲**：`console_orphan_census.report_delta()` 只在「開始前已有
  孤兒」印 ⚠️、「執行期間新增」印 ❌，零增長時沒有任何輸出行 ⇒ log 裡無法區分「普查
  跑了且乾淨」與「普查沒被執行」，本輪以外部監看器的建立事件統計補證（見下）。

### 待主控回填

- 主控收尾全套（修復棒 F＋收尾窗口改動落地後、commit 前）：`& .venv\Scripts\python.exe
  tools\run_root_unittests.py` rc=0、wall 131.3s、`發現 4617 個測試（下限 4543）`、
  `[cpu_budget] root-unittest workers=18 source=cpu_budget`、`📊 … S=1872.8s｜
  ideal=…=104.0s（S/W-bound）｜loss=1.00x｜slot 利用率=99.7%`；log 無 ⚠️／❌ 普查行。同時
  以 `console_qa/watch_console.ps1`（WMI `__InstanceCreationEvent WITHIN 0.2`）監看
  22:04:11～22:09:11 完整涵蓋全套：行程建立事件 2964 筆（python.exe 1269／git.exe 728／
  bash.exe 564／conhost.exe 266／powershell.exe 65／pythonw.exe 42／cmd.exe 23／cscript.exe 4／
  pwsh.exe 3），**OpenConsole.exe＝0、WindowsTerminal.exe＝0**；跑完現查 OpenConsole＝0、
  WindowsTerminal＝0、孤兒 conhost（父已死）＝0。對照事故前每次全套約 29～36 組洩漏。
- commit sha／push：`f901721`（本節上述修復三道鎖落地後的 commit，已 push）。
- 雲端驗收（windows-compat-ci／macos-compat-ci 兩支 workflow 因本節新增 paths 條目
  是否觸發、`test_ci_paths_cover_root_consumers.py` 雲端結果）：（留白）

### f901721 雲端驗收與後續修補

- **三支 CI 對 `f901721` 全紅，主控擷取 log 逐字歸因**（`ci3_root_full.log`／
  `ci3_mac.log`／`ci3_win.log`，皆為當場真 GitHub run 輸出）：
  - `root-infra-ci`（ubuntu）：`[M6 id 集合] tools/tests@linux：❌ 集合關係被破壞（本次
    skip 83 支）` — `落款缺 ['test_context_budget_guard.PlannerCheckIsConsoleFreeTest.
    test_planner_check_does_not_spawn_a_visible_terminal']`；另一支獨立紅：
    `FAIL: test_pre_push_dispatcher.TestPrePushDispatcher.
    test_two_legs_trigger_parallel_segment_with_headers_and_marker_line`
    （`AssertionError: 1 != 0`），即 DEF-200-392 的 SIGPIPE 競態。
  - `macos-compat-ci`：`[M6 id 集合] tools/tests@darwin：❌ 集合關係被破壞（本次 skip
    47 支）`，同型落款缺口（新測試尚未落款進 `skip_id_ledger.json` 的 darwin 剖面）。
  - `windows-compat-ci`：`[M6 id 集合] tools/tests@win32：❌ 集合關係被破壞（本次 skip
    44 支）`；且逐字印出該測試的 skip 理由：`[已標籤 [ENV-DISABLED]]
    test_context_budget_guard.PlannerCheckIsConsoleFreeTest.
    test_planner_check_does_not_spawn_a_visible_terminal`／`理由：[ENV-DISABLED]
    本機解不出任何逐字稿`——證實新增的行為鎖在乾淨 CI runner 上結構上必經
    `resolve_transcript(None, None) is None` 那一支，從未真正執行過。
  - 三支同紅的共通根因＝落款檔（`skip_id_ledger.json`）未跟著本節新增的
    `PlannerCheckIsConsoleFreeTest` 同步三個剖面，而非各自獨立的新缺陷；SIGPIPE 那一支
    是並存的第二個根因（見 DEF-200-392）。
- **本機結構性盲區**：本機（win32）跑 `tools/run_root_unittests.py` 只能現查
  `tools/tests@win32` 一個剖面的 M6／S3 結果，darwin／linux 兩個剖面的落款是否同步
  必須等真雲端 run；本機看不到、也不該假裝看得到。
- **修復棒 G 的處置＝落款三剖面補齊＋豁免**：darwin／linux 兩剖面補上該測試的
  `[WINDOWS-NATIVE-ONLY]` 必然互補 skip（platform 群 ceiling 同步上修），SIGPIPE 以
  here-string 修法解決（DEF-200-392）；但 win32 剖面選擇用 `_M6_EXEMPT` 豁免這支測試
  的 `[ENV-DISABLED]` 落款漂移，而不是修掉造成漂移的根本原因。
- **主控否決該豁免，理由**：`_M6_EXEMPT` 只能讓 M6 判準不再報漂移，改變不了「這支
  防 console 洩漏事故（DEF-200-389）再犯的行為鎖在 windows-compat-ci 上，因
  `resolve_transcript(None, None)` 解不到真逐字稿而永遠 `[ENV-DISABLED]` skip、從未
  真正執行」這個事實——豁免掩蓋的正是防護本身失效。
- **修復棒 H（DEF-200-393）的修法**：改用 `tempfile` 合成逐字稿（`_write_jsonl`）＋
  顯式 `--transcript <path>` 餵給 `pythonw session_resume_planner.py --check`，繞開
  `resolve_transcript` 對「機台上是否真有一份 Claude Code 逐字稿」的依賴——`measure()`
  仍無條件走到 `guard.window_evidence()` 那條裸 `git ls-files` 子行程（事故路徑不變，
  只是不再需要真逐字稿才能踩進去）。移除 `_M6_EXEMPT` 第 4 筆與
  `skip_id_ledger.json` win32 剖面的該筆登記（該測試在 win32 上不再 skip、會真跑）。
  **突變自證**：暫時拔掉 `AISDLC_SDD/scripts/sdd_version.py` 的 `creationflags`
  ⇒ 本機真跑該測試紅、逐字列出觸發的 `OpenConsole.exe`／`WindowsTerminal.exe`
  建立事件；改回後綠。

### 🔴 主控訂正：先前「全套期間 OpenConsole＝0」的量測覆蓋不完整

`console_qa/watch_console.ps1` 對**每一筆**事件再做兩次 `Get-CimInstance` 查父／祖父行程，
處理速率約每秒 7～8 筆，遠低於全套的行程建立速率 ⇒ 事件在佇列積壓、到期限時未處理的
**直接丟棄**，且記錄的 `at` 是處理時間而非建立時間。實證：同一支全套在它之下記到
**0 筆 pythonw**，而改用 WMI 端過濾版（下）記到 72 筆。故本節上方與 `f901721` commit
訊息中「2964 筆／OpenConsole＝0」「push 期間 4300 筆／0」、以及修復棒 F 的「三次全套建立
事件＝0」皆**覆蓋不完整、不得作為修補有效的證據**（單獨跑行為鎖那類低流量量測不受影響）。

**權威量測（主控親跑）**：`scratchpad/watch_filtered.ps1`——WMI 查詢端即過濾
`Name IN (pythonw.exe, OpenConsole.exe, WindowsTerminal.exe)`、時間戳取 `TIME_CREATED`
（建立時刻），流量小不積壓。三條判準須同時成立才算數：① 覆蓋率正向對照＝全套期間必須
抓得到 pythonw；② 全套期間 OpenConsole／WindowsTerminal＝0；③ 已知陽性（pythonw 以零旗標
起 `git --version`）必須被抓到。結果：根層全套 23:41:09～23:43:08 rc=0，① **pythonw 72 筆**
（23:42:25～23:43:00，即 test_context_budget_guard 等以 pythonw 真跑 planner 的單位）、
② **OpenConsole＝0、WindowsTerminal＝0**、③ 陽性探針 23:43:09.027 起 pythonw ⇒ 23:43:09.373
**OpenConsole.exe＋WindowsTerminal.exe 各 1 筆（父 svchost）**。跑完現查 OpenConsole＝0、
WindowsTerminal＝0、孤兒 conhost＝0。

### 待主控回填（f901721 後續）

- 主控收尾全套（本節修補落地後）：rc=0、`發現 4617 個測試`、`[M6 id 集合] tools/tests@win32：
  ✅ 集合關係成立（本次 skip 43 支）`、`[skip census] tools/tests@win32 共 43 支：platform=42／
  …／env-disabled=1`（行為鎖不再被 skip）；修補過程中主控另補 `skip_tag_policy.
  _SITE_CLASS_CENSUS["tools/tests"]["runtime-skipTest"]` 33→32（行為鎖移除 runtime skipTest
  後的站點數，全套靜態前置掃描抓到——修復棒 H 被禁跑全套故未見）。
- 下一次真 `windows-compat-ci`／`macos-compat-ci`／`root-infra-ci` run（本輪修法的
  commit push 後）：三剖面 M6 是否轉綠、win32 skip census 是否不再含本測試（留白）。
