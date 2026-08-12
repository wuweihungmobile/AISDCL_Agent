# CrossPlatform_R85_Review_Architect — R85 Architect 獨立複審（macOS，唯讀）

> 複審者角色：Architect 獨立複審（抓漏／挑剔，尤重架構面）。
> **唯讀**：本輪除本檔外未寫入任何檔案、未執行任何 git 寫入指令。
> 🔴 **體例**：每一筆 finding 都附「我這回合真跑過的指令 ＋ 真實輸出」。凡未實測者一律標明。
> 🔴 本輪在 **macOS**（`darwin`）；涉及 Windows 的結論一律標「靜態推論、未真機驗證」。

---

## §0 筆數與嚴重度分佈

| 嚴重度 | 筆數 | 編號 |
|---|---|---|
| **blocking** | **5** | ARCH-01、ARCH-02、ARCH-03、ARCH-11、ARCH-12 |
| major | 5 | ARCH-04、ARCH-05、ARCH-06、ARCH-07、ARCH-13 |
| minor | 3 | ARCH-08、ARCH-09、ARCH-10 |
| **合計** | **13** | |

**駁回本輪宣稱：4 筆**（ARCH-01 駁 P2「delta 0／第一個非上升輪」、ARCH-02 駁 P12「exe-argv 可達性判準落地」、ARCH-04 駁「R85 是減法輪」的成立條件、ARCH-12 駁「鐵律三大表分子增列已完成」）。

> 🔴 **一句話總結**：**工作樹目前是紅的——根層 unittest 全套 `Ran 3284 tests / FAILED (failures=7, skipped=44) / EXIT=1`**，
> 其中 **6 支為真、1 支為並行測試污染**（我已單跑複驗為 OK，見 ARCH-13）。
> 6 支真紅收斂為 **3 個根因**：護欄層淨額 +458（3 支）、E501 債棘輪 140>139（1 支）、鐵律三覆蓋率 floor 過時（2 支）。
> **三個根因全部是「本輪動了治理數字卻沒把對應常數重釘回去」的同一種形態。**

---

## §1 我這回合真跑過的指令與輸出（取證清單）

**取數管道自證**：凡「命中 0／不可達／恆綠」的宣稱，下表都附一個已知會命中的**對照組**。

| # | 指令（絕對路徑 python，**讀 rc 不接管線**） | rc / 輸出 |
|---|---|---|
| 1 | `.venv/bin/python tools/tests/test_adr_xplat001_c1c2_lock.py --print-guard-lines` | rc=**0**；末行逐字 `# _GUARD_LINES_REPIN_LOG 新列：("R<n>", 82838, 83296, +458, "<理由>"),` |
| 2 | `cd tools/tests && ../../.venv/bin/python -m unittest test_adr_xplat001_c1c2_lock` | rc=**1**；`Ran 133 tests` / `FAILED (failures=3)` |
| 3 | `git diff --numstat HEAD`（分 code/docs 桶彙總） | code `ins=2167 del=1262 net=+905 del_ratio=36.8%` |
| 4 | 同 #3 但對 `a1a07c2~1 a1a07c2`（R84） | code `ins=7872 del=589 net=+7283 del_ratio=7.0%` |
| 5 | `git diff --diff-filter=D --name-only HEAD` | **0 支**（R84 同法亦為 0） |
| 6 | AST：`test_platform_neutral_paths.py` 的 `scan_*` 定義數 vs `_injection_criteria()` 接線數 | **12 定義 / 8 接線**；未接線 4 支 |
| 7 | 對 corpus 直呼 `scan_foreign_exe_argv` | `b8-schtasks`→**HIT**、`b11-powershell-shell`→**HIT**、`a8-shebang-exec`→miss、`b4-exe-suffix`→miss；**對照組**（portable snippet）→miss（正確） |
| 8 | 解析 `_XPLAT_INJECTION_CORPUS` 的 caught flag | 22 題，`True=11 / False=11`；b8／b11／a8／b4 皆仍為 **False** |
| 9 | `grep -rn "PlaybookRunner(" --include='*.py'`（AutoClaude，排除 .venv） | **27 個建構點，100% 落在 `tests/`**；production **0** |
| 10 | `grep -rn "mutation_service" --include='*.py'`（全 AutoClaude） | 非測試呼叫端**只有** `execution/playbook_runner.py:170`（`.apply`）與 `:178`（`.validate_batch`） |
| 11 | `Read AutoClaude/autoclaude/core/kernel.py:387-417` | `_apply_mutation` 只分派 4 型：`GOTO_STEP`／`INJECT_BEFORE`／`INJECT_AFTER`／`REVISE_CURRENT` |
| 12 | `grep -n '= "' AutoClaude/autoclaude/models/step_mutation.py` | `StepMutationType` 共 **7** 型（多出 `DELETE_STEP`／`SKIP_TO`／`CONDITIONAL`） |
| 13 | `.venv/bin/lint-imports`（AutoClaude cwd） | rc=**0**；`Contracts: 9 kept, 0 broken.` |
| 14 | `.venv/bin/lint-imports --config <scratchpad>/ctrl.ini`（**對照組**） | rc=**1**；`CONTROL core must not import models (known-violated) BROKEN` ／ `CONTROL ghost module forbidden KEPT` ⇒ 工具有牙，且 ghost 契約 vacuously KEPT |
| 15 | `.venv/bin/python -m importlinter.cli lint-imports` | rc=**0**、**輸出 0 bytes**（假綠管道，見 ARCH-10） |
| 16 | `.venv/bin/python AutoClaude/tools/check_loc_budget.py --json` | rc=0；`total=20423 cap=20438` ⇒ 餘裕 **15 行** |
| 17 | `find tools/tests -name '*.py' \| xargs wc -l` | **83296** |
| 18 | 同法：`tools/lib`=12038、`tools/*.py`=14444、`.claude/hooks`=3306、`AutoClaude/autoclaude`=**26125**、`AutoClaude/tests`=67755 | — |
| 19 | 分桶普查 `tools/tests/*.py` 的守備標的（見 ARCH-06） | 守散文 34.2%／守 SDD 23.0%／無檔案參照 16.2%／守自己 14.0%／**守生產碼 12.5%** |
| 20 | `cd tools/tests && ../../.venv/bin/python -m unittest discover` | **rc=1**；`Ran 3284 tests in 445.476s` / `FAILED (failures=7, skipped=44)` |
| 21 | 單跑 `test_platform_utils_dedup.…test_sdd_latest_helpers_defined_only_in_sdd_latest`（**隔離複驗**） | **rc=0 / OK** ⇒ #20 的該支為並行污染，見 ARCH-13 |
| 22 | `grep -n "_scan_surface_probe" tools/tests/test_platform_utils_dedup.py` | `:588 probe_dir = _REPO_ROOT / f"_scan_surface_probe_{os.getpid()}"` ⇒ 探針寫進**自己要掃的那個面** |

