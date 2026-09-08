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
