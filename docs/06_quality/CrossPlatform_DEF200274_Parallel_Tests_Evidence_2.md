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
- 本節修法 commit `ee4bdd4`（push `f901721..ee4bdd4`；pre-push 期間 WMI 過濾版監看
  pythonw 76 筆、OpenConsole＝0、WindowsTerminal＝0）的雲端 run 全數 success（主控
  `gh run view --log` 親抓逐字）：root-infra-ci 36156520219、macos-compat-ci 36156520097、
  windows-compat-ci 36156520147、AutoClaude CI 36156520154、shellcheck-ci 36156520128。三平台
  `發現 4617 個測試（下限 4543）`；`[skip census] tools/tests@linux 共 83 支：platform=81…`、
  `tools/tests@darwin 共 47 支：platform=47…`（兩者皆列 `[已標籤 [WINDOWS-NATIVE-ONLY]]
  test_context_budget_guard.PlannerCheckIsConsoleFreeTest…`＝正確的平台 skip）；
  `tools/tests@win32 共 43 支：platform=42／…／env-disabled=1`、`[M6 id 集合] tools/tests@win32：
  ✅ 集合關係成立（本次 skip 43 支）`——行為鎖不在 win32 skip 清單內 ⇒ 在 windows-compat-ci
  上真的執行並通過。

## 收斂後複驗與遺留收尾（2026-09-26）

掌舵者六問重問＋前輪〈Windows console 洩漏事故〉三項遺留。流程：四方唯讀審查（Architect／SA／
SD／QA，皆 Sonnet，主控 Opus 5.5）→ Developer 實作 → 閘門棒（護欄棘輪重釘＋根層全套＋SDD
ci-gate）→ 兩面獨立審查（程式正確性／對抗式反駁）→ 審查修補 → 主控收尾。額度 converge 帶下
守衛擋 Workflow，除首輪四方審查外改逐個派 Agent。

### 六問答覆

1. **帳本多 CPU 問題**：非 fixed 列原有 311／381／386 三筆。386 本輪根治（見下）；381 為觀察期
   （2026-10-03 起查 7 次排程 run，日曆卡住）；311 為「未重現≠已修」且解鎖條件未滿足。SA 對 9 筆
   fixed 列做 zero-trust 抽查（宣稱的鎖／函式逐一 Grep），全數真實存在且在守宣稱主題。
2. **功能完備與 CI 多 CPU**：QA 親跑根層全套 rc=0、`發現 4617 個測試`、`workers=18
   source=cpu_budget`、`S=2014.1s｜ideal=111.9s（S/W-bound）｜loss=1.00x｜slot 利用率=99.8%`。
   雲端（ee4bdd4／c5d1722，`gh run view --log` 親抓）：root-infra-ci／windows-compat-ci
   workers=4、macos-compat-ci workers=3、AutoClaude CI 三 job `xdist workers=4`＋`nodes confirmed=4`、
   fsm-chaos-nightly 排程 run 36106419756 `xdist workers=4`。Architect 確認 worker 數唯一來源＝
   `tools/lib/cpu_budget.py`，三個消費端只委派，未見寫死的第二複本。
3. **頭重腳輕**：未見結構性不均。pre-push root 前景滿 W、AutoClaude／SDD 背景各 2 worker 是 S/W
   模型下的刻意設計（root leg 恆為瓶頸，另兩 leg 對 worker 數不敏感）；本機 slot 99.8%、loss 1.00x。
   唯一殘留的「看起來不均」訊號是每次都響的種子過期警告——查明是比較面錯誤（DEF-200-386），
   不是負載真的不均。
4. **其他可平行面**：Architect 覆核 CI matrix 分片、nightly stage 平行、SDD ci-gate 兩軌平行、
   ruff／lint-imports、ONBOARDING 回填量測，結論同前：收益不抵成本或已被 root leg 遮蔽，本輪不做。
5. **是否收斂**：多 CPU 機制維持收斂，不重啟系列；本輪修掉的是收斂後才被量到的比較面缺陷與
   console 洩漏的鄰居站點。
6. **前輪三項遺留**：(a) 負對照不彈窗只在本機驗證 → DEF-200-396 改為全套自動驗證；(b) v0.30 三支
   缺旗標 → DEF-200-394，且查出 `hub_sync.py` 其實在 hook 路徑上（前輪判斷訂正）；(c)
   `test_install_windows_nightly` 並行紅一次 → DEF-200-395，QA 30 次壓力（含與全套並行）全綠、
   當時輸出未保留，改為下次紅燈自帶診斷，維持 open。另補前輪自陳的「普查零增長不出聲」→
   DEF-200-397。

### 修復

- **DEF-200-386**：`tools/lib/parallel_shard.py::run_parallel()` 在 `save_live_cache()` 後拿
  「本輪原始耗時」（無父鍵加總、無保留鍵）比種子，而 `tools/refresh_parallel_timing_seed.py`
  拿磁碟合併後的活體快取比；同一演算法、不同比較面。新增單一入口
  `parallel_timing_cache.current_staleness_report()`（磁碟種子 vs 磁碟活體快取），兩端改走它。
  回歸鎖 `RunParallelStalenessAdvisoryReadsMergedLiveCacheTest`：退回舊行為即紅，且紅在 30%，
  與雲端三平台實際症狀同值。
- **DEF-200-394**：v0.30 `.claude/hooks/session_start.py` 會 import `tools.fsm_runtime.hub_sync`
  並呼叫 `pull()` → `_mirror_git()` 的三處 git；hook 載具是 pythonw。`knowledge/hub-registry.yaml`
  檢入值為 `auto_pull_on_session_start: true`、`allowed_endpoints: []`——只差填一個 endpoint 就重演
  DEF-200-389。四檔七處子行程（四處 git、兩處 docker、一處 TLC java）補
  `creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)`，刻意不加 CREATE_NEW_PROCESS_GROUP
  （保留 Ctrl+C 中斷長跑 TLC）。`closure_evidence.py::_run_git` 是擴大掃描面後新抓到的同型站點。
  鎖：`tools/tests/test_check_hooks_liveness.py` 的 LATEST hook 掃描面由「hook 檔本身」擴為
  「hook 可達的 import 模組」。
- **DEF-200-396**：`NoWindowBehaviourTest.test_the_shipped_flag_really_suppresses_the_console`
  在負對照量測期間武裝 WMI 建立事件監看（重用 `_LIVE_CONSOLE_WATCH_PS1`），斷言武裝成功與 0 筆
  OpenConsole／WindowsTerminal 建立事件。突變自證：拿掉 SW_HIDE 即紅，實抓到 WindowsTerminal.exe
  與 OpenConsole.exe 各一筆，隨後自行收尾，前後數量 0／0、孤兒 conhost 0。
- **DEF-200-395**：四處 subprocess 補 timeout；WhatIf 斷言訊息帶 before／after 與 PowerShell
  rc、stdout／stderr 尾段。
- **DEF-200-397**：`report_delta()` 零增長印 `✅ 孤兒 console 普查：零增長（前 N／後 M）。`

### 獨立審查與修補

兩面審查皆 APPROVE-WITH-FIXES，六條關鍵宣稱（跨平台 skip 集合不變、T2 鎖以真實檔案複本突變
也會紅、T4 在 windows-compat-ci 上真跑、DEF-200-386 根因、v0.01～v0.29 零改動、無 console 洩漏）
皆未被推翻。收尾前修掉的四項：監看器 deadline 自腳本啟動起算、餘裕過緊（慢機器上可能量測尚未
結束監看器已收工，變成空洞的 0 筆）——改為斷言量測結束時監看器仍在線，同型缺口的既有
`PlannerCheckIsConsoleFreeTest` 一併修；BFS 原本跳過相對 import（漏掉 `hub_sync.py` 以
`from .anonymizer`／`from .pii_scanner` 帶入的兩支，目前零子行程）——改為解析相對 import；BFS
補接 `UnicodeDecodeError`；附記「六處 git 子行程」訂正為七處子行程。

### 🔴 誠實劃界

- **雲端種子重疊率**：種子取自 Windows 本機；比較面修正後，雲端若仍報過期，可能是各平台熱點
  分布真實不同（合法的「該刷新」訊號），不能直接判為本修法失效——下一輪先比對兩邊排名。
- **DEF-200-396 在雲端的鑑別力未驗**：GitHub windows runner 是否以 Windows Terminal 為預設終端
  未查；若不是，該斷言在 CI 上恆為 0 筆、只有開發機有鑑別力。
- **DEF-200-395 未重現≠已修**：本輪只讓下次失敗自帶診斷。
- **tlc_runner.py 無 timeout**：SD 審查另發現 TLC 呼叫無 timeout（形式化驗證卡住會無界等待），
  屬另一件事、本輪未改。
- **v0.01～v0.29 同型站點**：依版本規則不可原地改，未盤點。

### 待主控回填

- 閘門棒（審查前）[他包回報]：根層全套第 3 次 rc=0、`發現 4622 個測試`、`S=1741.2s｜ideal=96.7s｜
  slot 利用率=99.8%`，三次全套皆無過期警告（未執行 refresh，比較面修正後現有種子即達標）；SDD
  ci-gate rc=0（v0.01 1478、v0.30 1956、scripts/tests 364 passed，arch_fitness fail=0）；
  `sync_onboarding_baselines.py --check-snapshot` rc=0。
- 主控收尾全套（審查修補、帳本與本節落地後）：rc=0、`發現 4622 個測試（下限 4543）`、
  `[cpu_budget] root-unittest workers=18 source=cpu_budget`、`📊 派工摘要：worker=18｜S=1714.1s｜
  ideal=max(S/W, 最長單位)=95.2s（S/W-bound）｜loss=1.00x｜slot 利用率=99.7%｜最長單位：
  test_dev_start.TestBootstrapIncompleteMarker 61.4s`、`[M6 id 集合] tools/tests@win32：✅ 集合關係
  成立（本次 skip 43 支）`、`✅ 孤兒 console 普查：零增長（前 0／後 0）。`，無過期警告。全套前後
  現查 OpenConsole／WindowsTerminal／孤兒 conhost 皆 0／0／0；`--check-snapshot` rc=0；
  `check_defect_log_crossref.py` rc=0。
- commit `a7ec277`；push `c5d1722..a7ec277`，pre-push `[cpu_budget] parallel legs: root=18
  autoclaude=0 sdd=2 wall=146s`、`✅ 本次 push 觸發的所有 leg 皆通過（rc=0）`；root leg `發現 4622
  個測試`、`S=1785.1s｜ideal=99.2s｜loss=1.00x｜slot 利用率=99.8%`、普查零增長、無過期警告；SDD leg
  v0.01 1478／v0.30 1956／scripts/tests 364 passed。push 後現查 OpenConsole／WindowsTerminal 0／0。