**#20 的 7 支逐字（`grep -E "^(FAIL|ERROR):"`）**

| 測試 | 根因 |
|---|---|
| `test_the_line_ratchet_took_over_and_has_teeth` | ① 護欄層 +458（ARCH-01） |
| `test_ratchet_is_independent_of_git_state` | ① 同上 |
| `test_a_net_zero_swap_is_red` | ① 同上 |
| `test_e501_debt_only_shrinks` | ② E501 債 140>139（ARCH-11） |
| `test_the_two_floors_are_not_themselves_stale` | ③ `_IRON_LAW3_COVERED_FLOOR` 過時（ARCH-12） |
| `test_every_lock_in_this_file_holds_under_every_simulated_platform` | ③ 同上的模擬平台級聯 |
| `test_sdd_latest_helpers_defined_only_in_sdd_latest` | ④ **並行污染，非真紅**（ARCH-13，已隔離複驗 OK） |

---

## §2 🔴 訴求 2 執行量：我的量法、R85 數字、與 R84 的 2.6% 對照

### 2.1 R84 的 2.6% 是什麼（先把被對照的那個數字還原）

`docs/04_planning/AutoSDD_improving_109.md:22` 逐字：「R84 對訴求 2 的執行量經 Architect 實測為 **2.6%**（淨減法僅 −71 行）」。
同檔 `:13` 給出逐輪護欄層淨額，R84＝**2655**。⇒ `71 / 2655 = 2.67%`。
**該量法的分母是「本輪護欄層淨增量」**，分子是「真正被移除的機制行數」。

🔴 **我不沿用這個量法當唯一判準**，因為它的分母會隨「這一輪剛好加了多少」浮動：加得愈多，同樣的減法看起來佔比愈小。改採**三個互補、皆可重跑**的量。

### 2.2 我的量法（可重跑；三個量各自單邊，不可互相換算）

```bash
# M-A 減法佔比（程式碼面）：del / (ins+del)，只算 .py/.ps1/.sh/.json/.ya?ml，排除 .md
git diff --numstat <RANGE> | awk '$3 ~ /\.(py|ps1|sh|json|ya?ml)$/ {i+=$1;d+=$2} \
  END{printf "ins=%d del=%d net=%+d del_ratio=%.1f%%\n", i,d,i-d, 100*d/(i+d)}'

# M-B 機制整支移除數（訴求 2 的字面意思：「拿掉」）
git diff --diff-filter=D --name-only <RANGE> | wc -l

# M-C 專案自己的 SSOT 指標（護欄層淨額）
.venv/bin/python tools/tests/test_adr_xplat001_c1c2_lock.py --print-guard-lines   # 看末尾建議列
```
`<RANGE>`：R84＝`a1a07c2~1 a1a07c2`；R85＝`HEAD`（工作樹未 commit）。
🔴 **M-A 的已知偏差**：`git diff` **不含未追蹤檔**。R85 未追蹤程式碼 = `AutoClaude/tests/execution/*.py`(766) + `tools/lib/unattended_authz.py`(101) + `tools/probe/xplat_hazard_census.py`(280) = **+1147 行純新增**，下表已補計。

### 2.3 結果

| 量 | R84 | R85（tracked） | R85（含未追蹤，**實況**） | 判讀 |
|---|---|---|---|---|
| **M-A 減法佔比** | **7.0%** | 36.8% | **27.6%**（del 1262 /(3314+1262)） | ✅ **真實改善 ~3.9 倍**——本輪唯一站得住的正面結論 |
| **M-B 機制整支移除** | **0 支** | **0 支** | **0 支** | ❌ **零**。訴求 2 字面上的「拿掉」一次都沒發生 |
| **M-C 護欄層淨額** | +2655（宣稱）／實為 +3755 | 宣稱 **0** | **+458**（實測） | ❌ 宣稱為假，見 ARCH-01 |
| 程式碼淨行數 | **+7283** | +905 | **+2052** | 仍是加法輪 |

### 2.4 結論（三句話）

1. **以 M-A 衡量，R85 確實比 R84 減法得多（27.6% vs 7.0%，約 3.9 倍）**——這一點我實測支持，本輪不是空話。
2. **以 M-B 與 M-C 衡量，R85 不是減法輪**：整支移除 0 支，護欄層淨額 **+458**（不是宣稱的 0）。
3. ⇒ **本輪自訂的成敗判準（`AutoSDD_improving_109.md:11`「R85 是減法輪」＋「連八輪上升後第一個非上升輪」）未達成。**
   若要用 R84 那把尺（分子/分母）逼近一個可比數字：本輪真正屬於「拿掉機制」的淨減項集中在
   `tools/check_wrapper_thinness.py`(−89) 與其測試(−82) 共 **−171 行**，對分母 +458 ⇒ 約 **−37%**，
   但這個比值因為分母是「淨增量」而不穩定，**我不建議用它當下一輪的判準**，建議改用 M-A＋M-B 雙軌。

---

## §3 逐筆 Findings

### 🔴 ARCH-01（blocking）P2 宣稱「淨額 0／連八輪上升後第一個非上升輪」為假，且**工作樹現在是紅的**

