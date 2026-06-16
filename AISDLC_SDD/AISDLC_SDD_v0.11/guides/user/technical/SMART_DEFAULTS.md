# AISDLC-SDD v0.01 智能預設值配置
# Smart Defaults Configuration

**版本**: v0.03-phase4
**建立日期**: 2025-11-03 (更新至v0.01)
**用途**: 減少使用者決策負擔，遵循 80/20 原則

---

## 🎯 設計原則

### 80/20 Rule (帕累托法則)

```yaml
principle:
  coverage: 80% 的專案可使用預設值
  customization: 20% 的特殊需求允許客製化
  goal: 降低 60%+ 的決策時間

philosophy:
  - 預設值基於業界最佳實踐
  - 所有預設值可被覆寫
  - 新手友善，專家不受限
  - 漸進式揭露複雜度
```

---

## 1. 技術棧預設值 (Technology Stack Defaults)

### 1.1 Web Application

```yaml
web_application:
  frontend:
    primary_choice:
      framework: React 18.x
      language: TypeScript 5.x
      reason: |
        - 業界主流 (NPM weekly downloads: 20M+)
        - 生態系完整，第三方套件豐富
        - 團隊技能普及度高
        - Meta 官方長期支持
      override_options:
        - Vue.js 3.x (更簡單的學習曲線)
        - Angular 17+ (企業級大型應用)
        - Svelte 4 (更輕量高效能)

    state_management:
      primary: Redux Toolkit
      alternative: Zustand / Jotai (輕量專案)
      reason: Redux 成熟穩定，工具鏈完整

    styling:
      primary: Tailwind CSS
      alternative: CSS Modules / Styled Components
      reason: Utility-first，開發速度快

    ui_library:
      primary: Material-UI (MUI) / Ant Design
      alternative: Chakra UI / shadcn/ui
      reason: 元件豐富，企業級品質

  backend:
    primary_choice:
      runtime: Node.js 20.x LTS
      framework: Express.js / Nest.js
      language: TypeScript 5.x
      reason: |
        - 與前端統一語言 (Full-stack TypeScript)
        - 非同步 I/O 效能佳
        - 套件生態豐富
      override_options:
        - Python + FastAPI (資料處理/ML 相關)
        - Java + Spring Boot (企業級/金融)
        - Go (高併發/微服務)

    orm:
      primary: Prisma
      alternative: TypeORM / Sequelize
      reason: 型別安全，開發體驗佳

    authentication:
      primary: JWT + Refresh Token
      alternative: Session-based / OAuth 2.0
      reason: Stateless，適合分散式系統

  database:
    primary_choice:
      relational: PostgreSQL 15.x
      reason: |
        - 功能完整 (JSON/全文搜尋/GIS)
        - 效能優秀
        - 開源且社群活躍
      override_options:
        - MySQL 8.x (更簡單配置)
        - SQL Server (Microsoft 生態系)

    nosql:
      primary: MongoDB 7.x
      reason: 彈性 schema，快速迭代
      use_case: 非結構化資料、快速原型

    cache:
      primary: Redis 7.x
      reason: 高效能，支援多種資料結構
      use_case: Session、快取、訊息佇列

  infrastructure:
    hosting:
      primary: AWS / Vercel (Frontend) + Railway (Backend)
      alternative: GCP / Azure / DigitalOcean
      reason: AWS 生態系完整，Vercel/Railway 部署簡單

    ci_cd:
      primary: GitHub Actions
      alternative: GitLab CI / CircleCI
      reason: 與 GitHub 整合，免費額度足夠

override_command:
  「改用 Vue.js」
  「後端使用 Python FastAPI」
  「資料庫使用 MySQL」
```

---

### 1.2 Mobile Application