- 雲端（`a7ec277`，主控 `gh run view --log` 親抓）五支全 success：root-infra-ci 36178806924
  （`workers=4｜S=1346.0s｜ideal=336.5s｜slot 99.8%`、`[M6 id 集合] tools/tests@linux：✅（本次 skip 83
  支）`）、windows-compat-ci 36178806852（`workers=4｜S=2141.1s｜ideal=535.3s｜slot 99.4%`、`@win32：✅
  （43 支）`、`✅ 孤兒 console 普查：零增長（前 1／後 1）`；NoWindowBehaviourTest 與
  PlannerCheckIsConsoleFreeTest 不在 skip 清單⇒真跑且通過）、macos-compat-ci 36178806842
  （`workers=3｜S=1247.9s｜ideal=416.0s｜slot 99.5%`、`@darwin：✅（47 支）`）、aisdlc-sdd-ci
  36178806990（`xdist workers=4`＋`nodes confirmed=4`）、AutoClaude CI 36178806865（三 job 皆
  `xdist workers=4`＋`nodes confirmed=4`）。**三平台 log 皆無「種子檔可能已過期」**（上一輪
  ee4bdd4／c5d1722 三平台皆報 30%）⇒ DEF-200-386 在雲端同樣消失；上方〈誠實劃界〉第一條的
  「跨平台熱點差異」風險本次未出現。

## 收斂後複驗 II——mac 親驗輪（2026-09-26，Apple M1 Max 10P/10L，Docker down）

掌舵者六問重問＋前輪〈收斂後複驗與遺留收尾〉五項誠實劃界。流程：四方唯讀審查（Architect／SA／SD／QA
皆 Sonnet，主控 Fable 5.1）→ 主控裁決去重 → Developer 實作 → 兩面複審鏡 → 主控收尾。SD 獨占機器做重量測，
QA 在三方交卷後才啟動（突變自證需要獨占工作樹）。四方判決：Architect CONDITIONAL／SA CONDITIONAL／
SD APPROVE／QA APPROVE；18 筆帳本列零信任重驗 18/18 CONFIRMED，無 REFUTED。

### 六問答覆（mac 面）

1. **帳本多 CPU 問題**：非 fixed 列仍是 311（mac 序列 20/20＋xdist 3/3 皆綠，未重現≠已修）、381（chaos-latest
   排程 1/7、無紅，日曆 2026-10-03 未到）；本輪新立並修掉 DEF-200-398（tlc_runner 逾時，見下）。DEF-200-316
   方案 B：四方確認**尚未實作**（三份 settings 條目 24/12/6＝設計書修前基線；mac 探針 6 行 posix_spawn ENOENT
   ＋2 行 SessionStart success，主控與 SA 各親跑一次同值）；設計書 D1～D10 經 Architect 逐項覆核可執行，兩處漂移
   要訂正（`tools/dev_start.py` 現 1950 行、餘裕 2 非 0；`test_check_hooks_liveness.py` 兩類別行號 +187，以類別名
   重定位）。**本輪未動**：auto mode 分類器以 [Self-Modification] 擋下改 `.claude/settings.json` 的派工，
   依規則不得改派其它工具繞過，留掌舵者親手窗口。
2. **功能完備與 CI 多 CPU**：[他包回報 SD] 根層全套 `workers=9 source=cpu_budget`、`發現 4622 個測試`、
   `S=813.8s｜ideal=90.4s（S/W-bound）｜loss=1.00x｜slot 利用率=99.6%`、real 109.98s、rc=0；AutoClaude
   `xdist workers=9`＋`nodes confirmed=9`、4738 passed／156 skipped、31.45s；SDD ci-gate `broadcast workers=9`、
   v0.01 1475（序列，設計如此）／v0.30 `xdist workers=9` 1959／scripts 363。[他包回報 SA] 雲端 edd36587 三支
   push run 皆 success：workers=4（ubuntu）／3（macos）／4（windows）、三平台 `發現 4622 個測試`、slot 99.3～99.8%。
   [他包回報 Architect] 全 repo `cpu_budget` 249 命中逐一分類、8 支 workflow 逐支核過：worker 數唯一來源
   `tools/lib/cpu_budget.py`，兩處字面數字（pre-push 背景 leg=2、五處 CI job 顯式 `-p no:xdist`）皆有明文 WHY。
3. **頭重腳輕**：[他包回報 SD] 最長葉節點 test_dev_start 39.5～48.1s ≪ fair_share 85.6～91.0s；W=8／9／10 三次
   全套零 🚨／⚠️／🐢；`dispatch_imbalance.py` 已接線（run_root_unittests.py:539）、沉默是「無不均可報」。
   **整輪 CPU（前輪未量）**：top 取樣穩態（去頭尾 10s）W=9 **88.32%**（10 核 W=9 理論上限 ≈90%）；AutoClaude
   avg 83.31%。W 掃描：W=8 real 109.78s／78.73%／S=728.3s、W=9 109.98s／88.32%／813.8s、W=10 104.51s／88.45%／
   855.8s——wall 差 <5%（cpu_budget 檔頭跨輪漂移容許 6.7%），公式 `logical−ceil(logical/physical)`=9 在無 SMT
   機器維持，不調 CAP。
4. **其他可平行面**（[他包回報 Architect]，附算式）：mac nightly 四 stage 28／148／35／46s＝257s，stage 2/3/4
   各吃預算 9，跨 stage 並行＝27 worker 搶 10 核（2.7 倍超訂；cpu_budget 實測 1.4 倍超訂即 +9.5% 總工作量）⇒ 不做。
   **新發現**：ci-gate.sh 三軌序列 12.42＋15.68＋15.24s，背景並行僅 10% 超訂、理論省 27.6s（全輪 10.7%）⇒
   絕對量小、DOCUMENT_ONLY。TLA+ 五軌現況零自動通道跑（假議題）；mutmut 2.4.3 無平行旋鈕（DOCUMENT_ONLY）；
   CI 矩陣分片增加計費 runner-分鐘⇒不做；ruff／lint-imports 不做。
5. **是否收斂**：多 CPU 機制在 mac 亦收斂——核數自動偵測（psutil ABSENT → darwin 分支 `sysctl -n hw.physicalcpu`
   =10）、worker 廣播、負載平衡、種子過期偵測四機制完備；不重啟系列。
6. **前輪遺留**：(a) 種子跨平台：`refresh_parallel_timing_seed.py --check` rc=0「沒有明顯過期」，Windows 種子
   Top-15 vs mac 活體 Top-15 交集 12／聯集 18＝66.7%（門檻 50%）⇒ 維持單一種子；(b) 整輪 CPU 已量（上 3）；
   (c) tlc_runner 無 timeout ⇒ DEF-200-398 本輪修；(d) v0.01～v0.29：Architect 唯讀盤點 30 版皆
   `subprocess.run=1 timeout=0`，依版本規則不改，登記於 398 列；(e) DEF-200-396 雲端鑑別力：SA 查明
   windows-nightly-full 只在 schedule／dispatch 跑、最近排程 09-21 早於修復 ⇒ 主控 dispatch run 36212273769
   （edd36587）取證，結果見〈待主控回填〉；runner 映像 README 查無 "terminal" 字樣，預裝與否查不到。

### 修復：DEF-200-398 tlc_runner.py 逾時保護（LATEST v0.30）

`subprocess.run` 加 `timeout=DEFAULT_TLC_TIMEOUT_S`（1500s，**嚴格小於**雲端 chaos nightly job 級
`timeout-minutes: 30`，讓內層先逾時、留下可讀 exit=2 與 log_tail）；`except TimeoutExpired` → `ok=False,
exit=2`（不用 exit=1：那是「跑完且找到 invariant 違反」）；CLI `--timeout`。鎖 `tools/tests/test_tlc_runner_timeout.py`
（LATEST 走 `tools/lib/sdd_latest.py` SSOT；ast 靜態鎖／行為紅綠自證／CLI 透傳；[他包回報] 3 ok、拿掉 `timeout=`
即 2 支紅、ci-gate rc=0 1475／1959／363、ruff 全綠）。

### 獨立審查與修補（三輪）

第一輪：鏡 A（正確性／消費端）REJECT、鏡 B（對抗式反駁）APPROVE-WITH-FIXES。P1×2：`TimeoutExpired.stdout/stderr`
在 POSIX 即使 `text=True` 仍是 bytes，逾時分支 `(exc.stdout or "") + "\n"` 炸 `TypeError`→rc=1（正是禁止的
exit=1 語意；第一輪測試手造 str 形狀例外故未攔到）；三支鎖皆未覆蓋「不覆寫預設值」路徑（預設改 None 三鎖仍綠）。
P2／P3：`ci-gate.sh --full-tlc` 對凍結基線 v0.01 亦跑五軌（依政策不改、仍無 timeout，已揭露）；WHY 註解稱
「chaos nightly 有 30 分鐘 job 時限」查無此通道（現況零自動通道跑 TLC）；`--timeout 0`／負數無驗證；ast 鎖不查
`timeout=None`；檔頭退出碼說明未同步。修補：`_as_text()`（None／bytes／str）＋真子行程端對端測試（修法前必炸
TypeError）＋預設值路徑鎖＋`_positive_float`（>0）＋ValueError＋ast 值檢查＋文案訂正。
第二輪：兩鏡 APPROVE-WITH-FIXES，上一輪逐條「已修」；**兩鏡交叉**抓到同一新洞：`--timeout inf`／`nan` 繞過
`<= 0`（inf 重現無界等待；nan 讓 `selectors.select` 拋未捕捉 ValueError，main() 以 exit=1 崩潰）。修補：
`math.isfinite` 雙防線（CLI type 與 `run_tlc()`）＋ inf／-inf／nan／1e400 測試＋端對端斷言 `subprocess.run`
從未被呼叫；`_as_text` docstring 訂正（Windows 分支 run() 會再 communicate 一次拿到 str）。
第三輪：兩鏡 APPROVE（親餵 inf／-inf／nan／1e400／Infinity 全拒、0.5／1e-3／1500／1e300 全收；`main(["--timeout","nan"])`
改為乾淨 SystemExit(2)）。鎖檔 18 支測試；收尾單人窗口把 docstring 史料壓進本節（359→292 行）以符合回歸鎖軌
單輪上限 309（核准超額名額已用罄）。附帶事故：鏡 A 第三輪誤呼叫未 mock 的 `run_tlc()` 真的起了一個 TLC java
（PID 9998，7 核跑 7 分鐘），主控收尾時 kill 回收。

