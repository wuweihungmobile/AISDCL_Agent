# Cross-Platform R61 SA/QA 收輪證據

> HEAD（動工前）`ad92e37`；本檔記錄 R61 SA/QA 混合角色的兩件事：① 全專案八維
> （Scan-A~H）掃描結果；② 根治 `DEF-101-573` 殘留的「並行下收集數少 12 支」懸案。
> 量測環境：Windows 11、本機 `D:\CursorProject\AISDCL_Agent`。

## 1. 八維掃描結果：本輪零新缺陷

依 `docs/06_quality/CrossPlatform_Scan_Dimensions.md` 的 Scan-A~H 方法論，對 monorepo
（`AutoClaude/`、`AISDLC_SDD/`、根層 `tools/`、`.github/workflows/`、git hooks）做一輪
掃描，逐項確認**非**過去 60 輪已知/已修過的舊案（grep 帳本主檔＋34 份 archive 交叉核對）。
結論：**本輪掃描沒有找到新的跨平台相容性缺陷**。已排查並確認為非新案或非缺陷的候選：

- Windows/PowerShell 與 Git Bash 兩種載具對根層治理指令（`check_script_parity.py`／
  `check_wrapper_thinness.py`）跑出**逐字相同**輸出（見 §3 驗證區塊）——無載具落差。
- `windows-compat-ci.yml`／`macos-compat-ci.yml` 的 `paths:` 只列 `AutoSDD_Defect_Log.md`、
  未列姊妹治理文件（`CrossPlatform_*.md`）：查證 `root-infra-ci.yml`
  **無 `paths:` 過濾**（每次 push/PR 皆跑），故 `check_defect_log_crossref.py`／
  `run_root_unittests.py` 的覆蓋不受此影響，非缺口。
- 全 repo grep 未發現任何 tracked 檔含本機專屬絕對路徑（`D:\CursorProject`／
  `C:\Users\wuwei` 等）。
- Architect 本輪對 `check_script_parity.py`／`check_wrapper_thinness.py` 的新增內容
  （`_THINNESS_ENROLLED`／`_PINNED_SHA256`／`_FORBIDDEN`／`--print-collapse`）逐項覆核：
  hash 長度、CLI 分支、既有型別相容性皆正確，無新增缺陷。

**方法論誠實揭露**：60 輪高強度多角色複審後，單輪掃描的邊際產出天然遞減；本輪選擇
不虛構低價值發現湊數（見專案紀律「不要無謂延後／不編造工具輸出」），把主力投入
第 2 節的 `DEF-101-573` 根因調查。

## 2. `DEF-101-573` 根治：「收集數少 12 支」根因確認為已消失，非活躍缺陷

### 2.1 原始懸案

`AutoSDD_Defect_Log.md` DEF-101-573 列記載：與 6 個 python 行程並行時
`tools/run_root_unittests.py` 只收集 **894** 支且 `TestMain` 4 支翻紅，獨占重跑皆
**906** 支、rc=0；三個已知並行假紅成因（`__pycache__` 位元碼競態／就地突變 tracked
生產碼互踩／機器級具名 mutex）皆無法解釋這「少 12 支」的現象，R60 收輪時交棒 R61。

### 2.2 既有線索（R60 round 3 checkpoint，commit `796c7a6`）

`tools/run_root_unittests.py` 的 `inventory_fingerprint()` docstring 記載 R60 曾做
115 次量測（並行度 0~8），**零違反**「同一磁碟指紋 ⇒ 同一收集數」；結論是三個歷史數字
894/906/916 實為 `865 + {29,41,51}`——同一支檔（`test_check_defect_log_crossref.py`）
被另一個並行修復包從 29 支逐步擴充到 51 支的三個時間切片，**不是 race**。但 R60 收輪
commit（`216aa4e`）的 `DEF-101-573` 列**仍寫「另一半是獨立問題，狀態不變，交 R61」**——
本節不採信這段歷史宣稱，親自重新驗證。

### 2.3 本輪獨立複驗（真實命令與輸出）

**(a) 字面重現原始情境**——6 個 `run_root_unittests.py` 完整行程並行，且**先清空
`tools/`／`AutoClaude/` 全部 `__pycache__`**（排除位元碼快取殘留變因）：

```
$ find tools -name "__pycache__" -type d -exec rm -rf {} +
$ for i in 1 2 3 4 5 6; do python tools/run_root_unittests.py > out_$i.txt 2>&1 & done; wait
run 1: ✅ 發現 1075 個測試（下限 1069）／指紋 7c1aaffef133／OK (skipped=10)
run 2: ✅ 發現 1075 個測試（下限 1069）／指紋 7c1aaffef133／OK (skipped=10)
run 3: ✅ 發現 1075 個測試（下限 1069）／指紋 7c1aaffef133／OK (skipped=10)
run 4: ✅ 發現 1075 個測試（下限 1069）／指紋 7c1aaffef133／OK (skipped=10)
run 5: ✅ 發現 1075 個測試（下限 1069）／指紋 7c1aaffef133／OK (skipped=10)
run 6: ✅ 發現 1075 個測試（下限 1069）／指紋 7c1aaffef133／OK (skipped=10)
```

