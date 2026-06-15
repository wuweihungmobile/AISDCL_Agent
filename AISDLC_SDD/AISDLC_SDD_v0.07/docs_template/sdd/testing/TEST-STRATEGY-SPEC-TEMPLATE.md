# Test Strategy Specification — Template
# 測試策略規格文件模板
# Phase 05 — Testing 情境 SDD 強化

**文件類型**: Test Strategy Specification (TSS)
**SDD Gate**: SCG-4 Test Strategy Gate
**使用時機**: SRD 完成後、開發開始前（Spec-First 強制）
**存放位置**: `docs/03_testing/TEST-STRATEGY-{project}-{date}.md`

---

## 文件資訊

| 欄位 | 說明 |
|------|------|
| **專案名稱** | {ProjectName} |
| **系統版本** | {Version} |
| **建立日期** | {YYYY-MM-DD} |
| **最後更新** | {YYYY-MM-DD} |
| **負責人** | {QA Lead Name} |
| **SCG Gate** | SCG-4 □ 待審 / □ 通過 / □ 未通過 |
| **前置文件** | SRD-{project}.md, FRD-{project}.md |

---

## 1. 測試範圍與目標

### 1.1 測試範圍（In Scope）

| 功能模組 | 測試類型 | 優先級 |
|---------|---------|-------|
| {Module-A} | Unit / Integration / E2E | P0/P1/P2 |
| {Module-B} | Unit / Integration | P1 |

### 1.2 排除範圍（Out of Scope）

- [ ] {Excluded-Item-1}：原因 {reason}
- [ ] {Excluded-Item-2}：原因 {reason}

### 1.3 測試目標

```
1. 確保所有 AC（Acceptance Criteria）均有對應 AT（Acceptance Test）
2. 覆蓋率達到 Test Pyramid Spec 所定義目標
3. 關鍵業務流程 E2E 覆蓋率 100%
4. 性能指標符合 PBS（Performance Baseline Spec）
5. 安全測試覆蓋 OWASP Top 10
```

---

## 2. 測試金字塔規格（Test Pyramid Spec）

> **SDD 原則**: 測試金字塔是規格，不是目標。每層必須在此文件明確定義。

```
           ┌─────────────┐
           │     E2E     │  {X}% — 覆蓋關鍵使用者旅程
           ├─────────────┤
           │     API     │  {X}% — 所有 API 端點 + Contract Tests
           ├─────────────┤
           │  Integration│  {X}% — 服務整合層
           ├─────────────┤
           │    Unit     │  {X}% — 業務邏輯核心 (≥ 70% coverage)
           └─────────────┘
```

### 2.1 各層規格定義

| 測試層 | 比例目標 | 覆蓋率目標 | 執行頻率 | 工具 | 負責人 |
|-------|---------|----------|---------|------|-------|
| Unit | 40-50% | ≥ 70% code coverage | 每次 PR | {tool} | Dev |
| Integration | 25-30% | 所有整合點 | 每次 PR | {tool} | Dev + QA |
| API/Contract | 25-30% | 所有 API 端點 | 每次 PR | {tool} | QA Automation |
| E2E | 10-15% | 關鍵使用者旅程 | 每日 | {tool} | QA Automation |
| Performance | — | PBS SLO 達標 | 每次發布 | {tool} | Perf Eng |
| Security | — | OWASP Top 10 | 每次發布 | {tool} | Security Eng |

### 2.2 失敗處理策略

| 測試層 | 失敗處理 |
|-------|---------|
| Unit | 立即阻擋 CI，開發者修復後重試 |
| Integration | 阻擋 CI，識別根因後修復 |
| API/Contract | 阻擋 CI，契約違反需 Contract Owner 確認 |
| E2E | 告警通知，評估是否阻擋發布 |
| Performance | SLO 未達標阻擋發布 |
| Security | 高/關鍵級別漏洞阻擋發布 |

---

## 3. 覆蓋率 SLA（Coverage SLA）

> **SDD 原則**: 覆蓋率 SLA 必須量化，並由 CI Quality Gate 自動驗證。

| 指標 | 目標值 | 閾值（最低可接受） | 驗證方式 |
|-----|-------|----------------|---------|
| 行覆蓋率（Line Coverage） | ≥ 80% | ≥ 70% | CI Quality Gate |
| 分支覆蓋率（Branch Coverage） | ≥ 75% | ≥ 65% | CI Quality Gate |
| 功能覆蓋率（Feature Coverage） | 100% | 95% | RTM 追蹤 |
| AC → AT 映射覆蓋率 | 100% | 100% | RTM 追蹤 |
| E2E 關鍵旅程覆蓋 | 100% | 100% | E2E 測試套件 |
| API Contract 覆蓋 | 100% | 100% | Contract Test |

