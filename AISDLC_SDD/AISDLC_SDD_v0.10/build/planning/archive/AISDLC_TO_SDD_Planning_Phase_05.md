# AISDLC → SDD 轉型執行藍圖 Phase 05
# 品質情境：Testing（測試與QA）+ Performance（效能調校）+ Security（安全合規）

**版本**: v1.0
**建立日期**: 2026-04-11
**前置條件**: Phase 01、02、03、04 完成
**文件類型**: 規劃文件（Planning）
**所屬分類**: docs/04_planning/

---

## 📋 Phase 05 目標

針對 **「Spec-First 品質保證」** 的三個核心情境進行 SDD 整合：
1. **Testing**：測試策略本身即是規格，先定義再執行
2. **Performance**：效能 SLO/SLA 必須先規格化，再測試驗證
3. **Security**：STRIDE 威脅模型是安全設計的核心規格

> 💡 **SDD 洞察**：品質不是事後驗證的，而是從規格設計時就內建的。
> Testing / Performance / Security 的 SDD 轉型核心在於：
> **「Quality Contract」— 品質契約先行於實作。**

---

## 🔵 情境八：Testing（測試與QA）

### SDD 強化分析

**Testing 的 SDD 轉型**：從「測試驗收」到「測試即規格」

| 現狀 | SDD 目標 |
|------|---------|
| 測試計畫在 Story 後撰寫 | Test Strategy Spec 與 Story 同步定義 |
| AC 定義模糊 | AC 直接生成 AT（Acceptance Test）規格 |
| 測試覆蓋率目標模糊 | 覆蓋率 SLA 在策略文件中明確定義 |
| 測試類型不系統化 | 測試金字塔規格（比例明確） |
| 整合測試依賴 Mock | Contract Test 取代 Mock（基於 CDC） |

### 測試金字塔規格（Test Pyramid Spec）

```
SDD 中的測試金字塔是規格，不是目標：

           ┌───────┐
           │  E2E  │  ← 規格：覆蓋關鍵使用者旅程 10-15%
           ├───────┤
           │  API  │  ← 規格：所有 API 端點 + Contract Tests 25-30%
           ├───────┤
           │ Integ │  ← 規格：服務整合層 25-30%
           ├───────┤
           │ Unit  │  ← 規格：業務邏輯核心 ≥ 70% 覆蓋率 40-50%
           └───────┘

每層必須在 Test Strategy Spec 中明確定義：
- 覆蓋比例目標
- 使用工具
- 執行頻率
- 失敗處理策略
```

### SDD 強化版 Testing 流程

```
Stage 0: 測試策略規格（🆕 SDD 先行）
  ├── qa-lead: Test Strategy Specification Document
  │     ├── 測試金字塔比例規格
  │     ├── 覆蓋率 SLA（各層目標）
  │     ├── 測試工具選型 ADR
  │     └── CI 整合規格
  └── 🔷 SCG-4 → 🔴 Human: 策略規格凍結

Stage 1: AC → AT 映射規格（SDD 強化）
  ├── qa-lead + qa-tester: Test Contract Spec
  │     每個 AC 必須有對應 AT（可自動化的格式）
  ├── 🆕 RTM 更新（AC → AT 層完成）
  └── 🔴 Human: 測試規格確認

Stage 2: 自動化測試規格
  ├── qa-automation: 自動化框架 ADR（選型決策）
  ├── qa-automation: 自動化測試腳本規格（命名/結構/報告）
  ├── qa-lead: L2 Full Test Specification
  └── 🔴 Human: 自動化策略確認

Stage 3: Contract Test 規格化（🆕 SDD 強化）
  ├── qa-lead: Consumer Contract Test Spec（整合測試升級）
  ├── 替換所有 Mock-Based Integration Tests → Contract Tests
  └── 🔴 Human: Contract Test 策略確認

Stage 4: 測試執行規格
  ├── qa-lead: 測試執行計畫（各環境/各階段）
  ├── qa-lead: 缺陷分類規格（嚴重度/優先級標準）
  └── 🔴 Human: 測試範圍確認

Stage 5: 測試報告規格（Living Test Report）
  ├── qa-lead: 測試報告格式規格
  ├── 🆕 自動化生成：RTM Coverage Report
  └── 🔴 Human: 品質門檻確認（Quality Gate）
```

