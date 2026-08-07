# 全庫 skipped 測試盤點（R76，2026-08-05，Windows 11 真機實測）

> ## 🔴 R79 更新（2026-08-07）：本檔**不再是 skip 數的真相源**
>
> 掌舵者 S3 逐字：「為何會有 skipped？要如何才能測試到 skipped？**徹底解決 skipped，
> 沒有 skipped，全部可測**」。R76 的答案是這份 754 行的人工盤點，而那正是問題本身——
> R79 逐項實查確認：**全 repo 對「這次真的 skip 了幾支」零機械管轄**
> （`PG_CONTRACT_MAX_SKIPPED` 是唯一天花板、只覆蓋 `pg-contract` 一個 CI job；
> `AutoClaude/tools/local_ci_gate.py` 對 `skipped` 零字樣；根層 runner 只印不判；
> ONBOARDING §7 自陳 `skipped=N` 刻意不在鎖內）。於是這個數字每輪由人重新盤點一次，
> 而它可以在兩次盤點之間無聲上升——上升的樣子在摘要裡長得像「乾淨」。
>
> **R79 落地的三件事**（詳見 `AutoSDD_Defect_Log` 的 R79 D-skipped 列）：
> 1. **skip 理由分群標籤化**：`tools/lib/skip_tag_policy.py` 由 4 個標籤擴為 7 個、
>    歸成 6 群（platform／tool-absence／env-disabled／structural-pair／debt／untagged）。
> 2. **逐群天花板 ＋ 雙單邊棘輪**：`_RUNTIME_SKIP_CEILING`（只准降，由
>    `_RUNTIME_SKIP_CEILING_MAX` 守）× 群數只准增（誠實登記新群不會轉紅）。
>    消費者＝`AutoClaude/tools/local_ci_gate.py::check_skip_census`，rc 真的被吃。
> 3. **本機預設路徑自動注入 DSN**：`local_ci_gate.py::pg_autodetect` 探到 localhost:5432
>    且該 DB 已被 migrate 就注入 ⇒ 「甲類 skip」預設就會跑，不再靠人記得。
>
> **R79 當回合實測（Windows 11 真機、repo `.venv`、`pytest tests/ -q -rs`）**：
>
> | 狀態 | 結果 | rc |
> |---|---|---|
> | 未設 DSN（R76 以來的本機預設） | 4069 passed／135 skipped／92.17s | 0 |
> | 設好三個環境變數（＝R79 自動注入後的預設） | 4160 passed／44 skipped／91.80s | 0 |
>
> ⇒ **91 支由 skip 轉 passed，耗時零增加**。這 91 支裡沒有一支是缺件——PG 容器長駐
> healthy、`.venv` 的 sqlalchemy/psycopg2/pgvector/asyncpg/alembic 全裝、DB 已在
> `alembic upgrade head`。缺的只有三個環境變數。
>
> 🔴 **打開之後掉出來的東西才是重點**：`tests/perf/test_pgvector_recall_perf.py`
> （ADR-SD08-003 §2.2「p95 < 50ms」SLA 在測試層的唯一代言人）自 2026-06-12 落地起
> **一次都沒被執行過**——全 repo 沒有任何通道設 `PG_REAL_ENABLED`，而且首次真跑立刻
> `TypeError`（建構子與 `search()` 兩處簽章都對不上），修好簽章後又量到單位錯誤
> （每個樣本 100 次查詢 vs 每次查詢 50ms 的 SLA，差 100 倍）。R76 把它歸進「誠實劃界、
> 補不了」那一格，理由「跑不到」——那句話對，但它讓後續三輪都以為問題只有一層。
> **凡是被歸進「不可覆蓋」的格子，都可能藏著同型的第二層。**
>
> 本檔 §1 起的所有數字是 **R76 當時**的量測，保留為史料；要看現況請跑
> `local_ci_gate.py`（會印 `[skip census]` 一行）或直接跑 `pytest tests/ -q -rs`。

> **緣起**：掌舵者提問逐字——「請問測試的程式中為何會有 skipped 的部分？例如 AutoClaude
> pytest 3900 passed / 224 skipped，要如何才能測試到 224 skipped 這個部分？」
>
> 本檔是全庫第一份 skip 盤點。此前 repo 有**機制**（`tools/lib/skip_tag_policy.py`
> ＋ `skip_static_scan.py` 的站點分類棘輪、`run_root_unittests.py` 的 `report_all_skips`
> 逐支明細），但**沒有任何一份文件回答「這 224 支要怎麼跑到」**——ONBOARDING §7 表② 只
> 記一個數字，且明文自陳 `skipped=N` **不在鎖內**（dated snapshot）。
>
> 🔴 **本檔的每一個數字都是 R76 當回合在 Windows 11 Pro（26200）原生 PowerShell 上實跑
> 取得**，不引用任何既有文件的宣稱。指令與 rc 逐項附在 §1。

---

## 1. 本輪實測基線（四棵樹 ＋ 一棵超出既有掃描射程的樹）

| 測試樹 | 指令（cwd） | 實測結果 | rc |
|---|---|---|---|
| AutoClaude pytest | `AutoClaude` ／ `python -m pytest tests/ -q -rs -p no:randomly` | **3900 passed, 224 skipped, 1 warning in 89.62s** | 0 |
| 根層 unittest | repo 根 ／ `python tools/run_root_unittests.py` | **Ran 1903 tests in 303.365s — OK (skipped=43)** | 0 |
| SDD v0.01 fsm_runtime | `AISDLC_SDD/AISDLC_SDD_v0.01` ／ `pytest tools/fsm_runtime/tests/ -m 'not chaos' -q -rs` | **1478 passed, 4 skipped, 34 deselected, 14 subtests passed in 34.34s** | 0 |
| SDD v0.30（LATEST）fsm_runtime | `AISDLC_SDD/AISDLC_SDD_v0.30` ／ 同上 | **1742 passed, 6 skipped, 34 deselected, 14 subtests passed in 44.41s** | 0 |
| SDD scripts/tests | `AISDLC_SDD` ／ `pytest scripts/tests/ -q -rs` | **4 failed, 316 passed, 1 skipped, 31 subtests passed** | 1 |

> ⚠️ **scripts/tests 那 4 紅不是本 repo 的缺陷、也不是本盤點的發現**：同輪另一個並行掃描員
> （Scan-N）在工作樹留下探針檔（`git status` 實查：`AD docs/06_Quality/probe_r76_scan_n.md`、
> `AD docs/r76scannlongpathsegment/…/probe.md`），`test_ntfs_length_gate.py:311` 與
> `test_copy_on_evolve.py` 因此判紅。**skip 那一欄不受影響**（1 支，理由「Unix chmod 分支在
> Windows 不可達」），故本檔只採該欄。這是「並行突變互踩假紅」的又一次重演，記在此處以免
> 未來讀者把它當成 R76 的退化。

**AutoClaude 的 224 支與 ONBOARDING §7 表② Windows 欄逐字相符（3900 / 224）**，
根層 43 亦與表① 相符 ⇒ 兩個基線在**掃描當下**為新鮮。

> 🔴 **R76 PKG-C 落地後這個基線已過期**：本包在
> `AutoClaude/tests/test_conftest_windows_native_skip_report.py` 併入 2 支反方向回歸鎖
> （§4.6），樹淨增 2 支 ⇒ Windows 欄應為 **3902 / 224**（全新 `[dev]` venv 實測，§4.5）。
> 收斂包須跑 `sync_onboarding_baselines.py --write --with-slow` 回填。
> PKG-C 無 `ONBOARDING.md` 授權，且該檔本輪由別的包持有，故不就地改。

### 1.1 靜態站點普查（五棵樹，含兩棵**超出**既有掃描射程者）

用 repo 既有的 `tools/lib/skip_static_scan.py` 對五棵樹跑一次（唯讀，未改任何檔）：

| 樹 | 檔數 | 站點數 | windows-only | posix-only | tool-absence | runtime-skipTest | unclassified |
|---|---|---|---|---|---|---|---|
| `tools/tests` | 53 | 74 | 13 | 11 | 38 | 12 | 0 |
| `AutoClaude/tests` | 255 | 30 | 8 | 6 | 16 | 0 | 0 |
| `AISDLC_SDD/scripts/tests` | 29 | 13 | 1 | 1 | 11 | 0 | 0 |
| `SDD_v0.01/fsm_runtime/tests` 🔴 | 52 | 1 | 0 | 0 | 1 | 0 | 0 |
| `SDD_v0.30/fsm_runtime/tests` 🔴 | 76 | 4 | 1 | 1 | 2 | 0 | 0 |

前三列與 `skip_tag_policy._SITE_CLASS_CENSUS` 的棘輪基線**逐格相等** ⇒ 該棘輪在 R76 為新鮮。
🔴 後兩列**不在 `_EXTRA_SCAN_TREES` 射程內**（見 §6 findings）。

### 1.2 為何「站點數」永遠回答不了掌舵者的問題

`AutoClaude/tests` 只有 **30** 個靜態站點，卻產生 **224** 支 runtime skip。差額來自四種
靜態掃描**結構上看不到**的形態：

1. `@pytest.mark.parametrize` × class 級 `skipif` ⇒ 一個站點乘出 N 支（本輪最大一筆：
   `test_ac_matrix_scaffolding.py:217` 一個站點 = **29 支**）。
2. 模組級 `pytest.importorskip("sqlalchemy")` ⇒ 整檔跳過，**連 collect 都少算**
   （ONBOARDING §7 已記載這個差額）。
3. `conftest.py::pytest_collection_modifyitems` 動態注入的 skip marker（`pg_real` 那一批）。
4. fixture 內的 `pytest.skip()`（`real_pg_dsn` fixture）。