**現查指令與輸出**
```
$ .venv/bin/python tools/tests/test_adr_xplat001_c1c2_lock.py --print-guard-lines
rc=0
# _GUARD_LINES_REPIN_LOG 新列：("R<n>", 82838, 83296, +458, "<理由>"),

$ cd tools/tests && ../../.venv/bin/python -m unittest test_adr_xplat001_c1c2_lock
rc=1 ; Ran 133 tests ; FAILED (failures=3)
```
三支紅（逐字）：
- `TestGuardLayerRatchet.test_the_line_ratchet_took_over_and_has_teeth`
- `TestShrinkOnlyRatchet.test_ratchet_is_independent_of_git_state`
- `test_a_net_zero_swap_is_red`

紅燈訊息逐字：`[成長] 護欄層行數由 82838 增為 83296（+458）`，成長最多者
`[('test_platform_neutral_paths.py', 221), ('test_doc_loc_baseline_freshness_r60.py', 138), ('test_block_destructive_git_r83.py', 93), ('_ps_engine.py', 7), ('test_check_hooks_liveness.py', 6)]`。

**為什麼是問題**
1. `_GUARD_LINES_REPIN_LOG` 已寫入 `("R85", 82838, 82838, 0, …)`，而磁碟實測是 **83296**。**這一列是假事實**，且它正是本輪對外宣稱「第一個非上升輪」的唯一依據。
2. 🔴 **這是 R85 自己診斷的那個病，在同一輪原地復發**：`test_adr_xplat001_c1c2_lock.py` 內 R85 新寫的註解逐字說明 R84 失敗的原因是「**同一輪稍後的第二次重釘**（+1100）已讓 R84 的真實合計變成 3755 ⇒ 到期目標訂完就過期了」。本輪 P2 在 P12（自陳 +425）等包停工**之前**重釘，於是重演同一形態。CLAUDE.md 的重釘紀律逐字要求「多包並行的輪次由**收尾包在所有包停工後**重釘一次」——本輪未遵守。
3. 款(11)（`ADR-XPLAT-002 §8.1 item 15`）要求 **R86 前兌現一次淨額 ≤ 0 的重釘**。+458 ⇒ **未兌現**，債務原封不動滾進 R86。

**修法草案**（收尾單人窗口，非並行包）
在**所有包停工後**重跑 `--print-guard-lines`，以實測值重釘 `_FROZEN_GUARD_LINES`，並把 R85 那一列改為實測三元組。若仍要主張「非上升輪」，必須真的再刪 ≥458 行；否則**誠實把該列寫成 +458 並移除「第一個非上升輪」的宣稱**（本輪其他文件亦須同步）。

🔴 **複審末追記（工作樹在我複審期間被另一個窗口就地修改，此處記錄我最後一次量到的狀態）**
另有窗口正在做這次重釘，且**目前是半套**：
```
$ .venv/bin/python tools/tests/test_adr_xplat001_c1c2_lock.py --print-guard-lines
# _GUARD_LINES_REPIN_LOG 新列：("R<n>", 83320, 83320, +0, "<理由>"),   ← _FROZEN_GUARD_LINES 已重釘為 83320

$ grep -A6 '"R85", ' tools/tests/test_adr_xplat001_c1c2_lock.py
        "R85", 82838, 82838, 0,                                        ← 但 LOG 那一列仍是舊值

$ cd tools/tests && ../../.venv/bin/python -m unittest test_adr_xplat001_c1c2_lock
rc=1 ; Ran 133 tests ; FAILED (failures=6)      ← 由 3 紅變 6 紅
  test_the_repin_log_accounts_for_the_frozen_table
  test_appending_one_row_keeps_the_history_digest_stable
  test_letting_the_unfrozen_tail_grow_is_red
  test_the_docs_cite_the_live_guard_total
  test_the_extended_doc_surface_covers_the_handoff_without_false_reds
  test_the_real_repin_log_stays_inside_the_cost_envelope
```
**這個半套狀態本身就是 ARCH-01 的最佳佐證**：一次「重釘」不是改一個數字，而是要同時收斂
**凍結表 ＋ LOG 列 ＋ history 指紋 ＋ 文件引用的 live total ＋ 交棒書** 五個站點；
只改前一個就會讓紅燈數**上升**（3 → 6）。⇒ 這正是鐵律七講的「常數／史料／消費端不在同一持有面」，
**必須一次做完**，且**期間不得有其他窗口同時改 `tools/tests/**`**（否則 total 再次漂移，無限循環）。
🔴 我最後一次量到的 `GLC_LINES = 83320`（非我量第一次的 83296）——**這個數字在收尾當下必須重量，不可引用本檔任何一個值**。

**持有面**（🔴 **五個站點，非三個**——複審末的實測修正）
1. 常數：`tools/tests/test_adr_xplat001_c1c2_lock.py` 的 `_FROZEN_GUARD_LINES`
2. 史料：同檔 `_GUARD_LINES_REPIN_LOG` 的 R85 列
3. 指紋：同檔 `_REPIN_LOG_FROZEN_PREFIX_LEN`／`_REPIN_LOG_HISTORY_SHA256`（**須在貼上新列之後**重跑 `--print-guard-lines` 才算得出來）
4. 消費端：同檔測試（第一次量到 3 支、半套狀態下 6 支）
5. **文件引用的 live total**：`docs/04_planning/AutoSDD_improving_109.md`、`docs/06_quality/CrossPlatform_R85_Ledger_Closure.md`、`docs/06_quality/CrossPlatform_R85_Guard_Repin_Evidence.md`（複審期間新出現）、以及 `R85_HANDOFF`（由 `test_the_extended_doc_surface_covers_the_handoff_without_false_reds` 守）

---

### 🔴 ARCH-02（blocking）P12 新建的 `scan_foreign_exe_argv` **未接進 M5 矩陣**，本輪把接線率**做差了**