### Testing SDD 執行 Checklist

#### 5.1 Testing — 文件準備

- [ ] 5.1.1 Stage 0 新增：Test Strategy Specification Document（測試策略規格）
- [ ] 5.1.2 Stage 0 新增：測試金字塔規格（每層比例和覆蓋率目標明確）
- [ ] 5.1.3 Stage 0 新增：測試工具選型 ADR
- [ ] 5.1.4 Stage 1 強化：Test Contract Spec（AC → AT 完整映射）
- [ ] 5.1.5 Stage 1 強化：RTM 完整（加入 AT 層）
- [ ] 5.1.6 Stage 2 新增：自動化框架 ADR（工具選型決策）
- [ ] 5.1.7 Stage 3 新增：Contract Test Spec（取代 Mock-Based Integration Tests）
- [ ] 5.1.8 Stage 4 新增：缺陷分類規格（Defect Classification Spec）
- [ ] 5.1.9 Stage 5 新增：測試報告格式規格（Living Test Report）

#### 5.2 Testing — Agent 設定變更

- [ ] 5.2.1 `qa-lead-zh.yaml`：新增 `test_strategy_spec` Skill（策略規格化）
- [ ] 5.2.2 `qa-lead-zh.yaml`：新增 `test_pyramid_spec_gen`（金字塔規格生成）
- [ ] 5.2.3 `qa-lead-zh.yaml`：新增 `test_contract_gen`（AC → AT 映射）
- [ ] 5.2.4 `qa-automation-zh.yaml`：新增「自動化框架 ADR 模板」
- [ ] 5.2.5 `qa-tester-zh.yaml`：強化「可自動化的 AT 格式」規範
- [ ] 5.2.6 `dev-developer-zh.yaml`：新增「測試性設計（Testability by Design）」提示詞

#### 5.3 Testing — CI/CD Pipeline 調整

- [ ] 5.3.1 L0：`DocLint` + `TestSpec-Validate`（測試規格完整性）
- [ ] 5.3.2 L1：Unit Test（基於 Test Pyramid Spec）
- [ ] 5.3.3 SAST：靜態安全掃描
- [ ] 5.3.4 **L2 Full（SDD 強化）**：
  - Contract Tests（取代 Mock Integration）
  - Integration Tests（基於 Test Pyramid Spec）
  - E2E Tests（覆蓋關鍵使用者旅程）
  - RTM Coverage Report 自動生成
- [ ] 5.3.5 🆕 Quality Gate：覆蓋率 < 目標時自動失敗
- [ ] 5.3.6 🔔 Notify: Standard

---

## 🟡 情境九：Performance（效能調校）

### SDD 強化分析

**Performance 的 SDD 核心**：
> 「效能優化沒有規格，就是在黑暗中射箭」

**SLO/SLA Spec-First 原則**：
- 效能目標（SLO）必須在測試**前**定義
- 優化目標必須可量化、可驗證
- Benchmark 結果必須對照 SLO 規格解讀

### SLO/SLA Spec 設計框架

```
Performance Baseline Spec（PBS）結構：

1. 系統 SLO 定義
   ├── Availability: 99.9% / 99.99%
   ├── Latency P50: < 100ms
   ├── Latency P95: < 500ms
   ├── Latency P99: < 1000ms
   ├── Throughput: > 1000 RPS
   └── Error Rate: < 0.1%

2. 測試場景規格
   ├── 正常負載（Normal Load）: X concurrent users
   ├── 峰值負載（Peak Load）: Y concurrent users
   └── 壓力測試（Stress Load）: Z concurrent users

3. 通過標準（Pass/Fail Criteria）
   └── 所有 SLO 在峰值負載下仍然達標

4. 優化目標（如需改善）
   └── 每個優化迭代必須對應改善的 SLO 指標
```

### SDD 強化版 Performance 流程

