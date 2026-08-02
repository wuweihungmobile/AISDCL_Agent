# ADR-XPLAT-003：`autoclaude/` 生產碼的平台能力抽象層（platform capability layer）

| 欄位 | 內容 |
|------|------|
| **狀態** | Accepted（R69 落地，非設計交付——本 ADR 記錄的是**已合入工作樹並實測綠**的異動） |
| **日期** | 2026-08-02 |
| **決策層** | 架構修復包裁決（承接 R69 Architect REJECT 第 2 點） |
| **適用範圍** | `AutoClaude/autoclaude/`（**生產碼**）內的作業系統平台判斷與行程樹回收。**不適用**於護欄／載具層（`tools/`、`AISDLC_SDD/scripts/`），那一層由 `ADR-XPLAT-002` 管 |
| **關係** | `ADR-XPLAT-002` §1 引述 Architect 的裁決原文：「**跨平台相容性本身沒有出現任何抽象層——沒有統一的 platform capability 層**…裁決＝部分達成，不足以稱最佳化」。該 ADR 的適用範圍是四棵 `tools/` 樹，**結構上碰不到 `autoclaude/`**；本 ADR 補的正是它射程外的那一半。`DEF-101-706` 的**收斂標的**由本 ADR 落地，但該筆**不結案**——帳本狀態欄現為 `partial`（解鎖條件① 餘裕 ≥100 行未達標）。🔴 **R69 終審訂正**：本欄原寫「亦由本 ADR 的收斂項結案」，與同輪帳本直接互斥；ADR 對缺陷狀態的宣稱一律**以帳本為準**，且 ADR 目錄自 R69 起納入 `check_defect_log_crossref.py` 的掃描面（`DEF-101-735`），此類互斥自此可被機械抓到 |

---

## 1. 背景（實測，非引述）

R69 動工前的機械現況：

```
$ grep -rn --include='*.py' "sys\.platform\|os\.name\|platform\.system" AutoClaude/autoclaude
autoclaude/utils/notifier.py:63:    if sys.platform == "darwin" and _try_osascript(title, message):
autoclaude/models/escalation.py:81:        # 未來若要改為依 sys.platform 產生平台原生指令（架構正解…
autoclaude/execution/evaluator.py:22:_NEW_SESSION_KWARGS: dict = {} if sys.platform == "win32" else {...}
autoclaude/execution/evaluator.py:38:    if sys.platform == "win32":
autoclaude/perception/pty_wrapper.py:47:    if sys.platform != "win32":
autoclaude/perception/pty_wrapper.py:192:        if sys.platform != "win32":
autoclaude/perception/pty_wrapper.py:198:            # …故以 sys.platform 守門，見 close()
autoclaude/perception/pty_wrapper.py:301:        if sys.platform == "win32" and isinstance(self._proc.pid, int):
autoclaude/perception/pty_wrapper.py:311:        elif sys.platform != "win32" and isinstance(self._proc.pid, int):
```

9 筆 grep 命中中，**2 筆是註解**（`escalation.py:81`、`pty_wrapper.py:198`），真正的判斷式為 **7 處 / 3 檔 / 3 層**
（`execution/` 2、`perception/` 4、`utils/` 1）。以 AST 計數複驗（不受註解干擾）同為 7。

三個具體後果：

1. **同一套邏輯的兩份複製**：`execution/evaluator.py::kill_process_tree()` 與
   `perception/pty_wrapper.py::close()` 各自寫了一遍「Windows `taskkill /T /F` ／ POSIX `killpg`
   SIGTERM→輪詢→SIGKILL」。兩者連常數（2 秒緩衝、0.05 秒輪詢）都相同，只是變數名不同。
   ⇒ 修一邊忘另一邊＝單平台靜默退化，而 **Windows 零真機**的情況下沒有任何測試會抓到。
   此即 `DEF-101-706` 已識別但未指派的收斂標的（本 ADR 落地的是**該標的**；`DEF-101-706` 本身仍 `partial`，理由見上表〈關係〉欄與帳本該列）。
2. **跨樹不可共用**：根層已有 `tools/lib/platform_utils.py`，但它與 `autoclaude/` 分屬不同封裝樹，
   `autoclaude/` import 它會建立 repo 級的反向相依（且 `.importlinter` 的 `root_packages = autoclaude`
   對它完全不設防）⇒ 結構上不可能共用，不是沒人想到。