**現查指令與輸出**
```
$ .venv/bin/python  (AST 對帳 tools/tests/test_platform_neutral_paths.py)
scan_* defs = 12
wired into _injection_criteria = 8
NOT wired: ['scan_foreign_exe_argv', 'scan_git_path_enumeration',
            'scan_naive_timestamp_persist', 'scan_ps_platform_sites']

$ (對 corpus 直呼新 scanner)
a8-shebang-exec        corpus_flag=False  -> miss
b4-exe-suffix          corpus_flag=False  -> miss
b8-schtasks            corpus_flag=False  -> HIT
b11-powershell-shell   corpus_flag=False  -> HIT
CONTROL portable snippet -> miss(correct)        # 取數管道自證：對照組不誤命中

$ (解析 _XPLAT_INJECTION_CORPUS)
corpus items=22 ; caught totals: {'True': 11, 'False': 11}
```

**為什麼是問題**
1. P4 的深掃報告（`CrossPlatform_R85_Scan_Findings.md` §B-0）已把「M5 判準集自己漏了三分之一」列為 **blocking**，當時量到 **11 定義 / 8 接線**。本輪 P12 新增了第 12 支，**卻沒有接線** ⇒ 接線率由 8/11 惡化為 **8/12**。**針對 blocking 的處置反而讓該指標變差。**
2. 更關鍵：P4 的 §B-1 表逐字把 `b8-schtasks`／`b11-powershell-shell` 的修法指向「**A-3**」（＝這支新 scanner）。我實測證明**它真的攔得到那兩題**（HIT），對照組不誤命中。但因為沒接線，`_XPLAT_INJECTION_CORPUS` 仍記 `caught=False`、矩陣仍是 11/22。
   ⇒ **能力已經做出來，卻對所有閘門不可見**——這正是本輪要抓的「看起來像修好了、其實沒有」的**鏡像**：東西是真的做好了，但**沒有接上，所以等於沒做**，而表徵（測試全綠、scanner 有自己的單測）與「做好且接上」完全相同。
3. 另外三支未接線者（`scan_git_path_enumeration`／`scan_naive_timestamp_persist`／`scan_ps_platform_sites`）是 R81／R84 的存量，本輪未處理。

**修法草案**（一行 ＋ 兩個 flag）
```python
# tools/tests/test_platform_neutral_paths.py :: _injection_criteria()
"foreign-exe-argv": scan_foreign_exe_argv,
```
接線後把 `_XPLAT_INJECTION_CORPUS` 中 `b8-schtasks`／`b11-powershell-shell` 的 caught flag 由 `False` 翻 `True`（矩陣 11/22 → **13/22**），並重跑 `TestXplatInjectionMatrix` 以實測值收斂。
🔴 **注意**：此檔本輪已 +221 行（ARCH-01 的最大成長來源），改動會再動到 `_FROZEN_GUARD_LINES` ⇒ **必須與 ARCH-01 的重釘同一次做完**，否則兩者互相把對方打紅。

**持有面**
- 消費端：`tools/tests/test_platform_neutral_paths.py` 的 `_injection_criteria()`
- 史料：同檔 `_XPLAT_INJECTION_CORPUS` 的兩個 caught flag
- 連帶常數：`tools/tests/test_adr_xplat001_c1c2_lock.py` 的 `_FROZEN_GUARD_LINES`（同 ARCH-01）
🔴 **三者跨兩支檔 ⇒ 依鐵律七，本項不得派給並行包，只能由收尾單人窗口做。**

---

### 🔴 ARCH-03（blocking）訴求 2 最大的一筆可執行減法，本輪**一行未動**

P11 的宣稱我**獨立驗證為真**，且比它自己說的更強。

**現查指令與輸出**
```
$ grep -rn "PlaybookRunner(" --include='*.py' .  (AutoClaude, 排除 .venv)
27 個建構點，逐檔統計後 100% 落在 tests/；production 0

$ grep -rn "mutation_service" --include='*.py' .
非測試呼叫端只有：
  autoclaude/execution/playbook_runner.py:170  -> .mutation_service.apply(
  autoclaude/execution/playbook_runner.py:178  -> .mutation_service.validate_batch(

$ Read autoclaude/core/kernel.py:387-417
_apply_mutation 只分派 4 型：GOTO_STEP / INJECT_BEFORE / INJECT_AFTER / REVISE_CURRENT

$ grep -n '= "' autoclaude/models/step_mutation.py
StepMutationType 共 7 型（多 DELETE_STEP / SKIP_TO / CONDITIONAL）

$ grep -n "PlaybookRunner" autoclaude/main.py
:145  # 舊 PlaybookRunner 直連模式已於 W6 拔除（DeprecationWarning 期已結束）
:155  kernel = build_kernel(...)   :160  service = AutoResumeService(kernel, ...)
```

**可達性鏈（我實測拼出的完整鏈，非採信自陳）**
```
production 入口 autoclaude.main:main
  → build_kernel()  → AutoResumeService(kernel)  → kernel._apply_mutation()   ← 只認 4 型
MutationApplyService（7 個 strategy，含 ConditionalStrategy/SkipTo/DeleteStep）
  ← 唯一非測試呼叫端 = PlaybookRunner:170/178
  ← PlaybookRunner 的 27 個建構點全在 tests/
⇒ DELETE_STEP / SKIP_TO / CONDITIONAL 在 production **結構上不可達**
⇒ 三份平行 CONDITIONAL 實作全部 production 不可達：
   autoclaude/core/services/mutation/conditional.py              (116 行)
   autoclaude/core/services/mutation/_conditional_evaluator.py   ( 56 行)
   autoclaude/execution/mutation_applier/_conditional.py         (103 行)
```
`wiring.py:231/413` 確實把 `MutationApplyService()` 注入 kernel、`kernel.py:58` 也開了 `mutation_service` property——但**沒有任何 production 呼叫端**，只是把不可達的東西接上電源。

