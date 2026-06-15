# Greenfield SDD CI/CD Pipeline 規格
# SDD Greenfield CI/CD Enhancement

**版本**: v1.0
**建立日期**: 2026-04-12
**適用情境**: Greenfield（新專案開發）
**前置條件**: Phase 01 SDD_CICD_BASE_LAYER.md 已定義

---

## 🏗️ Greenfield L0 基礎層（SDD 強化版）

### 2.3.1 + 2.3.2 新增品質驗證步驟

```
Build → Unit Test → Lint → DocLint → SpecTrace → API Spec Validation → Security Scan → Deploy
                              ↑           ↑              ↑
                    （Phase 01）    （Phase 01）  （Phase 02 新增）
```

#### DocLint（繼承 Phase 01）
- 驗證所有 Markdown 文件格式
- 驗證 ADR/CONTRACT/TCS 命名規範
- 驗證連結有效性

#### SpecTrace（繼承 Phase 01）
- 驗證 RTM 追溯鏈完整性
- 驗證 ADR 覆蓋率
- 驗證 API Contract 追溯至 US

### 2.3.3 Unit Test + Build（維持不變）
- 標準 Unit Test 流程無變化
- Build Check 維持原有設定

### 2.3.4 SAST（維持不變）
- 靜態安全掃描維持原有設定
- Greenfield 建議新增：`npm audit` / `snyk`

### 2.3.5 通知機制（維持不變）
- 標準 Slack/Teams 通知無變化

### 2.3.6 API Spec Validation（🆕 Phase 02 新增）

```yaml
api_spec_validation:
  name: "OpenAPI Spec Validation"
  trigger: "docs/02_architecture/api/ 有新增或修改時"
  tool: "openapi-validator / spectral"
  config: ".spectral.yaml"
  validation_rules:
    - "OpenAPI 3.1 語法正確"
    - "所有 endpoint 有 summary"
    - "所有 Response Schema 已定義"
    - "x-aisdlc.related_us 欄位不為空"
    - "安全機制已定義（securitySchemes）"
  fail_on_error: true
  output: "build/reports/verification/APISpec-Validation-{date}.md"
```

---

## 📋 Greenfield 各 Stage 品質閘門觸發配置

```yaml
greenfield_spec_gates:
  stage_0:
    gate: "SCG-0 Spec Foundation"
    checks:
      - "docs/02_architecture/adr/ 目錄存在"
      - "docs/03_testing/RTM-{project}.md 已建立"

  stage_1:
    gate: "🔷 SCG-1 Requirement Spec Gate（PRD）"
    checks:
      - "PRD NFR 章節已填寫"
      - "業務目標可量化"

  stage_2:
    gate: "🔷 SCG-1 Requirement Spec Gate（FRD + RTM）"
    checks:
      - "FRD 所有欄位完整"
      - "RTM 初版已建立（EPIC→AC 四層）"
      - "所有 AC 可測試"

  stage_3:
    gate: "🔷 SCG-2 Architecture Spec Gate"
    checks:
      - "C4 L1 Context 圖已產出"
      - "C4 L2 Container 圖已產出"
      - "ADR-001（技術棧）已建立"
      - "ADR-002（架構模式）已建立"
      - "ADR-003（部署策略）已建立"
      - "NFR 已規格化（數值明確）"

  stage_4:
    gate: "🔷 SCG-3 API Contract Gate"
    checks:
      - "所有 API 端點已定義（OpenAPI 3.1）"
      - "API Spec Validation 通過"
      - "Consumer Side 已確認"

  stage_5:
    gate: "🔷 SCG-4 Test Strategy Gate"
    checks:
      - "Test Strategy Document 已完成"
      - "Test Contract Spec 已建立"
      - "RTM AT 層填入（覆蓋率 ≥ 90%）"
```

---

## 🔗 相關文件

- [SDD CI/CD 基礎層](SDD_CICD_BASE_LAYER.md)
- [Greenfield SDD 強化規範](../../AISDLC_v0.09/scenarios/greenfield/SDD_GREENFIELD_ENHANCEMENT.md)
