# Brownfield Project 舊專案維護與改造 SOP

**版本**: v0.01 | **最後更新**: 2026-03-26

> 📘 **文檔導航**: [快速參考 QuickRef](./SOP_QuickRef.md) | [深度技術指南 DeepDive](./SOP_DeepDive.md) | [情境轉換指引](../SCENARIO_TRANSITION_GUIDE.md)

> 📝 **關於範例連結說明**:
> 本 SOP 中部分連結（如文檔路徑、配置檔案等）為示例性質，
> 展示一般專案的文檔結構。實際使用時，請根據您的專案結構調整路徑。

## 🎯 情境概述

**適用場景**：既有系統的功能改進、Bug 修復、技術改造

**預計時間**:
- 📋 **AISDLC 規劃階段**: 3-4 小時
  - **規劃時間** (AI 分析 + 人工確認): 3-4 小時
  - **執行時間** (依變更複雜度):
    - 小型變更 (Bug修復/小功能): 1-5 天
    - 中型變更 (功能增強/模組改造): 5-10 天
    - 大型變更 (架構調整/大規模改造): 10-20 天
- 🔨 **實際執行階段**: 依變更複雜度而定 (開發/測試/部署)

> 💡 **時間估算說明**:
> - **規劃時間**指使用 AISDLC 流程進行影響分析、設計方案、測試計畫的時間
> - **執行時間**指實際開發、測試、部署的時間，會因系統複雜度、技術債程度、測試完整性而有很大差異
> - 小型變更通常指單一模組的 Bug 修復或小功能新增
> - 中型變更指涉及多個模組的功能增強或部分重構
> - 大型變更指架構層級的調整或大規模技術債清理

**涉及角色**：SA, Code-Analyzer, Dev-Senior, QA, DevOps；選用：Security-Engineer, Compliance-Officer, SD-Mobile-Architect, QA-Mobile-Tester, Integration-Specialist ⭐ v0.01 新增

**最終產出**：影響分析報告 + 變更設計文件 + 測試計劃 + 部署方案 + 回歸測試報告

---

## 🤝 協作模式 (Phase 2: v0.03, v0.01 更新)

### 主要協作模式

#### 1. Lead-Support (主導-支援)
- **主導 Agents**: SA (需求分析), Dev-Senior (技術決策)
- **支援 Agents**: Code-Analyzer, QA, SD
- **使用階段**: 現況分析、影響評估、變更設計
- **模式說明**: SA 主導分析流程，Dev-Senior 主導技術決策，其他 Agents 提供專業支援

#### 2. Sequential-Handoff (順序交接)
- **流程**: Code-Analyzer → 分析報告 → 🔴 → SA → 需求文檔 → 🔴 → Dev-Senior → 實作方案 → 🔴 → QA
- **交接點**: 分析結果 → 變更需求 → 設計方案 → 測試驗證
- **模式說明**: 先分析現況，再定義變更，最後實作和測試

### 次要協作模式

#### 3. Peer-Review (同儕審查)
- **使用階段**: Dev-Senior ↔ Code-Analyzer 代碼品質審查
- **模式說明**: 資深開發者與代碼分析工具互補驗證

---

## 🔒 Layer 0: Security Baseline（強制前置）

> **🔴 v0.01 CI/CD 強化**: 所有 CI/CD Pipeline 建置**必須先完成 Layer 0 安全基線**，再進入後續階段。
> Layer 0 是跨所有情境的強制安全基線，包含 Secret Detection、SCA、License Compliance。

**執行步驟**: 參考 [devops-setup-flow.md 步驟 0](../../workflow/scenario-specific/devops-setup-flow.md)
**配置範本**: [Layer0_Security_Baseline_Template.md](../../docs_template/scenario_specific/devops/Layer0_Security_Baseline_Template.md)
**CI 範本**: [GitHub Actions](../../docs_template/scenario_specific/devops/github-actions/security-baseline.yml) | [GitLab CI](../../docs_template/scenario_specific/devops/gitlab-ci/security-baseline-template.yml)

---

## 🔨 Layer 1: Build & Verify（強制建置驗證）

> **🔴 v0.01 CI/CD 強化**: Layer 0 通過後，**必須完成 Layer 1 建置驗證**。
> Brownfield 情境特殊規則：全局覆蓋率閾值可降至 **65%**，但**新增/修改行**的差異覆蓋率必須 ≥ **85%**。

**Layer 1 三道關卡**:
- Lint + Format Check — 程式碼風格一致性
- Compile / Build — 編譯成功、依賴正確
- Unit Test + Coverage Gate — 差異覆蓋率 ≥ 85%（既有代碼按現狀）

**執行步驟**: 參考 [devops-setup-flow.md 步驟 0.5](../../workflow/scenario-specific/devops-setup-flow.md)
**配置範本**: [Layer1_Build_Verify_Template.md](../../docs_template/scenario_specific/devops/Layer1_Build_Verify_Template.md)
**CI 範本**: [GitHub Actions](../../docs_template/scenario_specific/devops/github-actions/build-verify.yml) | [GitLab CI](../../docs_template/scenario_specific/devops/gitlab-ci/build-verify-template.yml)

---

## 🛡️ 增強安全掃描: SAST（Standard 等級）

> **Brownfield 情境安全等級: Standard** (L0 + L1 + SAST)
> 聚焦新增/修改代碼的 SAST 靜態安全分析，確保變更不引入安全漏洞。

| 掃描類型 | 工具 | 阻塞策略 | 說明 |
|---------|------|---------|------|
| **SAST** | Semgrep / CodeQL | 🔴 Critical/High 阻塞 | 新增/修改代碼靜態分析 |
| **Container Scan** | Trivy / Grype | ⚠️ 有 Docker 時啟用 | 容器映像漏洞掃描 |

**配置範本**: [Security_Scan_Integration_Template.md](../../docs_template/scenario_specific/devops/Security_Scan_Integration_Template.md)
**CI 範本**: [GitHub Actions](../../docs_template/scenario_specific/devops/github-actions/security-scan-enhanced.yml) | [GitLab CI](../../docs_template/scenario_specific/devops/gitlab-ci/security-scan-enhanced-template.yml)

### ⚡ Performance Benchmark Gate（⚠️ 選配）

> Brownfield 情境可選配 Micro-Benchmark，偵測關鍵路徑效能退化。

| 層級 | 觸發時機 | 阻塞策略 | 說明 |
|------|---------|---------|------|
| **Micro-Benchmark** | 每次 PR | 🔴 退化 > 10% 阻塞 | 關鍵路徑效能退化偵測 |

📖 **配置範本**: [Performance_Benchmark_Gate_Template.md](../../docs_template/scenario_specific/devops/Performance_Benchmark_Gate_Template.md)
🔧 **建置流程**: [devops-setup-flow 步驟 0.8](../../workflow/scenario-specific/devops-setup-flow.md)

### 📝 Documentation Pipeline（⚠️ 選配）

> Brownfield 情境可選配 Doc Lint + Link Check，確保文檔更新品質。

📖 **配置範本**: [Documentation_Pipeline_Template.md](../../docs_template/scenario_specific/devops/Documentation_Pipeline_Template.md)
🔧 **建置流程**: [devops-setup-flow 步驟 0.9](../../workflow/scenario-specific/devops-setup-flow.md)

### 🔔 Event-Driven Agent Notification（🔴 強制）

> PR 事件 → Agent 結果匯聚 → PR Comment + Slack 通知，部署完成 → 全員通知。

📖 **配置範本**: [Event_Driven_Agent_Notification_Template.md](../../docs_template/scenario_specific/devops/Event_Driven_Agent_Notification_Template.md)
🔧 **建置流程**: [devops-setup-flow 步驟 0.10](../../workflow/scenario-specific/devops-setup-flow.md)

---

## 📋 前置準備檢查清單

> ⚠️ **重要提示**: 以下前置材料為理想狀態。若材料缺失,請參考「材料缺失應對方案」。

### 必要材料
- [ ] 現有系統代碼庫存取權限
- [ ] 變更需求描述 (Bug report / Feature request / Change request)
- [ ] 系統現有文檔 (架構圖、API 文檔等，如有)
- [ ] 測試環境存取權限
- [ ] 部署權限和流程資訊

### 選擇性材料
- [ ] 既有測試案例和測試數據
- [ ] 系統監控數據 (logs, metrics)
- [ ] 相關 Issue/Ticket 歷史
- [ ] 系統使用者回饋
- [ ] 資料庫 Schema 文檔
- [ ] 依賴系統清單
- [ ] 部署架構圖

### 環境檢查
- [ ] 本地開發環境可運作
- [ ] 可執行現有測試套件
- [ ] 可連接測試資料庫
- [ ] 可存取相關 API/服務

---

## 🔧 材料缺失應對方案

> 💡 **現實情況**: 既有系統常因歷史原因導致文檔不完整或缺失。以下提供實用的替代方案。

| 缺失材料 | 影響程度 | 應對方案 | 預計額外時間 |
|---------|---------|---------|-------------|
| **系統架構文檔** | 🔴 高 | • **方案 1**: 使用 Code-Analyzer 自動生成初步架構圖<br>• **方案 2**: 執行 `dependency-cruiser` 或 `Madge` 生成依賴關係圖<br>• **方案 3**: 訪談資深開發者或系統維護者,繪製簡易架構圖<br>• **方案 4**: 採用「[文檔重建 Workflow](../../workflow/scenario-specific/documentation-reconstruction-flow.md)」先重建基礎文檔 | +2-4 小時 |
| **API 文檔** | 🔴 高 | • **方案 1**: 使用 Code-Analyzer 掃描代碼生成 API 清單<br>• **方案 2**: 使用 Postman/Insomnia 進行逆向工程實測<br>• **方案 3**: 檢查 Swagger/OpenAPI 註解自動生成文檔<br>• **方案 4**: 使用網路抓包工具 (如 Charles/Fiddler) 觀察實際 API 呼叫 | +1-3 小時 |
| **資料庫 Schema 文檔** | 🟡 中 | • **方案 1**: 使用資料庫工具匯出 Schema (MySQL Workbench/pgAdmin/DBeaver)<br>• **方案 2**: 執行 SQL 查詢生成表結構: `SHOW CREATE TABLE` 或 `pg_dump --schema-only`<br>• **方案 3**: 使用 ORM 反向生成 Schema (如 Rails `schema.rb`, Django migrations) | +0.5-1 小時 |
| **測試案例** | 🟡 中 | • **方案 1**: 先進行探索性測試,記錄關鍵使用場景<br>• **方案 2**: 使用 QA-Automation 從需求反推基本測試案例<br>• **方案 3**: 檢查現有代碼中的範例或註解推測預期行為<br>• **方案 4**: 暫時跳過,使用「保守變更策略」降低風險 | +1-2 小時 |
| **部署流程文檔** | 🟡 中 | • **方案 1**: 檢查代碼庫中的 CI/CD 配置檔 (`.github/workflows`, `Jenkinsfile`, `.gitlab-ci.yml`)<br>• **方案 2**: 訪談 DevOps 或維運人員記錄現有流程<br>• **方案 3**: 檢查部署腳本 (`deploy.sh`, `Makefile`, `package.json` scripts)<br>• **方案 4**: 先在測試環境手動部署,記錄步驟 | +1-2 小時 |
| **變更需求詳細說明** | 🔴 高 | • **方案 1**: 與需求提出者 (PM/PO/使用者) 進行需求訪談<br>• **方案 2**: 檢查相關 Issue/Ticket 歷史補充背景資訊<br>• **方案 3**: 分析類似功能或 Bug 推測預期行為<br>• **方案 4**: 使用 SA Agent 協助結構化需求訪談問題清單 | +0.5-2 小時 |
| **系統監控數據** | 🟢 低 | • **方案 1**: 暫時跳過,使用「小範圍測試」策略驗證變更<br>• **方案 2**: 建立基本監控 (如使用免費 APM 工具 Prometheus/Grafana)<br>• **方案 3**: 使用應用日誌分析替代 (ELK Stack 或簡易 log parsing) | +0.5-1 小時 |

### 文檔完全缺失時的完整應對流程

若系統幾乎沒有任何文檔,建議採用「**漸進式文檔重建**」策略:

#### 階段 1: 快速建立最小文檔集 (3-6 小時)
1. **架構概覽** (1-2 小時)
   - 使用 Code-Analyzer 自動掃描生成目錄結構圖
   - 識別主要模組和技術棧
   - 繪製簡易系統架構圖 (可使用 draw.io 或 Mermaid)

2. **API 清單** (1-2 小時)
   - 掃描代碼提取所有 API 端點
   - 使用 Postman 實測並記錄基本請求/回應格式
   - 生成簡易 API 索引文件

3. **資料模型** (1-2 小時)
   - 匯出資料庫 Schema
   - 識別核心資料表和關聯關係
   - 繪製 ERD (Entity Relationship Diagram)

#### 階段 2: 依需求補充特定領域文檔 (2-4 小時)
- 針對本次變更相關的模組,進行深入文檔化
- 記錄關鍵業務邏輯和資料流
- 補充必要的測試案例文檔

#### 階段 3: 持續改進 (長期)
- 每次變更時補充相關文檔
- 逐步建立完整的系統文檔庫

---

## 🛠️ 免費工具替代方案

> 💡 **成本考量**: 既有系統維護與改造需要程式碼分析、重構、測試、文檔管理等工具，商業方案成本高昂（SonarQube Enterprise $150k/年, JetBrains全套 $649/年/人）。以下提供功能相近的免費/開源替代方案。

### 既有系統維護工具對照表