**為什麼是問題（架構層級）**
1. 這是訴求 2「拿掉不合理機制」在整個 repo 內**最大的一筆**：三份平行實作共 **275 行**，加上 `MutationApplyService` 的 7-strategy 註冊表與 `PlaybookRunner` 這條 facade，合計遠超本輪所有減法的總和（−171 行）。
2. 它同時是「**不重複模組**」訴求的教科書反例：同一個 CONDITIONAL 語意有**三份**實作，且彼此已經漂移（`shell=True` vs `shell=False`、`_SHELL_TRUE_COND_WHITELIST` vs `_SHELL_FALSE_COND_WHITELIST` 兩份白名單）。本輪 P7 為此**再加**了一層可攜性診斷 ⇒ **在不可達的三份實作之上又疊了第四層**。
3. 本輪對此的處置是「登記發現」，**程式碼一行未動**（我確認 `git diff HEAD` 對三支 conditional 檔只有註解／診斷呼叫的改動，無刪除）。

**修法草案（分階段，本輪不必全做，但必須擇一表態）**
- **階段 0（零風險，建議本輪就做）**：在 `kernel._apply_mutation` 的 `else` 分支對 3 個未處理型別 **fail loud**（記 WARN／raise），讓「production 收到 CONDITIONAL 會靜默忽略」這件事**可偵測**。今天它是靜默 `return None`，與「條件不成立」無法區分——同鐵律六「失敗表徵與正常進行相同」。
- **階段 1**：把 `PlaybookRunner` 與 `MutationApplyService` 標記為 test-only（或整支移除），三份 conditional 收斂為一份。
- 🔴 **風險與成本（誠實劃界）**：`PlaybookRunner` 是 27 支測試的建構點、`.importlinter` 有 2 條契約（Rule 3／Rule 6）以它為 source_modules、`equivalence/` 有快照測試。淨減法會撞「跨檔參照稅」（CLAUDE.md 鐵律三下方已判例：**淨減法只能由收尾單人窗口做**）。⇒ **不可派給並行包。**

**持有面**
- 生產：`AutoClaude/autoclaude/core/kernel.py`（`_apply_mutation`）、`core/wiring.py`、`core/services/mutation/**`、`execution/playbook_runner.py`、`execution/mutation_applier/**`
- 契約：`AutoClaude/.importlinter`（Rule 3／Rule 6）
- 消費端：`AutoClaude/tests/**` 27 個建構點 ＋ `tests/equivalence/`
- 常數：`AutoClaude/tools/check_loc_budget.py`（移除後 total 會掉，`SPECIAL_FILES` 棘輪**雙邊咬人**，須同步下修）

---

### ARCH-04（major）「R85 是減法輪」的定位未達成——建議改寫，不建議補刪

見 §2.3。**M-B（整支移除）＝0、M-C（護欄層淨額）＝+458**。
唯一成立的正面結論是 M-A（減法佔比 7.0% → 27.6%）。
**修法草案**：不建議為了湊「淨額 ≤ 0」而臨時刪行（那會製造 ARCH-02 那種「刪掉的是接線而不是機制」的風險）；建議**誠實改寫定位**為「減法佔比首次進入 ~28% 帶，但淨額仍為正，M1 的『連續三輪不上升』債務滾入 R86」，並把 ARCH-03 的階段 0 排進 R86 當真正的減法標的。
**持有面**：`docs/04_planning/AutoSDD_improving_109.md`、`docs/06_quality/CrossPlatform_R85_Ledger_Closure.md`。

---

### ARCH-05（major）款(10)／款(12) 互斥：分段表是**正解**，但它揭露的是「棘輪把兩個不同的量綁在同一個數字上」

**我的判讀（駁回「這只是補丁」的可能質疑，但也不完全背書）**
- **分段表本身是正解**：`net_cap_for_round()` ＋ append-only ＋ 輪號遞增 ＋ 上限只准遞減，三條形狀鎖俱全（`net_cap_schedule_problems()`），且與既有 `_REPIN_ROUND_CAP_SINCE`「不追溯」語意同構。這是把一次性生效點推廣成分段函式，**是抽象升級不是補丁**。
- **但根因沒被命名**：互斥的成因是 `_REPIN_ROUND_NET_CAP` 這**一個純量**同時承擔兩個語意——「歷史每一輪當時受判的尺」與「未來的目標」。分段表拆開了前者，**後者（`_REPIN_NET_CAP_DUE_TARGET`）仍是純量**，且本輪就地重新武裝為 R87／2600。⇒ **同一個結構性死結會在 R87 以相同形態復發**，除非屆時再追加一列。
- 這正是本輪該問「這個機制合不合理」的地方，而本輪只修了它、沒問它。

**修法草案**：R86 評估是否讓 `_REPIN_NET_CAP_DUE_*` 也表驅動（或直接以「schedule 末列輪號 + N」導出，取消第二個純量）。
**持有面**：`tools/tests/test_adr_xplat001_c1c2_lock.py`（`_REPIN_NET_CAP_SCHEDULE` 常數／`_FROZEN_*` 凍結基準／`repin_cost_ratchet_problems()` 消費端，三者同檔）。
**嚴重度**：major（不擋本輪，但會在 R87 重演）。

---

### ARCH-06（major）護欄層只有 **≤12.5%** 在守生產碼——比例問題的真正形狀不是「太多」，是「守錯對象」

**現查指令與輸出**
```
$ find tools/tests -name '*.py' | xargs wc -l   → 83296
  tools/lib=12038  tools/*.py=14444  .claude/hooks=3306
  → 根層護欄層合計 113,084 行
$ find AutoClaude/autoclaude -name '*.py' | xargs wc -l → 26125   (生產碼)
$ find AutoClaude/tests     -name '*.py' | xargs wc -l → 67755
```
⇒ 根層護欄層 : 生產碼 = **4.33 : 1**；含 AutoClaude 測試的總 harness : 生產碼 = **6.92 : 1**。

**分桶普查（`tools/tests/*.py` 共 63 支 / 83,296 行，依「檔內參照到哪一棵樹」分類）**

| 守備標的 | 檔數 | 行數 | 佔比 |
|---|---|---|---|
| docs／CLAUDE.md（**散文**） | 16 | 28,519 | **34.2%** |
| AISDLC_SDD | 11 | 19,189 | 23.0% |
| 無檔案參照／自足 | 25 | 13,453 | 16.2% |
| **護欄層自己** | 7 | 11,695 | **14.0%** |
| **AutoClaude 生產碼** | 4 | 10,440 | **12.5%** |

