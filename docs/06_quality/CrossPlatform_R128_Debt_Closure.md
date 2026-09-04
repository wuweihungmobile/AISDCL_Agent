# CrossPlatform R128 技術債結案證據檔（落地輪：呈報單七項落款）

- **輪籤**：R128（2026-09-04，Windows 11）
- **輪型**：落地輪。掌舵者對 R127 呈報單七項逐項回覆「同意建議」，本輪把七項落款成
  程式碼與帳本狀態，外加一筆落地候選（`DEF-200-264` 接線）。
- **護欄層**：<!-- guard-total:R128 --> 行數 `92268→92268`（淨額 **+0**）。本輪未動任何
  `_FROZEN_GUARD_LINES` 成員檔，`--print-guard-lines` 逐檔漂移 0 支 ⇒ **不重釘**
  （在零漂移的輪次追加重釘列，那一列自己就是本輪唯一的淨額來源）。
- **體例**：不使用「延後到R／交給R／留給R／承接輪次：R」等前瞻輪號句型；所有數字皆本
  session 親跑。

---

## §裁決總覽（七項逐項落款結果）

| 呈報單項 | 掌舵者裁決 | 本輪落地 | 帳本結果 |
|---|---|---|---|
| ① R121 呈報單檔頭 | 改 Adopted | 已落款，並就地訂正一筆推薦的假前提 | 非帳本列 |
| ② `DEF-200-259` | wontfix | 已落款 ＋ 三處活指示改符號名錨 | wontfix |
| ③ `DEF-200-182` ① | 家歸 `check_handoff_carriers.py` | **原設計對立案案例失明**，未實作 | 仍 open（②已結） |
| ④ `DEF-200-256` | 維持不修 | 已落款（登記面現查確認） | wontfix |
| ⑤ `DEF-200-255` | opt-in 終態 | 已落款 ＋ 政策自述劃出例外 | wontfix |
| ⑥ `DEF-101-736` 子項 | `560` wontfix 落款 | 已落款（列本身仍有三筆子項） | 仍 open |
| ⑦ `DEF-101-856` ⑥ | 本機 Docker 算 staging | **裁決的事實前提不成立**，未結 | 仍 open |

**未結列**：34 → **31**（結 4：`DEF-200-259`／`DEF-200-255`／`DEF-200-256`／`DEF-200-264`；
新立 1：`DEF-200-265`，途中發現，逐節在 `CrossPlatform_R128_Scan_Findings.md` §3）。
`check_defect_log_crossref.py` 不帶參數 rc=0、`--unresolved-count` rc=0（實測「未結列數＝31／
全部 194 列」）。

🔴 **兩筆沒有照裁決結案，理由都是「裁決依據的事實經現查不成立」**（③ 與 ⑦），逐節寫在下方。
把它們塗綠會製造兩個更壞的結果：③ 會做出一個對自己立案案例一次都不會出聲的鎖；
⑦ 會宣稱一組根本還沒實作斷言的測試「已覆核」。

---

## §DEF-200-259（wontfix ＋ 三處活指示訂正）

**裁決**：wontfix。理由＝治理文件本來就明文「行號會漂移，請用符號名定位」。

**現查依據（本輪實跑 `git grep`，四處明文政策）**：

| 座標 | 逐字 |
|---|---|
| `PRD_Amendment_R108_Pacing.md`〔現查碼〕欄 | 「文中給出檔案與行號；行號會漂移，複現時以『函式名』為錨」 |
| `PRD_Amendment_R108_BurnDown_Addendum.md`〔現查碼〕欄 | 「行號會漂移，錨是**函式名**」 |
| 同檔 ④ 底線列 | 「跨檔引用一律用節號」／「行號會漂移，錨是節號」 |
| `test_bash_probe_spec_contract.py` 的豁免說明 | 「不用行號登記表——行號會漂移」 |

