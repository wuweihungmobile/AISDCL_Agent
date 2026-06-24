# AISDLC-SDD v0.01 快速啟動範本庫
# Quick Start Templates Library

**框架版本**: v0.01
**建立日期**: 2025-11-03（更新至 v0.01）
**最後更新**: 2026-06-06
**用途**: 提供預配置的專案範本，實現 < 3 分鐘快速啟動

---

## 📚 範本總覽

| 範本代碼 | 範本名稱 | 情境 | 技術棧 | 預估週期 | 適用規模 |
|---------|---------|------|--------|---------|---------|
| `ecommerce-web` | 電商網站 | Greenfield Web | React + Node.js | 2-3 月 | 中大型 |
| `mobile-app` | 移動應用 | Greenfield Mobile | React Native | 1.5-2.5 月 | 中型 |
| `api-service` | API 服務 | Greenfield Backend | Node.js/Python | 1-2 月 | 中型 |
| `legacy-upgrade` | 舊系統升級 | Brownfield | (取決於原系統) | 2-4 月 | 大型 |
| `api-integration` | API 整合 | Integration | (取決於主系統) | 2-4 週 | 小中型 |
| `performance-tuning` | 效能優化 | Performance | (取決於系統) | 1-3 週 | 小中型 |

---

## 1. ecommerce-web - 電商網站標準範本

### 基本資訊

```yaml
template_id: ecommerce-web
name: 電商網站標準流程
scenario: Greenfield Web
category: Full-stack Web Application
estimated_duration: 2-3 個月
team_size: 4-8 人
```

### 預設技術棧

```yaml
frontend:
  framework: React 18.x
  language: TypeScript 5.x
  state_management: Redux Toolkit / Zustand
  ui_library: Material-UI / Ant Design
  styling: Tailwind CSS / CSS Modules

backend:
  runtime: Node.js 20.x
  framework: Express.js / Nest.js
  language: TypeScript 5.x
  authentication: JWT + Refresh Token
  api_style: RESTful API

database:
  primary: PostgreSQL 15.x
  cache: Redis 7.x
  search: Elasticsearch (optional)

infrastructure:
  hosting: AWS / GCP / Azure
  cdn: CloudFront / CloudFlare
  ci_cd: GitHub Actions / GitLab CI
  monitoring: Datadog / New Relic
```

### 核心功能模組

```yaml
modules:
  1. 使用者系統:
    - 註冊登入 (Email + OAuth)
    - 個人資料管理
    - 密碼重設
    - 權限管理 (顧客/管理員)

  2. 產品目錄:
    - 產品列表與搜尋
    - 產品分類導航
    - 產品詳細資訊
    - 產品評論與評分

  3. 購物車:
    - 加入/移除商品
    - 數量調整
    - 購物車持久化
    - 折扣碼應用

  4. 結帳流程:
    - 訂單資訊確認
    - 配送地址管理
    - 付款方式選擇
    - 訂單確認與追蹤

  5. 後台管理:
    - 產品管理 (CRUD)
    - 訂單管理
    - 使用者管理
    - 報表分析
```

### 載入的 Agents

```yaml
primary_agents:
  - pm-po-agent (Victoria): 產品規劃與商業邏輯
  - sa-analyst (Amanda): 需求分析與功能設計

supporting_agents:
  - sd-architect (Marcus): 技術架構設計
  - dev-developer: 開發實施評估
  - qa-tester (Quincy): 測試策略與驗收標準
```

### 推薦文檔

```yaml
documents:
  - PRD_Universal_Template.md (Greenfield)
  - FRD_Universal_Template.md (Standard)
  - SRD_Module_Template.md (每個模組一份)
  - API_Specification_Template.md (每個 API 端點一份)
  - AT_Module_Template.md (按模組測試)
```

### 使用範例