**所以「站點棘輪全綠」與「224 支裡有多少是洞」是兩個不同問題**。ONBOARDING 自己也寫了
「站點 ≠ 測試支數」，但沒有人把後者盤出來——本檔補的就是這一格。

---

## 2. AutoClaude 224 支的逐類統計（依 skip reason 歸類，總和 = 224）

歸類軸依任務書 (a)~(f)。**「雲端覆蓋」欄是逐 workflow 實查**（見 §5）。

| # | 類別 | 支數 | 佔比 | 代表 reason（逐字） | 有任何通道跑到嗎 |
|---|---|---|---|---|---|
| **(d)** | **選配套件未安裝（extras）** | **69** | 31% | `sqlalchemy 未安裝；DDL snapshot 略過`（59）／`could not import 'sqlalchemy'`（3）／`sqlalchemy 未安裝`（3+1）／`could not import 'claude_agent_sdk'`（3） | 🔴 **零通道** |
| **(c)** | **環境旗標／DSN 未設** | **93** | 42% | `需設定 AUTOCLAUDE_DB_DSN 或 AUTOCLAUDE_TEST_PG_DSN 才能跑 00XX 契約測試`（16+15+12+10+10+8+5+2＝78）／`PG backend 契約測需 docker-compose postgres:17 + AUTOCLAUDE_TEST_PG_DSN`（11）／`SD_07 pg_real：未啟用 SD07_REAL_PG_E2E_ENABLED=true 或缺 DSN`（3）／`pgvector recall 性能僅在 perf machine 跑`（1） | 部分：**14 支有**（11 → `pg-contract` 硬閘、3 → `pg-e2e-nightly`）；**79 支零通道** |
| **(e)** | **刻意永久 skip（技術債）** | **29** | 13% | `W0 scaffolding：對應 Wave 開工時將 skip 移除並挪到專屬測試檔` | 🔴 **結構上不可能**（無條件 `pytest.mark.skip`，函式體是 `pytest.fail()`） |
| **(a)** | **平台條件（POSIX／macOS 專屬）** | **17** | 8% | `需要 POSIX bash 實跑本 .sh`（12）／`POSIX process group 專屬`（2）／`POSIX killpg 專屬行為`（1）／`POSIX process-group 孤兒防護僅適用於 POSIX`（1）／`macOS 真機專屬（非 Darwin 上 skip 而非恆綠）`（1） | ✅ **16 支有**（ubuntu `test` job 全跑）；1 支只在 `macos-nightly-full`（非阻斷排程軌） |
| **(b)** | **外部依賴／權限缺席** | **16** | 7% | 🔴 **R79 收輪改判**：這 11 支的 reason 已在樹上改寫（本欄不再逐字複製，避免第二個家；現查 `Select-String -Path "$r\AutoClaude\tests\test_gap014_020.py" -Pattern 'requires_claude_cli' -Context 0,10`）。舊 reason 把 `CLAUDECODE=1` 講成**死結成因**，R79 實測證偽：剝除該變數的對照組行為完全相同 ⇒ 它是巢狀環境的**標記**不是成因，真正掛住的是「巢狀 session × `wexpect.spawn()`」這一組（見 `DEF-101-913`）。判準維持不變、只改寫 reason（11）／`PG CRUD 行為快照需 docker-compose postgres:17 + AUTOCLAUDE_TEST_PG_DSN env var`（4）／`本機無建立 symlink 權限（[WinError 1314]…）`（1） | 1 支有（symlink → ubuntu）；**15 支零通道** |
| **(f)** | **無理由／理由空泛** | **0** | 0% | — | — |
| | **合計** | **224** | 100% | | **192 支（86%）零通道，見 §5** |

> **(f) 為 0 是好消息，但只對 AutoClaude 成立**：224 支**每一支都有非空 reason 字串**。
> 根層 unittest 那 43 支則有 11 支（26%）對標籤機制隱形，見 §3。

### 2.1 三個最大單點

| 站點 | 支數 | 性質 |
|---|---|---|
| `tests/contract/test_pg_existing_schema_lock.py`（整檔） | **63** | 只缺 `sqlalchemy`＋一個 PG。§4 已實測**修好後 62 passed** |
| `tests/contract/test_ac_matrix_scaffolding.py:217`（1 個站點） | **29** | 無條件 skip，任何環境變更都跑不到。§2.2 實測：**23/29 的 target 檔已存在** |
| 六支 `test_alembic_00XX.py` ＋ `test_three_tier_schema.py` | **71** | 雙層閘門（DSN env → psycopg2），§4 已實測層次 |

### 2.2 那 29 支永久 skip 的實測體檢

`test_ac_matrix_scaffolding.py` 的 `AC_MATRIX` 有 29 條，每條帶一個 `target_test_file`。
R76 逐條檢查該路徑是否存在（唯讀腳本，未改 repo）：

```
entries: 29  waves: 29
target exists   : 23
target MISSING  : 6
   MISSING: .importlinter / tests/contract/test_brain_executor_isolation.py   ← 不是路徑
   MISSING: .importlinter runner-no-checkpoint-logic                          ← 不是路徑
   MISSING: tests/contract/test_w6_deletion.py
   MISSING: tests/integration/test_concurrent_runs.py
   MISSING: tests/integration/test_config_schema_api.py
   MISSING: tests/integration/test_sigint_checkpoint.py
```

**23/29（79%）指向的檔案已經存在**——也就是那些 Wave 早就做完了，佔位 skip 卻還留著，
而它的 reason 逐字寫著「**對應 Wave 開工時將 skip 移除**並挪到專屬測試檔」。
同時該測試的 docstring 第 3 條又寫「若已 100% 對位至 target_test_file，**本 case 仍保留
skip 以維 SSOT**」——**reason 與 docstring 直接矛盾**：一個說會移除、一個說永遠留。
另有 2 條的 `target_test_file` 根本不是檔案路徑（`.importlinter / tests/...` 這種混寫）。

⇒ 讀到這 29 支 skip 的人**無法判斷哪幾條是真的還沒做**。這正是 (e) 類要點名的理由：
它讓「沒在測」變成隱形，而且是 224 支裡佔比第二大的單一站點。

---

## 3. 根層 unittest 43 支的逐類統計

`report_all_skips` 每次跑閘門都逐支印出（DEF-101-510 要求），R76 實測分佈：

| 標籤 | 支數 | 內容 |
|---|---|---|
| `[MAC-NATIVE-ONLY]` | **24** | `install_mac_nightly.sh` 家族（`plutil`／BSD `date -v`／launchd plist 語意） |
| `[POSIX-NATIVE-ONLY]` | **8** | `os.killpg`／process group／POSIX shell 載具 |
| **未標籤** | **11** | 見下表 |

**11 支未標籤逐支盤點**（這是本檔的 (f) 類真正的落點）：

| 支數 | reason（逐字） | 為何算「隱形」 |
|---|---|---|
| 6 | `tools/dev_start.sh 檔頭自陳為 macOS/Linux 專用（Windows 對等＝tools/dev_start.ps1，由本檔第一部分覆蓋）——不在 Windows 上驗證非目標平台的殼` | 語意就是 POSIX-only，卻沒帶 `[POSIX-NATIVE-ONLY]`。這 6 支對應 1 個靜態站點，正是 `_POSIX_TAG_RATCHET['tools/tests'] = 1` 那筆**被凍結的欠債** |
| 2 | `[TOOL-MISSING] 找不到版本 < (3, 11) 的真直譯器…` | 🔴 作者**有意**標籤，但用的字面是 `[TOOL-MISSING]`，而 SSOT 註冊的是 `[TOOL-ABSENCE]`（`skip_tag_policy.py:44`）⇒ 報告器判為「未標籤」。**兩套詞彙、零機械物比對**（finding F3） |
| 2 | `需要 zsh` ／ `本機無 zsh` | 純工具缺席，未帶 `[TOOL-ABSENCE]`（該標籤刻意不接 rc，見 `untagged_tool_absence_sites` docstring） |
| 1 | `本機無建立 symlink 權限（[WinError 1314] …）` | 同上 |

---

## 3.1 標籤覆蓋的方向不對稱：Windows 側 8/8、POSIX 側 0/6

`AutoClaude/tests` 的 14 個平台方向站點逐支查標籤（靜態普查輸出逐字）：

| 方向 | 站點數 | 已帶標籤 | 逐支 |
|---|---|---|---|
| `windows-only`（非 Windows 才 skip） | 8 | **8／8 = 100%** | `test_perception.py:345`、`tools/test_run_local_nightly_static.py:245,1348,1489,1578,1797,1873,2061` 全部 `TAG=[WINDOWS-NATIVE-ONLY]` |
| `posix-only`（Windows 才 skip） | 6 | **0／6 = 0%** | `test_evaluator_kill_tree.py:56,91,112`、`test_perception.py:412`、`test_perception_platform_honesty.py:84`、`tools/test_run_local_nightly_sh_static.py:186` 全部 `TAG=-` |

後果（實測）：在整份 224 支的執行輸出裡 `Select-String 'NATIVE-ONLY|TOOL-ABSENCE'` → **零命中**。
`AutoClaude/tests/conftest.py:261-270` 那段 R74 新增的
`POSIX/MAC-NATIVE-ONLY SKIPS (本次跑在 Windows 上失去的覆蓋)` 區塊，
**在每天實際跑的這一側一行都不會印**——因為 `non_windows_native_skips()` 恆回空清單。
而 `_POSIX_TAG_RATCHET['AutoClaude/tests'] = 6` 把這 6 筆凍結成「可見欠債」⇒
棘輪永遠綠、摘要永遠空。詳見 finding F2。

