# SPEC-PATCH — {AC_ID}（{DATE}）

> Phase J / ACT-078 規格自癒草案模板。由 `spec_patch_proposer.propose()` 自動產出，
> **複製填寫後仍為 proposed**；絕不自動套用（Rule 9.22.5 / Rule 8 人工確認）。

- **trust_level**: `proposed`（人工 approve 後才由 SPEC_DRAFTING 套用）
- **source**: `spec_defect-auto-generated`
- **觸發**: spec_defect verdict 語意同模式重複 ≥ 2 次（pattern_matcher）
- **出口**: 人工 approve → `SPEC_DRAFTING` 套用；reject → 維持原 AC
- **限流**: 同一 AC 全 session ≤ 2 次（超限直升 ESCALATION）

## 1. 反例證據

來自 `ADVERSARIAL_EVALUATION` / `SLV` / `EXECUTION_EVALUATION` 的具體反例：

- {counterexample_1}
- {counterexample_2}

## 2. Before（現行 AC）

```
{current_ac_text}
```

## 3. After（建議補強 — proposed diff）

```
{proposed_ac_text}
```

## 4. 影響面（人工 review 時確認）

- 受影響 RTM TC：{affected_tc}
- 受影響下游契約 / API：{affected_contracts}

---

> 本草案為 advisory；人類維持設計掌舵者高度，只需 approve / reject 一個 diff，
> 不需從零重寫 AC。
