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
  `ReportModuleTimingsPrintsWorkerCountTest`（不均偵測 v2）。
- `tools/tests/test_pre_push_dispatcher.py`：686→704（+18），新增
  `test_syntax_error_under_tools_fails_the_rootinfra_leg`（compileall 遷移
  語法偵測回歸鎖）。
- `tools/tests/test_adr_xplat001_c1c2_lock.py`（本檔）：guard-line R147 重釘
  自身逐檔漂移收斂 +104（`_GUARD_LINES_REPIN_LOG` 本輪多列＋`_FROZEN_GUARD_
  LINES` 反覆更新＋新增 `_REGRESSION_LANE_LOG` 列＋`_REPIN_NET_CAP_SCHEDULE`
  到期兌現 cap 543→542 與重新武裝下一段（`_REPIN_NET_CAP_DUE_ROUND=149`／
  `_REPIN_NET_CAP_DUE_TARGET=541`）＋`_PHASE2_REVIEW_LOG` 新增 R147
  `[維持觀察]` 列＋`_ROOT_TOOLS_OLD_SCALE_DEBT_DUE_ROUND` 具名展延
  147→152（非 root-tools 重構持有面，真拆仍待獨立窗口）＋
  `_REPIN_LOG_FROZEN_PREFIX_LEN` 181→203 與 `_REPIN_LOG_HISTORY_SHA256`／
  `_FROZEN_PREFIX_REWRITE_LEDGER` 重釘＋E501 存量債棘輪折行（8 行單行列改
  雙行避免過長行）。
- 分軌：回歸鎖軌 270（P1/P0 zshrc 假紅根治 119 行＋既有缺陷修復回歸鎖
  ParallelTimingCacheLoadHintsTest／ParallelShardSigtermCleanupTest／
  ParallelShardSigtermIgnoredOffMainThreadTest 151 行，未使用任何一次性例外
  名冊）；功能軌餘額 462（＝內容成長 358〔LPT 排序／保存／過期回報／大批
  持久化＋自動細分＋不均偵測 v2＋worker 數印出＋既有 cap 8→9 調整 340 行＋
  compileall 遷移回歸鎖 18 行〕＋本檔〔`test_adr_xplat001_c1c2_lock.py`〕
  自身記帳漂移 104 行，本輪刻意不把自身記帳漂移歸入回歸鎖軌以保留其 cap 309
  的餘裕）。回歸鎖軌 270 ≤ cap 309、功能軌餘額 462 ≤ 到期後 cap 542，
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
