# AISDLC → SDD 轉型執行藍圖 Phase 04
# 基礎設施情境：Migration（技術棧遷移）+ DevOps（CI/CD）+ Integration（第三方整合）

**版本**: v1.0
**建立日期**: 2026-04-11
**前置條件**: Phase 01、02、03 完成
**文件類型**: 規劃文件（Planning）
**所屬分類**: docs/04_planning/

---

## 📋 Phase 04 目標

針對 **「Contract-Driven（契約驅動）」** 最關鍵的三個情境進行 SDD 深度整合：
1. **Migration**：遷移契約是系統並行運行的核心，必須先規格化
2. **DevOps**：IaC（Infrastructure as Code）即是規格，Pipeline 即是文件
3. **Integration**：Consumer-Driven Contract 是 SDD 在整合情境的最佳實踐

> 💡 **SDD 洞察**：這三個情境都涉及**系統邊界的精確定義**，
> 是 Contract-Driven Development 的主戰場。
> 任何邊界的模糊性都會導致整合失敗或遷移風險。

---

## 🔴 情境五：Migration（技術棧遷移）

### SDD 強化分析

**Migration 是 SDD 最複雜的情境**：

| 複雜度 | 描述 | SDD 對應 |
|--------|------|---------|
| 雙系統並行 | 新舊系統同時運行 | Migration Contract Map（MCM） |
| 資料一致性 | 資料在兩系統間同步 | Data Contract Spec |
| 逐步切換 | Canary / Blue-Green | Cutover Spec |
| 回滾機制 | 出錯必須能回退 | Rollback Spec |

### Migration Contract Map（MCM）設計

```
Migration Contract Map（MCM）是 SDD + Migration 的核心文件：

舊系統 API A ─────────────────────────────────────────────► 新系統 API A'
                          ↕ Contract Bridge
舊系統 DB Schema ──────────────────────────────────────────► 新 DB Schema
                        ↕ Data Migration Contract

MCM 定義：
- 每個 API 的舊→新映射關係
- 資料欄位的舊→新轉換規則
- 並行期間的路由規則
- 切換觸發條件
- 回滾觸發條件
```

### SDD 強化版 Migration 流程

```
Stage 0: 遷移評估（SDD 先行）
  ├── code-analyzer: 舊系統複雜度量化
  ├── sa: 業務功能清單（100% 完整）
  ├── sd: 舊系統 C4 圖（As-Is Architecture）
  └── 🔴 Human: 遷移可行性確認

Stage 1: 遷移策略規格（關鍵）
  ├── sd + sa: Migration Strategy ADR
  │     選擇：Big Bang / Strangler Fig / Database-First / Event-Driven Migration
  ├── sd: 遷移架構設計（並行運行架構）
  ├── 🆕 sd: Migration Contract Map（MCM）骨架
  └── 🔷 SCG-2 → 🔴 Human: 遷移策略凍結

Stage 2: 契約規格化（SDD 核心）
  ├── sd + integration-specialist: Migration Contract Map（MCM）完整版
  │   ├── API Mapping Contract（舊→新 API 映射）
  │   ├── Data Migration Contract（欄位映射 + 轉換規則）
  │   ├── Routing Contract（流量路由規則）
  │   └── Consistency Contract（資料一致性保證）
  ├── 🆕 Backward Compatibility Contract（向後相容性保證）
  └── 🔷 SCG-3 → 🔴 Human: 契約凍結（開發前）

Stage 3: Cutover & Rollback Spec（🆕 SDD 強制）
  ├── devops: Cutover Spec（切換觸發條件 + 步驟）
  ├── devops: Rollback Spec（回滾觸發條件 + 步驟）
  ├── devops: Blue-Green / Canary 部署規格
  └── 🔴 Human: Cutover 策略確認

Stage 4: L2 Contract 測試規格（SDD 強化）
  ├── qa: Contract Test Spec（基於 MCM）
  │     每個 API 映射必須有對應契約測試
  ├── qa: Data Integrity Test Spec
  ├── 🆕 Consumer-Driven Contract Tests（integration-specialist）
  └── 🔷 SCG-4 → 🔴 Human: 測試規格凍結

Stage 5-N: 分層遷移執行
  └── [每層：DB → 後端 → 前端，依 MCM 執行]
      ├── 每層完成後：Contract Test 全部通過
      └── 🔴 Human: 每層切換確認

Stage Final: L3 Canary 規格
  ├── devops: Canary Release Spec（%流量規格）
  └── 🔴 Human: 全量切換確認
```