```yaml
mobile_application:
  cross_platform:
    primary_choice:
      framework: React Native 0.72+
      language: TypeScript 5.x
      reason: |
        - 一套程式碼支援 iOS + Android
        - 與 Web 技術棧共用 (React)
        - 社群大，第三方套件多
      override_options:
        - Flutter (Google 支持，效能更佳)
        - Ionic (基於 Web 技術)

    state_management:
      primary: Redux Toolkit / MobX
      alternative: Zustand / Recoil
      reason: 與 Web 共用狀態管理邏輯

    navigation:
      primary: React Navigation
      alternative: React Native Navigation
      reason: 官方推薦，文檔完整

  ios_native:
    primary_choice:
      language: Swift 5.x
      ui_framework: SwiftUI
      architecture: MVVM
      reason: |
        - Apple 官方語言
        - SwiftUI 宣告式 UI，開發快速
      override_options:
        - UIKit (需支援舊版 iOS)

  android_native:
    primary_choice:
      language: Kotlin 1.9+
      ui_framework: Jetpack Compose
      architecture: MVVM
      reason: |
        - Google 官方推薦
        - Jetpack Compose 現代化 UI
      override_options:
        - Java (企業既有代碼)
        - XML Views (需支援舊版 Android)

  services:
    analytics:
      primary: Firebase Analytics
      alternative: Mixpanel / Amplitude
      reason: 免費，整合簡單

    crash_reporting:
      primary: Firebase Crashlytics
      alternative: Sentry
      reason: 即時回報，免費額度足夠

    push_notification:
      primary: Firebase Cloud Messaging (FCM)
      alternative: OneSignal
      reason: 官方支持，穩定可靠

override_command:
  「使用 Flutter」
  「iOS 原生開發使用 UIKit」
  「崩潰回報使用 Sentry」
```

---

### 1.3 Backend API Service

```yaml
backend_api:
  option_1_nodejs:
    runtime: Node.js 20.x LTS
    framework: Express.js (簡單) / Nest.js (企業級)
    language: TypeScript 5.x
    reason: JavaScript 全端統一
    use_case: 中小型專案，快速迭代

  option_2_python:
    runtime: Python 3.11+
    framework: FastAPI
    reason: 型別提示，自動生成 API 文檔
    use_case: 資料處理、ML 相關

  option_3_go:
    runtime: Go 1.21+
    framework: Gin / Echo
    reason: 高效能，併發處理能力強
    use_case: 高流量、微服務

  option_4_java:
    runtime: Java 17 LTS
    framework: Spring Boot 3.x
    reason: 企業級成熟方案
    use_case: 大型企業、金融

  default_selection_logic:
    if team_has_skill:
      選擇團隊熟悉的語言
    elif project_type == 'startup':
      選擇 Node.js (快速迭代)
    elif project_type == 'enterprise':
      選擇 Java Spring Boot
    elif project_has_ml:
      選擇 Python FastAPI
    elif high_concurrency:
      選擇 Go
```

---

## 2. Workflow 預設值 (by Scenario)

### 2.1 Greenfield (新專案開發)

```yaml
greenfield_defaults:
  execution_mode:
    primary: Standard Mode
    alternative: Quick Mode / Detailed Mode
    reason: 平衡效率與品質

  confirmation_points:
    critical: 8 個 (🔴 必須確認)
    recommended: 5 個 (🟡 建議確認)
    automated: 10+ 個 (✅ 自動執行)
    reason: 新專案風險可控，允許適度自動化

  document_level:
    prd: Medium Detail
    frd: Detailed (含完整 User Stories)
    srd: Detailed (含架構圖、API 規格)
    reason: 新專案需要完整文檔奠定基礎

  parallel_execution:
    enabled: Yes
    strategy: |
      - PRD + FRD 可並行準備（不同人員）
      - 多模組 SRD 可並行撰寫
      - 前後端開發可並行（基於 API 契約）
    time_saving: 23-38%

override_command:
  「使用 Quick Mode」(減少確認點)
  「使用 Detailed Mode」(增加確認點)
  「不使用並行化」(團隊人力不足)
```

---

### 2.2 Brownfield (既有專案維護)

```yaml
brownfield_defaults:
  execution_mode:
    primary: Balanced Mode
    reason: 需謹慎評估影響，但不過度冗長

  confirmation_points:
    critical: 5 個 (🔴 必須確認)
    recommended: 3 個 (🟡 建議確認)
    automated: 8+ 個 (✅ 自動執行)
    special_points:
      - 影響分析 (🔴 強制執行)
      - 回歸測試範圍確認 (🔴 強制執行)

  document_level:
    frd: Core Sections + Change Impact
    srd: Incremental (僅變更部分)
    test_plan: Regression Test Focus
    reason: 既有專案重點在影響分析，不需完整文檔

  risk_management:
    impact_analysis: Mandatory (強制執行)
    rollback_plan: Mandatory (強制執行)
    reason: 降低既有系統變更風險

override_command:
  「跳過影響分析」(不建議，需明確理由)
  「增加詳細文檔」(複雜變更)
```

---

### 2.3 Performance (效能優化)