### 🔴 誠實劃界
- DEF-200-316 方案 B 本輪未實作（auto mode Self-Modification 阻斷）；mac 探針 ENOENT 仍 6 行。
- DEF-200-396 雲端鑑別力：dispatch run 36212273769（edd36587）三 job success、`✅ 孤兒 console 普查：零增長（前 1／後 1）`，
  但 runner 映像 `windows-2025-vs2026`（Windows Server 2025）軟體清單 README 36KB 對 terminal／OpenConsole 零命中，
  而監看器刻意只數 OpenConsole.exe／WindowsTerminal.exe（conhost 在無桌面環境恆 0）⇒ **雲端結構上無鑑別力**，
  只有 WT 為預設終端的開發機有鑑別力；帳本 396 列已改寫揭露。
- v0.01～v0.29 tlc_runner 同型缺口依版本規則不改（凍結基線 v0.01 若被任何工具用來跑 TLC，該面仍無 timeout）。
- SD：top（全機）與 /usr/bin/time（行程樹）兩種 CPU% 量法差距（83～88% vs 68%）如實記錄未深究。
- SD 用語：「CPU 核數自動偵測」與「派工粒度細分（人工白名單＋偵測建議）」是兩層機制，勿混讀。
- 主控流程失誤：scratchpad 任務書 `SA.md` 與報告 `sa.md` 在 APFS 為同一檔，四份任務書被報告覆蓋（agent 已先讀完，
  無損），已入記憶。

### 待主控回填

- 護欄棘輪 R174：106664 → 106966（+302；新檔 292＋本表自身 10），全額申報回歸鎖軌、主軌 0。
  `_REPIN_LOG_HISTORY_SHA256`／接鏈列 new12 的填寫第一次被 auto mode 以 Self-Modification 擋下，掌舵者明文授權後
  第二次放行（值＝`--print-guard-lines` 印出的 e8711dba…）；`test_adr_xplat001_c1c2_lock` 192 tests OK。
- 收尾途中另兩處機械重釘：`_TREE_FILE_FLOORS['tools/tests']` 65→66（runner 靜態掃描早退印出的建議值）；
  `run_tlc.sh` 檔頭補註後 101 行撞薄殼上限 100，收斂為單行註解回到 100 行（`test_check_wrapper_thinness`＋
  `test_check_script_parity` 169 tests OK）。
- 主控收尾全套（mac）：`REAL_RC=0`、`發現 4640 個測試（下限 4543）`、`[cpu_budget] root-unittest workers=9
  source=cpu_budget`、`📊 派工摘要：worker=9｜S=777.0s｜ideal=max(S/W, 最長單位)=86.3s（S/W-bound）｜loss=1.00x｜
  slot 利用率=99.6%｜最長單位：test_dev_start 44.3s`、`[M6 id 集合] tools/tests@darwin：✅ 集合關係成立（本次
  skip 47 支）`，無種子過期警告。SDD ci-gate rc=0（v0.01 1475／v0.30 1959／scripts/tests 363）；
  `--check-snapshot` rc=0 指紋相符；`check_defect_log_crossref.py` rc=0；ruff 四檔 `All checks passed!`。
- commit／push／雲端：見 git log 與 `gh run list --commit <sha>`（本節不寫死 sha）。


## 雲端假紅補記（2026-09-26，e4bf51af 推送後）

e4bf51af 觸發的雲端 CI 兩支紅（macos-compat-ci run 36232784475／AutoClaude CI run 36232784477），
同一份碼在 edd36587／a7ec277 皆 success，判定為不穩定假紅而非迴歸。session 中途意外中斷，
兩個修復包各自狀況不同：AutoClaude 那包完整交卷（STATUS: done）；macOS 那包中途中斷、diff 已
套用但未留報告，由主控親自驗證後採用。

### DEF-200-399（macOS smoke 紅）
`RunParallelStalenessAdvisoryReadsMergedLiveCacheTest` 用真 `time.sleep` 10ms 階梯＋4 執行緒量
`elapsed` 排序，macOS runner 3 核負載下排序被 GitHub Actions 排程抖動打亂，重疊率跌到 36%／43%
（門檻 50%），連帶 `CarrierVerdictParityTest` 判定載具分歧。修法：改用執行緒區域（`threading.local()`）
假時鐘 offset 取代真 sleep，`parallel_shard.time.monotonic` 被 patch 成疊加 offset，排序不再受
排程影響。主控親驗：整模組 `Ran 230 tests` OK；突變自證——退回舊比較面（`staleness_report()` 直接比
`module_timings`）即紅（重疊率 30%），還原後綠；ruff 綠。

### DEF-200-400（AutoClaude CI 紅）
`test_close_kills_grandchild_spawned_via_shell_background_job`／`TestCloseKillsCmdShimGrandchild`
同型：sh 背景工作 `echo $! > marker` 先 truncate 建檔、後寫入 PID，測試只輪詢「檔案存在」即讀，
在建檔與寫入之間的窗口讀到空字串 ⇒ `int('')` ValueError。修法：輪詢條件改「檔案存在且內容非空」，
兩處（POSIX／cmd shim）同型寫法一併修。開發包驗證：本機（mac，較快較安靜）修前／修後、無加壓／
加壓（12 個 `yes`）四組各 30 次皆 30/30 passed——本機未能重現 CI 上的空 marker 競態（低機率、僅
雲端 Linux + xdist 4 workers 高併發下現形），如實回報「未重現」而非偽稱「已重現」；48 passed 1
skipped；ruff 綠。`AutoClaude/tests` 指紋樹變動 ⇒ ONBOARDING §7 表② mac 欄已用乾淨 venv 回填
（autoclaude 4638 passed／222 skipped，指紋 e847688ec487）。

### 護欄棘輪 R175
`test_run_root_unittests.py` 淨增 19 行（DEF-200-399 修法本身；`test_perception.py` 不在
guard-line 計數面內）；全額申報回歸鎖軌（19 ≤ 軌上限 309），主軌 0。同輪兌現
`_REPIN_NET_CAP_SCHEDULE` 到期義務 (175, 529)，重新武裝 177／528。

### 收尾全套
根層全套第二次 rc=0：`發現 4640 個測試`、`workers=9`、`S=764.7s｜slot 利用率=99.6%`、M6 ✅、無過期
警告。SDD ci-gate rc=0（1475／1959／363）。`--check-snapshot` rc=0。`check_defect_log_crossref.py`
rc=0。ruff 三檔（`test_adr_xplat001_c1c2_lock.py`／`test_run_root_unittests.py`／
`test_perception.py`）全綠。帳本新立 399／400（皆 fixed）。


## 收斂後複驗 III——mac 四方重驗（2026-09-26，Apple M1 Max 10P/10L，Docker down）

掌舵者六問第三次重問。流程：四方唯讀審查（Architect／SA／SD／QA 皆 Sonnet，主控 Fable 5.1）；
Architect／SA／SD 並行、QA 後置（突變自證需要獨占工作樹）；四方判決 Architect **CONDITIONAL**／
SA **APPROVE**／SD **APPROVE**／QA **CONDITIONAL**。QA 對 Architect 報告的一處附屬細節誤標
（REFUTED）不推翻 Architect 的核心缺陷判斷；本輪帳本零信任重驗（SA 5 筆指定列＋隨機抽 10 筆
fixed 列，QA 另交叉核對）合計 15/15 CONFIRMED，0 REFUTED、0 STALE。

### 六問答覆（mac 面，第三次）

1. **帳本多 CPU 問題**：[他包回報 SA] 帳本零信任重驗 5 筆指定列＋隨機抽 10 筆 fixed 列，共
   15/15 CONFIRMED、0 REFUTED、0 STALE。非 fixed 列仍是 311（[他包回報 QA] mac 加壓 20/20
   綠，未重現≠已修）、381（[他包回報 SA] chaos-latest 觀察期 1/7→2/7，日曆 2026-10-03 未到）、
   395（[他包回報 QA] mac 上 `[WINDOWS-NATIVE-ONLY]` 皆 skip（2 skipped×20），只有 Windows
   能重現）。DEF-200-316 方案 B：[他包回報 Architect／SA] 三份 settings 條目仍 24/12/6（未
   變）、mac 探針仍 6 行 posix_spawn ENOENT＋2 行 SessionStart success——本輪仍**未實作**，
   結構性卡在掌舵者親手窗口（見下〈主控裁決〉R2／R3）。
2. **功能完備與 CI 多 CPU**：[他包回報 Architect／SD／QA] 三支獨立全套（Architect S=768.7s、
   SD S=811.1s、QA S=766.3s）皆 rc=0、`workers=9 source=cpu_budget`、slot 利用率 99.7%、
   loss=1.00x、零 🚨／⚠️／🐢、零種子過期警告（三次數字同量級、非同一次轉述）。[他包回報 SA]
   雲端 HEAD f717181b 四支 push run 全 success，逐 job 表（`gh run view --json jobs` 現查）：

   | Workflow | Job | 平台 | workers | 測試數/證據 | 耗時 |
   |---|---|---|---|---|---|
   | root-infra-ci (36235336043) | root infra guard | ubuntu | 4（source=cpu_budget） | 發現 4640 個測試；slot 99.9% | 10:17:21→10:24:10 ≈ 6m49s |
   | AutoClaude CI (36235336034) | Tests + LOC Budget | ubuntu | 4（xdist, nodes confirmed=4） | — | 10:17:22→10:18:50 ≈ 88s |
   | AutoClaude CI | Equivalence Snapshot | ubuntu | 4（confirmed） | — | 10:18:52→10:19:22 ≈ 30s |
   | AutoClaude CI | PG Contract Tests | ubuntu | 4（confirmed） | — | 10:18:52→10:20:09 ≈ 77s |
   | AutoClaude CI | CLAUDE.md Budget + Snapshot Freshness | ubuntu | 不適用（非 pytest，只跑 LOC/新鮮度檢查） | — | 10:17:22→10:17:31 ≈ 9s |
   | macos-compat-ci (36235336059) | macOS smoke | macos | 3（root-unittest／broadcast／xdist 皆 3，source=cpu_budget/env） | 發現 4640 個測試；slot 99.7% | 10:17:27→10:26:25 ≈ 8m58s |
   | windows-compat-ci (36235336046) | Windows smoke | windows | 4（root-unittest／xdist／broadcast 皆 4，source=cpu_budget/env） | 發現 4640 個測試；slot 99.4%、loss 1.01x | 10:17:22→10:33:29 ≈ 16m7s |

   四平台 push job 皆逐字印出 `[cpu_budget]` 行，無單核執行；全庫 `-p no:xdist` 實際呼叫行
   恰 9 行（橫跨 4 個 workflow 檔），皆有明文 WHY（mutation hash 隔離／pg_real 單一 DB／perf
   計時純度／凍結基線競態），零裸奔單核。