### Migration SDD 執行 Checklist

#### 4.1 Migration — 文件準備

- [ ] 4.1.1 Stage 0 強制：As-Is C4 圖（舊系統完整架構）
- [ ] 4.1.2 Stage 0 強制：業務功能完整清單（100%，無遺漏）
- [ ] 4.1.3 Stage 1 強制：Migration Strategy ADR（遷移策略決策文件）
- [ ] 4.1.4 Stage 2 強制（開發前）：Migration Contract Map（MCM）完整版
  - [ ] API Mapping Contract
  - [ ] Data Migration Contract
  - [ ] Routing Contract
  - [ ] Consistency Contract
- [ ] 4.1.5 Stage 2 強制：Backward Compatibility Contract
- [ ] 4.1.6 Stage 3 強制：Cutover Spec（切換步驟規格）
- [ ] 4.1.7 Stage 3 強制：Rollback Spec（回滾步驟規格）
- [ ] 4.1.8 Stage 4 強制：Contract Test Spec（基於 MCM 的測試規格）
- [ ] 4.1.9 Stage 4 強制：Data Integrity Test Spec
- [ ] 4.1.10 Stage Final：Canary Release Spec（流量百分比規格）

#### 4.2 Migration — Agent 設定變更

- [ ] 4.2.1 `sd-architect-zh.yaml`：新增 `migration_contract_map_gen` Skill
- [ ] 4.2.2 `sd-architect-zh.yaml`：新增「遷移 ADR 格式」（Big Bang/Strangler/Event-Driven 分支）
- [ ] 4.2.3 `integration-specialist-zh.yaml`：新增 `consumer_driven_contract`（MCM 場景）
- [ ] 4.2.4 `devops-engineer-zh.yaml`：新增 `cutover_spec_gen`（切換規格生成）
- [ ] 4.2.5 `devops-engineer-zh.yaml`：新增 `rollback_spec_gen`（回滾規格生成）
- [ ] 4.2.6 `qa-tester-zh.yaml`：新增 `contract_test_gen`（基於 MCM 的契約測試）
- [ ] 4.2.7 `sa-analyst-zh.yaml`：新增「業務功能 100% 清單提取」驗證邏輯

#### 4.3 Migration — CI/CD Pipeline 調整

- [ ] 4.3.1 L0：`DocLint` + `MCM-Validate`（MCM 完整性驗證）
- [ ] 4.3.2 L1：Unit Test + Build Check
- [ ] 4.3.3 SAST：靜態安全掃描
- [ ] 4.3.4 Container：容器化驗證
- [ ] 4.3.5 **L2 Contract Test（SDD 強化）**：
  - 基於 MCM 自動生成契約測試
  - 每個 API 映射必須通過
  - 資料完整性驗證
- [ ] 4.3.6 **L3 Canary（SDD 強化）**：依 Canary Release Spec 執行
- [ ] 4.3.7 🔔 Notify: Advanced（每個遷移層完成通知）

### Migration SDD 新增必產文件

| 文件 | 說明 | 存放位置 |
|------|------|---------|
| `AS-IS-C4-{system}.md` | 舊系統架構 C4 圖 | `docs/02_architecture/` |
| `MIGRATION-CONTRACT-MAP-{system}.md` | 遷移契約地圖 | `docs/02_architecture/migration/` |
| `MIGRATION-ADR-{NNN}.md` | 遷移策略決策 ADR | `docs/02_architecture/adr/` |
| `CUTOVER-SPEC-{system}.md` | 切換規格 | `docs/08_deployment/` |
| `ROLLBACK-SPEC-{system}.md` | 回滾規格 | `docs/08_deployment/` |
| `CANARY-SPEC-{system}.md` | Canary 部署規格 | `docs/08_deployment/` |
| `CONTRACT-TEST-SPEC-{system}.md` | 契約測試規格 | `docs/03_testing/contracts/` |