🔴 **量法偏差已標明**：這是 first-match 啟發式，優先序把「AutoClaude 生產碼」排**第一**
⇒ 一支同時參照生產碼與散文的檔會被算進生產碼桶 ⇒ **12.5% 是上界，真值只會更低**。
（可重跑腳本見本檔 §1 #19 所用的分桶邏輯；判準＝檔內以引號寫出的路徑字面。）

**為什麼是問題**
「8 萬行護欄 vs 2 萬行生產碼」這個比例本身**不必然不合理**——本 repo 的產品有一半是方法論與文件，守散文是正當的。真正的問題是：
1. **48.2%（34.2%+14.0%）的護欄層在守散文與守自己**，而這一桶正是每輪成長最快的（ARCH-01 的成長榜前三名全在此桶：`test_platform_neutral_paths.py` +221、`test_doc_loc_baseline_freshness_r60.py` +138、`test_block_destructive_git_r83.py` +93）。
2. CLAUDE.md 自己已經判過「**護欄自己是最大單一缺陷來源**——這一桶不會因為多加一道鎖而變小」，但**沒有任何機械物在量這個比例** ⇒ 它每輪惡化而無人看見。

**修法草案（結構性，非「少寫一點」）**
- **S1（本輪可做，零風險）**：把上表這個分桶普查做成 probe（`tools/probe/guard_target_census.py`），輸出可 diff 的 jsonl。**先讓比例可見，再談收斂**——同 repo 對「misstep_attribution」「shell_command_corpus」的既有體例（每輪重跑、不寫死百分比）。
- **S2（R86+）**：把 `_FROZEN_GUARD_LINES` 的單一總量棘輪**按桶拆開**：守生產碼那一桶允許成長，守散文／守自己那兩桶走 shrink-only。今天單一總量的形狀讓「加一支守散文的鎖」與「加一支守生產碼的鎖」付一樣的代價，於是**便宜的那種（守散文）永遠贏**——這正是 34.2% 的由來。
- **S3**：守散文那一桶的根因是 CLAUDE.md 承載了太多會漂移的事實。真正的減法是**把事實移出散文**（本 repo 已在做：「數字一律現查」），每移走一項就能退掉對應的鎖。

**持有面**：`tools/tests/test_adr_xplat001_c1c2_lock.py`（`_FROZEN_GUARD_LINES` 需按桶拆＝常數＋消費端）、新建 probe（`tools/probe/`）、`docs/04_planning/ADR/ADR-XPLAT-002-platform-surface-reduction.md`（政策）。

---

### ARCH-07（major）棘輪／指紋／append-only 史料是否已過臨界？——**依據如下，結論是「未過臨界，但已到必須分桶的點」**

題目要求給依據不給感覺。我用三個可量的指標：

| 指標 | 實測 | 判讀 |
|---|---|---|
| **維護成本**：本輪護欄層改動中，屬於「重釘／指紋／史料」而非新判準的行數 | `test_adr_xplat001_c1c2_lock.py` 本輪 +120（186 ins / 66 del），其中 `_FROZEN_GUARD_LINES` 重釘 8 列 ＋ `_GUARD_LINES_REPIN_LOG` 新增 8 行 ＋ 分段表機制 ~90 行 | 重釘本身的稅 ≈ 16 行/輪，**不高** |
| **它防到的問題**：本輪這套機制是否真的攔到東西 | ✅ **攔到了 ARCH-01**——若無此棘輪，「淨額 0」這句假話**沒有任何東西會反駁它**。3 支紅是它在說話 | **這是它本輪最強的辯護** |
| **失效模式**：機制自己製造的 blocking | ARCH-01（重釘時序）＋ ARCH-05（純量互斥） 皆源自機制本身 | 2/3 的 blocking 出自護欄層自己 |

**結論**：**尚未過臨界**——理由是第二列：這套機制本輪**真的攔下了本輪最重要的一句假話**，這正是它存在的目的，且成本（~16 行/輪）遠低於它防的問題（一句假的治理數字滾進下一輪）。
**但**它已到「必須分桶」的點（ARCH-06 S2）：單一總量的形狀讓成長壓力全部灌向最便宜的那一桶，而那一桶正是 CLAUDE.md 自己判定的最大缺陷來源。
🔴 **我明確反對「因為維護成本高就拆掉棘輪」**——本輪的證據指向相反方向。

---

### ARCH-08（minor）`.importlinter` 「9 kept」含一條**結構恆綠**的契約

**現查指令與輸出（含對照組，證明工具本身有牙）**
```
$ .venv/bin/lint-imports                              → rc=0  Contracts: 9 kept, 0 broken.
$ .venv/bin/lint-imports --config <scratchpad>/ctrl.ini → rc=1
  CONTROL core must not import models (known-violated)  BROKEN   ← 工具有牙（真違規會紅）
  CONTROL ghost module forbidden (should be vacuous)    KEPT     ← 不存在的模組 = vacuously KEPT
  Contracts: 1 kept, 1 broken.
$ ls autoclaude/execution/ | grep _runner_internals    → (無)
```
契約 3 `runner-internals-isolation` 的 `forbidden_modules = autoclaude.execution._runner_internals`
指向一個 **SD_06 W6 G6 已物理刪除**的模組（`.importlinter:78` 自陳）。

**判讀**：這是**刻意的防復活柵欄**，設計上正當（有人重建同名模組就會紅）。
**但**它使「9 kept」這個治理數字高估實際強制面至少 1 條，而 CLAUDE.md 與 Architecture Snapshot 都以「9 kept」當能力宣稱。
**修法草案**：在 Snapshot／CLAUDE.md 標註該條為 anti-resurrection（分母 0），或讓 `lint-imports` 的呼叫端額外印出「有幾條是空集合契約」。
**持有面**：`AutoClaude/.importlinter`（史料/註解）、`AutoClaude/CLAUDE.md` 的 `[Architecture Snapshot]`（機械生成，SSOT＝`AutoClaude/tools/snapshot_sync.py`）。

---