**逐筆訂正是無底洞的實證**：`CrossPlatform_R96_Scan_Findings.md` §F-④ 自己記載，同一個座標
在**同一輪內漂了兩次**（包 A 寫時為真 → 包 B 在該檔上方插入註解推走 → 該包當回合再查又不同）。
在 append-only 帳本上逐筆追訂正，成本隨編修次數線性成長而收益為零。

### 🔴 wontfix 的例外面：三處**仍在生效的祈使指示**已就地訂正

`§F-④` 原文把「歷史敘事」與「仍生效的指示」混在同一個清單裡，但兩者不同軸：

- **歷史敘事**（史料快照、已結列、已歸檔列）：wontfix，逐字保留。
- **祈使指示**（「一律以 X 現查為準」這種指路牌）：**不是史料**。它指錯地方時，照做的人會查到
  不相干的東西 ⇒ 這是活的缺陷，不是歷史記錄。

本輪實查 `tools/run_root_unittests.py` 的 `MIN_TESTS` 現在住 **L58**，而
`ADR-XPLAT-002-platform-surface-reduction.md` 有三處祈使句以 `:48` 為錨（該行現在是別的內容）。
三處皆改為符號名錨（`tools/run_root_unittests.py` 的 `MIN_TESTS`）：

1. §8 邊界 8 的 R66 訂正段末句（「一律以 … 現查為準，勿沿用本條所引任何數字」）——並附
   `DEF-200-259` 落地訂正註記，明說同條上方那句「我實查」屬 R60 史料、行號逐字保留不改。
2. 同段上一行的括號指路（「… 的註解本身就明文規定了這個取值程序」）。
3. §6 表格內「現況請一律以 … 現查為準」那一格。

**刻意不動**：同段「我實查 :48」屬 R60 當回合的量測史料；`DEF-101-701`／已歸檔列引用的座標
亦屬史料面。

---

## §DEF-200-255（wontfix：opt-in ＋ env 門檻即終態）

**裁決**：明文 opt-in 終態。理由＝它量的是延遲，開發機的鄰居行為本來就會干擾。

**現查發現：opt-in 不是要新建的狀態，是 R82 已用實測數據驗證過並主動退回的現況。**
`tools/lib/skip_group_policy.py` 的登記註解逐字：

> `env-disabled` 維持 12——本輪一度把 `PG_REAL_ENABLED` 接進 conftest 自動打開，實跑
> `p95=51.703ms ≥ 50ms` 後判定那會製造 flaky 閘門，故回退為 opt-in（見該檔 reason）。

**三次獨立量測都落在 50~52ms 窄帶**（門檻 50ms）：

| 出處 | 值 | 情境 |
|---|---|---|
| `test_pgvector_real_recall.py` 檔頭註解 | 50.59ms | 100 query × HNSW top-10、pgvector:pg18 on Docker Desktop |
| 同檔 `TestP95Latency` 註解 | 51.32ms | 同一台機器 |
| `skip_group_policy.py` 登記註解（R82 自動打開實驗） | 51.703ms | 機器忙碌時 |

⇒「結構性 flaky」有連續三輪實測支撐，不是一次性結論。Windows 那一格已另行校準為 80ms 預設
（`test_pgvector_real_recall.py` 依 `sys.platform` 分流），Linux/CI 仍 50.0。

### 落地內容：修掉「政策自述 ↔ 帳本落款」互相矛盾

原政策自述逐字寫「`env-disabled` 應該清到 0」，而這句話**沒有排除**設計上永久 opt-in 的那一半。
帳本落款成終態、政策卻說該清到 0 ⇒ 下一個讀政策的人會照著把它打開，那正是 R82 已經踩過一次
的坑，而群天花板只看群總數、不看群內成分，**機械層攔不住這種重演**。

`tools/lib/skip_group_policy.py` 的分群 WHY 段落改為明文兩分：(a) 缺件型該清到 0；
(b) 設計上永久 opt-in 型清不掉也不該清（具名 `DEF-200-255` 與 R82 的實測值）。

**刻意不動**：`_RUNTIME_SKIP_CEILING`／`_RUNTIME_SKIP_CEILING_MAX` 兩表的數字。這兩支測試以
`[ENV-DISABLED]` 身分早已計入該剖面現值，落款不改變任何 skip 計數 ⇒ 動它才是製造漂移。

