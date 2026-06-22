# Test-Contract Negotiation — {SystemName}

> **Phase H M2 / ACT-049**：IMPLEMENTATION 前的「測試標準合約談判」憑證。
> 對應 SDD_improving_Automation_08.md §G3（Planner 宏觀擴展 → Generator/Evaluator 微觀合約談判）。
> 從 `docs_template/sdd/testing/` 複製到 `docs/03_testing/` 後填寫，**禁止直接改模板**。

| 欄位 | 值 |
|------|----|
| contract_ref | API_/SRD_ 凍結引用（SCG-3 後） |
| generator | dev-senior（程式生成者） |
| evaluator | sdd-evaluator（執行接地評估者） |
| negotiated_at | YYYY-MM-DDThh:mm:ssZ |

## Oracle 定義（每條 AC 一列，pass/fail 必須客觀可執行）

| AC ID | 驗收準則 | 客觀 Oracle（pass 條件） | 失敗判定 | 量測方式 |
|-------|---------|------------------------|---------|---------|
| AC-001-1 | 使用者可登入 | HTTP 200 + JWT 有效 + P95 < 200ms | 4xx/5xx 或 P95 ≥ 200ms | sandbox HTTP driver |
| AC-002-1 | 密碼規則 | 拒絕 < 12 字元（HTTP 422） | 接受 < 12 字元 | Playwright UI 斷言 |

> ⚠️ Oracle 必須是**沙箱可實跑驗證**的客觀條件，不可為「應正確處理」等模糊描述
> （否則 AmbiguityScorer / 談判閘會退回 SPEC_DRAFTING）。

## 簽署（git 留痕）

- [ ] **Evaluator 草擬 oracle 完成**（每條 AC 有客觀 pass/fail）
- [ ] **Generator 簽署確認**（dev-senior 已讀並同意以此 oracle 為準）— `generator_signed: true`
- [ ] **記錄持久化**：`subagent_contract.record_test_standard_agreement()` →
      `build/reports/eval/TEST-CONTRACT-AGREEMENT-{date}.yaml`

> 三項全勾且 `ready_for_implementation: true` 後，方可 `exit_test_contract_negotiated("agreed")`
> 進入 IMPLEMENTATION；任一未完成 → `exit_test_contract_negotiated("underspecified")` 退回重擬規格。
