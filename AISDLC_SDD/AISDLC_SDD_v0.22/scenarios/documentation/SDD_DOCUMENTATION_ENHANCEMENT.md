# Documentation 情境 SDD 強化規範
# SDD Documentation Scenario Enhancement

**版本**: v1.0
**建立日期**: 2026-04-12
**適用情境**: Documentation（文件維護）
**前置條件**: Phase 01 SDD_CICD_BASE_LAYER.md 已定義

---

## 🎯 目標

將 Documentation 情境從「文件產出」升級為「規格維護（Living Spec）」，確保：
1. 所有架構決策有 ADR 記錄
2. 文件健康度可量化追蹤
3. 文件-程式碼同步自動驗證

---

## 📋 Documentation SDD 強化流程

```
Stage 1: Documentation Audit（SDD 新增）
  ├── technical-writer: 現有文件 SDD 符合度審計
  ├── sa-analyst: 規格完整性驗證
  └── 🔷 SCG-Doc：文件缺口清單確認

Stage 2: ADR Index 建立（SDD 強制）
  ├── technical-writer: 掃描現有架構決策
  ├── sd-architect: 隱性決策轉化為 ADR
  └── 產出：ADR-INDEX.md（所有決策索引）

Stage 3: Living Documentation 架構
  ├── technical-writer: 文件-程式碼雙向連結
  ├── technical-writer: 版本化文件策略
  └── dev-senior: 技術正確性審查

Stage 4: RTM 逆向建立（SDD 新增）
  ├── sa-analyst: 從現有文件提取需求追溯鏈
  └── 產出：RTM-EXISTING-SYSTEM.md

Stage 5: API Documentation 升級（強化）
  ├── sd-architect: 現有 API 轉化為 OpenAPI Spec
  ├── integration-specialist: API 契約驗證
  └── 🔷 SCG-3 → 🔴 Human: API Spec Freeze
```

---

## 🔍 2.8 產出物審查工作流

### 2.8.1 SDD 審計報告審查

**參與者**: technical-writer（主持）+ sa-analyst（協同）
**觸發時機**: Stage 1 完成後
**審查項目**:

```yaml
sdd_audit_review:
  checklist:
    spec_first_gate:
      - "PRD 是否在開發前完成？"
      - "FRD 是否在實作前完成？"
      - "API Spec 是否在 UI 開發前凍結？"
      - "測試計畫是否在實作前完成？"
    design_as_doc:
      - "C4 Context 圖（L1）存在？"
      - "C4 Container 圖（L2）存在？"
      - "ADR 目錄存在且有記錄？"
      - "NFR 規格（SLO/SLA）已定義？"
    contract_driven:
      - "所有 API 端點已 OpenAPI 文件化？"
      - "API Contract 與實作一致？"
      - "Test Contract 已定義？"
  output: "docs/02_architecture/SDD-COMPLIANCE-AUDIT-{date}.md"
  template: "docs/02_architecture/SDD-COMPLIANCE-AUDIT-TEMPLATE.md"
  pass_criteria: "SDD 整體符合度 ≥ 70%"
  human_confirmation: "🔴 Human 確認審計結果與行動方案"
```

---

### 2.8.2 ADR 索引審查

**參與者**: sd-architect（主持）
**觸發時機**: Stage 2 完成後，每季度重複執行
**審查項目**:

```yaml
adr_index_review:
  checklist:
    completeness:
      - "技術棧選型是否有對應 ADR？"
      - "架構模式選擇是否有 ADR？"
      - "部署策略是否有 ADR？"
      - "SRD 中所有技術選型是否已 ADR 化？"
    validity:
      - "所有 Accepted ADR 是否仍然有效？"
      - "是否有技術已過時應標記為 Deprecated？"
      - "是否有 ADR 被新決策取代（Superseded）？"
    format:
      - "每個 ADR 是否有 Context/Decision/Rationale/Consequences？"
      - "ADR-INDEX.md 統計數字是否正確？"
  output: "docs/02_architecture/adr/ADR-INDEX.md 更新"
  responsible: "sd-architect"
  frequency: "每季度 + 每次架構變更後"
  human_confirmation: "🔴 Human 確認廢棄 ADR 標記"
```