#### ✅ R76 PKG-C 已修（本節上表的「0／6」現已作古，保留原文以存證）

三件事同一輪做完，**修法與取證都在 §4.6**：

| 動作 | 前 | 後 |
|---|---|---|
| 6 個 posix-only 站點補標籤（5 檔 6 處；`test_perception_platform_honesty.py:84` 依其 `!= "darwin"` 條件用 `[MAC-NATIVE-ONLY]`，其餘用 `[POSIX-NATIVE-ONLY]`） | 0／6 | **6／6** |
| `skip_tag_policy._POSIX_TAG_RATCHET['AutoClaude/tests']` | 6（凍結存量） | **0**（欠債清空） |
| conftest 反方向摘要在 Windows 上的實際輸出 | **0 行**（結構性沉默） | **17 行**（§4.6 逐字） |
| 反方向摘要的回歸鎖 | **零**（整段刪掉全綠） | 2 支（正向＋負向），併入既有 `tests/test_conftest_windows_native_skip_report.py`（R76 當時的理由是護欄層**檔數**棘輪「禁新增鎖檔」——🔴 **R79 訂正：那條裁決在 R77 就已被取代**，現行約束是護欄層**行數**棘輪 `tools/tests/test_adr_xplat001_c1c2_lock.py::TestGuardLayerRatchet`，語意逐字為「新增檔案本身不違規，**淨行數上升**才違規」。原文把已退場的檔數棘輪寫成**現行**約束，照著讀的人會以為新鎖一律不准開檔而把它塞進別的樹去；R79 實測這件事已經發生過一次） |

另補一道 **shrink-only 天花板** `_POSIX_TAG_RATCHET_CEILING`：舊判準是「相等」，
於是它的失敗訊息會誠實地把「把基線改成實測值」列為出口之一——**新增未標籤站點後把 6
改成 7，鎖當場全綠，欠債被合法加大且看起來像在維護基線**。天花板讓「加大欠債」變成必須
同時改兩個常數的顯式動作。誠實劃界：兩個常數住同一支檔，擋不了「同一個 commit 把天花板
一起改大」——本表買到的是**可見度**（那個動作會出現在 diff 裡、可被複審點名），不是
不可能性；真正的不可能性只有把欠債清成 0，`AutoClaude/tests` 本輪做到了。

另注意 `test_perception_platform_honesty.py:84` 的條件是 `skipif(sys.platform != "darwin")`，
語意是 **darwin 專屬**（正確標籤應為 `[MAC-NATIVE-ONLY]`），但分類器只有兩極
（windows／non-windows）故歸進 `posix-only`——在 ubuntu 上它同樣會 skip，所以
「ubuntu job 覆蓋 posix-only」這個推論對它**不成立**（§5.2 已單獨列出）。

---

## 4. 本輪實測：三類 skip 真的跑起來（前後對照 ＋ rc）

> 🔴 這一節是本檔唯一不可省的取證。沒有實跑的盤點只是猜測清單。

### 4.1 Demo A —（c）環境旗標 ＋（b）外部依賴：`SDD_RUN_TLC=1`（TLA+/TLC 五軌）

同一組 4 支檔案，只差一個環境變數。載具：`AISDLC_SDD/AISDLC_SDD_v0.30`。

```powershell
# 前（不設旗標）
& $py -m pytest tools/fsm_runtime/tests/test_phase_m.py tools/fsm_runtime/tests/test_phase_n.py `
      tools/fsm_runtime/tests/test_tla_python_sync.py tools/fsm_runtime/tests/test_meta_halt.py `
      -m 'not chaos' -q -rs -p no:randomly
# 後（$env:SDD_RUN_TLC='1'）同一條指令
```

| | 結果 | rc | 耗時 |
|---|---|---|---|
| **前** | `92 passed, 4 skipped` — 4 支 reason 皆 `set SDD_RUN_TLC=1 to run full TLC（離線可達性不變量已常駐守門）` | 0 | **0.99s** |
| **後** | **`96 passed`（skipped=0）** | 0 | **333.01s** |

**這一格同時證明兩件事**：① 旗標是唯一開關；② 外部依賴（Java ＋ `tla2tools.jar`）在本機
**已具備**——`Get-Command java` → `C:\Program Files\Android\Android Studio\jbr\bin\java.exe`，
jar 實存於 `AISDLC_SDD/AISDLC_SDD_v0.30/tools/fsm_runtime/formal/lib/tla2tools.jar`。
**代價就是那 332 秒**，這正是它被放在旗標後面的原因（合理設計，不是洞）。

### 4.2 Demo B —（c）環境旗標的**層次**：DSN 設了還是跑不到

```powershell
$env:AUTOCLAUDE_TEST_PG_DSN='postgresql+asyncpg://autoclaude:autoclaude@localhost:5432/autoclaude'
& $py -m pytest tests/contract/test_alembic_0010_fk_three_step.py tests/contract/test_three_tier_schema.py -q -rs
```

| | reason 逐字 | rc |
|---|---|---|
| **前** | `需設定 AUTOCLAUDE_DB_DSN 或 AUTOCLAUDE_TEST_PG_DSN 才能跑 0010 契約測試` | 0 |
| **後** | `could not import 'psycopg2': No module named 'psycopg2'` | 0 |

🔴 **結論：把 DSN 設好只是把第一層閘門打開，reason 換一句話而已。** 這 71 支需要
**DSN ＋ `psycopg2` ＋ 一個跑得動 `alembic upgrade head` 的 PG** 三者同時到位。
任何只寫「設 DSN 就能跑」的指引都是錯的。

### 4.3 Demo C —（d）選配套件：63 支 → 62 passed

**關鍵背景（實查）**：本機此刻有一個健康的 PG 容器在跑——
`docker ps` → `autoclaude_pg  pgvector/pgvector:pg18  Up 2 days (healthy)`，port `5432`。
**資料庫從來不是瓶頸，缺的是 venv 裡的 driver。** 實查 repo venv：
`sqlalchemy ABSENT / psycopg2 ABSENT / pgvector ABSENT / anyio PRESENT / click PRESENT`。

為了不污染其他並行掃描員共用的 `.venv`（ONBOARDING §7 明文警告 pgextras 會讓 `passed`
虛高），本示範在 **scratchpad 另建一個 venv**，repo 的 `.venv` 零改動：

```powershell
uv venv <scratchpad>\pgvenv --python 3.11
uv pip install --python <scratchpad>\pgvenv\Scripts\python.exe `
   'sqlalchemy>=2.0' 'psycopg2-binary>=2.9' 'pgvector>=0.3' 'alembic>=1.13' 'tenacity>=8.2' `
   'cachetools>=5.3' 'pydantic>=2.0' 'pyyaml>=6.0' 'httpx>=0.27' 'pytest==9.1.1' `
   'pytest-mock>=3.14' 'hypothesis==6.156.6' 'asyncpg>=0.29'
$env:PYTHONPATH='<repo>\AutoClaude'
$env:AUTOCLAUDE_TEST_PG_DSN='postgresql+asyncpg://autoclaude:autoclaude@localhost:5432/autoclaude'
& <scratchpad>\pgvenv\Scripts\python.exe -m pytest tests/contract/test_pg_existing_schema_lock.py -q -rs
```

| | 結果 | rc | 耗時 |
|---|---|---|---|
| **前**（repo `.venv`） | **`63 skipped`（0 passed）** | 0 | 0.26s |
| **後**（temp venv ＋ 活 PG） | **`62 passed, 1 skipped`** | 0 | **1.42s** |

**63 支（全部 224 的 28%）在 1.4 秒內從全 skip 變成全 pass。** 沒有任何效能理由讓它們
留在 skip 狀態——它們只是缺一次 `uv pip install '.[postgres,pgvector]'`。

唯一剩下的 1 支 skip 是**反向條件**：`pgvector 已安裝；測 present case 改由 _present test`
——absent／present 兩條路徑互斥成對，**任何單次執行都必然有一支 skip**。這類是結構上
不可歸零的健康 skip，盤點時不可算成洞。

> **中途一筆值得記的觀察**：只裝 `sqlalchemy` 而未裝 `asyncpg` 時，CRUD 那 4 支**不是 skip
> 而是 ERROR**（`ModuleNotFoundError: No module named 'asyncpg'` 於 fixture setup）。
> 也就是說這條路上「半套依賴」會 fail-loud 而非假綠——這是好設計，值得保留。

---

## 4.4 🔴 R76 PKG-C 落地：`pg-contract` job 射程擴大的**前後實測**

> 本節是 `.github/workflows/autoclaude-ci.yml` 那筆改動的量測憑證。任務書要求「先量再改」，
> 以下每一行都是 2026-08-05 於 Windows 11 Pro 原生 PowerShell 真跑的輸出。

**載具**（刻意不動 repo `.venv`，避免與同輪其他並行包互踩）：

```powershell
uv venv <scratchpad>\pkgc_venv --python 3.11
uv pip install --python <scratchpad>\pkgc_venv\Scripts\python.exe -e '.[dev,postgres,pgvector]'   # ← CI recipe 逐字
docker exec autoclaude_pg psql -U autoclaude -d postgres -c "CREATE DATABASE ac_r76c;"            # 不動開發用 DB
$env:AUTOCLAUDE_TEST_PG_DSN = 'postgresql+asyncpg://autoclaude:autoclaude@localhost:5432/ac_r76c'
$env:AUTOCLAUDE_DB_DSN      = $env:AUTOCLAUDE_TEST_PG_DSN
$env:AUTOCLAUDE_ALLOW_INSECURE_DB = '1'
& $py -m alembic upgrade head            # rc=0；alembic current → 0018_version_kind_discriminator (head)
& $py -m pytest tests/contract/ tests/integration/ tests/infra/ -q -rs --tb=short
```

| 射程 | | 結果 | rc | 耗時 |
|---|---|---|---|---|
| `contract/` ＋ `integration/`（第一版） | 前（repo `.venv`） | 772 passed, 184 skipped | 0 | 14.24s |
| | 後 | 920 passed, 36 skipped | 0 | 18.49s |
| **＋ `infra/`（最終落地版）** | **前**（repo `.venv`，無 PG 相依、無 DSN） | **1052 passed, 195 skipped** | 0 | 15.79s |
| | **後**（上述 recipe） | **1241 passed, 40 skipped** | 0 | **21.66s** |

⇒ 最終落地版 **155 支由 skip 轉 passed**，pytest 耗時 **+5.87s**。

**為何 passed 淨增 189 > 155**：`tests/infra/` 有 3 支**模組級** `importorskip("sqlalchemy")`，
解除後那 3 個模組內原本連 collect 都沒被算到的 34 支測試一併現身（195−40=155 支轉綠、
另 34 支是新收集到的）。這正是 §1.2 第 2 點與 ONBOARDING §7 記載的那個差額，在此拿到數字。

**為何把 `tests/infra/` 也納入**：另有 7 支同因的零覆蓋 skip 住在那裡——3 支模組級
`importorskip("sqlalchemy")`（`test_pg_phase1_adapters` ／`test_dual_state_repository_pg_fallback`
／`test_pg_memory_store_security`，全是 PG adapter 的安全與 fallback 契約）＋ 4 支
`test_storage_factory.py` 的 DSN 解析路徑。它們與本 job 的 extras 是**同一個開關**，而主
`test` job 只裝 `[dev]` 永遠救不到。邊際成本 +5.9s。

### 4.4.1 🔴 中途撞到的真缺陷：Mako 1.4.0 誤打包一個頂層 `tools/` 套件

第一次跑擴大射程時**不是綠的**，逐字：

```
ERROR collecting tests/contract/test_ac4_progress_check.py
E   ModuleNotFoundError: No module named 'tools.ac4_progress_check'
（同型另 4 筆：test_loc_budget_tiered / test_mutation_baseline_lock /
  test_mutation_multi_module_lock / tests/integration/test_yaml_import）
