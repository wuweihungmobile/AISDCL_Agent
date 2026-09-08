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

**加速比**：740s → 257s（約 2.9x，8 worker；遠低於 8x 理論值——最重的一組 shard 依 LOC
權重仍獨占約 210s，屬已知、留待後續優化的效率議題，非正確性問題）。

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

**誠實劃界（修復後仍未涵蓋的邊角）**：`run_parallel()` 對 `Popen()` 呼叫前本身拋出的
非 `SystemExit` 例外，或 `merge_results()` 因不完整 payload 拋 `KeyError`，本輪未處理，
`leak_fence()` 對它們仍無 try/except；不屬本次「shard 崩潰以 SystemExit 回報」這一條
具體路徑的目標範圍。

## 帳本 ROW_MAX_BYTES 超標處置（本輪一併收斂）

上一輪落地時，`AutoSDD_Defect_Log.md` 該列的狀態欄寫入過長全文（2206 bytes），觸發
`test_check_defect_log_crossref.py::TestR79RowByteCeiling` 兩支失敗。依該測試紅字指路
的合法出口（帳本列是索引，長文搬進 `docs/06_quality/` 具名證據檔）處置：**本檔即為那個
搬遷目的地**，並已在 `tools/lib/governance_docs.py::_GOVERNANCE_DOCS` 登記（檔名
`CrossPlatform_DEF200274_Parallel_Tests_Evidence.md` 符合 `_GOVERNANCE_DOC_GLOBS` 的
`CrossPlatform_*.md` 樣式，`unregistered_governance_docs()` 對它結構上可見）；帳本列已
縮回一句話＋本檔指針，未把 ID 補進 `OVERSIZE_ROW_GRANDFATHERED`（那是砸溫度計）。

## 結案前待辦（尚未做，誠實列出）

1. 排查/證明跨 shard 並發執行時，涉及真實 OS 排程器狀態或共享追蹤目錄的測試模組不會互踩
   （或改良分片邏輯讓這類模組必定同 shard 串行）。
2. 補一支會真的 spawn subprocess 的整合測試，覆蓋 `run_parallel()`/`_worker_main()` 協定
   通道本身（目前的崩潰測試 mock 了 `subprocess.Popen`，未涵蓋真實子行程 stdout/stderr
   管線行為）。
3. 至少一次 Windows 真機驗證，才能解除「僅 macOS 驗證」的限制、宣稱雙平台可用。
4. `test_adr_xplat001_c1c2_lock.py` 的 guard-line 行數棘輪需重釘（本輪新增測試行數所致，
   屬既有機械物的收尾單人窗口範疇）。
5. `stderr` backpressure（未重導向、pipe buffer 理論上限）風險評估與必要時的緩解。

在上述五項未完成前，DEF-200-274 維持 `partial`，不宣稱 `fixed`/`closed`。