3. **無頭重腳輕／自動偵測／平衡負載**：[他包回報 SD] D1 自動偵測三方交叉一致（cpu_budget
   內部函式／`os.cpu_count()`／`sysctl` 皆測得 logical=physical=10、total_budget=9）；D6
   最長單位 `test_dev_start` 44.1~46.6s ≪ fair_share 85~90s，`loss=1.00x` 代表已達理論最佳
   排程，數學上不存在頭重腳輕（非「沒抓到」，是連最重的單位都遠低於均分線）。[他包回報
   Architect] A1 全 repo 平行度字面 421→301 筆非噪音命中，19 筆 `_JUSTIFIED_SERIAL_SITES`
   全數登記、`test_ci_gate_xdist_allowlist -v` 13 tests OK；pre-push `leg=2` 與 CI 9 處
   `-p no:xdist` 皆有明文 WHY，零未管制字面。
4. **其他可平行面**：[他包回報 Architect] 沿用既有六項結論算式全部覆核吻合（nightly 跨
   stage 2.7 倍超訂不做／`ci-gate.sh` 三軌序列 DOCUMENT_ONLY／TLA+ 五軌零自動通道跑（假
   議題）／mutmut 2.4.3 無平行旋鈕（本場未獨立驗證，沿用既有結論）／CI 矩陣分片增加計費
   不做／ruff／lint-imports 不做）；新查五項面向（AutoClaude xdist `worksteal` 與根層／SDD
   一致性、根層 runner 序列段占比、pre-push 各 leg 分配、SDD v0.01 序列 WHY、`.ps1`／`.sh`
   對稱性）均無新缺陷。
5. **是否收斂**：四方一致：多 CPU 機制在 mac 本輪第三次重驗仍收斂（核數自動偵測、worker
   廣播、負載平衡、種子過期偵測四機制完備），不重啟系列。
6. **前輪未完成任務**：[他包回報 SA] 唯一真正未完成項目仍是 DEF-200-316 方案 B，結構性卡在
   auto mode 的 `[Self-Modification]` 分類器（非本 session 或任何 subagent 可繞過）；
   [他包回報 Architect] 本輪新發現 **P2-1**（方案 B 設計書 D2b 測試影響盤點不完整，漏列
   `test_hook_wiring_cwd_safety.py` 與 `test_block_destructive_git_r83.py` 兩檔），已回流
   為設計書新增〈D2c〉節；其餘「待主控回填」項目在 f717181b commit message 中皆已可見落地，
   非未結事項。

### 主控裁決

主控（Fable 5.1）本輪裁決 R1～R7（原文照錄）：

R1. 多 CPU 系列維持收斂，本輪零程式碼改動：三支獨立全套（Architect／SD／QA 各跑一次）皆
    rc=0、workers=9 source=cpu_budget、slot 99.7%、loss=1.00x、零 🚨／⚠️／🐢、零種子過期；
    雲端 HEAD f717181b 四支 push run 全 success、workers 4／4／3／4（ubuntu／ubuntu／macos／
    windows）皆印 `[cpu_budget]`；全庫 `-p no:xdist` 皆有明文 WHY（口徑差異：SA 數 11 處、
    Architect 數 9 行實際呼叫行、主控現查文字出現 13 次含 WHY 註解，三者同一結論）；chaos-nightly
    LATEST track workers=4。不重啟系列。
R2. Architect P2-1 CONFIRMED（QA 逐行核實）：方案 B 設計書 D2b 漏列兩檔
    （`AISDLC_SDD/scripts/tests/test_hook_wiring_cwd_safety.py` L190／262／438 呼叫將刪除的
    `is_posix_carrier()`；`tools/tests/test_block_destructive_git_r83.py::test_it_is_exec_
    form_with_both_platform_carriers` L487-503 斷言 `len==2` 且需 POSIX 載具，同檔
    `test_the_whole_settings_file_has_no_form_problems` L506-510 與
    `test_check_hooks_liveness.py::test_real_settings_is_all_exec_form` L1951-1958 同型
    耦合）⇒ 本輪把 D2c 補進設計書（設計書在 repo 外，不受 auto mode 阻擋）；兩處漂移以現值
    訂正（`tools/dev_start.py` 1950 行／cap 1952 餘裕 2；`test_check_hooks_liveness.py` 的
    `TestRuntimeCarrierEvidenceIsRead` 現 L3383、`TestTheStopGuardIsTheAutomaticReaderOf
    ThatEvidence` 現 L3467，檔案 3526 行，改以類別名定位）。
R3. 方案 B 不可分段：測試層耦合證據（兩支測試直接讀真實 `.claude/settings.json` 餵
    `hook_form_problems()` 斷言 `== []`）⇒ D1＋D2＋D2b＋D2c＋D5 必須同一原子提交，由掌舵者
    在非 auto mode 窗口親手做。D3（新模組 `hook_carrier_symlink.py`）雖可獨立先做，主控裁決
    **不預作**：未接線的模組是投機性程式碼（Rule 2），且會觸發護欄棘輪與 LOC 記帳卻無對應
    功能；留到同一窗口一併做。
R4. QA 對 Architect 的附屬 REFUTED（grep 命中檔歸屬寫反）：不影響 P2-1 本體；D2c 以 QA 核實
    後的歸屬為準（`test_check_hooks_liveness.py` 是 D2b 已處理面、非額外命中；
    `test_block_destructive_git_r83.py` 是真命中）。
R5. 帳本四列（皆 open 維持）：311 加註「2026-09-26 mac 加壓 20/20 綠，未重現≠已修」；316 加註
    本輪 P2-1 與 R2／R3 裁決指針；381 觀察期 1/7→2/7；395 加註「mac 上 `[WINDOWS-NATIVE-ONLY]`
    皆 skip（2 skipped×20），只有 Windows 能重現」。四列現值 676／655／638／667 bytes，上限
    `ROW_MAX_BYTES=700`，且 `OVERSIZE_ROW_GRANDFATHERED` 清單（36）與超標總量（20027）皆滿額
    ⇒ **不得讓任何一列超過 700 bytes**：狀態欄改寫成索引（一句現況＋「詳見…」），被移出的
    原文逐字搬進本節新增的〈帳本列瘦身對照〉小節。
R6. 主控自陳流程失誤：任務書兩處路徑筆誤（`tools/dispatch_imbalance.py` 應為
    `tools/lib/dispatch_imbalance.py`；`AISLDC_SDD` 應為 `AISDLC_SDD`）；QA 判準字面「有一條
    REFUTED 即 CONDITIONAL」未區分附屬／本體，致 QA 判 CONDITIONAL 而六問實無新缺陷——主控
    以實質裁決。
R7. SD 觀察到同機 peer session（`aisdcl-agent-bb`）在量測窗外跑同一套件並留 3 個未追蹤暫存檔
    後自清；本輪三次全套時間窗與其不重疊。

### 設計書 D2c 補記

方案 B 設計書 `~/.autosdd/handoff/PlanB_design_20260917.md`（repo 外）本輪新增
〈D2c　D2b 漏列的兩個測試檔〉節（回應 Architect P2-1／R2／R4）：逐一列出
`AISDLC_SDD/scripts/tests/test_hook_wiring_cwd_safety.py`（L190／262／438 三處
`is_posix_carrier()` 呼叫＋L236 R97「跨平台配對各造一半」前提衝突）與
`tools/tests/test_block_destructive_git_r83.py::test_it_is_exec_form_with_both_platform_
carriers`（L487-503，`assertEqual(len(mine), 2, ...)` 與 `is_posix_carrier()` 呼叫兩處
必炸）的現行斷言原文、方案 B 下會紅的原因、與比照 D2b 規格的「先紅再綠」改法草案（明文
「改法草案待實作窗口親讀全文後定案」，不預先鎖死函式／常數命名）。同輪並於 D9 表訂正
`tools/dev_start.py` 現值為 1950 行／餘裕 2（非表定的 1952 行／零餘裕）；D2b 內兩個類別的
行號引用改以類別名定位（現值 `TestRuntimeCarrierEvidenceIsRead` L3383、
`TestTheStopGuardIsTheAutomaticReaderOfThatEvidence` L3467，檔案現 3526 行）；D7 補上
〈測試層耦合證據〉段（R3 的兩支直接讀真實 `settings.json` 的測試），並明文「D3 不預作
（主控裁決，Rule 2）」。

### 帳本列瘦身對照

| ID | 瘦身前狀態欄原文逐字 | 瘦身後狀態欄原文逐字 | bytes（整列）前→後 |
|---|---|---|---|
| DEF-200-311 | open（2026-09-15）；2026-09-17 連跑 20 次 rc 全 0、整檔＋xdist 50 passed（四方 SA 實測；未重現≠已修）；2026-09-25 再補：CPU 壓力 20/20、I/O 負載 26/26 皆綠（他包回報）；未重現≠已修，解鎖條件不變 | open（2026-09-15）；2026-09-26 mac 加壓 20/20 綠，未重現≠已修，解鎖條件不變。詳見 CrossPlatform_DEF200274_Parallel_Tests_Evidence_2.md〈收斂後複驗 III〉。 | 676→611 |
| DEF-200-316 | open（2026-09-17）；裁決已回填 | open（2026-09-17）；09-26 補 D2c。詳見〈收斂後複驗 III〉 | 655→687 |
| DEF-200-381 | open（未指派）：同分流去向欄，另需同步鎖 `test_gating_job_names_does_not_yet_include_chaos_latest`。詳見 CrossPlatform_DEF200274_Parallel_Tests_Evidence_2.md〈系列收斂後四方重驗〉 | open（未指派）：觀察期 2/7（2026-09-26 新增一次成功排程，日曆 2026-10-03 未到），同步鎖 `test_gating_job_names_does_not_yet_include_chaos_latest`。詳見 CrossPlatform_DEF200274_Parallel_Tests_Evidence_2.md〈收斂後複驗 III〉。 | 638→690 |
| DEF-200-395 | open（2026-09-26）：未重現≠已修；承接輪次：**未指派**；解鎖＝該測試下次紅燈時讀斷言自帶的診斷定位根因。詳見 CrossPlatform_DEF200274_Parallel_Tests_Evidence_2.md〈收斂後複驗與遺留收尾（2026-09-26）〉 | open（2026-09-26）：未重現≠已修；mac 上 [WINDOWS-NATIVE-ONLY] 皆 skip（2 skipped×20），只有 Windows 能重現；承接輪次：**未指派**。詳見 CrossPlatform_DEF200274_Parallel_Tests_Evidence_2.md〈收斂後複驗 III〉。 | 667→658 |

（316 因該列其餘欄位本就偏長，瘦身後last欄可用預算僅 85 bytes，故未能塞入完整證據檔檔名，
以簡短索引「詳見〈收斂後複驗 III〉」代替，完整指針見上表左欄本節；此為 bytes 硬約束下的
如實取捨，非遺漏。）

### 🔴 誠實劃界