```
使用者：「AISDLC 使用範本 ecommerce-web」

AI 回應：
✅ 已載入範本: ecommerce-web (電商網站標準流程)

📋 範本配置:
   情境: Greenfield Web
   技術棧: React + TypeScript + Node.js + PostgreSQL
   核心模組: 5 個 (使用者/產品/購物車/結帳/後台)
   預估週期: 2-3 個月

🤖 已載入 Agents:
   ✅ pm-po-agent (Victoria) - 產品經理
   ✅ sa-analyst (Amanda) - 系統分析師
   ✅ sd-architect (Marcus) - 系統設計師
   ✅ dev-developer - 開發工程師
   ✅ qa-tester (Quincy) - 測試工程師

📝 請提供專案特定資訊:
   1. 專案名稱: [必填，例: "MyShop 線上商城"]
   2. 目標市場: [可選，例: "台灣 B2C 市場"]
   3. 特殊需求: [可選，例: "支援多語系(中英日)"]
   4. 團隊規模: [可選，預設 4-8 人]

或直接輸入 "使用預設配置" 立即開始...
```

---

## 2. mobile-app - 移動應用標準範本

### 基本資訊

```yaml
template_id: mobile-app
name: 移動 App 標準流程
scenario: Greenfield Mobile
category: Mobile Application
estimated_duration: 1.5-2.5 個月
team_size: 3-6 人
```

### 預設技術棧

```yaml
cross_platform:
  framework: React Native 0.72+
  language: TypeScript 5.x
  navigation: React Navigation
  state_management: Redux Toolkit / MobX
  ui_library: React Native Paper / NativeBase

ios_native:
  language: Swift 5.x
  ui_framework: SwiftUI
  architecture: MVVM / Clean Architecture
  dependency_manager: CocoaPods / SPM

android_native:
  language: Kotlin 1.9+
  ui_framework: Jetpack Compose
  architecture: MVVM / Clean Architecture
  dependency_manager: Gradle

backend:
  api_type: RESTful / GraphQL
  authentication: JWT + Biometric
  push_notification: Firebase Cloud Messaging

services:
  analytics: Firebase Analytics / Mixpanel
  crash_reporting: Crashlytics / Sentry
  ab_testing: Firebase Remote Config
```

### 核心功能模組

```yaml
modules:
  1. 使用者認證:
    - Email/手機號註冊登入
    - 社交登入 (Google/Apple/Facebook)
    - 生物辨識 (Face ID / Fingerprint)
    - 推播通知權限

  2. 主要功能:
    - 首頁 Dashboard
    - 核心業務流程 (依專案而定)
    - 搜尋與過濾
    - 個人化推薦

  3. 使用者中心:
    - 個人資料編輯
    - 設定與偏好
    - 通知中心
    - 幫助與回饋

  4. 整合服務:
    - API 整合
    - 推播通知
    - 深度連結 (Deep Link)
    - 應用內更新
```

### 載入的 Agents

```yaml
primary_agents:
  - pm-po-agent (Victoria): 產品規劃
  - sa-analyst (Amanda): 功能分析

supporting_agents:
  - sd-architect (Marcus): 架構設計
  - dev-developer: 開發實施
  - qa-tester (Quincy): 測試策略
  - qa-automation (AutoQA): 自動化測試 (E2E)
```

---

## 3. api-service - 後端 API 服務範本

### 基本資訊

```yaml
template_id: api-service
name: 後端 API 服務標準流程
scenario: Greenfield Backend
category: Backend API Service
estimated_duration: 1-2 個月
team_size: 2-5 人
```

### 預設技術棧

```yaml
option_1_nodejs:
  runtime: Node.js 20.x
  framework: Express.js / Nest.js / Fastify
  language: TypeScript 5.x
  orm: Prisma / TypeORM

option_2_python:
  runtime: Python 3.11+
  framework: FastAPI / Django REST Framework
  async: asyncio / aiohttp
  orm: SQLAlchemy / Django ORM

option_3_java:
  runtime: Java 17+ / Kotlin 1.9+
  framework: Spring Boot 3.x
  build_tool: Gradle / Maven
  orm: Hibernate / JPA

common_components:
  database: PostgreSQL / MySQL / MongoDB
  cache: Redis
  message_queue: RabbitMQ / Kafka (optional)
  authentication: JWT / OAuth 2.0
  api_documentation: OpenAPI 3.1 / Swagger
  logging: Winston / Logback / structlog
  monitoring: Prometheus + Grafana
```

### 核心功能模組

