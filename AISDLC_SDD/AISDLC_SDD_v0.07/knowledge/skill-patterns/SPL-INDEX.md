# SPL — Skill Pattern Library（成功技能庫索引）

> Phase I M3 / ACT-066（Rule 9.21.6）。與 `failure-patterns/FPL` **對稱**的「成功技能庫」。

## 設計動機（PI-6 — 只記仇不記恩的結構性不對稱）

Phase H 之前，整條學習迴路（FPL→SLV、scaffold_gc、6 observation 態、nightly cron）
**全部失敗/漂移導向**。`scaffold_gc` 把 productive 軌跡只**計數**從不**萃取**；
`rule_loader.propose_graduation` 只 active→audit-only→deprecated **單向退化**。
一個只記得失敗、把成功 FIFO 丟棄的系統會永遠從零重摸已解過的問題。

Phase I 補上**合成代謝**（鷹架代謝的加法面）：反覆成功的軌跡結晶成可複用技能。

## SPL schema（`SPL-NNN.yaml`）

| 欄位 | 說明 |
|------|------|
| `id` | `SPL-NNN` |
| `trigger_states` | 此技能適用的 FSM 狀態 |
| `abstracted_steps` | 從多 productive episode 聚合的抽象步驟 |
| `reuse_count` | 被複用次數 |
| `provenance.source_episodes` | 來源軌跡（decision_trace 指紋） |
| `trust_level` | `proposed` / `verified` / `external`（三階，沿用 SLV 慣例） |

## 鐵則（§8 風險表）

- `spl_consolidator` 只產 `trust_level: proposed` 草案，**禁自動 verified**（人工 gate）。
- 同模式 **≥ N 次** 成功（`pattern_matcher.is_same_pattern`）才提案，防偶發成功誤結晶。
- 退役提案優先於結晶提案（避免剛固化又被退役震盪）。
- 經 Hub 跨實例散播時上游若標 verified → `_stamp_external_trust_level` 強制 external（Rule 9.12.6）。

## 索引

| SPL | 標題 | trust_level | 來源 |
|-----|------|-------------|------|
| （尚無 verified 技能 — 由 spl_consolidator 於 MEMORY_CONSOLIDATION 產出 proposed 草案後人工 review 升級） | — | — | — |