- SD 整輪 wall 未掛 `time`（以 78 筆 1 秒取樣推估 ≈78s 量級，非精確值）；穩態 CPU% 以 top
  取樣去頭尾 58 筆 ≈92%（上輪 88%，同量級，量法差異不深究）。
- 逐 worker 負載分佈／最大最小負載比不可得：runner 只印 top5；活體快取父子鍵重複計入
  （天真加總 S=1270.2s vs 真實 811.1s）。
- DEF-200-395 在 mac 全 skip，加壓 20 次 rc=0 是 skip 的綠、非真跑。
- mutmut 2.4.3 無平行旋鈕之結論本場未獨立驗證（套件未裝根層 `.venv`）；沿用上輪。
- windows nightly-full 最近 schedule run 35600885460（09-21）未逐行覆核 cpu 行，只核了
  dispatch 36212273769。
- DEF-200-316 方案 B 仍未實作，mac 探針 ENOENT 仍 6 行；本輪只把設計書補完整。
- 主控任務書兩處路徑筆誤（R6）：`tools/dispatch_imbalance.py` 應為
  `tools/lib/dispatch_imbalance.py`；`AISLDC_SDD` 應為 `AISDLC_SDD`。

### 待主控回填

- 主控親驗（收尾單人窗口）：`check_defect_log_crossref.py` rc=0；四列 bytes 611／687／690／658、
  `oversize_row_problems` 0；`test_doc_loc_baseline_freshness_r60` OK rc=0、`test_archive_defect_log`
  OK rc=0；根層全套 `REAL_RC=0`、`發現 4640 個測試（下限 4543）`、`[cpu_budget] root-unittest
  workers=9 source=cpu_budget`、`📊 派工摘要：worker=9｜S=760.7s｜ideal=max(S/W, 最長單位)=84.5s
  （S/W-bound）｜loss=1.00x｜slot 利用率=99.7%｜最長單位：test_dev_start 43.5s`、
  `[M6 id 集合] tools/tests@darwin：✅ 集合關係成立（本次 skip 47 支）`，零 🚨／🐢／種子過期行。
- 複審鏡三條 P3 由主控親手修：瘦身對照表四列改為逐字（自 HEAD 帳本抄，不加外層反引號）；
  `test_the_whole_settings_file_has_no_form_problems` 行號訂正為 L506-510（證據檔與設計書兩處，
  現查 def 在 L506、下一個 def 在 L512）；R1 補 `-p no:xdist` 三種口徑（11／9／13）的註記。
- commit／push／雲端：見 git log 與 `gh run list --commit <sha>`（本節不寫死 sha）。

---

## 🔴 DEF-200-316 方案 B——D2/D2b/D2c/D3/D5 落地，D1 被 auto-mode 擋下（2026-09-26；同輪稍後由主控親手補齊 D1，見下方〈D1 落地與兩鏡複審〉）

角色：Developer（Fable 5.1 主控派工）。單人串行一棒，依 PlanB_design_20260917.md 執行，**未 commit**（交棒單人窗口收尾）。

### 🔴 阻斷（本輪最重要的發現）

任務書事實基線寫「auto mode 已關閉（改 `.claude/settings.json` 不再被 Self-Modification 擋）」——**現查為假**。本輪 Bash 工具對 `.claude/settings.json` 的**任何**操作（含純讀取 `git status .claude/settings.json`）皆被 auto mode 分類器以 `[Self-Modification]` 擋下，逐字：

```
Permission for this action was denied by the Claude Code auto mode classifier. Reason: [Self-Modification].
```

依分類器自身說明「don't pursue the same outcome through another tool」，未嘗試改用 Edit/Write 工具繞過。**D1（三份 `settings.json` 刪 POSIX 半）本輪完全未落地**，三份條目數仍為 24／12／6（原值，非目標 12／6／3）。這與設計書 D7／D9 的預判一致（「auto mode 分類器以 `[Self-Modification]` 擋下改 `.claude/settings.json` 的派工…留掌舵者非 auto mode 環境一次做完」）——本輪是**實測驗證**這個預判為真，不是新發現。`.claude/hooks/*.py`（非 settings.json）與其餘一般檔案不受此限（已驗證：`check_claim_provenance.py` 編修正常放行）。

### 已落地（D2／D2b／D2c／D3／D5，皆已驗證）

- **D3**：新模組 `tools/lib/hook_carrier_symlink.py`（51 行）＋測試 `tools/tests/test_hook_carrier_symlink.py`（105 行，5 支全綠）。`tools/dev_start.py` 整合點：`step_venv()` 收尾呼叫 `hook_carrier_symlink.ensure()`，emit 走專用 lambda（不可直接接 `_warn`——首次建立成功也會 emit 一行**資訊**，直接接 `_warn` 會誤標 ⚠️ 進 WARNINGS，此為本包在 `test_dev_start.py` 兩支既有測試轉紅時發現並修正的真缺陷）。**已在本機真的建出符號連結**：`readlink .venv/Scripts/pythonw.exe` → `../bin/python`；`.venv/Scripts/pythonw.exe -c 'import sys;print(sys.version)'` 可執行（3.11.15）。
- **D2**：`tools/lib/hook_wiring.py`（780→774 行，淨減）：刪 `POSIX_CARRIER_REL`／`POSIX_CARRIER`／`is_posix_carrier()`／`declared_posix_carriers()`；`hook_form_problems()` 判準 B／E 改單一 Windows 形態載具；`carrier_liveness_problems()` 兩平台共用 `exists()`，新增 `is_symlink`／`readlink` 注入＋私有 `_posix_symlink_health_problems()`（取代 `posix_carrier_problems()`）；`runtime_carrier_verdict()` 刪 `by_design_fail` 桶與 `on_windows` 參數，三態收斂兩態。`tools/lib/single_venv_identity.py`（71→56 行）刪 POSIX 迴圈與 `canonical_posix`。`.claude/hooks/check_claim_provenance.py` 呼叫端同步去 `by_design_fail` 引用。
- **D2b**：`tools/tests/test_check_hooks_liveness.py` 逐類別改法全數落地（`TestHookEntriesAreExecForm`／`TestDeclaredWindowsCarrierExists`／`TestPosixCarrierLiveness`→`TestPosixSymlinkHealth`／`TestRuntimeCarrierEvidenceIsRead`／`TestTheStopGuardIsTheAutomaticReaderOfThatEvidence`），另發現並修正設計書未列的第七處耦合（`TestExecFormConversionScope::test_a_parent_relative_carrier_is_not_a_false_positive` 合成 settings 仍含 POSIX 半，非讀真磁碟卻同樣耦合）。
- **D2c**：`tools/tests/test_block_destructive_git_r83.py`（`len(mine)==1`，去 `is_posix_carrier` 斷言）；`AISDLC_SDD/scripts/tests/test_hook_wiring_cwd_safety.py`（`_as_running_interpreter`／`_materialise_carrier` 依 D2c 指示結構性改寫為單一路徑；另發現並刪除 `test_deny_carrier_resolution_stays_red_when_the_local_platform_half_is_missing`——經實測驗證，其前提（另一平台載具在本機解析不到）被方案 B 的符號連結**永久打破**，非僅 D1 未落地的過渡態）。全數 rc=0。
- **D5**：根 `CLAUDE.md`〈hook 載具〉L73/74 改寫＋補 `readlink` 現查；`test_doc_loc_baseline_freshness_r60.py` 全套 281 支綠（過程中發現並修正 7 處幽靈符號——反引號指名已刪除／已改名的符號，改用「」引號規避 `_SYMBOL_CLAIM_RE` 誤判，未動 `_GHOST_SYMBOL_BASELINE`）。`useMacWin.md` 三處（表格列＋段落＋[6/7] 正面現查）。

### S5 驗收（逐字，本機真跑）

```
$ readlink .venv/Scripts/pythonw.exe
../bin/python
$ claude -p --model haiku --debug hooks --debug-file …/planb_hooks.log "ok"
$ grep -E 'ENOENT.*\.venv/(Scripts|bin)' …/planb_hooks.log | wc -l
0
$ grep -c 'Hook SessionStart.*success' …/planb_hooks.log
4
$ grep -c 'hook_non_blocking_error' …/planb_hooks.log
0
```

🔴 **對照值前後**：SA 上輪對 HEAD 舊 settings 實測 ENOENT 6 行；本輪（D3 symlink 已建、settings.json 仍是舊格）ENOENT＝0、`hook_non_blocking_error`＝0。這是**尚未落地 D1 也已生效**的真實改善——舊 settings.json 的 Windows 半（`.venv/Scripts/pythonw.exe`）此前在 mac 上必然 ENOENT，D3 的符號連結讓它現在真的可執行，M9 立案的 217 筆噪音的根因（唯一那條在 mac 上必然失敗）已被移除，即使 POSIX 半尚未刪除。

負向驗證：`rm .venv/Scripts/pythonw.exe` → `python tools/check_hooks_liveness.py` rc=1，對三份 settings 逐一出聲；重建符號連結 → 再跑 rc=0（安靜）。`shell_command_corpus.py --summary`：tracked 5522/5166、transcripts 5052/4850，git／waitform 判準命中數與本輪改動無關（設計書 D8 預判正確）。

### 設計書偏差（逐條）

1. **D1 完全未落地**（見上，auto-mode 阻斷，非設計書可預見的實作細節問題）。
2. `TestRuntimeCarrierEvidenceIsRead`／`TestTheStopGuardIsTheAutomaticReaderOfThatEvidence` 的 `_NATIVE_CARRIER_EACCES`／`_ALIEN_CARRIER_ENOENT` 命名語意：設計書稱「`_NATIVE_CARRIER_EACCES` 永遠是 native、`_ALIEN_CARRIER_ENOENT` 永遠是 alien」——**經本包逐行追蹤 `runtime_carrier_verdict()` 的 `ours` 判準驗證，實際恰好相反**（`_ALIEN_CARRIER_ENOENT` 的 command 字面是唯一那條 Windows 形態載具，方案 B 起永遠判 native；`_NATIVE_CARRIER_EACCES` 是舊 POSIX 專屬字面，方案 B 起永遠判 alien）。已重新命名為 `_THE_CARRIER_ENOENT`／`_STALE_POSIX_LITERAL_EACCES`（內容逐字不動，僅改名＋docstring），並在程式碼內留下「方案書原文誤植」的訂正記錄。
3. `test_deny_carrier_resolution_stays_red_when_the_local_platform_half_is_missing`：設計書 D2c 未預見此測試需要處理（僅列了三處 `is_posix_carrier` 呼叫點），本包發現其隱含依賴同一前提，經實測（`.venv/bin/python` 字面在本機真實存在，代換判準改寫後仍會直接解析成功）確認其驗證意圖已被方案 B 結構性打破，予以刪除而非修補。
4. `TestExecFormConversionScope::test_a_parent_relative_carrier_is_not_a_false_positive`：設計書 D2b 明列此類別「維持綠燈」，但其中一格自建雙載具合成 settings，本包實跑抓到並修正（設計書審查範圍未覆蓋到函式體內容，只看了類別清單）。
5. `tools/dev_start.py` 的 `hook_carrier_symlink.ensure()` 整合：設計書給的呼叫式直接把 `_warn` 當 `emit` 傳入（同 `stray_venv.enforce()` 既有慣例）——本包實跑 `test_dev_start.py` 抓到這會把「已建立」這種**成功資訊**污染進 `WARNINGS`（兩支既有測試轉紅），改用小 lambda 依訊息前綴分流（`❌` 才升級 `_warn`）。