```yaml
modules:
  1. 認證授權:
    - JWT Token 認證
    - Refresh Token 機制
    - 角色權限管理 (RBAC)
    - API Key 管理

  2. 核心業務 API:
    - RESTful CRUD 操作
    - 複雜業務邏輯處理
    - 資料驗證與轉換
    - 錯誤處理機制

  3. 資料存取層:
    - Database ORM
    - Transaction 管理
    - Query 優化
    - Connection Pooling

  4. 整合服務:
    - 第三方 API 整合
    - Webhook 處理
    - 背景任務 (Job Queue)
    - 檔案上傳/下載

  5. 運維支援:
    - Health Check API
    - Metrics 輸出
    - 結構化日誌
    - API 文檔自動生成
```

### 載入的 Agents

```yaml
primary_agents:
  - sd-architect (Marcus): 技術架構與 API 設計

supporting_agents:
  - sa-analyst (Amanda): 需求分析
  - dev-developer: 實施指導
  - qa-automation (AutoQA): API 自動化測試
  - devops-engineer: 部署與監控
```

---

## 4. legacy-upgrade - 舊系統升級範本

### 基本資訊

```yaml
template_id: legacy-upgrade
name: 舊系統升級標準流程
scenario: Brownfield
category: Legacy System Modernization
estimated_duration: 2-4 個月
team_size: 4-10 人
```

### 評估階段配置

```yaml
assessment_phase:
  code_analysis:
    - 技術債統計
    - 依賴關係分析
    - 安全漏洞掃描
    - 效能瓶頸識別

  business_analysis:
    - 現有功能盤點
    - 使用者流程分析
    - 痛點識別
    - 優先級排序

  risk_analysis:
    - 技術風險評估
    - 業務影響分析
    - 回退策略規劃
    - 資源需求評估
```

### 升級策略選擇

```yaml
strategy_options:
  1. Strangler Fig Pattern (絞殺者模式):
    - 漸進式替換舊系統
    - 新舊系統並存
    - 風險: 🟢 低
    - 週期: 3-6 個月
    - 適用: 大型系統

  2. Big Bang Replacement (大爆炸替換):
    - 一次性完全替換
    - 切換時間短
    - 風險: 🔴 高
    - 週期: 1-2 個月
    - 適用: 小型系統

  3. Parallel Run (並行運行):
    - 新舊系統同時運行
    - 對比驗證結果
    - 風險: 🟡 中
    - 週期: 2-4 個月
    - 適用: 關鍵業務系統

  4. Incremental Modernization (增量現代化):
    - 分模組逐步升級
    - 保持系統可用
    - 風險: 🟢 低
    - 週期: 4-8 個月
    - 適用: 複雜業務系統
```

### 載入的 Agents

```yaml
primary_agents:
  - sa-analyst (Amanda): 現況分析與需求整理
  - dev-senior (Senior): 資深開發者，架構評估

supporting_agents:
  - code-analyzer (CodeX): 代碼分析與技術債評估
  - sd-architect (Marcus): 新架構設計
  - qa-tester (Quincy): 測試策略與回歸測試
  - devops-engineer: 部署策略與回退計畫
```

---

## 5. api-integration - API 整合專案範本

### 基本資訊

```yaml
template_id: api-integration
name: 第三方 API 整合標準流程
scenario: Integration
category: Third-party Integration
estimated_duration: 2-4 週
team_size: 2-4 人
```

### 常見整合類型

```yaml
integration_types:
  payment_gateway:
    - Stripe
    - PayPal
    - 綠界 ECPay
    - 藍新 NewebPay
    complexity: 🟡 中等
    duration: 2-3 週

  social_login:
    - Google OAuth 2.0
    - Facebook Login
    - Apple Sign In
    - LINE Login
    complexity: 🟢 簡單
    duration: 1-2 週

  crm_system:
    - Salesforce
    - HubSpot
    - Zoho CRM
    complexity: 🔴 複雜
    duration: 3-4 週

  messaging:
    - SendGrid (Email)
    - Twilio (SMS)
    - LINE Messaging API
    complexity: 🟢 簡單
    duration: 1 週

  cloud_storage:
    - AWS S3
    - Google Cloud Storage
    - Azure Blob Storage
    complexity: 🟢 簡單
    duration: 1 週

  map_service:
    - Google Maps API
    - Mapbox
    complexity: 🟢 簡單
    duration: 1-2 週
```

### 核心實施步驟

