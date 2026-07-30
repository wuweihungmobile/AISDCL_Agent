# Cross-Platform R61 Architect 收輪證據

> HEAD（動工前）`ad92e37`；量測時點 2026-07-30，工作樹 `tools/tests/` 量測面乾淨
> （`git status --porcelain -- tools/tests/` 空輸出）。本檔記錄本輪**唯一實作**：
> ADR-XPLAT-002 Phase 1-B（全量）＋ Phase 1-C（最小可行切片）。完整裁決理由見
> `docs/04_planning/ADR/ADR-XPLAT-002-platform-surface-reduction.md`（R61 更新段）。

## 1. 現測數字（改前 → 改後）

| 指標 | 改前 | 改後 | 指令 |
|------|------|------|------|
| UEP（`_EXEMPT_PAIRS` + `_TLC_TRACK_ENROLLED`） | 8 | **6** | `python -c "import sys;sys.path.insert(0,'tools');import check_script_parity as P;print(len(P._EXEMPT_PAIRS)+len(P._TLC_TRACK_ENROLLED))"` |
| `_THINNESS_ENROLLED` | 5 | **7** | 同上模組 |
| `_PINNED_SHA256` | 10 | **14** | `check_wrapper_thinness._PINNED_SHA256` |
| AC（六張登記表總和） | 42 | **46** | `check_script_parity.py --print-collapse` |
| `tools/tests/*.py`（護欄層 GLC，報表非閘門） | 56 支／28,118 行 | 56 支／**28,194 行**（**檔數不變，行數 +76**） | `ls tools/tests/*.py \| wc -l`；`python -c "…splitlines()…"` |
| AutoClaude 生產碼（`check_loc_budget`） | total=20361 | total=20361（**不變**） | `python AutoClaude/tools/check_loc_budget.py` |

🔴 **R61 round 1 Architect 複審訂正**：原文誤寫「行數不變」，經複審親測為假——+76 行
來自擴充既有 `test_check_script_parity.py`（+70）／`test_check_wrapper_thinness.py`（+6）
兩支既有檔（`git diff --stat` 可核）。**檔數確實不變**（零新增 `tools/tests/test_*.py`，
符合 R60 round 3 訂正的「R61 開輪即禁止新增鎖檔、只准合併／刪除」模式），但比照 R60 的
誠實揭露紀律，行數增長不應寫成「不變」。

## 2. 做了什麼（合併/優化）

**ADR-XPLAT-002 Phase 1-B**（全量落地）：`AutoClaude/tools/install_git_hooks` 與
`AISDLC_SDD/scripts/install-hooks` 兩對腳本，由 `check_script_parity._EXEMPT_PAIRS`
（零守門的決策豁免，DEF-101-088 自 R11 起掛在此處）遷入 `_THINNESS_ENROLLED` ＋
`check_wrapper_thinness._PINNED_SHA256` 補 4 支 hash ＋ `_FORBIDDEN` 補 4 組並聯關鍵字
（沿用既有薄殼同款清單，非新判準）。四支腳本本體（`.sh`/`.ps1`）**零位元變動**——
業務邏輯本已下沉 `tools/git_hooks_install_common.py` 單一真相源，本輪只是把「無人守著」
升級為「hash 釘選 + 行數上限 + 業務樣板關鍵字並聯」。

**ADR-XPLAT-002 Phase 1-C（最小可行切片）**：`check_script_parity.py` 新增
`--print-collapse` CLI 分支，印出 UEP／AC／六張登記表長度。**不含**完整 1-C（tier 分類
重構、`_EXEMPT_PAIRS`/`_SINGLE_SIDED_EXEMPT` 值改為 `(tier, reason)` tuple）——延後理由
見下節。

## 3. 為何安全（風險評估）

1. **1-B 零程式邏輯變更**：`git status --porcelain` 顯示四支腳本本體無 diff；改動僅落在
   兩支既有登記表檔，且四支殼 raw 行數（50/65/40/42）皆 ≤ `MAX_LINES=100`，符合 ADR §3.1
   納編前置條件。
