# FPL-{NNN}：{Pattern 標題}

**狀態**: draft | active | deprecated
**建立日期**: YYYY-MM-DD
**建立人**: {agent_id 或姓名}
**SLV 補強建議**: SLV-00X 候選

## 摘要

一句話說明此 Pattern 是什麼，AC 在什麼條件下會出現。

## 偵測時機

- 目前 SLV-001~006 中哪一條「接近但未捕獲」此案例？
- 何種語句、語法、關鍵字會觸發？

## 典型反例（壞味道）

```text
[舉一條真實 AC 原文]
```

## 為何有問題

- 語義歧義點：{描述}
- 測試上的後果：{測試不可判定 / 測試物理不可達 / 測試結果依賴未凍結的外部條件}
- FSM 上的後果：{觸發何種 retry / ESCALATION}

## 歷史案例

| 專案 | 日期 | AC_id | FSM 觸發 | 結局 |
|------|------|-------|---------|------|
| {project} | YYYY-MM-DD | AC-XXX-Y | PR_REVIEW × N | ESCALATION / Resolved |

## 建議 SLV 規則（草案）

```yaml
slv_XXX_candidate:
  pattern: "{正則或語義規則}"
  required_qualifier:
    - "{條件 1}"
    - "{條件 2}"
  failure_example: "{反例}"
  pass_example: "{正例}"
```

## 修正範本

```text
[示範如何把反例改寫成合規 AC]
```

## 相關
- FPL-... （如果與其他 Pattern 同源）
- SLV-... （關聯既有規則）
