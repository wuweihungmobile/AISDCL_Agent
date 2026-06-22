# Adversarial Patterns Index（ADV-*）— Phase J / ACT-073

> 對抗攻擊模式庫，對稱於 [`failure-patterns/`](../failure-patterns/)（FPL）與
> [`skill-patterns/`](../skill-patterns/)（SPL）。`ADV-*.yaml` 由
> `adversarial_synthesizer` 於 `MEMORY_CONSOLIDATION` 動態結晶：≥3 次成功破防的
> 攻擊向量 → proposed ADV 草案（**禁自動 verified**，須人工 review）。

| ADV ID | 攻擊類型 | 描述 | trust_level |
|--------|---------|------|-------------|
| （尚無——由 MEMORY_CONSOLIDATION 動態產出）| — | — | — |

## 攻擊類型（adversarial_synthesizer.ATTACK_TYPES）

| 類型 | 說明 |
|------|------|
| `property_based` | 從 AC 抽取可檢性質（單調/冪等/非負/邊界），生成違反輸入 |
| `metamorphic` | 輸入變換關係（f(2x) vs 2·f(x)、排序不變性） |
| `fuzz` | 型別感知邊界 fuzz（空集合/極值/NaN/Unicode） |
| `mutation_guided` | 語意保持變異，偵測弱 oracle |

> 強度權重凍結於 `adversarial_synthesizer.ADVERSARIAL_PROFILE_VERSION`；
> 變更須 bump 版本（Rule 9.22.2 — 判官不自我放水）。