---

## §DEF-200-256（wontfix：維持已登記的可見欠債）

**裁決**：不修。理由＝修一個不會執行的檔，換來破壞一條可機械核對的不變量，不划算。

**現查三筆（本輪實跑）**：

1. `git ls-files "*hub-push.yml"` 的計數為 **30**；根層 `.github/workflows/*.yml` 的列舉裡
   **沒有** `hub-push.yml`。GitHub 只執行 repo 根 `.github/workflows/` 下的 workflow
   ⇒ 這 30 份在本 monorepo 結構上不會被執行。
2. 欠債登記確實在：`tools/tests/test_platform_neutral_paths.py` 的 `_GIT_QUOTEPATH_DEBT`
   有該檔條目，理由逐字已寫明「各版此檔為同一 git blob 是一個目前可機械核對的不變量，
   只改 LATEST 這一份會讓它首次分裂」。
3. 該登記表是**雙向精確比對**：未登記的 offence 紅，已還的欠債留在表裡也紅
   ⇒ 這筆欠債是「被看著的」，不是遺忘。

**誠實劃界**：這條 wontfix 的成立依賴「該 workflow 不會被執行」這個事實。若日後把
`hub-push.yml` 搬進根層 `.github/workflows/`，本裁決即失效。

---

## §DEF-101-736（子項 `DEF-101-560` wontfix 落款；本列仍 open）

**裁決**：`560` wontfix 落款；`649` 待 macOS 真機；`880` 待以新尺重算。

**現查 `DEF-101-560` 的狀態逐字**（`CrossPlatform_R81_Ledger_Triage.md` 的真待辦表）：

> `DEF-101-560`（「fixed@R60（主檔）／open（archive 側 14 列，承接輪次：未指派）」）

⇒ 主檔那一半 R60 已修，殘留的只有 archive 側 14 列的舊資料格式。archive 是歷史記錄
（搬進去就是為了不再編修），對它做格式回溯與 append-only 精神相衝 ⇒ wontfix 成立。

**本列為何仍 open**：`DEF-101-736` 承接四筆子項，`560` 落款後仍有三筆——`DEF-101-557`
（跨包請求未落機械載具）、`DEF-101-649`（產出已交付但 ADR 未回填）、`DEF-101-880`
（違規率未以新尺重算）。掌舵者未對 `DEF-101-557` 表態，該筆維持原狀。

---

## §DEF-200-182（② 結案；① 原設計失明，未實作）

### 瘦身：原現象欄逐字保全（R124 體例）

本列現象欄原 654 bytes、餘裕 46，且**含一句已被本輪推翻的宣稱**。依 R124 體例瘦身，原文逐字
保全於此（一字未改）：

> 🔴 **假綠 B（沒跑）**：`ea304b2` 的〈驗證〉節只列四項，不含 `local_ci_gate.sh` 與
> `AISDLC_SDD/scripts/tests` ⇒ DEF-200-179／180 從未被量到；而 `pre-push:120`／`:261` 本會跑
> 那套 ⇒ 該次 push 必定繞過 pre-push，🔴 繞過手段證據只在那台 Windows 機器上，不猜。見
> `CrossPlatform_R98_Mac_Closure_Evidence.md` §4

### ② 結案：不是繞過，是 leg 依路徑路由合法不觸發

**親驗兩筆（本輪實跑，皆為主控本人親跑，非轉述）**：

1. `git diff --name-only ba4599f ea304b2` 的輸出裡，落在 `AutoClaude/` 或 `AISDLC_SDD/` 底下的
   檔案數實測 **`count=0`**——那次變更全落在 `tools/`、`docs/`、`ONBOARDING.md`。
2. `tools/git-hooks/pre-push` 設定 `run_autoclaude`／`run_sdd` 的那兩行，判準純粹是
   「push 範圍字串裡有沒有該子樹路徑」⇒ 這兩個 leg 在該次 push **合法不觸發**。