| 工具類別 | 商業方案 | 免費/開源替代 | 功能對比 | 適用場景 |
|---------|---------|-------------|---------|---------|
| **程式碼分析** | SonarQube Enterprise<br>Veracode<br>Checkmarx | **SonarQube CE**<br>**CodeQL (GitHub)**<br>**Semgrep** | 核心功能完整<br>缺少: 企業級報表、合規報告 | 程式碼品質分析<br>技術債務追蹤<br>安全漏洞掃描 |
| **重構工具** | JetBrains Ultimate<br>ReSharper | **VS Code + Extensions**<br>**IntelliJ CE**<br>**Eclipse** | 基本重構功能完整<br>缺少: AI輔助重構 | 程式碼重構<br>架構調整<br>重複程式碼檢測 |
| **依賴管理** | Snyk Pro<br>WhiteSource | **Dependabot (GitHub)**<br>**Renovate**<br>**OWASP Dependency-Check** | 自動化掃描完整<br>免費額度充足 | 套件版本更新<br>安全漏洞檢測<br>授權合規檢查 |
| **測試工具** | TestRail<br>Zephyr Enterprise | **Allure**<br>**ReportPortal**<br>**TestLink** | 開源版功能足夠<br>缺少: BI分析 | 測試案例管理<br>測試報告視覺化<br>迴歸測試追蹤 |
| **API 文檔** | Postman Teams<br>Stoplight | **Swagger/OpenAPI**<br>**Redoc**<br>**Hoppscotch Teams** | 基本功能完整<br>缺少: 協作註解 | API 自動文檔<br>API 測試與監控<br>API 版本管理 |
| **資料庫遷移** | Liquibase Pro<br>Flyway Teams | **Liquibase OSS**<br>**Flyway CE**<br>**golang-migrate** | 核心功能相同<br>免費版夠用 | Schema 版本控制<br>資料庫遷移<br>回滾管理 |
| **日誌分析** | Splunk<br>Datadog Logs | **ELK Stack**<br>**Loki + Grafana**<br>**Graylog** | 開源方案強大<br>需自行維護 | 日誌聚合與搜尋<br>錯誤追蹤<br>系統監控 |
| **變更追蹤** | Jira Software<br>Linear | **GitLab Issues**<br>**Redmine**<br>**Plane** | 免費版功能完整 | 需求變更管理<br>Bug 追蹤<br>技術債追蹤 |

### 推薦工具組合 (依系統規模)

| 系統規模 | 程式碼分析 | 重構工具 | 測試管理 | 依賴管理 | 日誌分析 | 年度成本 |
|---------|----------|---------|---------|---------|---------|---------|
| **小型** (<10萬行) | SonarQube CE / Semgrep | VS Code | Allure | Dependabot | ELK (雲端) | $0-500 |
| **中型** (10-50萬行) | SonarQube CE (自架) | IntelliJ CE | ReportPortal | Renovate + OWASP | ELK (自架) | $0 (自架) |
| **大型** (50萬行+) | CodeQL + SonarQube | 混合使用 | ReportPortal | Snyk + Renovate | Loki + Grafana | $1k-5k/年 |

### 成本對比

| 方案 | 月度成本 (10人團隊) | 年度成本 | 工具組合 | 維護成本 |
|------|-------------------|---------|---------|---------|
| **完全免費 (雲端)** | $0 | $0 | GitHub + Dependabot + Semgrep + VS Code | 低 (雲端服務) |
| **完全免費 (自架)** | $0 | $0 | GitLab + SonarQube CE + ELK + Allure | 中-高 (需維護) |
| **混合方案** | $100-300 | $1,200-3,600 | SonarQube Cloud + Snyk + 其他免費 | 低-中 |
| **全商業方案** | $800-2,000 | $10k-24k | SonarQube Enterprise + JetBrains + Splunk | 低 (廠商支援) |

### 各階段工具建議

#### 系統分析階段
- **程式碼掃描**: SonarQube CE / CodeQL / Semgrep
- **依賴分析**: Dependency-Cruiser / Madge
- **架構視覺化**: Structurizr / PlantUML / C4-PlantUML
- **複雜度分析**: Lizard / SonarQube CE

#### 重構階段
- **IDE**: IntelliJ CE / VS Code + Refactoring Extensions
- **程式碼格式化**: Prettier / Black / gofmt (依語言)
- **Linter**: ESLint / Pylint / golangci-lint (依語言)
- **重複程式碼檢測**: PMD / CPD / SonarQube CE

#### 測試階段
- **單元測試**: Jest / pytest / JUnit (依語言)
- **整合測試**: Testcontainers / Docker Compose
- **E2E 測試**: Playwright / Cypress
- **測試覆蓋率**: Coverage.py / Istanbul / JaCoCo
- **測試報告**: Allure / ReportPortal

#### 部署階段
- **資料庫遷移**: Flyway CE / Liquibase OSS
- **環境配置**: Docker Compose / Kubernetes
- **監控工具**: Prometheus + Grafana / ELK Stack
- **日誌聚合**: Loki / Graylog / ELK

#### 文檔維護階段
- **API 文檔**: Swagger UI / Redoc / Stoplight Elements
- **架構文檔**: Structurizr / Mermaid.js / PlantUML
- **變更日誌**: Conventional Commits / auto-changelog
- **Wiki**: BookStack / Outline / Wiki.js

---

## 🛠️ Claude Code Skills 整合指引

> 本 SOP 各階段可搭配以下 Claude Code Skills 使用。每個 Skill 均有明確的觸發時機和使用方式。

### Skills 對應總覽（含觸發說明）

| SOP 階段 | Skill | 觸發時機 | 觸發範例指令 | 對應 Workflow |
|---------|-------|---------|------------|-------------|
| **1 啟動** | `/brownfield-analysis` | 開始分析前，告知系統背景 | `/brownfield-analysis` 後描述「系統使用 Next.js + Spring Boot，要新增掃碼功能」 | `brownfield-analysis-flow` |
| **1 啟動** | `/sa-analyst` | 需求描述不清晰，需結構化釐清時 | `/sa-analyst` 後描述「使用者希望能手機掃碼查庫存」 | `requirements-extraction` |
| **2 代碼分析** | `/brownfield-analysis` | 步驟 2.2 觸發自動代碼掃描 | `/brownfield-analysis` 後附上目錄結構或關鍵檔案路徑 | `brownfield-analysis-flow` |
| **2 代碼分析** | `/refactoring-code-quality` | 技術債評分後，需量化重構優先順序 | `/refactoring-code-quality` 後貼上高複雜度模組的代碼 | `refactoring-flow` |
| **3 影響分析** | `/sa-analyst` | 產出結構化影響分析報告 | `/sa-analyst` 後描述「評估新增 JWT 認證對現有 Session 系統的影響」 | `requirements-change-management` |
| **3 影響分析** | `/compliance-audit` | 🔴 **涉及金流/個資/旅宿法規時必須觸發** | `/compliance-audit` 後描述「民宿訂房整合 Stripe，需確認退款合規」 | — |
| **4 變更設計** | `/sd-architect` | 步驟 4.2 設計技術方案（特別是架構調整）| `/sd-architect` 後描述「設計跨模組共用 PaymentService」 | `user-story-and-design` |
| **4 變更設計** | `/documentation-api` | 步驟 4.3 新增或修改 API 端點時 | `/documentation-api` 後提供 API 端點描述 | `api-specification-generation` |
| **4 變更設計** | `/integration-api-client` | 涉及呼叫外部 API 或建立 API Client | `/integration-api-client` 後描述外部 API 規格 | — |
| **4 變更設計** | `/integration-stripe` | 🆕 涉及 Stripe 金流整合（新增或跨模組重用）| `/integration-stripe` 後描述「民宿訂房預授權付款流程」 | — |
| **5 相容性** | `/sa-analyst` | 評估 Breaking Changes 影響範圍 | `/sa-analyst` 後描述「API 版本升級的向下相容方案」 | `document-consistency-check` |
| **6 測試規劃** | `/qa-testing` | 步驟 6.2 制定整體測試策略 | `/qa-testing` 後描述功能和風險等級 | `sprint-execution`（測試段） |
| **6 測試規劃** | `/testing-strategy` | 需要測試金字塔設計和自動化策略 | `/testing-strategy` 後描述系統規模和覆蓋率現狀 | — |
| **7 實作審查** | `/dev-review` | 步驟 7.2 每支程式完成後代碼品質審查 | `/dev-review` 後貼上程式碼 | — |
| **7 實作審查** | `/code-review` | Pull Request 審查前的標準化檢查 | `/code-review` 後貼上 diff 或 PR 連結 | — |
| **7 實作審查** | `/security-audit` | 🔴 涉及認證/金流/個資的程式碼必須執行 | `/security-audit` 後貼上相關代碼 | — |
| **8 部署** | `/devops-github-actions` | 建立或更新 CI/CD Pipeline | `/devops-github-actions` 後描述部署環境和需求 | `devops-setup-flow` |
| **8 部署** | `/devops-docker` | 新增容器化或更新 Dockerfile | `/devops-docker` 後描述服務架構 | — |
| **8 部署** | `/devops-monitoring` | 🆕 設定監控告警（含第三方 Webhook 健康監控）| `/devops-monitoring` 後描述關鍵指標需求 | — |
| **8 部署** | `/integration-webhook` | 🆕 建立或驗證 Webhook 處理邏輯 | `/integration-webhook` 後描述 Webhook 事件類型 | — |
| **10 執行驗收** | `/release-management` | 步驟 10.3 部署前後驗收流程 | `/release-management` 後描述版本號和發布範圍 | — |
| **跨平台** | `/mobile-development` | 情境 F：新增 Android/macOS App 時 | `/mobile-development` 後描述目標平台和功能需求 | — |
| **DB 遷移** | `/database-migration` | Schema 有破壞性變更或跨 DB 平台遷移 | `/database-migration` 後描述遷移範圍 | — |

### Skills 選擇速決表（不確定時查這裡）

| 我要做什麼 | 用這個 Skill |
|-----------|------------|
| 分析現有代碼架構和技術債 | `/brownfield-analysis` |
| 釐清模糊需求、產出 FRD | `/sa-analyst` |
| 設計技術架構（含抽象化決策） | `/sd-architect` |
| 生成/更新 API 規格文檔 | `/documentation-api` |
| 整合 Stripe 金流 | `/integration-stripe` |
| 建立 Webhook 處理 | `/integration-webhook` |
| 制定測試策略 | `/qa-testing` + `/testing-strategy` |
| 審查程式碼品質 | `/dev-review`（開發中）/ `/code-review`（PR 前） |
| 安全漏洞審查 | `/security-audit` |
| 建立 CI/CD | `/devops-github-actions` 或 `/devops-gitlab-ci` |
| 設定監控系統 | `/devops-monitoring` |
| 發布版本（上線前後） | `/release-management` |
| 合規/法規審查 | `/compliance-audit` |
| 行動端 App 開發 | `/mobile-development` |
| 重構代碼品質 | `/refactoring-code-quality` |

---

## 🔴 開發-編譯-測試循環（強制規則）

> 依據 AISDLC CLAUDE.md 強制規則，所有開發階段必須遵守此循環。

```
開發 1 支程式（或 1 個功能單元）
    ↓
立即編譯 (Compile/Build)
    ↓
編譯失敗？ → 🔴 立即停止 → 修復 → 重新編譯
    ↓
編譯成功 ✅ → 執行單元測試
    ↓
測試失敗？ → 🔴 立即停止 → 依規格修復 → 重新測試
    ↓
測試通過 ✅ → 繼續開發下一支
```

**絕對禁止**：
- ❌ 累積多支程式後才編譯
- ❌ 編譯失敗後繼續開發
- ❌ 跳過單元測試
- ❌ 測試失敗後註解掉測試

**完整規範**：[Development_Build_Test_Cycle.md](../../guides/user/process/Development_Build_Test_Cycle.md)

---

## 📁 產出文件存放目錄指引

> **🔴 重要**：各階段產出文件必須依據 [FILE_DIRECTORY_RULES.md](../../FILE_DIRECTORY_RULES.md) 存放至正確目錄。

| 階段 | 產出文件 | 存放目錄 |
|------|---------|---------|
| 2 代碼分析 | 系統架構分析報告、代碼品質評估 | `docs/02_architecture/` |
| 2 代碼分析 | 技術債清單 | `docs/06_quality/` |
| 3 影響分析 | 影響分析報告、風險評估矩陣 | `docs/04_planning/` |
| 3 影響分析 | 變更範圍文件 | `docs/01_requirements/` |
| 4 變更設計 | 技術設計文件、API 變更規格 | `docs/02_architecture/` |
| 4 變更設計 | 實作計畫、資料遷移方案 | `docs/04_planning/` |
| 5 相容性 | 相容性分析、Breaking Changes 清單 | `docs/02_architecture/` |
| 6 測試策略 | 測試計畫、測試案例、測試腳本 | `docs/03_testing/` |
| 7 實作指引 | 實作指引、安全性檢查清單 | `docs/06_quality/` |
| 8 部署方案 | 部署方案、回滾手冊 | `docs/08_deployment/` |
| 9 文檔更新 | Release Notes | `docs/08_deployment/` |
| 9 文檔更新 | ADR、知識轉移記錄 | `docs/05_development/` |

---

## 🚀 完整執行流程

### 階段 1：啟動和情境確認 (20 分鐘)

> **Skills 觸發**：
> - 載入後立即執行 `/brownfield-analysis`，輸入系統描述（技術棧、業務領域、變更方向）
> - 若需求描述模糊，同步執行 `/sa-analyst` 協助結構化

#### 步驟 1.1：載入 AISDLC 框架
```
執行指令：
「請載入 AISDLC_SDD_INIT.md (v0.01)，我要對既有系統進行改造」

或具體說明：
「請載入 AISDLC_INIT.md，我要修復既有 Web 系統的認證問題」
「請載入 AISDLC_INIT.md，我要在既有 iOS App 新增支付功能」
```

#### 步驟 1.2：回答情境識別問題
系統會詢問：
- 系統類型 (Web/iOS/Android/Backend/Full-stack)
- 業務領域數量 (單一領域/多領域融合) 🆕
  - 若為多領域融合（如電商+民宿、ERP+CRM），需額外確認：
  - 各領域間的資料共用程度（獨立/部分共用/完全共用）
  - 變更是否跨領域（僅影響單一領域/跨領域影響）
  - 領域間的業務規則衝突風險
  - **共用角色/權限情況**：不同領域是否共用使用者角色（如：民宿管理員 = 電商管理員？）
  - 📋 **多領域融合確認問題**：參考 [Standard_Confirmation_Questions.md 多領域專區](../../scenarios/greenfield/checklists/Standard_Confirmation_Questions.md)（第 55-72 題）