### LOC／棘輪記帳（S6，部分完成）

`python AutoClaude/tools/check_loc_budget.py`：`violations=0`。逐檔：`../tools/dev_start.py: 1951 （餘裕 1 行）`；`../tools/lib/hook_wiring.py` 774 行（cap 782，已脫離 SPECIAL-WARN 名單，餘裕回升至 8）。`hook_carrier_symlink.py` 51／`single_venv_identity.py` 56（cap 400 generic，餘裕巨大）。ruff 全部改動檔 `All checks passed!`。

🔴 **`tools/tests/` 護欄棘輪（`test_adr_xplat001_c1c2_lock.py` 的 `_GUARD_LINES_REPIN_LOG`／`_REGRESSION_LANE_LOG`／`_FROZEN_GUARD_LINES`／`_REPIN_LOG_HISTORY_SHA256`）本輪刻意未重釘**——`--print-guard-lines` 已現查淨額 106985→107092（+107，含新檔 `test_hook_carrier_symlink.py` 105 行全額申報＋既有三檔逐檔漂移 +2），但完整重釘涉及自我指紋 SHA256 需**追加後重跑再收斂**的多輪迭代（本檔沿革逐字自陳「`--print-guard-lines` 反覆覆核收斂」是常態，非一次到位），且本輪工作樹本就不會被 commit（D1 阻斷、單人窗口收尾），誤填一個字元會在下一個完全不相干的角落炸出新的紅——風險回報比不利於本輪代做。**現查值已備妥**（見上），供收尾窗口在確定最終工作樹（含 D1 落地後）一次性重釘，不需要重新推導。

### 待主控回填（收尾單人窗口）

- **D1 三份 `settings.json`**（本輪唯一阻斷項，需非 auto mode 環境）：刪 POSIX 半，條目數 24→12／12→6／6→3；改完後 `tools/tests/test_check_hooks_liveness.py`／`test_block_destructive_git_r83.py` 的 3＋2＝5 支現存失敗（皆讀真實 settings.json）會自動轉綠，**不需要再改一行 `.py`**（已用「假設 D1 已落地」的邏輯撰寫測試，本輪已驗證除了讀真磁碟那幾格外全數綠燈）。
- 護欄棘輪重釘（見上，數字已備妥）。
- `docs/06_quality/AutoSDD_Defect_Log.md` DEF-200-316 列狀態（本輪已更新為 partial，見下）。

### 追加（同輪，S7 全套驗證期間發現並修復的第二批真缺陷）

`python tools/run_root_unittests.py` 全套跑法揭露設計書與 D2b/D2c 皆未覆蓋的額外耦合面，逐一修復：

1. `tools/tests/test_mac_readiness_r82.py::TestPosixCarrierWarningTellsTheTruth`：呼叫已刪除的 `hook_wiring.posix_carrier_problems()`（本包 S0 census 的符號正規表達式未涵蓋此符號名，是純文字掃描的已知盲區）——改呼叫 `carrier_liveness_problems()` 並注入 `is_symlink`／`readlink` 健康值，只讓版本分支單獨說話。
2. `_TREE_FILE_FLOORS['tools/tests']`（`tools/lib/skip_tag_policy.py`）：新檔 `test_hook_carrier_symlink.py` 使掃描面 83→84 支，下限 66→67（工具逐字指示重釘值，零加減推算）。
3. `test_platform_neutral_paths.py` 兩處 encoding 掃描腐化上界（`TestTextIoDeclaresEncoding`／`TestScanSurfaceParityWithSisterLock`）：新檔使掃描檔數過上界，812→965（工具逐字指示重釘值）。
4. `tools/tests/test_hook_carrier_symlink.py` 自身兩處：`.write_text()`/`.read_text()` 缺 `encoding="utf-8"`（encoding 債務棘輪，shrink-only）；`assertEqual` 的 POSIX 絕對路徑字面（Windows 上 `os.readlink()` 可能回傳反斜線正規化值）補 `# posix-abs-ok:` 行尾豁免。
5. `.github/workflows/{windows,macos}-compat-ci.yml`：`tools/lib/hook_carrier_symlink.py` 是根層消費檔，`test_ci_paths_cover_root_consumers.py` 要求雙平台 CI `paths:` 觸發器補列（否則只改該檔時兩支 CI 都不會跑其回歸鎖），各檔兩處（不同 job）皆已補。

以上五類與 D1（settings.json）是否落地**完全無關**，皆為方案 B 程式碼本身在更大掃描面下暴露的真缺陷，已全數修復並個別驗證 rc=0。

### 最終驗證彙總（本輪收尾，全部逐字現查）

- `python tools/run_root_unittests.py`：REAL_RC=1，發現 4644 個測試（下限 4543 ✅），`workers=9｜S=763.5s｜slot 利用率=99.7%`，M6 `✅ 集合關係成立`；**恰好 8 支失敗**，逐一核對：5 支讀真實 `settings.json`（D1 阻斷，見上）＋3 支 `test_adr_xplat001_c1c2_lock.py` 護欄棘輪未重釘（見上，刻意留給收尾窗口）。其餘 4636 支全綠，零其他未解釋失敗。
- `bash AISDLC_SDD/scripts/ci-gate.sh`：`RC=0`，逐軌計數 `AISDLC_SDD_v0.01:1475 AISDLC_SDD_v0.30:1959 scripts/tests:362`（scripts 較基線 363 少 1——刪除 `test_deny_carrier_resolution_stays_red_when_the_local_platform_half_is_missing` 所致，屬預期）。
- `cd AutoClaude && python -m pytest tests/ -q`：`RC=0`，`4738 passed, 156 skipped`（AutoClaude 樹本輪零改動，數字變化來自其他既有工作）。
- `git status --short`：確認 `.claude/hooks/*.py`／`.github/workflows/*.yml`／`tools/`／`AISDLC_SDD/scripts/tests/`／`docs/`／`ONBOARDING.md`／`CLAUDE.md`／`useMacWin.md` 有改動；**三份 `settings.json` 皆不在異動清單內**（D1 確認未落地）；未見任何治理 `.yaml`／`FSM-STATE-*` 被意外回寫。
- S8 指紋回填：`python tools/lib/clean_venv_carrier.py`（樹外乾淨 venv，psycopg2／sqlalchemy 皆 ABSENT）一條龍跑完 `RC=0`；`--check-snapshot` 回到 `RC=0`（macOS 欄四棵樹指紋皆已同步：v001/v030 不變、scripts ec35ee2838d0（因 `test_hook_wiring_cwd_safety.py` 改動）、autoclaude e847688ec487）；乾淨 venv 已確認自動刪除（樹外暫存目錄不再存在）。

## D1 落地與兩鏡複審（主控收尾，2026-09-26）

D1（三份 `settings.json` 刪 POSIX 半）由主控（Fable 5.1）在非 auto-mode 窗口親手落地，隨即派兩面複審鏡（Sonnet 5，皆讀真實工作樹）交叉驗證。以下數字凡未附「主控現查」字樣者，皆逐字抄自兩鏡報告並標明來源。

### 主控親手落地與親驗

- **三份條目數**：根 `.claude/settings.json` 24→12、`AutoClaude/.claude/settings.json` 12→6、`AISDLC_SDD/AISDLC_SDD_v0.30/.claude/settings.json` 6→3（主控現查：`grep -c '"command"'` 對三份分別回 24／12／6，因每條 hook 條目含 `"type": "command"` 與 `"command": "..."` 各一行而**倍數計數**，故真實條目數＝該值 ÷2＝12／6／3，與設計目標相符）。
- **POSIX 字面清零**：主控現查 `grep -c 'bin/python"'` 對三份 `settings.json` 皆回 `0`（不含 exit code 為 1 的「無匹配」語意，純粹計數為零）。
- **凍結版零改動**：主控現查 `git status --short AISDLC_SDD | grep settings` 只列出 `AISDLC_SDD_v0.30`（LATEST）一份；`git diff --stat -- AISDLC_SDD/AISDLC_SDD_v0.01/.claude/settings.json` 輸出為空，確認凍結基線 v0.01 與其餘中間歷史版皆未被觸碰。
- **敘事改寫只動配對句**：主控現查 `git diff -- .claude/settings.json` 的 Stop block `_comment`（M9 史料段）——依 P3-1 裁決**維持不改**，僅在原文「本條目下方兩個載具是跨平台配對」後插入「（方案 B 前）」四字，並在段落末尾追加一句「（史料：2026-09-26 方案 B 已把配對拆為單一載具，ENOENT 自此皆為真缺陷，見根 CLAUDE.md〈hook 載具〉。）」；長段落本體逐字未動。頂層 `description` 欄則依 D5 明文改寫成一句（`10 條 → 20 條` 後補「2026-09-26 方案 B 後每支一條＝12 條」，並把舊的「Windows/POSIX 各一條、恆有一條 ENOENT」敘事改為「單一 Windows 形態載具＋symlink 解到同一顆 .venv」）。

### 主控親驗 helm_hooks.log（新 settings 下、本機真跑）

```
$ claude -p --model haiku --debug hooks --debug-file .../helm_hooks.log "ok"
$ grep -c 'ENOENT.*\.venv/(Scripts|bin)' helm_hooks.log
0
$ grep -c 'Hook SessionStart.*success' helm_hooks.log
2
$ grep -c 'hook_non_blocking_error' helm_hooks.log
0
```

### 鏡 B（對抗式反駁鏡，Sonnet 5）—— VERDICT: APPROVE

[他包回報 鏡 B] 七項反駁（ENOENT 歸零、負向會出聲、Windows 不受影響、測試沒被弱化、S7 五類真缺陷、首次 clone 安全、SDD／AutoClaude 側綠）**全數失敗**（即 Developer 的宣稱全部自行重現成立）：