3. **LOC 政策壓力**：`check_loc_budget.py` 實測 `total=20436 / cap=20438` ⇒ **餘裕 2 行**，
   `autoclaude/` 生產碼實質凍結。護欄層與生產碼的比例失衡（`ADR-XPLAT-002` §1）在此表現為
   「想修生產碼卻一行都放不下」。
   🔴 **本 ADR 落地後這一條**依然成立、且**一個字都沒有緩解**：§3 的 −21 行只是把額度讓給了
   同輪其他修復包，交付樹現查仍是 `total=20436 / cap=20438`＝**餘裕 2 行、凍結未解除**。
   本節刻意不寫成「壓力已降低」——那正是 §3 原始版本犯的錯（見該節 R69 訂正段）。

---

## 2. 決策

在 `autoclaude/utils/platform_caps.py` 建立**單一平台能力抽象層**，公開四個純函式：

| API | 語意 |
|-----|------|
| `is_windows()` / `is_macos()` | 平台識別（**唯一**允許讀 `sys.platform` 的地方） |
| `new_session_kwargs()` | `subprocess.Popen` 的行程組隔離參數（POSIX `start_new_session=True`／Windows 空 dict） |
| `kill_process_tree(proc)` | 行程樹回收的**全樹唯一實作**（Windows `taskkill /T /F`；POSIX `killpg` SIGTERM→輪詢→SIGKILL） |

三個呼叫端一律改為委派：`execution/evaluator.py`（re-export 供
`execution/mutation_applier/_conditional.py` 沿用原 import 路徑）、`perception/pty_wrapper.py`、
`utils/notifier.py`。

### 2.1 為何放 `utils/`，而不是 `core/ports/` + `infra/adapters/`

這是本 ADR 唯一有爭議的一步，理由逐條：

| 判準 | Port + Adapter | `utils/`（採用） |
|------|---------------|-----------------|
| Port 的存在理由＝**wiring 期可抽換的實作** | 作業系統在 process 啟動時就定死，**沒有第二種實作可注入**；Port 化只會得到「一個介面、一個永遠選中的 adapter」 | 純函式、無狀態、無 I/O 策略，形狀與既有 `utils/trace_context.py` 完全同構 |
| 呼叫端拿不拿得到注入 | `notifier.notify()` 是**模組級函式**，`pty_wrapper._resolve_command()` 是**模組級函式**，兩者都不在 Kernel 建構鏈上 ⇒ 要 Port 就得先把它們物件化，射程遠超「重構不是重寫」 | 直接 import，零改動呼叫形狀 |
| LOC 成本（本輪的硬約束） | interface + adapter + wiring 註冊 + 型別宣告，估 ≥ 80 LOC ⇒ **餘裕從 2 行變成負數**，閘門當場紅 | 淨 **−21 LOC**（§3） |
| `.importlinter` 8 條 contract | `core/ports/` 屬 data tier ≤150 且受 contract 2 保護；新 Port 需同步改多條 ignore | `utils.platform_caps` **不在任何 forbidden 清單內** ⇒ **零新增 ignore 條目**，8 kept / 0 broken |
| 架構純度 | contract 2 禁 `core → infra`；若把實作放 `infra/adapters/`，未來 core 需要平台判斷時無路可走 | `utils/` 是既有 shared-kernel 層，`core` / `execution` / `perception` / `plugins` 皆已 import |

⇒ **判準是「有沒有第二種實作要抽換」，不是「有沒有外部相依」。** 作業系統是前者的反例。
把它 Port 化是把 Hexagonal 當成教條套用，代價（LOC、contract、呼叫端物件化）全部真實，收益為零。

### 2.2 刻意保留的設計細節

- `platform_caps` 內部**於呼叫時**讀 `sys.platform`，不在 import 期快取。理由：Windows 零真機，
  Windows 分支只能靠 `patch("autoclaude.utils.platform_caps.sys.platform", "win32")` 模擬，
  快取會讓那些模擬全部失效（變成恆綠的假鎖）。
- 唯一的例外是 `execution/evaluator.py::_NEW_SESSION_KWARGS` —— 它在 import 期算一次，
  為的是維持 `Popen(..., **_NEW_SESSION_KWARGS)` 這個既有呼叫站點的語意，讓
  `test_new_session_kwargs_are_actually_forwarded_to_popen` 的哨兵手法（平台無關的轉發鎖）繼續有效。