2. **Dominance test（bug-injection）已實測**：在 `AISDLC_SDD/scripts/install-hooks.ps1`
   注入 `foreach ($x in @(1,2,3)) { Write-Host $x }`，`check_wrapper_thinness.py` 正確回報
   hash 不符**與**禁止關鍵字 `'foreach ('` 命中（rc=1，兩訊號並聯皆紅）；以 Edit 逐行改回
   （未用 `git checkout --`），復驗 `git diff` 零差異、rc 復綠。
3. **1-C 切片未改動既有資料型別**：`--print-collapse` 純附加印出邏輯，不改動
   `_EXEMPT_PAIRS`/`_SINGLE_SIDED_EXEMPT` 現有的字串型別，故不牽動既有依賴這些值為
   字串的測試（`test_check_script_parity.py:248` 的 `.strip()`、
   `test_onboarding_parity_interlock.py:105/114` 的字串比對）。
4. **未做的部分（DEF-101-561 四處合併）已評估、非疏漏**：親讀四份原始碼後確認
   `_has_ssot_guard`（bash 位置錨定正則）／`_ps1_code_lines()`（PS1 只剝整行）／
   `check_wrapper_thinness._normalize`（PS1 整行+區塊+去空行）／`_ps_engine` 相關掃描器
   （其實是 Python AST 掃描，非文字剝除）四者語意互不相同，強行合併需通過 ADR §4.2 rule 3
   的 dominance test（逐一構造既有斷言的突變證明新機制同樣抓得到），風險/效益不成比例，
   且不移動任何本 ADR 已閘門化的指標（UEP/AC/SDS）。裁決記錄於 ADR 本輪更新段。

## 4. 驗證（本回合真實跑出的輸出，非推測）

```
$ python tools/check_wrapper_thinness.py
✅ wrapper 薄殼守門通過（14 支殼 hash 釘選 + 行數上限皆正常）
REAL_RC=0

$ python tools/check_script_parity.py
✅ run_tlc_tracks（LATEST FSM 軌錨點集合）：6 個 step 標籤一致
✅ pytest 釘選一致：三處皆 pytest==9.1.1
✅ git longpaths 旗標鎖：兩側皆含 '-c core.longpaths=true'（macos 1 處／windows 2 處）
✅ thinness 交叉鎖：7 對薄殼登記與 14 支 hash 釘選鍵集合一致
✅ 腳本註冊完整性：13 對 + 18 支單邊皆已納管（遞迴掃描 3 棵 SSOT 樹 + LATEST tools）
✅ 雙平台腳本對等檢查通過
REAL_RC=0

$ python tools/check_script_parity.py --print-collapse
UEP=6
AC=46
THINNESS_ENROLLED=7
PINNED_SHA256=14
EXEMPT_PAIRS=5
SINGLE_SIDED_EXEMPT=18
TLC_TRACK_ENROLLED=1
MIN_EXTRACT_COUNTS=1
REAL_RC=0

$ python -m pytest tools/tests/ -q
1065 passed, 10 skipped, 1 warning, 367 subtests passed in 93.83s
（改動前基線：1059 passed, 10 skipped, 366 subtests；本輪新增 6 個測試於既有檔
test_check_script_parity.py／test_check_wrapper_thinness.py，零新增測試檔）

$ cd AutoClaude && python -m pytest tests/ -q
3767 passed, 208 skipped, 1 warning in 69.07s
REAL_RC=0（無 failed）

$ cd AutoClaude && PYTHONUTF8=1 lint-imports
Contracts: 8 kept, 0 broken.
REAL_RC=0

$ python AutoClaude/tools/check_loc_budget.py
[check_loc_budget v2-tiered] total=20361 baseline=17032 cap=20438 violations=0
REAL_RC=0
（根層無 tools/check_loc_budget.py——ADR §2.6 已載明該檔只存在於 AutoClaude/tools/，
本輪複驗此事實仍成立：`ls tools/check_loc_budget.py` → No such file or directory）

$ python -m pytest tools/tests/test_defect_id_reference_integrity.py tools/tests/test_archive_defect_log.py -q
105 passed, 111 subtests passed
（本輪編輯缺陷帳本時一度誤植一個未跳脫的字面 `|` 導致 20 個測試失敗，
已定位並修正——見下節「修過程中的一個插曲」）
```