- 負向驗證四段全部逐字重現：① `rm .venv/Scripts/pythonw.exe` → `check_hooks_liveness.py` RC=1，三份 settings 逐一出聲；② 改放普通檔案（非 symlink）→ RC=1，訊息含「必須是符號連結…可能是舊版殘留或手動放置的同名檔案」；③ `ln -sf /usr/bin/python3 ...`（指錯目標）→ RC=1，訊息含「是符號連結但指向…預期…身分錯」；④ 用 `ensure()` 重建 → `readlink` 回 `../bin/python`、RC=0（安靜）。
- 刪除的 7 支 `def test_` 全數對得上 D2b／D2c／Developer 報告〈五〉揭露清單：4 支純刪除（`by_design_fail` 相關 3 支＋`test_deny_carrier_resolution_...`）＋3 支「刪除再以同名／改名新增」（非淨損失）；零 `@skip` 新增；未發現任何不在揭露清單上的刪除／弱化。
- encoding 掃描上界 `812→965`：鏡 B**獨立重算**（非引用 Developer 字面）——`_scan_repo()` 實測 `scanned=1016`；`repin_ceiling(812)=1015`（已超界，觸發重釘需求）；`suggested_floor(1016)=965`，與程式碼填入值逐字相符，證明是工具印出的值而非手改。
- D1 落地後複驗：Developer 報告列為「因 D1 阻斷而現存失敗」的 5 支測試（`test_check_hooks_liveness.py` 3 支＋`test_block_destructive_git_r83.py` 2 支）獨立重跑**全部轉綠**。
- SDD／AutoClaude 側獨立重跑：`AISDLC_SDD/scripts/tests` 362 passed／2 skipped（RC=0，較基線 363 少 1，即已揭露刪除）；`AutoClaude/tests/tools` 901 passed／52 skipped（RC=0）。

判決：**APPROVE**，未發現任何 P1（未揭露的刪除／弱化／載具佈線變動）。

### 鏡 A（正確性／消費端鏡，Sonnet 5）—— VERDICT: APPROVE-WITH-FIXES

[他包回報 鏡 A] D1～D5 全數落地，判準／測試／文件三面與設計書高度一致，零殘留死符號呼叫、零 LOC／ruff／crossref 違規、8 支目標測試全綠。提出 3 條 P3：

1. **P3-1（settings.json Stop block `_comment`）**：未依 D1「整段刪除改寫成一句」指示完整改寫，改為保留史料＋追加一句；純文件風格，不影響機械守衛或測試。**主控裁決：維持不改**（Rule 3 外科手術；史料本身帶日期，加註「方案 B 前」／追加一句已足夠說明現況，無需整段改寫）。
2. **P3-2（`hook_carrier_symlink.py::ensure()`）**：目標 `bin/python` 不存在時仍回 `True` 並建出 dangling symlink（未檢查目標存在性）。**主控裁決：修**——本輪（收尾單人窗口）已改為目標不存在時**不建連結**、`emit` 錯誤訊息（含目標絕對路徑與「請先跑 dev_start 完成 bootstrap 後重試」）、回 `False`；新增測試 `test_a_missing_target_is_not_linked_to_a_dangling_path`（6 支全綠，含此新增，見本檔〈驗證〉節）。
3. **P3-3（帳本 DEF-200-316 描述欄）**：移除了「詳情見 CrossPlatform_R152_DEF200314_MacNightly_Evidence.md」的舊指針。**主控裁決：修**——本輪已把該指針補回描述欄末尾，並把狀態欄改寫為 `fixed（2026-09-26）` 併指向本節。

### 過渡現象（設計內噪音，非缺陷）

本 session（主控）Stop hook 於收尾期間回報 8 筆 `pythonw.exe` ENOENT——全部是**符號連結建好前**留在逐字稿裡的舊紀錄（`check_claim_provenance.py` 讀的是累積逐字稿，不是即時狀態），此後計數不再增加。這正是根 CLAUDE.md〈鐵律一之二〉要求的「失效可偵測」：噪音沒有被隱藏，而是隨符號連結生效後**自然停止成長**，可用「计数是否還在漲」機械分辨「舊債」與「新缺陷」。

### 誠實劃界

- **Windows 真機未驗**：`ensure()` 的 `is_windows=True` 分支是純 no-op（不觸碰磁碟），Windows 上字面零變動，本輪只靠靜態 diff 與合成測試（`TestEnsureWindowsIsNoOp`）覆蓋，未有 Windows 實機交叉驗證。
- **Linux CI 無真 `.venv` 只靠合成測試**：CI runner 不具備本機那顆已 bootstrap 的 `.venv`，`hook_carrier_symlink.py` 的正向/負向路徑僅由 `tempfile.TemporaryDirectory()` 合成樹覆蓋，未在 CI 環境對真實 `.venv` 交叉驗證。
- **首次 clone 到 dev_start 前的 POSIX hook fail-open 視窗依設計保留**：`hook_carrier_symlink.ensure()` 的呼叫點在 `step_venv()` 收尾，與 bootstrap 建 venv 同一次 `dev_start.py` 呼叫內完成；殘餘風險視窗僅「clone 後、第一次跑 dev_start.py 之前」，此為設計書 D3 已揭露且裁決保留的已知邊界，非本輪新增缺口。

## C8 復原判準（收尾單人窗口，2026-09-26）

### 根因（主控親查）

`tools/lib/hook_wiring.py` 的 `runtime_carrier_verdict()` 把逐字稿裡**所有**載具失敗都當成現況回報，即使同一載具之後已成功上百次。本 session 實況：失敗集中在 11:18～11:26Z 與 15:00～15:01Z，皆在 symlink 建立（15:02:25Z）之前；之後 `hook_success` 160 筆。這違反本 repo 原則「每一件事每次回覆都喊的守衛會被關掉」——同一批舊失敗每輪重報，正是待收斂的噪音。

### 修法規格與落地

1. **`runtime_carrier_verdict(attachments)`**：`attachments` 依 `hook_result_attachments()` 保序。新增私有 `_is_ours_attachment()` 共用判準（原 `ours` 判斷抽成函式，供成功與失敗兩處呼叫）。先一遍掃出 `last_ours_success`（最後一筆「ours 的 `hook_success`」的索引，找不到回 `-1`），再逐筆判：`ours` 失敗若其索引 `< last_ours_success` ⇒ 落入新桶 `counts["healed_fail"]`（不進 `problems`、不計入 `native_fail`）；否則才是活的（`native_fail`）。`alien_fail` 不受此規則影響（認不得的載具本身就是缺陷，不會被之後任何成功治癒）。`problems` 上限維持 8 筆，但改取**最新** `problems[-8:]`（原為 `problems[:8]`，取最舊）。
2. **`.claude/hooks/check_claim_provenance.py`**：訊息裡的「N 筆」改印 `counts['native_fail'] + counts['alien_fail']`（live 全量），不是 `len(problems)`（後者被最新 8 筆截斷，會把「其實還有更多」誤報成「只有這幾筆」）；`healed_fail` 刻意不印，安靜治癒。
3. **`tools/lib/hook_wiring.py` LOC 記帳**：改前 774 行、改後 772 行（净 **-2**，非 +N——新函式簽章雖增行，但把兩段歷史普查散文（M9 立案的 217 筆分佈普查、九天無讀者沿革）從 29 行壓成 6 行 pointer 抵銷有餘）。cap 782，餘裕回升至 10。
4. **測試（`tools/tests/test_check_hooks_liveness.py::TestRuntimeCarrierEvidenceIsRead`）**：先紅再綠，紅的逐字輸出：
   ```
   test_failures_before_a_later_carrier_success_are_healed_not_live ... ERROR
   KeyError: 'healed_fail'
   Ran 1 test in 0.004s
   FAILED (errors=1)
   ```
   修法落地後同一支測試與另外三支（(b) 成功後又失敗仍活著、(c) alien 不被治癒、(d) 上限只留最新 8 筆）＋ `TestTheStopGuardIsTheAutomaticReaderOfThatEvidence::test_a_healed_failure_keeps_the_stop_guard_quiet`（真子行程端到端：失敗＋同載具成功 ⇒ stderr 不含 `_SPEAKS_TARGET`）全數綠：
   ```
   Ran 11 tests in 0.124s
   OK
   ```
   完整回歸：
   ```
   $ python -m unittest test_check_hooks_liveness test_claim_provenance_r86
   Ran 248 tests in 10.052s
   OK (skipped=5)
   ```
5. **主軌淨額**：`test_check_hooks_liveness.py` 因新增 5 支測試（TDD 要求的正向／負向／邊界覆蓋）淨增約 33 行；同輪把本檔內五段純歷史敘事（命名沿革、方案書誤植訂正、九天無讀者立案普查）壓縮成指向本節的 pointer，原文逐字保全於下方〈帳本列瘦身對照〉。壓縮後淨額未能完全歸零（新測試覆蓋是 TDD 必要產出，非可壓縮的史料），剩餘淨額循 R174/R175 既有先例全額申報回歸鎖軌（見 R176 棘輪重釘節）。

### 帳本列瘦身對照（原文逐字保全）

**`_THE_CARRIER_ENOENT` 原註解**（`tools/tests/test_check_hooks_liveness.py`，壓縮前）：
> 本機全母體實測到的那 217 筆失敗其中一種**逐字形狀**（去識別化：把家目錄換成假路徑）——command 是**唯一**那條 Windows 形態載具（`.venv/Scripts/pythonw.exe`）。🔴 方案 B（DEF-200-316）起的哲學反轉：pre-Plan-B 這筆在 mac 上是「另一平台的配對半邊，刻意的 fail-open」（舊名「_ALIEN_CARRIER_ENOENT」）；post-Plan-B 兩平台共用同一條宣告，沒有「配對半邊」這件事了 ⇒ 這條命令失敗永遠是**真的壞了**（native_fail），與平台無關。舊名已改，內容（歷史真實逐字）不動。

**`_STALE_POSIX_LITERAL_EACCES` 原註解**：
> 舊 POSIX 專屬字面（`.venv/bin/python`，方案 B 前的獨立宣告）。🔴 方案 B 起沒有任何 `settings.json` 會再宣告這個字面 ⇒ 若逐字稿裡出現這個 command 失敗，它是**認不得的載具**（alien_fail），不再是「本平台自己那條」（舊名「_NATIVE_CARRIER_EACCES」已改，內容不動）。

**`TestRuntimeCarrierEvidenceIsRead` 原類別 docstring**：
> 🔴 **立案：這一格此前完全沒有人守，而它沉默了九天。** 立案的普查數字與「三道既有機械物為何一條都沒說話」的逐條對號，**唯一真相源＝`tools/lib/hook_wiring.py` 的〈執行期證據〉區塊註解**（本檔刻意不複寫：那些數字是量測值，抄第二份就會漂移，而只有一份會被改）。現查：`grep -n hook_non_blocking_error tools/lib/hook_wiring.py`。本組守的是**判準本體**（純函式、合成輸入、紅綠雙向）。方案 B（DEF-200-316）起 `by_design_fail` 桶已刪、`runtime_carrier_verdict()` 不再收 `on_windows` 引數——三態分類收斂成兩態（native／alien），與平台無關（見該函式 WHY）。

