# PRD — strutils 字串工具庫（AutoSDD_improving_95 A 軌橋接端到端真跑用）

> **用途**：本 PRD 為 improving_95 A 軌「PRD→playbook 橋接端到端真跑」之**輸入樣本**。刻意小型，
> 使 Archy agent 拆解出的「專案→目標→任務」三層結構有界、且 execution_item 可被機械驗證
> （規格步以 keyword、程式步以 pytest）。**非正式產品**，僅為驗證橋接鏈通而設計。

## 1. 願景

提供一個零依賴的純函式 Python 字串工具庫 `strutils`，給其他模組做常見字串處理。
強調「小而正確」：每個函式行為明確、可單元測試完全覆蓋。

## 2. 功能範圍

### F-001 slugify（轉 URL slug）
- 將任意字串轉為小寫、空白與底線轉連字號 `-`、移除非 `[a-z0-9-]` 字元、合併連續連字號、去頭尾連字號。
- 範例：`slugify("Hello World!") == "hello-world"`；`slugify("  Foo__Bar  ") == "foo-bar"`；`slugify("a---b") == "a-b"`。

### F-002 truncate（截斷加省略號）
- 將字串截斷至最多 `n` 個字元；若超長，截到 `n-1` 字元並補一個 `…`（單一 Unicode 省略號，總長 = n）。
- `n` 必須 ≥ 1；`n < 1` 時 raise `ValueError`。
- 範例：`truncate("hello", 10) == "hello"`（未超長原樣回傳）；`truncate("hello world", 8) == "hello w…"`（總長 8）；`truncate("x", 1) == "x"`。

## 3. 非功能需求

- **NFR-001**：純函式、零第三方依賴（只用標準庫）。
- **NFR-002**：每個函式有 pytest 單元測試，邊界案例（空字串、超長、最小 n）全覆蓋。

## 4. 里程碑（給 Archy 拆解的提示）

- **M1 規格凍結**：確認 slugify / truncate 行為契約（SCG-0~1）。
- **M2 實作至綠**：以 TDD（先測後實作）逐函式建至 pytest 全綠（SCG-4）。

## 5. 通過標準

- `pytest test_strutils.py -q` 全綠（slugify + truncate 含邊界案例）。
- 行為符合 §2 範例。