!!!!!!!!!!!!!!!!!!! Interrupted: 5 errors during collection !!!!!!!!!!!!!!!!!!!  rc=2
```

排除後再跑，`tests/integration/test_sdd_bridge/test_rollback_compat.py` 又以子行程形態復發：
`AISDLC_SDD_v0.01 的 state_loader 產出 FSM 狀態失敗（rc=1）… ModuleNotFoundError: No module
named 'tools.fsm_runtime'`。

**根因**（實查，非推測）：`mako-1.4.0.dist-info/RECORD` 逐字列出

```
tools/__init__.py,sha256=47DEQpj8HBSa-_TImW-5JCeuQeRkm5NMpJWZG3hSuFU,0
tools/toxnox.py,...
tools/warn_tox.py,...
```

而 `AutoClaude/tools/` **沒有** `__init__.py`（隱式 namespace package，實查 `Test-Path` → False）。
Python 的匯入規則是「掃到 namespace portion 會**繼續往後找**，遇到 regular package 立刻勝出」
⇒ site-packages 裡 mako 帶來的 `tools` 把 `AutoClaude/tools` 整個遮蔽，**與 sys.path 順序無關**
（實測 `tools.__file__` 指向 `…\pkgc_venv\Lib\site-packages\tools\__init__.py`）。
Mako 是 `alembic` 的相依 ⇒ **只有裝了 `[postgres]` extras 的環境會中招**；本 job 先前只跑一支
不 import `tools.*` 的檔案，所以這個地雷從未顯形。

單變因驗證：`uv pip install 'mako<1.4'` → mako 1.3.12 → `tools` 解析回
`D:\…\AutoClaude\tools`，5 筆 collection error 與那筆子行程失敗**全消**，
`alembic upgrade head` 仍 rc=0。上表「後」那一列即在 mako 1.3.12 下量得。

**處置**：本輪在 `autoclaude-ci.yml` 的 pg-contract 安裝步就地釘 `"mako<1.4"` 並附完整 WHY。
🔴 **這是止血不是根治**——根治位置是 `AutoClaude/pyproject.toml` 的 `postgres` extra
（任何本機執行 `uv pip install -e '.[dev,postgres]'` 的開發者都會踩到，且 R76 同輪該檔由別的
包持有）。已列交棒 **R77**。

### 4.4.2 剩下的 40 支為什麼**不**硬塞

| 支數 | 內容 | 為何不救 |
|---|---|---|
| 29 | `test_ac_matrix_scaffolding.py:212` 無條件 `pytest.mark.skip` | 任何環境變更都跑不到（§2.2 的技術債，非本包射程） |
| 3 | `test_sdk_executor_adapter.py` 的 `importorskip("claude_agent_sdk")` | 由主 `test` job 的 `sdk` extra 覆蓋（§4.5），本 job 不重複裝 |
| 2 | `test_pg_existing_schema_lock.py:318`（pgvector 已裝）／`test_pg_state_repository_contract.py:220`（sqlalchemy 已裝） | **absent／present 互斥成對**，任何單次執行必有一支 skip ＝結構上不可歸零的健康 skip |
| 2 | `test_pgvector_hnsw_recall.py:161,167` | 需 W3 G3 staging（1k seed ＋ BGE-M3 真實向量），不是裝 extras 就能到 |
| 3 | `test_pgvector_real_recall.py`（`pg_real`） | 已由 `pg-e2e-nightly` job 覆蓋（該 job 設 `SD07_REAL_PG_E2E_ENABLED=true` ＋ 跑 `seed_kb.py`），本 job 不重複 |
| 1 | `test_sdd_to_playbook_adapter.py:182` symlink 權限 | Windows 非管理者帳號限制；ubuntu runner 原生有權限，`test` job 已覆蓋 |

> 🔴 **訂正 §5.3 的一處預估**：該表把 `test_pgvector_hnsw_recall` 的 2 支列為「✅ 可救（另需
> `seed_kb.py`）」。本節實測證偽——它們的 reason 是 **W3 G3 staging 環境**而非 seed，裝好
> extras ＋ 活 PG ＋ `alembic upgrade head` 之後**仍然 skip**。已改列「不可能覆蓋」。

---

## 4.5 🔴 R76 PKG-C 落地：主 `test` job 加 `sdk` extra 的**全樹**前後實測

`tests/infra/adapters/test_sdk_executor_adapter.py` 有 3 處
`pytest.importorskip("claude_agent_sdk")`，而 `sdk` extra **在全部 11 支 workflow 裡從未被安裝
過一次**。這一筆的風險不在「跑不跑得起來」，而在「裝了會不會讓別的測試變色」，所以量的是
**整棵樹**而不是那一個檔：

```powershell
uv venv <scratchpad>\devonly_venv --python 3.11
uv pip install --python … -e '.[dev]'        # ← CI test job recipe 逐字
& $py -m pytest tests/ -q -rs --tb=short
# 然後：uv pip install --python … -e '.[dev,sdk]' 再跑同一條
```

| | 結果 | rc | 耗時 |
|---|---|---|---|
| **前** `.[dev]` | **3902 passed, 224 skipped** | 0 | 86.98s |
| **後** `.[dev,sdk]` | **3905 passed, 221 skipped** | 0 | 88.64s |

⇒ 3 支由 skip 轉 passed、**其餘 3902 支零變動**（無新紅、無新 skip）、耗時 **+1.66s**。
生產碼 `sdk_executor_adapter.py` 對該套件是 lazy import，裝了不改變預設 executor 後端（仍 pty）。

> ⚠️ **`3902` 不是 §1 的 `3900` 打錯**：本包在
> `tests/test_conftest_windows_native_skip_report.py` 併入 2 支反方向回歸鎖（§4.6），
> 樹本身淨增 2 支。**這使 ONBOARDING §7 表② 的 Windows 欄 `3900 / 224` 過期**——
> 收斂包須跑 `sync_onboarding_baselines.py --write --with-slow` 回填為 `3902 / 224`
> （PKG-C 無 `ONBOARDING.md` 授權，且該檔本輪由別的包持有）。

**perf 那 1 支**（`tests/perf/test_pgvector_recall_perf.py`，需 `PG_REAL_ENABLED` ＋ 活 PG）
本包**未救**：它落在 `perf-baseline-nightly` job，該 job 無 `services:`、未設該變數、只裝
`[dev]`（`autoclaude-ci.yml:544`）。要救得動那個 job 的 service container 與 env，屬另一件事
（排程軌、非 push 阻斷），本輪誠實留在「未覆蓋」。

---

## 4.6 🔴 R76 PKG-C 落地：反方向覆蓋損失從「結構性沉默」到「17 行」

補標 6 處後，同一批測試在 **Windows 上**的終端輸出（逐字節錄）：

```
============== POSIX/MAC-NATIVE-ONLY SKIPS (本次跑在 Windows 上失去的覆蓋) ==============
17 個非 Windows 專屬測試本次「因為跑在 Windows 上而沒跑」（R74／PKG-4 E：反方向的覆蓋損失此前無任何標籤／摘要／計數）：
  - tests/test_evaluator_kill_tree.py::test_timeout_kills_grandchild_spawned_via_shell_compound_command
  - tests/test_evaluator_kill_tree.py::test_evaluator_child_runs_in_its_own_process_group
  - tests/test_evaluator_kill_tree.py::test_conditional_evaluator_child_runs_in_its_own_process_group
  - tests/test_perception.py::TestCloseKillsPosixGrandchild::test_close_kills_grandchild_spawned_via_shell_background_job
  - tests/test_perception_platform_honesty.py::test_macos_non_root_register_reports_unavailable_for_real
  - tests/tools/test_run_local_nightly_sh_static.py::…（另 12 支，含 parametrize 展開）
