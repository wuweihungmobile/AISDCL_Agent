# PS1 Complexity Checklist（ADR-SD09-010 §5 W1）

> **適用範圍**：`tools/run_local_nightly.ps1` 及其他 nightly 採集 / 取證鏈 ps1 腳本。
> **觸發時機**：PR 新增 / 修改 ps1 區塊時，reviewer 對照本 checklist 判斷是否須建 Python helper SSOT。

## 三條觸發條件（任一命中即建議 helper 化）

| # | 觸發條件 | 範例 |
|---|---------|------|
| 1 | 解析外部工具 stdout / stderr 混雜輸出（JSON / regex marker section / table parsing）| ps1:415-441 解析 `ac4_progress_check.py --json` 混雜 stdout(JSON)+stderr(warning) |
| 2 | 跨 stage 累計數字寫入 jsonl（如觀察期 #1/#2/#3 jsonl record）| ps1:607-616 jsonl line count |
| 3 | bitmask / regex marker section 解析（exit code bitmask / `--- xxx ---` 邊界）| ps1:337-358 mutmut counts marker section parsing |

**補充**：≥ 4 條件分支且涉及外部輸入 → 建議拆 helper；trivial mapping → 不需。

## Helper SSOT 規範（建立後必滿足）

- ✅ Helper 為 Python pure function（無 side effect；可單元測試）
- ✅ Helper LOC ≤ 100（plugin_entry tier 半量；強制低門檻）
- ✅ Helper ≥ 4 case unit test（與分支數 ≥ 1:1 對應）
- ✅ Helper docstring 標明對應 ps1 行號 + 同步紀律（範例：`tools/ac4_nightly_alert_parser.py:1-13`）
- ✅ ps1 端 inline 呼叫 helper（`& python tools/<helper>.py args`），**不可重複實作邏輯**
- ✅ ps1 變動觸發 helper 同步更新 + 重跑對應 unit test

## 既有 helper 範例

| Helper | LOC | Test case | 對應 ps1 區塊 |
|--------|-----|-----------|-------------|
| [tools/ac4_nightly_alert_parser.py](../../tools/ac4_nightly_alert_parser.py) | 134 | 16 | ps1:415-441 F2 區塊（OK/ALERT/stderr/WARN）|
| [tools/mutmut_counts_parser.py](../../tools/mutmut_counts_parser.py) | 97 | 7 | ps1:337-358 mutmut counts marker section |

## Reviewer 操作流程

1. PR diff 含 ps1 新增 → 對照三條觸發條件；命中 → 標 `requires-ps1-helper` label
2. PR author 補建 helper + ≥ 4 case unit test；既有 ps1 改動 grandfather clause 不溯及

## 候選 ps1 區塊清單（W2~W3 評估）

| # | 區塊 | 行號 | W1+ 狀態 |
|---|------|------|---------|
| 1 | F2 ac4 alert parser | 415-441 | ✅ 已 helper 化（Round 9 P2-R9-1）|
| 2 | mutmut counts marker section | 337-358 | ✅ **已 helper 化（W1 ADR-SD09-010）** |
| 3 | Container 選擇 + pg_isready retry | 199-246 | 🟡 W3 評估（外部 docker exec，不易 mock）|
| 4 | mutation Stage 1 pipeline 頭尾 | 270-359 | 🟡 W2 評估（核心 docker run 不易 mock）|
| 5 | drift_log 表 + severity query | 511-566 | 🟡 W3 評估（外部 psql exec，不易 mock）|
| 6 | END observation progress jsonl count | 607-616 | ⏭️ 不需治理（純 IO 統計，trivial）|

---

**版本**：v1.0 2026-05-25（W1 ADR-SD09-010 §5 W1 必做交付）| **長度約束**：≤ 50 內容行