---

## 3. 實測前後（同一個工作樹，改前 / 改後各量一次）

`ADR-XPLAT-002` §1.1 的第一條設計約束是「任何以行數下降為成果的宣稱，必須在同一個 commit 上前後各量一次」。
本節照辦，量法為 `check_loc_budget.py` 自己的 `count_loc`（排除空行與純 `#` 註解行）：

| 檔案 | 改前 LOC | 改後 LOC | Δ |
|------|---------:|---------:|---:|
| `autoclaude/execution/evaluator.py` | 88 | 61 | **−27** |
| `autoclaude/perception/pty_wrapper.py` | 233 | 196 | **−37** |
| `autoclaude/utils/notifier.py` | 102 | 102 | 0 |
| `autoclaude/utils/platform_caps.py` | 0（新增） | 43 | +43 |
| **合計（本包 4 檔）** | **423** | **402** | **−21** |

> `pty_wrapper.py` 的 −37 含同輪另一並行修復包新增的 `CmdLineTooLongError`（+2），
> 本包單獨貢獻約 −39。刻意不去拆算：跨包記帳正是 `ADR-XPLAT-002` §1.1 否決的做法。

平台判斷點（AST 計數，註解不算）：

| 位置 | 改前 | 改後 |
|------|-----:|-----:|
| `execution/evaluator.py` | 2 | 0 |
| `perception/pty_wrapper.py` | 4 | 0 |
| `utils/notifier.py` | 1 | 0 |
| `utils/platform_caps.py`（抽象層自身） | 0 | 2 |
| **合計** | **7 處 / 3 檔** | **2 處 / 1 檔** |

閘門實測（改後，於**交付樹**現查；`cd AutoClaude`）：

```
$ python tools/check_loc_budget.py     # 只引與本 ADR 射程相關的三欄，見下方訂正段 (c)
[check_loc_budget v2-tiered] total=20436 baseline=17032 cap=20438

$ PYTHONUTF8=1 lint-imports
Contracts: 8 kept, 0 broken.

$ python -m pytest tests/ -q           # rc=0、零 failed；passed/skipped 計數不在此登載
```

🔴 **R69 訂正（本節原文寫下的三個數字，在交付樹上一個都複現不出來——與 R68「commit
message 宣稱閘門全綠」是同一型缺陷，只是搬進了 ADR）**。原文逐字保全於下一行（**該行掛
豁免標記；豁免逐行生效，不會放行本段其餘任何一行**），供未來辨認版本：

> 「`total=20415 baseline=17032 cap=20438 violations=0` ／ 改前 total=20436，餘裕 2 行 → **改後餘裕 23 行**」與「`3923 passed, 146 skipped`」 <!-- adr-measurement-historical: R69 訂正前的原文逐字保全，非現行宣稱；本 ADR 的歷史訂正段依 repo 紀律不得改寫 -->

訂正三點：

(a) **餘裕沒有變成 23 行**。上表 −21 行是**本包四個檔**的淨值，是真的；但它與「`autoclaude/`
    總量下降 21 行」是**兩件事**——同輪其他修復包已把這 21 行額度全數消耗，交付樹現查
    `total=20436 / cap=20438`，**餘裕仍是 2 行，生產碼凍結完全沒有解除**（與 §1 第 3 點
    記載的動工前狀態逐字相同）。這正是 `ADR-XPLAT-002` §1.1 那條約束要防的事：本節**照辦了
    「前後各量一次」**，卻把「本包四檔的 Δ」講成了「全樹的餘裕」，射程偷換。
(b) **pytest 計數不再登載於此**。原文的 `3923` 與實測差 6，而根層閘門**取不到** AutoClaude
    全套的現場值（跑一次 80 秒以上）。本 repo 早已為這個數字指定唯一的家：`ONBOARDING.md §7`
    （守門者＝`tools/check_pytest_baseline_sites.py`），要引請指向該處，不要在 ADR 裡再開一個家。