91 passed, 17 skipped, 1 warning in 3.91s   （rc=0）
```

**6 個靜態站點 → 17 支 runtime skip**，又一次坐實 §1.2 說的「站點數永遠回答不了掌舵者的
問題」：`test_run_local_nightly_sh_static.py` 的 1 個 `_POSIX_ONLY` 別名站點展開成 12 支。

> ⚠️ **一個誠實的邊界（同輪另一個 venv 實測到 16 而非 17）**：
> `test_perception_platform_honesty.py:84` 疊了三個 `skipif`，pytest 只印**第一個成立**的
> reason。在**沒有裝 `keyboard`** 的環境裡先命中的是「keyboard 套件未安裝」，`[MAC-NATIVE-ONLY]`
> 那句就不會出現在摘要裡（本輪 `devonly_venv` 實測即為此，該處顯示 16 行）。
> 靜態棘輪不受影響（它讀原始碼、看得到標籤），但**runtime 摘要對「疊多層 skipif」的站點
> 天生只看得到最上面那一層**——這是本機制既有的邊界，不是本輪引入的，記在此以免下一個人
> 拿 16 與 17 的差異當成回歸。
>
> 🔴 **R76 複審 SD-03 訂正兩點**：① 上面那句「不是本輪引入的」在 **macOS CI** 上不成立
> ——R76 之前雲端環境有 `keyboard`（它是核心相依），命中的是帶 `[MAC-NATIVE-ONLY]`
> 標籤的 darwin 層；是本輪把 `keyboard` 移進 `[hotkey]` extra 之後，才變成命中沒有標籤
> 的那一層。② 已就地消除這個邊界：`keyboard 套件未安裝` 那一層的 `reason` 也掛上
> `[MAC-NATIVE-ONLY]` 標籤，兩層都帶標籤 ⇒ 不論命中哪一層，反方向摘要都看得到它。

### 4.6.1 bug-injection 紅綠（三筆，逐字）

閘門載具＝`windows_skip_tags.report_untagged_windows_skip_decorators()`（`tools/run_root_unittests.py` 消費其 rc）。

| # | 注入 | 結果 |
|---|---|---|
| 綠底 | 無 | `PROBLEMS=0`／rc=0 |
| A | 拿掉 `test_perception.py` 的 `[POSIX-NATIVE-ONLY]` | rc=1、`AutoClaude/tests：未標籤的「Windows 上會 skip」站點實測 1、基線 0——新增了未標籤站點` |
| B | 基線 0→3、天花板不動 | rc=1、`AutoClaude/tests：基線 3 高於 shrink-only 天花板 0——反方向標籤欠債只准變少` |
| C | 拿掉標籤 **＋** 照舊判準把基線改成實測值 1（**舊制下這樣就全綠**） | rc=1、天花板那一筆照樣說話 ⇒ 舊出口確實已封 |
| 還原 | 以 Edit 工具逐筆還原（未用 `git checkout --`） | `PROBLEMS=0`／rc=0；`TestSkipDirectionAndTagSymmetry` 13 tests OK |

conftest 反方向區塊的兩支新鎖亦各驗一次：停用區塊（`if False and posix_ids`）→
`nomatch: '*POSIX/MAC-NATIVE-ONLY SKIPS*'` 1 failed；把標籤篩選改成「全收」→ 負向那支
`assert 'POSIX/MAC-NATIVE-ONLY' not in …` 1 failed；還原後 **5 passed**。

---

## 4.7 🔴 R76 複審後補測：整棵樹接上本機 PG 之後，**4 支從未被執行過的紅**

> 本節是掌舵者當場糾正一個共同前提之後補的。前提是「本機沒有 PostgreSQL，那批只能在雲端
> 驗」——**該前提為假**：本機一直有一個長駐健康的 `pgvector/pgvector:pg18` 容器（§4.3 已
> 記載），缺的只是**環境變數與 extras**。本節每一行都是 2026-08-05 Windows 11 原生
> PowerShell 真跑。

### 4.7.1 配方（可重跑）與兩個基線

```powershell
$env:AUTOCLAUDE_DB_DSN='postgresql+asyncpg://autoclaude:autoclaude@localhost:5432/<DB>'
$env:AUTOCLAUDE_TEST_PG_DSN=$env:AUTOCLAUDE_DB_DSN
$env:AUTOCLAUDE_ALLOW_INSECURE_DB='1'; $env:SD07_REAL_PG_E2E_ENABLED='true'
# 一次性：uv pip install -e '.[postgres,pgvector]'（缺 sqlalchemy 時症狀是 error 而非 skip）
python -m pytest tests/ -q -p no:randomly
```

| 環境 | 結果 | rc |
|---|---|---|
| 預設（無 DSN、無 extras）＝**出廠基線** | 🔴 **本檔刻意不複寫這個數字**，唯一站點是 `ONBOARDING.md` §7 表②，現查配方見下 | 0 |
| 接上**長壽開發 DB**（`autoclaude`） | **`4 failed, 4106 passed, 67 skipped`**（103.52s） | **1** |
| 接上**乾淨 DB**（新建＋`alembic upgrade head`＋同一次 `seed_kb`） | **`4108 passed, 69 skipped`**（94.97s） | **0** |

> 🔴 **第一列為何不寫數字（R76 收尾訂正，依本輪 SA 判準 B）**：原文在此寫死了一組「預設
> 基線」常數，而**出廠基線的唯一站點是 `ONBOARDING.md` §7 表②**。同一個量有兩個家，第二個
> 家必然先過期——實測：本檔原本那組數字與 §7 表② 的現值已經對不上，而**沒有任何東西會為
> 它說話**（`tools/check_pytest_baseline_sites.py` 守的正是「基線數字只准住一個家」，只是它的
> `_SCAN_FILES` 不含本檔 ⇒ 本檔落在該鎖的射程外）。故改為只留現查配方：
>
> ```powershell
> python tools/sync_onboarding_baselines.py --check-snapshot
> #   → 印出本平台欄的 [autoclaude-pytest-snapshot:] {'passed': …, 'skipped': …}
> ```
>
> ⚠️ **兩個名詞不要混**：§7 表② 的「出廠基線」定義是**只裝 `.[dev,notifications]` 的乾淨
> venv**（provenance 記 `pgextras=absent`）；本表下兩列量的是**接上 PG 之後**的同一棵樹。
> 兩者數字不同是預期行為，不是基線壞掉——而下兩列是**一次性補測的紀錄**（帶 rc 與耗時），
> 不是基線宣稱，故照原樣保留。

⇒ **157 支在本機跑得到**。而那 4 支紅**不是本輪弄壞的，是從未被執行過所以從未被看見的**。
兩個原因完全不同，逐一取證於下。

### 4.7.2 三支 `backfill_legacy_fk` — **DB 沒有真的被 migrate 過**（環境，不是實作）

```
psycopg2.errors.UndefinedFunction: function backfill_legacy_fk(unknown, integer) does not exist
```

逐步取證：

| # | 動作 | 輸出 |
|---|---|---|
| 1 | `select version_num from alembic_version;`（開發 DB） | `0018_version_kind_discriminator`（＝head） |
| 2 | `select proname from pg_proc where proname like 'backfill%';` | **0 rows** |
| 3 | 讀 `alembic/versions/0010_link_legacy_to_tiers.py:222-231` | `upgrade()` **無條件** `op.execute(_UPGRADE_SQL_STEP2)`，該 SQL 就是 `CREATE OR REPLACE FUNCTION backfill_legacy_fk` |
| 4 | 同一容器內 `CREATE DATABASE ac_r76fix` ＋ `alembic upgrade head` | rc=0；`proname = backfill_legacy_fk`（1 row）；`version_num` 同為 0018 |
| 5 | 對乾淨 DB 重跑該檔 | **`16 passed`**，rc=0 |

⇒ 結論：**測試是對的，DB 是壞的**。`alembic_version` 停在 head **不代表**整條鏈真的跑過
（`alembic stamp` 或由 schema dump 建起的 DB 顯示的 head 一模一樣）。這三支紅是**正確訊號**。

> **環境清理聲明**：上表第 4 步建的 `ac_r76fix` 已於取證完成後 `DROP DATABASE`，容器內
> 只留原有的 `autoclaude`／`ac_r76qa`；開發 DB 的 `alembic_version` 與 `knowledge_entries`
> 列數（0）與我進場前逐字相同，**schema 與資料皆零改動**。要重跑上表只需三行：
> `CREATE DATABASE <名>` → `alembic upgrade head` → `pytest tests/contract/test_alembic_0010_fk_three_step.py`。

🔴 **處置刻意不是「讓它綠」**：斷言一字未改（任務書明令，且改了就等於把「這個 DB 沒被
migrate 過」這個事實藏起來）。只把失敗訊息改成指得到唯一已知成因
（`tests/contract/test_alembic_0010_fk_three_step.py::test_backfill_function_exists`）。
開發 DB 的 schema 本輪**零改動**（任務書明令）。

### 4.7.3 一支 `recall@10 = 0.000` — **ground truth 與語料必須同一次 seed**

這一支的根因比表面難看，而且是**結構性**的：

| 事實 | 取證 |
|---|---|
| `knowledge_entries` 有 0 列 | `select count(*) …` → 0 |
| query fixture 是**決定性**的 | 重跑 `seed_kb.py` 產出的 queries 與 repo 內那份 `==` → `True` |
| ground truth fixture **不是** | 同一次重跑產出的 gt 與 repo 內那份 `==` → `False`；**兩者的列 UUID 交集＝0／100** |
| 為什麼 | ground truth 記的是 `knowledge_entries` 的**列 UUID**，而 `seed_kb.py --mock-pg-seed` 每次插入都重新隨機產生 UUID |
| 檢索本身有沒有壞 | **沒有**。用同一次 seed 產出的 gt 量測 → **`recall@10 = 0.999`** |

⇒ 也就是說：committed 的 `pgvector_real_ground_truth.json` 只是**某一次歷史 seed 的殘骸**，
它與任何其他 DB 的交集**結構上恆為 0**。CI 與 nightly 之所以綠，是因為它們都在跑本檔**之前**
先跑一次 seed 並就地覆寫這兩份 fixture（`autoclaude-ci.yml:371-373`、
`autoclaude-pg-e2e-on-label.yml:82-84`、`run_local_nightly.ps1:1231` 逐字皆然）。
本檔 docstring 第 9~14 行本來就把「預先 seed ≥ 100 列 KB」列為**啟用條件之一**，
只是四條裡**只有三條寫成了 code**。

**處置**：把第 4 條也寫成 code（`_require_seeded_corpus()`），不碰 `>= 0.95` 這個期望值。
判準刻意分得開兩件事，並以注入實測證明：

| 情境 | 期望 | 實測 |
|---|---|---|
| DB 內 0 列語料 | skip，理由指名缺件 | `SKIPPED … [PG-CORPUS-MISSING] 本 DB 只有 0 列…先跑 python tools/seed_kb.py --mock-pg-seed`，rc=0 |
| DB 有 100 列，但 gt 來自別次 seed | skip，理由指名「不同次 seed」 | `SKIPPED … [PG-CORPUS-STALE] …交集為 0…`，rc=0 |
| 語料與 gt 同一次 seed | **真跑且綠** | `3 passed, 1 skipped`，rc=0 |
| 語料與 gt 同一次 seed，但**檢索被注入成永遠回空** | **必須紅，不得被吃成 skip** | `AssertionError: recall@10 = 0.000 < 0.95`，**rc=1** ✅ |

最後一列是這筆修法能不能收的關鍵：新前置檢查**沒有**掩蓋真回歸。注入載具＝
scratchpad 的 `break_search.py`（`-p break_search` 覆寫 `PgVectorSearchAdapter.search`），
repo 內零改動；repo fixture 於實驗前備份、實驗後還原並以 `Get-FileHash` 逐一比對相同。

> **順帶揪出的一筆假綠**：`TestP95Latency` 在空 DB 上是**綠的**——對 0 列做 100 次 HNSW
> 查詢當然快。也就是說它量的不是「檢索有多快」而是「查空表有多快」。同一台機器 seed 100 列
> 後實測 `p95 = 51.32ms`（門檻 50ms）。本輪一併給它上同一道前置檢查：**把假綠換成誠實的
> skip**，方向與「把紅換成綠」相反。Windows + Docker Desktop 的門檻本來就備了旁路
> （`AUTOCLAUDE_TEST_P95_THRESHOLD_MS`，該檔第 41 行），設 80 後 3 passed。

### 4.7.4 🔴 版本差誠實揭露：本機 pg18 ≠ 閘門 pg17

| 面 | 版本 | 出處 |
|---|---|---|
| 本機開發容器（本節全部數字） | **PostgreSQL 18.4** | `show server_version;` → `18.4 (Debian 18.4-1.pgdg12+1)`；`docker ps` → `pgvector/pgvector:pg18` |
| 雲端 `pg-contract` / `pg-e2e-nightly` | **pg17** | `.github/workflows/autoclaude-ci.yml:219,323` → `image: pgvector/pgvector:pg17` |
| repo 自備的 CI 對等品 | **pg17** | `AutoClaude/docker-compose.ci.yml` |

**本節任何一個綠都不得被讀成「pg17 閘門會綠」。** 這一條在 R76 對抗複驗中已被單獨立案過
（該筆最終判為非 blocking，理由是「那 63 支多數是離線 ORM 斷言、且 ubuntu 主 `test` job
每次 push 就跑過整棵樹」，**但揭露義務仍在**）。同一位複驗者當回合以
`pgvector/pgvector:pg17` 起容器重跑閘門射程，得 `1241 passed, 40 skipped, rc=0, 21.69s`
——與 pg18 那組逐位相同。⇒ 目前**沒有**已知的 pg17／pg18 行為差，但那是量測結果，不是推論，
新增任何 PG 相關斷言時仍須各量一次。

### 4.7.5 結構性教訓：「未啟用」與「缺件」是兩件事

本輪暴露的通則：skip 理由寫「需要 X」**不代表 X 缺席**，多半只是環境變數沒設或 extras 沒裝。
`Skipped_Test_Inventory` 的 (b)(c)(d) 三類先前混在一起，讀者無從得知「這是我兩行就能開的，
還是我真的少一台機器」。R76 起在**輸出面**把兩者分開（不只在本文件分開）：

| 類 | 輸出面新增字樣 | 落地站點 |
|---|---|---|
| **未啟用**（旗標／DSN 沒設，設了就能跑） | `【未啟用，非缺件】<設什麼即可啟用>` | `test_pgvector_real_recall.py::_require_real_pg` |
| **缺件**（資料／語料真的不在） | `[PG-CORPUS-MISSING]`／`[PG-CORPUS-STALE]` ＋ 可直接複製的指令 | 同檔 `_require_seeded_corpus` |

誠實劃界：本輪只把這個區別落到**這一支檔**的 skip 理由上（它是踩到的那一支）。全樹 224 支
的 reason 字串**尚未**逐支套用同一形態，交棒 R77（見 `DEF-101-859`）。

---

## 5. 不可能在本平台跑到的清單 ＋ 逐筆雲端對照

### 5.1 Windows 上**結構上**跑不到的（誠實劃界）

| 類別 | 支數 | 為何在 Windows 不可能 |
|---|---|---|
| POSIX process group／`os.killpg`（AutoClaude 4、根層 8） | 12 | Windows 無 process group 語意 |
| POSIX shell 載具（`.sh` 實跑；AutoClaude 12、根層 6、v0.30 2、scripts 1） | 21 | 判準含 `sys.platform == "win32"` 短路 |
| macOS 專屬（根層 24 `[MAC-NATIVE-ONLY]`、AutoClaude 1） | 25 | 依賴 `plutil`／BSD `date -v`／launchd |
| `zsh` 專屬（根層） | 2 | Windows 無 zsh |
| 舊版直譯器（`python3.9` 等，根層） | 2 | Windows 無 `/usr/bin/python3` |
| symlink 建立權限（AutoClaude 1、根層 1） | 2 | 非管理者帳號無 `SeCreateSymbolicLinkPrivilege` |

### 5.2 逐筆雲端 job 對照（`.github/workflows/` 實查）

| 這一類在 Windows 跑不到 | 哪個 job 補上 | 觸發 | 實查憑證 |
|---|---|---|---|
| 根層 unittest 的 24 + 8 + 6 = 38 支平台 skip | `macos-compat-ci.yml` → `macos-smoke` 跑 `python3 tools/run_root_unittests.py` | **push／PR 阻斷** | `macos-compat-ci.yml:472,475,509` |
| AutoClaude 16 支 POSIX-only | `autoclaude-ci.yml` → `test` job（ubuntu-latest）跑 `pytest tests/ -q -rs` | **push／PR 阻斷** | `autoclaude-ci.yml:71,73,103` |
| AutoClaude 1 支 macOS-only（`test_perception_platform_honesty.py` 的 `test_macos_non_root_register_reports_unavailable_for_real`） | ⚠️ **只有** `macos-nightly-full`（`local_ci_gate.sh` 全套）——`macos-smoke` 只跑 `pytest tests/test_perception.py`，跑不到這一支。🔴 **R76 複審 SD-03 訂正**：本列在寫下的當回合是**假的**——同輪把 `keyboard` 由核心 dependencies 移進 `[hotkey]` extra，而 `macos-nightly-full` 的安裝當時是 `pip install -e ".[dev,lint]"`（不含 hotkey）⇒ 該支在雲端**兩條 macOS 軌上都會 skip**，覆蓋歸零（§5.3 的 grep 區塊當時已寫 `NONE`，同一份文件內部自相矛盾，而磁碟站在 §5.3 那邊）。修法＝`macos-compat-ci.yml` 的 nightly-full 安裝改為 `".[dev,lint,hotkey]"`，本列於修法落地後恢復成立。**`macos-smoke` 仍不裝 hotkey**（走 `tools/bootstrap_core.py` 的 extras，該檔明寫刻意不含），故 push 阻斷層對這一支仍是零覆蓋 | schedule、**非阻斷** | `macos-compat-ci.yml` nightly-full 安裝步驟（本輪改為含 `hotkey`）；`gh run view 30807193487` → `macOS nightly full suite（深度回歸，非阻斷）= success` |
| v0.30 的 2 支 POSIX post-commit hook ＋ scripts/tests 的 1 支 chmod | `aisdlc-sdd-ci.yml` → `offline-gate`（ubuntu）跑 `bash scripts/ci-gate.sh` | **push／PR 阻斷** | `aisdlc-sdd-ci.yml:84,86,99` |
| Windows-only 的 13+8+1+1 個站點（在 mac 上會 skip） | `windows-compat-ci.yml` → `windows-smoke` 跑 `python tools/run_root_unittests.py` | **push／PR 阻斷** | `windows-compat-ci.yml:612,615,729` |

**⇒ (a) 平台類的雙向覆蓋是健康的**：兩邊都有 push 阻斷軌，唯一的單點是那 1 支 macOS-only
落在非阻斷的排程軌上。這一格不需要新機制。

### 5.3 🔴 兩邊都跑不到的（＝零覆蓋，比 skip 更糟）

逐 workflow grep（`Select-String '.github\workflows\*.yml'`）結果：

```
test_pg_existing_schema_lock  -> NONE
test_alembic_0007 / 0008 / 0010 / 0011 / 0012 -> NONE
test_three_tier_schema        -> NONE
test_advisory_lock_concurrent -> NONE
test_pgvector_hnsw_recall     -> NONE
test_ac_matrix_scaffolding    -> NONE
test_perception_platform_honesty -> NONE   ← 檔名不被任何 workflow 逐字點名，但它會隨
                                             `macos-nightly-full` 的 local_ci_gate.sh 全套跑到
                                             （§5.2 那一列講的是這條通道，非本 grep 的射程）
