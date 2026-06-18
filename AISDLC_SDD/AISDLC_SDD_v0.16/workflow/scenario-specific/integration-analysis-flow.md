# Integration Analysis Flow
# 系統整合分析流程

## Workflow 名稱
**integration-analysis-flow** - 系統整合規劃與實作流程

## 描述
第三方服務整合的完整流程，包含 API 研究、整合設計、認證機制、資料轉換、錯誤處理、測試和監控。

## 適用場景
- **使用時機**：第三方 API 對接、系統間資料交換、Legacy 系統整合
- **適用專案**：支付整合、物流對接、CRM 整合、任何第三方服務整合
- **執行頻率**：按需執行（每次新整合）

## 觸發條件
- 需要整合第三方服務
- API 文檔已取得
- 整合需求明確

---

# 角色與責任

## 主要負責人
**Agent 角色**：Integration-Specialist + SD
**責任**：API 研究、整合架構設計、跨系統資料同步策略

## 參與者
- **Dev-Developer**：整合實作指導、認證與授權實作
- **QA**：整合測試設計
- **DevOps-Engineer**：監控告警設計、部署策略

## 選擇性參與者
- **Security-Engineer**：涉及支付、OAuth、敏感資料整合時
- **Performance-Engineer**：高頻 API 呼叫或大量資料同步時
- **SD-Mobile-Architect**：行動端整合架構設計（Android/iOS/macOS）
- **QA-Mobile-Tester**：行動端整合測試（掃碼、離線同步、推播）

---


---

## SDD SCG 閘門整合（v0.01）

> 整合分析使用 Consumer Contract-First 模式，Contract 必須在開發前凍結。

| 步驟 | 對應 SCG 閘門 | 強制產出 |
|------|-------------|---------|
| 整合需求分析 | **SCG-1 準備** | 整合架構設計 + ADR |
| Contract 設計 | **🔴 SCG-3 凍結** | Consumer Contract（OpenAPI 3.1） |
| 整合測試設計 | SCG-3 通過後 | Contract Test Cases |
| 整合驗證 | **SCG-5 準備** | Consumer Contract 全通過 |

**🔷 整合閘門**：SCG-1（整合設計）→ SCG-3（Contract 凍結）→ SCG-5（整合驗證）
**📌 SDD CI/CD 規格**：參考 `cicd/SDD_INTEGRATION_CICD.md`


# 執行步驟

## 步驟 1：API 研究與理解 (40-60 分鐘)
**執行者**：Integration-Specialist

**作業內容**：
1. API 文檔分析
2. 認證機制研究
3. 端點清單整理
4. 限流政策分析
5. 錯誤處理機制研究
6. 功能可行性評估

**確認點** 🔴：API 研究確認
- 審查 API 能力矩陣
- 確認限制可接受
- 確認風險可控

**產出**：API 研究報告、功能對應矩陣、限制清單

## 步驟 2：整合架構設計 (1-1.5 小時)
**執行者**：SD + Integration-Specialist

**作業內容**：
1. 選擇整合模式（直接呼叫/非同步/API Gateway）
2. 設計資料流
3. 設計錯誤處理策略
4. 設計重試機制
5. 設計降級方案
6. 設計冪等性機制

**確認點** 🔴：架構設計確認
- 審查整合架構圖
- 確認模式選擇
- 確認錯誤處理策略

**產出**：整合架構設計、資料流程圖、錯誤處理策略

## 步驟 3：認證與授權設計 (30-40 分鐘)
**執行者**：Integration-Specialist + Dev-Senior

**作業內容**：
1. 設計認證方案（API Key/OAuth/JWT/HMAC）
2. Token 管理策略
3. Webhook 認證設計
4. 安全性檢查

**確認點** 🔴：認證方案確認

**產出**：認證實作指南、Token 管理策略、Webhook 安全設計

## 步驟 4：資料轉換與映射 (40-60 分鐘)
**執行者**：Integration-Specialist

**作業內容**：
1. 資料映射規格設計
2. Request/Response 轉換
3. 資料驗證設計
4. 特殊資料處理（日期/金額/檔案）

**確認點** 🔴：資料轉換確認

**產出**：資料映射規格、轉換函式庫、驗證規則

## 步驟 5：測試策略設計 (40-60 分鐘)
**執行者**：QA + Integration-Specialist

