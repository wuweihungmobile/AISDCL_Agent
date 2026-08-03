# ADR-SD09-009 — mutmut suspicious 半確定性結果處理政策

| 項目 | 內容 |
|------|------|
| 編號 | ADR-SD09-009 |
| 狀態 | **ACCEPTED v1.2 — 2026-05-25 PM 拍板選項 A（suspicious 0.5 半 kill + ±2pp）+ 2026-05-28 PM 拍板 §11 等價變異天花板 / 76% 真實水位（R38）+ 2026-05-29 R47 audit §11.6 unique sha 源碼演進閘門訂正** |
| 提出者 | Architect + SA + SD 三方獨立研究（SD_09 W3 Round 11 派工 agent）|
| 提出日期 | 2026-05-25 |
| 對應議題 | SD_Improving_09 議題 B + 觀察期 #1 — mutmut suspicious 半確定性導致 kill_rate bounce |
| 相依 ADR | [ADR-SD08-002](ADR-SD08-002-mutation-baseline.md) v1.0（分模組差異化目標 + 連續 7 次達標鎖定）/ [ADR-SD09-002](ADR-SD09-002-mutation-full-module-expansion.md) v1.0（全模組擴展策略）|
| CLAUDE.md 紀律 | #1（stage rc 必須區分真實失敗 vs 工具標準回報）/ #4（驗證鏡子自身要被驗證）/ #5（跨工具數字對齊 assertion）|

---

## 1. 背景

mutmut 2.4.x 對 timing-sensitive 程式碼點位（如 token_guard 計時 / sleep / lock）存在「半確定性」狀態：**同一 mutant 在不同 run 可能被歸為 `suspicious` 或 `killed`**。SD_09 W3 Round 9~11 連續 3 次 nightly 真實採證：

| Round | Nightly run | Killed | Survived | Timeout | Suspicious | Skipped | kill_rate |
|-------|-------------|--------|----------|---------|------------|---------|-----------|
| **R9** | 第 4 跑（2026-05-25 f3b8a12）| 104 | 38 | 0 | **7** | 0 | **69.80%** |
| **R10** | 第 5 跑（2026-05-25 72ef7a3）| 107 | 38 | 0 | **4** | 0 | **71.81%** |
| **R11** | 第 6 跑（2026-05-25 d29e226）| 111 | 38 | 0 | **0** | 0 | **74.50%** |

**現象**：3 次 nightly 之間 7 個 suspicious 全部 bounce 回 killed（7→4→0），同時 survived 與 timeout 完全穩定（38 / 0），證實：