---

## 🟠 情境六：DevOps/CI/CD（部署自動化）

### SDD 強化分析

**DevOps 的 SDD 轉型核心**：
> "Infrastructure as Code" → "Infrastructure as **Specification**"

**IaC 即規格原則**：
- 每個 Pipeline Stage 必須有對應的規格說明
- 每個基礎設施決策必須有 ADR
- Pipeline 是系統的**部署契約**

### SDD 強化版 DevOps 流程

```
Stage 1: 基礎設施需求規格（🆕 SDD 先行）
  ├── devops: Infrastructure Requirements Spec
  │     ├── 計算資源規格（CPU/Memory/Storage SLO）
  │     ├── 網路拓撲規格
  │     ├── 安全邊界規格
  │     └── 可用性目標（RTO/RPO）
  ├── sd: 部署架構 ADR（Container/Serverless/VM 選擇）
  └── 🔷 SCG-2 → 🔴 Human: 基礎設施規格凍結

Stage 2: Pipeline 規格化（IaC-as-Spec）
  ├── devops: Pipeline Specification Document
  │     ├── Stage 定義（L0/L1/L2/L3 規格）
  │     ├── 每個 Stage 的輸入/輸出/成功條件
  │     ├── 通知策略規格
  │     └── 失敗處理規格
  ├── qa-automation: 測試自動化整合規格
  └── 🔷 SCG-Pipeline → 🔴 Human: Pipeline 規格確認

Stage 3: IaC 實作（基於規格）
  ├── devops: 依 Infrastructure Requirements Spec 撰寫 IaC
  ├── security-engineer: IaC SAST（安全掃描）
  └── 🔴 Human: IaC 審查確認

Stage 4: L2 Contract Test 整合
  ├── devops + qa-automation: 環境契約測試（確保各環境行為一致）
  └── 🔴 Human: 環境一致性確認

Stage 5: L3 Canary / Blue-Green 規格化
  ├── devops: 切換策略規格
  ├── devops: 監控告警規格（基於 SLO）
  └── 🔴 Human: 生產部署確認
```

### DevOps SDD 執行 Checklist

#### 4.4 DevOps — 文件準備

- [ ] 4.4.1 Stage 1 新增：Infrastructure Requirements Spec（基礎設施需求規格）
- [ ] 4.4.2 Stage 1 新增：部署架構 ADR（技術選型決策）
- [ ] 4.4.3 Stage 1 新增：RTO/RPO 規格（可用性目標定義）
- [ ] 4.4.4 Stage 2 強化：Pipeline Specification Document（每個 Stage 規格化）
- [ ] 4.4.5 Stage 2 強化：IaC 檔案視為規格文件（含充分注解）
- [ ] 4.4.6 Stage 4 新增：環境契約測試規格（Dev/Stage/Prod 一致性）
- [ ] 4.4.7 Stage 5 強化：監控告警規格（告警閾值基於 SLO）

#### 4.5 DevOps — Agent 設定變更

- [ ] 4.5.1 `devops-engineer-zh.yaml`：新增 `iac_specification` Skill
- [ ] 4.5.2 `devops-engineer-zh.yaml`：新增 `pipeline_spec_doc`（Pipeline 規格化）
- [ ] 4.5.3 `devops-engineer-zh.yaml`：新增「IaC 注解標準」（每段 IaC 有對應規格說明）
- [ ] 4.5.4 `sd-architect-zh.yaml`：新增「部署架構 ADR 模板」
- [ ] 4.5.5 `qa-automation-zh.yaml`：新增「環境契約測試」規格