---

### 2.8.3 RTM 追溯鏈審查

**參與者**: sa-analyst（主持）+ qa-tester（協同）
**觸發時機**: Stage 4 完成後，每月審查
**審查項目**:

```yaml
rtm_review:
  coverage_targets:
    rtm_coverage: "≥ 80%（US 有完整 AC/AT）"
    ac_coverage: "≥ 85%（AC 有對應 AT）"
    api_coverage: "100%（所有 API 有 US 追溯）"
    nfr_coverage: "≥ 90%（NFR 有對應 US）"
  gap_analysis:
    - "識別無 AC 的 US（優先補充）"
    - "識別無 AT 的 AC（次優先）"
    - "識別無 NFR 的效能/安全 US"
  action_items:
    p0_gaps: "缺 AC 的核心功能 US → sa-analyst 補充"
    p1_gaps: "缺 AT 的 AC → qa-tester 補充"
    p2_gaps: "NFR 未對應 → 下個 Sprint 補充"
  output: "docs/03_testing/RTM-{project}.md 更新"
  template: "docs/03_testing/RTM-EXISTING-SYSTEM-TEMPLATE.md"
  frequency: "每月 + 每個 Sprint Review 後"
  human_confirmation: "🔴 Human 確認缺口優先級與補充計畫"
```

---

### 2.8.4 API Spec 審查

**參與者**: sd-architect（主持）+ dev-developer + integration-specialist
**觸發時機**: Stage 5 完成後，每次 API 變更後
**審查項目**:

```yaml
api_spec_review:
  format_check:
    - "所有 API 使用 OpenAPI 3.1 格式？"
    - "每個 endpoint 有 summary 和 description？"
    - "所有 Request/Response Schema 已定義？"
    - "x-aisdlc.related_us 欄位已填入？"
    - "認證機制（securitySchemes）已定義？"
  consistency_check:
    - "API Spec 與實際 Route 一致？"
    - "API Spec 版本號與系統版本一致？"
    - "deprecated 端點已標記且有替代方案？"
  traceability_check:
    - "每個 API 端點可追溯至 User Story？"
    - "Consumer Side 已確認（Consumer-Driven Contract）？"
  output: "build/reports/verification/APISpec-Review-{date}.md"
  consumer_sign_off: "🔴 Consumer Side 確認（前端/外部消費者）"
  human_confirmation: "🔴 Human 確認 API Spec Freeze"
```

---

## 📊 Documentation 情境健康度指標

| 指標 | 計算方式 | 最低目標 | 優秀目標 |
|------|---------|---------|---------|
| RTM 覆蓋率 | 有完整追溯的 US / 總 US | ≥ 80% | ≥ 95% |
| API 文件覆蓋率 | 有 OpenAPI Spec 的 API / 總 API | 100% | 100% |
| ADR 覆蓋率 | 有 ADR 的架構決策 / 總架構決策 | ≥ 90% | 100% |
| 文件更新及時率 | 7 天內更新 / 觸發事件數 | ≥ 85% | ≥ 95% |
| SDD 符合度 | 符合 SDD 三支柱的文件 / 總文件 | ≥ 70% | ≥ 90% |

---

## 🔗 相關文件

- [SDD CI/CD 基礎層](../../../docs/08_deployment/SDD_CICD_BASE_LAYER.md)
- [SDD 符合度審計範本](../../../docs/02_architecture/SDD-COMPLIANCE-AUDIT-TEMPLATE.md)
- [ADR 索引](../../../docs/02_architecture/adr/ADR-INDEX.md)
- [Living Doc 策略範本](../../../docs/05_development/LIVING-DOC-STRATEGY-TEMPLATE.md)
- [RTM 既有系統範本](../../../docs/03_testing/RTM-EXISTING-SYSTEM-TEMPLATE.md)
- [Greenfield SDD 強化規範](../greenfield/SDD_GREENFIELD_ENHANCEMENT.md)
