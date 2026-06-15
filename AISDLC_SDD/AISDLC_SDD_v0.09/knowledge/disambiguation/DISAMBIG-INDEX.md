# Disambiguation Index（DIS-*）— Phase K / ACT-083+084

> 規格歧義對知識庫，對稱於 [`failure-patterns/`](../failure-patterns/)（FPL）、
> [`skill-patterns/`](../skill-patterns/)（SPL）與 [`adversarial-patterns/`](../adversarial-patterns/)（ADV）。
> `DIS-*.yaml` 由 [`spec_debate`](../../tools/fsm_runtime/spec_debate.py) 於 `SPEC_DEBATE`
> 出口（divergence → `HUMAN_PENDING`）落盤：存放兩條隔離詮釋（pro/con）+ 分歧證據 +
> 人類裁決，回饋 `AmbiguityScorer` 校準語料。

advisory（Rule 9.23.4 / 9.23.5）：歧義對**只建議不自動阻塞/改寫 AC**，divergence
僅導向 `HUMAN_PENDING` 人工裁決；落盤草案一律 `maturity: proposed`（**禁自動 verified**，
比照 SPL/ADV 治理，須人工 review 升級）。

漸進式揭露：DIS 模式經狀態感知 lazy load（`SPEC_DEBATE` 狀態），不汙染 eager 地圖；
acyclic 無覆寫（已落盤的 `DIS-*.yaml` 不被後續分解覆蓋，新歧義對取新編號）。

## DIS schema（`DIS-NNN.yaml`）

| 欄位 | 說明 |
|------|------|
| `id` | `DIS-NNN` |
| `ac_id` | 觸發辯證的 AC（如 `AC-014`） |
| `interp_a` | 詮釋 A（pro=inclusive/強讀法，oracle-blind） |
| `interp_b` | 詮釋 B（con=exclusive/弱讀法，oracle-blind） |
| `divergence` | 量化分歧度（`pattern_matcher` 反向相似度） |
| `markers` | 命中的雙讀標記（如 `可疊加`、`and/or`） |
| `verdict` | 人類裁決（`null` = 待裁決；裁決後填 `interp_a` / `interp_b` / 自訂澄清） |
| `profile_version` | 辯證強度版本（`SPEC_DEBATE_PROFILE_VERSION`，變更須 bump） |
| `provenance` | 來源（`spec_debate`、產出時間） |
| `maturity` | `proposed` / `reviewed`（三階沿用 SPL；落盤恆為 `proposed`） |

## 鐵則（§4 Rule 9.23）

- `spec_debate` 落盤只產 `maturity: proposed` 草案，**禁自動 verified/reviewed**（人工 gate）。
- divergence **不自動阻塞 SCG、不自動改寫 AC**（Rule 9.23.4 advisory），僅附歧義對導 `HUMAN_PENDING`。
- 辯證強度凍結於 `SPEC_DEBATE_PROFILE_VERSION`；變更須 bump（Rule 9.23.3 — 判官不自我放水）。

## 索引

| DIS | AC | divergence | verdict | maturity |
|-----|----|------------|---------|----------|
| （v1 初始為空，待 `SPEC_DEBATE` divergence 出口運行落盤 proposed 草案） | — | — | — | — |
