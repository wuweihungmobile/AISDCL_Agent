# Failure Pattern Library（FPL）— 索引

**版本**: v0.01（Phase D / ACT-015）
**建立日期**: 2026-04-19
**用途**: 記錄 SLV-001~006 尚未覆蓋、但在實戰中出現的 Spec 缺陷模式。
供 `/spec-logical-validator` 與未來 SLV Rule Generator（Phase E / ACT-020）查詢。

## 收錄規則

| 條件 | 行動 |
|------|------|
| SCG_VALIDATION retry_count ≥ 2 且最終 PASS | SA 應歸納失敗模式，若非 SLV-001~006 覆蓋則新增 FPL 條目 |
| 進入 ESCALATION 且根因為 Spec 歧義 | 強制新增 FPL 條目並於 Abort Report 引用 |
| 同一模式在 ≥ 2 個專案重複出現 | 升級為 SLV-00N 新規則候選（送 Phase E 審核） |

## 索引

| ID | 標題 | 建立 | SLV 補強建議 | 狀態 |
|----|------|------|-------------|------|
| [FPL-001](FPL-001-temporal-inconsistency.md) | 時序語義矛盾（N+1 vs N 無穩態條件） | 2026-04-19 | **SLV-007 已採納（2026-04-24, Phase E M4）** | adopted |
| [FPL-002](FPL-002-cache-eviction-assumption.md) | 快取永遠命中假設（未定義 miss 回退） | 2026-04-19 | SLV-008 候選 | active |

## 模板

- [FAILURE-PATTERN-TEMPLATE.md](templates/FAILURE-PATTERN-TEMPLATE.md)

## 使用方式

1. SA/Architect 在 SCG 閘門重試後回顧失敗根因；若屬未覆蓋模式 → 依 template 新增 FPL 條目。
2. `/spec-logical-validator` 執行時載入 `FPL-INDEX.md`，對每條 active pattern 做 heuristic 掃描，發現疑似案例即輸出「建議引用 FPL-00X」。
3. Phase E：SLV Rule Generator 讀 FPL 草擬新 SLV 規則，經 SA Lead 審核後加入 `.claude/skills/spec-logical-validator/rules.yaml`。