```yaml
performance_defaults:
  execution_mode:
    primary: Quick Mode
    reason: 效能優化通常範圍明確，迭代快速

  confirmation_points:
    critical: 3 個 (🔴 必須確認)
    recommended: 2 個 (🟡 建議確認)
    automated: 12+ 個 (✅ 自動執行)
    special_points:
      - Baseline 基準建立 (🔴 強制執行)
      - 優化前後對比 (🔴 強制執行)

  benchmarking:
    automated: Yes
    tools: Lighthouse / k6 / Apache Bench
    baseline_required: Yes
    reason: 效能優化必須有量化指標

  optimization_strategy:
    ai_recommendation: 80% (AI 推薦優化方案)
    human_approval: 20% (人類批准實施)
    reason: 效能優化有標準解法，AI 可自動分析

override_command:
  「使用 Standard Mode」(複雜效能問題)
  「關閉自動化基準測試」(無測試環境)
```

---

### 2.4 Integration (第三方整合)

```yaml
integration_defaults:
  execution_mode:
    primary: Quick Mode
    reason: 整合範圍明確，遵循第三方 API 規範

  confirmation_points:
    critical: 4 個 (🔴 必須確認)
    recommended: 2 個 (🟡 建議確認)
    automated: 10+ 個 (✅ 自動執行)
    special_points:
      - API 文檔確認 (🔴 強制執行)
      - 認證機制設計 (🔴 強制執行)
      - 錯誤處理策略 (🔴 強制執行)

  documentation:
    api_research: Detailed (API 文檔完整閱讀)
    integration_design: Medium (認證+資料轉換)
    test_plan: Sandbox + Production
    reason: 整合成功關鍵在於理解第三方 API

  error_handling:
    retry_strategy: Exponential Backoff (預設)
    fallback: Required (必須設計降級方案)
    reason: 第三方服務不可控，必須有容錯

override_command:
  「不需要 Fallback」(非關鍵整合)
  「使用 Standard Mode」(複雜整合如 Salesforce)
```

---

## 3. 文檔模板預設值

### 3.1 PRD (Product Requirements Document)

```yaml
prd_defaults:
  template: PRD_Universal_Template.md
  sections: Full (所有章節)
  level_of_detail: Medium
  include_diagrams: Yes
  scenario_selection: 根據專案類型自動選擇

  greenfield:
    focus_sections:
      - 產品定位與目標
      - 使用者畫像
      - 核心功能
      - MVP 範圍
    skip_sections: []

  brownfield:
    focus_sections:
      - 變更背景
      - 現況分析
      - 改善目標
    skip_sections:
      - 市場分析 (已有產品)

  integration:
    focus_sections:
      - 整合目標
      - 第三方服務說明
      - 整合範圍
    skip_sections:
      - 使用者畫像 (不適用)

override_command:
  「使用簡化版 PRD」(跳過非必要章節)
  「包含完整市場分析」(新創產品)
```

---

### 3.2 FRD (Functional Requirements Document)

```yaml
frd_defaults:
  template: FRD_Universal_Template.md
  sections: Core + Scenario-specific
  user_stories: Detailed format
  acceptance_criteria: GIVEN-WHEN-THEN
  scenario_selection: 根據需求類型自動選擇

  standard:
    user_story_format: |
      作為 [角色]
      我想要 [功能]
      以便 [價值]
    ac_format: GIVEN-WHEN-THEN
    priority: Must Have / Should Have / Could Have

  refactoring:
    focus_sections:
      - 重構範圍
      - 重構前後對比
      - 測試策略
    ac_format: Technical Checklist

  performance:
    focus_sections:
      - 效能目標 (量化指標)
      - 基準與目標對比
      - 優化策略
    ac_format: Performance Metrics

  integration:
    focus_sections:
      - API 端點清單
      - 資料 Mapping
      - 錯誤處理
    ac_format: Integration Checklist

override_command:
  「使用簡化版 User Stories」(小型功能)
  「不使用 GIVEN-WHEN-THEN」(使用簡易 Checklist)
```

---

### 3.3 SRD (System Requirements Document)

```yaml
srd_defaults:
  template: SRD_Module_Template.md
  architecture_diagrams: Mermaid (Markdown 格式)
  api_specs: Separate files (mandatory when APIs exist)
  tech_stack: Detailed justification

  diagram_types:
    - System Architecture (必須)
    - Database ERD (必須，如有資料庫)
    - API Sequence Diagram (建議)
    - Component Diagram (可選)

  api_documentation:
    format: OpenAPI 3.0
    separate_files: Yes (每個 API 端點一個檔案)
    include_examples: Yes
    reason: API 是前後端契約，必須詳細

override_command:
  「不生成 API 規格」(無 API 的專案)
  「使用 ASCII Diagrams」(無 Mermaid 支持環境)
```