```yaml
implementation_phases:
  1. API 研究 (30 分鐘):
    - 閱讀官方文檔
    - 識別認證方式
    - 確認 rate limit
    - 確認定價方案

  2. 認證設計 (20 分鐘):
    - OAuth 2.0 流程設計
    - API Key 管理
    - Token 更新機制
    - 安全性檢查

  3. 資料轉換 (30 分鐘):
    - Request mapping
    - Response parsing
    - 錯誤碼轉換
    - 資料驗證

  4. 錯誤處理 (20 分鐘):
    - Retry 策略
    - Fallback 機制
    - 錯誤通知
    - 日誌記錄

  5. 測試計畫 (30 分鐘):
    - Sandbox 測試
    - Edge case 測試
    - 效能測試
    - 上線檢查清單
```

### 載入的 Agents

```yaml
primary_agents:
  - integration-specialist (IntegX): 整合專家

supporting_agents:
  - sd-architect (Marcus): 架構設計
  - qa-tester (Quincy): 測試策略
  - security-engineer (SecEng): 安全審查 (如涉及敏感資料)
```

### 快速參考

```yaml
quick_reference:
  - scenarios/integration/SOP_QuickRef.md (5 分鐘快速掌握)
  - scenarios/integration/SOP.md (完整流程)
  - scenarios/integration/SOP_DeepDive.md (進階技術細節)
```

---

## 6. performance-tuning - 效能優化專案範本

### 基本資訊

```yaml
template_id: performance-tuning
name: 效能優化標準流程
scenario: Performance
category: Performance Optimization
estimated_duration: 1-3 週
team_size: 2-5 人
```

### 效能問題分類

```yaml
performance_categories:
  frontend_performance:
    issues:
      - 首次載入時間過長 (TTFB/FCP/LCP)
      - JavaScript bundle 過大
      - 圖片未優化
      - 過多 API 請求
    tools:
      - Lighthouse
      - Chrome DevTools
      - WebPageTest
      - Bundle Analyzer
    typical_duration: 1-2 週

  backend_performance:
    issues:
      - API 回應時間慢 (> 200ms)
      - 資料庫查詢慢 (N+1 query)
      - 記憶體洩漏
      - CPU 使用率高
    tools:
      - Application APM (Datadog/New Relic)
      - Database Query Analyzer
      - Profiling Tools (Node.js Profiler/py-spy)
    typical_duration: 1-2 週

  database_performance:
    issues:
      - 查詢過慢 (> 100ms)
      - 缺少索引
      - 資料表設計不佳
      - Connection pool 不足
    tools:
      - EXPLAIN ANALYZE
      - Slow Query Log
      - Database Profiler
    typical_duration: 1 週

  infrastructure_performance:
    issues:
      - 網路延遲高
      - CDN 未配置
      - 伺服器資源不足
      - 負載均衡問題
    tools:
      - Network Monitoring
      - Server Metrics (CPU/RAM/Disk)
      - Load Testing (k6/JMeter)
    typical_duration: 1-2 週
```

### 優化流程

```yaml
optimization_workflow:
  phase_1_baseline:
    - 建立效能基準
    - 設定優化目標
    - 識別瓶頸
    duration: 1-2 天

  phase_2_analysis:
    - Profiling 分析
    - 根因分析
    - 優化策略制定
    duration: 2-3 天

  phase_3_implementation:
    - 實施優化
    - A/B 測試
    - 效能驗證
    duration: 3-5 天

  phase_4_validation:
    - 上線前測試
    - 效能回歸測試
    - 監控設定
    duration: 1-2 天
```

### 載入的 Agents

```yaml
primary_agents:
  - performance-engineer (Perf): 效能工程師

supporting_agents:
  - sd-architect (Marcus): 架構優化建議
  - dev-senior (Senior): 代碼優化實施
  - qa-automation (AutoQA): 效能測試自動化
  - devops-engineer: 基礎設施優化
```

### 快速參考

```yaml
quick_reference:
  - scenarios/performance/SOP_QuickRef.md (5 分鐘快速掌握)
  - scenarios/performance/SOP.md (完整流程)
```

---

## 🚀 範本使用指南

### 步驟 1: 選擇範本

根據您的專案情況，選擇最合適的範本：