```
Stage 0: 效能 SLO/SLA 規格（🆕 SDD 強制先行）
  ├── performance-engineer: Performance Baseline Spec（PBS）
  │     ├── 系統 SLO 定義（Latency/Throughput/Error Rate）
  │     ├── 測試場景規格（Normal/Peak/Stress）
  │     └── 通過標準（可量化）
  ├── sd: 效能架構 ADR（優化策略選型）
  └── 🔷 SCG-6 → 🔴 Human: PBS 規格凍結

Stage 1: 效能測試工具規格
  ├── qa-automation: 效能測試框架 ADR
  ├── qa-automation: 測試腳本規格（基於 PBS 場景）
  └── 🔴 Human: 測試工具確認

Stage 2: Baseline Measurement（基準測量）
  ├── performance-engineer: 執行 Baseline Benchmark
  ├── 產出：Baseline Performance Report（對照 PBS）
  └── 🔴 Human: 基準確認（差距識別）

Stage 3: 瓶頸分析規格
  ├── performance-engineer: 瓶頸分析報告
  ├── dev-senior / code-analyzer: 程式碼層瓶頸分析
  ├── sd: 架構層瓶頸分析
  └── 每個瓶頸必須有「量化影響評估」

Stage 4: 優化 ADR（每個優化決策）
  ├── 每個優化措施必須有：
  │     ├── 預期改善量（量化）
  │     ├── 對應 SLO 指標
  │     └── 實施風險
  └── 🔴 Human: 優化策略確認

Stage 5: 迭代優化循環
  ├── 執行優化措施
  ├── 執行 Benchmark（對照 PBS）
  ├── 更新 Performance Report
  └── SLO 達標？→ 是 → 🔴 完成 | 否 → 繼續迭代

Stage 6: 監控規格化（SDD 強化）
  ├── devops: 監控告警規格（基於 SLO）
  └── 所有 SLO 必須有對應監控告警
```

### Performance SDD 執行 Checklist

#### 5.4 Performance — 文件準備

- [ ] 5.4.1 Stage 0 強制：Performance Baseline Spec（PBS）先於任何測試
- [ ] 5.4.2 Stage 0 強制：SLO 定義（Latency P50/P95/P99、Throughput、Error Rate）
- [ ] 5.4.3 Stage 0 強制：測試場景規格（Normal/Peak/Stress 場景定義）
- [ ] 5.4.4 Stage 0 強制：通過標準（Pass/Fail Criteria）量化定義
- [ ] 5.4.5 Stage 1 新增：效能測試框架 ADR（工具選型決策）
- [ ] 5.4.6 Stage 2 新增：Baseline Performance Report（對照 PBS 的基準報告）
- [ ] 5.4.7 Stage 4 強化：每個優化措施必須有量化 ADR
- [ ] 5.4.8 Stage 6 新增：監控告警規格（每個 SLO 有對應告警）

#### 5.5 Performance — Agent 設定變更

- [ ] 5.5.1 `performance-engineer-zh.yaml`：新增 `slo_sla_spec` Skill
- [ ] 5.5.2 `performance-engineer-zh.yaml`：新增 `baseline_benchmark_spec`（PBS 格式標準）
- [ ] 5.5.3 `performance-engineer-zh.yaml`：新增「優化 ADR 格式」（量化改善預期）
- [ ] 5.5.4 `qa-automation-zh.yaml`：新增「效能測試場景規格格式」
- [ ] 5.5.5 `devops-engineer-zh.yaml`：新增「SLO 告警規格化」能力

#### 5.6 Performance — CI/CD Pipeline 調整

- [ ] 5.6.1 L0：`DocLint` + `PBS-Validate`（SLO 規格完整性）
- [ ] 5.6.2 L1：Unit Test
- [ ] 5.6.3 Container：容器化驗證
- [ ] 5.6.4 **🔴 Benchmark（SDD 強化）**：
  - 每次部署執行 Baseline Benchmark
  - 對照 PBS 自動判斷通過/失敗
  - SLO 未達標自動阻擋部署
- [ ] 5.6.5 🔔 Notify: Advanced（效能退化即時通知）

---

## 🔴 情境十：Security（安全與合規）

### SDD 強化分析