test_pg_state_repository_contract -> autoclaude-ci.yml:255      （pg-contract，硬閘）
test_pgvector_real_recall     -> autoclaude-ci.yml:289,328；autoclaude-pg-e2e-on-label.yml:89
```

而**唯二**安裝 PG 依賴的 job 各自只跑一支檔案：
`pg-contract` 只跑 `tests/contract/test_pg_state_repository_contract.py`（`autoclaude-ci.yml:255`）；
`pg-e2e-nightly` 只跑 `tests/integration/test_pgvector_real_recall.py`（`autoclaude-ci.yml:328`）。
主 `test` job 是 `pip install -e ".[dev]"`（`autoclaude-ci.yml:96`）＋**無 `services:`**，
而 `dev` extras 內**沒有** sqlalchemy（`pyproject.toml:28-51`；sqlalchemy 在 `postgres` extras，行 79）。
`sdk` extras（行 95-96）與 `pgvector` extras（行 88-90）**在任何 workflow 都沒被安裝過**。
地端 nightly 亦同：`AutoClaude/tools/run_local_nightly.ps1:1211,1224` 的 pg-e2e stage 也只跑那兩支檔，
且該檔第 118 行自陳「`.venv` 未裝 `[postgres,pgvector]` 選配 → pg-e2e 假紅」。

**零覆蓋清單（192 支，86%）** — 「本輪處置」欄為 R76 PKG-C 落地後實測結果：

| 支數 | 內容 | 掃描階段預估 | 🔴 本輪處置（實測） |
|---|---|---|---|
| 63 | `test_pg_existing_schema_lock.py` | ✅ 已實測（§4.3）1.4 秒全綠 | **已補**（`pg-contract` 擴射程） |
| 71 | 六支 `test_alembic_00XX` ＋ `test_three_tier_schema` | ✅ 需 DSN＋psycopg2＋`alembic upgrade head` | **已補**（同上） |
| 5 | `test_advisory_lock_concurrent` | ✅ 同上 | **已補**（同上） |
| 2 | `test_pgvector_hnsw_recall` | ✅（原估「另需 `seed_kb.py`」） | ❌ **預估證偽**：reason 是 W3 G3 staging（1k seed ＋ BGE-M3 真實向量），裝好 extras ＋ 活 PG ＋ migration 後**仍 skip**。改列不可覆蓋（§4.4.2） |
| 7 | sqlalchemy 整檔 importorskip(3) ＋ `test_storage_factory`(4) | ✅ 只缺 extras | **已補**——但要注意它們住 `tests/infra/`，故 `pg-contract` 射程必須含第三個目錄（§4.4） |
| 3 | `claude_agent_sdk` importorskip | ✅ 只缺 `pip install '.[sdk]'` | **已補**（主 `test` job 加 sdk extra，全樹零副作用，§4.5） |
| 11 | 需 `claude` CLI binary 且非巢狀 session | ⚠️ 可誠實劃界為永久不覆蓋，但要明寫 | 未動——**明示標籤仍缺**，交棒 R77 |
| 1 | pgvector recall perf（perf machine） | ⚠️ `perf-baseline-nightly` 只裝 `[dev]`、無 PG | 未動——要救得動該 job 的 service container 與 env，屬另一件事（排程軌、非 push 阻斷） |
| 29 | `test_ac_matrix_scaffolding` | ❌ 無條件 skip | 未動（純技術債，非本包射程；見 F4／§2.2） |

---

## 6. 一句話回答掌舵者（🔴 R76 PKG-C 修完後重寫）

**224 支 skip 裡，158 支（71%）是「該補的洞」——它們在 Windows、macOS、以及全部 11 支
workflow 都沒有任何通道跑到；本輪兩行 CI recipe 修改把這 158 支全數補回，實測 rc=0，
push 閘門總耗時只增加約 7.5 秒。剩下的 66 支中，34 支是真正健康的條件式跳過（另一個平台的
push 阻斷軌真的在跑它們），11 支需付費的 `claude` CLI 且在巢狀 session 掛住不回（🔴 **R79 收輪
改判：不是「永久不覆蓋」**——非巢狀環境的每日 nightly 真的在跑它們，見下表該列），29 支是無條件
`pytest.mark.skip` 的純技術債，另有 3 支
（2 支需 staging 環境、1 支 perf job 缺 service container）本輪誠實補不了。**

> 🔴 **R76 複審後補充（§4.7）——上面那段回答的是「雲端有沒有通道」，不是「我現在跑不跑得到」。**
> 這兩個問題的答案不一樣，而本檔初版只答了前者，於是讀起來像是「這批只能等 CI」。
> 實測：把 DSN ＋ extras 補齊後，**157 支在這台 Windows 開發機上當場跑得到**
> （出廠基線 → `4106 passed/67 skipped`，兩個基線與現查配方見 §4.7.1）。也就是說上表「本輪已補 158」
> 那一格講的是**雲端**補回來的，而其中絕大多數**本機一直都跑得到，只是沒有人告訴你怎麼開**。
> 這正是 §4.7.5 那條教訓的實體：「需要 PG」不等於「沒有 PG」。
>
> 同一次補測揭出 **4 支從未被執行過的紅**（3 支＝開發 DB 沒真的 migrate 過、1 支＝ground
> truth 與語料必須同一次 seed），逐筆取證與處置見 §4.7.2／§4.7.3；乾淨環境重跑
> **`4108 passed, 69 skipped`／rc=0**。**本機容器是 pg18、閘門是 pg17，版本差揭露見 §4.7.4。**

拆解（每一格都有 §4.4／§4.5 的實測憑證，非估算；合計 158＋66＝224）：

| 分類 | 支數 | 說明 |
|---|---|---|
| **本輪已補** | **158** | **155** ← `pg-contract` job 射程由 1 支檔擴為 `tests/contract/ tests/integration/ tests/infra/`（實測 skip 195→40、passed 1052→1241、rc=0、+5.87s）；**3** ← 主 `test` job 加 `sdk` extra（**全樹**實測 3902/224 → 3905/221、rc=0、+1.66s，其餘 3902 支零變動） |
| **健康：另一平台的阻斷軌在跑** | **17** | 16 支 `[POSIX-NATIVE-ONLY]`（ubuntu `test` job）＋ 1 支 symlink 權限（ubuntu 原生有） |
| **健康：已有專屬 job 覆蓋** | **3** | `pg_real` → `pg-e2e-nightly`（設 `SD07_REAL_PG_E2E_ENABLED=true` ＋ `seed_kb.py`） |
| **健康：結構上不可歸零** | **2** | absent／present 互斥成對，任何單次執行必有一支 skip |
| **健康：darwin 專屬** | **1** | `[MAC-NATIVE-ONLY]`，`macos-nightly-full` 覆蓋（⚠️ 非阻斷排程軌，§5.2 已單獨列出）。🔴 **R76 複審 SD-03**：這句話在本輪寫下時因 `keyboard` 移出核心相依而**曾經為假**（§5.3 grep 同時寫著 `NONE`）；已由 nightly-full 安裝補 `hotkey` extra 修復。push 阻斷層仍零覆蓋 |
| **健康：非巢狀 nightly 在跑**（🔴 R79 收輪由「可辯護的永久不覆蓋」改判） | **11** | 需 `claude` CLI binary 且**非巢狀** session。🔴 **改判的兩半**：①「永久不覆蓋」**為假**——非巢狀環境的每日 nightly 實測會真的跑（`AutoClaude/logs/nightly_2026-08-06_223002.log` 逐字 `4 failed, 4080 passed, 120 skipped in 107.28s`，其 `-rs` 清單對這兩支檔**零命中**＝那一跑裡它們沒有被 skip）；②「`CLAUDECODE=1` 必死結」**為假**——剝除該變數的對照組行為完全相同，掛住的是「巢狀 session × `wexpect.spawn()`」這一組（`DEF-101-913`）。**判準本身維持不變**（在巢狀環境內 skip 仍是對的，拿掉那半個條件會讓這 11 支當場掛死整棵樹，已注入實證），改的是 reason 與本表的分類 |
| **仍補不了（誠實劃界）** | **3** | 2 支 `test_pgvector_hnsw_recall`（需 W3 G3 staging：1k seed ＋ BGE-M3 真實向量）／1 支 `test_pgvector_recall_perf`（`perf-baseline-nightly` 無 `services:`、未設 `PG_REAL_ENABLED`、只裝 `[dev]`） |
| **純技術債** | **29** | `test_ac_matrix_scaffolding`——23/29 的 target 檔已存在（§2.2），reason 與 docstring 互相矛盾 |

> 🔴 **與本檔初稿（掃描階段）的三處差異，逐筆交代**——初稿是估算、本節是實測：
> ①初稿估「該補 152」，實測 **158**（初稿漏算 `tests/infra/` 那 7 支同因 skip，且低估了
> 模組級 `importorskip` 解除後多收集到的 34 支）。②初稿把 `test_pgvector_hnsw_recall` 那
> 2 支列為「✅ 可救」，實測證偽——它們卡在 W3 G3 staging 而非 seed，已改列不可覆蓋
> （§4.4.2 訂正框）。③初稿沒有預見 **Mako 1.4.0 遮蔽 `AutoClaude/tools`** 這顆地雷
> （§4.4.1）——舊射程「只跑一支檔」恰好繞過了它，也就是說**擴大射程這個動作本身，是這個
> 從未顯形的環境缺陷被發現的唯一原因**。

**已落地的改動**（`.github/workflows/autoclaude-ci.yml`，兩個 job 各一處）：
- `test` job：`pip install -e ".[dev]"` → `".[dev,sdk]"`
- `pg-contract` job：安裝步 `".[dev,postgres]"` → `".[dev,postgres,pgvector]" "mako<1.4"`；
  最後一步 `pytest tests/contract/test_pg_state_repository_contract.py -v`
  → `pytest tests/contract/ tests/integration/ tests/infra/ -q -rs --tb=short`

**本輪未動、但應接著做的**（交棒 R77，理由＝檔案不在 PKG-C 授權內）：
① `AutoClaude/pyproject.toml` 的 `postgres` extra 加 mako 約束（根治 §4.4.1，讓本機
`uv pip install -e '.[dev,postgres]'` 的開發者不再踩到）；② 那 11 支 `claude` CLI skip 補一個
明示「永久不覆蓋」的標籤並登記，別再混在「可救」那堆裡；③ `test_ac_matrix_scaffolding`
那 29 支的 reason ↔ docstring 矛盾（§2.2）。

---

## 7. 各類「怎麼跑到它」— Windows 與 macOS 雙欄

| 類別 | Windows 11 | macOS | 備註 |
|---|---|---|---|
| (d) sqlalchemy／psycopg2 gated（69） | `uv pip install -e '.[dev,notifications,postgres,pgvector]'`（`AutoClaude/` 下）；⚠️ 會讓 `sync_onboarding_baselines.py --write --with-slow` **rc=2 拒跑**，需 `--allow-pg-extras` | 同左，extras 一律加單引號（zsh filename generation） | 只裝 sqlalchemy 不裝 asyncpg 會 **ERROR 而非 skip**（§4.3） |
| (d) `claude_agent_sdk`（3） | `uv pip install -e '.[sdk]'` | 同左 | 最便宜的一筆 |
| (c) alembic／three-tier 契約（71） | ① `docker compose -f docker-compose.ci.yml up -d`（**本機若已有長駐容器就跳過**——實查 `autoclaude_pg` 已 healthy 兩天，⚠️ 那支是 **pg18**，`docker-compose.ci.yml` 與雲端是 **pg17**，見 §4.7.4） ② `$env:AUTOCLAUDE_TEST_PG_DSN='postgresql+asyncpg://autoclaude:autoclaude@localhost:5432/<DB>'` ③ 裝 `[postgres]` ④ `alembic upgrade head` | 同左，env 寫 `export AUTOCLAUDE_TEST_PG_DSN=...` | **四步缺一即仍 skip**（§4.2 已實測）。🔴 ④ **不可用 `alembic stamp` 代替**：長壽 DB 停在 head 卻沒真跑過 0010 ⇒ 3 支 `backfill_legacy_fk` 紅（§4.7.2） |
| (c) `pg_real`（3） | 上述四步 ＋ `$env:SD07_REAL_PG_E2E_ENABLED='true'` ＋ `python tools/seed_kb.py --mock-pg-seed --pg-dsn <dsn>` | 同左 | recipe 抄 `autoclaude-ci.yml:305-330`。🔴 **seed 那一步不是可選的、也不能是上次跑的**：ground truth 記的是列 UUID，`--mock-pg-seed` 每次重新隨機產生 ⇒ **語料與 fixture 必須同一次 seed**，否則 R76 起會 `[PG-CORPUS-STALE]` skip（修前是 `recall@10 = 0.000` 誤導性紅）。詳 §4.7.3 |
| (c) TLC 五軌（SDD 4~6 支） | `$env:SDD_RUN_TLC='1'`；需 Java（本機 Android Studio jbr 即可）＋ `tla2tools.jar`（v0.30 已內附） | `export SDD_RUN_TLC=1`；`brew install openjdk` 或 `run_tlc.sh` 自動下載 jar | 已實測（§4.1），代價 332s |
| (c) `chaos` marker（34 deselected） | `pytest tools/fsm_runtime/tests/ -m chaos` | 同左 | 是 **deselect 不是 skip**，不計入本盤點 |
| (c) `perf` marker | 預設**就會跑**（本輪 224 內無 perf skip） | 同左 | 唯一 perf skip 是 pgvector 那支 |
| (c) pgvector perf（1） | `$env:PG_REAL_ENABLED='1'` ＋ 活 PG（讀取點＝`tests/perf/test_pgvector_recall_perf.py:26`，reason 給的變數名實查為真、非誤植） | `export PG_REAL_ENABLED=1` | ⚠️ `perf-baseline-nightly` job（`autoclaude-ci.yml:544`）**無 `services:`、未設本變數、只裝 `[dev]`** ⇒ 這支在名為 Perf Baseline 的 job 裡照樣 skip |
| (a) POSIX 專屬（21+12） | 🔴 **結構上不可能** | 原生就跑 | 靠 ubuntu／macos job（§5.2） |
| (a) macOS 專屬（25） | 🔴 **結構上不可能** | 原生就跑 | 靠 `macos-smoke`（38 支）／`macos-nightly-full`（1 支） |
| (a) `zsh`（2） | 🔴 Windows 無 zsh | 預設 shell 即 zsh | — |
| (a) 舊直譯器（2） | 🔴 無 `/usr/bin/python3` | macOS 必有 3.9.x | — |
| (b) symlink 權限（2） | 以**管理者**開 shell，或開啟 Windows 開發人員模式 | 原生有權限 | 唯一「Windows 上可自救」的平台類 |
| (b) `claude` CLI（11） | 需 `claude` 在 PATH **且** 非巢狀 session（`CLAUDECODE` 未設）。**每日 nightly 就是這個環境**，不必手動做什麼 | 同左 | 在 Claude Code session **內**確實跑不到（R79 實測：`wexpect` pty spawn 180/180/45s 未回返、`claude.exe` 從未被啟動；剝除 `CLAUDECODE` 的對照組相同 ⇒ 成因是巢狀執行環境，該變數只是標記。`DEF-101-913`）。🔴 但 session **外**跑得到——「永遠跑不到」只對巢狀環境成立，不是這 11 支的全稱結論 |
| (e) AC matrix scaffolding（29） | 🔴 **無任何方法** | 🔴 同左 | 見 F4 |

---

## 8. 機制現況（誰在看這些數字）

| 量 | 有機械物嗎 | 射程 |
|---|---|---|
| 靜態站點分類普查 | ✅ `skip_tag_policy._SITE_CLASS_CENSUS`（**相等**棘輪，任一格變動即紅） | 只有 3 棵樹、只有 **reason 為字面字串**的站點 |
| 逐樹檔數下限 | ✅ `tree_floor_problems()`（雙向：縮面紅／下限過期也紅） | 同上 3 棵樹 |
| 反方向標籤欠債 | ✅ `_POSIX_TAG_RATCHET`（🔴 R76 由 1/**6**/1 下修為 1/**0**/1——`AutoClaude/tests` 的欠債已清空；另加 shrink-only 天花板 `_POSIX_TAG_RATCHET_CEILING` 封住「把基線改大」這條舊出口） | 同上 3 棵樹 |
| 反方向摘要（conftest 區塊）本身 | 🔴 R76 前**零回歸鎖**（整段刪掉全綠）／R76 後 ✅ 2 支（正向＋負向），併入既有 `AutoClaude/tests/test_conftest_windows_native_skip_report.py` | 只有 AutoClaude 側；**AISDLC_SDD 側仍缺**（finding R76-15 ②，本輪未做） |
| runtime 逐支明細 | ✅ `report_all_skips`（根層閘門每次都印，DEF-101-510） | **只有根層 unittest**；AutoClaude pytest 側只有 `-rs` 且非預設 |
| **AutoClaude 的 224 這個數字** | 🔴 **無值判準**。只有 `--check-snapshot` 的指紋觸發器（測試樹一變即 presumed stale，逼人回填）——它管「數字新不新鮮」，**不管「這個數字可不可以接受」** | — |
| 兩棵 `fsm_runtime/tests` | 🔴 **完全在射程外**（`_EXTRA_SCAN_TREES` 不含 `AISDLC_SDD_v0.NN/`） | — |
| 「基線數字只准住一個家」 | ⚠️ `tools/check_pytest_baseline_sites.py` — 但它是**寫死 6 檔的白名單**（`_SCAN_FILES`，行 58-69） | 🔴 **本檔就是活體反證**：本檔通篇寫著 `3900 passed, 224 skipped`，跑該閘門實測 **rc=0**（`✅ pytest 基線站點守門通過：6 份掃描檔中僅 SSOT…`）。R59 已經為同一形態補過一次檔（`docs/AISDLC_Agent_UserGuide.md`，該檔的舊數字「落後數百支且從未翻紅」），白名單型鎖只會在**受害之後**才長 |

---

*本檔為 R76 Scan-Q3 產出。所有數字皆 2026-08-05 於 Windows 11 Pro（26200）原生 PowerShell
實測，指令與 rc 逐項列於 §1／§4。掃描員為唯讀角色，除本檔外未改動 repo 任何檔案。*
