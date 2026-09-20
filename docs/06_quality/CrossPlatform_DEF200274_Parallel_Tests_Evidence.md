# DEF-200-274 證據檔：根層 tools/tests 本機平行執行（opt-in）

> 本檔為 `docs/06_quality/AutoSDD_Defect_Log.md` 該列的體積守門接收端（`ROW_MAX_BYTES` 洩壓）；
> 列上只留一句話與本檔指針，逐條重驗所需的原文與逐字終端輸出住這裡。
> 命名刻意不帶 `R<N>` 輪號：本任務不屬於帳本的輪次迭代序列（`current_round()` 現查為
> 100），是掌舵者直接提問、由 AISDLC 角色化 Workflow（Architect→SA→SD→Developer→雙審）
> 一次性落地與收尾，故比照既有姊妹檔（`CrossPlatform_Scan_Dimensions.md`、
> `CrossPlatform_Maturity_Criteria.md`）的零輪號慣例命名。

## 原始要求（DEF-200-274，2026-09-07 立案）

根層測試 runner（`tools/run_root_unittests.py`）純序列跑，未利用 Mac 多核心；全套約 4000+ 支
測試跑 12~13 分鐘，拖慢每輪收尾驗證。要求：評估 `pytest-xdist`／`unittest-parallel`；落地前
須確認 `leak_fence()`／`skip_tag_policy` 站點普查／`MIN_TESTS` 收集數三項監控在平行下不失真，
雙平台（macOS／Windows）皆可用。

## 第一輪：AISDLC 角色化設計與落地（Workflow run wf_b86d35da-f78）

**Architect 裁決**：採方案 (a) subprocess-per-module 分片，父行程用小型 JSON 彙總協定收集各
分片結果，以環境變數 `AUTOSDD_PARALLEL_TESTS`（`=1` 開啟，未設/非 1 完全走現行序列路徑）
opt-in、預設關閉。理由：本檔四層監控（MIN_TESTS/discovery、skip 站點普查、leak_fence、
execution_gap）全部靠一個真實 `unittest.TestResult` 物件的欄位驅動，subprocess 方案讓每個
獨立直譯器行程算出這些原始值再序列化成 JSON，parent 端幾乎零改動地餵給既有 `report_*` 函式；
同時完全避開 spawn 模式下 pickle `TestResult`/`TestCase` 的已知痛點，subprocess 語意在
Windows/macOS 上一致。