---

## 4. 確認點模式預設值

### 4.1 三級確認點系統

```yaml
confirmation_points:
  critical (🔴):
    behavior: Always confirm
    cannot_skip: Yes
    examples:
      - 情境選擇
      - 技術棧選型
      - 架構設計方向
      - 上線前檢查
    reason: 影響全局決策，必須人類確認

  recommended (🟡):
    behavior: Confirm in Standard/Detailed Mode
    can_skip_in: Quick Mode
    examples:
      - 文檔章節選擇
      - User Story 優先級
      - 測試案例範圍
    reason: 重要但有合理預設值

  automated (✅):
    behavior: Auto-execute with notification
    always_skip: Yes
    examples:
      - 文檔格式檢查
      - ID 引用驗證
      - 命名規範檢查
    reason: 機械性檢查，無需人類介入

mode_defaults:
  quick_mode:
    critical: Yes
    recommended: No
    automated: Yes
    use_case: 快速迭代，熟悉流程

  standard_mode:
    critical: Yes
    recommended: Yes
    automated: Yes
    use_case: 一般專案，平衡效率與品質

  detailed_mode:
    critical: Yes
    recommended: Yes
    automated: Yes (but show results)
    use_case: 高風險專案，需最大透明度

default_mode: Standard Mode

override_command:
  「使用 Quick Mode」
  「使用 Detailed Mode」
  「所有確認點都需要確認」(最謹慎)
```

---

### 4.2 確認點觸發時機

```yaml
timing_defaults:
  before_major_decision:
    - 情境選擇 (🔴)
    - 技術棧選型 (🔴)
    - 架構設計 (🔴)

  after_document_generation:
    - PRD 完成 (🟡)
    - FRD 完成 (🔴)
    - SRD 完成 (🔴)
    - API 規格完成 (🟡)

  before_implementation:
    - 所有文檔一致性檢查 (🔴)
    - 測試計畫確認 (🟡)

  before_deployment:
    - 上線前檢查清單 (🔴)
    - 回退計畫確認 (🔴)

override_command:
  「跳過文檔確認點」(Quick Mode)
  「增加階段性確認點」(Detailed Mode)
```

---

## 5. Agent 協作預設值

### 5.1 Decision Authority (決策權重)

```yaml
decision_authority:
  technical_decisions:
    primary: sd-architect (Marcus) - 60%
    secondary: dev-senior (Senior) - 30%
    advisory: dev-developer - 10%
    final_override: Human (always)
    examples:
      - 技術棧選擇
      - 架構模式 (Monolithic vs Microservices)
      - 資料庫選擇

  business_decisions:
    primary: pm-po-agent (Victoria) - 70%
    secondary: ba-business-analyst (Beatrice) - 20%
    advisory: sa-analyst (Amanda) - 10%
    final_override: Human (always)
    examples:
      - 功能優先級
      - MVP 範圍
      - 產品方向

  quality_decisions:
    primary: qa-tester (Quincy) - 50%
    secondary: qa-lead - 30%
    advisory: qa-automation (AutoQA) - 20%
    final_override: Human (always)
    examples:
      - 測試範圍
      - 品質標準
      - 驗收標準

conflict_resolution:
  when agents_disagree:
    step_1: Lead Agent 做最終建議
    step_2: 列出各方意見與理由
    step_3: 人類做最終決策
    step_4: 記錄決策與理由

example:
  scenario: 技術棧選擇
  disagreement:
    sd-architect: 「建議 React，生態系完整」(權重 60%)
    dev-senior: 「建議 Vue，學習曲線平緩」(權重 40%)
  resolution:
    final_recommendation: React (based on weighted decision)
    human_override: Available
    reasoning: |
      - React 社群更大
      - 團隊已有 2 人熟悉 React
      - 第三方套件更豐富
      但如果團隊整體偏好 Vue，可覆寫決策
```

---

### 5.2 Collaboration Patterns

```yaml
default_patterns:
  greenfield:
    phase_1_requirements:
      pattern: Lead-Support
      lead: pm-po-agent
      support: [sa-analyst, ba-business-analyst]

    phase_2_design:
      pattern: Peer-Review
      peers: [sa-analyst, sd-architect]

    phase_3_implementation:
      pattern: Sequential-Handoff
      sequence: [sd-architect, dev-developer, qa-tester]

  brownfield:
    phase_1_analysis:
      pattern: Parallel-Convergence
      agents: [sa-analyst, code-analyzer, dev-senior]

    phase_2_change:
      pattern: Iterative-Refinement
      agents: [sd-architect, qa-tester]

  performance:
    pattern: Lead-Support
    lead: performance-engineer
    support: [sd-architect, dev-senior, qa-automation]

  integration:
    pattern: Lead-Support
    lead: integration-specialist
    support: [sd-architect, qa-tester]
```