- 變更性質 (Bug 修復/功能增強/技術改造/效能優化/功能停用/**跨模組重用**)
  - 🆕 **跨模組重用**：既有模組 A 的功能被模組 B 引用（如電商 Stripe 整合被民宿模組重用）
  - 若為跨模組重用，需額外確認：
    - 是否直接依賴（高耦合）或抽象化共用服務（低耦合）？→ 見階段 4 的「共用服務抽象化決策指引」
    - 既有整合是否包含業務邏輯（影響重用可行性）？
- 變更驅動因素 (使用者需求/技術債/法規合規/效能瓶頸)
- 系統規模 (小型/中型/大型/Legacy 系統)
- 代碼品質狀況 (良好/普通/待改善/Technical Debt 嚴重)
- 測試覆蓋率 (高/中/低/無)

#### 步驟 1.2.1：平台識別與 Agent 推薦 🆕 v0.01

> **🔴 重要**：若變更涉及新增平台（Android/iOS/macOS/跨平台），必須在此步驟觸發平台識別。

**平台識別觸發條件**：
- 新增 Mobile App 功能 → 載入 `sd-mobile-architect` + `qa-mobile-tester`
- 涉及硬體整合（掃碼、NFC、IoT）→ 載入 `integration-specialist`
  - 📋 `integration-specialist` 參與階段：
    - **階段 2**：分析硬體 SDK/API 整合現況、第三方服務依賴
    - **階段 4**：設計硬體整合方案（SDK 選型、通訊協議、錯誤處理）
    - **階段 6**：制定硬體整合測試策略（設備模擬、Sandbox 環境）
    - **階段 10**：驗證硬體整合功能（實機測試）
- 涉及認證授權/安全漏洞修復 → 載入 `security-engineer` ⭐ v0.01 新增
- 涉及法規/會計準則變更 → 載入 `compliance-officer`

**參考文件**：[Platform_Agent_Selection_Guide.md](../../guides/system/agent/Platform_Agent_Selection_Guide.md)

**建議 Skill**：`/brownfield-analysis`、`/sa-analyst`

#### 步驟 1.3：確認載入結果
期待回應：
```
✅ 識別情境：Brownfield Project (舊專案維護)
✅ 識別變更類型：[您的變更類型]
✅ 識別平台需求：[Web/Mobile/跨平台]
✅ 載入 Primary Agents：SA, Dev-Senior
✅ 載入 Supporting Agents：Code-Analyzer, SD, BA, PM/PO, QA, Dev, DevOps（按需載入）
✅ 載入 Optional Agents：[依平台和合規需求載入]
✅ 推薦 Workflow：brownfield-analysis-flow + change-management + sprint-execution
準備開始代碼分析與影響評估...
```

---

### 階段 2：代碼理解與架構分析 (1-1.5 小時 | 複雜 Legacy 系統可延長至 3-4 小時)

**建議 Skill**：`/brownfield-analysis`、`/refactoring-code-quality`
> - **步驟 2.2 開始時**：執行 `/brownfield-analysis`，提供代碼庫路徑或架構描述 → 產出技術債評估、依賴關係圖
> - **TD_Score ≥ 13 時**：接著執行 `/refactoring-code-quality`，量化需優先重構的模組清單

#### 步驟 2.1：提供系統資訊
```
執行指令：
「開始代碼分析流程，以下是系統資訊：
- 代碼庫路徑：[路徑]
- 主要技術棧：[技術]
- 變更需求：[詳細描述]
- 關鍵檔案/模組：[如已知]」
```

#### 步驟 2.2：自動代碼掃描 (Code-Analyzer Agent)
系統會執行：
- **目錄結構分析**：識別專案架構模式
- **技術棧識別**：確認框架、函式庫版本
- **相依性分析**：找出相關模組和檔案
- **代碼品質評估**：識別 code smells, technical debt
- **技術債評分**：使用標準化公式量化技術債嚴重程度
- **測試覆蓋分析**：評估現有測試完整性

**技術債評分公式 (Technical Debt Score)**：

```
TD_Score = (Complexity + Coupling + Age_Factor × 3) × (1 - Test_Coverage)

其中：
- Complexity（複雜度）：循環複雜度正規化，1-10 分
  - CC 1-5 → 1-3：低複雜度
  - CC 6-15 → 4-6：中等複雜度
  - CC 16-30 → 7-8：高複雜度
  - CC > 30 → 9-10：極高複雜度
  - ⚠️ 注意：實際 CC 值需正規化到 1-10 分，超出時按上表對照

- Coupling（耦合度）：模組間依賴程度，1-10 分
  - 1-3：低耦合（良好封裝）
  - 4-6：中等耦合（可接受）
  - 7-10：高耦合（需重構）

- Age_Factor（老化係數）：程式碼最後修改時間，1-5 分
  - < 6 個月：1
  - 6-12 個月：2
  - 1-2 年：3
  - 2-5 年：4
  - > 5 年：5

- Test_Coverage（測試覆蓋率）：0.0-1.0
  - 直接使用覆蓋率百分比除以 100
  - 若覆蓋率為 0%，使用 0.0

TD_Score 範圍：0-35 分
- 0-5：低技術債（🟢 綠燈）- 可安全修改
- 6-12：中等技術債（🟡 黃燈）- 建議先補測試
- 13-20：高技術債（🟠 橙燈）- 需謹慎修改，考慮先重構
- 21-28：嚴重技術債（🔴 紅燈）- 建議先重構再修改
- 29-35：極度危險（⚫ 黑燈）- 強烈建議暫停變更，優先進行系統級重構

校驗範例：
- 中等系統（Complexity=6, Coupling=6, Age=2, Coverage=45%）:
  TD_Score = (6 + 6 + 2×3) × (1 - 0.45) = 18 × 0.55 = 9.9 → 🟡 黃燈（合理）
- 高風險系統（Complexity=9, Coupling=8, Age=4, Coverage=10%）:
  TD_Score = (9 + 8 + 4×3) × (1 - 0.1) = 29 × 0.9 = 26.1 → 🔴 紅燈（合理）
- 健康系統（Complexity=3, Coupling=3, Age=1, Coverage=80%）:
  TD_Score = (3 + 3 + 1×3) × (1 - 0.8) = 9 × 0.2 = 1.8 → 🟢 綠燈（合理）
```

**AI 會提問以補充資訊** (零臆測原則)：
- 「這個模組的職責是什麼？」
- 「這個 API 的預期行為是？」
- 「這個資料表的更新頻率如何？」
- 「這個功能是否有外部依賴？」

> **🆕 多領域融合 Coupling 評分補充說明**
>
> 若系統為多領域融合（如電商+民宿+內容+知識管理），**跨領域耦合度（Coupling）評分**應按以下方式計算：
>
> | 跨領域依賴情況 | Coupling 加分 | 說明 |
> |--------------|-------------|------|
> | 共用 User/Auth 服務 | +1 | 常見且可接受 |
> | 共用 Payment 服務 | +1.5 | 業務邏輯可能不同，需評估 |
> | 直接跨模組呼叫（非抽象層） | +2 | 高耦合，建議重構 |
> | 共用資料庫表（無 Schema 隔離） | +2 | 風險高，需特別注意 |
> | 多個領域共用角色/權限邏輯 | +1.5 | 角色定義易產生衝突 |
>
> **範例**：電商+民宿融合系統，基礎 Coupling=5，共用 User(+1) + Payment(+1.5) + 共用 role 邏輯(+1.5) = 實際 Coupling = 8（超過中等，進入高耦合）
>
> ⚠️ 多領域融合系統的 TD_Score 評估結果通常偏高，此為正常現象，應據此更謹慎設計變更方案。

#### 步驟 2.3：架構理解確認點 (20 分鐘)

> 🔴 **人機協作點：架構理解確認**
>
> **AI 提供**：
> - 系統架構圖（識別的模組關係）
> - 資料流圖（資料流動路徑）
> - 關鍵組件清單（核心模組、API、資料表）
> - 技術債清單（代碼問題和風險）
>
> **需人工確認**：
> - ✅ 架構理解是否正確
> - ✅ 是否有遺漏的關鍵組件
> - ✅ 技術債評估是否準確
> - ✅ 補充任何背景資訊
>
> **產出文件**：
> - 系統架構分析報告 (System Architecture Analysis)
> - 代碼品質評估報告 (Code Quality Assessment)
> - 技術債清單 (Technical Debt Inventory)

---

### 階段 3：變更範圍界定與影響分析 (40-60 分鐘)

**建議 Skill**：`/sa-analyst`、`/compliance-audit`（合規驅動變更時）
> - **步驟 3.2 開始時**：執行 `/sa-analyst`，描述「變更對哪些模組/使用者/API 有影響」→ 產出結構化影響分析報告
> - **以下情況必須執行 `/compliance-audit`**（並同步啟動「情境 G：合規驅動變更」）：
>   - 涉及金流退款/稅務（旅宿訂金、電商退款）
>   - 涉及個資處理方式變更
>   - 涉及旅宿業/食品業/金融業等有特定法規的行業
>   - 涉及統一發票、會計分錄邏輯
>
>   **觸發範例**：`/compliance-audit` 後說明「民宿訂房新增 Stripe 線上付款，需確認台灣消費者保護法、旅宿業退款規定」

#### 步驟 3.1：觸發影響分析
```
執行指令：
「請分析此變更對系統的影響範圍」
```

#### 步驟 3.2：多維度影響分析 (SA + Code-Analyzer + BA)

**代碼層面影響**：
- 需修改的檔案清單
- 影響的 API/函式簽名
- 資料模型變更需求
- 相依模組影響

**資料層面影響**：
- 資料庫 Schema 變更
- 資料遷移需求
- 既有資料相容性
- 資料備份策略

**整合層面影響**：
- 外部 API 呼叫影響
- 第三方服務整合
- 內部服務相依性
- 向下/向上相容性

**使用者層面影響**：
- UI/UX 變更範圍
- 使用者工作流影響
- 權限和角色影響
- 向下相容性考量

> **🆕 多領域共用角色影響分析**（多領域融合系統必查）
>
> 若系統有多個業務領域，且存在跨領域共用角色（如「管理員」同時管理電商和民宿），必須確認：
>
> | 確認項目 | 說明 |
> |---------|------|
> | 角色合一性 | 同一使用者帳號是否扮演多個領域角色？ |
> | 權限邊界 | 電商管理員是否應能存取民宿資料？ |
> | 變更影響範圍 | 修改某領域角色是否意外影響其他領域的同角色使用者？ |
> | 新功能授權 | 新功能的存取權限，由哪個領域的角色政策管理？ |
>
> **建議**：若共用角色邏輯複雜，在階段 4 設計時考慮引入 RBAC（Role-Based Access Control）或 ABAC（Attribute-Based Access Control）統一授權層。

#### 步驟 3.3：風險識別與評估

**風險評估模板**：[Risk_Assessment_Template.md](../../docs_template/scenario_specific/analysis/Risk_Assessment_Template.md) 🆕

系統會分析：
- **高風險區域**：核心業務邏輯、支付、認證等
- **資料風險**：資料遺失、資料不一致可能性
- **效能風險**：可能的效能退化點
- **相容性風險**：API breaking changes, 版本不相容
- **合規風險** 🆕：法規合規（會計準則、GDPR、資安法）、產業標準、審計要求
- **業務驗證風險** 🆕：業務邏輯變更需由領域專家（會計師、法務等）驗證正確性
- **歷史資料影響** 🆕：變更是否需要重算/遷移歷史資料，評估資料量與時間成本

> **🔴 情境 G 自動觸發檢查（步驟 3.3 執行後必須確認）**
>
> 若風險識別發現以下任一項，**必須立即啟動「情境 G：合規驅動變更」並執行 `/compliance-audit`**：
>
> | 觸發條件 | 常見場景 |
> |---------|---------|
> | 金流/退款/稅務邏輯變更 | 民宿訂金退款、電商退貨稅務 |
> | 旅宿業/食品業/金融業特定法規 | 旅宿業消費者保護、預訂合約規定 |
> | 個人資料處理方式改變 | 新增收集欄位、跨境傳輸 |
> | 統一發票/電子發票邏輯 | 修改開立邏輯或格式 |
> | 財務報表/會計分錄 | 計算方式改變 |
>
> **操作**：發現以上情況 → 在影響分析確認點告知使用者「本次變更需啟動情境 G」→ 執行 `/compliance-audit` → 載入 `compliance-officer` Agent → 依情境 G 流程執行

#### 步驟 3.4：影響分析確認點 (20 分鐘)

> 🔴 **人機協作點：影響分析確認**
>
> **AI 提供**：
> - 影響範圍地圖（視覺化展示影響的模組和關係）
> - 變更清單（需要修改的所有檔案和原因）
> - 風險矩陣（按嚴重性和可能性分類的風險）
> - 相依性鏈（變更的上下游影響）
> - 回滾策略（如何安全回滾）
>
> **需人工確認**：
> - ✅ 影響範圍評估是否完整
> - ✅ 風險等級是否正確
> - ✅ 是否有遺漏的影響點
> - ✅ 回滾策略是否可行
>
> **產出文件**：
> - 影響分析報告 (Impact Analysis Report)
> - 風險評估矩陣 (Risk Assessment Matrix)
> - 變更範圍文件 (Change Scope Document)

---

### 階段 4：變更設計與技術方案 (1-1.5 小時)

**建議 Skill**：`/sd-architect`、`/integration-api-client`、`/documentation-api`、`/integration-stripe`（涉及 Stripe 時）
> - **步驟 4.2 方案設計**：執行 `/sd-architect`，描述「需設計什麼架構或抽象層」→ 產出技術設計文件
> - **步驟 4.3 新增 API**：執行 `/documentation-api`，描述新端點 → 產出 OpenAPI 規格
> - **涉及外部 API Client**：執行 `/integration-api-client`，描述外部 API 規格
> - **涉及 Stripe 金流**：執行 `/integration-stripe`，描述付款流程（預授權/Capture/退款）→ 產出 Stripe 整合代碼

#### 步驟 4.1：觸發設計流程
```
執行指令：
「基於影響分析，請設計最小風險的變更方案」
```

#### 步驟 4.2：設計方案生成 (Dev-Senior + SD)

**方案 A：最小變更方案**
- 優點：風險最低，變更範圍小
- 缺點：可能累積技術債
- 適用：緊急修復、時間緊迫

**方案 B：平衡改進方案**
- 優點：兼顧需求與代碼品質
- 缺點：需要更多測試
- 適用：一般功能改進

**方案 C：重構優化方案** (如適用)
- 優點：改善架構，減少技術債
- 缺點：變更範圍大，風險高
- 適用：有時間預算，值得投資

#### 步驟 4.3：技術實作細節

對每個方案，系統會提供：
- **檔案變更清單**：具體要改哪些檔案
- **程式碼範例**：關鍵邏輯的實作範例
- **資料遷移腳本**：SQL/NoSQL migration scripts
- **API 變更規格**：新增/修改的 API 定義（建議使用 [`api-specification-generation` workflow](../../workflow/core/api-specification-generation.md)）
- **設定檔變更**：環境變數、config 調整

**Mobile API 設計特殊考量**（如涉及 Mobile/Desktop 端）🆕：

> 若變更涉及新增或修改 Mobile 端使用的 API，需額外考慮以下設計要點：

| 設計面向 | Web API | Mobile API | 說明 |
|---------|---------|------------|------|
| **認證** | Session/Cookie | JWT (Bearer Token) | Mobile 無狀態設計，支援 Token Refresh |
| **請求模式** | 即時請求 | 批量請求 (Batch API) | 減少 Mobile 網路請求次數 |
| **數據量** | 完整回傳 | 精簡回傳 + 分頁 | Mobile 流量敏感，使用 `fields` 參數選擇欄位 |
| **分頁** | Offset-based | Cursor-based | 適合無限滾動，避免資料漂移 |
| **壓縮** | 選配 | 必要 (gzip/brotli) | 減少傳輸量 |
| **離線** | 不需要 | 佇列 + 同步機制 | 支援離線操作後上線同步 |
| **版本** | URL path (/v1/) | Header + 強制更新 | `min_supported_version` 機制 |
| **錯誤處理** | HTTP Status | 統一錯誤格式 + 重試策略 | `{ code, message, retryable }` |
| **推送** | WebSocket/SSE | FCM/APNs | 伺服器→客戶端即時通知 |

> **🆕 macOS Desktop App 特殊考量**
>
> macOS App 與 Android 的設計差異點：
>
> | 設計面向 | Android | macOS App | 說明 |
> |---------|---------|-----------|------|
> | **認證** | JWT Bearer | JWT Bearer 或 Session+Cookie | macOS 可選有狀態 Session（Keychain 儲存） |
> | **掃碼硬體** | CameraX + ML Kit | AVFoundation 或外接 USB 掃碼槍 | USB 掃碼槍模擬鍵盤輸入，需不同邏輯 |
> | **安全儲存** | Keystore | Keychain | Token/密碼安全儲存 |
> | **推送** | FCM | APNs 或 NSUserNotification | macOS 推送走 APNs 認證 |
> | **更新機制** | Google Play | Mac App Store 或 Sparkle | 直接分發需整合 Sparkle 自動更新 |
> | **Notarization** | 不需要 | Apple 公證必要 | DMG 分發需 notarize + staple |

**🆕 跨模組重用時的「共用服務抽象化決策指引」**

> 當變更需要跨模組重用既有整合（如 A 模組的 Stripe 整合被 B 模組引用），需在此做架構決策：

| 方案 | 適用情境 | 優點 | 缺點 | 實作成本 |
|------|---------|------|------|---------|
| **直接依賴**（A 模組呼叫 B 的 Service） | 業務邏輯完全相同，緊急需求 | 快速 | 高耦合，B 模組變更影響 A | 低（0.5-1天） |
| **抽象共用層**（提取 SharedPaymentService） | 多個模組有相近需求，可能繼續擴展 | 低耦合，可維護 | 需重構，有初期成本 | 中（1-3天） |
| **領域事件**（Event-Driven，A 發事件→B 處理） | 微服務或高度解耦需求 | 最低耦合 | 複雜，需事件基礎設施 | 高（3-5天） |

**決策標準**：
- 2 個以上模組需重用 → 選「抽象共用層」
- 業務邏輯差異大（如退款政策不同）→ 各自實作，僅共用 API Client
- 緊急修復 → 直接依賴 + 排程重構

> ⚠️ **ADR 觸發**：當選擇「抽象共用層」或「領域事件」時，**必須記錄架構決策記錄（ADR）**，說明選擇理由和替代方案。ADR 存放：`docs/05_development/ADR-XXX-[主題].md`

#### 步驟 4.4：方案選擇確認點 (15 分鐘)

> 🔴 **人機協作點：方案選擇確認**
>
> **AI 提供**：
> - 方案對比表（3 個方案的優缺點、工時、風險對比）
> - 推薦方案（基於風險和效益的推薦）
> - 實作步驟（選定方案的具體執行步驟）
> - 時間評估（開發、測試、部署時間估算）
>
> **需人工確認**：
> - ✅ 選擇哪個方案
> - ✅ 是否需要調整設計
> - ✅ 確認實作步驟順序
> - ✅ 確認時間評估合理性
>
> **產出文件**：
> - 技術設計文件 (Technical Design Document)
> - 變更實作計畫 (Implementation Plan)
> - 資料遷移方案 (Data Migration Plan) — 模板：[Data_Migration_Template.md](../../docs_template/scenario_specific/brownfield/Data_Migration_Template.md) 🆕
> - API 變更規格 (API Change Specification)

---

### 階段 5：相容性與依賴檢查 (30-40 分鐘)

#### 步驟 5.1：觸發相容性檢查
```
執行指令：
「請檢查此變更的相容性和依賴影響」
```

#### 步驟 5.2：多層次相容性分析

**向下相容性檢查**：
- 既有 API 呼叫者是否受影響
- 舊版客戶端 (Web/Mobile) 是否可用
- 資料格式變更的向下相容
- URL/Routing 變更影響

**依賴服務檢查**：
- 上游服務 API 版本相容性
- 下游服務是否需要同步更新
- 第三方函式庫版本相容性
- 資料庫版本相容性

**版本管理策略**：
- API versioning 策略 (v1/v2)
- Feature flags ��用建議
- Graceful degradation 設計
- 藍綠部署/金絲雀部署建議

> **⚠️ 無版本管理系統的應對方案**
>
> 若舊系統缺少 API versioning 機制,採用以下策略:
>
> **方案 A: 加入版本管理 (推薦)**
> - 在 API 路徑加入版本: `/v1/users` → `/v2/users`
> - 在 Header 加入版本: `Accept: application/vnd.myapi.v2+json`
> - 保留舊版本 API 並設定 Deprecation 時間表
> - 提供遷移指南給 API 使用者
>
> **方案 B: 功能偵測 (Feature Detection)**
> - 在 Response 加入 `api_version` 或 `capabilities` 欄位
> - Client 根據回應欄位判斷是否支援新功能
> - 舊 Client 忽略新欄位,新 Client 使用新欄位
> - 適合「向下相容」的變更
>
> **方案 C: 分離端點 (Separate Endpoints)**
> - 新功能使用全新的 API 端點: `/users` → `/users-v2`
> - 舊端點維持不變,逐步棄用
> - 適合破壞性變更 (Breaking Changes)
>
> **方案 D: 代理層版本控制 (API Gateway Versioning)**
> - 在 API Gateway 層處理版本路由
> - 根據 Header/Query Parameter 路由到不同版本後端
> - 適合微服務架構
>
> **無法加入版本管理時的風險緩解**:
> - ✅ 充分的溝通計畫 (提前通知所有 API 使用者)
> - ✅ 長時間的 Staging 測試期 (至少 2 週)
> - ✅ Feature Flag 控制新功能,可即時回滾
> - ✅ 監控 API 錯誤率,異常時立即降級
> - ✅ 保留回滾腳本和資料備份

#### 步驟 5.3：相容性確認點 (10 分鐘)

> 🔴 **人機協作點：相容性確認**
>
> **AI 提供**：
> - 相容性矩陣（各層面的相容性狀態）
> - Breaking Changes 清單（不可避免的破壞性變更）
> - 緩解措施（如何處理不相容問題）
> - 溝通計畫（需要通知哪些團隊/使用者）
>
> **需人工確認**：
> - ✅ 相容性評估是否完整
> - ✅ Breaking changes 是否可接受
> - ✅ 緩解措施是否充分
> - ✅ 溝通計畫是否完備
>
> **產出文件**：
> - 相容性分析報告 (Compatibility Analysis)
> - Breaking Changes 清單 (Breaking Changes List)
> - 版本管理策略 (Versioning Strategy)

**Breaking Change 通知範例** 🆕：

> 當存在不可避免的 Breaking Changes 時，使用以下模板通知相關團隊/使用者：

```markdown
## ⚠️ Breaking Change 通知

**影響系統**: [系統名稱]
**變更日期**: [YYYY-MM-DD]
**影響範圍**: [API / DB Schema / UI]

### 變更內容
| 項目 | 舊版 | 新版 | 影響 |
|------|------|------|------|
| [API 端點] | GET /api/orders | GET /api/v2/orders | 回應格式變更 |
| [欄位] | order.total | order.total_amount | 欄位名稱變更 |

### 遷移指南
1. [具體遷移步驟]
2. [程式碼修改範例]

### 時間表
- **通知日**: [日期]
- **Staging 可測試**: [日期]
- **舊版停用**: [日期]（建議保留 30-90 天遷移期）

### 聯絡窗口
- 技術問題: [負責人/頻道]

### SEO 影響（如涉及 URL 移除或頁面停用）
- **受影響 URL 數量**: [N 個頁面/端點]
- **重定向方案**: 301 永久重定向至 [新 URL]（建議保留 6 個月以上）
- **Sitemap 更新**: 移除舊 URL，添加新 URL，提交至 Google Search Console
- **robots.txt**: 確認已移除不必要的 Disallow 規則
- **Google Search Console**: 提交「URL 移除工具」加速舊 URL 從索引移除
- **預估 SEO 影響**: [說明影響範圍和恢復預期時間]
```

---

### 階段 6：測試策略與測試計畫 (40-60 分鐘)

**建議 Skill**：`/qa-testing`、`/testing-strategy`
> - **步驟 6.2 開始時**：執行 `/testing-strategy`，描述「系統規模、目前覆蓋率、變更風險等級」→ 產出測試金字塔設計
> - **步驟 6.3 產出案例**：執行 `/qa-testing`，描述「功能描述 + 驗收條件」→ 產出 Given-When-Then 格式的測試案例

#### 步驟 6.1：觸發測試規劃
```
執行指令：
「請制定完整的測試計畫，確保變更安全」
```

#### 步驟 6.2：測試策略設計 (QA + QA-Automation)

**單元測試計畫**：
- 新增程式碼的單元測試
- 修改程式碼的測試更新
- 測試覆蓋率目標 (建議 ≥80%)
- Mock/Stub 策略

> **⚠️ 無測試系統的應對方案 - 測試補強專項流程**
>
> 若系統完全缺少測試,採用以下漸進式測試補強流程:
>
> **從零建立測試的步驟**:
>
> **1. 識別測試缺口** (1-2 天)
> - 執行測試覆蓋率掃描 (如有程式碼)
> - 識別核心業務邏輯模組
> - 建立測試優先級矩陣 (風險 × 變更頻率)
> - 列出高優先級測試目標 (Top 20%)
>
> **2. 建立測試基礎設施** (2-3 天)
> - 選擇測試框架:
> - JavaScript/TypeScript: Jest + Testing Library
> - Python: pytest + pytest-cov
> - Java: JUnit 5 + Mockito
> - .NET: xUnit + Moq
> - 配置測試環境 (獨立測試資料庫)
> - 建立測試資料工廠 (Test Data Factory)
> - 設定 CI 測試流程
>
> **3. 補充測試 (1-2 週,視規模)**
> - **Phase 1: 核心路徑測試** (Golden Path) - 40% 工作量
> - 主要業務流程的 Happy Path
> - 關鍵 API 端點的基本測試
> - **Phase 2: 邊界條件和異常處理** - 30% 工作量
> - 輸入驗證測試
> - 錯誤處理測試
> - **Phase 3: 整合測試** - 20% 工作量
> - 資料庫整合測試
> - 第三方服務 Mock 測試
> - **Phase 4: E2E 關鍵流程** - 10% 工作量
> - 端對端關鍵業務流程
>
> **4. 持續改進**
> - 設定 coverage 目標: 先 40% → 60% → 80%
> - 每次變更強制補充測試 (Pre-commit hook)
> - Code Review 檢查測試品質
> - 定期執行測試健康度檢查
>
> **推薦工具** (免費/開源):
> - **Coverage 工具**: nyc (JS), coverage.py (Python), JaCoCo (Java)
> - **Mock 框架**: nock (JS), responses (Python), WireMock (Java)
> - **測試資料**: Faker.js, factory_boy (Python), Java Faker
>
> **測試補強檢查清單**:
> - [ ] 測試框架已設定並可執行
> - [ ] 核心模組測試覆蓋率 ≥60%
> - [ ] 所有 Public API 都有基本測試
> - [ ] 關鍵業務邏輯有完整測試
> - [ ] CI Pipeline 整合測試
> - [ ] 測試執行時間 <5 分鐘 (快速回饋)

**整合測試計畫**：
- API 整合測試案例
- 資料庫整合測試
- 第三方服務整合測試
- 端對端流程測試

**Mock vs Sandbox 測試選擇指引** 🆕：

> 第三方服務的測試策略應根據風險等級和服務特性選擇合適的方式。

| 測試方式 | 適用場景 | 優點 | 缺點 |
|---------|---------|------|------|
| **Mock/Stub** | 單元測試、CI 快速回饋 | 速度快、穩定、無外部依賴 | 可能與真實行為不一致 |
| **Sandbox** | 整合測試、UAT | 真實行為、完整流程驗證 | 速度慢、需申請帳號、可能有使用限制 |
| **Contract Test** | API 版本相容性 | 輕量、自動化 | 需維護 Contract 定義 |

| 第三方服務類型 | 建議測試方式 | 理由 |
|--------------|------------|------|
| 支付閘道（Stripe/綠界） | 🔴 **Sandbox 必要** | 金流正確性攸關業務，Mock 風險過高 |
| 推送通知（FCM/APNs） | 🟡 Mock + Sandbox | 單元用 Mock，整合用 Sandbox |
| Email/SMS 服務 | 🟢 Mock 為主 | 低風險，Sandbox 驗證一次即可 |
| OAuth 認證 | 🟡 Mock + Sandbox | 登入流程需真實驗證 |
| 地圖/地理服務 | 🟢 Mock 為主 | 回傳格式穩定，Mock 足夠 |
| 會計/ERP 系統 | 🔴 **Sandbox 必要** | 業務邏輯複雜，需真實驗證 |

**🆕 測試優先順序決策（覆蓋率 < 70% 時）**

> 當系統測試覆蓋率不足時，有限時間內應優先補哪類測試？

| 情境 | 優先補充順序 | 理由 |
|------|------------|------|
| 新增功能 | 1. 新功能單元測試 → 2. 新功能整合測試 → 3. 核心路徑回歸 | 新代碼最脆弱，必須先保護 |
| Bug 修復 | 1. 重現 Bug 的測試 → 2. 修復驗證測試 → 3. 相關模組回歸 | 先確認修復正確，再防止回歸 |
| 跨模組整合 | 1. 整合點測試 → 2. 各模組單元測試 → 3. E2E 主要流程 | 整合點是最高風險區 |
| 功能停用 | 1. 否定測試（確認已移除） → 2. 受影響模組回歸 → 3. 重定向正確性 | 驗證「不存在」同樣重要 |

**回歸測試計畫**：
- 既有功能回歸測試範圍
- 自動化回歸測試套件
- 手動測試檢查清單
- 效能回歸測試

**特殊測試需求**：
- 資料遷移測試 (如適用)
- 向下相容性測試
- 負載/壓力測試 (如適用)
- 安全性測試 (如涉及認證/授權)
- **功能停用否定測試** (如涉及功能移除) 🆕
  - 確認已停用的 API 回傳 410 Gone（非 404）
  - 確認舊版 URL 正確執行 301 重定向
  - 確認已移除的 UI 入口確實消失
  - 確認共用組件在移除後，其他使用方仍正常運作

**🆕 CI 環境硬體設備模擬策略**（適用於涉及掃碼/NFC/GPS 等硬體整合）

> 硬體設備（相機掃碼、NFC、GPS）無法在 CI 環境直接測試，採用以下分層策略：

| 測試層級 | 測試方式 | CI 可自動化 | 說明 |
|---------|---------|------------|------|
| 解碼邏輯單元測試 | Mock 掃碼結果字串 | ✅ 是 | 測試 BarcodeParser 的業務邏輯 |
| API 整合測試 | Mock 相機輸入 → 測試 API | ✅ 是 | 跳過相機，直接測試後端處理 |
| UI 功能測試 | Espresso/Detox + 模擬掃碼 | ✅ 是 | 注入假掃碼事件 |
| 實機整合測試 | Firebase Test Lab / 實際設備 | ⚠️ 手動 | 真實相機 + 條碼，PR 合併前執行 |
| 上架前驗收 | 實際設備完整場景 | ❌ 手動 | 上線前必做，覆蓋 Top 5 裝置型號 |

**重要**：CI Pipeline 執行「解碼邏輯 + API 整合 + UI 功能」自動化測試，實機測試排程在每週 / Release 前手動執行。

**跨平台測試需求**（如涉及 Mobile/Desktop 擴展）🆕：
- 設備碎片化：至少覆蓋 Top 5 主流裝置型號
- 作業系統版本：Android 12-15、macOS 13-15、iOS 16-18
- 權限處理：授權/拒絕/稍後詢問的完整流程
- 離線/弱網：斷網、2G、3G、Wi-Fi 切換場景
- 硬體功能：相機（掃碼）、NFC、GPS 的異常處理
- 電量/記憶體：長時間操作的資源消耗監控
- 第三方服務 Sandbox：支付閘道、推送通知使用 Sandbox 環境測試（非 Mock）
- 測試案例 ID：使用 AISDLC 標準格式 `TC-XXX-Y-Z`（參考 [ID 命名規範](../../guides/system/naming/AISDLC_ID_Naming_Convention.md)）

#### 步驟 6.3：測試案例生成

系統會生成：
- **測試案例清單**：包含 Given-When-Then 格式
- **測試資料準備**：測試所需的資料和環境
- **測試腳本範例**：自動化測試程式碼範例
- **測試執行順序**：建議的測試執行順序

#### 步驟 6.4：測試計畫確認點 (15 分鐘)

> 🔴 **人機協作點：測試計畫確認**
>
> **AI 提供**：
> - 測試金字塔（單元/整合/E2E 測試比例）
> - 測試案例清單（完整的測試案例 50+ 個典型）
> - 測試環境需求（所需的測試環境和資料）
> - 測試時間評估（各階段測試預估時間）
> - 自動化程度（建議自動化的測試比例）
>
> **需人工確認**：
> - ✅ 測試案例是否完整
> - ✅ 測試覆蓋是否充分
> - ✅ 測試環境是否可行
> - ✅ 時間評估是否合理
>
> **產出文件**：
> - 測試計畫 (Test Plan)
> - 測試案例清單 (Test Cases)
> - 測試腳本 (Test Scripts)
> - 測試資料準備指南 (Test Data Guide)

---

### 階段 7：實作指引與程式碼審查準備 (30 分鐘)

**建議 Skill**：`/dev-review`、`/code-review`、`/security-audit`（涉及安全性時）
> - **每完成一個功能單元**：執行 `/dev-review`，貼上程式碼 → 即時代碼品質回饋（配合開發-編譯-測試循環）
> - **PR 提交前**：執行 `/code-review`，貼上完整 diff → 產出標準化審查意見
> - **涉及認證/金流/個資時（必須）**：執行 `/security-audit`，貼上相關代碼 → OWASP Top 10 審查報告

#### 步驟 7.1：實作前最終檢查
```
執行指令：
「請生成實作檢查清單和程式碼審查標準」
```

#### 步驟 7.2：實作指引生成 (Dev-Senior)

> 🔴🔴🔴 **開發-編譯-測試循環（強制規則）** 🔴🔴🔴
>
> **每完成一支程式（或一個功能單元），必須立即執行編譯→測試循環！**
> ```
> 開發 1 支程式 → 編譯 → 失敗？立即修復 → 測試 → 失敗？立即修復 → 下一支
> ```
> ❌ 禁止累積多支程式後才編譯 | ❌ 禁止跳過測試 | ❌ 禁止測試失敗後繼續開發
>
> 完整規範：[Development_Build_Test_Cycle.md](../../guides/user/process/Development_Build_Test_Cycle.md)

**實作順序建議**：
1. 🔴 **回滾策略準備** (必要步驟) 🆕 v0.01 新增
2. 資料庫 Schema 變更 (如需要)
3. 資料遷移腳本 (如需要)
4. 後端 API 變更
5. 前端 UI 變更
6. 測試撰寫
7. 文檔更新

**🔴 回滾策略準備（步驟 7.2.0）** 🆕 v0.01 新增

> **重要**：回滾策略必須在實作前準備完成，確保發生問題時能快速恢復。

**回滾前置檢查清單**：
- [ ] 已識別所有受影響的資料表和欄位
- [ ] 已準備資料庫回滾腳本（Schema Rollback Script）
- [ ] 已規劃資料備份時間點（Backup Checkpoint）
- [ ] 已定義回滾觸發條件（Rollback Trigger Criteria）
- [ ] 已估算回滾時間（預計 < 30 分鐘）
- [ ] 已確認回滾後的資料一致性驗證方法

**回滾策略類型**：

| 變更類型 | 回滾策略 | 準備項目 | 預估時間 |
|---------|---------|---------|---------|
| **Schema 新增** | DROP 新欄位/表 | DROP 腳本 | < 5 分鐘 |
| **Schema 修改** | ALTER 還原 | ALTER REVERSE 腳本 | 5-15 分鐘 |
| **資料遷移** | 還原備份 | 遷移前完整備份 | 10-30 分鐘 |
| **API 變更** | 部署前一版本 | Git tag + CI/CD | 5-10 分鐘 |
| **設定變更** | 還原設定檔 | 設定檔備份 | < 5 分鐘 |

**回滾決策矩陣**：
| 問題嚴重度 | 影響範圍 | 建議行動 |
|-----------|---------|---------|
| 低 | 單一功能 | 熱修復，不回滾 |
| 中 | 多個功能 | 評估後決定 |
| 高 | 全系統 | 🔴 立即回滾 |
| 緊急 | 資料損壞 | 🔴 立即回滾 + 資料修復 |

**程式碼規範檢查**：
- Coding style 遵循
- 命名規範一致性
- 註解和文檔完整性
- 錯誤處理完整性
- 日誌記錄適當性

**安全性檢查清單**：
- 輸入驗證（前後端雙重驗證）
- SQL Injection 防護（Parameterized Query）
- XSS 防護（Output Encoding）
- CSRF Token（State-changing 操作）
- 敏感資料處理（加密儲存、傳輸加密）
- 權限檢查（RBAC/ABAC 驗證）
- API Rate Limiting（防止暴力攻擊/DoS）🆕
- CORS 配置（跨平台 API 必要）🆕
- JWT/Session 安全（Token 過期、Refresh 策略）🆕

#### 步驟 7.3：實作指引確認點 (10 分鐘)

> 🔴 **人機協作點：實作指引確認**
>
> **AI 提供**：
> - 實作檢查清單（開發時的檢查項目）
> - 程式碼審查標準（審查時的重點）
> - 常見陷阱提醒（此類變更的常見錯誤）
> - 參考範例（相似變更的最佳實踐）
>
> **需人工確認**：
> - ✅ 實作檢查清單是否完整
> - ✅ 審查標準是否符合團隊規範
> - ✅ 陷阱提醒是否涵蓋已知風險
> - ✅ 參考範例是否適用
>
> **產出文件**：
> - 實作指引 (Implementation Guide)
> - 程式碼審查檢查清單 (Code Review Checklist)
> - 安全性檢查清單 (Security Checklist)

---

### 階段 8：部署方案與回滾計畫 (30-40 分鐘)

**建議 Skill**：`/devops-github-actions`、`/devops-docker`、`/devops-monitoring`（🆕 監控）、`/integration-webhook`（🆕 Webhook 驗證）
> - **步驟 8.2 CI/CD 設計**：執行 `/devops-github-actions`（GitHub）或 `/devops-gitlab-ci`（GitLab），描述部署環境 → 產出完整 Pipeline 配置
> - **涉及容器化**：執行 `/devops-docker`，描述服務結構 → 產出 Dockerfile + docker-compose
> - **🆕 設定監控**：執行 `/devops-monitoring`，描述關鍵業務指標 → 產出 Prometheus/Grafana 告警規則（含 Webhook 靜默失敗告警）
> - **🆕 驗證 Webhook**：執行 `/integration-webhook`，描述 Webhook 事件 → 產出 Webhook 處理/驗證/重試代碼

#### 步驟 8.1：觸發部署規劃
```
執行指令：
「請制定安全的部署方案和回滾計畫」
```

#### 步驟 8.2：部署策略設計 (DevOps)

**部署方式選擇**：
- **直接部署**：適用於低風險變更
- **藍綠部署**：適用於需要快速回滾的變更
- **金絲雀部署**：適用於高風險變更，逐步放量
- **Feature Flag**：適用於需要動態開關的功能

> **⚠️ 多租戶系統部署注意事項**
>
> SaaS 多租戶系統需要特殊的部署策略:
>
> **1. 租戶隔離驗證**
> - **資料隔離測試**: 確保租戶 A 看不到租戶 B 資料
> - **效能隔離**: 一個租戶的負載不影響其他租戶
> - **配置隔離**: 租戶特定設定不互相干擾
> - **測試方法**: 使用 2+ 測試租戶進行交叉驗證
>
> **2. 部署策略選擇**
> - **Rolling Update**: 適合同構租戶,逐批更新 (批次大小: 10-20%)
> - **Tenant-by-Tenant**: 逐個租戶部署,高風險租戶優先測試
> - 先部署內部測試租戶
> - 再部署 Beta 租戶 (願意嘗試新功能)
> - 最後部署 Production 租戶
> - **Canary with Tenant Selection**: 選擇特定租戶作為 Canary
> - 選擇流量較小的租戶
> - 監控 24-48 小時無異常後擴大範圍
> - **Blue-Green per Tenant**: 大型租戶獨立藍綠部署
> - 適合 VIP 租戶或大流量租戶
> - 可即時切換回滾
>
> **3. Schema 變更管理**
> - **共享資料庫模式**: 
> - 需確保 Schema 向下相容 (先加欄位,後刪欄位)
> - 使用資料庫遷移腳本 (Flyway/Liquibase)
> - 分階段執行: Schema 變更 → 部署應用 → 清理舊欄位
> - **獨立資料庫模式**:
> - 需批次執行遷移腳本 (逐個租戶資料庫)
> - 失敗處理: 記錄失敗租戶,手動修復
> - **混合模式**: 需分階段處理,共享表先處理
>
> **4. Feature Flag 策略**
> - 支援租戶級別的 Feature Toggle
> - 允許租戶選擇性試用新功能 (Beta Program)
> - 新功能先開放給內部租戶或 Beta 租戶
> - 緊急關閉: 可針對單一租戶關閉問題功能
>
> **5. 回滾策略**
> - 支援租戶級別回滾 (不影響其他租戶)
> - 保留租戶資料快照 (部署前自動備份)
> - 快速切換租戶路由 (DNS/Load Balancer)
> - 回滾順序: 新部署租戶 → Beta 租戶 → 內部租戶
>
> **6. 監控與告警**
> - 租戶級別的錯誤率監控
> - 租戶級別的效能監控 (回應時間, QPS)
> - 異常租戶自動隔離機制 (Circuit Breaker)
> - 租戶 SLA 告警 (超過 SLA 立即通知)
>
> **多租戶部署檢查清單**:
> - [ ] 租戶隔離測試已通過
> - [ ] 部署策略已選定並驗證
> - [ ] Schema 遷移腳本已測試
> - [ ] Feature Flag 機制已就緒
> - [ ] 租戶級別監控已設定
> - [ ] 回滾方案已驗證
> - [ ] 租戶溝通計畫已執行 (通知維護窗口)

**部署步驟清單**：
1. Pre-deployment 檢查
2. 資料庫備份
3. 資料遷移執行 (如需要)
4. 應用程式部署
5. Smoke test 執行
6. 監控檢查
7. 流量切換 (如適用)
8. Post-deployment 驗證

**監控與告警**：
- 關鍵指標監控 (CPU/Memory/Response time)
- 業務指標監控 (轉換率、錯誤率)
- 日誌監控關鍵字
- 告警閾值設定

**🆕 第三方整合健康監控**（涉及 Webhook / 外部 API 時必須設定）

> 第三方整合（Stripe Webhook、FCM 推送等）可能靜默失敗，常規系統監控無法偵測，需額外設定：

| 整合類型 | 監控方式 | 告警條件 |
|---------|---------|---------|
| **Stripe Webhook** | 監控 Stripe Dashboard Events 的失敗率；應用側監控 webhook_received_count | Webhook 靜默 > 1 小時且有訂單活動 |
| **FCM/APNs 推送** | 監控推送成功率 + 設備 Token 過期率 | 推送成功率 < 95% |
| **外部 API 呼叫** | 監控 HTTP 5xx 錯誤率 + 超時率 | 錯誤率 > 1% 或 P99 延遲 > 3 秒 |
| **資料庫遷移後** | 監控關鍵業務指標（訂單建立、付款完成）是否正常 | 業務指標偏離歷史基準 > 20% |

**Webhook 監控設定步驟**：
1. 在應用側記錄每次 Webhook 接收事件到日誌（含 event_type、status）
2. 設定告警：「最近 1 小時無 Stripe Webhook 事件」（前提：有業務活動）
3. 在 Stripe Dashboard → Webhooks 頁面，監控 Failed 事件並啟用重試
4. 部署後 48 小時內每日手動檢查 Stripe Dashboard 的事件交付狀態

#### 步驟 8.3：回滾計畫設計

**回滾觸發條件**：
- 錯誤率超過閾值
- 效能降低超過 X%
- 關鍵功能失效
- 資料不一致

**回滾步驟**：
1. 停止新流量
2. 切換到舊版本
3. 資料回滾 (如適用且可行)
4. 驗證系統恢復
5. 事後分析

**回滾時間目標**（參考建議值）：

| 變更規模 | RTO（恢復時間） | RPO（資料遺失容忍） |
|---------|----------------|-------------------|
| 小型（UI/設定） | < 10 分鐘 | 0（無資料遺失） |
| 中型（API/邏輯） | < 30 分鐘 | < 5 分鐘 |
| 大型（Schema/遷移） | < 60 分鐘 | 需完整備份還原 |
| 緊急（資料損壞） | < 15 分鐘（切換） | 以最近備份點為準 |

- RTO (Recovery Time Objective): 從發現問題到系統恢復正常的最大容許時間
- RPO (Recovery Point Objective): 可接受的最大資料遺失時間範圍

#### 步驟 8.4：部署方案確認點 (15 分鐘)

> 🔴 **人機協作點：部署方案確認**
>
> **AI 提供**：
> - 部署流程圖（完整的部署步驟視覺化）
> - 部署時間表（建議的部署時間窗口）
> - 回滾手冊（詳細的回滾步驟和指令）
> - 監控儀表板（需要監控的指標清單）
> - 溝通計畫（部署前中後的溝通安排）
>
> **需人工確認**：
> - ✅ 部署策略是否合適
> - ✅ 部署步驟是否完整
> - ✅ 回滾計畫是否可執行
> - ✅ 監控是否充分
> - ✅ 部署時間窗口是否合適
>
> **產出文件**：
> - 部署方案 (Deployment Plan)
> - 回滾手冊 (Rollback Playbook)
> - 監控指標定義 (Monitoring Metrics)
> - 部署檢查清單 (Deployment Checklist)

---

### 階段 9：知識轉移與文檔更新 (20-30 分鐘)

#### 步驟 9.1：文檔更新清單
```
執行指令：
「請列出需要更新的文檔和知識庫」
```

#### 步驟 9.2：文檔更新內容 (Technical-Writer + SA)

**技術文檔更新**：
- Architecture Diagram 更新
- API Documentation 更新
- Database Schema 文檔
- 設定檔說明更新
- Troubleshooting Guide 補充

**使用者文檔更新**：
- User Guide 更新 (如有 UI 變更)
- Release Notes
- Migration Guide (如有 breaking changes)
- FAQ 補充

**知識庫更新**：
- 設計決策記錄 (ADR)
- 常見問題解答
- 除錯指南
- 維護手冊

#### 步驟 9.3：知識記錄與分享

> 💡 **v0.01 開發專注版說明**：以下檢查清單依團隊規模分為精簡版（2-3 人團隊）和完整版（4+ 人團隊）。
> 2 人團隊無需正式會議，透過文檔記錄和程式碼走查即可完成知識轉移。

**知識轉移檢查清單 (Knowledge Transfer Checklist)**：

> 確保關鍵知識不遺失，依類別確認交接

| 類別 | 檢查項目 | 完成 |
|------|---------|------|
| **技術知識** | | |
| | 架構決策記錄 (ADR) 已更新 | [ ] |
| | 關鍵演算法/邏輯說明文檔 | [ ] |
| | 資料庫 Schema 變更說明 | [ ] |
| | API 變更與向下相容說明 | [ ] |
| **營運知識** | | |
| | 部署/回滾流程文檔 | [ ] |
| | 監控告警閾值說明 | [ ] |
| | 常見問題排查指南 | [ ] |
| **業務知識** | | |
| | 功能使用說明 | [ ] |
| | 使用者影響說明 | [ ] |
| **知識分享方式**（依團隊規模選擇） | | |
| | 🔹 精簡版（2-3 人）：程式碼走查 + 文檔 Review | [ ] |
| | 🔹 完整版（4+ 人）：團隊分享會 + 運維交接 + 客服培訓 | [ ] |

**知識轉移完成標準**：
- ✅ 團隊所有成員理解核心變更內容（2 人團隊 = 全員）
- ✅ 文檔可供未來維護者獨立參考
- ✅ 緊急聯絡人清單已更新

**產出文件**：
- 文檔更新清單 (Documentation Updates)
- Release Notes
- 知識轉移記錄 (Knowledge Transfer Log)

---

### 階段 10：執行與驗證 (實際開發時間)

#### 步驟 10.1：實作階段

> 🔴 **提醒**：實作過程必須嚴格遵守「開發-編譯-測試循環」（參考步驟 7.2 強制規則）

這個階段由開發團隊執行實際開發：
1. 按照實作計畫開發（**每完成一個功能單元立即編譯+測試**）
2. 撰寫單元測試
3. 本地驗證
4. 提交 Pull Request
5. 程式碼審查
6. 整合測試

AISDLC 在此階段提供：
- 實作檢查清單輔助
- 程式碼審查標準
- 測試案例參考

#### 步驟 10.2：測試執行階段

按照測試計畫執行：
1. 單元測試執行
2. 整合測試執行
3. 回歸測試執行
4. 效能測試 (如適用)
5. 安全性測試 (如適用)
6. UAT (User Acceptance Testing)

#### 步驟 10.3：部署執行階段

**建議 Skill**：`/release-management`、`/devops-github-actions`
> - **部署前**：執行 `/release-management`，描述版本號和發布範圍 → 產出 Release Checklist 和 Release Notes
> - **Production 部署後**：再次執行 `/release-management` 驗收 → 確認 Smoke Test 通過

按照部署方案執行：
1. Pre-deployment 檢查
2. 部署到 Staging 環境
3. Staging 驗證
4. 部署到 Production
5. Production 驗證
6. 監控觀察 (24-48 小時)

#### 步驟 10.4：Mobile App 發布流程（如適用）🆕 v0.01

> 若變更涉及 Mobile App 更新，需額外執行以下發布步驟：

**Android 發布**：
1. 生成 Signed APK/AAB
2. 上傳至 Google Play Console
3. 設定 Internal/Closed/Open Testing Track
4. Beta 測試通過後提交審核
5. 分階段發布（10% → 50% → 100%）
6. 監控 Google Play Console Vitals（ANR、Crash Rate）

**macOS 發布**：
1. Code Signing + Notarization
2. 選擇發布管道：Mac App Store 或直接分發（DMG/PKG）
3. App Store 審核（若走 App Store 管道）
4. 或 Notarize + Staple → 分發 DMG

**iOS 發布（如適用）**：
1. TestFlight Internal/External Testing
2. App Store Connect 提交審核
3. Phased Release（7 天漸進發布）
4. 監控 App Analytics + Crash Reports

**跨平台版本管理策略** 🆕：
- App 版本號遵循 SemVer：`Major.Minor.Patch`（如 `2.1.3`）
- Build Number 遞增，不與版本號綁定
- API 版本相容性：維護 App 版本 ↔ API 版本相容矩陣
- 強制更新機制：API 回傳 `min_supported_version`，低於此版本提示更新
- Web/Android/macOS 版本號可獨立遞進，但 API 版本需統一

**審核被拒應對方案** 🆕：

| 被拒原因 | 應對措施 | 預計延遲 |
|---------|---------|---------|
| 權限說明不足 | 在 Info.plist / AndroidManifest 補充用途說明 | 1-2 天 |
| 隱私政策不完整 | 更新 Privacy Policy 頁面 | 1-2 天 |
| UI/UX 不符規範 | 依平台 HIG/Material Design 調整 | 2-3 天 |
| 功能不完整 | 補充缺少功能或移除未完成入口 | 3-5 天 |
| 安全性問題 | 修復安全漏洞，重新提交 | 2-5 天 |

> ⚠️ **預留緩衝**：首次提交建議預留 5-7 天審核時間，更新版本預留 2-3 天。

---

## 🎯 成功標準

### 分析完整性
- [ ] 代碼架構理解準確
- [ ] 影響範圍評估完整
- [ ] 風險識別充分
- [ ] 相依性分析清晰

### 設計合理性
- [ ] 技術方案符合需求
- [ ] 變更範圍最小化
- [ ] 相容性問題已解決
- [ ] 技術債考量平衡

### 測試完備性
- [ ] 測試案例覆蓋完整
- [ ] 回歸測試範圍充分
- [ ] 自動化測試比例合理
- [ ] 測試環境準備就緒

### 部署安全性
- [ ] 部署方案經過驗證
- [ ] 回滾���畫可執行
- [ ] 監控告警已設定
- [ ] 溝通計畫已執行

### 文檔完整性
- [ ] 技術文檔已更新
- [ ] Release Notes 完整
- [ ] 知識轉移已完成
- [ ] 維護手冊已更新

### 人機協作品質
- [ ] 所有確認點都已完成
- [ ] 無自主臆測，所有決策有人類確認
- [ ] 協作記錄完整可追溯
- [ ] 風險充分溝通

---

## 📊 時間分配參考

| 階段 | 預估時間 | 可彈性調整 |
|------|---------|-----------|
| 啟動和情境確認 | 20 分鐘 | ±5 分鐘 |
| 代碼理解與架構分析 | 1-1.5 小時 | 視系統複雜度 |
| 變更範圍界定與影響分析 | 40-60 分鐘 | 視變更複雜度 |
| 變更設計與技術方案 | 1-1.5 小時 | - |
| 相容性與依賴檢查 | 30-40 分鐘 | - |
| 測試策略與測試計畫 | 40-60 分鐘 | - |
| 實作指引與審查準備 | 30 分鐘 | - |
| 部署方案與回滾計畫 | 30-40 分鐘 | - |
| 知識轉移與文檔更新 | 20-30 分鐘 | - |
| **準備階段總計** | **3-4 小時** | |
| **實作與部署** | 依專案而定 | |

---

## 💡 最佳實踐

### 1. 深入理解再行動
- 不要急於修改，先充分理解代碼
- 繪製流程圖和資料流圖幫助理解
- 詢問原開發者背景和設計意圖
- 查看相關 commit 歷史和 PR 討論

### 2. 最小化變更範圍
- 遵循「最小驚訝原則」(Principle of Least Surprise)
- 避免「順手重構」，專注於需求
- 如需重構，應該是獨立的變更
- 評估每個變更的必要性

### 3. 充分的測試保護
- 變更前先補充測試（如缺少）
- 確保測試可重現問題（Bug 修復時）
- 回歸測試不可省略
- 重視邊界條件和異常情況

### 4. 謹慎處理資料遷移
- 資料遷移必須可回滾或冪等
- 大量資料遷移應分批執行
- 先在 Staging 環境驗證
- 保留完整的資料備份

### 5. 段階式部署降低風險
- 高風險變更採用金絲雀部署
- 使用 Feature Flag 控制功能開關
- 準備隨時回滾的心理準備
- 在低流量時段部署

### 6. 完整的知識記錄
- 記錄設計決策和理由 (ADR)
- 更新相關文檔和註解
- 分享給團隊成員
- 建立 Runbook 供維運參考

---

## 🚨 常見陷阱

### ❌ 避免這些錯誤

**1. 分析階段**
- ❌ 僅看表面，未理解深層邏輯
- ❌ 忽略隱藏的相依性（runtime dependencies）
- ❌ 低估遺留系統的複雜度
- ❌ 未考慮多環境差異（dev/staging/prod）

**2. 設計階段**
- ❌ 過度設計，引入不必要的複雜度
- ❌ 破壞既有的設計模式和慣例
- ❌ 忽視效能影響（N+1 query, memory leak）
- ❌ 未考慮並發和競態條件

**3. 測試階段**
- ❌ 僅測試 Happy Path，忽略錯誤處理
- ❌ 測試資料不夠真實，無法發現問題
- ❌ 跳過回歸測試，導致既有功能損壞
- ❌ 未測試資料遷移的可回滾性

**4. 部署階段**
- ❌ 未準備回滾計畫就直接部署
- ❌ 在高峰時段部署高風險變更
- ❌ 忽視監控，部署後未持續觀察
- ❌ 資料庫遷移與應用程式部署順序錯誤

**5. 溝通階段**
- ❌ 未通知相關團隊和使用者
- ❌ Release Notes 不清楚或缺失
- ❌ Breaking Changes 未充分溝通
- ❌ 未建立問題回報機制

---

## 🔍 特殊情境處理

### ⚡ 情境組合觸發指引 🆕

> 一個變更可能同時觸發多個情境。以下矩陣幫助判斷何時需要組合使用。

| 變更內容 | 主情境 | 可能觸發的附加情境 |
|---------|--------|-------------------|
| 在既有系統新增 Mobile App | A-E 任一 | + **F**（跨平台擴展） |
| 涉及退款/稅務/會計邏輯 | B（修改） | + **G**（合規驅動） |
| 修改涉及大量舊代碼 | B（修改） | + **A**（Legacy 改造） |
| Schema 大規模變更 | B/C | + **D**（資料密集） |
| 停用功能 + 新功能替代 | E（停用） | + Greenfield（新功能） |
| 架構級重構 + 加功能 | C（重構） | + Greenfield |

**觸發規則**：階段 3（影響分析）完成後，檢查是否需要啟用附加情境。

### 📎 AISDLC Workflow 連結指引 🆕

> Brownfield SOP 各階段應連結使用的 AISDLC Workflow。

| SOP 階段 | 對應 AISDLC Workflow | 用途 |
|---------|---------------------|------|
| 階段 3 影響分析 | `requirements-change-management` | 結構化管理變更需求 |
| 階段 4 API 變更 | `api-specification-generation` | 生成/更新 API 規格文件 |
| 階段 5 相容性 | `document-consistency-check` | 驗證文檔間一致性 |
| 階段 6 測試 | 參考 `docs_template/core/tests/` | 使用標準測試案例模板 |
| 新增功能 | `user-story-and-design` | 為新功能產出 User Story + AC |

> ⚠️ **注意**：Brownfield 情境中「新增功能」仍需產出 User Story（使用 `user-story-and-design` workflow），確保需求結構化定義。

---

### 情境 A：Legacy 代碼改造
**特徵**：代碼年代久遠、缺少測試、文檔不全

**調整策略**：
1. 增加「代碼考古」時間（+1-2 小時）
2. 優先補充測試再改動
3. 採用「絞殺者模式」(Strangler Pattern) 逐步替換
4. 建立知識文檔避免知識流失

### 情境 B：緊急 Bug 修復
**特徵**：時間緊迫、影響嚴重、需快速上線

**快速通道**：
1. 縮減分析時間，專注於問題核心
2. 採用最小變更方案
3. 重點測試問題場景和回歸測試
4. 準備快速回滾機制
5. 排程後續完整修復（如為 Workaround）

### 情境 C：大規模重構
**特徵**：影響範圍廣、技術債清理、架構改進

**調整策略**：
1. 分階段執行，每階段獨立可部署
2. 建立完整的測試保護網
3. 使用 Feature Flag 控制切換
4. 準備 A/B Testing 驗證效果
5. 充足的時間緩衝（2-3x 估算）

### 情境 D：資料密集型變更
**特徵**：涉及大量資料遷移、Schema 變更

**特別注意**：
1. 資料遷移腳本必須冪等
2. 準備資料驗證腳本
3. 分批執行，避免鎖表過久
4. 準備資料修復腳本（Rollback Plan）
5. 在 Staging 驗證完整流程

### 情境 E：功能停用/刪除 (Deprecation) 🆕 v0.01
**特徵**：停用舊功能模組、替換為新版本、清理技術債

> ⚠️ **功能停用是高風險操作**：與新增功能不同，停用功能的主要風險是「隱性依賴」和「資料合規」。請確實執行以下「依賴普查」步驟。

**🔴 第一步：停用前完整依賴普查（必做，不可跳過）**

在開始任何程式碼修改前，必須完成以下普查：

| 普查類型 | 普查方法 | 發現影響 |
|---------|---------|---------|
| **代碼依賴** | grep/IDE 全專案搜尋被停用模組的引用 | 需重構或移除 |
| **共用組件** | 識別哪些 UI 組件同時被停用和保留模組使用 | 需分離後才能移除 |
| **資料庫 FK** | 檢查 DB Schema 中的 Foreign Key 引用 | 需先移除 FK 再刪表 |
| **外部 API 使用者** | 檢查 API Gateway 日誌，識別哪些客戶端仍在呼叫 | 需通知並等待遷移 |
| **第三方服務訂閱** | 確認停用模組是否有 Webhook 訂閱或 Cron Job | 需取消訂閱 |
| **搜尋引擎索引** | 使用 Google Search Console 確認停用頁面的索引量 | 需301重定向 |
| **環境變數/Secret** | 確認停用模組使用的 API Key 是否被其他模組共用 | 不可直接刪除共用 Key |
| **CI/CD 流程** | 確認 pipeline 是否有與停用模組相關的建置步驟 | 需更新 CI/CD |

**🔴 第二步：資料保留合規確認（必做，涉及法規）**

在移除任何資料前，必須確認：

| 確認項目 | 說明 | 常見法規要求 |
|---------|------|------------|
| **資料保留年限** | 相關業務資料是否有法定保留期限？ | 商業帳冊 5-7 年（台灣商業法）、個資 最短 1 年 |
| **資料歸檔方案** | 保留期限內資料如何歸檔？（Cold Storage / 獨立 DB） | 確保可查詢，但不影響生產系統效能 |
| **資料刪除通知** | 是否需通知資料主體（使用者）其資料將被刪除？ | GDPR Art.17、台灣個資法 |
| **刪除紀錄** | 執行資料刪除時，是否需保留刪除紀錄？ | 審計要求 |
| **備份保留** | 停用前的備份需保留多久？ | 建議至少保留至保留年限結束 |

> ⚠️ **發現需保留的資料時**：不可直接刪除，需先歸檔至 Cold Storage 或獨立歸檔資料庫，並更新保留期限追蹤記錄。

**分階段廢棄方案（依複雜度選擇）**

| 方案 | 適用情境 | 時程 |
|------|---------|------|
| **快速停用** | 無外部使用者，無資料保留需求 | 1-2 週 |
| **標準廢棄**（推薦） | 有內部依賴，資料需歸檔 | 4-6 週 |
| **長期廢棄** | 有外部 API 使用者，需遷移期 | 2-3 個月 |

**標準廢棄策略（推薦）**：
1. **標記 Deprecated**：在 API 回應中加入 `Sunset` Header、UI 顯示停用通知
2. **設定停用時間表**：通知使用者，提供遷移期（建議 30-90 天）
3. **功能對等驗證**：確認新版完全覆蓋舊版功能（Feature Parity Test）
4. **URL 重導向**：舊版 URL 301 重導至新版（**並通知 SEO 影響**：提交 Sitemap、Search Console）
5. **依賴遷移**：確保所有依賴模組已遷移至新版 API
6. **資料歸檔**：依法規保留年限，歸檔至 Cold Storage
7. **最終移除**：停用期結束後，移除舊版代碼、測試、配置檔
8. **死代碼清理**：移除相關的測試代碼、配置檔、依賴項、文檔

**停用檢查清單**：
- [ ] **依賴普查完成**（代碼/外部API/第三方/SEO）
- [ ] **資料保留合規確認**（保留年限/歸檔方案）
- [ ] 新版功能對等驗證通過
- [ ] 所有依賴模組已遷移
- [ ] 使用者已收到停用通知
- [ ] URL 重導向已設定（301 且 Sitemap 已更新）
- [ ] 舊版 API 已標記 Deprecated（含 Sunset Header）
- [ ] 資料已歸檔至 Cold Storage（依保留年限）
- [ ] 停用期結束後代碼已移除
- [ ] CI/CD Pipeline 已更新（移除停用模組相關步驟）
- [ ] 環境變數/Secret 已清理（注意勿刪除共用 Key）
- [ ] 文檔已更新（移除舊版引用）
- [ ] **否定測試已執行**（確認停用功能確實不可存取）

### 情境 F：跨平台擴展 (Multi-Platform) 🆕 v0.01
**特徵**：既有 Web 系統擴展至 Mobile（Android/iOS/macOS）

**執行策略（8 步）**：

1. **平台識別與 Agent 載入**：在階段 1.2.1 觸發 Platform_Agent_Selection_Guide
   - 載入 `sd-mobile-architect` + `qa-mobile-tester`
   - 涉及硬體整合（掃碼、NFC）→ 額外載入 `integration-specialist`

2. **API 適配設計**：
   - 認證機制：Mobile 建議 JWT（無狀態），Web 可用 Session
   - 批量請求：Mobile 應支援 Batch API 減少網路請求
   - 數據壓縮：啟用 gzip/brotli，Mobile 端流量敏感
   - 分頁策略：Cursor-based pagination（適合 Mobile 無限滾動）

3. **離線支援架構**（如需要）：
   - 本地 DB：Android 使用 Room/SQLite，macOS 使用 Core Data/SQLite
   - 同步策略：Last-Write-Wins 或 CRDT 衝突解決
   - 佇列機制：離線操作暫存，恢復網路後批量同步
   - ⚠️ 倉庫/門市環境可能無穩定網路，此為核心需求

4. **硬體整合差異**：
   - **掃碼功能**：
     - Android：CameraX + ML Kit Barcode Scanning
     - macOS：AVFoundation 相機 API 或外接 USB 掃碼槍（HID 模式）
     - ⚠️ 外接掃碼槍通常模擬鍵盤輸入，需不同的輸入處理邏輯
   - **NFC/RFID**（如需要）：Android NFC API，macOS 需外接讀卡機

5. **推送通知**：FCM（Android）/ APNs（macOS/iOS）整合

6. **跨平台測試策略**：
   - 設備碎片化測試：至少覆蓋 Top 5 Android 裝置 + macOS Intel/Apple Silicon
   - 權限處理測試：相機、儲存、通知權限的授權/拒絕流程
   - 離線/弱網測試：模擬 2G/3G/斷網環境
   - 電量與記憶體測試：長時間掃碼操作的資源消耗

7. **版本管理策略**：
   - App 版本號：遵循 SemVer（Major.Minor.Patch）
   - API 向後相容：App 版本 < 最新版時，API 需支援舊版格式
   - 強制更新機制：API 回傳 `min_app_version`，低於此版本強制更新
   - 版本矩陣：維護 App 版本 ↔ API 版本相容性對照表

8. **App 發布與審核應對**：
   - 發布流程：參考步驟 10.4
   - **審核被拒應對方案**：
     - 權限問題：明確說明每個權限用途（相機用於掃碼等）
     - 隱私政策：確保 Privacy Policy 涵蓋所有資料收集
     - 內容審查：避免展示敏感內容，確保符合商店政策
     - 被拒後：分析拒絕理由 → 修正 → 重新提交（預留 3-5 天緩衝）

**🆕 新平台首次發布前置作業清單**（首次發布 App 必做，更新版本可跳過）

| 平台 | 前置項目 | 預估時間 | 說明 |
|------|---------|---------|------|
| **Android** | Google Play 開發者帳號申請 | 1-3 天 | 需信用卡，$25 一次性費用 |
| **Android** | Signing Keystore 生成與安全儲存 | 0.5 天 | **永遠不可遺失！** 遺失無法更新 App |
| **Android** | FCM 專案設定 + google-services.json | 1 天 | Firebase Console 設定 |
| **Android** | Google Play 應用程式頁面建立（截圖、說明、圖標）| 2-3 天 | 行銷素材準備 |
| **macOS** | Apple Developer Program 申請（$99/年） | 3-7 天 | 需等待審核 |
| **macOS** | Code Signing 憑證申請（Developer ID） | 1 天 | Keychain Access 生成 |
| **macOS** | Notarization 設定（xcrun notarytool）| 1 天 | Apple 公證必要（macOS 10.15+）|
| **macOS** | 選擇分發管道：Mac App Store 或直接分發（DMG）| 0.5 天 | 各有不同審核流程 |
| **共用** | Privacy Policy 頁面建立（中英文）| 1-2 天 | App Store / Play Store 強制要求 |
| **共用** | 使用者條款（Terms of Service）更新 | 1 天 | 涵蓋 App 使用範圍 |
| **共用** | App 圖示（各尺寸）+ 啟動畫面設計 | 2-5 天 | 設計資源準備 |
| **共用** | Push Notification 使用者授權說明準備 | 0.5 天 | 需明確說明推播用途 |

> ⚠️ **重要**：以上前置作業需在開發啟動時就規劃，避免開發完成後才發現缺少憑證或帳號，導致延誤上線。建議在 AISDLC 階段 1 完成後立即啟動申請流程。

**跨平台擴展檢查清單**：
- [ ] **新平台前置作業已完成**（開發者帳號/憑證/FCM/Privacy Policy）
- [ ] Platform_Agent_Selection_Guide 已執行
- [ ] Mobile API 設計考量已完成（認證/批量/壓縮）
- [ ] 離線同步策略已確定（如適用）
- [ ] 硬體整合方案已驗證（掃碼/NFC）
- [ ] CI 環境硬體模擬測試策略已確定
- [ ] 跨平台測試計畫已制定
- [ ] 版本管理策略已定義
- [ ] App Store 審核準備已完成（截圖/說明/圖標）
- [ ] Privacy Policy 已更新

### 情境 G：合規驅動變更 🆕 v0.01
**特徵**：由法規、會計準則、產業標準驅動的系統變更

**自動觸發條件**（若變更涉及以下任一項，自動啟用情境 G）：
- 💰 退款/退貨邏輯變更（涉及營業稅、統一發票）
- 📊 財務報表/會計分錄邏輯變更
- 🔒 個資處理方式變更（GDPR/個資法）
- 📋 產業法規要求（食品安全、旅宿法規等）
- 🧾 發票/稅務計算邏輯變更

**執行策略（7 步）**：

1. **載入 Compliance Agent**：在階段 1 觸發 `compliance-officer`
   - 同時載入相關領域 Agent（如 `ba-business-analyst` 協助業務規則釐清）

2. **合規需求分析**：
   - 識別適用法規/準則（會計準則、稅法、個資法、產業法規）
   - 確認合規截止日期（法規生效日）
   - 評估不合規的風險與罰則

3. **業務驗證規劃**：
   - **驗證者**：指定領域專家（會計師、法務、稅務顧問）
   - **驗證內容**：業務邏輯正確性、計算公式、報表格式
   - **驗證方式**：提供測試數據 + 預期結果，由專家核對
   - **簽核文件**：產出「合規驗證簽核單」（含驗證者、日期、結論）

4. **歷史資料處理**：
   - 評估是否需要重算歷史資料（影響範圍、資料量、時間成本）
   - 若需重算：準備批次處理腳本 + 驗證機制
   - 若不需重算：記錄「新舊規則分界點」，確保報表正確區分

5. **審計追蹤**：
   - 確保所有變更有完整 Git 記錄
   - 關鍵業務邏輯變更需加入 Change Log（who/when/why/what）
   - 保留舊版計算邏輯的快照（供審計對照）

6. **合規證明產出**：
   - 合規驗證報告（Compliance Verification Report）
   - 業務邏輯變更對照表（Before/After）
   - 領域專家簽核記錄
   - 測試數據與預期結果對照

7. **持續合規監控**：
   - 設定合規相關監控告警（如：稅率變更通知）
   - 建立定期合規審查排程

**合規驅動變更檢查清單**：
- [ ] 適用法規/準則已識別
- [ ] Compliance Agent 已載入
- [ ] 領域專家驗證者已指定
- [ ] 業務邏輯變更已經領域專家驗證
- [ ] 歷史資料處理策略已確定
- [ ] 審計追蹤記錄完整
- [ ] 合規驗證報告已產出
- [ ] 領域專家簽核已完成

---

## 📞 需要幫助？

### 卡在某個階段
使用以下指令尋求幫助：
```
「我在 [階段名稱] 遇到困難，具體是 [描述問題]」
```

### 分析遇到障礙
如果代碼太複雜或文檔缺失：
```
「代碼分析遇到以下問題：[具體描述]
需要協助理解 [特定模組/功能]」
```

### 風險評估需要建議
如果不確定風險等級：
```
「此變更涉及 [描述]，請協助評估風險等級和建議緩解措施」
```

### 測試策略需要建議
如果測試覆蓋不確定：
```
「此變更的測試策略是否充分？是否有遺漏的測試場景？」
```

### 部署方式選擇
如果不確定部署策略：
```
「此變更應該採用哪種部署方式？請提供建議和理由」
```

---

## 📚 實際案例走查

### 案例 1：Legacy 系統現代化改造

#### 背景
某金融機構核心業務系統使用 10 年前的 ASP.NET Web Forms 技術，面臨維護困難、效能瓶頸、無法擴展等問題。決定逐步現代化為 .NET Core + React 架構。

#### 挑戰
- ❌ **技術棧老舊**：ASP.NET Web Forms、SQL Server 2008、jQuery
- ❌ **文檔缺失**：系統架構文檔、API 文檔完全缺失
- ❌ **測試覆蓋率 0%**：沒有任何自動化測試
- ❌ **強耦合**：UI、業務邏輯、資料存取混在一起
- ❌ **業務風險**：系統處理每日百萬筆交易，不能中斷

#### 執行步驟

**Phase 1：系統分析與文檔重建 (3 週)**
```
載入 AISDLC_INIT.md + Code-Analyzer
→ 使用 NDepend 分析程式碼結構
→ 使用 Redgate SQL Doc 生成資料庫文檔
→ 🔴 確認系統架構圖

分析結果:
- 代碼行數: 450,000 行 C# + 120,000 行 JavaScript
- 核心模組: 12 個 (交易、帳戶、報表、風控等)
- 資料表: 280 個
- Stored Procedures: 580 個
- 循環依賴: 23 處
- 程式碼複雜度: 平均 CC = 18 (高)

產出文檔:
1. 系統架構圖 (使用 C4 Model)
2. 資料庫 ERD
3. 業務流程圖 (關鍵 8 個流程)
4. API 端點清單 (逆向工程)
```

**Phase 2：測試保護網建立 (4 週)**
```
策略: Golden Master Testing + End-to-End Testing

1. Golden Master Tests (特徵測試)
   - 記錄現有系統的實際輸出
   - 涵蓋 20 個關鍵業務場景
   - 使用 Approval Tests .NET

2. E2E 測試 (Playwright)
   - 自動化 50 個關鍵使用者流程
   - 涵蓋率: 關鍵流程 100%

3. 資料庫整合測試
   - 測試 80 個關鍵 Stored Procedures
   - 使用 tSQLt 框架

結果:
- 測試覆蓋率: 0% → 65% (關鍵路徑 100%)
- E2E 測試執行時間: 25 分鐘
- 建立回歸測試保護網
```

**Phase 3：絞殺者模式漸進遷移 (6 個月，6 個 Sprint)**
```
採用 Strangler Pattern 逐步替換:

Sprint 1-2: 建立新架構基礎
- 建立 .NET Core Web API 專案
- 設定 API Gateway (Ocelot)
- 建立 React 前端框架
- 雙寫機制: 同時寫入新舊資料庫

Sprint 3: 遷移第一個模組 (使用者管理)
- 實作 User Service (.NET Core)
- 實作前端 User Management UI (React)
- API Gateway 路由: /api/users/* → 新系統
- 其他路由 → 舊系統
- 監控 2 週無異常

Sprint 4: 遷移第二個模組 (帳戶查詢)
- 實作 Account Query Service
- 前端 Account Dashboard (React)
- 逐步放量: 10% → 50% → 100%

Sprint 5-6: 遷移其他模組
- Transaction Service
- Report Service
- Risk Management Service
- ...

每個 Sprint:
1. 新舊系統並行運行
2. Feature Flag 控制切換
3. 監控關鍵指標 (回應時間、錯誤率)
4. 確認無異常後擴大範圍
```

**Phase 4：資料遷移與整合 (2 個月)**
```
資料遷移策略:

1. 雙寫階段 (4 週)
   - 新資料同時寫入新舊資料庫
   - 驗證資料一致性
   - 使用 Debezium 同步歷史資料

2. 資料驗證 (2 週)
   - 比對新舊資料庫資料
   - 差異率 < 0.01%
   - 修正不一致

3. 切換階段 (2 週)
   - 設定維護視窗 (週末凌晨)
   - 最終資料同步
   - 切換資料庫連線
   - 驗證所有功能正常
```

**Phase 5：舊系統退役 (1 個月)**
```
1. 保留 30 天 (雙跑)
   - 新系統為主,舊系統備用
   - 持續監控

2. 關閉舊系統 API (1 週)
   - 確認無流量
   - 關閉舊系統服務

3. 資料歸檔 (1 週)
   - 舊資料庫匯出備份
   - 長期冷儲存

4. 基礎設施回收 (2 週)
   - 關閉舊伺服器
   - 節省成本 $50k/年
```

#### 關鍵成果
- ✅ **現代化完成**：100% 功能遷移至新架構
- ✅ **效能提升**：API 回應時間 1.2s → 180ms (-85%)
- ✅ **可維護性改善**：程式碼複雜度 CC 18 → 6 (-67%)
- ✅ **測試覆蓋率**：0% → 82%
- ✅ **零停機遷移**：無業務中斷
- ✅ **成本節省**：基礎設施成本 -40%

#### 時程與成本
- **總時程**：12 個月
- **人力**：6 後端工程師 + 3 前端工程師 + 2 QA + 1 DevOps
- **成本**：約 $800k (人力) + $150k (基礎設施)
- **ROI**：維護成本降低 50% (每年節省 $500k)

#### 經驗教訓
1. **測試先行**：Golden Master Testing 是 Legacy 系統的救命稻草
2. **絞殺者模式**：漸進式遷移降低風險，可隨時停止或回滾
3. **雙寫驗證**：新舊系統並行，確保資料一致性
4. **監控必須**：每個遷移階段都需要密切監控
5. **業務優先**：依業務價值排序遷移順序

---

### 案例 2：緊急 Bug 修復流程

#### 背景
電商平台在雙 11 促銷活動前 3 天，發現購物車結帳金額計算錯誤，部分優惠券無法正確折抵。Bug 嚴重且緊急，需要在 24 小時內修復上線。

#### 挑戰
- ❌ **時間緊迫**：促銷活動前 3 天，必須 24 小時內修復
- ❌ **影響範圍廣**：涉及優惠券、購物車、訂單三個模組
- ❌ **複雜業務邏輯**：多種優惠券組合規則 (滿減、折扣、買一送一)
- ❌ **高流量風險**：預計促銷活動流量為平時 50 倍
- ❌ **無完整測試**：購物車模組測試覆蓋率僅 30%

#### 執行步驟

**Hour 0-2：緊急情境啟動與問題定位**
```
載入 AISDLC_INIT.md (緊急模式)
→ Code-Analyzer 快速掃描
→ 重現問題場景
→ 🔴 確認問題根因

問題重現:
1. 測試案例 1: 滿減券 (滿 $1000 減 $100)
   - 購物車金額 $1200
   - 套用優惠券
   - 實際: $1200 (優惠券未折抵) ❌
   - 預期: $1100 ✅

2. 測試案例 2: 折扣券 (9 折)
   - 購物車金額 $500
   - 套用優惠券
   - 實際: $500 ❌
   - 預期: $450 ✅

根因分析:
使用 Debugger 追蹤,發現問題在 DiscountCalculator.js:

function calculateDiscount(cart, coupon) {
  if (cart.total > coupon.minAmount) {  // Bug: 應該 >=
    return coupon.discountValue;
  }
  return 0;
}

問題: 邊界條件錯誤 (> 應為 >=)
```

**Hour 2-6：快速修復與測試**
```
修復策略: 最小變更 + 充分測試

1. 程式碼修復
// Before (Bug)
if (cart.total > coupon.minAmount) {
  return coupon.discountValue;
}

// After (Fixed)
if (cart.total >= coupon.minAmount) {
  return coupon.discountValue;
}

2. 補充單元測試 (優先)
describe('DiscountCalculator', () => {
  it('should apply coupon when cart total equals min amount', () => {
    const cart = { total: 1000 };
    const coupon = { minAmount: 1000, discountValue: 100 };

    const discount = calculateDiscount(cart, coupon);

    expect(discount).toBe(100);  // 邊界條件測試
  });

  it('should apply coupon when cart total exceeds min amount', () => {
    const cart = { total: 1200 };
    const coupon = { minAmount: 1000, discountValue: 100 };

    const discount = calculateDiscount(cart, coupon);

    expect(discount).toBe(100);
  });

  it('should not apply coupon when cart total is below min amount', () => {
    const cart = { total: 999 };
    const coupon = { minAmount: 1000, discountValue: 100 };

    const discount = calculateDiscount(cart, coupon);

    expect(discount).toBe(0);
  });
});

3. 整合測試
- 測試所有優惠券類型組合
- 測試邊界條件 (剛好滿額、差 1 元、超過 1 元)
- 測試多張優惠券疊加

結果:
- 單元測試: 15 個 (全通過) ✅
- 整合測試: 8 個場景 (全通過) ✅
```

**Hour 6-12：Staging 環境驗證**
```
部署到 Staging:
1. 匯入生產資料快照 (去識別化)
2. 執行完整回歸測試套件
3. 手動測試 50 個優惠券組合場景
4. 效能測試 (壓測 10,000 req/s)

驗證結果:
✅ 所有測試通過
✅ 效能無退化 (回應時間 < 100ms)
✅ 無新增 Bug
```

**Hour 12-18：生產環境部署**
```
部署策略: 金絲雀部署 + Feature Flag

1. 金絲雀部署 (1% 流量)
   - 部署到 2/200 台伺服器
   - 觀察 2 小時
   - 監控錯誤率、回應時間

2. 逐步擴大 (10% → 50% → 100%)
   - 每階段觀察 1 小時
   - 無異常則繼續

3. Feature Flag 備援
   - 保留舊邏輯程式碼
   - 可即時切換回舊版

部署時程:
- 12:00: 金絲雀 1%
- 14:00: 擴大至 10%
- 15:00: 擴大至 50%
- 16:00: 全量 100%
- 18:00: 確認穩定
```

**Hour 18-24：監控與驗證**
```
監控指標:
- 錯誤率: 0.01% (正常範圍) ✅
- API 回應時間: P95 < 120ms ✅
- 優惠券套用成功率: 99.8% ✅
- 訂單金額正確率: 100% ✅

業務驗證:
- 客服回報優惠券問題: 0 件 ✅
- 測試訂單: 200 筆 (全部正確) ✅
```

#### 關鍵成果
- ✅ **24 小時內修復**：從發現到上線僅 18 小時
- ✅ **零停機部署**：金絲雀部署無業務中斷
- ✅ **測試覆蓋提升**：購物車模組 30% → 85%
- ✅ **促銷活動順利**：雙 11 無優惠券問題
- ✅ **業務損失避免**：預計避免損失 $2M+

#### 時程與成本
- **總時程**：24 小時 (實際 18 小時)
- **人力**：2 後端工程師 + 1 QA + 1 DevOps
- **成本**：約 $5k (加班費)
- **ROI**：避免業務損失 $2M+ 和品牌聲譽損害

#### 緊急修復 SOP
1. **快速定位** (2 小時)：重現問題 → 追蹤根因 → 確認影響範圍
2. **最小變更** (4 小時)：只修復核心問題，不做額外重構
3. **充分測試** (6 小時)：補充單元測試 + 整合測試 + 回歸測試
4. **漸進部署** (6 小時)：金絲雀 → 逐步擴大 → 全量
5. **持續監控** (6 小時)：觀察關鍵指標，確認穩定

#### 經驗教訓
1. **測試補強**：緊急修復後必須補充測試，避免再次發生
2. **金絲雀部署**：高風險變更使用金絲雀部署降低風險
3. **Feature Flag**：緊急情況保留快速回滾機制
4. **監控必須**：部署後持續監控至少 6 小時
5. **事後檢討**：修復後進行 Postmortem，找出流程改進點

---

## 🎓 相關資源

- [Brownfield Prompt Templates](../../prompts/scenario-prompts/brownfield-prompts.md)
- [Code Analysis Workflow](../../workflow/scenario-specific/brownfield-analysis-flow.md)
- [Code Analyzer Agent](../../agent/specialized/code-analyzer-zh.yaml)
- [Dev Senior Agent](../../agent/specialized/dev-senior-zh.yaml)
- [Brownfield 文檔模板](../../docs_template/scenario_specific/brownfield/)

---

## 📋 快速檢查清單

### 開始前
- [ ] 代碼庫存取權限已確認
- [ ] 變更需求已清楚描述
- [ ] 測試環境已準備就緒
- [ ] 相關文檔已收集

### 分析階段
- [ ] 架構分析已完成並確認
- [ ] 影響範圍已完整評估
- [ ] 風險已識別並評級
- [ ] 相容性問題已分析

### 設計階段
- [ ] 技術方案已選定並確認
- [ ] 實作步驟已規劃
- [ ] 相依性問題已解決
- [ ] 資料遷移方案已制定（如需要）

### 測試階段
- [ ] 測試計畫已制定並確認
- [ ] 測試案例已準備
- [ ] 測試環境已就緒
- [ ] 自動化測試已實作

### 部署階段
- [ ] 部署方案已制定並確認
- [ ] 回滾計畫已準備並驗證
- [ ] 監控告警已設定
- [ ] 溝通計畫已執行

### 完成後
- [ ] 所有測試已通過
- [ ] 文檔已更新
- [ ] 知識已轉移
- [ ] 監控正常運作

---

**下一步**：準備好材料後，執行 [階段 1](#階段-1啟動和情境確認-20-分鐘) 開始你的 Brownfield 專案改造旅程！

---

## AutoClaude 自動化執行（Phase Z / v0.02 新增）

> 規格凍結（SPEC_FROZEN）後，本場景的 AT 契約可交由 AutoClaude 引擎自動執行實作與雙重驗證。
> 標準作業全文：`workflow/sdd-autoclaude-bridge/SDD_AUTOCLAUDE_BRIDGE.md`；
> 翻譯保真規則：`governance/rules/R-9.38-playbook-translation-fidelity.yaml`。

1. **編譯**（AutoClaude/ 目錄）：`python -m autoclaude.tools.sdd_compile --spec-dir <docs path> --out playbooks/sdd_bridge.yaml`
   - 規格未凍結 → exit 2 拒絕（Spec-First 硬閘）；weak_regex 斷言入 audit log。
2. **人工 review** 生成的 playbook YAML（SCG-4 精神：生成物 = 待審工件）。
3. **執行**：`python -m autoclaude playbooks/sdd_bridge.yaml` — SddGovernancePlugin 自動守 SCG 閘門、記帳契約違反、防規格 drift。
4. 🔴 人工確認閘門不可由自動化跳過（Rule 8）；ESCALATION 後必等人工。