**作業內容**：
1. 單元測試設計
2. 整合測試（Mock）設計
3. Contract Testing
4. Sandbox 測試
5. 錯誤場景測試

**確認點** 🔴：測試計畫確認

**產出**：整合測試計畫、測試案例、測試腳本

## 步驟 6：跨系統整合設計 (30-60 分鐘) 🆕
**執行者**：Integration-Specialist + SD

**作業內容**（當涉及多系統整合時）：
1. 跨語言 API 整合設計（如 Python API ↔ Spring Boot API）
2. 雙資料庫同步策略（CDC / 雙寫 / ETL / 事件驅動）
3. 統一認證方案設計（SSO / JWT 共享 / API Gateway 代理）
4. 前端整合策略（Micro-Frontend / API 橋接 / 共用元件庫）
5. 跨系統錯誤傳播與處理

**確認點** 🔴：跨系統整合設計確認

**產出**：跨系統整合架構圖、資料同步策略、統一認證方案

## 步驟 7：監控與告警 (30 分鐘)
**執行者**：DevOps-Engineer + Integration-Specialist

**作業內容**：
1. 設計監控指標
2. 設定告警規則
3. 設計日誌規範
4. 設定分散式追蹤

**產出**：監控方案、告警配置、日誌規範

---

# 輸出與交付

## 主要交付物
- API 研究報告
- 整合架構設計
- 認證實作指南
- 資料映射規格
- 測試計畫
- 監控方案

## 交付標準
- API 理解正確
- 整合架構合理
- 測試覆蓋完整
- 監控告警完善

---

## 📚 參考資源

- [Integration SOP 完整版](../../scenarios/integration/SOP.md)
- [Integration QuickRef 快速參考](../../scenarios/integration/SOP_QuickRef.md)
- [Integration DeepDive 深度指南](../../scenarios/integration/SOP_DeepDive.md)
- [Integration 快速啟動指令集](../../prompts/scenario-prompts/integration-prompts.md)
- [AISDLC_INIT.md](../../AISDLC_SDD_INIT.md)

### 相關 Agents
- [integration-specialist-zh.yaml](../../agent/specialized/integration-specialist-zh.yaml) - Integration Specialist（主導）
- [sd-architect-zh.yaml](../../agent/core/05.sd-architect-zh.yaml) - Marcus（整合架構設計）
- [qa-tester-zh.yaml](../../agent/core/07.qa-tester-zh.yaml) - Quincy（整合測試規劃）
- [dev-developer-zh.yaml](../../agent/core/06.dev-developer-zh.yaml) - David（認證與授權實作）
- [devops-engineer-zh.yaml](../../agent/specialized/devops-engineer-zh.yaml) - DevOps Engineer（監控與告警）
- [security-engineer-zh.yaml](../../agent/specialized/security-engineer-zh.yaml) - Security Engineer（OAuth/支付/敏感資料，選用）
- [performance-engineer-zh.yaml](../../agent/specialized/performance-engineer-zh.yaml) - Performance Engineer（高頻 API/大量同步，選用）
- [sd-mobile-architect-zh.yaml](../../agent/specialized/sd-mobile-architect-zh.yaml) - Mobile Architect（行動端整合架構，選用）
- [qa-mobile-tester-zh.yaml](../../agent/specialized/qa-mobile-tester-zh.yaml) - Mobile QA（行動端整合測試，選用）

### 相關 Skills
- `/integration-api-client` - API 客戶端建立（錯誤處理、重試、型別安全）
- `/integration-oauth` - OAuth 2.0 認證整合
- `/integration-stripe` - Stripe 支付整合
- `/integration-webhook` - Webhook 處理系統
- `/integration-database` - 資料庫整合（PostgreSQL、連線池、讀寫分離）
- `/integration-redis` - Redis 快取整合
- `/documentation-api` - API 文檔生成（OpenAPI/Swagger）
- `/security-audit` - 安全審查（OWASP Top 10）
- `/qa-testing` - 測試策略與測試計畫
- `/devops-monitoring` - 監控告警系統（Prometheus/Grafana）
- `/mobile-development` - 行動端整合開發（涉及 Android/iOS/macOS 時）

---

**版本**：v0.01
**維護者**：AISDLC Framework Team
**最後更新**：2026-04-17