## 5. 修過程中的兩個插曲（誠實記錄）

**插曲一**：編輯 `docs/06_quality/AutoSDD_Defect_Log.md` 為 `DEF-101-561` 追加狀態時，
第一次編輯把新文字接在該列既有的欄位結束 `|` **之後**而非**之內**，等同多插入一欄，
導致 `test_archive_defect_log.py` 的 row-arity 硬閘（斷言每列切出的欄數與表頭一致）
當場攔下（20 個測試失敗，錯誤訊息逐字列出「切出 10 個切片 ≠ 表頭 9 個」）。以 Edit
把該處的 `|` 改為句號後複驗，20 個測試全部轉綠——本輪自己的帳本編輯被自己的閘門真實
攔下並修正，非事後宣稱。

**插曲二**：新增本證據檔（`CrossPlatform_R61_Architect_Evidence.md`）後，
`tools/tests/test_check_defect_log_crossref.py` 13 個測試轉紅——本檔檔名符合
`docs/06_quality/CrossPlatform_*.md` 姊妹治理文件命名慣例，卻未登記進
`tools/check_defect_log_crossref.py::_GOVERNANCE_DOCS`（該常數同時控管體積守門與
`archive_defect_log.py` 的指針稽核）。已在該常數補登本檔一筆，複驗
`test_check_defect_log_crossref.py` 76 passed、`python tools/check_defect_log_crossref.py`
與 `python tools/archive_defect_log.py --check` 皆 rc=0。

## 6. 缺陷帳本異動

- `DEF-101-561`（既有列，追加狀態）：記錄本輪對①②（四處合併／AST 剝除層）的評估結論
  ——親讀四份原始碼後判定語意互不相同、不安全合併，理由詳列；③（邊際效益量測）記錄
  本輪新增鎖檔數＝0。
- `DEF-101-614`（新增列，fixed）：記錄 Phase 1-B 全量落地 + Phase 1-C 最小可行切片，
  含 UEP/AC 前後數字、bug-injection 實測、延後 1-C 全量的具體 grep 依據。
- 帳本主檔大小：229,307 bytes（硬閘 262,144 bytes，餘裕約 32KB）。

## 7. 未做的部分（留給 R62，非含糊「下輪再看」）

Phase 1-C 全量（(a)(b)(d)）：`_EXEMPT_PAIRS`/`_SINGLE_SIDED_EXEMPT` 值由字串升級為
`(tier, reason)` tuple、4 組異名對等品字典化、tier3/tier4 reason 關鍵詞斷言。**具體解除
判準**：
1. 逐一走過 `_EXEMPT_PAIRS`（5 項）+ `_SINGLE_SIDED_EXEMPT`（18 項）共 23 個條目，
   為每項指定 tier。
2. 同步改寫至少 3 支既有測試檔對字串型別的依賴：
   `tools/tests/test_check_script_parity.py:248`（`.strip()`）、
   `tools/tests/test_onboarding_parity_interlock.py:105/114`（`for key, why in
   ...items()` 字串比對）、`tools/tests/test_schedule_capability_parity.py`（提及
   `_EXEMPT_PAIRS` 語意的註解）。
3. 完成後 `--print-collapse` 才能印出逐對 tier/reason（本輪只印六張表的總量）。
4. UEP／AC 棘輪化（`python tools/check_script_parity.py` 的判準值不得被靜默調升）——
   照 `tools/tests/test_adr_xplat001_c1c2_lock.py::TestShrinkOnlyRatchet` 的形狀
   （`git show HEAD:<鎖檔>` 取上一版常數機械比對），不要照 `check_loc_budget.py`
   （ADR §2.6 已證那不是棘輪）。

`ADR-XPLAT-002` Phase 2（run_tlc 薄殼化、ci-gate fallback 刪除等）維持原判：
Phase 2-B 需使用者/PM signoff，本輪未觸碰。