**`_SPEAKS_FIXTURE` 原註解區塊**：
> 方案 B（DEF-200-316）起沒有平台分支這件事了：單一載具形態下失敗只有兩種分類（native／alien），與 os.name 無關，故此處不再是三元式。🔴 方案書原文誤植「_NATIVE_CARRIER_EACCES 永遠是 native」——經本包驗證（見 `runtime_carrier_verdict()` 的 ours 判準與上方兩個常數改名後的 docstring），實際恰好相反：唯一那條 Windows 形態載具失敗（`_THE_CARRIER_ENOENT`）才是永遠 native；舊 POSIX 專屬字面（`_STALE_POSIX_LITERAL_EACCES`）永遠是 alien。「_SILENT_FIXTURE」這個名字也不再真的「安靜」（alien 現在也真的出聲，見下方「test_the_by_design_failure_alone_keeps_the_stop_guard_quiet」已刪除）——保留這格只是為了驗證「兩個一起失敗時，target 名字不會被蓋掉」。

**`test_missing_carrier_is_red_on_posix_too` 原 docstring**：
> 方案 B（DEF-200-316）起哲學反轉：POSIX 上**應該**關心這條路徑——它現在是兩平台共用的**唯一**載具宣告，不再是「另一平台專屬、與我無關」。🔴 舊格「test_the_windows_criterion_is_silent_on_posix」已刪：R80 SA-05 立下的「POSIX 上不得對 Windows 專屬載具發言」（DEF-101-766 判例）本身不變，但方案 B 讓這個路徑不再是單平台專屬——存在性檢查兩平台共用同一份 `exists()` 判準（見 `carrier_liveness_problems()` 本體），對稱於既有的 `test_a_missing_carrier_is_red_on_windows`。

**`TestPosixSymlinkHealth` 原類別 docstring**：
> POSIX 側 symlink 身分＋可執行＋版本健康檢查（方案 B／DEF-200-316，取代原「TestPosixCarrierLiveness」：舊制驗的是「宣告的 `.venv/bin/python` 是否存在」，現在存在性已由呼叫端 `exists()` 驗過，本類別只驗 symlink 是不是一顆健康的連結）。沿革已搬至 CrossPlatform_R122_Guard_Prose_Migration.md〈TestPosixCarrierLiveness 立案（與 Windows 側不對稱）〉。

**`test_a_parent_relative_carrier_is_not_a_false_positive` 原 docstring**：
> A2b 的正向自證：帶 `../` 的載具（子專案／SDD 各版唯一可行的寫法）必須放行。方案 B 起每個 block 只剩單一 Windows 形態載具（POSIX 半邊已刪，見 `hook_wiring.hook_form_problems` 判準 B／E）。

**`tools/lib/hook_wiring.py` 原 M9 立案普查區塊**（29 行，壓成 6 行 pointer）：
> 🔴 為何靜態那三道全都看不到「載具解析不到」（M9 立案，本輪現查得出的空格）
> ---------------------------------------------------------------------------
> 現查（母體＝本機 `~/.claude/projects/<slug>/` 全部 1,061 支逐字稿）：`hook_non_blocking_error` 共 **217** 筆，其 stderr **全部** 是同一句 `ENOENT: no such file or directory, posix_spawn '<repo>/.venv/Scripts/pythonw.exe'`——分佈 PreToolUse 86／PostToolUse 72／SessionStart 40／**Stop 19**，跨 2026-08-12 ~ 2026-08-21（九天）、Stop 那 19 筆分屬 16 個不同 session。
>
> ⇒ 第一個結論與直覺相反：**這不是 Stop 專屬的缺陷**。四個事件全中，因為每個 block 依形態判準 E 都必須成對（Windows 一條 ＋ POSIX 一條），而 mac 上 Windows 那條每次必然 ENOENT。「Stop 只有 19 筆」不是它比較少壞，是 attachment 落盤本身有偏差（見下）。
>
> 三道靜態機械物為何一條都沒說話，逐一對號：
> · `hook_form_problems()`（A~F）：**成對是它要求的**，兩條都在 ⇒ 判綠是正確的。
> · `carrier_liveness_problems()`：非 Windows 第一行就 `return posix_carrier_problems(...)` ⇒ 結構上**看不到** Windows 那條。這是刻意的（外平台載具不存在是設計，不是缺陷），但代價是「宣告↔實況」這條綁定在每個平台**只綁一半**。
> · `tools/check_hooks_liveness.py`：檔頭自陳射程＝git hooks 生效性 ＋ 載具**存在性**，兩者都是靜態讀檔。
> ⇒ 缺的那一格不是「再加一條靜態判準」，是**沒有任何東西讀執行期證據**。而執行期證據一直都在（逐字稿裡的 hook attachment），只是零讀者——與本輪 M8 判過的「痕跡沒有自動讀者 ⇒ 它不是機制」同型。
>
> 🔴 第二個結論（判準能做到什麼、做不到什麼，是量出來的）：`hook_success` **只有在 hook 真的印了東西時才落盤**——全母體 11,438 筆 success 逐筆檢查，stdout 或 stderr 至少一個非空的有 11,438 筆、兩者皆空 **0 筆**；而根層六支守衛安靜時一筆都不留（全母體只有 14 筆屬於根層 hook，其餘 11,424 筆全是會固定印字的 SDD 三支）。⇒ 「某個目標零 success」**不能**當成「它沒跑起來」，那會對每一支安靜的守衛假紅。可判的只有**失敗**那一半，所以本判準只問一件事：**這次失敗的是不是本平台自己那條載具**。

### 誠實劃界（C8）

- `problems[-8:]` 的「最新」是**依 attachments 傳入順序**取尾端，不是依時間戳重新排序——若呼叫端傳入亂序 attachments，「最新」的語意會失真；本輪未新增時間戳排序層，沿用既有「逐字稿本身即順序」假設。
- `healed_fail` 只治癒**同一顆**載具（`_is_ours_attachment()` 判準相同才算同一顆）；不同 hook 目標各自獨立計算「之後有沒有成功」，不會互相治癒。

## C9 續航鏈載具鑑別力（主控親跑根層全套抓到的第三支漏盤，收尾單人窗口）

### 根因

主控親跑 `python tools/run_root_unittests.py` 抓到 REAL_RC=1、恰 1 支紅：`tools/tests/test_mac_endurance_r83.py::HookWiringReachesThisPlatformTest::test_the_guard_has_a_posix_carrier_on_both_endurance_events`。它讀真實 `.claude/settings.json`，斷言 `context_budget_guard.py` 在 `SessionStart`／`PostToolUse` 兩個事件上各有一條「不含 `Scripts`／`pythonw`」的 POSIX 載具——方案 B 下 POSIX 條目已刪，斷言前提結構性消失。這是設計書 D2c 測試影響盤點漏列的第三支（前兩支為 `AISDLC_SDD/scripts/tests/test_hook_wiring_cwd_safety.py` 與 `tools/tests/test_block_destructive_git_r83.py::test_it_is_exec_form_with_both_platform_carriers`，皆已於前一輪修復）。

紅的逐字輸出：
```
FAIL: test_the_guard_has_a_posix_carrier_on_both_endurance_events
AssertionError: [] is not true : SessionStart 只有 Windows 載具 ⇒ mac 上整條續航鏈不會被叫到
```

### 原斷言原文（逐字保全）

```python
def test_the_guard_has_a_posix_carrier_on_both_endurance_events(self) -> None:
    settings = json.loads((_REPO_ROOT / ".claude" / "settings.json")
                          .read_text(encoding="utf-8"))
    for event in ("SessionStart", "PostToolUse"):
        carriers = [entry.get("command", "")
                    for block in settings["hooks"].get(event, [])
                    for entry in block.get("hooks", [])
                    if any("context_budget_guard.py" in str(a)
                           for a in entry.get("args", []))]
        self.assertTrue(carriers, f"{event} 完全沒有掛 context_budget_guard")
        posix = [c for c in carriers if "Scripts" not in c and "pythonw" not in c]
        self.assertTrue(posix, f"{event} 只有 Windows 載具 ⇒ mac 上整條續航鏈不會被叫到")
```

### 修法（保留原鑑別力「續航鏈在本平台叫得到」，換成方案 B 的判準）

改名為 `test_the_guard_carrier_on_both_endurance_events_is_the_single_recognised_carrier`：
1. 對兩事件各自斷言 `carriers` 非空（不變）；每條 carrier 皆 `hook_wiring.win_carrier_kind(c) == "venv"`（唯一那條 Windows 形態載具、走根層 `.venv`）。
2. 合成注入（不碰真磁碟，同 D6 紀律）：`hook_wiring.carrier_liveness_problems(settings, str(_REPO_ROOT), on_windows=False, exists=lambda _p: True, is_symlink=lambda _p: True, readlink=lambda _p: "../bin/python", is_exec=lambda _p: True, probe=lambda _p: ("/usr/bin/python3", (3, 12)))` 斷言回 `[]`——即「在符號連結健康的 POSIX 世界裡這條佈線會被叫到」。
3. 新增負向格 `test_a_missing_symlink_still_breaks_the_endurance_chain`：同一份 settings 但 `is_symlink=lambda _p: False` ⇒ `problems` 非空，證明鑑別力沒有隨方案 B 一起被拿掉。
4. 類別 docstring 補一句方案 B 起「叫得到」由單一載具＋symlink 健康判準保證，指回本節。

### 零信任掃描（同型缺陷普查）

`grep -rn '"Scripts" not in\|"pythonw" not in' tools/tests/*.py AISDLC_SDD/scripts/tests/*.py AutoClaude/tests/tools/*.py` 全 repo（三棵測試樹）：僅本檔（本節新寫的 docstring 逐字引用舊斷言，非活程式碼）命中，**無其他同型「期待 POSIX 條目存在」的活斷言殘留**。`tools/tests/test_mac_readiness_r82.py`（D2b 已修）與 `tools/tests/test_check_hooks_liveness.py`（D2/D2b 已修）皆已是方案 B 語意（`is_symlink`／`readlink` 注入健康值），非同型缺陷。

### 驗證

```
$ python -m unittest test_mac_endurance_r83.HookWiringReachesThisPlatformTest -v
test_a_missing_symlink_still_breaks_the_endurance_chain ... ok
test_the_guard_carrier_on_both_endurance_events_is_the_single_recognised_carrier ... ok
Ran 2 tests in 0.001s
OK
```
```
$ python -m unittest test_mac_endurance_r83
Ran 113 tests in 2.278s
OK
```
`ruff check tools/tests/test_mac_endurance_r83.py`：All checks passed!