### ARCH-09（minor）AutoClaude LOC 餘裕僅 **15 行**

```
$ .venv/bin/python AutoClaude/tools/check_loc_budget.py --json
rc=0  total=20423  cap=20438  → 餘裕 15 行
```
P11 的 20435→20423 方向正確（我實測 total=20423 屬實），但 cap 距離只剩 15 行 ⇒ **下一個包加 16 行就撞閘門**。
這也反向支持 ARCH-03：`PlaybookRunner`／三份 conditional 的移除會一次釋出數百行餘裕。
**持有面**：`AutoClaude/tools/check_loc_budget.py`（`LOC_TIERS`／total cap）。

---

### ARCH-10（minor）取數管道陷阱：`python -m importlinter.cli` **靜默零輸出 rc=0**

```
$ .venv/bin/python -m importlinter.cli lint-imports  → rc=0, 輸出 0 bytes（假綠）
$ .venv/bin/lint-imports                             → rc=0, "Contracts: 9 kept, 0 broken."
```
我自己第一次就踩了這個坑（先用 `-m` 得到「rc=0」，若不做對照組就會寫下「契約全綠」這個**未經證實**的結論）。
**修法草案**：CLAUDE.md 既有指令寫的是 `PYTHONUTF8=1 lint-imports`（console script）＝正確；建議在 ONBOARDING 補一句「不可改用 `python -m importlinter.cli`，該形態零輸出且恆 rc=0」。
**持有面**：`ONBOARDING.md` §7。

---

### 🔴 ARCH-11（blocking）E501 債棘輪**上升**：140 > 139

```
FAIL: test_e501_debt_only_shrinks (test_subprocess_encoding_hygiene.TestRootToolsLintPolicy)
AssertionError: 140 not less than or equal to 139 :
  tools/tests/ 的過長行由 139 增至 140 —— 本棘輪只准往下改。
```
**為什麼是問題**：一個**自稱減法輪**的輪次，把「過長行」這個純債務指標**往上推了 1**。
數字本身微不足道，但它與 ARCH-01／ARCH-12 是**同一種形態**：本輪動了受棘輪管轄的量，卻沒有回頭把常數收斂。
**修法草案**：把本輪新寫的那一行折行（棘輪訊息逐字要求「新寫的行請自行折行」），**不要**改 139 這個門檻（它只准往下）。
**持有面**：常數＋消費端同住 `tools/tests/test_subprocess_encoding_hygiene.py`；違規行本身散在本輪新增的 `tools/tests/*.py`（現查：ruff E501 對 `tools/tests/`）。

---

### 🔴 ARCH-12（blocking）鐵律三覆蓋率棘輪的 **floor 常數過時 2 格**——「拆掉一支掃描器就紅」目前要拆 3 支才紅

```
FAIL: test_the_two_floors_are_not_themselves_stale (TestR74IronLawMechanismAccounting)
AssertionError: 2 not less than or equal to 1 :
  _IRON_LAW3_COVERED_FLOOR=19 落後現值 21 共 2 格（上限 1）
  ⇒ 「拆掉一支掃描器就紅」需要拆 3 支才紅。修法：把該常數重釘為 21
```
**為什麼是問題（架構層級，且與 ARCH-02 同源）**
1. 本輪**確實把鐵律三大表的分子由 19 推到 21**（我在 `git diff CLAUDE.md` 實見 `shell=True` 那一列由「**無機械物**」改成指名 `test_shell_portability_contract_r85.py`；另一格為 P12 的 exe-argv 列）。**分子增列是本輪的真實貢獻，我不否認**。
2. **但 floor 沒有跟著重釘** ⇒ 那道「拆掉掃描器就紅」的鎖**現在鬆了 2 格**。這正是 CLAUDE.md 自己寫的病：「餘裕就是日後無聲加回去的破口」。
3. 🔴 **與 ARCH-02 合看才是完整的故事**：本輪在**分子端**加了 2 格（其中 exe-argv 那一格的 scanner **根本沒接進 M5 矩陣**），卻在**棘輪端**留下 2 格鬆動。⇒ **治理數字向上、實際攔阻力向下**，兩者方向相反而表徵都是「有進展」。
**修法草案**：`_IRON_LAW3_COVERED_FLOOR` 重釘為 **21**（訊息逐字給了修法）。**須與 ARCH-02 的接線同一次做完**，否則接線後分子還會再動。
**持有面**：常數 `_IRON_LAW3_COVERED_FLOOR`（`tools/tests/test_doc_loc_baseline_freshness_r60.py`）／史料＝`CLAUDE.md` 鐵律三大表本身／消費端＝同檔 2 支測試。🔴 **跨 2 支檔 ⇒ 鐵律七，收尾單人窗口。**

---

### ARCH-13（major）掃描面鎖**把探針寫進自己要掃的那個面** ⇒ 並行測試下必然互踩（本輪 7 紅中有 1 支是它）

**現查指令與輸出**
```
$ grep -n "_scan_surface_probe" tools/tests/test_platform_utils_dedup.py
588:  probe_dir = _REPO_ROOT / f"_scan_surface_probe_{os.getpid()}"

$ (全套 discover 中)  FAIL: test_sdd_latest_helpers_defined_only_in_sdd_latest
AssertionError: 掃描面內的 .py 有 1 支讀不到 …
  ['_scan_surface_probe_44230/probe_platform_helper.py（FileNotFoundError）']

$ (隔離單跑同一支)  rc=0  OK          ← 對照組：非並行時通過
```
**成因**：探針目錄建在 `_REPO_ROOT`（即掃描面本身），以 **PID** 命名。兩個 `unittest discover` 並行時，
A 的探針檔會落進 B 的掃描面；A 掃完刪除 ⇒ B 在 `read_text()` 撞 `FileNotFoundError` ⇒ B 假紅。
（本輪確有兩個 discover 並行：我的 PID 45592 與另一個 agent 的 46659。）