**Security 的 SDD 核心**：
> STRIDE 威脅模型是安全設計的核心規格文件，必須先於實作

**Security Architecture Document（SAD）框架**：
```
SAD 是 Security 情境的 SDD 核心產出：

1. 系統資產清單（What to protect）
2. STRIDE 威脅模型（What can go wrong）
   ├── Spoofing（偽造身份）
   ├── Tampering（篡改資料）
   ├── Repudiation（否認行為）
   ├── Information Disclosure（資訊洩露）
   ├── Denial of Service（服務拒絕）
   └── Elevation of Privilege（特權提升）
3. 風險評估矩陣（Risk = Probability × Impact）
4. 安全控制規格（Security Controls Spec）
5. 安全測試計畫（Security Test Spec）
```

### SDD 強化版 Security 流程

```
Stage 0: 安全範圍規格（🆕 SDD 先行）
  ├── security-engineer: 系統資產清單
  ├── security-engineer: 信任邊界識別
  └── 🔴 Human: 安全範圍確認

Stage 1: STRIDE 威脅模型（SDD 核心規格）
  ├── security-engineer: STRIDE 分析
  │     每個威脅必須有：
  │     ├── 威脅描述
  │     ├── 影響評估（High/Medium/Low）
  │     ├── 可能性評估
  │     └── 緩解措施規格
  ├── sd: 安全架構 ADR（安全控制決策）
  └── 🔷 SCG-5 → 🔴 Human: 威脅模型凍結

Stage 2: Security Architecture Document（SAD）
  ├── security-engineer: 完整 SAD
  │     ├── STRIDE 矩陣
  │     ├── 安全控制規格（Authentication/Authorization/Encryption）
  │     ├── 資料分類規格（PII/PHI/Public/Internal）
  │     └── 安全 API 規格（OAuth 2.0/JWT 標準）
  └── 🔷 SCG-5 → 🔴 Human: SAD 凍結

Stage 3: 合規規格（GDPR/PCI-DSS/ISO 27001）
  ├── compliance-officer: 合規對照矩陣
  ├── compliance-officer: 合規控制清單
  └── 🔴 Human: 合規範圍確認

Stage 4: 安全測試規格（先於 DAST/Pentest）
  ├── security-engineer + qa-lead: Security Test Spec
  │     ├── SAST 規格（工具/規則集/通過標準）
  │     ├── DAST 規格（掃描範圍/頻率/通過標準）
  │     ├── Pentest 範圍規格（如需要）
  │     └── 安全回歸測試規格
  └── 🔷 SCG-5 → 🔴 Human: 安全測試規格凍結

Stage 5: 安全 CI/CD Pipeline 設計
  ├── devops: SAST/DAST 整合規格
  ├── devops: Container Security Scan 規格
  └── devops: Compliance Check 自動化規格

Stage 6: 安全監控規格
  ├── security-engineer: Security Event Monitoring Spec
  ├── security-engineer: Incident Response Spec
  └── 🔴 Human: 安全監控確認
```

### Security SDD 執行 Checklist

#### 5.7 Security — 文件準備

- [ ] 5.7.1 Stage 0 強制：系統資產清單（What to protect）
- [ ] 5.7.2 Stage 0 強制：信任邊界識別（Trust Boundary Map）
- [ ] 5.7.3 Stage 1 強制：STRIDE 威脅模型（每個威脅有完整評估）
- [ ] 5.7.4 Stage 1 強制：安全控制 ADR（每個安全決策）
- [ ] 5.7.5 Stage 2 強制：Security Architecture Document（SAD）完整版
  - [ ] 資料分類規格
  - [ ] 安全 API 規格（OAuth 2.0/JWT）
  - [ ] 加密規格（傳輸/靜態/密鑰管理）
- [ ] 5.7.6 Stage 3 強化：合規對照矩陣（GDPR/PCI-DSS/ISO 27001 條款對應）
- [ ] 5.7.7 Stage 4 強制：Security Test Spec（SAST/DAST 規格先行）
- [ ] 5.7.8 Stage 4 新增：安全回歸測試規格（新威脅出現時更新）
- [ ] 5.7.9 Stage 6 新增：Security Event Monitoring Spec（監控告警規格）
- [ ] 5.7.10 Stage 6 新增：Incident Response Spec（事件回應規格）