(c) **`violations=` 欄位刻意不登載**：它是**整棵樹當下的裁決**、由最後一個動到任何受管檔的人
    決定。R69 本包量測期間**當場目睹它翻了兩次**——與本 ADR 完全無關的 `tools/dev_start.py`
    一度破 special 2000 上限而讓該欄位轉為非零、稍後被另一包壓回零，而 `autoclaude/` 的
    `total` 全程一動不動。⇒ 把這個欄位寫進 ADR，等於讓任一支無關檔案的預算破線變成本 ADR
    的紅燈。ADR 只引與自己射程相關的 `total／baseline／cap` 三欄（本段刻意連該欄位的
    `<欄名>=<數字>` 寫法都不示範——那個形態本身就是上述機械鎖的違規標的）。

以上三點已由 `tools/tests/test_doc_loc_baseline_freshness_r60.py::TestR69AdrMeasurementTokensAreLive`
機械強制（現查比對＋豁免須具名理由＋掃描面崩塌 fail-loud），不再靠人審。

---

## 4. 強制機制（沒有鎖的架構決策等於沒有決策）

新增於 `AutoClaude/tests/test_evaluator_kill_tree.py` 第 4 節，全部 **AST 而非字串 grep**
（道數以該節實數為準，本表不寫死；註解裡提到 `sys.platform` / `taskkill` 不算違規）：

🔴 **R69 終審訂正（本段原文是過頭的宣稱，已被實測推翻）**：原文逐字為「真正的判斷式與呼叫
**一定**被抓到」。實測不成立——探針當時逐字比對 `ast.Name.id`，`import sys as _s` 之後的
`_s.platform` 對它完全不存在，`from os import name` 這種連 `ast.Attribute` 節點都沒有的形態
更是結構性失明；在 `autoclaude/` 放一支三種形態俱全的樣本檔，本節四道**全綠**。
現行探針已補上 import 別名解析（`import X as Y` 追蹤 ＋ `from X import sym` 判為違規站點），
並以 `test_platform_probe_sees_through_import_aliases` 對六種等價寫法逐一自證。
**訂正後的正確表述**：本鎖抓得到「以 `import`／`from … import` 取得該模組或符號後的判斷與
呼叫，不論是否改名」；它抓不到的仍有——`importlib.import_module("sys")`、`getattr(m, "platform")`
這類動態取用，以及非本檔掃描面（`autoclaude/` 以外）的程式碼。**「一定」這個字不該再出現在
本節**：鎖的射程要能被逐條指認，寫成全稱宣稱只會讓下一個人不再去驗它。

| 鎖 | 驗什麼 |
|----|--------|
| `test_platform_checks_are_confined_to_platform_caps_module` | `autoclaude/` 內除抽象層外零裸平台判斷 |
| `test_platform_check_allowlist_is_shrink_only` | 白名單棘輪的**牙**：清單有殘留條目即紅（不是「宣稱 shrink-only」而已） |
| `test_process_tree_reaping_has_exactly_one_implementation` | 收殺原語（`os.killpg` / `"taskkill"`）只准出現在抽象層 |
| `test_both_reaping_call_sites_route_to_the_shared_implementation` | **身分鎖**：`evaluator.kill_process_tree is pty_wrapper.kill_process_tree is platform_caps.kill_process_tree`（防「各自 import 自己的複製品」） |
| `test_platform_probe_sees_through_import_aliases`（R69 新增） | **探針自證**：六種等價寫法（裸 import／`as` 別名／`from … import`／`from … import … as`，跨 `sys`／`os`／`platform`）必須全部命中——鎖住「別名解析」本身，防解析器被改回逐字比對 |
| `test_platform_probe_does_not_flag_unrelated_names`（R69 新增） | 對照組：同名的區域變數／屬性（如 `c.platform`）不得誤報 |
| `test_reaping_probe_sees_through_import_aliases`（R69 新增） | 收殺原語側的同款自證（`import os as _o` ／ `from os import killpg as _k`） |

🔴 白名單 `_BARE_PLATFORM_CHECK_ALLOWLIST` 目前是**空 frozenset（零例外）**，且棘輪由上表第二道
真實比較強制——刻意不做成 `ADR-XPLAT-002` §8 記載過的那種「檔頭寫著 shrink-only、把上限往上改卻不會紅」
的零強制宣告。新增條目＝繞過抽象層，須先在本 ADR §5 記錄理由。

---

## 5. 例外登記（目前為空）

| 模組 | 理由 | 登記輪次 |
|------|------|---------|
| （無） | — | — |

---

## 6. 判準邊界（誠實劃界）