#### 4.6 DevOps — CI/CD Pipeline 調整

- [ ] 4.6.1 L0：`DocLint` + `IaCS-Validate`（IaC 規格完整性）
- [ ] 4.6.2 L1：Unit Test（IaC 單元測試）
- [ ] 4.6.3 **IaC SAST（SDD 強化）**：IaC 安全掃描 + 規格符合性驗證
- [ ] 4.6.4 Container：容器化驗證
- [ ] 4.6.5 **L2 Contract Test**：環境契約測試（環境間行為一致性）
- [ ] 4.6.6 **L3 Canary**：依切換策略規格執行
- [ ] 4.6.7 🔔 Notify: Advanced

### DevOps SDD 新增必產文件

| 文件 | 說明 | 存放位置 |
|------|------|---------|
| `INFRA-REQUIREMENTS-SPEC.md` | 基礎設施需求規格 | `docs/02_architecture/` |
| `ADR-DEPLOYMENT-{NNN}.md` | 部署架構決策 ADR | `docs/02_architecture/adr/` |
| `PIPELINE-SPEC.md` | Pipeline 規格文件 | `docs/08_deployment/iac/` |
| `ENV-CONTRACT-SPEC.md` | 環境契約測試規格 | `docs/03_testing/contracts/` |
| `MONITORING-ALERT-SPEC.md` | 監控告警規格 | `docs/08_deployment/` |

---

## 🟣 情境七：Integration（第三方整合）

### SDD 強化分析

**Integration 的 SDD 核心**：
> Consumer-Driven Contract（CDC）是 Integration 情境的 SDD 最佳實踐

**CDC 工作原理**：
```
消費者（Consumer）定義它期望的 API 行為規格（Contract）
         ↓
Contract 儲存並共享
         ↓
提供者（Provider）驗證自己的 API 符合 Contract
         ↓
任何 API 變更必須通過所有 Consumer Contract 驗證
```

### SDD 強化版 Integration 流程

```
Stage 1: 整合需求規格化
  ├── integration-specialist: 第三方 API 研究報告
  ├── 🆕 integration-specialist: Consumer Contract Draft
  │     「我們期望第三方 API 提供什麼行為」
  ├── sd: 整合架構設計（Anti-Corruption Layer / Gateway）
  ├── sd: 整合 ADR（整合模式選擇）
  └── 🔷 SCG-1 → 🔴 Human: 整合需求確認

Stage 2: API Contract 設計（SDD 核心）
  ├── integration-specialist: OpenAPI Spec（Consumer 視角）
  ├── 🆕 integration-specialist: Consumer-Driven Contract Spec
  │     ├── 期望的請求格式
  │     ├── 期望的回應格式
  │     ├── 期望的錯誤碼
  │     └── SLA 期望（回應時間/可用性）
  ├── sd: Provider API Spec（我們提供給外部的 API）
  └── 🔷 SCG-3 → 🔴 Human: API Contract 凍結

Stage 3: 整合測試規格（Contract Test First）
  ├── qa: Contract Test Spec（基於 Consumer Contract）
  ├── qa: 整合測試計畫（mock/stub 策略）
  ├── 🆕 整合點失敗模擬規格（Chaos Contract）
  └── 🔷 SCG-4 → 🔴 Human: 測試規格確認

Stage 4: 實作（基於規格）
  ├── dev: 依 Consumer Contract 實作 API 客戶端
  ├── dev: Anti-Corruption Layer 實作
  └── [依規格實作，Contract Test 驅動]

Stage 5: Contract Test 執行
  ├── 每個整合點必須通過 Contract Test
  └── 🔴 Human: 整合驗收確認
```

### Integration SDD 執行 Checklist

#### 4.7 Integration — 文件準備