```
新專案開發 → ecommerce-web / mobile-app / api-service
既有系統 → legacy-upgrade
第三方整合 → api-integration
效能問題 → performance-tuning
```

### 步驟 2: 使用範本啟動

```
「AISDLC 使用範本 [template-name]」

範例:
- 「AISDLC 使用範本 ecommerce-web」
- 「AISDLC 使用範本 api-integration」
```

### 步驟 3: 客製化配置（可選）

AI 會提示您填寫專案特定資訊，或您可以：

```
「使用預設配置」→ 使用範本預設值快速開始
「客製化配置」→ 修改技術棧/模組/時程等
```

### 步驟 4: 開始執行

AI 會自動：
1. ✅ 載入對應 Agents
2. ✅ 應用 Smart Defaults
3. ✅ 推薦文檔模板
4. ✅ 提供 QuickRef (如有)
5. ✅ 進入執行階段

---

## 🔧 範本客製化

### 修改技術棧

```
「我想改用 Vue.js 而不是 React」
「後端改用 Python FastAPI」
「資料庫改用 MongoDB」
```

AI 會：
- ✅ 更新技術棧配置
- ✅ 調整文檔模板建議
- ✅ 保留其他範本設定

### 調整模組範圍

```
「暫時不需要後台管理模組」
「增加會員等級與積分系統」
「需要支援多租戶架構」
```

AI 會：
- ✅ 調整模組清單
- ✅ 更新預估週期
- ✅ 調整 Agent 配置

### 改變執行模式

```
「使用 Quick Mode（減少確認點）」
「使用 Detailed Mode（完整確認點）」
「啟用 Tutorial Mode（學習模式）」
```

---

## 📊 範本效益

### 啟動時間對比

```yaml
without_template:
  情境選擇: 5 分鐘
  技術棧討論: 15 分鐘
  架構設計: 20 分鐘
  Agent 載入: 3 分鐘
  文檔設定: 7 分鐘
  total: 50 分鐘

with_template:
  範本選擇: 30 秒
  客製化調整: 1-2 分鐘 (可選)
  自動載入: 30 秒
  total: < 3 分鐘

time_saved: 94% (50 分鐘 → 3 分鐘)
```

### 決策減負

```yaml
without_template:
  需要決策的項目: 25-30 個
  - 情境類型
  - 每個技術棧選擇 (Frontend/Backend/Database/...)
  - Agent 選擇
  - 文檔模板選擇
  - 確認點模式
  - ...

with_template:
  需要決策的項目: 3-5 個
  - 範本選擇
  - 專案名稱
  - 特殊需求 (可選)

decision_reduction: 85%
```

---

## 🎯 最佳實踐

### 何時使用範本

**✅ 建議使用**:
- 標準類型專案（電商、社群、內容管理等）
- 團隊經驗豐富，熟悉範本技術棧
- 時程緊迫，需要快速啟動
- 新手使用者，需要引導

**🟡 考慮客製化**:
- 特殊業務需求
- 技術棧與範本不同
- 企業既有架構限制

**❌ 不建議使用**:
- 高度創新的專案（範本無法涵蓋）
- 完全非標準化的技術棧
- 需要深度定製的流程

### 範本選擇技巧

1. **明確專案類型**: 新專案 vs 既有系統
2. **識別核心目標**: 開發 vs 優化 vs 整合
3. **評估團隊技能**: 選擇熟悉的技術棧範本
4. **考慮專案規模**: 小型專案優先簡單範本

### 範本使用後續

範本只是快速啟動工具，實際執行時：
- ✅ 仍需遵循 AISDLC 流程和確認點
- ✅ 文檔產出標準不變
- ✅ Agent 協作規則適用
- ✅ 可隨時調整配置

---

## 📚 相關文檔

- [AISDLC_SDD_INIT.md](../../../AISDLC_SDD_INIT.md) - 框架初始化（含按需載入啟動）
- [QUICK_START_GUIDE.md](QUICK_START_GUIDE.md) - 快速上手指南
- [TUTORIAL_MODE.md](TUTORIAL_MODE.md) - 互動式教學模式
- [scenarios/*/SOP_QuickRef.md](../../../scenarios/) - 各情境快速參考

---

**文檔版本**: v0.01
**最後更新**: 2026-06-06
**維護者**: AISDLC-SDD Framework Team