1. **Windows 側為模擬，非真跑**：本輪平台為 macOS 26.5.2 arm64，Windows 零真機。
   Windows 分支（`taskkill /T /F` 的命令列組裝、`new_session_kwargs()` 回空 dict）皆以
   `patch(".../platform_caps.sys.platform", "win32")` 驗證**我們送出什麼**，
   不主張「Windows 上 taskkill 的實際行為」。POSIX 側則是真跑（真實子行程 pgid 量測）。
2. **本 ADR 只收「平台判斷 + 行程樹回收」**：路徑分隔符、行尾、檔名保留字等跨平台議題不在射程內，
   刻意不擴大（重構不是重寫）。若日後要收，請擴充 `platform_caps` 而非另開第二個收斂點——
   §4 第一道鎖會擋下新的散落點，但擋不了「開第二個抽象層」。
3. **測試側 patch 目標已改指抽象層**：`tests/test_perception.py`（8 處）、`tests/utils/test_notifier.py`
   （4 處）、`tests/test_evaluator_kill_tree.py`（2 處）原本 patch 各自模組的 `sys.platform`。
   `patch("<mod>.sys.platform", ...)` 本來就是在改**全域 `sys` 模組**的屬性（各模組的 `sys` 是同一個物件），
   故掛載點改到唯一決策點後模擬語意不變；改的是掛載點，不是斷言強度。

---

## 7. 為何 AutoClaude 需要自己一份平台判斷，而這不違反 DRY（R70 補記，`DEF-101-751`）

> **為何非補不可**：R69 收輪後 `git push` 被 pre-push 阻斷，唯一紅燈就是本 ADR 與 R17 舊鎖的**正面衝突**——
> `tools/tests/test_platform_utils_dedup.py` 要求 `is_windows` 全 repo 只有一個定義點（`DEF-101-231`），
> 而本 ADR 讓 `platform_caps.py` 也定義了一份。§1 第 2 點雖已寫下「跨樹不可共用」，那是**散文**；
> 鎖讀不到散文，鎖只讀鎖。**架構決策若沒有把「為何允許重複」寫成可被鎖引用的判準，就會在下一次
> 被別的鎖當成違規** —— 修法必須是「ADR 立判準 → 鎖照判準改寫」，不是「把新檔加進白名單了事」。

### 7.1 結構事實：兩個相依孤島

| 孤島 | 範圍 | 唯一真相源 | 為何搆不到對方 |
|------|------|-----------|---------------|
| `root-shared` | 根層 `tools/`（含 `tools/lib/`）、`AutoClaude/tools/`、`AISDLC_SDD/scripts/`、各 `.claude/hooks/` | `tools/lib/platform_utils.py` | 這一層以 `sys.path.insert(root/"tools"/"lib")` 取用，**只依賴 stdlib**（hook 腳本執行環境不保證有第三方套件，見該檔檔頭）。若改 import `autoclaude`，pydantic 會被拉進 hook 與 `aisdlc-sdd-ci` 的 import graph ⇒ 正是 R68 讓該 CI 恆紅的形態（`AISDLC_SDD/scripts/tests/test_cross_subproject_import_isolation.py` 檔頭有實證與 run id） |
| `autoclaude-package` | `AutoClaude/autoclaude/` | `AutoClaude/autoclaude/utils/platform_caps.py` | `autoclaude` 是**可獨立 pip 安裝**的套件（`AutoClaude/pyproject.toml`；hatchling 未宣告 `[tool.hatch.build]`，預設只打包與專案同名的 `autoclaude/`）。根層 `tools/lib/` **不在 wheel 內** ⇒ 純 pip 安裝、脫離 monorepo checkout 的情境下 import 它必然 `ModuleNotFoundError` |

⇒ 這不是「沒人想到要共用」，也不是取捨；**兩個方向的 import 都會壞掉真實情境**，故各留一份是結構必然。

### 7.2 為何不違反 DRY：本 repo 早有同款判例與既定解法

`DEF-101-295`（R33 Architect 裁決）處理過**一模一樣**的情形：Windows 禁用檔名／保留裝置名的判準，
在 `autoclaude/utils/logger.py`、`tools/check_ntfs_paths.py`、`tools/git-hooks/pre-commit` 三處各留一份。
該裁決的原文就寫在 `autoclaude/utils/logger.py` 檔內註解裡：