⇒ 原推論的前提（上游 `CrossPlatform_R98_Mac_Closure_Evidence.md` §4 逐字寫的「R98 確實改了
AutoClaude 檔」）與第 1 筆直接矛盾。**沒有繞過這件事**，也就沒有「繞過手段永不可知」這個
取證死結——R121 呈報單對 ② 的 `closed-by-decision` 理由因此被推翻，已在該檔就地加訂正註記。

### ① 為何不照原設計實作

R121 呈報單〈方向 A〉把判準寫成：

> 在 `check_handoff_carriers.py`（或新工具）加判準：commit 訊息／交接文件的〈驗證〉節，
> 在 push 範圍含 `AutoClaude/` 或 `AISDLC_SDD/` 時必須列出 `local_ci_gate` 與 `ci-gate.sh` 那一套

而立案案例的 push 範圍**恰好不含**那兩個目錄（親驗 `count=0`）⇒ 照這個設計做出來的鎖，
**對它自己的立案案例一次都不會出聲**。這正是本 repo 反覆記載的「鎖沒有鑑別力」病，且這一次
是在動工前就看得到。

**真正的缺口改判**：〈驗證〉節沒有交代**某些 leg 為何沒跑**，讀者因此分辨不出「路由未觸發」
與「被繞過」——R98 那次誤判就是這個分辨不出來造成的。判準要判的是「交代的完整性」，
不是「有沒有列出兩個特定字面」。分母＝`pre-push` 實際的六個 leg（AutoClaude／AISDLC_SDD／
root-infra 快層／root-infra 慢層／根層消費檔／整合閘門），其中兩個依路徑路由。

**這是設計面的重新拍板，不是實作細節**：它改變判準的輸入面（需要知道變更範圍才知道該觸發
哪些 leg），也改變假紅風險。已列入本輪呈報單。

---

## §DEF-101-856（⑦ 裁決的事實前提不成立，未結案）

**裁決**：本機 Docker pgvector（pg18、alembic head）算 staging 等價替代，理由＝功能正確性
完全測得到，測不準的只有延遲。

**現查三筆，指向「功能正確性目前也測不到」**：

1. **那三支測試的函式體還沒有斷言**。`test_pgvector_hnsw_recall.py` 的
   `test_pgvector_recall_at_10_ge_095` 與 `test_pgvector_p95_latency_under_50ms` 兩支，
   函式體整個就是一句 `pytest.skip("[DEBT] …")`——**沒有任何 `if` 包住它**，DSN 設好也一樣
   skip；`test_pgvector_real_recall.py` 的 `test_bge_failure_minimax_fallback_under_60s` 需要
   一個本機不存在的 fixture 檔，且其末尾是 `assert True`。⇒ 讓它們「跑起來」等於**寫測試實作**，
   不是設環境變數。
2. **staging 的機械定義是「≥1000 列真實 BGE-M3（1024 維）向量 ＋ HNSW index」**（登記在
   `test_conftest_windows_native_skip_report.py` 的平台綁定欠債表）。本機容器唯讀查詢：
   `pgvector/pgvector:pg18`、`Up 35 hours (healthy)`、`alembic_version` 已到
   `0018_version_kind_discriminator`、`knowledge_entries` 共 100 列且**真實 BGE-M3 為 0 列**
   （其餘為 mock 種子）。⇒ 以現行判準量，本機不滿足。
