# Experiment Patterns 索引（EXP-*）— Phase L M-L2 / ACT-091

> 對稱於 `knowledge/failure-patterns/`（FPL）、`knowledge/intent-patterns/`（INT）、
> `knowledge/adversarial-patterns/`（ADV）。存放離線反事實重放結晶出的「補丁→歷史命中」
> 模式（`EXP-*.yaml`），由 `counterfactual_replay.crystallize_patterns()` 於 ≥ 3 次同型
> 命中後產出 **proposed** 草案（**禁自動 verified**，須人工 review 升級；治理同 SPL/INT/ADV）。

## 用途

- 補丁約束（`guard_text` 正規化指紋）與其歷史命中率的可複用知識。
- 未來相同領域的 `spec_patch_proposer` 補丁可參考既有 EXP 模式的歷史有效性。
- lazy load（不汙染 eager 規則地圖）；advisory，絕不自動套用改 spec（Rule 9.24.4/9.24.5）。

## 條目

（目前無已結晶條目——隨 runtime 累積 ≥ 3 次同型「補丁→歷史命中」後自動產出 `EXP-NNN.yaml`。）

| EXP id | patch 約束指紋 | occurrences | avg 命中率 | maturity |
|--------|----------------|-------------|-----------|----------|
| —      | —              | —           | —         | —        |