**被拒絕的替代方案**：(b) `multiprocessing.Pool`/`ProcessPoolExecutor` 直接分派
`TestSuite`——`TestResult`/`TestCase` 跨行程 pickle 不穩定、spawn 模式下每個 worker 會重新
執行模組頂層程式碼；(c) `pytest-xdist`——需要把整個測試套件從 stdlib unittest 換成 pytest，
等同重寫 leak_fence／skip 站點普查／execution_gap 三層監控賴以運作的 `TestResult` 介面；
(c') `unittest-parallel`（第三方套件）——新增外部相依、分片粒度不保證暴露本檔監控所需的
`is_fixture`／完整 `known_ids` 中繼資料。

**落地檔案**：新檔 `tools/lib/parallel_shard.py`（分片、worker、彙總協定）；
`tools/run_root_unittests.py` 插入環境變數三元分支（未設時逐字沿用原本
`unittest.TextTestRunner(verbosity=1).run(suite)` 那一行）；
`tools/tests/test_run_root_unittests.py` 新增 `ParallelShardMergeSmokeTest`（純函式驗證
`merge_results()`）。

**本機（macOS，Darwin 25.6.0 arm64）全套真跑基準**（4034 支測試，MIN_TESTS 4033→4034）：

```
序列：python3 tools/run_root_unittests.py
  ✅ 發現 4034 個測試（下限 4034）；Ran 4034 tests in 724.060s；OK (skipped=46)；RC=0 ELAPSED=740s

平行：AUTOSDD_PARALLEL_TESTS=1 python3 tools/run_root_unittests.py（8 workers）
  ✅ 發現 4034 個測試（下限 4034）；skip census 46 支（platform=46／其餘 0）；
  [M6 id 集合] ✅ 集合關係成立；RC=0 ELAPSED=257s
```

**加速比**：740s → 257s（約 2.9x，8 worker；遠低於 8x 理論值——最重的一組 shard 依
`weighted_shards()` 現行權重（**測試方法數**，非 LOC；程式碼與 docstring 逐字如此，本行
2026-09-08 第三輪複審訂正此前「依 LOC 權重」的誤述）仍獨占約 210s，屬已知、留待後續優化的
效率議題，非正確性問題；第三輪複審另以乾淨環境重測見下節，實測到同一失衡現象更明顯的
一次復現）。

**正確性核對**：兩次收集數／指紋皆相同（`8e1c7c5370f8`）；rc 皆 0；skip 46 支集合排序後
逐行 diff 為空（僅輸出順序不同，因平行模式依 shard 完成順序而非模組字母序，屬預期差異）。

**兩位獨立審查者**（read-only 複核，未重跑重型套件）：兩者皆 **APPROVE_WITH_CONDITIONS**
（非 REJECT，對當下 opt-in 落地無 blocking）：

- 審查者 A（正確性/回歸）：major——`run_parallel()` 對 shard 崩潰 `raise SystemExit`，會穿透
  `sentinel_lifecycle.leak_fence()` 的 `rc = run()`（無 try/except），讓其收尾快照與洩漏比對
  整段沒有執行；minor——兩個已修 bug（worker stdout 被孫行程 fd1 污染／
  `AUTOSDD_PARALLEL_TESTS` 遞迴洩漏進巢狀自測）當時只有手動驗證，無自動回歸鎖；minor——
  env 未設時走舊分支僅靠人工跑一次全套佐證，無結構化測試鎖定。
- 審查者 B（跨平台/併發安全）：major——至少 15 支測試涉及真實 OS 排程器狀態或共享追蹤
  目錄，跨 shard 並發執行的互踩風險未排查；major——`stderr` 未重導向，理論上有 pipe
  backpressure 卡死風險；major——當時無真的 spawn subprocess 的整合測試覆蓋兩個已修 bug；
  minor——Windows 未經真機驗證。blocking（僅擋「標為 fixed/closed」，不擋此次 opt-in 落地）：
  跨 shard 資源互踩排查、補整合測試、Windows 真機驗證三項需在結案前完成。

## 第二輪：修復 leak_fence 繞過（Workflow run wf_8eef3b67-deb）

**修法**（`tools/lib/parallel_shard.py::run_parallel()`）：shard 崩潰時不再 `raise
SystemExit`，改為印出完整崩潰診斷（哪個 shard、哪些模組、完整 stdout/stderr）後，把崩潰
資訊包成一筆合成 `errors` 條目併入正常呼叫 `merge_results()` 的結果，正常 `return`。
`wasSuccessful()` 因此自然為 `False`、`rc` 依然非零，但 `leak_fence()` 的 `rc = run()`
這一行能完整執行完畢，其後的 `jobs_after` 快照、洩漏比對、審核 log 落檔皆正常照跑。

**驗證方式（端到端真測，非僅結構推理）**：新增
`ParallelShardCrashDoesNotRaiseTest`（崩潰路徑不拋例外、`wasSuccessful()==False`、`errors`
內含崩潰模組名與原始 stderr）與
`ParallelShardCrashLeakFenceIntegrationTest`（把會讓 shard 崩潰的 `run_parallel()` 呼叫包進
真正的 `sentinel_lifecycle.leak_fence()`，只 mock 排程後端與暫存目錄，斷言不拋
`SystemExit`、`rc==1`、假後端 `list_jobs()` 恰被呼叫 2 次〔收尾前後各一次〕、痕跡檔落地）。
兩支測試皆先在「暫時改回 `raise SystemExit`」的版本上跑過一次確認會失敗（
`AssertionError: leak_fence() 的 rc = run() 被 SystemExit 打斷`），再切回修復版確認轉綠，
證明測試對此回歸真的有鑑別力。

**重跑驗證**：`ruff check tools/` 全綠；全套平行模式重跑兩次（rc 皆 1、4036 蒐集／
7 failures／0 errors、無任何 shard 崩潰診斷輸出）——7 個失敗經核對與本次修法無關
（4 支源自 `AutoSDD_Defect_Log.md` 本列先前超過 `ROW_MAX_BYTES` 700 bytes 上限所觸發的
`TestR79RowByteCeiling`——已在本輪一併處理，見下節；3 支源自本輪新增 187 行測試觸發
`test_adr_xplat001_c1c2_lock.py` 的 guard-line 行數棘輪，屬既有慣例的收尾單人窗口重釘
範疇，非本次修法引入的邏輯錯誤）。獨立審查者複核：**APPROVE**（僅 1 筆 note 級發現，
即上述 guard-line 棘輪待重釘，非阻塞）。

**誠實劃界（修復後仍未涵蓋的邊角，第二輪落地當時）**：`run_parallel()` 對 `Popen()` 呼叫前
本身拋出的非 `SystemExit` 例外，或 `merge_results()` 因不完整 payload 拋 `KeyError`，本輪
未處理，`leak_fence()` 對它們仍無 try/except；不屬本次「shard 崩潰以 SystemExit 回報」這一條
具體路徑的目標範圍。**（2026-09-08 第三輪複審已修復此邊角，見下節。）**

## 帳本 ROW_MAX_BYTES 超標處置（本輪一併收斂）

上一輪落地時，`AutoSDD_Defect_Log.md` 該列的狀態欄寫入過長全文（2206 bytes），觸發
`test_check_defect_log_crossref.py::TestR79RowByteCeiling` 兩支失敗。依該測試紅字指路
的合法出口（帳本列是索引，長文搬進 `docs/06_quality/` 具名證據檔）處置：**本檔即為那個
搬遷目的地**，並已在 `tools/lib/governance_docs.py::_GOVERNANCE_DOCS` 登記（檔名
`CrossPlatform_DEF200274_Parallel_Tests_Evidence.md` 符合 `_GOVERNANCE_DOC_GLOBS` 的
`CrossPlatform_*.md` 樣式，`unregistered_governance_docs()` 對它結構上可見）；帳本列已
縮回一句話＋本檔指針，未把 ID 補進 `OVERSIZE_ROW_GRANDFATHERED`（那是砸溫度計）。

## 第三輪：對抗式獨立複審收斂（收尾單人窗口，2026-09-08）

**任務前提**：本輪明文要求不採信前兩輪的自我陳述（作者自證不計分），對上一節列出的
五項待辦逐一獨立重新查證，並自行對照現有程式碼與實測結果，找出前兩輪未覆蓋的其他問題。

**問題 5（stderr backpressure）——查證結果：真實可重現缺陷，已修復。**
`run_parallel()` 用 list comprehension 一次性併發啟動全部 shard 的 `Popen`（stdout/stderr
皆設 `PIPE`），卻用序列 `for` 迴圈依序呼叫每個 shard 的 `.communicate()`；`_worker_main()`
只把自己的 stdout（fd1）重導向 devnull，stderr（fd2）完全沒被排空。用兩個合成模組
（SLOW 只 `sleep`；LOUD 立即寫入超過 OS pipe buffer 的內容到 stderr）逼進不同 shard 且
LOUD 排在 SLOW 之後被 `communicate()`，修復前 LOUD 的 stderr 寫入耗時（實測 2.520s）幾乎
精確等於 SLOW 的 `sleep` 秒數（2.5s）——證實 backpressure 真的會把「平行」的 shard 靜默
串行化。**修法**：新增 `_communicate_all()`，改用每個 shard 各一條 thread 呼叫自己的
`.communicate()`，取代原本的序列迴圈；修復後 LOUD 的寫入耗時降到 < 0.5s，與 SLOW 的
`sleep` 秒數解耦。回歸測試：`ParallelShardStderrBackpressureRegressionTest`（先在暫時
還原序列版本上跑過一次確認會紅，再切回修復版確認轉綠）＋
`ParallelShardRealSubprocessProtocolIntegrationTest`（同時覆蓋協定通道 happy path 與此
情境，`join(timeout=17s)` 作死鎖硬性防線）。

**誠實劃界延伸（第二輪遺留的「Popen 前例外／`merge_results()` KeyError」邊角）——查證
結果：非立即可觸發的線上事故，但防禦性硬化缺口，已修復。** `merge_results()` 對缺鍵
payload 直接拋 `KeyError`（可執行復現：餵一筆缺 `testsRun` 鍵的 payload 即拋），而
`run_parallel()` 對 Popen 迴圈與 `merge_results()` 呼叫全程無 `try/except`，此類例外會
一路穿透到 `sentinel_lifecycle.leak_fence()` 未受保護的 `rc = run()`，重演與已修復
「shard 崩潰 raise SystemExit」同型的 leak_fence 繞過失效——只是觸發條件換成例外類型。
**修法**：把 Popen 迴圈／`_communicate_all`／`merge_results()` 整段包
`try/except Exception`，任何例外都合成一筆 `errors` 條目後正常 `return`；同時把 Popen
迴圈由 list comprehension 改為一般 `for` 迴圈，任一次 `Popen()` 失敗時對已啟動的 shard
逐一 `kill()`＋`wait()`，不留孤兒行程。回歸測試：
`ParallelShardRunParallelExceptionSafetyTest`（`KeyError` 不再穿透）、
`ParallelShardMergeExceptionLeakFenceIntegrationTest`（端到端包進真正的
`leak_fence()`，證明此類例外情境下收尾快照仍完整執行）、
`ParallelShardPopenFailureKillsAlreadyStartedProcsTest`（已啟動的 shard 行程被
`kill()`，非孤兒）。

**問題 2（真實 subprocess 整合測試）——已補齊。** 新增
`ParallelShardRealSubprocessProtocolIntegrationTest`：全程不 mock `subprocess.Popen`，
一次涵蓋協定通道 happy path（3 shard，涵蓋 pass/fail/error/skip/`expectedFailure`-但-
passes 五種結果型別的正確彙總）與 stderr backpressure 情境。此前三支既有 Parallel*
測試（`ParallelShardMergeSmokeTest`／`ParallelShardCrashDoesNotRaiseTest`／
`ParallelShardCrashLeakFenceIntegrationTest`）全數 mock `subprocess.Popen`，這正是
問題 5 能存活到本輪才被抓到的直接原因。

**問題 1（跨 shard 共享資源互踩）——獨立重做排查，結論：現階段風險已收斂，未發現需要
新增釘選邏輯的真實衝突。** 不採信任一方的既有結論，自行對全 repo grep
`AUTOSDD_TRACE_DIR`／`schtasks`／`launchctl` 命中的候選檔案逐一 Read 分類：其中大多數
只把這些字串當成 AST 掃描判準的合成注入語料（從未在執行期真正呼叫過），真正在執行期
觸碰 `AUTOSDD_TRACE_DIR` 的兩支（`test_claim_provenance_r86.py`、
`test_context_budget_guard.py`）皆用每次呼叫獨立的 `tempfile` 隨機路徑隔離，且後者另有
`SchedulerHygieneTest` 這道 AST 強制守衛（實跑 `pytest -k SchedulerHygieneTest` 全綠）；
額外排查固定埠號／鎖檔／`pg_real` 三類共享資源，`tools/tests/` 範圍內同樣未發現未隔離
的真實共用單例。誠實劃界：候選面是否窮盡（其他共享資源類別）仍不保證，僅是本輪已知
排查範圍內零命中。

**問題 4（guard-line 行數棘輪）——已重釘。** 本輪新增測試使
`test_run_root_unittests.py` +437 行，`test_adr_xplat001_c1c2_lock.py` 自身逐檔漂移
+26 行，護欄層累積淨額 94902 → 95520（+618，其中
`ParallelShardRealSubprocessProtocolIntegrationTest` +158 全額歸回歸鎖軌，扣除後 460
遠低於單輪上限 549）。**刻意沿用同一輪號、未另立新輪**：另立會讓
`live_repin_round()` 同時撞上三項與本缺陷完全無關的到期義務（Phase 2 §6 時效、U9
root-tools 舊尺技術債到期輪、`_REPIN_NET_CAP_DUE_ROUND`，三者的展延或清償皆非本任務
範圍），故沿用既有輪號延伸記帳，避免手術式修改範圍外溢。逐項見
`docs/06_quality/CrossPlatform_R131_Scan_Findings.md` §8。

**問題 3（Windows 真機驗證）——維持未解，誠實標記。** 本輪全程 macOS session，三份 CI
workflow 均未設定 `AUTOSDD_PARALLEL_TESTS`，平行路徑在 Windows CI 上零自動化涵蓋；本項
性質上無法在本次任務內完成，需要有人在實體或虛擬 Windows 機器上手動驗證 fd 重導向與
pipe backpressure 修復在 Windows CRT text-mode fd 語意下是否仍成立。

**加速比再測（乾淨環境，2026-09-08 第三輪）——誠實揭露一個與既有「2.9x」宣稱不符的
新發現，而非重申舊數字。** 重測前 `ps aux` 確認無殘留 `run_root_unittests`／
`parallel_shard.py` 行程、`git status --porcelain` 乾淨。本次環境
`AUTOSDD_PARALLEL_TESTS_WORKERS` 被 shell 環境預設釘在 4（非上一輪量測時使用的 8），
在此 4-worker 設定下實測：序列 572s（4042 測試，MIN_TESTS 4034→4042）；平行（4
workers）570s——**幾乎零加速比**。即時觀察：4 個 shard 行程中 3 個在數十秒內完成，
剩下一個（含 `test_doc_loc_baseline_freshness_r60.py`／`test_platform_neutral_paths.py`
／`test_pre_push_dispatcher.py` 等全樹掃描型重量檔）獨占了與序列總耗時相當的 CPU
時間，其餘 worker 提早收工後閒置——這正是 `weighted_shards()` 現行「依測試方法數」
權重（而非實際耗時）分片時，少量測試但單支耗時極長的模組會被錯配成輕量、破壞負載
平衡的具體重現，而非本輪修法引入的新回歸（兩次量測的收集數 4042、skip 46 支、rc 皆為
0，逐項比對後 skip 集合排序後 diff 為空，完全一致）。**結論**：舊「2.9x」數字很可能是
在 8-worker、且當時模組分佈剛好較均衡的情境下量得，本身未必不實，但**不具跨環境／跨
worker 數的穩定性保證**；`weighted_shards()` 的權重演算法（依測試方法數而非實測耗時）
本輪查證確認就是 evidence 檔原先記載的既知限制本體，非新增缺陷。

## 結案前待辦（誠實列出現況）

1. ~~排查跨 shard 共享資源互踩~~ ——第三輪已獨立重做排查，現階段未發現需要新增釘選
   邏輯的真實衝突（見上節「問題 1」）；候選面窮盡度未 100% 保證，留供後續複審延伸。
2. ~~補真實 subprocess 整合測試~~ ——已補齊（`ParallelShardRealSubprocessProtocolIntegrationTest`，
   見上節「問題 2」）。
3. **Windows 真機驗證——仍未解，維持 partial**：需要人在 Windows 機器上手動驗證，見上節
   「問題 3」，不可用靜態分析或既有跨平台掃描器通過來替代。
4. ~~guard-line 行數棘輪重釘~~ ——本輪已重釘（見上節「問題 4」）。
5. ~~stderr backpressure~~ ——已修復並有回歸鎖證明改前會紅、改後會綠（見上節「問題 5」）。
6. **`weighted_shards()` 權重演算法效率優化（非正確性缺陷，選擇性）**：若要把權重來源
   由「測試方法數」改為「歷史實測耗時」，或把已知重量級檔案個別拆成獨立 shard，屬效率
   優化項目，本輪未落地，留供容量決策後續處理。

僅剩第 3 項（Windows 真機驗證）與第 6 項（效率優化，非阻塞）未解。DEF-200-274 於本輪
維持 `partial`，不宣稱 `fixed`/`closed`——Windows 真機驗證這一項的性質決定它無法由
macOS-only session 完成，需交棒。

## 第四輪：work-stealing 動態派工重構 + 四方對抗式複審全修（2026-09-08／09）

### 背景

主控直接動手把 `parallel_shard.py` 由「依測試方法數貪婪裝箱成 N 個固定 shard」
（`weighted_shards()`）改成**動態工作竊取**：共用 `queue.Queue` 塞全部模組，最多
`worker_count()` 條 thread 各自認領下一個模組、自己 Popen＋自己 communicate，取代
舊版靜態裝箱；`weighted_shards()`／`_communicate_all()` 已刪除。同批新增
`LoadBalancingRegressionTest`（合成 1 個高方法數 TRIVIAL 模組＋2 個低方法數但真的
耗時的 SLOW_A/SLOW_B 模組，證明兩個 SLOW 模組會被兩條不同 thread 同時執行而非
序列化）；`ParallelShardPopenFailureKillsAlreadyStartedProcsTest` 因原本依 Popen
呼叫次序判斷成敗在多執行緒下不再可靠，改成依 argv 模組名判斷。此輪落地時因
DEF-200-275（SDD-FSM context 計量誤差誤觸 ESCALATION）中途擋下工具呼叫，Developer
角色的收尾與四方複審因此延到本節記載的這次收斂。

### 四方複審結果（逐條處理）

四方對本輪未經審查的變更（`parallel_shard.py`／`test_run_root_unittests.py`／
`quota_escalation.py`／`check_loc_budget.py`／`hook_wiring.py`／`spawn_failure.py`／
pre-commit／pre-push）跑了一輪對抗式複審，裁決 Architect＝APPROVE_WITH_CONDITIONS、
SD＝APPROVE_WITH_CONDITIONS、QA＝REJECT。逐條處理如下：

1. **Architect 阻斷①：`run_parallel()` 多執行緒例外收集有靜默漏失通道**
   （`thread_errors.get_nowait()` 只取第一筆就 `raise`，兩條以上 thread 同時失敗時
   其餘例外永遠留在佇列裡、從未被印出）——**已修復**：改為 join 完後把
   `thread_errors` 整個排空，逐筆印到 stderr，單筆時原樣 `raise` 保留原始例外型別
   （不破壞既有測試對特定例外型別的斷言），多筆時合成一個 `RuntimeError` 把全部
   `repr()` 串在訊息裡一併 `raise`。同時把「Popen 失敗偵測時效在動態佇列下變慢」
   這個非功能性變化明寫進 docstring（Architect minor finding）。見
   `tools/lib/parallel_shard.py::run_parallel()`。
2. **Architect 阻斷②：`quota_escalation.py::_write()` 的 `write_bytes` 改法理由
   虛構**（註解宣稱替代的是 `Path.write_text(newline=)`，但實際被取代的是
   `Path.open(newline=)`，後者在 macOS 系統 Python 3.9 上完全正常，commit 89c4e91
   當時修的正是這件事，本輪的註解把已修好的舊 bug 誤植到新變更上）——**已修復**：
   保留 `path.write_bytes(text.encode("utf-8"))` 這個寫法（已獨立驗證與
   `.open("w", encoding="utf-8", newline="\n").write(text)` 對純 `\n` 字串逐位元組
   等價、且是 guardrail_lib tier 400 行預算下省 1 行的必要寫法），只訂正虛構理由的
   註解本身，**不是**改回 `.open()`（第四輪第二次對抗式複審 SA/SD 交叉核對抓到本節
   先前這句「已修復：改回 .open() 寫法」與實際程式碼不符，此處已訂正為據實描述）。
3. **SD 阻斷：`check_loc_budget.py` 新增的 `hook_wiring.py` 782 行 SPECIAL_FILES
   棘輪調高，缺陷帳本裡沒有對應的具名理由列，且註解自陳「本行落地當回合尚未
   補」**——**已修復**：把 DEF-200-273（`block_destructive_git.py` 非阻斷提醒被
   `runtime_carrier_verdict()` 誤判為載具故障）的狀態欄由 `open（未指派）` 改為
   `fixed（commit fab2d0e）`，敘明 `_SPAWN_FAILURE_RE` 修法與連帶的 782 行棘輪
   理由；同步把 `check_loc_budget.py` 該處註解的「尚未補」文字更新為指向
   DEF-200-273。
4. **QA 阻斷①：`tools/lib/spawn_failure.py` 是 git 未追蹤檔，`hook_wiring.py`
   `import spawn_failure` 會在 fresh clone 上 ImportError**——**已核實、未修復**：
   本 session 的任務書明確指示「不要執行 git add/commit/push」，而修復此問題唯一
   的手段是 `git add tools/lib/spawn_failure.py`。這是本輪唯一因外部約束而**無法**
   在本 session 內完成的項目，留給下一個有 git 寫入權限的窗口在 commit 前執行
   `git add tools/lib/spawn_failure.py`（檔案內容本身已核實正確，SD／QA 兩方各自
   獨立驗證過）。
5. **QA 阻斷②：端到端執行 rc≠0（11 failures + 2 errors）**，三類根因：
   (a) 護欄層行數棘輪未同步（`test_run_root_unittests.py` +92 行）；
   (b) 缺陷帳本逐列 700-byte 上限／存量超標總量棘輪／淨額棘輪三項違規；
   (c) `check_loc_budget.py:178`／`spawn_failure.py:2` 的「R135」輪號註記超前帳本
   當前輪（`current_round()` 現查為 100）——**均已修復**：
   - (a) 見下方「guard-line 行數棘輪重釘」小節。
   - (b) DEF-200-274／DEF-200-275 兩列瘦身至 ≤700 bytes（本檔即為瘦身後的接收
     端），DEF-200-275 另建 `CrossPlatform_DEF200275_Context_Metering_Evidence.md`
     承接全文；淨額棘輪由 DEF-200-273 改標 `fixed` 抵銷（見上第 3 點）。
   - (c) 兩處註解的「R135」改為指名 commit `fab2d0e`，不再宣稱任何輪號（避免對
     一個未經證實對應哪個計輪序列的數字做出無法查證的宣稱）。
6. **QA 阻斷③：平行模式下的 TOCTOU 競態產生偽 `FileNotFoundError`**——本 session
   親自重現（`test_platform_neutral_paths.TestTextIoDeclaresEncoding.
   test_debt_ratchet_is_exact_and_shrink_only` 對 `_zzz_protocol_repro_a_mixed_*.py`
   ERROR）：`tools/tests/` 內多支治理測試（`run_unit_scan()`／
   `TestTextIoDeclaresEncoding._scan_repo()`／`_scan_file()`）會先 glob
   `tools/tests/*.py` 拿到檔案清單，再逐一 `read_text()`；`LoadBalancingRegressionTest`
   ／`ParallelShardRealSubprocessProtocolIntegrationTest` 在**不同 worker
   subprocess** 裡對同一目錄寫入並以 `addCleanup` 刪除合成暫存模組
   （`_zzz_*.py`），兩步之間的窗口造成競態——**已修復**：新增共用輔助函式
   `_read_text_or_none()`（`tools/tests/test_platform_neutral_paths.py`），檔案
   在讀取當下消失即回 `None`、呼叫端一律 `continue`／回空清單（消失的檔案本來
   就不是治理掃描要看的內容，容忍它消失不會掩蓋任何真實違規），套用到
   `run_unit_scan()`、`TestTextIoDeclaresEncoding._scan_repo()`、`_scan_file()`
   三個實際會被此競態命中的呼叫點。
7. **QA minor：`quota_escalation.py` 註解失實**——與 Architect 阻斷②同一處，已在
   第 2 點一併修復。

### guard-line 行數棘輪重釘

本輪 `tools/tests/` 護欄層行數 95520 → 95762（+242，全額歸回歸鎖軌）。除
`test_run_root_unittests.py`（work-stealing 重構回歸測試＋對抗式複審收斂追加的
`ParallelShardMultipleThreadFailuresAreAllReportedTest`）／`test_platform_neutral_paths.py`
（`_read_text_or_none()` TOCTOU 緩解）兩項功能性成長外，本輪落地時一併觸發並兌現／
展延了四項各自獨立的到期義務：`_REPIN_NET_CAP_SCHEDULE`（cap 549→548）、
`_ROOT_TOOLS_OLD_SCALE_DEBT_DUE_ROUND`（135→137，具名展延）、
`_FROZEN_PREFIX_REWRITE_LEDGER`（指紋接鏈）、`_PHASE2_REVIEW_LOG`（追加
`[維持觀察]` 列）——這四項與本輪主軸（parallel_shard.py 修復）無直接關聯，純粹是
`_GUARD_LINES_REPIN_LOG` 推進到 R135 這個輪號時，四個各自獨立的到期輪計數器恰好
同時到期而觸發（`_ROOT_TOOLS_OLD_SCALE_DEBT_DUE_ROUND`／`_REPIN_NET_CAP_DUE_ROUND`
两者皆早由前幾輪具名展延至 135）。逐項數字、每一步的計算過程與到期義務處置理由
完整記載於 `CrossPlatform_R135_Scan_Findings.md`（本節不重複），該檔命名依既有
`CrossPlatform_R<N>_Scan_Findings.md` 慣例（款(9) `_PER_FILE_LIST_RE` 要求）。

### 本 session 端到端重驗（逐字見任務完成回覆）

修復後重跑 `cd tools/tests && .venv/bin/python3 -m unittest test_run_root_unittests
-v -k Parallel -k LoadBalancing`、`test_adr_xplat001_c1c2_lock.TestGuardLayerRatchet`、
`test_check_defect_log_crossref`（全套）、`AUTOSDD_PARALLEL_TESTS=1
AUTOSDD_PARALLEL_TESTS_WORKERS=4 python tools/run_root_unittests.py` 端到端兩次，
逐字輸出見本輪任務回覆（未落成第二份副本，避免與回覆內容產生第二個會漂移的
真相來源）。

## 第四輪第二次對抗式複審：型別缺口＋計時脆弱性＋文件同步收斂（2026-09-09）

### 背景

第四輪初版修復（上一節）落地並經 Architect／SD／QA 三方 APPROVE_WITH_CONDITIONS／
APPROVE_WITH_CONDITIONS／REJECT 收斂後，同一批檔案又跑了第二次四方對抗式複審
（Architect／SA／SD／QA），裁決 Architect＝REJECT、SA＝APPROVE_WITH_CONDITIONS、
SD＝APPROVE、QA＝未回報（null）。逐條處理如下：

1. **Architect 阻斷①：`LoadBalancingRegressionTest` 的計時斷言有複合延遲風險**
   （`worker_count=2` 下 TRIVIAL 若被某條 thread 搶先認領，該 thread 完成後會
   回頭再認領剩下的那個 SLOW，形成「兩次 Popen 啟動延遲疊加」，使 1.6x 安全邊際
   在 Windows／高負載 CI 上的實際餘裕不明）——**已修復**：改用 Architect 建議的
   選項 (c)，`worker_count` 由 2 改為 3（＝模組數），讓 3 個模組在啟動瞬間各自
   被 1 條 thread 一次認領到位、全程零佇列競爭，徹底移除複合延遲來源（而非只是
   加大安全邊際掩蓋它）。docstring 同步記錄改法理由。見
   `tools/tests/test_run_root_unittests.py::LoadBalancingRegressionTest`。
2. **Architect 阻斷②：`run_parallel()` 的例外安全網對非 `Exception` 子類的
   `BaseException`（`SystemExit`／`KeyboardInterrupt`／`GeneratorExit`）有型別
   缺口**（worker thread 用 `except BaseException` 蒐集後，若合成例外重新
   `raise`、交外層 `except Exception` 接住，非 `Exception` 子類會直接穿透）——
   **已修復**：抽出 `_crash_fallback(started, exc)` 共用函式，thread_errors 路徑
   改成呼叫端拿到例外物件後**直接**呼叫該函式收尾，不再經過 `raise` 依賴外層
   `except` 篩選型別；外層 `except Exception` 對 main thread 自己的
   `KeyboardInterrupt`（如 `t.join()` 期間被 Ctrl-C 中斷）刻意維持不攔截，
   docstring 明寫這個取捨。新增回歸鎖
   `ParallelShardWorkerThreadBaseExceptionDoesNotEscapeTest`（用 `SystemExit`
   驗證，`OSError` 換不出這個型別缺口）。見
   `tools/lib/parallel_shard.py::_crash_fallback()`／`run_parallel()`。
3. **SA 阻斷①：`MIN_TESTS` 未同步重釘**（本輪新增測試方法後 discovery 實測
   4045，`MIN_TESTS` 仍是 4042）——**已修復**：以唯讀 discovery 探針實測直接
   填入 4045，落款記錄成長來源（`ParallelShardWorkerThreadBaseExceptionDoesNotEscapeTest`），
   `python tools/sync_onboarding_baselines.py --write` 同步回填 `ONBOARDING.md`
   §7 的 `rootunit-baseline-live:` 格（`--check` 覆核 rc=0）。
4. **SA 阻斷②：`parallel_shard.py` 模組層 docstring（第 1~31 行）仍描述舊版
   靜態分片設計，與 `run_parallel()` 內已正確描述的動態工作竊取設計矛盾**——
   已修復：改寫成「依模組拆成獨立派工單位、塞進共用佇列，最多 `worker_count()`
   條 thread 各自認領」的敘述，與 `run_parallel()` docstring 一致。
5. **SA 阻斷③：pre-commit／pre-push 的 venv 偵測修法缺具名缺陷帳本理由**（註解
   只模糊指向「DEF-200-274 系列同類病灶的另一個發作點」，查無對應 DEF-ID）——
   已修復：新開 `DEF-200-276`，狀態 `fixed（本輪）`，指向本節。
6. **SA minor：`ParallelShardStderrBackpressureRegressionTest` docstring 前後
   用語不一致**（開頭已改寫成 work-stealing 語言，但「修復前」段落仍沿用
   「shard 0/1」字面）——順手修復：改寫成「LOUD／SLOW 那個模組」的敘述，並
   明確標註「修復前（第三輪）」／「修復後（第四輪動態工作竊取）」兩個階段。
7. **QA：本輪未回報裁決（`null`）**——無對應阻斷條件需要處理。

### 本輪重驗（逐字，2026-09-09）

```
$ cd tools/tests && .venv/bin/python3 -m unittest test_run_root_unittests -v -k Parallel -k LoadBalancing
...
Ran 12 tests in 7.233s

OK
```

（較上一輪的 11 支多 1 支：新增的 `ParallelShardWorkerThreadBaseExceptionDoesNotEscapeTest`。）

discovery 探針（唯讀，`countTestCases()`，不執行任何測試）：`4045`，與重釘後的
`MIN_TESTS` 一致；`python tools/sync_onboarding_baselines.py --check` rc=0。

`LoadBalancingRegressionTest` 連續 3 次獨立執行皆 `ok`（`worker_count=3` 版本，
逐次耗時見任務完成回覆）；額外手動驗證 `worker_count=1`（強迫兩個 SLOW 模組
排隊）重跑同一情境，耗時 5.175s（逼近 `2 × 2.5s`），佐證新設計與舊版行為在
計時斷言上仍能明確區分。

### 第四輪第三次收斂（收尾單人窗口，2026-09-09）——誠實揭露 QA 鏡頭全程未曾真正執行

**背景**：第四輪的兩次對抗式複審（本節上方）與其後再跑一次的第三輪複審，QA 這個
鏡頭**三次全數**因（本次任務環境的）安全分類器攔截而回報 `null`，從未真的完成過
一次 QA 驗收。前一批收斂記錄把「QA 回報 null」直接讀成「無阻斷條件需要處理」——
這個假設本身沒有被質疑過，是本輪誠實補上的缺口，不是新發現的程式碼問題。

**第三輪 Architect（APPROVE）／SA／SD（皆 APPROVE_WITH_CONDITIONS）找到的阻斷條件
與處置**（收尾單人窗口逐條核實並修復，非自證）：

1. `tools/lib/spawn_failure.py` 仍是 git 未追蹤檔——**這是唯一會讓「功能完備」
   在字面上失敗的項目**：`tools/lib/hook_wiring.py` 已無條件 `import spawn_failure`，
   commit 前必須把這支新檔與其餘 6 個已修改檔案一起 `git add`，否則任何 fresh
   clone／CI checkout 會在 import 階段崩潰。**已記錄為 commit 前必做步驟**（見本檔
   結尾〈結案前待辦〉）。
2. 本檔上一節「Architect 阻斷②…已修復：改回 `.open()` 寫法」一句與
   `tools/lib/quota_escalation.py` 現況（仍是 `write_bytes`）矛盾——**已訂正**：
   改為據實描述「保留 `write_bytes`、只訂正虛構理由的註解」（該寫法已獨立驗證與
   `.open(newline="\n")` 逐位元組等價，且是 LOC 預算下必要的省 1 行寫法）。
3. `tools/lib/parallel_shard.py`（3 處）與 `tools/tests/test_run_root_unittests.py`
   （2 處）把同一批修復稱為「第五輪複審」，與本檔／`R135`／`R136` findings 檔的
   「第四輪第二次對抗式複審」用語不一致，形成懸空輪號參照——**已全部訂正**為
   「第四輪第二次對抗式複審」。
4. `ONBOARDING.md` §7 表①「（量測時點 2026-08-19）」與本輪實際重釘日期
   （2026-09-09）矛盾，是 R96 已判過的同型舊病復發——**已訂正**日期。
5. `LoadBalancingRegressionTest` docstring 用 `worker_count=2` 的手算例子論證
   測試設計動機，但測試本體實際 mock 的是 `worker_count=3`；SD 獨立重算舊版
   `weighted_shards()` 在 n=3 下並不會把 `SLOW_A`／`SLOW_B` 分進同一 bin，故本測試
   對「已刪除的舊演算法」在其實際配置下沒有雙態鑑別力——**已訂正** docstring，
   明確承認 n=2 例子僅為動機說明，本測試真正鎖住的是「n=3 下三模組真的併發執行」
   本身。
6. SA／SD 皆點名 `AutoClaude/tools/git-hooks/pre-commit`／`pre-push` 的 `.venv`
   偵測邏輯在「檔案存在但不可執行」這個邊角案例下會靜默退回系統 python、毫無
   診斷輸出（與 Rule 12 Fail loud 精神不符，標記 minor、非阻斷）——**已順手修復**：
   兩檔皆補一行 stderr 警告，偵測到此情境時先出聲再退回。

**收尾單人窗口自行執行的 QA 等效驗證**（補足三輪皆缺席的 QA 鏡頭，逐字）：

```
$ cd tools/tests && .venv/bin/python3 -m unittest test_run_root_unittests -v -k Parallel -k LoadBalancing
Ran 12 tests in 7.222s
OK
```
（含上述 5 項文件/docstring 訂正後重跑，行為不變、全數維持通過。）

`LoadBalancingRegressionTest` 額外獨立重跑 2 次，皆 `OK`（無 flaky 跡象）。

邊角案例驗證（QA 原定任務項目）：`run_parallel(unittest.TestSuite(), tools/tests, {})`
（空 suite ＋空 module_counts）→ `testsRun=0, wasSuccessful()=True`，未崩潰、未卡死、
無除以零——`n = min(worker_count(), 0) or 1` 建立 1 條 thread，該 thread 立即命中
`queue.Empty` 收工，`merge_results([], {})` 正常回傳空結果，行為符合預期。

`ruff check` 與 `check_loc_budget.py`（`violations=0`）於本輪所有訂正後重跑皆綠；
兩支 git hook 的 shell 語法以 `bash -n` 確認無誤。

**仍誠實保留、刻意不在本輪處理的一項**（Architect 第三輪 minor finding，非阻斷）：
`_crash_fallback()` 讀取 `started` list 時未持有 `started_lock`，唯一理論競態路徑是
`threading.Thread.start()` 本身失敗（需 OS 層級資源耗盡）且發生在 for 迴圈啟動到一半
時——機率極低，且 Architect 本人明確判定「非本輪阻斷條件」。收尾單人窗口判斷：在
沒有專屬回歸測試佐證修法正確性的情況下，於收尾窗口倉促加鎖修改例外安全網這種
本輪已三度被複審驗證過的核心路徑，風險高於保留現況、留待下一輪帶測試一併處理的
風險。**留供下一輪處理，非本輪遺漏**。

## 第五輪：四方獨立複審（Architect/SA/SD/QA）全庫 TOCTOU 排查與 Ctrl-C／計時收斂（2026-09-09）

### 背景

掌舵者直接提問：派出 Architect／SA／SD／QA 四方獨立審查（各自不共享上下文，分別跑），
針對現況重新核對三題——①帳本問題是否解決、②多CPU測試功能是否完備、③是否有頭重
腳輕分配不均。四方皆親自讀程式碼／文件，QA 並親自實跑（本輪 QA 未再被安全分類器
攔截，三輪全數完成，補齊第四輪三次皆缺席的鏡頭）。

### 四方複審結果摘要

- **Architect**：`VERDICT_LEDGER_RESOLVED=partial`／`VERDICT_FEATURE_COMPLETE=partial`
  ／`VERDICT_LOAD_BALANCED=partial`。找到 4 項發現：(1) 無 per-module 計時觀測——
  work-stealing 的核心效率宣稱無從驗證；(2) 確認 `TestPathextReadsAreePlatformGuarded`
  TOCTOU 缺口為真；(3) `TestScanSurfaceParityWithSisterLock` 是架構層級問題（list-vs-list
  race，讀取端防護治不了），非局部 bug；(4，新發現) Ctrl-C 中斷時其餘 worker thread
  未被清理、非 daemon thread 卡住直譯器退出、已啟動子行程未被 kill。
- **SA**：三題判斷與 Architect 一致（皆 partial），額外指出 `ONBOARDING.md` 完全未提及
  `AUTOSDD_PARALLEL_TESTS` 開關——功能存在但無人能發現，直接構成 feature-complete
  只能判 partial 的理由；並訂正「本輪任務的真正源頭是缺陷帳本一次性提問，不是
  `AutoSDD_improving_112.md` 迭代序」。
- **SD**：逐條核實 Architect 四項發現皆屬實，並獨立在 `tools/tests/` 另外九支檔案
  （`test_subprocess_encoding_hygiene.py`／`test_no_invalid_escape_sequences.py`／
  `test_pre_push_dispatcher.py`／`test_adr_xplat001_c1c2_lock.py`／`test_ps_engine_ssot.py`
  ／`test_dev_start.py`／`test_bash_probe_spec_contract.py`／`test_mac_endurance_r83.py`／
  `test_find_git_bash_parity.py`）找到同一 TOCTOU 病灶的呼叫點，判定 Architect 建議的
  「搬離 `tools/tests/`」修法因 `_worker_main()` 硬性斷言 `start_dir == tests_dir` 而不可行，
  改採「`_zzz_` 前綴排除」集中修法。
- **QA**：實測序列 805.61s（`Ran 4045 tests in 788.378s`，real 13:25.61）vs 平行(8 worker)
  252.72s——3.19x 加速比（約 40% 理論效率），總 CPU 秒數兩次量測幾乎守恆（857.3 vs
  861.0，+0.4%），確認是乾淨比較。直接計時單一模組找到根因：
  `test_doc_loc_baseline_freshness_r60.py` 單模組耗時 163.19s，獨占平行總耗時約
  65%——這就是「頭重腳輕」問題的量化根因（277 支測試但單執行緒全樹掃描）；對照
  `test_context_budget_guard.py`（621 支測試僅 28.32s）證實「方法數」與「實際耗時」
  無關，佐證了 work-stealing 取代舊版方法數加權裝箱的設計決策。邊界案例
  （`WORKERS=1`／`WORKERS=50`）皆正確；現場複現 TOCTOU 崩潰 1/3 次（間歇性競態，
  非每次必現）。誠實揭露：8-worker 與 4-worker 兩次量測的失敗數不一致（10F/0E vs
  6F/1E），懷疑與本機背景 nightly 自動化搶資源有關，未能在本輪內完全排除。

### 修復（收尾單人窗口逐條落地）

1. **TOCTOU 病灶全庫排查修復**：十支 `tools/tests/` 檔案（Architect 原僅點名 1 支，
   SD 複核時另找到 2 支，收尾單人窗口實作時逐一核對整棵 `tools/tests/` 樹又找到
   剩餘 7 支）各補一道 `_zzz_` 合成暫存模組排除；`test_platform_neutral_paths.py`
   的 `TestPathextReadsAreePlatformGuarded` 額外疊加既有 `_read_text_or_none()`
   讀取防護（雙重保險）。
2. **Ctrl-C 孤兒行程清理**（`tools/lib/parallel_shard.py::run_parallel()`）：新增
   `stop_event`（worker thread 認領新模組前檢查）；`t.join()` 迴圈外包
   `except KeyboardInterrupt`：立旗標→排空 `pending`→kill 已啟動子行程（`started_lock`
   保護下拍照）→等所有 thread 真的結束→`raise`（不吞例外，只是先清乾淨）。誠實
   劃界：極窄殘留窗口（一條 thread 剛拿到模組、還沒檢查旗標就被排程出去）仍可能
   多起一個子行程，但 `t.join()` 保證它會被等到、不會變真正孤兒。
3. **per-module 計時觀測**：`_worker_thread_loop()` 用 `time.monotonic()` 量測每個
   模組的 wall-clock 秒數，經 `_MergedResult.module_timings` 傳給新函式
   `run_root_unittests.py::report_module_timings()`，平行模式下印出耗時排行前 5。
4. **`_crash_fallback()` started_lock 缺口**（第四輪第三次收斂刻意留給下一輪的項目，
   本輪即為該「下一輪」）：兩處呼叫端在傳入 `started` 前皆先於 `started_lock` 下
   拍照，不再依賴「呼叫時機恰好安全」這個隱性前提。
5. **`git add tools/lib/spawn_failure.py`**：已於本輪 commit 前完成（第四輪唯一因
   任務書限制無法完成的項目）。
6. **`ONBOARDING.md`**：§7 bash／PowerShell 兩區塊補上 `AUTOSDD_PARALLEL_TESTS` 開關
   的呼叫範例與 Windows-未驗證註記。

### 本輪重驗（逐字，2026-09-09）

```
$ AUTOSDD_PARALLEL_TESTS=1 AUTOSDD_PARALLEL_TESTS_WORKERS=4 python tools/run_root_unittests.py
... Ran 839 tests in 215.104s ... OK (skipped=16)
```

（涵蓋全部本輪修改檔案：`test_platform_neutral_paths`／`test_subprocess_encoding_hygiene`
／`test_no_invalid_escape_sequences`／`test_pre_push_dispatcher`／`test_ps_engine_ssot`
／`test_dev_start`／`test_bash_probe_spec_contract`／`test_mac_endurance_r83`／
`test_find_git_bash_parity`／`test_run_root_unittests`。）

`test_adr_xplat001_c1c2_lock.py` 全套 192 支獨立重跑：`OK`（含護欄層行數棘輪、
`guard_self` 分桶棘輪、`_REPIN_NET_CAP_SCHEDULE` 到期義務、`_FROZEN_PREFIX_REWRITE_LEDGER`
接鏈、`_ROOT_TOOLS_OLD_SCALE_DEBT_DUE_ROUND` 展延、文件側 guard-total 對帳，逐項見
`CrossPlatform_R137_Scan_Findings.md`）。`ruff check` 全部本輪異動檔案：`All checks
passed!`。

### 誠實劃界（本輪仍未解決）

- **Windows 真機驗證**：仍未解，本 session 全程 macOS-only。`VERDICT_LEDGER_RESOLVED`
  ／`VERDICT_FEATURE_COMPLETE` 因此維持 `partial`，不宣稱 `fixed`/`closed`。
- **run-to-run 失敗數變異**：QA 懷疑與本機背景自動化搶資源有關，未完全排除。
- **本輪 TOCTOU 排查僅涵蓋 `tools/tests/`**：未對 `AutoClaude/tests/`／`AISDLC_SDD/`
  等其他樹做同型排查，若那些樹底下也有平行測試合成暫存檔案的類似風險，仍可能
  有漏網，逐項見 `CrossPlatform_R137_Scan_Findings.md` §5。

## 第六輪：頭重腳輕根因修法＋四方獨立複審收斂（2026-09-09）

### 背景

第五輪 QA 量到 `test_doc_loc_baseline_freshness_r60.py` 單模組占平行總耗時
65%，是「頭重腳輕」的直接根因，但當輪未落地修法（列入誠實劃界）。掌舵者直接
提問，要求真正解決此問題並派 Architect/SA/SD/QA 四方獨立審查（各自不共享
上下文，分別跑）核對三題：①帳本問題是否解決、②多CPU測試功能是否完備、
③是否有頭重腳輕分配不均。

### 實作（收尾單人窗口）

實測定位真正離群值是單一測試方法而非整個檔案：
`TestR67R3ThisFileMakesNoUnstatedPlatformAssumption.
test_every_lock_in_this_file_holds_under_every_simulated_platform` 佔全模組
157.52s 的 118.49s（≈75%）。新增 `tools/lib/dispatch_granularity.py`：平行
派工鍵改採白名單模組 (module, class) 細分（`unittest.TestLoader.
loadTestsFromName()` 原生支援點號路徑，`parallel_shard.py` worker 協定零
改動），其餘模組維持整模組派工。白名單納入兩檔：
`test_doc_loc_baseline_freshness_r60`（36 類別）與修完第一熱點後浮現的新
單一最重模組 `test_archive_defect_log`（224.5s，36 類別）。端到端重驗時
親自複現並修復第五輪排查漏掉的第 11 個同型 TOCTOU 站點
（`test_platform_utils_dedup.py`）。逐項見 `CrossPlatform_R138_Scan_
Findings.md`。

### 四方獨立複審結果（Architect/SA/SD/QA，各自獨立跑）

四方三題裁決一致：**VERDICT_LEDGER_RESOLVED=partial**／
**VERDICT_FEATURE_COMPLETE=partial**／**VERDICT_LOAD_BALANCED=partial**。
共同確認核心技術修法真實且可獨立重現（QA 實測序列 794.00s vs 平行 4-worker
300~308s，加速比 ≈2.6x，強力推翻第三輪「幾乎零加速比」的舊描述；SD 另寫
腳本對真實 4045 支測試逐鍵回灌 `loadTestsFromName()` 核對計數，139 個派工鍵
0 筆不符）。共同點名的缺口（本輪已逐項修復）：

1. **`dispatch_granularity.py` 落地時零測試覆蓋**，且其 docstring 宣稱
   「由 `test_run_root_unittests.py` 回歸鎖看守」查無實據——已修復：補上
   `DispatchGranularityDispatchKeyTest`／
   `DispatchGranularityPlaceholderConstantStaysInSyncTest`／
   `DispatchGranularityWhitelistHasNoModuleLevelFixturesTest` 三個測試類別
   （涵蓋白名單細分／fail-closed 安全網／placeholder 特例／兩份
   `_PLACEHOLDER_MODULE` 複本同步／白名單模組無模組層 fixture 五個面向），
   docstring 訂正為據實描述。
2. **本檔（證據檔）缺〈第六輪〉章節、主缺陷帳本 DEF-200-274 列未同步**——
   已修復：本節即為該章節；`AutoSDD_Defect_Log.md` 該列已回填。

逐項複審記錄與修復見 `CrossPlatform_R139_Scan_Findings.md`。

### 誠實劃界（本輪仍未解決）

- **Windows 真機驗證**：仍未解，沿用第五輪既有記載，本輪未觸及。
- **單一測試 118~134s 的結構性下限**：`test_every_lock_in_this_file_holds_
  under_every_simulated_platform` 本身仍需 118~134s（依機器負載變動），本輪
  只解決「不拖累其他測試」，未嘗試縮短該測試自身邏輯（其職責是逐一模擬多
  平台重跑本檔全部鎖，縮短需求須先確認不犧牲覆蓋率，非本輪範圍）。四方
  獨立確認：4-worker wall-clock 理論最佳值（總 CPU 時間 / 4）與實測仍有
  約 29~46% 落差，機制仍是手動白名單、非自動負載感知派工——下一個新熱點
  出現時仍需人工重新發現與加白名單（SA 建議：補一份正式 runbook 取代目前
  純靠 docstring 範例的操作指引，本輪未落地，留供後續）。
- **本輪 TOCTOU 補漏排查僅涵蓋端到端重驗實際命中的一個站點**：未對整棵
  `tools/tests/` 樹重做第五輪等級的逐檔普查，不保證這是最後一個漏網站點。

## 第七輪：負載不均自動偵測 + 四方獨立複審收斂（2026-09-09）

### 背景

第六輪〈誠實劃界〉記載：白名單機制（`CLASS_LEVEL_DISPATCH_MODULES`）仍是
手動——下一個新熱點出現時，需要有人親自讀 `report_module_timings()` 印出的
「⏱ 模組耗時排行」、自己心算比例，才會發現該加進白名單。掌舵者直接提問，
要求「設計自動偵測機制」取代「靠人眼發現新熱點」，並再次派 Architect/SA/SD/QA
四方獨立審查（各自不共享上下文，分別跑）核對三題：①帳本問題是否解決、
②多CPU測試功能是否完備、③是否有頭重腳輕分配不均。

### 實作（收尾單人窗口）

新增 `tools/lib/dispatch_imbalance.py`：純函式 `detect_imbalance(module_timings,
worker_count, ratio_threshold=1.5)` 讀 `parallel_shard.run_parallel()` 已收集的
`module_timings`，算出每個派工單位耗時相對「公平均分基準」（總耗時 /
`min(worker_count, len(module_timings))`）的倍率，超過門檻即回傳（依倍率遞減
排序）；`report_dispatch_imbalance()` 在平行模式跑完後印出警告與可執行建議
（指向既有的白名單機制）。`tools/run_root_unittests.py::run_with_floor()` 在
`report_module_timings(result)` 之後多加一行呼叫轉接。核心邏輯與印出接線皆
抽到獨立檔案（同 `dispatch_granularity.py` 先例）：`run_root_unittests.py`
特殊層行數棘輪原訂 773，落地當下無餘裕，抽檔後只餘 1 行 import + 1 行轉呼叫，
淨增 +2 行（773→775，已同步 `AutoClaude/tools/check_loc_budget.py`）。

### 四方獨立複審結果（Architect/SA/SD/QA，各自獨立跑）

四方裁決三題時方向一致但理由略有差異（詳見下方逐項）：

- **Architect**：`VERDICT_LEDGER_RESOLVED=partial`（無倒退）／
  `VERDICT_FEATURE_COMPLETE=partial`／`VERDICT_LOAD_BALANCED=partial`。實測
  `wc -l tools/run_root_unittests.py`＝775，與棘輪表逐字吻合；`ruff check`
  全乾淨；`test_run_root_unittests.py` 143 個測試全綠。點名 F1（major）：
  `.github/workflows/*.yml` 三支與 `tools/git-hooks/pre-push` 皆未設定
  `AUTOSDD_PARALLEL_TESTS`，偵測結果只印 stdout、不落檔、不影響 rc——「自動」
  目前僅對手動 opt-in 平行模式的個別開發者生效，CI/pre-push 完全看不到。
  F2（major，潛伏未觸發）：`fair_share` 分母用未經 cap 的名目 `worker_count`，
  實測「1 個單位、worker=8」與「3 個完全平衡的單位、worker=8」皆被誤判為不均。
- **SA**：`VERDICT_LEDGER_RESOLVED=open`（F1／F2 兩個 blocking：本輪新增的
  `_GUARD_LINES_REPIN_LOG` 列引用了當時尚不存在的〈第七輪〉章節，且
  `AutoSDD_Defect_Log.md` DEF-200-274 列未同步本輪——與第六輪複審點名過的同型
  缺口重演）／`VERDICT_FEATURE_COMPLETE=partial`／`VERDICT_LOAD_BALANCED=open`
  （本輪對派工演算法本身零改動，純觀測工具不是負載平衡改善）。獨立核實
  `AutoClaude/pyproject.toml` 與 30 份 `AISDLC_SDD/AISDLC_SDD_v0.*/pytest.ini`
  逐一比對內容完全相同、皆無平行化設定，佐證「多 CPU 測試」僅涵蓋根層
  `tools/tests/`；`AutoClaude/tools/run_local_nightly.sh` 呼叫本 runner 時亦
  未設定該環境變數。
- **SD**：獨立寫合成場景實測證實 F2「不是邊緣情況偶爾誤報，而是這個公式在
  `dispatch units < worker_count` 整個區間裡都不是在測『不均』，而是在測
  `worker_count` 設定值本身」（單一單位倍率恆等於 worker_count，與 elapsed
  數值無關）；確認唯一生產路徑（69 支測試檔＋白名單細分後遠大於 worker 上限 8）
  結構上不會踩到，但公式正確性不該依賴這個僥倖。給出一行修法：分母改用
  `min(worker_count, len(module_timings))`。
- **QA**：`VERDICT_LOAD_BALANCED=fixed`（唯一與其他三方不同的裁決——親測全套
  4062 支測試、139 個派工單位、4 worker，`grep "🚨"` 零命中，無誤報也無舊熱點
  假性復發，5 個模組耗時排行數字與第六輪機制吻合）。用合成場景逐一戳邊界（10
  種情境，含極小浮點數／恰好門檻值／10x 主導）驗證核心邏輯本身正確，唯一真缺陷
  即 F2（用 3 個完全相同耗時的單位、worker=8 實測全數 3 個皆被誤標，5 個相同
  單位、worker=8 同樣全數誤標，7 個則不誤標——精確定位問題邊界）。親跑全套時
  rc=1，15 個失敗經逐一核對測試名稱皆為 `test_adr_xplat001_c1c2_lock.py` 的
  護欄層棘輪測試（因收尾窗口尚未補完 R140 帳本三件套），與 `dispatch_imbalance`
  本身無關。

### 修復（收尾單人窗口，依四方共同點名逐條落地）

1. **F2／SD 一行修法**：`detect_imbalance()` 分母改為
   `effective_workers = min(worker_count, len(module_timings))`；新增回歸測試
   `test_fewer_units_than_workers_and_balanced_flags_nothing`（3 個耗時皆 20.0
   的單位，worker_count 分別代入 2/3/4/8/50，斷言皆不觸發），釘住四方共同
   驗證過的邊界。
2. **F1／SA／Architect「未達自動」缺口**：本節〈誠實劃界〉如實記載，不宣稱
   已解決（見下）。
3. **F1（SA blocking）文件斷鏈**：本節本身即為該修復——`_GUARD_LINES_REPIN_LOG`
   R140 列的引用落地時生效；`AutoSDD_Defect_Log.md` DEF-200-274 列同輪回填；
   `docs/06_quality/CrossPlatform_R140_Scan_Findings.md` 新建（含四方複審逐項
   記錄與 guard-total:R140 標記）。

### 🔴 誠實劃界（本輪仍未解決，不可宣稱已完備）

- **同日追加（收尾單人窗口）**：掌舵者提問「把 CI 也接進去用多CPU模式跑一次」
  之後，`windows-compat-ci.yml`／`macos-compat-ci.yml`／`root-infra-ci.yml`
  三支 CI 呼叫 `tools/run_root_unittests.py` 的 step 皆已加上
  `env: AUTOSDD_PARALLEL_TESTS: "1"`（worker 數沿用出廠公式，不寫死），使下一
  次推上 main 起，這三個平台每次 CI 都會真的跑平行模式、`report_dispatch_
  imbalance()` 的輸出會出現在 CI log 裡——原本「這不是真正的自動，只是自動化了
  計算，沒有自動化觸發」這道缺口在**CI 曝光**這個面向已解除。**仍未解除的部分**：
  `tools/git-hooks/pre-push`（本機開發者日常 push 前的閘門）刻意未動——那是
  另一個更大的行為變更（會改變一個被多處註解引用的既有序列耗時基準
  「111.89s」），未在本輪範圍內；`report_dispatch_imbalance()` 仍只印 stdout、
  不落檔、不影響 rc、不升級——CI log 裡出現警告後，仍需要有人主動去讀那份 log
  才會被看見，並非會主動推播或讓 CI 變紅的「真正無人值守也會被通知」。
- **Windows 真機驗證**：本機（macOS）仍未解，沿用第五、六輪既有記載（掌舵者
  已表示會自行在 Windows 11 驗證）。**但**上述 CI 接線讓 `windows-compat-ci.yml`
  的 `windows-latest` runner 第一次真的執行 `AUTOSDD_PARALLEL_TESTS=1` 路徑——
  這是六輪以來記載的「Windows 真機驗證未解」缺口的第一個機械訊號（雲端 CI
  runner，非掌舵者本人的 Windows 11 真機；兩者不可互相替代，此處誠實劃界不
  含糊帶過）。
- **`AutoClaude/tests/`／`AISDLC_SDD` 的 pytest 套件不受本機制惠及**：SA 獨立
  核實 `AutoClaude/pyproject.toml` 與全部 `AISDLC_SDD_v0.*/pytest.ini` 皆無
  平行化設定；DEF-200-274 立案文字本身即限定「根層測試 runner」，範圍本身不算
  違反承諾，但此前六輪皆未在〈誠實劃界〉明講這個邊界，本輪一併記載。
- **`ratio_threshold=1.5` 寫死、不可由環境變數覆寫**（Architect 指出）：目前
  只影響 print，無害，但與 `worker_count` 可用 `AUTOSDD_PARALLEL_TESTS_WORKERS`
  覆寫的慣例不一致，留供後續評估是否需要開放調整。

## 第八輪：四方獨立複審修復收尾（2026-09-09）

### 背景

commit 9478bda（第七輪產出：三支 CI workflow 接上平行測試模式）push 後，
主控派 Architect/SA/SD/QA 四方獨立審查（各自不共享上下文，分別跑）該次
push 的真實 CI 結果與程式碼本身，找出下一步要修的具體缺口。真實 CI 結果：
windows-compat-ci／macos-compat-ci 皆 success（windows 是本機制第一次在
Windows 真機驗證成功），root-infra-ci failure。

### 四方獨立複審找到什麼

- **root-infra-ci failure 根因定位**：`tools/run_root_unittests.py` 撞上
  `AutoClaude/tools/check_loc_budget.py` 的 special-tier LOC 棘輪——第六、
  七輪各自的 P0/P1 修復（平行模式失敗內容補印 stderr；`worker_count()==1`
  時退回序列）各自加了幾行 WHY 註解，兩段合計 +13 行使 775 行預算超額
  （775→788）。
- **SD／QA 共同點名**：`ParallelFallbackToSequentialTest` 等既有測試全數用
  `mock.patch.object(parallel_shard, "worker_count", ...)` 整個換掉函式
  本體，從未直接呼叫 `worker_count(cpu_count=N)` 斷言公式輸出本身——公式
  （`max(1, min(8, cpu-1))`）、環境變數覆寫、非法值退回三條路徑因此零覆蓋。
- **SA 點名**：CI 已接 `AUTOSDD_PARALLEL_TESTS=1`，但零測試覆蓋，未來可能被
  無聲刪除而無人發現；`AutoClaude/tools/run_local_nightly.sh`／
  `run_local_nightly.ps1` 兩支本機 nightly 腳本呼叫 `run_root_unittests.py`
  時未設同一開關，與使用者原始訴求①「本機收尾驗證也不該被拖慢」最直接對應
  的場景反而漏接。
- **SA 提出方向、本輪落地**：`dispatch_imbalance.report_dispatch_imbalance()`
  偵測到不均時，CI 上應額外印一行 GitHub Actions 原生 `::warning::`
  annotation，直接顯示在 run 摘要頁面，不需人工捲動冗長 log。

### 修復（收尾單人窗口）

1. **special-tier LOC 超額**——完整 WHY（原本要移到本節的兩段壓縮理由）：

   - **`worker_count()==1` 退回序列**那一段（第七輪四方獨立複審 Architect／SD
     命中）：`worker_count()` 算出 1（例如 `AUTOSDD_PARALLEL_TESTS_WORKERS=1`，
     或單核心環境的預設公式）時，走 subprocess 架構零平行效益、純損耗——
     139 個派工單位逐一開 subprocess 序列執行，比直接 `TextTestRunner` 慢
     且多一層 JSON 彙總故障面。此時退回序列路徑（`use_parallel = parallel_
     shard.enabled() and parallel_shard.worker_count() > 1`）。
   - **平行模式失敗內容補印 stderr** 那一段（DEF-200-274 CI 事故，commit
     9478bda，root-infra-ci run 34358252409）：平行模式此前只把失敗明細
     `body` 落檔、從未印到 console；CI runner 的落檔目錄是 job 臨時工作
     目錄，job 結束即銷毀，三支 CI workflow 也都沒有 upload-artifact 步驟
     ——結果主控台完全看不到任何 `FAIL:`/`ERROR:`/Traceback，與序列模式
     `TextTestRunner.run()` 內建 `printErrors()` 的行為不對等。修法：把已經
     收集好的內容多印一次到 stderr；只在 `wasSuccessful()` 為 False 時才
     觸發，不影響全綠輸出。
   - 兩段原本各佔 4 行與 6 行完整散文 WHY，本輪壓成各 1 行行內指標式註解
     （上面兩段完整文字即該 WHY 全文，程式碼裡只留指向本節的指標）。壓縮
     後 `tools/run_root_unittests.py` 由 788→777 行，仍超過 775 行預算 2 行
     ——已確認在不刪除已驗證功能、不動無關程式碼的前提下無法再壓縮（唯一
     可省的 3 行程式碼分別是：`use_parallel` 條件判斷本身、`print(body, …)`
     呼叫本身，以及避免重複計算 `"\n".join(lines)` 而引入的 `body` 變數——
     已改為省略 `body` 變數、直接兩處各自呼叫 `"\n".join(lines)`，接受一次
     微小的重複計算換取 1 行），故依既有慣例在 `AutoClaude/tools/
     check_loc_budget.py` 的 `SPECIAL_FILES` 具名調高 775→777（該檔內已有
     逐輪沿革註解，本輪新增一段）。
2. **`worker_count()` 公式直接單元測試**：新增 `WorkerCountFormulaTest`（
   `tools/tests/test_run_root_unittests.py`）：
   - `test_formula_across_cpu_counts`：`cpu_count ∈ {0,1,2,9,10,100}` 對應
     `max(1, min(8, cpu-1))` 的公式輸出。
   - `test_workers_env_override_wins_over_formula`：合法正整數覆寫勝過公式。
   - `test_invalid_override_values_fall_back_to_formula`：`"0"`／`"-5"`／
     `"abc"` 三種非法值皆退回公式。
   - `test_none_cpu_count_uses_real_os_cpu_count_within_bounds`：
     `cpu_count=None` 時走真的 `os.cpu_count()`，只斷言落在 `[1, 8]` 值域
     （不斷言精確值，避免綁死在跑測試那台機器的核心數）。
3. **CI 接線回歸鎖**：新增 `TestParallelTestsCiWiring`（
   `tools/tests/test_smoke_ci_sync.py`），以 `yaml.safe_load` 解析三支
   compat-CI，斷言呼叫 `run_root_unittests.py` 的 step 帶
   `AUTOSDD_PARALLEL_TESTS=1`（正則只認「真的執行它」的 run 本體，避免誤中
   `ruff check --show-settings tools/run_root_unittests.py` 這種只是拿它
   當參照對象的 step）。連帶：`test_smoke_ci_sync.py` 因此新增 `import
   yaml`，使該模組在零相依沙箱同樣會塌，已同步加入
   `tools/lib/min_tests_margin.py` 的 `PREREQ_DEPENDENT_MODULES`。
4. **兩支本機 nightly 腳本補開關**：`AutoClaude/tools/run_local_nightly.sh`
   改用 `env AUTOSDD_PARALLEL_TESTS=1 "$PY" "$ROOT/tools/run_root_
   unittests.py"`；`run_local_nightly.ps1` 在呼叫前後暫時設值／還原
   （`$prevParallelEnv` + `try/finally`），不外溢到其餘 stage。
5. **GitHub Actions annotation**：`dispatch_imbalance.
   report_dispatch_imbalance()` 偵測到不均時，`GITHUB_ACTIONS=true` 才
   額外逐筆印 `::warning::平行負載不均：<key> 耗時 <elapsed>s（<ratio>x
   公平均分基準）`；非 CI 環境維持純 print 行為不變。新增
   `test_github_actions_env_adds_warning_annotation`／
   `test_non_ci_env_has_no_warning_annotation` 兩支回歸鎖。

### 驗證數字（本 session 親跑，逐字貼）

- 序列（`unset AUTOSDD_PARALLEL_TESTS AUTOSDD_PARALLEL_TESTS_WORKERS &&
  python3 tools/run_root_unittests.py`）：見下方逐字貼（收尾回報時填入）。
- 平行（`AUTOSDD_PARALLEL_TESTS=1 python3 tools/run_root_unittests.py`）：
  見下方逐字貼（收尾回報時填入）。
- `python3 -m unittest test_adr_xplat001_c1c2_lock -v`（`tools/tests/` 下）：
  192 個測試全部通過（`TestGuardLayerRatchet`／`TestPhase2FiveRoundDeadline
  IsMechanical`／`TestRepinReasonStaysAnIndexNotAReport` 三族皆綠）。
- `AutoClaude/tools/check_loc_budget.py --json`：`special_violations: []`，
  rc=0。

### 🔴 誠實劃界（本輪仍未解決，不可宣稱已完備）

- **不可宣稱本輪修復後 CI 會轉綠**——special-tier LOC 修復（775→777）尚未
  經過新的 CI run 驗證（修復尚未 push）。已本機驗證乾淨（序列／平行兩次
  全套跑通過、rc 一致），待下次 push 後的真實 CI run 才能驗證。
- **`_PHASE2_REVIEW_LOG` 的 R141 `[提案]` 列是機械副作用，不是新的實質
  判斷**：本輪把 `_GUARD_LINES_REPIN_LOG` 推進到 R141，越過 ADR-XPLAT-013
  Phase 2 條文五 §6 的 5 輪視窗到期輪（R140），而『維持觀察』名額（R135）
  已用罄，§6 只剩 `[提案]`／`[落地]` 兩條合法出路。本列**不對** ADR-
  XPLAT-013 (c) 觀測→阻斷方向做任何新判斷——R129 提出的既存提案迄今仍待
  主控排定四方複審，本列僅重新登記該既存未決狀態以符合款(5) 的封閉表格式。
  這是 DEF-200-274 guard-line 記帳的機械副作用觸發，非本輪對 (c) 方向有
  新意見；此事需要主控知悉並確認處置方式是否恰當。
- `ratio_threshold=1.5` 仍寫死、不可由環境變數覆寫（延續第七輪誠實劃界）。
- `AutoClaude/tests/`／`AISDLC_SDD` 的 pytest 套件仍不受本機制惠及。
- Windows 真機驗證（掌舵者本人 Windows 11 機器）仍未解；CI 上
  `windows-compat-ci` 的 `windows-latest` runner 已驗證成功，但那是雲端
  runner，非掌舵者本人機器，兩者不可互相替代。

逐項見 `docs/06_quality/CrossPlatform_R141_Scan_Findings.md`；缺陷帳本見
`docs/06_quality/AutoSDD_Defect_Log.md` DEF-200-274。

## 第九輪：預設自動多核心＋LPT＋自動細分＋不均偵測 v2＋SIGTERM 清理＋P1 zshrc 假紅根治＋pytest-xdist（2026-09-13）

### 背景

主控派 Architect/SA/SD/QA 四方獨立審查（各自不共享上下文分別跑，每個發現另配
2 位懷疑者投票）本機制第八輪落地後的現況，逐項核實此前「靠人眼發現熱點」與
「zshrc 殘留 `AUTOSDD_PARALLEL_TESTS=1` 會不會讓合成樹測試誤觸平行」等疑慮。

### 四方獨立複審找到什麼（存活發現）

- **P1（零信任判死）：zshrc 假紅真因**——三方獨立實測證實：既有合成樹測試在
  自己的行程內直接呼叫 `run_with_floor()`，而該函式在 D1 之前對「未設環境變數」
  一律視為序列；一旦操作者的 shell rc 檔殘留 `AUTOSDD_PARALLEL_TESTS=1`，
  合成樹測試會被平行 worker 接手，而 worker 對合成樹的 `assert start_dir` 前提
  斷言炸掉——「靜態掃描能提早攔截」一說經三方各自重現後不成立，唯一收斂的修法
  是讓 `should_run_parallel()` 對非真實 `tools/tests` 目錄一律強制序列，不論
  環境變數為何。
- **P2**：`fair_share` 倍率判準在低 worker 數（如 worker=1～2）下被稀釋，
  且此前從未在 CI 的預設序列模式下觸發過，判準等於長期休眠。
- **P2**：偵測到不均只印警告，沒有接到任何「自動採取行動」的閉環（例如自動
  細分過熱模組）。
- **P2**：pre-push 的 leg②（root-infra）此前未接上平行模式，本機收尾驗證的
  最大宗場景反而繼續吃序列的全部時間代價。
- **P2**：`AutoClaude/tests/`／`AISDLC_SDD` 兩個子專案的 pytest 套件仍是純
  序列，零 xdist，與根層 `tools/tests` 的處境不一致。
- **P2**：`MIN_TESTS` 收集數保鮮提醒（`WARN`）此前已存在但未被本輪前處理。
- **P3**：SIGTERM 情境下，已啟動的子行程沒有清理機制，會變成孤兒行程。
- **P3**：`run_root_unittests.py` 執行時不印實際使用的 worker 數，除錯時難以
  判斷平行是否真的生效。
- **P3**：`run_root_unittests.py` 本檔自身行數 777/777，已頂到 special-tier
  上限，任何新增都得先在同一次變更內找到等量刪減。
- **駁回的疑慮**：`os.dup` 在 Windows 上是否安全（三方各自查證 CI 已在
  windows-latest runner 真的跑過，不成立）；P/E core（效能／能效核心）異質
  排程是否需要感知（駁回，非本輪範圍）。

### 設計裁決

- `parallel_shard.should_run_parallel()` 改寫三條件真值表：目標目錄必須是
  真實 `tools/tests`（非合成樹）、worker 數 > 1、且未被顯式關閉；三者皆真
  才平行。合成樹（單元測試注入的 fixture 目錄）無論環境變數為何一律序列，
  根治 P1。
- 零相依探針子行程（`_zero_dep_probe_cached()`）新增 `_zero_dep_child_env()`
  輔助函式，無條件把子行程環境的 `AUTOSDD_PARALLEL_TESTS` 強制寫成 `"0"`，
  阻斷探針對自身遞迴 fan-out（同 DEF-101-803 遞迴熱點史料的精神延伸，P0）。
- 新增 `tools/lib/parallel_timing_cache.py`：`read_json()`／`load_hints()`
  對缺檔／壞 JSON／非 dict／bool 誤判為計時數值等情境一律容錯回空值；
  `order_dispatch_units()` 依歷史耗時做 LPT（Longest-Processing-Time）派工
  排序，無 hints 時與舊排序位元級相同（零回歸承諾）；`save_live_cache()`
  只在大型執行（≥20 派工單位）才落盤，避免小型合成測試污染活體快取；
  `staleness_report()` 偵測快取與現況重疊率過低時提醒重新種子化。
- `tools/lib/dispatch_granularity.py` 新增 `auto_class_level_candidates()`／
  `auto_suite_dispatch_units()`：對通過安全網（頂層、非 placeholder、未定義
  `setUpModule`/`tearDownModule`）的候選類別自動細分派工單位，倍率判準沿用
  既有 `dispatch_imbalance.detect_imbalance()`。
- `tools/lib/dispatch_imbalance.py` 不均偵測 v2：新增 1.0～1.5 倍率帶（排程
  救不了、需細分的族群，去重後只印一次）與整體 `wall/ideal` 排程效率回報；
  `report_module_timings()` 標題行印出實際 worker 數（SA-09）。
- `parallel_shard.py` 修 SIGTERM 清理競態：主執行緒收到 SIGTERM 時，所有
  已啟動的子行程（含清理快照之後才登記的）皆被 `kill()`，且舊 handler 事後
  被還原；非主執行緒呼叫 `run_parallel()` 不因掛 SIGTERM handler 而拋
  `ValueError`。
- worker cap 8→9（掌舵者/設計者以離線模擬數據反對再往上調到 12，見下方
  〈主控實測〉）。
- `pre-push` leg①（root-infra）由 `find -exec py_compile` 改
  `compileall -j0`（平行語法檢查），新增回歸鎖驗證語法錯誤偵測能力不因遷移
  而倒退。
- AutoClaude／AISDLC_SDD 兩個子專案的 pytest 套件接上 `pytest-xdist`：
  `addopts` 全域帶 `-n auto --dist worksteal`（fail-loud，非 conftest 靜默
  降級）；PostgreSQL 真實資料庫在場時強制 `--dist loadgroup`（conftest
  fail-loud＋`local_ci_gate.py`／`pre-push` 自動加旗標）；`LedgerPerformance
  Tests` 在 xdist worker 內的時間閾值放寬到 1.0s（worker 間資源競爭）。
  v0.01（ci-gate 凍結基線）不動，`requirements-ci.txt` 可加 pin（先例
  commit d411dc6）；兩份 `pytest.ini` 不動，旗標放呼叫端。

### 實作（本收尾單人窗口落地物）

- `tools/run_root_unittests.py`：`MIN_TESTS` 4054→4246（discovery 探針實測
  直接填入，見該檔第 58 行的重釘註記）。
- `tools/tests/test_run_root_unittests.py`：3648→4258（+610），新增
  `ShouldRunParallelDecisionTest`／`RunWithFloorNeverParallelizesSyntheticTreeTest`／
  `ZeroDepProbeForcesSequentialChildEnvTest`（P0/P1 根治回歸鎖）、
  `ParallelTimingCacheLoadHintsTest`／`ParallelTimingCacheOrderDispatchUnitsTest`／
  `ParallelTimingCacheSaveLiveCacheTest`／`ParallelTimingCacheStalenessReportTest`／
  `RunParallelPersistsLiveCacheOnlyForLargeRunsTest`（LPT 快取）、
  `ParallelShardSigtermCleanupTest`／`ParallelShardSigtermIgnoredOffMainThreadTest`
  （SIGTERM 清理）、`DispatchGranularityAutoSplitCandidatesTest`／
  `DispatchGranularityAutoSuiteDispatchUnitsTest`（自動細分）、
  `ReportDispatchImbalanceOverFairShareBandTest`／
  `ReportDispatchImbalanceWallClockLossTest`／
  `ReportModuleTimingsPrintsWorkerCountTest`（不均偵測 v2）；同輪追加：主控
  CI 複驗修正 4258→4268（+10，Windows 上 SIGTERM 測試改為不自殺的平台分支
  ＋CI 多印 `::warning::` 的計數修正）。
- `tools/tests/test_pre_push_dispatcher.py`：686→704（+18），新增
  `test_syntax_error_under_tools_fails_the_rootinfra_leg`（compileall 遷移
  語法偵測回歸鎖）。
- `tools/tests/test_adr_xplat001_c1c2_lock.py`（本檔）：guard-line R147 重釘
  自身逐檔漂移收斂 +110（`_GUARD_LINES_REPIN_LOG` 本輪多列＋`_FROZEN_GUARD_
  LINES` 反覆更新＋新增 `_REGRESSION_LANE_LOG` 列＋`_REPIN_NET_CAP_SCHEDULE`
  到期兌現 cap 543→542 與重新武裝下一段（`_REPIN_NET_CAP_DUE_ROUND=149`／
  `_REPIN_NET_CAP_DUE_TARGET=541`）＋`_PHASE2_REVIEW_LOG` 新增 R147
  `[維持觀察]` 列＋`_ROOT_TOOLS_OLD_SCALE_DEBT_DUE_ROUND` 具名展延
  147→152（非 root-tools 重構持有面，真拆仍待獨立窗口）＋
  `_REPIN_LOG_FROZEN_PREFIX_LEN` 181→204 與 `_REPIN_LOG_HISTORY_SHA256`／
  `_FROZEN_PREFIX_REWRITE_LEDGER` 重釘＋E501 存量債棘輪折行（多支單行列改
  雙行避免過長行）。
- 分軌：回歸鎖軌 270（P1/P0 zshrc 假紅根治 119 行＋既有缺陷修復回歸鎖
  ParallelTimingCacheLoadHintsTest／ParallelShardSigtermCleanupTest／
  ParallelShardSigtermIgnoredOffMainThreadTest 151 行，未使用任何一次性例外
  名冊）；功能軌餘額 478（＝內容成長 368〔LPT 排序／保存／過期回報／大批
  持久化＋自動細分＋不均偵測 v2＋worker 數印出＋既有 cap 8→9 調整 340 行＋
  compileall 遷移回歸鎖 18 行＋主控 CI 複驗修正 10 行〕＋本檔
  〔`test_adr_xplat001_c1c2_lock.py`〕自身記帳漂移 110 行，本輪刻意不把自身
  記帳漂移歸入回歸鎖軌以保留其 cap 309 的餘裕）。回歸鎖軌 270 ≤ cap 309、
  功能軌餘額 478 ≤ 到期後 cap 542，
  皆未超額，未動用任何一次性例外名冊。

### 驗證數字（逐字）

- 主控實測：6 worker 現行排序 wall 262～264s（4205 支）；離線模擬（模型
  對上實測 264.5s）：LPT 排序 w=6→206.1s、w=8→154.6s、w=9→137.4s 皆＝理論
  下界；拆最重測試對 makespan 幫助＝0。
- 主控實測：安靜機器 auto 平行 worker=9 LPT 排序：**4246 支、wall 159s**；
  ⏱ 前五：`TestR67R3ThisFileMakesNoUnstatedPlatformAssumption` 141.6s／
  `test_platform_neutral_paths` 81.7s／`test_run_root_unittests` 76.4s／
  `TestMoveSubsetSelectionIsNamedAndTraceable` 74.7s／
  `TestPlanRejectsRowsWithExternalResidencePointers` 46.0s；新偵測印出
  「⚠️ 以下派工單位耗時超過公平份額：…TestR67R3… 141.6s（1.3x）」。
- `[他包回報]` Pkg-R（根層引擎）：全套兩次 3:55（冷快取）→ 2:40（LPT）；
  先紅再綠：P1 修前 failures=4、SIGTERM 舊邏輯 15/15 紅→15/15 綠、LPT
  2/3 紅→3/3 綠、cache 容錯 4/5 紅→5/5 綠。
- `[他包回報]` Pkg-X（pytest-xdist）：AutoClaude 4579 passed／222 skipped／
  30.42s（序列基線主控親測 160s／4570 passed）；AISDLC_SDD `scripts/`
  tests 351 passed／16.15s（主控親測序列 90.6s）；v0.30 fsm 1941 passed／
  15.69s；發現並修復 v0.30 `snapshot.py` 固定 `.tmp` 中繼檔名競態（v0.01
  凍結基線不可改 ⇒ `ci-gate.sh` 對凍結基線維持序列）；conftest 分群機制
  兩個必要條件（`tryfirst`＋標記迴圈在早退前）各有先紅再綠。
- 本收尾單人窗口親跑（2026-09-13，安靜機器）：
  `(cd tools/tests && python -m unittest test_adr_xplat001_c1c2_lock -q)` →
  `Ran 192 tests in 10.853s` `OK`；
  `python tools/archive_defect_log.py --check` → `✅ 帳本保全稽核通過` rc=0；
  `python tools/check_defect_log_crossref.py` → `✅ 缺陷帳本跨文件狀態一致`
  rc=0；`python tools/check_handoff_carriers.py` → `✅ 每一筆前瞻延後宣稱都
  有帳本承接載體` rc=0；`python tools/check_pytest_baseline_sites.py` →
  `✅ pytest 基線站點守門通過` rc=0。

### 誠實劃界（本輪仍未解決，不可宣稱已完備）

- 掌舵者本人 Windows 11 物理機親驗待補；CI `windows-compat-ci` 的
  `windows-latest` runner 已在第八輪驗證成功，但那是雲端 runner，非掌舵者
  本人機器，兩者不可互相替代，本輪 push 後會再驗一次雲端 CI。
- `compileall -j0` 與 SIGTERM 清理在 Windows 上的實機行為尚未驗證。
- AutoClaude 真實 Docker PostgreSQL 環境下的 `--dist loadgroup` 端到端流程
  尚未驗證。
- 自動細分機制在 worker cap=9 下目前休眠（需 worker ≥ 10 才觸發），本輪
  未能實測其真正生效路徑；其候選判準與安全網（`setUpModule`／import 失敗
  排除、無快取時與既有行為逐位元相同）只有單元測試
  （`test_run_root_unittests.py` 的 `auto_class_level_candidates`／
  `auto_suite_dispatch_units` 測試類別）覆蓋，沒有真實觸發的端到端證據
  （四方複審 QA F6，P3）。
- D7 其餘多CPU候選**評估後不做**（四方複審 SA F3 要求明列）：① pre-push 十支
  守門工具並行——每支皆 <5s、總和約 20s，並行要處理輸出交錯與 rc 彙整，
  收益 < 複雜度；② `ci-gate.sh` v0.01／v0.30 雙軌並行——各軌已由 xdist 吃滿
  全部核心，再並行只會互相搶 CPU；③ 根層 root-infra-ci 的逐檔 `py_compile`
  step——它逐檔印 `::error::` annotation 需要檔名，`compileall -j0` 的並行輸出
  順序不保證，另案處理；④ 單一最重測試方法內部平行化——離線模擬證明對
  makespan 幫助為 0（瓶頸是 sum/w），不做。
- `snapshot.py::_append_raw_abort_event()` 的中繼檔名碰撞（四方複審 Architect
  PF-02／SA F2）已於複審後一併改走 `_atomic_write_text`；其讀-改-寫三步的
  lost-update 窗口仍未修（best-effort raw audit，呼叫端吞例外，不影響任何判定）。
- 四方複審 PF-01／F1（P1）：`-p no:xdist` 在 `gate_pg()` 與 pg-e2e-nightly 兩個
  CI step 漏配 `-o addopts=`（會直接 `unrecognized arguments`），複審後已補齊並在
  `test_local_ci_gate.py` 加成對斷言。
- `_PHASE2_REVIEW_LOG` 的 R147 `[維持觀察]` 列同第八輪 R141 `[提案]` 列
  一樣是機械副作用：本輪把 `_GUARD_LINES_REPIN_LOG` 推進到 R147，越過
  ADR-XPLAT-013 Phase 2 條文五 §6 的到期輪，`[提案]`（R141）已用罄
  「維持觀察」的連續資格重置，本列不對 (c) 觀測→阻斷方向做任何新判斷，
  R129 提出的既存提案迄今仍待主控排定四方複審。
- `_ROOT_TOOLS_OLD_SCALE_DEBT_DUE_ROUND`（U9 舊尺技術債，四支 `[ROOT-TOOLS]`
  檔）本輪恰好到期（147），與本輪主軸（guard-line 記帳＋pytest-xdist 落地）
  無關，依鐵律七具名展延 147→152（真拆仍待獨立重構持有面窗口，非本輪
  範圍）。
- AutoClaude／AISDLC_SDD 之後的 pytest-xdist 真 Docker PG／Windows 物理機
  組合尚無任何一次同時驗證過。

逐項見 `docs/06_quality/CrossPlatform_R145_Scan_Findings.md`〈第九輪附記〉節；
缺陷帳本見 `docs/06_quality/AutoSDD_Defect_Log.md` DEF-200-274。

## 第十輪：四方獨立審查覆核第九輪發現＋5 包並行修復收斂（2026-09-13）

### 背景

DEF-200-274 第十輪（掌舵者要求四方獨立審查 Architect／SA／SD／QA 覆核第九輪 24 條發現）
的複審找到什麼、設計裁決、5 包並行修復逐條與逐項驗證數字，完整記述寄居
`CrossPlatform_R145_Scan_Findings.md`〈第十輪附記（R148）〉（同 R129～R147 既有「單一缺陷
收尾附帶記帳」寄居體例，未另開新檔）；該附記第 241～242 行指標「詳細…見本節」，本節僅
承接此指標，補上 commit `6a12da1` 摘要與本輪收尾之後、文件回填單人窗口本場現查的 push
後 CI／nightly-full dispatch 補驗結果——四方複審發現與設計裁決本體不在此重複，一律以
R145 附記為準，避免雙份記帳漂移。

commit `6a12da1` 摘要：拆 139.9s 臨界測試為三平台類（本機牆鐘 156.6→135.6s）、
`halt_verdict()` 加 10s 活動容忍窗（c4a7e00 治具規避的生產面根治）、perf-baseline／pg-e2e
排除 xdist、nightly-full 接 xdist、ci-gate xdist 判準改 LATEST 允許清單＋回歸鎖、staleness
advisory 補 CI `::warning::`、skip 語意平行回歸鎖；驗證跑時四方複審再揪出兩處既有測試
競態（ghost-symbol 掃描與第三態探針的固定檔名撞見平行 worker）並硬化；新立
DEF-200-289／290。

### 第十輪補驗：push CI 與 nightly-full dispatch 結果（2026-09-13）

- **A. push 觸發 CI（含 run ID）**：`6a12da1` push 後四支同步 CI 皆 success——
  root-infra-ci run `34740753858`、AutoClaude CI run `34740753876`、aisdlc-sdd-ci run
  `34740753843`、shellcheck-ci run `34740753839`；windows-compat-ci run `34740753883`／
  macos-compat-ci run `34740753845` 因與稍後的 workflow_dispatch 共用 concurrency group
  被 `cancelled`（非失敗），同 commit 的 smoke job 由下方 B 項 dispatch run 補足驗證。
- **B. DEF-200-290 補驗（workflow_dispatch）**：windows-compat-ci run `34740773049`
  （smoke success；**nightly-full job failure**；alert success）、macos-compat-ci run
  `34740774601`（smoke success；**nightly-full job failure**；alert success）。兩支 run
  的整體 `conclusion=success` 只因 nightly-full step 帶 `continue-on-error: true`，不代表
  job 本身通過。
- **C. nightly-full 失敗鑑識**（鑑識 agent 本場現查）：兩邊皆敗在 AutoClaude
  `local_ci_gate.{ps1,sh}` 的 pytest 閘；pytest 子行程本身 **0 failed**——Windows
  `4626 passed, 175 skipped in 154.21s`、macOS `4579 passed, 222 skipped in 107.18s`，
  皆帶 `-n auto --dist worksteal`，**AutoClaude xdist 首次在真 Windows／macOS 全套驗證
  通過**。rc=1 來自 `AutoClaude/tools/local_ci_gate.py:387-398 check_skip_census()` 把
  `CENSUS_PROFILE_UNREGISTERED` 與 `CENSUS_FAIL` 同判 rc=1（`gate_pytest()` L639
  `return rc or census_rc`）；剖面 `AutoClaude/tests@win32+nopg+solo`／`darwin+nopg+solo`
  未登記（`tools/lib/skip_group_policy.py:821-863`，掌舵者裁決「先修 pgextras 軸、修好前
  維持 advisory 不登記」）。此紅**非本輪／非 xdist 引入**：2026-09-07 schedule run
  `34121302118`／`34127718484` job 同樣 failure、同字樣；GitHub Issue #10
  （2026-07-14 開單、仍 OPEN、7 則留言）。SDD LATEST `fsm_runtime` pytest 步（本輪新接
  xdist）在兩邊皆綠（Windows `1935 passed, 14 skipped in 68.24s`）。
- **D. 附帶缺陷（鑑識 agent 現查）**：macOS nightly-alert job 的
  `gh issue create --label "p1,macos,nightly"` 因 repo 無 `p1` label 報
  `could not add label: 'p1' not found` → exit 1，被 `continue-on-error` 蓋掉 ⇒ mac 側
  從未真正開過 issue（Windows 側有 Issue #10）。座標
  `.github/workflows/macos-compat-ci.yml:1382-1467`。

**主控原假設被鑑識推翻**：主控原判「xdist 讓 nightly-full 紅」，鑑識指出哪個量在
變——`check_skip_census()` 對未登記剖面判紅的邏輯自 R79（Issue #10 於 2026-07-14 即已存在）
起即存在，xdist 落地前後皆紅，此量從未因本輪改變；本輪新增的兩個 xdist 站點（AutoClaude
全套、SDD `fsm_runtime` nightly-full）皆綠，才是本輪真正變動的量。

🔴 **誠實劃界**：nightly-full 的深度回歸訊號目前不可信（未登記剖面恆判紅，真回歸與既有
已知缺口同判 rc=1、無法分辨），待 DEF-200-291 修復前，nightly-full job 的 `failure` 不構成
本輪／後續變更的回歸證據。

逐項見 `docs/06_quality/CrossPlatform_R145_Scan_Findings.md`〈第十輪附記（R148）〉節；
缺陷帳本見 `docs/06_quality/AutoSDD_Defect_Log.md` DEF-200-274／DEF-200-289／DEF-200-290／
DEF-200-291／DEF-200-292。

## 第十一輪：掌舵者 Windows 11 物理機親驗補記（2026-09-15）

### 背景

第九輪〈誠實劃界〉留下「掌舵者本人 Windows 11 物理機親驗待補」四項，此前只住在
`useMacWin.md`〈B 段〉尾端的一次性待辦（帳本 DEF-200-274 已標 fixed，兩份文件互相矛盾）。
下輪切換 macOS 前把可從物理機**既有取證**回填的三項在此收攏，剩一項如實留缺並另立
DEF-200-313；`useMacWin.md` 不再攜帶該待辦——一次性的單平台待辦不該住在兩平台共用的
啟動 SOP 裡。

### 四項對照（本場現查，物理機＝Windows 11 Pro 10.0.26200）

| 項 | 第九輪待驗內容 | 物理機證據 | 判定 |
|---|---|---|---|
| ① 多核 runner | `run_root_unittests.py` rc=0、log 含 `worker=` | schtasks 觸發之 nightly（2026-09-15 14:55，RunId 具名檔 `AutoClaude/logs/nightly_2026-09-15_145513.log`——刻意不引 `nightly_latest.log`：它是會被後續 nightly 覆寫的滾動指標，22:30 那次已使行號推移一行；取證紀律 #3）L210 `模組耗時排行（前 5，共 151 模組，平行模式，worker=9）`；L303 `local_ci_gate=0 root_unittests=0` | 已驗（排程環境） |
| ② `compileall -j 0` | pre-push 慢層該段無 ❌，或手動 `python -m compileall -q -j 0 tools .claude/hooks` rc=0 | 本場以根層 `.venv\Scripts\python.exe` 手動實跑：輸出 0 行、rc=0（pre-push 呼叫點＝`tools/git-hooks/pre-push:354`） | 已驗（互動 session） |
| ③ Ctrl-C／SIGTERM 孤兒行程 | 全套中 Ctrl-C 後 `Get-CimInstance Win32_Process` 無殘留 | 無——需人在終端機前按 Ctrl-C，`Stop-Process` 送的是 TerminateProcess 不是 SIGINT，不可替代 | **未驗**（DEF-200-313，下次 Windows 窗口補） |
| ④ AutoClaude xdist 全套 | rc=0 且 log 開頭 `bringing up nodes` | 同一支 RunId log（`nightly_2026-09-15_145513.log`）L89～90 `bringing up nodes...`；STAGE-L rc=0（L303） | 已驗（排程環境） |

🔴 誠實劃界：①④ 的證據來自 schtasks 排程環境（最高權限、非互動），與掌舵者在互動終端機
手打的執行環境不完全等價（DEF-200-312 正是兩者分歧的實證）；本輪不另在互動 session 重跑
全套，因為互動 session 的 xdist 全套在 R152 收尾窗口已跑過（該窗口宣稱見 `AutoSDD_improving_112.md`，
本節不重複其數字）。

## 第十二輪：掌舵者四問（多 CPU 是否完備／CI 是否接入／負載是否均衡／還有哪裡可用）四方獨立審查＋收尾（2026-09-17～18）

### 背景

掌舵者提出四個問題：Q1 帳本「Python 測試可用多 CPU」是否已解決；Q2 功能是否完備、CI 是否也用多 CPU；
Q3 有無頭重腳輕、「自動偵測多 CPU 平衡負載」設計是否最佳；Q4 還有哪些沒列入可用多 CPU。並要求
Architect／SA／SD／QA 四方獨立審查（皆 Sonnet 5、唯讀、不共享上下文），確認前輪宣稱（6a12da1／54ae6e9
已 push、CI 全綠）屬實。主控（Fable）只裁決、派工、收尾。

### 四方審查結果摘要（各自獨立跑；細節見 scratchpad 證據檔，本節只留存活發現）

- **一致確認**：核心機制與 CI 接線完備——root-infra-ci worker=3、macos worker=2、windows worker=3
  （runner vCPU 4／3／4 套 cpu-1）、AutoClaude CI xdist `4605 passed, 224 skipped in 86.48s`、SDD LATEST
  fsm 五段 `bringing up nodes`（皆 QA 自 CI log grep，[他包回報]）；前輪兩 commit 皆在 origin/main、
  最近 push CI 全綠（主控本場親查 `gh run list`：7b102176 的 macos／root-infra／windows 三支 success，
  bbb8a0b8 的五支 success）。
- **Q3 無結構性頭重腳輕**（SD 以快取實算，[他包回報]）：本機 worker=9 最重派工單位 93s ＜ 公平份額
  123.3s；CI worker=2／3 公平份額 370～555s 遠大於任何單位；worker 認領是共用佇列（動態）非靜態分片；
  `detect_imbalance` 在 worker=2／3／9 三種假設下皆回空。QA 自 CI log grep「公平份額／排程效率」四字面
  零命中。SD 駁回 Architect「自動細分需 worker≥10」——程式碼無此門檻，休眠是因兩個熱點已被人工白名單
  拆掉（第九輪〈誠實劃界〉該句已 stale，本節訂正）。
- **存活缺口**（四方交叉皆 VERIFIED）：
  1. DEF-200-289：五套 CPU 公式互不知情（`worker_count()`／xdist `-n auto`／ci-gate.sh 與 pre-push 各寫死
     `-n auto --dist worksteal`／compileall -j0／tlc `-workers auto`），且 CI headless 仍套 cpu-1 白白少用一核
     （Architect F2／F5、SD SD-01）。
  2. GAP-D（QA P1）：`ci-gate.ps1` 無 Git Bash 時的 native fallback 缺 xdist 且 `.ps1` 零鎖。
  3. GAP-E（QA P1）：AutoClaude `pyproject.toml` addopts 的 `-n auto --dist worksteal` 全庫無鎖。
  4. DEF-200-290／292 帳本 open 且程式碼確實未修（SA 逐條 grep）；SA 另查 Windows Issue #10 labels=[]
     為同根因（repo 無 `p1` label）。
- **評估後不做**（四方一致）：ci-gate 雙軌並行、pre-push 十支守門工具並行、TLC 五軌並行（各軌已吃滿
  核心，並行只互搶；ci-gate 雙軌真因是凍結基線 `snapshot.py` 競態非 CPU 預算）、單一重測試內部平行。
  Architect 建議 root-infra-ci 182 檔逐檔 `py_compile` 改兩階段（先 `compileall -q -j0`，失敗才逐檔印
  annotation）：主控評估收益約一次 CI 十秒級、需動受多鎖 workflow，**本輪不做**，留作候選。

### 主控裁決與實作（兩包 Sonnet，檔案面互不相交；A 在主工作樹、B 在隔離 worktree 交 patch）

**A 包（DEF-200-289＋GAP-D＋GAP-E）**：新增 `tools/lib/cpu_budget.py`（60 行）為唯一 CPU 預算算法：
`total_budget(cpu_count, headless)`＝headless（`GITHUB_ACTIONS=true` 或 `AUTOSDD_CPU_HEADLESS=1`）用滿全部核心、
互動保留一核，cap 9 沿用（SD-03 列為待量化 HYPOTHESIS，本輪不動）；`per_leg_budget(n_legs)` 平分；CLI
`--legs N` 只印整數。`parallel_shard.worker_count()` 改委派（覆寫優先序不變）。pre-push／ci-gate.sh／
ci-gate.ps1 在 legs 定案後一次算好、經 `AUTOSDD_PARALLEL_TESTS_WORKERS`＋`PYTEST_XDIST_AUTO_NUM_WORKERS`
（xdist 3.8.0 `plugin.py::pytest_xdist_auto_num_workers()` 原生優先讀此變數，A 包已於 .venv 原始碼核實）
廣播給全部 leg；使用者已顯式設定則不覆寫；算不出來靜默跳過——**刻意 fail-open**（純效能層，擋 push
只會逼人 `--no-verify`）。今日 n_legs=1 ⇒ 行為與現況位元級相同，只有 CI headless 多 1 worker（預期
ubuntu／windows 3→4、macos 2→3，待 push CI 實測）。GAP-D 判讀偏離 QA 字面：fallback 硬寫死只跑凍結基線
v0.01，凍結基線不可加 xdist（`snapshot.py` 固定檔名競態，實測 1/3～4/9 翻紅，v0.01 依鐵律不可原地改），
故鎖住「不加」（`CiGatePs1FallbackXdistTest`）而非加旗標；真正缺口＝fallback 無 LATEST 軌，另立
DEF-200-318（open）。GAP-E 立 DEF-200-317 並以 tomllib 讀 pyproject 斷言（同輪 fixed）。棘輪重釘：
`skip_tag_policy._TREE_FILE_FLOORS["tools/tests"]` 61→62（新增 test_cpu_budget.py 使樹 77→78 支）。

**B 包（DEF-200-290＋292）**：root-infra-ci 哨兵 step 補抓最近成功 nightly-full run 的 `headSha`，對
`WATCHED_PATHS`（12 條：AutoClaude pyproject／conftest／local_ci_gate 三檔、ci-gate.sh／.ps1、
parallel_shard／cpu_budget／run_root_unittests、兩支 compat-ci yml）最後改動做 `git merge-base
--is-ancestor`，未涵蓋只 `::warning::`（advisory：nightly-full 每週一班，硬阻斷會紅到下個週日）；gh／git
失敗只 warning 說明無法評估。mac／win 告警 job：開單前 `gh label create p1／<平台>／nightly --force`
自癒（idempotent），開單 step 移除 `continue-on-error: true`、`gh issue create` 失敗 `::error::`＋exit 1；
自動關閉 step 未動。B 包本機以真 git 驗 SHA 判準：對 HEAD rc=0、對 HEAD~30 rc=1、對假 SHA rc=128 各走
對應分支（[他包回報]）。

**收尾單人窗口（主控）**：套 B patch（`git apply --check` OK）、解鎖並移除 B worktree、`git add` 兩新檔；
護欄行數棘輪重釘 100211→100695（+484＝內容 +445＋本檔自身漂移 +39；分軌：回歸鎖軌 257／功能軌 227；
`_REPIN_NET_CAP_SCHEDULE` 兌現 (153, 539) 並重新武裝 155／538；`_PHASE2_REVIEW_LOG` 依 R141 體例登記
`[提案]`）；帳本三筆結案、三筆新立（317 同輪修、318 open、319 同輪修）、五列縮到 700 bytes 內；
第一次 push 被 SDD leg `test_ci_paths_cover_root_consumers` 正確擋下（新檔未列入兩支 compat-ci 觸發 paths）→ 三支
workflow 補路徑；第二次 push 被 root leg 一支 error 擋下：`test_dev_start.TestSigintForwardsToBootstrapProcessGroup`
讀 pidfile 得空字串 `ValueError`（只等 `is_file()` 不等內容，孫行程 create→write 之間的 TOCTOU；同碼在第一次
push 與主控親跑皆綠＝時序性），立 DEF-200-319 並把該類別兩支同型測試改等 pid 文字 `isdigit()`（+6 行，歸回歸鎖軌）；`check_defect_log_crossref.py` 本場實跑
「✅ 缺陷帳本跨文件狀態一致：帳本 248 筆有效狀態紀錄、19 份掃描目標皆無矛盾」。

### 驗證數字（[他包回報] 者為 A／B／QA 子 agent 本場實跑，主控未重跑；其餘為主控本場親跑）

- [他包回報，QA] AutoClaude 本機全套 `4707 passed, 156 skipped in 32.92s`（real 33.297s、cpu 695%）；根層本機
  全套 real 143.25s、cpu 724%（QA 的 `tail -80` 被 skip 清單擠滿，`Ran／OK` 逐字未擷取——誠實列缺）。
- [他包回報，A] `PYTEST_XDIST_AUTO_NUM_WORKERS=3 … -n auto` 恰得 `[gw0] [gw1] [gw2]`；CLI `--legs 1`→9、
  `GITHUB_ACTIONS=true --legs 1`→9（本機 10 核 cap 9 使兩者相同）、`--legs 2`→4、`--bogus` rc=2。
- [他包回報，B] 針對性 `test_workflow_permission_concurrency_lock test_smoke_ci_sync` → `Ran 85 tests` OK；
  14 支紅→綠鑑別力全成立。
- 主控親跑：`python -m unittest test_adr_xplat001_c1c2_lock` → `Ran 192 tests in 11.604s` OK，
  `GLC_LINES=100689`；根層全套最終結果見下一行（本場回填）。
- 主控親跑根層全套（所有並行包停工、B worktree 移除後）：`rc=0`、`✅ unittest 數量下限釘選通過：發現 4340 個測試
  （下限 4246）`、`模組耗時排行（前 5，共 152 模組，平行模式，worker=9）` 首位 `test_archive_defect_log.
  TestMoveSubsetSelectionIsNamedAndTraceable: 94.0s`、`[skip census] tools/tests@darwin 共 46 支：platform=46
  ／tool-absence=0／env-disabled=0／structural-pair=0／debt=0／untagged=0`、time `932.08s user 118.66s system
  745% cpu 2:20.92 total`（最重派工單位 94.0s ＜ 牆鐘 140.9s，與 SD 快取實算「無結構性頭重腳輕」一致）。
  另 `ruff check` 八支改動 py 檔 rc=0（B 包一處 F841 未用變數由主控同行數替換為段落錨點斷言）、`bash -n`
  兩支 shell OK、三支 workflow yml `yaml.safe_load` OK、`ci-gate.ps1` 101 行全 CRLF。

### 🔴 誠實劃界（本輪仍未解決，不可宣稱已完備）

- CI headless 多 1 worker（4／4／3）原為公式推論；〈第十三輪〉SA 與 QA 各自對 07909c4d 三支 CI log grep 到
  root-infra `worker=4`／windows `worker=4`／macos `worker=3`，**已回填為實測**（本條保留以示曾為推論）。
- DEF-200-290 的 SHA warning 自本 push 起會持續出現到下次 nightly-full 成功為止——這是設計內訊號，不是回歸。
- DEF-200-292 的自癒與 fail-loud 要等下一次 nightly-full **真失敗**才能觀測 issue 是否真的開出來。
- DEF-200-318：`ci-gate.ps1` fallback 無 LATEST 軌；`run_local_nightly.ps1:46-50` 自陳本機 Windows nightly
  缺 SDD 雙軌 xdist 覆蓋——解鎖條件：fallback 補 LATEST 軌（帶 xdist，LATEST 現查 `sdd_version.py`）並擴
  `CiGatePs1FallbackXdistTest`，或掌舵者明文裁決 fallback 僅為降級路徑並在 .ps1 檔頭寫明。
- cap=9 仍是校準到單一 10 核筆電的硬編數字（SD-03 HYPOTHESIS）；`os.cpu_count()` 用邏輯核心、未考慮
  SMT／cpuset（SD-04）；自動細分候選層自落地至今在真實全套零觸發（SD-05，純安全網）；timing seed 只靠
  人工 `refresh_parallel_timing_seed.py`，CI 無 `--check` 提醒（SD-06）——四項皆未立帳，屬觀察。
- 護欄層 R152／R153 連續兩輪上升，`_REPIN_MAX_CONSECUTIVE_RISING_ROUNDS=2` 名額用罄 ⇒ **R154 必須淨減**。
- 掌舵者 Windows 11 物理機互動 session 親跑 `python tools/run_root_unittests.py` 仍待掌舵者本人執行；
  DEF-200-316 hook 單一載具方案 B 未動工（單人窗口、不可並行）。

## 第十三輪：四方獨立複審「R153 是否全部修好」＋兩缺口同輪收尾（2026-09-18）

### 背景

掌舵者要求 Architect／SA／SD／QA 四方（皆 Sonnet 5、唯讀、不共享上下文）獨立複審〈第十二輪〉的全部宣稱：
DEF-200-289／290／292／317／319 fixed、318 open、CI worker=4／4／3、無頭重腳輕、Q4 四項不做。主控（Fable）
只裁決、派工、收尾。額度守衛（converge 帶）限每 300s 兩次扇出，四方分三批派出。

### 四方判決（各自獨立；逐字輸出見各自 scratchpad 證據檔，本節只留存活發現）

- **SA：PASS**。六筆帳本列逐筆對程式碼核實（`pre-push:238-251`／`ci-gate.sh:272-286`／`ci-gate.ps1:46-52`
  匯出段、`root-infra-ci.yml:511-742` 哨兵 step 且 `WATCHED_PATHS` 逐條數＝12、兩支 compat-ci 告警 job 開單
  step 無 `continue-on-error`、`test_cpu_budget.py:135-153` tomllib 斷言、`test_dev_start.py` 兩支 `isdigit()`）；
  `check_defect_log_crossref.py` rc=0「帳本 249 筆有效狀態紀錄、19 份掃描目標皆無矛盾」；四處對帳
  100211→100695（+484）、回歸鎖軌 257／功能軌 227 一致；帳本第 291～321 行 bytes 全 ≤700（最大 695）。
  CI log 實測 root-infra `worker=4`／windows `worker=4`／macos `worker=3`（[他包回報]）。
- **QA：PASS**。獨立複核同三值；AutoClaude CI `4605 passed, 224 skipped in 67.28s (0:01:07)`；aisdlc-sdd-ci 四行
  `bringing up nodes...`；DEF-200-290 的 `##[warning]` 在 windows／macos 兩支 CI 皆為實際輸出；本機
  `cpu_budget.py --legs 1`→9、`--legs 2`→4、`--bogus` rc=2；`test_cpu_budget test_ci_gate_xdist_allowlist`
  `Ran 27 tests in 0.104s OK`；DEF-200-319 已硬化兩支連跑 3 次 OK、第三支同型未硬化者連跑 5 次 OK（本機重現不了
  CI-only 時序）；AutoClaude 本機全套 `4707 passed, 156 skipped in 31.31s`、`real 31.65／user 142.02`（user/real≈4.5）；
  `PYTEST_XDIST_AUTO_NUM_WORKERS=3` → `created: 3/3 workers`；`detect_imbalance` 對 git 追蹤種子（149 筆、總
  1063.5s、worker=9 fair_share=118.16s）回空、最重單位 0.74x；`ruff check` 四檔 rc=0（皆 [他包回報]）。
- **Architect：PARTIAL**。核心 SSOT 與廣播鏈成立，但「唯一」字面有兩處反例：`windows-compat-ci.yml`
  windows-nightly-full 與 `macos-compat-ci.yml` macos-nightly-full 各有內嵌 `pytest … -n auto --dist worksteal`
  繞過 ci-gate 廣播、xdist 自算核心數，今日數值巧合相同（CI 核心 ≤9）但結構性未覆蓋且零鎖 ⇒ **A-01**（立
  DEF-200-320）。DEF-200-318 判讀正確維持 open（凍結基線 `snapshot.py:159/249/299` 固定 `.tmp` 檔名；LATEST
  `snapshot.py:24-45` 已改 pid+uuid4）。Q4：root-infra-ci 逐檔 `py_compile` 184 檔本機序列 5.893s vs
  `compileall -q -j0` 0.141s，維持「留作候選」；`tools/*.py` 其餘 260 處 for-loop 未逐一稽核（資料不足）。
  root-infra-ci 無 `paths:` 過濾器（`test_root_infra_ci_has_no_paths_filter` 綠），此問對它不適用。
- **SD：PARTIAL**（設計面）。`run_parallel()` 為共用 `queue.Queue` 動態工作竊取；`detect_imbalance()` 門檻熱點 1.5x
  ／over_share 1.0x；152 單位 worker=9 fair_share=123.03s 最重 94.6s＝0.77x ⇒ 無頭重腳輕。🔴 **駁回兩處主控前提**：
  (1) xdist `-n auto` 讀的是 `psutil.cpu_count(logical=False)`（`xdist/plugin.py:31`），且本 repo 未宣告 psutil ⇒
  落回 `os.cpu_count()`，與 cpu_budget 殊途同歸但非設計保證（SD-02）；(2) A-01 兩個 step 的解析／安裝／pytest
  全在同一 `run:` 區塊，寫 `$GITHUB_ENV` 下一 step 才生效 ⇒ 正解是腳本內直接設 process-level env var（SD-01）。
  SA-01 第三支同型測試（`test_lock_stays_busy_via_killpg_while_any_grandchild_alive_then_clears`）仍只等
  `is_file()`＋`time.sleep(0.3)` 權宜緩衝，設計抽 `_wait_pid_text()` helper 三處共用、淨 -2 行。

### 主控裁決與實作（單一 Sonnet 實作包，四檔；記帳與文件由收尾單人窗口親做）

- **DEF-200-320（A-01）**：兩支 nightly-full step 在 `cd`／`Push-Location` 之前（相對路徑仍在 repo 根）呼叫
  `cpu_budget.py --legs 1` 設 `PYTEST_XDIST_AUTO_NUM_WORKERS`（bash `export`；pwsh `$env:` 並 `$LASTEXITCODE`
  非零即 throw）；既有 `-n auto --dist worksteal` 不動（xdist `plugin.py:17` 原生優先讀該變數）。鎖：
  `CpuBudgetExportWiringTest` 三支重複方法合併為 `test_orchestrators_export_cpu_budget`（`subTest` 五目標：
  ci-gate.sh／ci-gate.ps1／pre-push 另需 `AUTOSDD_PARALLEL_TESTS_WORKERS`，兩支 workflow 只需
  `PYTEST_XDIST_AUTO_NUM_WORKERS`），213→213 淨 0；紅綠自證：暫移 macos 新增段 →
  `AssertionError: '--legs' not found … target='macos-compat-ci.yml' FAIL`，還原 → `Ran 6 tests OK`（[他包回報]）。
- **DEF-200-319 第三支補硬化（SA-01）**：模組層 `_wait_pid_text(path, timeout)` 取代三處輪詢；第三支移除
  `time.sleep(0.3)`。三個類別各連跑 3 次全 OK（5.15s／6.08s／0.41s 級，未變慢）；`ruff check` 兩檔
  `All checks passed!`（[他包回報]）。`test_dev_start.py` 6655→6653。
- **淨減法輪記帳**：護欄行數 100695→100691（-4）；`repin_growth_problems()` docstring 兩段史料（ADR-XPLAT-013
  Phase2 (b) 分軌、DEF-200-208 例外名冊）搬至 `CrossPlatform_Guard_Line_History.md`〈repin_growth_problems
  分軌與例外名冊 WHY〉節抵銷本表自身新增列漂移；母項為負 ⇒ 不申報 `_REGRESSION_LANE_LOG`（同 R146／R151 體例），
  款(11) 連續上升計數歸零。主控親跑 `--print-guard-lines` 收斂：`# 淨額 100691→100691 (+0)`。
- **SA-02**：〈第十二輪〉誠實劃界第一條「待回填」已改寫為實測（見上）。

### 🔴 誠實劃界（本輪仍未解決）

- DEF-200-318 維持 open 未指派（解鎖條件不變）。
- SD-02：xdist `-n auto` 與 cpu_budget 的一致是 psutil 缺席下的巧合；nightly-full 兩 step 已改走 env var 廣播
  故不受影響，其餘 `-n auto` 站點（AutoClaude addopts）仍靠 pre-push／ci-gate 廣播，CI 直跑 AutoClaude 的 job
  靠 `GITHUB_ACTIONS=true` headless 判準——這條在 `AutoClaude CI` workflow 內**沒有**廣播段，數值今日相同但
  同屬「殊途同歸」，未立帳（觀察）。
- DEF-200-292 自癒尚無實測觸發證據（`gh label list` 無 p1／nightly 相關 label，nightly-full 未曾真失敗）。
- cap=9／`os.cpu_count()` 邏輯核心（SD-03／04）無 16+ 核機器可量測；timing seed 5 天未更新、CI 無 `--check`
  （advisory-only 設計）；py_compile→compileall 候選未動。
- 掌舵者 Windows 11 物理機 `python tools/run_root_unittests.py` 仍待親跑；DEF-200-316 方案 B 未動工（單人窗口）。
- A-01 兩支 workflow 的實際 `PYTEST_XDIST_AUTO_NUM_WORKERS=` 輸出要等下次 nightly-full（週日）才看得到。

## 第十四輪：掌舵者再問四問＋Windows 對話框根治＋四方審查→兩包實作→四方複審（2026-09-19，R157）

### 背景

掌舵者重提四問（Q1 帳本是否已解／Q2 功能與 CI 是否完備／Q3 有無頭重腳輕、自動偵測是否最佳／Q4 還有哪裡可用多 CPU），
要求 Architect／SA／SD／QA 四方（皆 Sonnet 5、唯讀、不共享上下文）先審查、再由 Developer 實作、再四方獨立複審；
主控（Fable）只裁決、派工、收尾。本輪首次在 20 邏輯核／14 實體核（i5-14600K、128 GB）的 Windows 11 物理機量測，
前輪「無 16+ 核機器可量測」的劃界自此可回填。審查中掌舵者另回報「一直出現『選取應用程式以開啟 Python』」，
一併查明根治（DEF-200-325）。

### 四方審查存活發現（各自獨立；逐字見 scratchpad 四份 *_R157_evidence.md，本節只留判決）

- **Architect／SA 各自獨立命中（P1）**：`ci-gate.sh` L282／`ci-gate.ps1` L54 的 DEF-200-289 廣播段是死碼——`REPO_ROOT`／`$repo`
  ＝`AISDLC_SDD/`，而 `tools/lib/cpu_budget.py` 住 monorepo 根；SA 親跑 `ls "$REPO_ROOT/tools/lib/cpu_budget.py"` rc=2
  `No such file or directory`。fail-open 把「路徑錯」與「環境本來沒有」混成同一靜默分支；`CpuBudgetExportWiringTest`
  只 `assertIn` 字面，第十二、十三輪四方審查因此皆判「匯出段存在」PASS（SA 對 13 筆帳本列逐列對帳：DEF-200-289 REFUTED、其餘 CONFIRMED）。
- **SD（量測，機器安靜、序列）**：根層全套 `AUTOSDD_PARALLEL_TESTS_WORKERS`=9／14／19 ⇒ 196.5s／166.8s／173.7s（4364 支，
  w=14 一次 rc=1＝`test_a_net_zero_swap_is_red` 撞到 `_zzz_loadbalance_repro_*` 暫態檔，w=9／19 皆 rc=0）；
  AutoClaude 全套 `--dist loadgroup` 9／14／19 ⇒ 72.9s／70.9s／69.6s（4853 passed，與 worker 數無關）；
  SDD v0.30 9／14 ⇒ 19.8s／18.8s。真因：conftest 把 tests/contract／integration／infra 三目錄整批標 `pg_serial`，
  loadgroup 下全部序列（SD-01）；cap=9 是 10 核筆電硬編校準，實體核 14 最佳、邏輯核−1（19）反而慢（SD-02）；
  `local_ci_gate.py::gate_pytest` 未設 `PYTEST_XDIST_AUTO_NUM_WORKERS`，xdist 自算走 psutil 實體核（SD-04）；
  自動細分對 test_dev_start／test_platform_neutral_paths 未觸發待查（SD-06）。
- **QA（CI log 實證）**：root-infra worker=4／windows 4／macos 3 與 headless 預期吻合；AutoClaude CI 主 job 無 `-v`，
  worker 數結構上看不到（QA-01）；本機直呼子集 `created: 14/14 workers`＝psutil 實體核、繞過 cpu_budget（QA-02）；
  `Ran 27 tests` 舊宣稱在 HEAD 為 25（4f74e4f 合併 subTest，非回歸）；A-01／DEF-200-292 仍待下次 nightly-full。
- **SA-04**：`design_xdist.md` 被 8 處引用為設計出處，git log --all 零命中，從未入庫。
- **Q4 重評**：第十二輪四項「不做」維持；root-infra-ci 逐檔 py_compile（本機 5.9s vs compileall -j0 0.14s）本輪落地。

### DEF-200-325：對話框根治（主控親查）

監看器（每 400ms 查 `Win32_Process Name='OpenWith.exe'`）＋單獨跑 `test_repo_venv_present_is_preferred`：09:49:12 起跑、
09:49:13 出現 `OpenWith.exe -Embedding`（COM 啟動、父鏈＝svchost，只能靠時間對位）。真因＝19f3e75 該測試把 python.exe
複製成無副檔名 `tmp/.venv/bin/python`，`Get-RepoPython` 以 `&` 探測 ⇒ CreateProcess 失敗回退 ShellExecute（DEF-101-759 同型）；
headless 實作者把「探針 rc/stdout 皆空」誤記為「& 呼叫限制」。修法：`Get-RepoPython` 在 Windows 主機只探測 PATHEXT 內候選
（`$isWindowsHost` 短路同 `Resolve-NativeExecutable`）；訂正 docstring＋文字鎖。修後同模組 111 tests OK、監看器 seen=0。

### 主控裁決與實作（兩包 Sonnet，檔案面互不相交；A＝根層＋SDD，B＝AutoClaude；凍結為 3f77c20）

- DEF-200-326 廣播路徑：`MONOREPO_ROOT="$(cd "${REPO_ROOT}/.." && pwd)"`／`Join-Path $repo '..'`，缺檔 stderr 出聲（仍 fail-open）；
  鎖 `test_ci_gate_broadcasts_target_monorepo_root` 以各檔自身根算法重算路徑並斷言 `is_file()`（對 5134ee8 舊文字紅）。
- DEF-200-327 cpu_budget：互動＝`max(1, min(16, physical-1))`（psutil optional，缺席退回邏輯核）、headless＝邏輯核不變
  （CI 4/4/3 零回歸、SD-05 風險規避）、CAP 9→16（>16 實體核未量測＝HYPOTHESIS）；本機 `--legs 1` 13、headless 16；
  `test_cpu_budget` 22 tests OK；`parallel_shard.worker_count` docstring／ONBOARDING §7 字面同步；SDD
  `test_ci_paths_cover_root_consumers` 登記 psutil 為 optional 外部模組。
- DEF-200-318 fallback LATEST 軌：`ci-gate.ps1` 於 v0.01 段後以 `sdd_version.py` 解析 LATEST、帶 `-n auto --dist worksteal`
  跑一軌；`CiGatePs1FallbackXdistTest` 改為恰兩處呼叫（凍結基線不得帶、LATEST 必須帶）。誠實劃界：本機有 Git Bash，
  ci-gate.ps1 薄委派 .sh，fallback 分支本體未在無 Git Bash 環境端到端真跑。
- DEF-200-328 AutoClaude conftest：`pytest_xdist_auto_num_workers` hook（env 覆寫優先；subprocess 呼叫根層
  `cpu_budget.py --legs 1`＝CLI 契約，不 import；缺檔／例外 fail-open）＋`pytest_sessionstart` 印
  `[cpu_budget] xdist workers=N source=env|cpu_budget|xdist-default`；5 支純函式鎖。實測 workers=13 source=cpu_budget、env=3 ⇒ 3。
- DEF-200-329 pg_serial：逐檔審計 81 支（Glob 現查；與任務書 83 差 2 支，已登記）：63 支不碰 PG、18 支保留；判準改
  「路徑前綴 且 原始碼含 `_PG_SOURCE_INDICATORS`／`_PG_CLASS_NAME_RE`」或 `pg_real`，讀不到檔一律保守視為碰 PG，裸字面
  `factory` 刻意不列（會誤配 `canonical_playbook_id`）。全套 3 次 29.27s／29.08s／29.51s，4858 passed 10 skipped，rc=0。
- DEF-200-330：Dev-A 探針證實 `parallel_shard._worker_main()` 硬釘 start_dir＝tools/tests（AISDLC_SDD 側靜態路徑解析需求），
  fixture 改走暫存目錄會 shard_crashed ⇒ 改由護欄掃描器三處檔案列舉排除 `_zzz_` 前綴（全庫第五輪同型慣例）。
- DEF-200-331：8 處 `design_xdist.md` 引用改指本檔〈第九輪〉。
- SD-06：主控本場親跑 `auto_class_level_candidates(live_hints, w)`：w=13／14 候選含 test_dev_start，w=19 另含
  test_extras_quoting_zsh_safety／test_run_root_unittests——機制正常，Dev-A 查明 w=14 當時 fair_share 160s 高於 152s
  屬正當不觸發；鎖 `test_auto_split_follows_fair_share_not_module_size`（w=14 不細分、w=19 細分）。
- Q4：root-infra-ci py_compile 改兩階段（`compileall -q -j0` 全過即收工，失敗才逐檔印 `::error::`，保留 parity 判準字面）。

### 四方複審判決（各自獨立；逐字見 *_R157_review.md；實作凍結 3f77c20）

- **QA：PASS**。根層全套 rc=1（189.0s，worker=13，4371 支）——8 筆失敗中 7 筆逐字對應收尾窗口已知未完成
  （護欄棘輪 +55／guard_self 桶／E501 存量／帳本缺列），1 筆 `TraceIsolationTest` 為並行 agent 的 hook 寫入生產痕跡檔
  （環境自污染，非 diff 迴歸）；**根層全套＋SDD ci-gate 全程 OpenWith.exe 監看 seen=0**（對話框根治端到端證實）；
  AutoClaude 全套兩次 29.643s／29.640s 皆 4858 passed、`[cpu_budget] xdist workers=13 source=cpu_budget`；SDD ci-gate.sh
  67.5s rc=0（v0.01:1478／v0.30:1935／scripts/tests:354，log 兩次 `bringing up nodes` 證明廣播修復後 xdist 真的起來）；
  lint-imports 9 kept；root-infra-ci 兩階段片段本機真跑 `compileall -j0 全過（184 個 .py 檔）`。
- **SD：PARTIAL**。根層 default（w=13）166.94s，與四方審查最快值 w=14 166.80s 打平；AutoClaude w=13 29.59s、
  `PYTEST_XDIST_AUTO_NUM_WORKERS=6` 40.06s（pg_serial 收斂後仍有邊際平行效益）；makespan 下界 144.1s／實測 166.9s
  ⇒ 排程效率≈86%，下一個最值得拆的單位＝`test_archive_defect_log.TestMoveSubsetSelectionIsNamedAndTraceable`（144.1s）。
  **SD-1**：本輪新增斷言訊息一行顯示寬度 103 使 E501 存量債 139→140（收尾折行修復，棘輪常數不動）。
  **SD-2**：Dev-B 證據檔「18 碰／63 釋出」與程式化判準實測「25 碰／58 釋出」不符（方向安全：程式碼比人工表更保守）；
  收尾以機器判準數字為準（帳本列已改寫）。
- **Architect：PARTIAL**。十項宣稱九項 CONFIRMED；**ARCH-P1-01（P1）**：`pytest_xdist_auto_num_workers` 未標
  `@pytest.hookimpl(optionalhook=True)`，`-p no:xdist -o addopts=`（`gate_pg()`／`gate_pytest()` 非預設分支的真實 argv）
  在 collection 前撞 pluggy `PluginValidationError` ⇒ INTERNALERROR rc=3，父 commit 無此函式＝本輪新引入迴歸。
  ARCH-OBS-01：`_pg_models.py` ORM 類別不以 Pg 開頭，判準有結構性盲區（目前零命中）。
- **SA：PARTIAL**。追溯矩陣：四方審查全部存活發現皆對到 hunk 與鎖；四支鎖對 5134ee8 舊版逐一紅（鑑別力實證）；
  同樣獨立命中 optionalhook 迴歸（SA-NEW-01，隔離最小案例加裝飾器後 1 passed）；`check_defect_log_crossref.py` rc=0。

### 收尾單人窗口（主控親做）

- ARCH-P1-01／SA-NEW-01：conftest hook 加 `@pytest.hookimpl(optionalhook=True)`；新增 `test_conftest_survives_p_no_xdist_invocation`
  （真起子行程跑 `gate_claudemd_line()` 的 argv 形態）。實測：`tests/test_conftest_pg_group.py -q -p no:xdist -o addopts=`
  由 rc=3 ⇒ rc=0（6 passed）；鎖 6 passed。ARCH-OBS-01：`_PG_SOURCE_INDICATORS` 補 `_pg_models`。
- SD-1：line 429 折行；E501 存量債回到 139（鎖 `test_e501_debt_only_shrinks` 綠）。
- 帳本：新立 DEF-200-325～331（皆 fixed）、DEF-200-318 改 fixed（含未端到端真跑的劃界）；`check_defect_log_crossref.py` rc=0
  「帳本 261 筆有效狀態紀錄、19 份掃描目標皆無矛盾」，未結存量 34→33。
- MIN_TESTS 4246→4371（runner 自檢「餘裕只剩 89／214」指示；沿革補進 `CrossPlatform_Guard_Line_History_MinTests.md`）。
- 護欄行數棘輪：101607→101668（+61＝內容 +31＋本表自身 +30）；回歸鎖軌申報 61（raw +75，子集上限＝母項），主軌 0
  ⇒ 款(11) 連續上升計數歸零；cap 到期兌現 `(157, 537)`、重新武裝 159／536；`_ROOT_TOOLS_OLD_SCALE_DEBT_DUE_ROUND`
  具名展延 157→162；guard_self 桶 3162→3163 重釘（四方複審確認非功能迴歸）；`--print-guard-lines` 收斂 `+0`、
  指紋 53b023849913；鎖模組 200 tests OK。

### 驗證數字（[他包回報] 者為子 agent 本場實跑；其餘主控親跑）

- 主控收尾親跑（最終親跑）：根層全套 w=13 184.5s rc=1，3 筆失敗＝E501 折行前（已修，鎖回綠）、程式碼內 R157 字面撞輪號鎖
  （已改用日期指針）、`TraceIsolationTest` 競態（待立帳）；修後目標模組合跑 230 tests OK；護欄鎖模組 218 tests OK；
  `check_defect_log_crossref.py` rc=0；ONBOARDING §7 表②以乾淨 venv 載具回填兩次（137s／rc=0，`--check-snapshot` rc=0）。
  pre-push 實跑：第一次被 E501（139→141）＋指紋 stale 擋下；第二次五 leg 全過（推上 3f77c20＋5f71601，但收尾補正因
  commit 訊息檔缺失未入該次）；第三次（0b26a00）只剩 `TraceIsolationTest` 一筆翻紅被擋；第四次以 `AUTOSDD_PARALLEL_TESTS_WORKERS=9`
  重試——結果與雲端 CI 五支狀態見本輪 session 收尾回報，本檔於下一輪回填。

### 🔴 誠實劃界（本輪仍未解決）

- CAP=16 與「實體核−1」是單機（i5-14600K）加一個歷史點（10 核筆電）的校準；>16 實體核、GH-hosted runner 是否 SMT（SD-05）未量測。
- DEF-200-318 fallback 分支本體未在無 Git Bash 的 Windows 端到端真跑（本機恆薄委派）。
- pg_serial 釋出的 58 支（機器判準）靠原始碼指標判定；子目錄（tests/infra/adapters、tests/integration/test_sdd_bridge…）未逐檔登記進審計表，
  判準對其機械生效；fixture 間接觸碰 PG 的形態由本輪複審 SD 抽驗（見複審判決）。
- A-01 nightly-full 廣播輸出、DEF-200-292 自癒、掌舵者本人親跑 run_root_unittests.py：仍待。
- 待立帳（下一輪首件）：`TraceIsolationTest` 在 w=13 下約半數翻紅（生產痕跡 `autosdd_quota_degraded.jsonl` 被
  `source=no-account-key` 行程寫入，12:29:58／12:45:52／12:50:26 三筆，pid 未歸因、哨兵時刻不吻合）；本輪 push 以 w=9 降低重疊，
  不是修復。本輪未能立帳的原因＝工具衝突：帳本未結列淨額棘輪要求同一 commit 配對結案列，而逃生口 `AUTOSDD_NET_RATCHET_OFF=1`
  在 pre-push 同一 env 下洩入根層測試行程，使 test_check_defect_log_crossref 三支 env 敏感測試翻紅（實測 b3dc070 push 被擋）；
  下一輪先讓該三支測試自行隔離該環境變數，再立帳兩筆（TraceIsolationTest 競態、逃生口與 pre-push 互斥）。

## 第十五輪：四方獨立審查「R157 是否全部修好」＋三缺口修復（2026-09-20，R159；首次於 mac 覆核）

### 背景

掌舵者要求 Architect／SA／SD／QA 四方（皆 Sonnet 5、唯讀、不共享上下文）確認第十四輪（R157）的宣稱是否全部修好，並再答四問；
主控（Fable）只裁決、派工、收尾。本輪首次在 macOS（Apple M1 Max，`hw.physicalcpu=10`＝`hw.logicalcpu=10`、無 SMT；
根層單一 `.venv` 內 **psutil 缺席**）覆核——上一輪全部量測在 Windows i5-14600K 14P/20L。流程：三方（Architect／SA／QA）並行
唯讀審查 → SD 單獨在安靜機器上量測 → 15 條 F- 發現各派兩位反駁者（讀碼／重現鏡片）→ 4 條被推翻 → 三包實作（各自隔離
worktree、檔案面互不相交）→ 四方複審 → 收尾單人窗口。主控於本輪開始時對 main 手動 dispatch 兩平台 nightly-full
（run 35481684835 macos／35481686471 windows），供 C10／A-01 取證。

### 四方審查判決（皆 PARTIAL；逐字見 scratchpad 四份 `*_R159_evidence.md`，本節只留存活發現）

- **C1～C4、C6、C9 四方皆 CONFIRMED**（各自單獨跑鎖：`test_ci_gate_xdist_allowlist` 8 tests OK 含 `test_ci_gate_broadcasts_target_monorepo_root`；
  `test_cpu_budget` 22 tests OK；conftest `-p no:xdist -o addopts=` 子行程鎖 6 passed rc=0、env 覆寫 `source=env` 優先實測；
  本機 `compileall -j0` 0.133s vs 逐檔 5.863s，與註解宣稱 0.14s／5.9s 吻合）。Architect 另以 xdist 3.8.0 原始碼證實
  `pytest_xdist_auto_num_workers` 只在 controller 呼叫一次（worker 端 `setup_config()` 先把 numprocesses 清 None）。
- **C5 PARTIAL（平台差，非回歸）**：mac 全套 `4713 passed, 156 skipped in 34.82s`（QA 另一次 32.63s）vs Windows 4858；SD 以 conftest
  自身判準對 4869 個 collect-only nodeid 重算：**355 支／26 檔**觸碰 PG（R157 稱 25 檔，差 1，非阻斷）。
- **C7 NOT-VERIFIABLE-ON-MAC**；「同模組 111 tests」＝三檔合跑（`test_windowsapps_guard_bash_parity` 32＋`test_windowsapps_guard_cross_consistency` 76
  ＋`test_bootstrap_ps1` 3 ⇒ 反駁者實跑 `Ran 111 tests … OK (skipped=3)`）；SA 只算兩檔（108）、QA 算四檔（406）皆誤報，F-SA-05 被推翻、F-QA-04 保留為「文件可讀性」。
- **C8**：`_zzz_` 排除在 `tools/lib/guard_bucket_policy.py` L318／L352；`design_xdist.md` 字面殘留 2 處＝FSM 日誌資料、非設計引用。
- **C10 CONFIRMED（本輪 nightly-full 實證，A-01 結案）**：兩平台 dispatch 皆 completed/success。macOS nightly-full
  `PYTEST_XDIST_AUTO_NUM_WORKERS=3`＋`[cpu_budget] xdist workers=3 source=cpu_budget`；Windows `PYTEST_XDIST_AUTO_NUM_WORKERS=4`＋
  `[cpu_budget] xdist workers=4 source=cpu_budget`；ci-gate LATEST 軌兩平台皆 `bringing up nodes...`（v0.30：1949／1943 passed；
  scripts/tests：353／354 passed）。push 面 root-infra／windows／macos worker 4／4／3 QA 逐字重現。AutoClaude CI 主 job
  已可見 `[cpu_budget] xdist workers=4 source=cpu_budget`＋`bringing up nodes...`，但 `created: N/N workers` 只在帶 `-v` 的
  Equivalence Snapshot job 出現（F-QA-02 → 包 C）。`DEF-200-292` 帳本早於本輪 fixed（2026-09-18），R157 回報「仍待」措辭過期（F-QA-03，本節訂正）。
- **C11**：(a) CONFIRMED 且根因由反駁者**受控重現**：`TraceIsolationTest.test_the_real_production_trace_is_untouched_by_this_module`
  對 machine-wide `$TMPDIR/autosdd_quota_degraded.jsonl`（`quota_gate.quota_trace_path()`＝`tempfile.gettempdir()`，非 `~/.autosdd/traces`）
  做 byte-exact 前後比對；同機任何 session 的 hook 呼叫 `note_degraded()` 都會寫入（本場 tail 見 5 個不同 pid 在 14 分鐘內寫 `source=no-account-key`）；
  在測試視窗內注入一行 pid=999999 ⇒ `FAILED (failures=1)`，且斷言訊息誤歸因為「本測試寫髒」。記錄已含 `pid` 欄 ⇒ 改 pid 歸因（包 A）。
  (b) CONFIRMED 未修，範圍 **6 支非 3 支**（`TestNetNewVsClosedRatchet` 5＋`TestClosingRoundProblemsWiring` 1；乾淨 env `Ran 267 tests OK`、
  `AUTOSDD_NET_RATCHET_OFF=1` ⇒ `FAILED (failures=6)`）。(c) 未量測，維持 HYPOTHESIS。(d) CONFIRMED：psutil 於 pyproject／requirements／
  bootstrap 全庫零命中 ⇒ 乾淨環境「自動偵測實體核」結構上恆退回邏輯核（本機 10P=10L 巧合正確；SMT 機器缺 psutil 會算成 min(16,19)=16 而非 13）。
- **被推翻的 4 條**（各兩位反駁者 2/2）：F-ARCH-03「雙軌並行翻案」——真因＝v0.01 凍結基線 `snapshot.py` 固定 `.tmp` 檔名競態
  （本檔 L1133／L1148；v0.01 依鐵律不可原地改），與 CPU headroom 無關 ⇒ 維持不做；F-SA-02「subprocess 零隔離」——6 個站點皆經
  `_isolated_env()` 注入 TMPDIR/TEMP/TMP，`tempfile.gettempdir()` 子行程實測吃到沙箱；F-SA-03「簡報指錯目錄」——簡報從未提
  `~/.autosdd/traces`，SA 自己把 `endurance_env.py` 與 `quota_gate.py` 兩個 SSOT 混淆；F-SA-05 見 C7。F-SA-04（1/2）：DEF-200-328 列已明寫
  該 Windows 機 psutil 在場取 14 實體核 ⇒ 「13」無矛盾，不立案。

### SD 量測（mac，安靜機器、序列；逐字見 `sd_R159_evidence.md`）

- 根層全套 `AUTOSDD_PARALLEL_TESTS_WORKERS`＝9（cpu_budget 預設）**145s**／10 **140s**／5 **221s**，三次皆 rc=0；makespan 效率（下界/實測）
  78.2%／72.9%／92.3%；`detect_imbalance()` 1.5x 與自訂 1.3x 門檻皆 0 命中 ⇒ **無頭重腳輕**；最佳 w=10 僅比預設 9 快 3.4%（雜訊範圍）⇒ 預設維持。
  `auto_class_level_candidates()` 對 w=5／9／10 皆空集合（fair_share 門檻未達，非矛盾）。`TraceIsolationTest` 三次全綠（R157 是 w=13 觀察到）。
- AutoClaude 預設 `[cpu_budget] xdist workers=9 source=cpu_budget`；`PYTEST_XDIST_AUTO_NUM_WORKERS=5` ⇒ `workers=5 source=env`。
- SDD ci-gate.sh：v0.01 序列 11.15s、v0.30 xdist 16.53s；廣播成功路徑全靜默（F-SD-02 → 包 C）。
- Q4：pre-push 非測試步驟——10 支守門工具皆 <1.5s、ruff <0.1s、`integration_gate.sh --skip-full` 4s ⇒ 無新可平行候選；四項「不做」維持。

### 主控裁決（三包 Sonnet，各自隔離 worktree 交 patch；檔案面互不相交＝鐵律七）

- **包 A**（`tools/tests/test_check_defect_log_crossref.py`、`tools/tests/test_context_budget_guard.py`）：兩類別 setUp 整班隔離 `AUTOSDD_NET_RATCHET_OFF`
  ＋巢狀鎖；`TraceIsolationTest` 改 `foreign_trace_growth_problems(before, after, own_pid)`——只有 `pid == os.getpid()` 或無法歸因的新增行算洩漏。
- **包 B**（`tools/lib/cpu_budget.py`、`tools/tests/test_cpu_budget.py`＋字面同步）：`_detect_physical_count()`＝psutil → 平台原生
  （darwin `sysctl -n hw.physicalcpu`／linux `/proc/cpuinfo` physical id＋core id 唯一組合／win32 ctypes `GetLogicalProcessorInformation`
  計 RelationProcessorCore，**零 spawn**）→ None；fail-open 契約不變。
- **包 C**（三個廣播站點＋AutoClaude conftest＋兩支鎖檔）：成功路徑印 `[cpu_budget] broadcast workers=N source=cpu_budget|env`；
  `pytest_xdist_setupnodes`（optionalhook）印 `[cpu_budget] xdist nodes confirmed=N`。
- 不做：雙軌並行（真因競態）、pre-push leg 並行（SD 無數字支持）、GH runner SMT 量測（mac 做不到；headless 用邏輯核維持）。

### 實作（三包 Sonnet，各自隔離 worktree 交 patch；主控套 patch 後親驗；帳本 DEF-200-345～348）

- **包 A**：`_pop_leaked_net_ratchet_env()` helper＋兩類別 setUp；鎖 `test_a_leaked_escape_hatch_from_the_caller_cannot_flip_this_class`
  （拿掉隔離 ⇒ `FAILED (failures=1)`、還原 ⇒ OK）[他包回報]。`foreign_trace_growth_problems()`＋5 支鎖；受控重現（背景 thread 在測試
  視窗內對真檔追加 pid=999999 一行）：修前 `rc=1`（多了 63 bytes）／修後 `rc=0`，`restored ok: True` [他包回報]。
- **包 B**：`_detect_physical_count()` 三段（psutil → `_platform_physical_count()` → None）；純函式 `_parse_int_line`／`_parse_proc_cpuinfo`／
  `_count_processor_cores`；`test_cpu_budget` 22→41。win32 ctypes 分支只經 AST 掃描器守衛檢查、未真跑（劃界）。`parallel_shard.py`／
  ONBOARDING §7 無 psutil 字面，未動。
- **包 C**：三站點＋conftest `pytest_xdist_setupnodes`；鎖 `tools/tests/test_ci_gate_xdist_allowlist.py::test_orchestrators_broadcast_success_path`
  （`git show HEAD:` 修前三檔 grep 皆 0 ⇒ 先紅）與 `AutoClaude/tests/tools/test_local_ci_gate.py`（純函式＋optionalhook 屬性）。任務書指名
  `tests/test_conftest_pg_group.py` 有誤——既有 conftest 鎖住 `tests/tools/test_local_ci_gate.py`，Dev-C 貼齊慣例。沙箱擋 pwsh ⇒ 主控親跑
  `Parser::ParseFile` errors=0。
- 三包 diff 統計（2／2／6 檔）與 worktree staged 逐棵相符後套進主樹；三棵暫時 worktree 收掉（`block_destructive_git` 擋下 `--force` 一次，
  帶理由豁免後執行）。輪號字面零外洩（程式碼只用日期＋帳本號）。

### 驗證數字（主控親跑，套 patch 後、凍結前）

- root：`test_check_defect_log_crossref` `Ran 268 tests OK`（乾淨 env）／`AUTOSDD_NET_RATCHET_OFF=1` 亦 `OK` rc=0；`test_cpu_budget` `Ran 41 tests OK`；
  `test_ci_gate_xdist_allowlist` `Ran 9 tests OK`；`test_bash32_compat` 32 OK；`test_pre_push_dispatcher` 31 OK；`TraceIsolationTest` OK；
  `test_context_budget_guard` `Ran 659 tests` rc=0；`test_platform_neutral_paths` `Ran 177 tests` rc=0。
- ruff root 5 檔／AutoClaude 2 檔 `All checks passed!`；shellcheck 閘門 `11 筆 / 基線 11 筆 ✅`（pre-push 3 筆皆 HEAD 既有）；pwsh Parser errors=0；
  ci-gate.ps1 BOM＋CRLF 不變。
- AutoClaude：`tests/tools/test_local_ci_gate.py`＋`tests/test_conftest_pg_group.py` `100 passed`，輸出 `[cpu_budget] xdist workers=9 source=cpu_budget`／
  `[cpu_budget] xdist nodes confirmed=9`；`-p no:xdist -o addopts=` `100 passed`。
- cpu_budget（psutil 缺席）：`_platform_physical_count()=10`（sysctl）、`--legs 1`=9、`AUTOSDD_CPU_HEADLESS=1`=10。
- `check_defect_log_crossref.py` rc=0。