3. **本機連跑都跑不起來**：`AutoClaude/.venv` 沒有 `psycopg2`／`pgvector`。本輪跑針對測試時
   PG autodetect 自己印出來的逐字即為證據：`[PG autodetect] 偵測到 PG 但拒絕注入（psycopg2
   未安裝（uv pip install -e '.[postgres]'`））——注入只會把 skip 換成 UndefinedTable`。

**為何不擅自改判**：有一道現在有牙的鎖（平台綁定欠債表的「這台機器還得起卻還掛著 skip 就紅」
判準）正在用「≥1000 列真實 BGE-M3」這把尺量。要讓裁決成立有兩條路，兩條都改變護欄語意：
(a) 用真實 BGE-M3 模型重新 seed ≥1000 列語料；(b) 放寬那道探針對語料真實性的判準。
兩者都是設計決定，已列入本輪呈報單。**本輪只把現查事實寫進帳本狀態欄**，讓下一個窗口不必重查。

---

## §DEF-200-264（fixed：`state.json ×（1＋保留份數）` 真的計入空間預估）

**立案**：`main.run_boot_self_check` 呼叫 `estimate_freeze_bytes` 時沒傳 `state_bytes`／
`retain_versions`，兩參數的預設值讓 PRD R-6.2-3 ② 那一項恆為 0 ⇒ `STATE_RETAIN_VERSIONS`
的出廠值改動對預估零效果。

**落地三處**（第 3 處是四方複審的修復批，見下方〈複審修復〉）：

1. `FileStateRepository.state_bytes(playbook_id)` 新增公開方法（檔不存在／無權限回 0）。
   🔴 **刻意是公開方法而不是讓呼叫端自己拼路徑**：檔名經 `_sanitize_log_filename` 正規化過，
   把那段規則複製到呼叫端，下一次改規則就會靜默漂移成「量了一個不存在的檔」＝恆回 0 的假預估。
2. `main.run_boot_self_check` 以**鴨子型別探測**取值並傳下去。🔴 刻意不加進
   `StateRepositoryPort` 契約——但**哪些後端回 0 才是正確值**必須寫準（見第 3 處）。
   `playbook_id` 同時提取為變數（原本在參數列上算一次，接線後要用兩次）。
3. `DualStateRepository.state_bytes()` 轉發給 File 主端 ＋ `main.py` 註解訂正。

**紅綠自證（本輪親跑；下表為複審修復後的最終值）**：

| 步驟 | 指令 | 結果 |
|---|---|---|
| 新鎖綠 | `pytest tests/integration/test_def_200_205_production_wiring.py -q -k Def200264` | `4 passed, 22 deselected` |
| **突變驗紅（接線）** | 把 `main.py` 那兩個 kwarg 拔掉後重跑同一條 | `2 failed, 1 passed`（訊息逐字「state 檔大小沒進到預估（收到 None）」） |
| **突變驗紅（Dual 轉發）** | 把 `DualStateRepository.state_bytes` 改名後重跑同一條 | `1 failed, 3 passed`——只中新那一支，其餘不受影響 |
| 還原後回歸 | `pytest tests/integration/test_def_200_205_production_wiring.py tests/test_r100_boot_self_check.py -q` | `66 passed` |
| lint | `ruff check` 四支改動檔（不帶 `--config`） | `All checks passed!` |

`FileStateRepository` 自身那一支在接線突變時**仍綠**——正確，它不依賴 `main.py` 的接線。
兩次突變還原皆走 `Edit` 工具就地改回，未使用任何毀滅性 git 指令。

### 複審修復：`both` 模式漏轉發（Architect 鏡 blocking，主控親驗成立）

**缺口**：`main.py` 初稿註解逐字寫「只有 File backend 會在本機磁碟留 state 檔，PG／InMemory
後端回 0 是**正確值**」。這句話對 `storage.mode="both"` **為假**——`factory.py` 的檔頭逐字
「both： DualStateRepository(File primary + PG shadow)」，其主端就是真的
`FileStateRepository`，會實際把 state 檔寫到本機磁碟。而 `DualStateRepository` 逐一手寫委派、
**沒有** `__getattr__` 萬用轉發（主控親驗：該檔全部 `def` 清單裡沒有 `state_bytes`、
也沒有 `__getattr__`）⇒ 鴨子型別探測拿不到方法、靜默退回 0。

⇒ **`DEF-200-264` 這個「靜默低估」的病灶，在同一輪換一層又犯了一次**，而三支初版測試對它
零射程（它們只用自製 stub 與 `state_repo=None` 兩種情境，沒有一支走過真的 backend）。

**修法三處**：Dual 補轉發方法；`main.py` 註解改為誠實劃界（`db_only`／InMemory／`None` 回 0
正確，`yaml_only` 與 `both` 都會留檔）；補一支用**真** `DualStateRepository(primary=真
FileStateRepository, shadow=None)` 的測試。突變（把轉發方法改名）實測 `1 failed, 3 passed`
——只中新那一支，證明它測的正是轉發本身而非別的東西。

**新鎖住在哪與為什麼**：放進 `test_def_200_205_production_wiring.py` 而非模組自己的測試檔，
是因為該檔檔頭逐字要求「每一支測試都必須在把新加的呼叫拔掉時轉紅」——本缺陷正是
「機制蓋好沒接電」的同型，模組層的鎖在零呼叫端時照樣全綠。

---

## §四方複審（一審；`model: sonnet`，全程唯讀且明令禁跑 pytest 以免與全套互踩）

| 鏡 | 判決 | blocking | 主控親驗結果 | 處置 |
|---|---|---|---|---|
| Architect | `APPROVE_WITH_CONDITIONS` | 1：`both` 模式漏轉發 `state_bytes`，且 `main.py` 註解對此做了為假的斷言 | **成立**（親驗該檔 `def` 清單無 `state_bytes`、無 `__getattr__`；`factory.py` 檔頭逐字「both：File primary + PG shadow」） | 補轉發＋註解訂正＋新測試，突變 `1 failed, 3 passed` |
| SD | `APPROVE_WITH_CONDITIONS` | 2：①本節證據表過期（Dual 修復在複審中途落地）；②`1010 插入／1010 刪除` 與磁碟不符 | **皆成立**。②親驗：單檔 `--numstat` 是 `1000 1000`，`1010` 是**兩檔合計** `--stat` 末行的值 | ①本節已重跑並補第 3 處；②帳本與 Scan_Findings 兩處均訂正 |
| SA | `APPROVE` | 0 | ——（它另獨立親驗了本輪兩個關鍵推論：`ea304b2` 的 `count=0`、兩支測試函式體只有 `pytest.skip`，皆與主控結論一致） | 採納其一項可選建議：R121 呈報單〈核對發現〉節補一句核對軸劃界 |
| QA | `APPROVE_WITH_CONDITIONS` | 3：①`1010`（同 SD ②）；②交棒書〈已驗證〉引用落款前的 193／100 且與同句的 194 自相矛盾；③`Scan_Findings` §1 表漏列 `dual_state_repository.py` | **皆成立**。②親驗現值為 **194 筆／102 份** | 三筆全數訂正 |

**六筆 blocking 全數成立、全數修畢**，零筆被判為假紅。四鏡另有多筆 non-blocking 觀察
（例如「`main.py` 那句『預估量的是工作樹』容易被誤讀成量工作樹所在磁碟的餘量」、
「第三支測試經私有 `_path()` 落檔，測不到未來寫入端與讀取端路徑規則分歧」），本輪未動，
理由是它們都不改變任何判準的正確性，且各自附了「非必要」的自陳。

🔴 **一審即收斂，本輪未跑二審**：六筆 blocking 皆為單點事實錯誤或漏件（非設計分歧），
修法無爭議且逐筆有機械憑證（突變輸出／`--numstat`／閘門重跑值）。二審的價值在於「驗修復」，
而這六筆的修復本身就是可重跑的指令 ⇒ 收斂標準改以「逐筆附可重跑憑證」滿足。

## §本輪未動而下一個窗口可直接消費的座標

- `DEF-200-182` ① 的判準分母＝`tools/git-hooks/pre-push` 的六個 leg，其中
  `run_autoclaude`／`run_sdd` 依路徑路由、`run_rootinfra_guards` 對任何 push 都跑。
- `DEF-101-856` 的兩條路（重新 seed 語料／放寬探針判準）皆會改動平台綁定欠債表的判準面。
- `DEF-101-736` 殘留三筆子項：`DEF-101-557`／`DEF-101-649`／`DEF-101-880`。