> 「`autoclaude` 是可獨立 pip 安裝的套件（見 `AutoClaude/pyproject.toml`），**不可依賴 monorepo 根層
> `tools/lib/*.py`**（會讓純 pip 安裝、脫離 monorepo checkout 的情境下失效），故不比照
> `tools/lib/bash_probe_spec.py` 的『共用資料規格』模式合併。三者一致性由
> `tools/tests/test_windows_forbidden_filename_parity.py` 機械鎖住。」

DRY 要消除的是**知識的重複**，不是字元的重複；當結構上不可能共用同一份實作時，正確的形態是
**「跨孤島各留一份 ＋ 以鎖釘住它們不漂移」**，而不是為了字面唯一而製造一條會在真實情境下斷掉的相依。
本 ADR 沿用同一形態，只是把「一致性鎖」換成「**每島唯一性鎖**」（見 §7.3）。

同時**孤島內部仍嚴格 DRY**：`autoclaude/` 內除 `platform_caps.py` 外零裸平台判斷（§4 第一道鎖）；
`root-shared` 內四份核心一律 import `platform_utils`，不得各自重寫（`DEF-101-231`）。
**跨孤島各一份 ≠ 島內可以隨便複製**——後者仍是缺陷。

### 7.3 判準（鎖照著這條寫，不是反過來）

> **每一個相依孤島內，各平台判斷 helper 只准有一個定義點；孤島邊界必須是可被機械驗證的結構事實。**

落地於 `tools/tests/test_platform_utils_dedup.py`：

| 鎖 | 驗什麼 |
|----|--------|
| `test_platform_judgment_helpers_have_one_definition_per_island` | `is_windows`／`is_macos`／`os_label`／`venv_python_path` 在每島至多一個定義點；且該島宣告的 SSOT 必須真的在命中集合裡（防 regex 壞掉後恆綠空砲） |
| `test_autoclaude_package_island_cannot_reach_root_tools_lib` | **孤島邊界的機械證明**：`autoclaude/` 內不得 AST-import 任何 `tools/lib/*.py` 模組（模組名動態自磁碟取得，取到 <5 支即 fail-loud）。此鎖轉紅＝§7.1 的前提不成立、兩島應合併 ⇒ 屆時必須回來刪掉 `platform_caps` 的重複定義並改寫本節，而不是讓雙份定義變成無人複查的既成事實 |
| `TestIslandInvariantIsNotAToothlessWhitelist`（5 支） | 證明它不是白名單：根層孤島／AutoClaude 孤島各注入第三個定義點皆須紅；`os_label` 這種「不屬於某島」的 helper 出現在該島亦須紅；兩島之外的新樹一律歸 `root-shared`（故不會被靜默放行） |

**雙向注入實測**（R70，真檔上機）：

```
① 根層孤島：新增 tools/_probe_root_island.py（def is_windows）
   → FAILED (failures=1)
     AssertionError: Lists differ: ['tools/_probe_root_island.py'] != []
   → 刪除後：Ran 16 tests in 8.460s / OK

② AutoClaude 孤島：新增 AutoClaude/autoclaude/utils/_probe_caps_island.py（def is_windows）
   → FAILED (failures=1)
     AssertionError: Lists differ: ['AutoClaude/autoclaude/utils/_probe_caps_island.py'] != []
   → 刪除後：Ran 16 tests in 8.601s / OK
```

### 7.4 判準邊界（誠實劃界）

1. **本節只管「定義點的數量與位置」，不管兩份實作是否語意一致**。目前兩份 `is_windows` 都是
   `sys.platform == "win32"` 的單行式，漂移風險低但非零；`DEF-101-295` 那組是以 parity 鎖處理的，
   本組**刻意未加** parity 鎖（射程外，重構不是重寫）。要加時請比照
   `tools/tests/test_windows_forbidden_filename_parity.py` 的形態，而不是再開第三個抽象層。
2. **孤島清單是宣告式的**（`_HELPER_ISLAND_SSOT`），只有 `autoclaude-package` 的邊界有機械證明（§7.3 第二道鎖）。
   若日後出現真正的第三個孤島，必須先更新本節再擴充該常數——鎖的錯誤訊息會直接這樣指路。
3. **`platform_caps` 只承載「平台判斷 + 行程樹回收」**（§6 第 2 點）；`os_label`／`venv_python_path`
   刻意不進 autoclaude 孤島（那是護欄層的 venv/標籤語彙，生產碼用不到），鎖會擋下這類擴散。
