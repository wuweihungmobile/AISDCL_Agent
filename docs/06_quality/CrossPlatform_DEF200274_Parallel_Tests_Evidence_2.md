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