6/6 完全相同、零差異、零 failed。這是 DEF-101-573 原始報告的字面情境（「6 個 python
行程並行」），在乾淨 `__pycache__` 下重現，結果與獨占跑（單獨執行同一命令，同樣
1075／`7c1aaffef133`／`OK (skipped=10)`）逐位元相同。

**(b) 輕量探針補樣**——只做 `discover_suite()`＋`inventory_fingerprint()`（跳過實際
執行，隔離「收集」與「執行」兩個機制），在兩種額外負載情境各採 8 個並行樣本：

```
情境一（8 行程並行、無額外負載）：
  8/8 → COUNT 1075 FILES 53 FP 7c1aaffef133（零差異）

情境二（8 行程並行 ＋ AutoClaude 全套 pytest 同時起跑，清空雙邊 __pycache__）：
  背景負載：cd AutoClaude && python -m pytest tests/ -q → 3767 passed, 208 skipped in 68.25s
  8/8 探針 → COUNT 1075 FILES 53 FP 7c1aaffef133（零差異）
```

合計本輪 22 個並行樣本（6 全套 + 8 探針 + 8 探針+重負載），**逐筆相同、零違反**，
與 R60 round 3 的 115 次量測結論一致：`unittest` discovery 機制本身**不是**非決定性
來源；「收集數不同」的唯一觀測成因是磁碟狀態本身在不同時間點不同（被另一個並行
修復包編輯中的檔案），不是 collection 過程的 race。

**(c) 獨立核對「`TestMain` 4 支翻紅」那一半**——`tools/tests/test_check_defect_log_crossref.py`
的 `_ledger_text()` fixture docstring（L46~51）已載明機制：R60 為
`status_first_word_problems()` 新增「必須抽到《格式定義》權威散文」的 fail-loud 判準時，
沿用舊 fixture（未帶該句散文）的 `TestMain` 測試會觸發「抽不到權威散文」錯誤——**與
並行完全無關**，是一次性的 fixture 落後於主檔演化，且已在該檔演化中修正。本輪實測：

```
$ python -m unittest tools.tests.test_check_defect_log_crossref.TestMain -v
...
Ran 11 tests in 0.044s
OK
```

11/11 全綠，確認此症狀不會再復發。

### 2.4 結論

DEF-101-573 殘留的「收集數少 12 支」**不是待修的程式缺陷**：
1. Collection 機制本身無 race（22 樣本本輪 + 115 樣本 R60，合計 137 個樣本零違反）。
2. 原始數字差異的成因是「跨時間點量測同一份持續被編輯的磁碟狀態」，屬量測方法論
   缺口（`inventory_fingerprint()` 已在 R60 補上指紋比對，消除此類誤判空間）。
3. 「TestMain 4 支翻紅」的成因是一次性 fixture 落後，與並行無關，現況已修正
   （11/11 綠）。

兩個成因皆已在 R60 收輪前消失，本輪未變更任何生產碼即完成根治確認（純驗證/根因
排除，無需 code diff）。**是否可將 DEF-101-573 標記 closed 並歸檔，或仍要求下一輪
再排一次獨立驗證，留給主控裁示**——本檔不擅自把帳本狀態改判為 `fixed`/`wontfix`，
帳本列已如實記錄本輪發現與待決事項。

## 3. 本機真實驗證（Windows 11，rc 與數字皆為本回合實測）

```
$ python tools/check_script_parity.py            → rc=0（Bash 與原生 PowerShell 兩載具逐字相同輸出）
$ python tools/check_wrapper_thinness.py          → rc=0（14 支殼 hash 釘選＋行數上限皆正常）
$ python tools/check_defect_log_crossref.py       → rc=0（98 筆有效狀態紀錄、4 份掃描目標無矛盾）
$ python tools/archive_defect_log.py --check      → rc=0（帳本保全稽核通過，35 檔／726 個 ID）
$ python AutoClaude/tools/check_loc_budget.py     → rc=0（total=20361 baseline=17032 cap=20438 violations=0）
$ cd AutoClaude && python -m pytest tests/ -q     → 3767 passed, 208 skipped, 1 warning in 68.25s
$ cd AutoClaude && PYTHONUTF8=1 lint-imports       → Contracts: 8 kept, 0 broken
$ cd AISDLC_SDD && bash scripts/ci-gate.sh        → 本機 CI 閘門全數通過；逐軌計數 AISDLC_SDD_v0.01:1478
                                                      AISDLC_SDD_v0.30:1747 scripts/tests:249
$ python tools/run_root_unittests.py（獨占跑）    → ✅ 發現 1075 個測試（下限 1069）／OK (skipped=10)
```

全部 rc=0，無 failed。`tools/check_defect_log_crossref.py`／`archive_defect_log.py --check`
在本檔＋帳本主檔新增內容後仍通過，確認本輪對帳本的編輯未破壞保全稽核。

## 4. 缺陷帳本異動

- `DEF-101-573`（既有列，追加狀態）：記錄本輪根因複驗結論（§2），不改變既有狀態首詞，
  留給主控裁示是否可歸檔。
- 本檔已登記進 `tools/check_defect_log_crossref.py::_GOVERNANCE_DOCS`（符合
  `CrossPlatform_*.md` 姊妹治理文件命名慣例，登記面即刻補上避免重演
  SA-R60R3-01「新建證據檔兩張清單都沒進」路徑）。