#### 5.8 Security — Agent 設定變更

- [ ] 5.8.1 `security-engineer-zh.yaml`：新增 `stride_threat_model` Skill（STRIDE 格式化）
- [ ] 5.8.2 `security-engineer-zh.yaml`：新增 `security_arch_doc`（SAD 生成）
- [ ] 5.8.3 `security-engineer-zh.yaml`：新增「資產分類規格」標準格式
- [ ] 5.8.4 `compliance-officer-zh.yaml`：新增「合規對照矩陣格式」
- [ ] 5.8.5 `compliance-officer-zh.yaml`：新增「多合規框架並行」能力（GDPR + ISO 27001 同時）
- [ ] 5.8.6 `qa-lead-zh.yaml`：新增「Security Test Spec」格式（安全測試場景）
- [ ] 5.8.7 `devops-engineer-zh.yaml`：新增「SAST/DAST CI 整合規格」

#### 5.9 Security — CI/CD Pipeline 調整

- [ ] 5.9.1 L0：`DocLint` + `STRIDE-Validate`（威脅模型完整性）
- [ ] 5.9.2 L1：Unit Test + Security Unit Test
- [ ] 5.9.3 **SAST（SDD 強化）**：
  - 規則集基於 SAD 的安全控制規格
  - OWASP Top 10 自動覆蓋
  - 依賴漏洞掃描（SCA）
- [ ] 5.9.4 Container：容器安全掃描（Image Vulnerability Scan）
- [ ] 5.9.5 **DAST（SDD 強化）**：
  - 掃描範圍基於 Security Test Spec
  - 自動對照 STRIDE 威脅清單
- [ ] 5.9.6 **Compliance Check（SDD 新增）**：
  - 自動驗證合規對照矩陣項目
- [ ] 5.9.7 🔔 Notify: Enhanced（任何高風險安全問題即時通知）

### Security SDD 新增必產文件

| 文件 | 說明 | 存放位置 |
|------|------|---------|
| `ASSET-INVENTORY.md` | 系統資產清單 | `docs/06_quality/security/` |
| `TRUST-BOUNDARY-MAP.md` | 信任邊界圖 | `docs/02_architecture/` |
| `STRIDE-THREAT-MODEL.md` | STRIDE 威脅模型 | `docs/06_quality/security/` |
| `SAD-{system}-{date}.md` | 安全架構文件 | `docs/06_quality/security/` |
| `COMPLIANCE-MATRIX.md` | 合規對照矩陣 | `docs/06_quality/security/` |
| `SECURITY-TEST-SPEC.md` | 安全測試規格 | `docs/03_testing/` |
| `SECURITY-MONITORING-SPEC.md` | 安全監控規格 | `docs/08_deployment/` |
| `INCIDENT-RESPONSE-SPEC.md` | 事件回應規格 | `docs/06_quality/security/` |

---

## 📊 Phase 05 完成標準（Definition of Done）

| 情境 | 驗證項目 | 預期結果 |
|------|---------|---------|
| Testing | Test Strategy Spec 存在 | 測試金字塔比例已定義 |
| Testing | RTM 完整 | AC → AT 100% 映射 |
| Testing | Quality Gate | CI 覆蓋率目標自動驗證 |
| Performance | PBS 先於 Benchmark | SLO 規格在測試前存在 |
| Performance | Benchmark 對照 PBS | 每次 Benchmark 有對照分析 |
| Security | STRIDE 模型完整 | 所有威脅類型已評估 |
| Security | SAD 存在 | 安全架構文件完整 |
| Security | DAST 整合 | CI 包含動態安全掃描 |

---

**上一階段**: [Phase 04 - Migration & DevOps & Integration](AISDLC_TO_SDD_Planning_Phase_04.md)
**下一階段**: [Phase 06 - Final Validation & Rollout](AISDLC_TO_SDD_Planning_Phase_06.md)

**建立者**: 首席 AI-SDLC 轉型架構師
**最後更新**: 2026-04-11