- [ ] 4.7.1 Stage 1 強化：第三方 API 研究報告（正式規格文件）
- [ ] 4.7.2 Stage 1 新增：Consumer Contract Draft（我們的期望規格）
- [ ] 4.7.3 Stage 1 新增：整合 ADR（整合模式決策）
- [ ] 4.7.4 Stage 2 強制：OpenAPI Spec（Consumer 視角，先於實作）
- [ ] 4.7.5 Stage 2 強制：Consumer-Driven Contract Spec（完整版）
- [ ] 4.7.6 Stage 2 強制：Provider API Spec（我們提供給外部）
- [ ] 4.7.7 Stage 3 強化：Contract Test Spec（每個整合點）
- [ ] 4.7.8 Stage 3 新增：失敗模擬規格（Chaos Contract）

#### 4.8 Integration — Agent 設定變更

- [ ] 4.8.1 `integration-specialist-zh.yaml`：強化 `consumer_driven_contract` Skill
- [ ] 4.8.2 `integration-specialist-zh.yaml`：新增「Consumer Contract 格式」標準
- [ ] 4.8.3 `integration-specialist-zh.yaml`：新增 `openapi_spec_gen`（API 研究 → OpenAPI）
- [ ] 4.8.4 `sd-architect-zh.yaml`：新增「Anti-Corruption Layer ADR 模板」
- [ ] 4.8.5 `qa-tester-zh.yaml`：新增「Contract Test Spec 格式」（Integration 場景）
- [ ] 4.8.6 `devops-engineer-zh.yaml`：新增「Contract Test CI 整合」

#### 4.9 Integration — CI/CD Pipeline 調整

- [ ] 4.9.1 L0：`DocLint` + `Contract-Validate`（Consumer Contract 語法驗證）
- [ ] 4.9.2 L1：Unit Test + Mock Contract Test
- [ ] 4.9.3 SAST：靜態安全掃描
- [ ] 4.9.4 Container：容器化驗證
- [ ] 4.9.5 **Contract Test（SDD 核心）**：
  - Consumer Contract Tests 自動執行
  - Provider Contract Verification
  - 任何破壞性變更自動阻擋
- [ ] 4.9.6 🔔 Notify: Advanced（整合失敗即時通知）

### Integration SDD 新增必產文件

| 文件 | 說明 | 存放位置 |
|------|------|---------|
| `THIRD-PARTY-API-RESEARCH-{name}.md` | 第三方 API 研究報告 | `docs/01_requirements/` |
| `CONSUMER-CONTRACT-{provider}.yaml` | Consumer-Driven Contract | `docs/02_architecture/api/` |
| `PROVIDER-API-SPEC-{module}.yaml` | 我們提供的 API 規格 | `docs/02_architecture/api/` |
| `ADR-INTEGRATION-{NNN}.md` | 整合決策 ADR | `docs/02_architecture/adr/` |
| `CONTRACT-TEST-SPEC-{provider}.md` | 契約測試規格 | `docs/03_testing/contracts/` |
| `CHAOS-CONTRACT-{provider}.md` | 失敗模擬規格 | `docs/03_testing/` |

---

## 📊 Phase 04 完成標準（Definition of Done）

| 情境 | 驗證項目 | 預期結果 |
|------|---------|---------|
| Migration | MCM 完整性 | 所有 API/資料欄位映射 100% 覆蓋 |
| Migration | Cutover + Rollback Spec | 兩份規格均存在且可執行 |
| Migration | L2 Contract Test | 契約測試覆蓋所有映射 |
| DevOps | Pipeline Specification | 每個 Stage 有輸入/輸出/成功條件定義 |
| DevOps | IaC 規格完整性 | 每段 IaC 有對應規格說明 |
| Integration | Consumer Contract | 所有整合點有 CDC 規格 |
| Integration | Contract Test CI | CI 自動執行契約測試 |

---

**上一階段**: [Phase 03 - Brownfield & Refactoring](AISDLC_TO_SDD_Planning_Phase_03.md)
**下一階段**: [Phase 05 - Testing & Performance & Security](AISDLC_TO_SDD_Planning_Phase_05.md)

**建立者**: 首席 AI-SDLC 轉型架構師
**最後更新**: 2026-04-11