**為什麼是問題**：這支鎖的錯誤訊息會把成因**指向錯誤的方向**——它逐字建議「git mv 進行中／已 rm 未 stage（先完成或 `git checkout --`）」。
🔴 **在四方複審這種必然並行的場景下，它會誘導收尾窗口去跑 `git checkout --`，而那是 CLAUDE.md 鐵律五明文阻斷的毀滅性指令**（R83 事故的同一個動詞）。**一個假紅把人推向一個會清空工作樹的指令**，這比假紅本身嚴重。
**修法草案**：探針改建在 `tempfile.mkdtemp()`（掃描面之外）；若判準本身要求探針在樹內，則改用 `os.getpid()`+獨佔鎖並把該檔**加進掃描器的排除清單**。同時把錯誤訊息中的 `git checkout --` 建議移除。
**持有面**：`tools/tests/test_platform_utils_dedup.py`（`:588` 探針建立點 ＋ `:248` `_scan_repo_py_for` 的錯誤訊息，同檔）。

---

## §4 blocking 清單（收尾窗口據此修）

| # | 標題 | 持有面（常數／史料／消費端） | 可否派並行包 |
|---|---|---|---|
| **ARCH-01** | 護欄層淨額宣稱 0、實為 +458；3 支測試紅 | 常數 `_FROZEN_GUARD_LINES`／史料 `_GUARD_LINES_REPIN_LOG`＋指紋／消費端 3 支測試 — **皆在 `tools/tests/test_adr_xplat001_c1c2_lock.py`**；連帶 2 支 doc | ❌ 收尾單人窗口（須在**所有包停工後**） |
| **ARCH-02** | `scan_foreign_exe_argv` 未接線，M5 接線率 8/11→8/12 | 消費端 `_injection_criteria()`＋史料 `_XPLAT_INJECTION_CORPUS`（`test_platform_neutral_paths.py`）／連帶常數 `_FROZEN_GUARD_LINES`（**另一支檔**） | ❌ 跨兩支檔，鐵律七 ⇒ 收尾窗口，且**必須與 ARCH-01 同一次做完** |
| **ARCH-03** | 三份平行 CONDITIONAL production 不可達，本輪一行未動 | 生產 `kernel.py`／`wiring.py`／`services/mutation/**`／`playbook_runner.py`／`mutation_applier/**`；契約 `.importlinter` Rule 3+6；消費端 27 個 test 建構點；常數 `check_loc_budget.py` | ❌ 淨減法＝跨檔參照稅 ⇒ 收尾單人窗口。**建議本輪只做階段 0（fail loud），階段 1 排 R86** |
| **ARCH-11** | E501 債棘輪上升 140>139 | 常數＋消費端同住 `tools/tests/test_subprocess_encoding_hygiene.py`；違規行在本輪新增的 `tools/tests/*.py` | ⭕ 可單包（折行即可），但**須在 ARCH-01 重釘之前**做完 |
| **ARCH-12** | `_IRON_LAW3_COVERED_FLOOR=19` 落後現值 21 共 2 格 | 常數 `tools/tests/test_doc_loc_baseline_freshness_r60.py`／史料＝`CLAUDE.md` 鐵律三大表／消費端＝同檔 2 支測試 | ❌ 跨 2 支檔（鐵律七）⇒ 收尾窗口，**須與 ARCH-02 同一次做完** |

🔴 **收尾順序（有相依，不可任意併行）**
`ARCH-11（折行）` → `ARCH-02（接線＋翻 2 個 flag）` → `ARCH-12（floor 重釘為 21）` → **最後**`ARCH-01（在所有包停工後重釘 _FROZEN_GUARD_LINES ＋ 指紋）`。
理由：前三項都會改動 `tools/tests/**` 的行數 ⇒ 任何一項在 ARCH-01 之後做，都會讓剛重釘好的護欄層總量再次失準（＝本輪 ARCH-01 的成因原樣復發）。

---

## §5 我沒能查到的（誠實劃界）

1. **根層 unittest 全套已跑完**（`Ran 3284 / FAILED (failures=7, skipped=44) / EXIT=1`），但**該次執行與另一個 agent 的 discover 並行**（PID 45592 vs 46659）⇒ 除已複驗的 ARCH-13 那一支外，**我無法排除其餘紅燈也含並行效應**（我只對 ARCH-01 的 3 支做了單檔複跑 rc=1，ARCH-11／ARCH-12 未單獨複跑）。收尾窗口應在**無並行**的情況下重跑一次再宣稱。
   （🔴 另註：`tools/run_root_unittests.py` 會在靜態標籤掃描階段短路 ⇒ 不可用它的「沒有 FAIL 行」當通過憑證。）
2. **AutoClaude pytest 全套未跑**。P7／P11 改動了生產碼（`execution/evaluator.py` +114、`core/hookspec.py` −15、`main.py`、`wiring.py` 等），我**沒有**跑 `python -m pytest tests/ -q`，因此**無法**對「AutoClaude 側零退化」表態。
3. **AISDLC_SDD 側（P6）我完全沒查**。「`agent_template_lint` 由 1 桶擴到 4 桶／幽靈依賴 199→1／4 支 fail-open lint 治本」全部是**未經我驗證的自陳**。
4. **Windows 面全部未驗**。ARCH-02 中 `b8-schtasks`／`b11-powershell-shell` 的危害性是**靜態推論**；本輪在 macOS，`_ps_engine.py`／PS 5.1 相關結論一律未真機驗證。
5. **P10（ADR-XPLAT-007／根 `.env`／R-8→P-1）未查**。
6. **ARCH-06 的分桶普查是啟發式**（first-match、只看引號內路徑字面），量級可信、**小數不可引用為常數**；且未涵蓋 `tools/lib`／`tools/*.py`／`.claude/hooks` 三層（只做了 `tools/tests`）。
7. **ARCH-03 階段 1 的實際風險我只做了靜態盤點**（27 個建構點／2 條契約／equivalence 快照），**沒有實際試刪**（唯讀複審，且淨減法會撞跨檔參照稅）⇒ 真實成本可能高於我的估計。

---

*本檔由 R85 Architect 獨立複審產出；除本檔外未寫入任何檔案，未執行任何 git 寫入指令。*