---

## 6. 預設值覆寫機制

### 6.1 全局覆寫

```yaml
global_override:
  command_format: |
    「AISDLC [scenario-code] [project-brief] --mode=[mode] --tech-stack=[stack]」

  examples:
    - 「AISDLC greenfield-web 電商網站 --mode=quick --tech-stack=vue」
    - 「AISDLC brownfield --confirmations=all」
    - 「AISDLC integration Stripe --no-fallback」

  supported_flags:
    --mode: quick / standard / detailed
    --tech-stack: react / vue / angular / ...
    --confirmations: minimal / balanced / all
    --parallel: yes / no
    --docs-level: minimal / medium / detailed
```

---

### 6.2 互動式調整

```yaml
interactive_override:
  during_initialization:
    AI: 「預設使用 React，是否要改用其他框架？」
    User: 「改用 Vue」
    AI: 「✅ 已更新為 Vue.js 3.x」

  during_execution:
    AI: 「預設 Standard Mode (5 個確認點)，是否調整？」
    User: 「改用 Quick Mode」
    AI: 「✅ 已切換為 Quick Mode (3 個確認點)」
```

---

### 6.3 專案層級配置

```yaml
project_config_file:
  location: project/.aisdlc/config.yaml
  auto_load: Yes
  content_example: |
    scenario: greenfield-web
    mode: standard
    tech_stack:
      frontend: vue
      backend: python-fastapi
      database: postgresql
    confirmation_points:
      critical: true
      recommended: false
      automated: true
    parallel_execution: true

  usage:
    - 建立 .aisdlc/config.yaml
    - AI 自動讀取並應用配置
    - 可隨時手動覆寫
```

---

## 7. 預設值效益分析

### 7.1 決策時間減少

```yaml
without_smart_defaults:
  decisions_required: 25-30 個
  average_time_per_decision: 2-5 分鐘
  total_decision_time: 50-150 分鐘

with_smart_defaults:
  decisions_required: 5-8 個 (關鍵決策)
  average_time_per_decision: 2-5 分鐘
  total_decision_time: 10-40 分鐘

time_saved: 60-87%
```

---

### 7.2 新手友善度

```yaml
novice_users:
  without_defaults:
    learning_curve: Steep (需理解所有選項)
    time_to_productive: 2-4 小時
    error_rate: 30-40% (選擇不適合的配置)

  with_defaults:
    learning_curve: Gentle (使用預設值即可)
    time_to_productive: 15-30 分鐘
    error_rate: 5-10% (預設值基於最佳實踐)

improvement: 4-8x faster onboarding
```

---

### 7.3 專家使用者

```yaml
expert_users:
  benefits:
    - 快速啟動 (使用預設值)
    - 完全客製化能力 (可覆寫所有預設值)
    - 可建立專案配置檔 (團隊統一標準)

  workflow:
    quick_projects: 使用預設值，< 3 分鐘啟動
    custom_projects: 覆寫預設值，5-10 分鐘配置
    team_projects: 使用 .aisdlc/config.yaml，一鍵啟動
```

---

## 8. 最佳實踐

### 何時使用預設值

**✅ 建議使用預設值**:
- 標準類型專案
- 團隊技能與預設技術棧匹配
- 時程緊迫，需要快速啟動
- 新手使用者

**🟡 考慮客製化**:
- 企業既有技術棧不同
- 特殊需求（如高併發、離線支援）
- 監管要求（如金融、醫療）

**❌ 必須客製化**:
- 創新/研究型專案
- 非主流技術棧
- 高度定製化需求

---

## 📚 相關文檔

- [AISDLC_INIT.md](AISDLC_INIT.md) - 框架初始化
- [QUICK_START_TEMPLATES.md](QUICK_START_TEMPLATES.md) - 快速啟動範本
- [ERROR_PREVENTION_SYSTEM.md](ERROR_PREVENTION_SYSTEM.md) - 錯誤預防系統
- [PHASE4_VERIFICATION_REPORT.md](PHASE4_VERIFICATION_REPORT.md) - Phase 4 驗證報告

---

**文檔版本**: v1.0
**最後更新**: 2025-11-03
**維護者**: AISDLC Framework Team
**Phase 4 子任務**: 4.1 Smart Defaults Implementation