1. **suspicious 是 mutmut 對 timing 不確定 mutant 的標籤**，非真實 survived；
2. **suspicious 計入分母（依現行 [calc_kill_rate](../../tools/mutation_baseline_lock.py#L127)）導致 kill_rate 在 ±2~3pp 區間 bounce flake**；
3. 觀察期 #1「連續 7 次 ≥ 70%」門檻會被單次 bounce 觸發重計，**永遠不可能穩定達標**。

---

## 2. 問題本質

### 2.1 現行 kill_rate 計算（[mutation_baseline_lock.py:127-136](../../tools/mutation_baseline_lock.py#L127)）

```python
def calc_kill_rate(counts):
    denom = killed + survived + timeout + suspicious  # 排除 skipped
    return killed / denom
```

`suspicious` 計入分母但不計入分子 → 每次 bounce 影響 ~0.67pp（單 mutant 在 149 total 中佔比）。當 suspicious 在 [0, 7] 區間飄動 → kill_rate 在 [69.80%, 74.50%] 飄動 → **跨越 70% threshold 邊界**。

### 2.2 對紀律 #1 的對應

紀律 #1 要求「stage rc 必須區分真實失敗 vs 工具標準回報」。mutmut 2.4.x exit code bitmask 已正確處理（`bit0=exception` 才算真 crash；suspicious 為觀察期預期）。但 **kill_rate 分子分母計算**未對應「suspicious 是半確定性」語意 → 等於把工具標準回報當失敗計入。

### 2.3 對紀律 #4 / #5 的對應

紀律 #4「驗證鏡子自身要被驗證」延伸：`should_lock` 的鎖定判定不能被 suspicious bounce flake 觸發重計，必須有對應 unit test 覆蓋「bounce 場景 → 仍鎖定」。紀律 #5「跨工具數字對齊」延伸：`mutation_analysis.py` 與 `mutation_baseline_lock.py` 對 suspicious 的處理必須同一語意。

---

## 3. 三方獨立研究（§7 詳細立論）

| 選項 | 一句話 | PD 估計 | 風險 | 業界對應 |
|------|--------|---------|------|---------|
| **A** | Suspicious 計為 0.5 killed 半 kill 分子 + ±2pp tolerance | 0.5 PD | 低（保留 mutmut 全部資訊） | Stryker `--ignored` 部分對應；PIT 無對應 |
| **B** | 同 mutant suspicious 連續 N 次才確認 survived（retry 機制） | 2 PD | 中（nightly 時間 ×N 倍） | mutmut 官方 `--rerun-all` 概念 |
| **C** | 完全忽略 suspicious（不計入分子分母） | 0.2 PD | 中（資訊損失但計算最穩定） | Stryker `--ignored` 預設行為 |

### 3.1 共識決議方向

三方研究**共識傾向選項 A**，理由：

1. **保留 mutmut 全部資訊**：選項 C 完全忽略 suspicious 等於忽略「mutmut 對該 mutant 有疑慮」的資訊；
2. **不增加 nightly 時間成本**：選項 B 需 rerun 同 mutant N 次，TokenGuard 7 個 suspicious × 全測 ~100s × 3 retry = 額外 35 min，超出 45 min 上限；
3. **半 kill 語意符合 mutmut 設計**：mutmut README 明示 suspicious 為「probably killed but timing-sensitive」→ 0.5 weight 為合理近似。

### 3.2 PM 拍板項（✅ ACCEPTED v1.0 — 2026-05-25）

✅ **本 ADR §3.1 三方研究共識已由 PM 拍板採納選項 A**（SD_09 W3 Round 14 PM Agent 拍板書，見 [SD09_W3_Round14_NextAction.md §3.1](../../05_development/SD09_W3_Round14_NextAction.md)；2026-05-25）。拍板理由 5 點：(1) 三方研究 100% 共識無分歧；(2) 解除觀察期 #1 的 suspicious bounce ±4.7pp 數學死結；(3) 半 kill 0.5 weight 符合 mutmut 工具語意；(4) 既有 `.mutation_history.jsonl` 早期紀錄 suspicious=0 → 三選項數學等價（無 backfill 風險）；(5) ±2pp tolerance 符合紀律 #6 雙軌制。

> **政策 vs 實作狀態釐清（避免讀者誤判）**：本 ADR 為**政策決策**，已 ACCEPTED v1.0。對應**程式實作切換**（`calc_kill_rate` → `(killed + 0.5×suspicious)/denom` + `should_lock` 加 `EXTRA_TOLERANCE=0.02`）原規劃為 W1 任務（Round 14 §3.1 T1-M1/M2/M3），**實際已於 SD_09 W1 同 PR（commit `0169b96`，2026-05-25）落地完成**，並附 ≥ 5 case 單元測試（`tests/tools/test_mutation_baseline_lock.py` + `tests/contract/test_mutation_baseline_lock.py`）滿足紅線 §5.4。即政策與實作均已就位；紅線 §5.1「PM 拍板前不變更」於拍板前確實未動，拍板後同 PR 落地，無違反。

---

## 4. 過渡實作（三選項共通框架）

無論 PM 選 A/B/C，本 ADR 落地後**立即實作雙軌觀察工具**，提供 PM 拍板資料；不影響現行 `should_lock` 判定（紅線 §5.1）。

### 4.1 雙軌觀察工具：`tools/mutation_baseline_lock.py --policy-preview`

新增 CLI 參數預覽三種 policy 下的 kill_rate：

```bash
$ python tools/mutation_baseline_lock.py token_guard \
    --log mutation_token_guard.log \
    --policy-preview
[Mutation policy preview] module=token_guard
  current  (susp 計分母)        : kill_rate=74.50% (lock=PASS @70%)
  option A (susp=0.5 半 kill)   : kill_rate=74.50% (lock=PASS; susp=0 本輪無差)
  option B (retry 3 次合併)     : kill_rate=N/A (需重跑 nightly)
  option C (忽略 susp)          : kill_rate=74.50% (lock=PASS; susp=0 本輪無差)
  -- 歷史對照（R9~R11）：
    R9: current=69.80% / A=72.15% / C=73.24%
    R10: current=71.81% / A=73.15% / C=73.79%
    R11: current=74.50% / A=74.50% / C=74.50%
```

### 4.2 不修改 `should_lock` 判定（紅線）

過渡期間 `should_lock` 仍以 current 計法判定鎖定；policy-preview 僅為 PM 觀察資訊。PM 拍板 A/B/C 後再切換主判定路徑。

---

## 5. 紅線（不可違反）

| 編號 | 紅線 | 對應紀律 |
|------|------|---------|
| 5.1 | **PM 拍板前 `calc_kill_rate` 不變更** — 過渡期間僅新增 `--policy-preview`，主判定路徑不動 | 紀律 #1 |
| 5.2 | **`.mutation_history.jsonl` 不 backfill / 重寫** — 過往 R9~R11 真實 counts 保留；新 policy 套用「自拍板日起」新紀錄 | 紀律 #3（PASS 聲稱必須引用 RunId log 行號）|
| 5.3 | **`mutation_baseline_lock.py` 與 `mutation_analysis.py` 必須同步切換** — 兩工具對 suspicious 處理須單一真相 | 紀律 #5 |
| 5.4 | **policy 切換必須有 ≥ 5 case 單元測試** — 涵蓋 bounce 場景 / 邊界 threshold / 三選項數學等價性 | 紀律 #4 |
| 5.5 | **±2pp tolerance（若選 A）不可單方面採用** — 必須由 PM 拍板（會放寬鎖定門檻；對三模組對稱影響：TokenGuard 70%→68% / GoalSynthesis 65%→63% / Coordinator 60%→58%；對齊 [tools/mutation_baseline_lock.py:34-46](../../tools/mutation_baseline_lock.py#L34) TARGETS SSOT）| 紀律 #6（採集寬鬆 vs 升級嚴格分軌）|

---

## 6. 採納路徑

| 階段 | 動作 | 負責 | 時程 | 狀態 |
|------|------|------|------|------|
| **PROPOSED v0.1** | 本 ADR 落地 + `--policy-preview` 工具實作 + 5 case 單元測試 | Architect（2026-05-25）| 本輪 W3 Round 11 | ✅ 完成 2026-05-25 |
| **REVIEW** | PM 看 policy-preview 對照 + 三選項決議 | PM（cut-off 2026-06-08；實際提前）| 2 週 | ✅ 提前完成（Round 14）|
| **ACCEPTED v1.0** | PM 拍板**選項 A** → 切換 `calc_kill_rate` 主判定 + 同步 `mutation_analysis.py` + 更新 ADR-SD08-002 §2.1 | PM Agent（拍板）/ Tech Lead（實作）| PM 拍板後 1 PD | ✅ **拍板 + 實作均完成 2026-05-25**（拍板見 Round14 §3.1；實作於 W1 PR commit `0169b96`）|
| **OBSOLETED** | 觀察期 #1 連續 7 次達標鎖定後 | — | TBD | ⏳ 待 #1 unique sha 源碼演進閘門（需 W1 active 改 token_guard 源碼；idle 期凍結不達標，見 §11.6）<br>🔴 **本格已被 ADR-SD09-013（2026-08-03 ACCEPTED）supersede**：閘門移為 W1 出場驗收，且括號內因果已被實查推翻；**baseline 實際已於 2026-07-22 鎖定（0.7071）**，見 §11.3／§11.6 註記|

### 6.1 PROPOSED 階段強制週報（沿用 ADR-SD09-008 §6.1）

> ✅ **本節已失效**：PM 已於 2026-05-25（Round 14）提前拍板選項 A，未觸發 cut-off 2026-06-08 過渡寬限。以下為原 PROPOSED 期間的過渡保護條款，保留供歷史脈絡參考。

cut-off 2026-06-08 PM 未拍板 → 自動進入「過渡寬限」：
- 不修改 `calc_kill_rate` 主判定（紅線 §5.1）
- 觀察期 #1 達標日重新校準：`max(2026-06-01, PM_cutoff_date + 7 天)`（7 天 = 連續 7 次 nightly）
- sprint_history.md §觀察期 #1 自動標 `🟡 延期 — PM 拍板未完成`

---

## 7. 三方獨立研究詳述

### 7.1 Architect 視角（≥ 150 字）

> **選項 A 立論**：半 kill 權重 (0.5) 是工程實務常用平滑技術（類似 sigmoid soft label / partial credit），對應 mutmut 文件對 suspicious 的描述「probably killed but timing-sensitive」。**0.5 是中位無偏估計**，避免高估（=1 等於選 C ignore + 補回分子）或低估（=0 等於現行）。±2pp tolerance 是統計學上 N=7 連續判定的 95% CI 經驗值（149 mutants × ±0.67pp × 3 sigma ≈ ±2pp）。實作風險低，只需修 `calc_kill_rate` 加 `0.5 * suspicious` 至分子；單元測試 ≥ 5 case 即可驗證 R9~R11 三個歷史資料點數學一致性。**選項 B 反對立論**：retry 機制違反 nightly 45 min 上限（ADR-SD08-002 §2.3），且 mutmut 2.4.x `--rerun-all` 是 process-level 不是 mutant-level，無法只 retry suspicious 子集。**選項 C 反對立論**：忽略 suspicious 等於丟棄 mutmut 對該 mutant 的「有疑慮」訊號，違反紀律 #2「log 必須包含完整統計」精神（資料完整但故意不用 = 偽完整）。

### 7.2 SA 視角（≥ 150 字）

> **選項 A 立論**：從需求面 trace，觀察期 #1 的設計目的是「驗證 token_guard test coverage 對 mutation 的真實殺傷能力」。Suspicious bounce flake **是 mutmut 工具本質特性，不是 token_guard 真實 quality 缺陷** — 7 個 suspicious 跨 3 次 nightly bounce 至 0 證實這些 mutant 的 test 已能殺，只是 timing window 不穩定。將 suspicious 視為 0.5 killed 半 kill 反映「期望值」語意。**±2pp tolerance 對應觀察期 #1「連續 7 次達標」紀律**：避免單次 bounce flake 觸發重計 → 永遠不可能達標。**選項 B 反對立論**：從 user story 看，nightly 觀察期使用者期待「每日 1 跑 / 7 天可達標」；retry 機制等於把單次 nightly 拉長 3 倍 → 違反 user story 隱含的時間契約。**選項 C 反對立論**：對 GoalSynthesis（目標 70% / 容忍 65%）/ Coordinator（目標 65% / 容忍 60%）這類較低目標模組，忽略 suspicious 可能使 kill_rate 從 62% 跳到 72% → **假象大幅進步**，違反需求面「真實量測 test quality」目的。[tools/mutation_baseline_lock.py:34-38 TARGETS SSOT](../../tools/mutation_baseline_lock.py#L34)。

### 7.3 SD 視角（≥ 150 字）

> **選項 A 立論**：技術設計面，0.5 半 kill weight 是**單次 commit minimal change**：只修 [mutation_baseline_lock.py:127-136](../../tools/mutation_baseline_lock.py#L127) `calc_kill_rate` 加一行 `numerator = killed + 0.5 * suspicious`；[mutation_analysis.py:236-254](../../tools/mutation_analysis.py#L236) `analyze` 同步反映。±2pp tolerance 只需在 `should_lock` line 255 把 `s >= threshold` 改為 `s >= threshold - 0.02`。**約束評估**：(a) 向下相容 — 既有 `.mutation_history.jsonl` 4 筆紀錄 suspicious=0 → 三選項數學等價；(b) `should_lock` 判定邏輯不變 — 仍是「連續 7 次 + sha unique」；(c) 不影響 [run_local_nightly.ps1](../../tools/run_local_nightly.ps1) 載具邏輯，stage rc 仍由 `mutmut_exit_code.py classify` 決定。**選項 B 反對立論**：技術上需新增 mutmut subprocess wrapper 追蹤每個 mutant 跨 run 結果 → 引入 stateful 設計 + cache 一致性問題，違反 [ADR-SD08-002 §2.3 簡單原則](ADR-SD08-002-mutation-baseline.md)。**選項 C 反對立論**：分母改變等於整個 [calc_kill_rate](../../tools/mutation_baseline_lock.py#L127) 公式重定義，對既有 baseline TOML（token_guard=0.75 目標）數值意義改變，需重新校準三模組目標。

### 7.4 三方共識

三方研究**獨立得出同一傾向：選項 A**，差異點僅在實作細節（Architect 強調統計合理性 / SA 強調需求對齊 / SD 強調最小改動）。**PM 拍板留待 user 簽核**（本段為 Round 11 PROPOSED 期記錄；**已於 Round 14 拍板採納選項 A**，見 §3.2 + §6 採納路徑表），三選項配套修法皆已準備。

---

## 8. 相關修復取證

- 取證 jsonl：[.mutation_history.jsonl](../../.mutation_history.jsonl) 4 筆紀錄（2026-05-20 ~ 2026-05-25）
- 演進取證：[SD09_W3_Round9_NextAction.md](../../05_development/SD09_W3_Round9_NextAction.md) §1 / [Round10](../../05_development/SD09_W3_Round10_NextAction.md) §1 / [Round11](../../05_development/SD09_W3_Round11_NextAction.md) §1
- 現行邏輯（v1.0 實作後，commit `0169b96`）：[tools/mutation_baseline_lock.py:140](../../tools/mutation_baseline_lock.py#L140) `calc_kill_rate`（已含 `+0.5×suspicious`）/ [line 297](../../tools/mutation_baseline_lock.py#L297) `should_lock`（已含 `EXTRA_TOLERANCE=0.02`）；提案期（v0.1）原行號 L127 / L226
- 對應 ADR：[ADR-SD08-002 §2.1](ADR-SD08-002-mutation-baseline.md) 分模組目標 / [ADR-SD09-002 §2.5](ADR-SD09-002-mutation-full-module-expansion.md) 三模組目標延續
- 上下文 ADR：[ADR-SD09-008](ADR-SD09-008-ac4-tolerant-track.md)（同樣採「過渡寬限 + cut-off + 雙軌觀察」模式）

---

## 9. Consequences

### 9.1 採納選項 A 的後果

**正向**：
- 觀察期 #1 可在 PM 拍板後 7 天內首次穩定鎖定 baseline
- 對應紀律 #1（區分真實失敗 vs 工具標準回報）+ 紀律 #4（驗證鏡子自身被驗證）
- 三模組（TokenGuard / GoalSynthesis / Coordinator）治理一致

**負向**：
- 鎖定門檻語意改變：原「killed / total ≥ 70%」變「(killed + 0.5×susp) / total ≥ 68%」（±2pp tolerance）
- 對 SD_10 升級為 PR 阻塞門時，「真實 killed」與「半 killed」混合 → 需文件明示

### 9.2 採納選項 B 的後果

**正向**：消除 bounce flake，每個 mutant 結論明確
**負向**：nightly 時間 ×3 倍，超出 45 min 上限；需新增 mutmut wrapper

### 9.3 採納選項 C 的後果

**正向**：計算最穩定，無 bounce flake
**負向**：丟棄 suspicious 訊號；對 GoalSynthesis/Coordinator 較低目標模組可能假象進步

---

## 10. Related Decisions

- [ADR-SD08-002](ADR-SD08-002-mutation-baseline.md) v1.0 — 分模組差異化目標 + 連續 7 次達標鎖定（本 ADR 修訂其 §2.1 計算公式）
- [ADR-SD09-002](ADR-SD09-002-mutation-full-module-expansion.md) v1.0 — 全模組擴展策略（本 ADR 影響三模組統一處理）
- [ADR-SD09-008](ADR-SD09-008-ac4-tolerant-track.md) v0.2 — AC4 雙軌 p95（本 ADR 沿用其「過渡寬限 + cut-off」模式）

---

## 11. 等價變異天花板 / 76% 真實水位（v1.1 ACCEPTED 2026-05-28 — R38 PM 拍板）

### 11.1 背景

SD_09 W3 Round 37 zero-trust audit（[SD09_W3_Round37_NextAction.md §2 P2-2](../../05_development/SD09_W3_Round37_NextAction.md)）訂正了先前軸 B「刻意加 test case / churn 源碼衝 unique sha / 衝 80% kill_rate」的方向錯誤，並提請 PM 拍板。R38 用戶拍板選項 A，落地於本節。

### 11.2 核心論證：should_compact_decision 為等價變異天花板

R37 audit 以窮舉 168/300 組實證 + R38 PM 親自讀碼覆核，確認 [thresholds.py:36-45 `should_compact_decision`](../../autoclaude/plugins/token_guard/thresholds.py#L36) 邏輯恆等於 `return token_pct >= threshold`：

```python
def should_compact_decision(*, token_pct, threshold, in_correction_loop, correction_history_len) -> bool:
    if token_pct < threshold:                              # guard：False
        return False
    if in_correction_loop and correction_history_len <= 1:
        return token_pct >= threshold                      # 此分支已過 guard → 必為 True
    return True                                            # 其餘路徑 → True
```

一旦通過第一個 `token_pct < threshold` guard，後續所有路徑（含 `in_correction_loop`/`correction_history_len` 兩參數的任意組合）皆返回 True。因此 `in_correction_loop` 與 `correction_history_len` 對輸出**零影響** → 改動 L43-44 correction-loop 分支的變異（mutation_backlog #125/126/127）為**等價變異（equivalent mutants）**，定義上任何測試都殺不掉。R30→R31 加 64 case 對 kill_rate 無實質提升已實證此天花板。

### 11.3 PM 拍板決議（R38，選項 A）

> ⚠️ **ADR-SD09-013（2026-08-03 ACCEPTED）supersede 本表「#1 唯一剩餘瓶頸」列的閘門位置**：unique source_sha256 由 **W1 入場條件**移為 **W1 出場驗收**（門檻 ≥ 7 unique sha 的數值完全不變，只改它擺在入場處還是出場處）。
> 🔴 **本列「此唯有 W1 active 開發合法改動 token_guard 源碼時發生」的因果宣稱，已被 2026-08-03 磁碟實查推翻**：(a) W1 從未啟動，token_guard 源碼照樣持續演進 — `git log -- autoclaude/plugins/token_guard/` 在 W1 最遲啟動日 2026-06-26 前後仍有 5 筆 commit（`02cc073` 06-25、`318c965`／`ad334c2` 06-26、`a16e591` 06-27、`f356348` 07-10），`.mutation_history.jsonl` 對應記到 **5 個相異 `source_sha256`**（`5208cff3`→`20940e1b`→`4af78567`→`55013d0a`→`5a44cbba`）；(b) 權威閘門 `should_lock()` 的**有效門檻是 ≥ 5**（`MAX_BACKWARD_COMPAT_MISSING=2` 對 2 筆 legacy 缺欄位紀錄的寬容），**2026-07-22 即已達標並鎖定 baseline `token_guard = 0.7071`**（`logs/nightly_2026-07-22_183551.log:261`）。原文保留為 R38 當時的判斷紀錄，取證見 ADR-SD09-013 §1.4。

| 項目 | 決議 |
|------|------|
| **76% 真實水位** | ✅ 接受 token_guard mutation kill_rate ~76% 為真實水位（等價變異天花板）。當前 R37 kill_rate=76.51% > 68% effective threshold（§5.5），且 streak 已 7/7，**觀察期 #1 的 kill_rate 條件已達標**。|
| **80% 目標降級** | 80% **不再是 G0 硬目標**，下修為長期非 G0 硬目標（SD_10+ 若重構 `should_compact_decision` 消除等價變異再評估）。|
| **#1 唯一剩餘瓶頸** | unique source_sha256 條件（紀律 #12）為**源碼演進閘門**（非單純時間閘門；R47 audit 訂正見 §11.6），非 quality 缺陷。**達標需 token_guard plugin 目錄源碼產生 ≥ 7 個相異版本**（M-05 每 UTC 日上限 1 unique sha），此唯有 **W1 active 開發合法改動 token_guard 源碼**時發生；**idle 觀察期源碼凍結 → 重跑只追加相同 sha → unique 數不增**。若 W1 不觸碰 token_guard，#1 unique sha 依 R-SD08-PM-#3 延 SD_10。|
| **軸 B 方向訂正（紀律 #12 反作弊）** | ❌ **禁止為衝 unique sha 刻意 churn / 修改 token_guard 源碼**。理由：(1) `compute_source_sha256` 由 plugin 源碼計算，加測試不改 sha（tests/ 不在 plugin 目錄）；(2) `append_history` M-05 對同 module + 同 UTC date 去重 → 單 session 重跑當日只 +1 unique sha；(3) 刻意 churn 違反紀律 #12「防同 commit 重跑騙鎖、要求自然多日演進」的反作弊精神。|

### 11.4 與 v1.0 政策的關係

本節（v1.1）與 §3 的 suspicious 0.5 半 kill 政策（v1.0）**互補但獨立**：v1.0 處理「suspicious bounce flake 導致 kill_rate 邊界飄動」的計算口徑；v1.1 處理「等價變異導致 kill_rate 存在 ~76% 天花板無法達 80%」的目標設定。兩者皆服務於「觀察期 #1 真實量測 token_guard test quality」的需求目的（紀律 #2 / SA §7.2）。

### 11.5 不變更項（紅線延續）

- 本節為**目標設定與方向訂正決策**，**不修改任何程式碼**（`calc_kill_rate` / `should_lock` / `thresholds.py` 全部維持現狀）。
- 紀律 #12 unique sha 守門邏輯**不放寬**（`should_lock` 仍要求 tail 7 unique sha；禁人工 churn 繞過）。
- effective threshold 維持 68%（§5.5 ±2pp），不因接受 76% 真實水位而調整 TARGETS SSOT。

### 11.6 R47 audit 訂正（unique sha 達標路徑心智模型）

> ⚠️ **ADR-SD09-011（2026-06-30，improving_101）supersede 本節「需 W1 active 改源碼 × 多日演進」的時間綁定**：根因偵察揭露 M-05 同 UTC 日去重 + 每日 nightly 使 unique sha 每日上限 1、7 個需 ≥7 日曆天、idle 稀釋 tail → 空轉。改為「去重鍵 source_sha256（同日多 sha 皆計入）+ 源碼變動觸發」解除日曆綁定。**unique sha 反作弊與「禁 churn 衝 sha」仍完全保留**（§11 line 231/240 不變）；只取消與安全無關的日曆懲罰。詳見 ADR-SD09-011。

> ⚠️ **ADR-SD09-013（2026-08-03 ACCEPTED）supersede 本節訂正結論的閘門位置**：unique sha 由 W1 **入場**條件移為 W1 **出場**驗收（門檻 ≥ 7 不變）。
> 🔴 **本節下方「達標唯有 W1 active 開發合法改動 token_guard plugin 源碼」與「idle 觀察期源碼凍結不達標」兩句，已被 2026-08-03 實查推翻**：W1 未啟動期間 token_guard 源碼照樣持續演進（`.mutation_history.jsonl` 記到 **5 個相異 sha**，見 §11.3 註記）；且權威 `should_lock()` 有效門檻為 ≥ 5（含 2 筆 legacy 缺欄位寬容），2026-07-22 就已達標並鎖定 baseline 0.7071。原文保留為 R47 當時的判斷紀錄，取證見 ADR-SD09-013 §1.4。

SD_09 W3 Round 47 Architect + SA 並行 zero-trust audit 獨立指出 §11.3 line 230 原敘述「靠自然多日 commit 累積相異 sha 解決（約 2026-06-02~03）」**與 line 231 自相矛盾且誤導**：

- **根因**：`compute_source_sha256` 對 `autoclaude/plugins/token_guard/*.py` rglob 計算（[mutation_baseline_lock.py](../../../tools/mutation_baseline_lock.py)），**只反映 plugin 源碼**。token_guard 源碼自 2026-05-27 凍結 `20940e1b`（5/27~5/29 三日同 sha）；對 repo 其他部分的 commit **不改變** token_guard sha。
- **誤導後果**：易讓團隊誤以為 #1 unique sha 會在 2026-06-02~03「自然達標」，實則卡死於源碼凍結（log `reason=sha_partial_duplicate unique=2/6` 正確拒鎖）。
- **訂正**（已更新 line 230）：#1 unique sha 達標**唯有 W1 active 開發合法改動 token_guard plugin 源碼**（≥ 7 個相異 UTC 日版本，M-05 每日上限 1）；若 W1 不觸碰 token_guard 則依 R-SD08-PM-#3 延 SD_10。kill_rate 條件（76% > 68% effective）已達標不受影響。
- **不變更**：`should_lock` 守門邏輯與紀律 #12 反作弊（禁人工 churn）維持不放寬；本訂正純文件心智模型校正。

---

**版本紀錄**：
- v0.1（PROPOSED）2026-05-25 — SD_09 W3 Round 11 三方獨立研究初版（Architect + SA + SD 共識傾向選項 A；PM 拍板留待 user 簽核）
- **v1.0（ACCEPTED）2026-05-25** — SD_09 W3 Round 14 PM Agent 拍板選項 A（suspicious 計 0.5 killed 半 kill + ±2pp tolerance；三方研究 100% 共識）。同步更新 §3.2 / §6 採納路徑表 / §6.1（過渡寬限失效）。**程式實作於同日 SD_09 W1 PR（commit `0169b96`）落地**：`calc_kill_rate` 加 `0.5×suspicious` 至分子 + `should_lock` 加 `EXTRA_TOLERANCE=0.02`（token_guard effective threshold = 0.75 - 0.05 - 0.02 = 0.68）+ ≥ 5 case 單元測試。
- **v1.1（ACCEPTED）2026-05-28** — SD_09 W3 Round 38 PM Agent 拍板新增 §11「等價變異天花板 / 76% 真實水位」決策（接受 token_guard kill_rate ~76% 為真實水位，80% 下修為長期非 G0 硬目標；軸 B 方向訂正禁人工 churn 源碼衝 sha）。本節為 R37 audit 提請、R38 用戶拍板的 NEW 決策，與 v1.0 的 suspicious 政策互補。
- **v1.2（ACCEPTED）2026-05-29** — SD_09 W3 Round 47 Architect + SA 並行 audit 訂正 §11.3 line 230「自然多日 commit 累積 unique sha」誤導敘述，新增 §11.6：#1 unique sha 為**源碼演進閘門**（需 W1 active 改 token_guard 源碼，idle 期凍結不達標），非時間閘門；純文件心智模型校正，不改程式碼。
