# Ambiguity Waiver — {AC_ID}

**模板版本**: v1.0（對應 SCORER_VERSION v1.0）
**對應規則**: CLAUDE.md §9.16.3
**落地路徑**: `docs/01_requirements/AMBIGUITY-WAIVER-{AC_ID}.md`

---

## 必填欄位

| 欄位 | 值 |
|------|----|
| AC_ID | {AC-XXX-Y} |
| FRD 路徑 | docs/01_requirements/FRD-{Module}.md |
| ambiguity_score | {0.4~1.0} |
| 觸發維度 | {d1_quantifier, d2_passive, ...} |
| SCORER_VERSION | v1.0 |
| waived_by | {reviewer 姓名 / GitHub 帳號} |
| waived_at | {YYYY-MM-DD} |
| 有效期限 | {YYYY-MM-DD，最長 90 天，到期需重審} |

---

## 1. AC 原文

```
（複製 AC Given/When/Then 原文）
```

## 2. 模糊性說明（waiver rationale）

說明為何此 AC 雖被 AmbiguityScorer 判為模糊，仍可進入下游：
- 是否屬「業務上必要的留白」（如客戶體驗詞彙、stakeholder 共識用語）
- 是否在 SRD / API Spec / Test Contract 補強為可量化驗證
- 是否有對應 ADR 紀錄此抽象設計決策

## 3. 補強規格參照（必填至少一條）

- [ ] SRD: docs/02_architecture/SRD-{System}.md §{X.Y}
- [ ] API Spec: docs/02_architecture/api/openapi.yaml#{operationId}
- [ ] Test Contract: docs/03_testing/contracts/{name}-test-contract.md
- [ ] ADR: docs/02_architecture/adr/ADR-{NNN}.md

## 4. Reviewer Signoff

- [ ] 已閱讀 AC 原文
- [ ] 已確認補強規格能夠彌補模糊性
- [ ] 已通知 PM / SA 此 waiver 的存在

**簽名**: _________________________ **日期**: _________________

---

## 5. 重審時機

| 觸發條件 | 動作 |
|---------|------|
| 有效期限到期 | 重新評估或重寫 AC，移除 waiver |
| AC 內容變更 | 立即廢止 waiver，重新跑 ambiguity gate |
| SCORER_VERSION bump | 重新跑 score；若降至 < 0.4 即可移除 waiver |
| 同 FRD 出現 ≥ 3 條 waiver | 升級至 PM/SA 流程審視，避免規格品質劣化 |