---

## 4. 測試工具選型

> **SDD 原則**: 工具選型決策需有對應 ADR（見 `AUTOMATION-FRAMEWORK-ADR-TEMPLATE.md`）

| 測試類型 | 選定工具 | ADR 參考 | 理由摘要 |
|---------|---------|---------|---------|
| Unit Test | {tool} | ADR-{NNN} | {reason} |
| Integration Test | {tool} | ADR-{NNN} | {reason} |
| API Test | {tool} | ADR-{NNN} | {reason} |
| Contract Test | Pact | ADR-{NNN} | Consumer-Driven Contract |
| E2E Test | {tool} | ADR-{NNN} | {reason} |
| Performance Test | {tool} | ADR-{NNN} | {reason} |
| SAST | {tool} | ADR-{NNN} | {reason} |
| DAST | OWASP ZAP / Burp Suite | ADR-{NNN} | {reason} |

---

## 5. 測試環境規格

| 環境 | 用途 | 測試類型 | 資料策略 |
|-----|------|---------|---------|
| Dev | 開發驗證 | Unit + Integration | Mock Data |
| QA | 完整功能測試 | 全部類型 | Anonymized Prod Data |
| Staging | 預生產驗證 | E2E + Performance + Security | Near-Prod Data |
| Production | 冒煙測試 | Smoke Test | Real Data（只讀） |

---

## 6. CI 整合規格

```yaml
# CI Pipeline Test Stages（基於 Test Pyramid Spec）
stages:
  L0_DocLint:
    - TestSpec-Validate: 確認 RTM AC→AT 100% 映射
    - 覆蓋率目標已在 TSS 定義
  L1_Unit:
    - 執行所有 Unit Tests
    - Quality Gate: code coverage ≥ {X}%
  L2_Integration:
    - Contract Tests（取代 Mock-Based Integration Tests）
    - Integration Tests
    - API Tests
  L2_E2E:
    - 關鍵使用者旅程 E2E
    - RTM Coverage Report 自動生成
  Quality_Gate:
    - 覆蓋率 < 目標自動失敗
    - 未通過 Quality Gate → 阻擋部署
```

---

## 7. 缺陷管理策略

> 詳細規格見 `DEFECT-CLASSIFICATION-SPEC-TEMPLATE.md`

| 嚴重度 | 定義 | SLA（修復時間） | 阻擋發布？ |
|-------|------|--------------|----------|
| Critical | 系統崩潰 / 資料遺失 / 安全漏洞 | 24 小時 | 是 |
| High | 主要功能失效 | 72 小時 | 是 |
| Medium | 功能降級但可用 | 1 週 | 否（需記錄） |
| Low | 輕微問題 | 2 週 | 否 |

---

## 8. 退出標準（Exit Criteria）

### 8.1 測試完成標準

- [ ] 所有 Unit Tests 通過，覆蓋率達標
- [ ] 所有 Contract Tests 通過（零違反）
- [ ] 所有 Integration Tests 通過
- [ ] E2E 關鍵旅程測試通過
- [ ] RTM AC→AT 覆蓋率 100%
- [ ] 無 Critical/High 未解決缺陷
- [ ] Performance SLO 達標
- [ ] Security SAST/DAST 通過（無高/關鍵漏洞）

### 8.2 SCG-4 Gate 通過標準

| 驗證項目 | 判斷標準 | 狀態 |
|---------|---------|------|
| Test Pyramid 比例已定義 | 每層有明確百分比 | □ |
| 覆蓋率 SLA 量化 | 有最低可接受閾值 | □ |
| 工具選型 ADR 完成 | 每個工具有 ADR 參考 | □ |
| CI 整合規格完整 | 每個 CI Stage 已定義 | □ |
| 退出標準可量化 | 有明確數值目標 | □ |

---

## 9. RTM 連結

| 文件 | 路徑 |
|------|------|
| RTM（含 AT 層） | `docs/03_testing/RTM-{project}-{date}.md` |
| Test Contract Spec | `docs/03_testing/contracts/TCS-{feature}.md` |
| Defect Classification Spec | `docs/03_testing/DEFECT-CLASSIFICATION-SPEC-{project}.md` |
| Living Test Report | `docs/03_testing/LIVING-TEST-REPORT-{project}.md` |

---

## 📋 SCG-4 人工確認點

> 🔴 **必須等待人工確認後才能開始開發**

- [ ] 測試策略與業務目標一致
- [ ] 覆蓋率 SLA 目標實際可行
- [ ] 工具選型 ADR 已審閱通過
- [ ] CI 整合設計合理
- [ ] 退出標準明確可驗證

**確認人**: ____________  **確認日期**: ____________  **狀態**: □ 通過 / □ 待修訂
