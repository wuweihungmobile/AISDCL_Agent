# Integration - Quick Reference (5分鐘版)
# 第三方系統整合 - 快速參考卡

**情境**: Third-Party System Integration
**版本**: v0.01
**適用對象**: 已熟悉完整SOP，需要快速提醒的開發者

---

## ⚡ 核心流程 (7步驟)

```
┌────────────────────────────────────────────────────────────────────┐
│  邊界識別 → API研究 → 架構設計 → 認證設計 → 資料轉換 → 錯誤處理 → 測試計畫  │
│   (20m)     (30m)     (30m)      (20m)      (30m)       (20m)      (30m) │
└────────────────────────────────────────────────────────────────────┘
```
> 🆕 **多系統整合新增**：「邊界識別」(System of Record) + 「架構設計」（異質技術棧/規範模型/SSO/CDC）

### Step 0: 系統邊界識別 (20分鐘) ✅ 🆕
**產出**: `System_of_Record_Map.md`

**關鍵任務**:
- [ ] 識別各資料實體的 System of Record（主系統）
- [ ] 定義跨系統資料衝突仲裁規則
- [ ] 確認資料一致性等級（強一致/最終一致）
- [ ] 識別異質技術棧（不同語言/框架）

**常見陷阱**: ⚠️ 雙系統都認為自己是 SoR，導致資料衝突無法解決

---

### Step 1: API 研究 (30分鐘) ✅
**產出**: API_Research_Report.md

**關鍵任務**:
- [ ] 閱讀第三方 API 文檔（或逆向工程）
- [ ] 識別所需 Endpoints (3-5個)
- [ ] 確認認證方式 (OAuth/API Key/JWT)
- [ ] 檢查 Rate Limiting (多少 req/min)
- [ ] 測試環境存取驗證

**常見陷阱**: ⚠️ 未確認 API 版本，使用已棄用的端點

---

### Step 1.5: 整合架構設計 (30分鐘) ✅ 🆕（多系統複雜整合必做）
**產出**: `Integration_Architecture.md`、`Canonical_Data_Model.md`

**關鍵任務**:
- [ ] 選擇整合模式（API Gateway / BFF / Event-Driven）
- [ ] 設計規範資料模型 (Canonical Model)
- [ ] 規劃資料同步策略（Outbox Pattern / CDC / Webhook）
- [ ] 跨語言 API 客戶端生成（openapi-generator）

**快速決策**:
```
異質技術棧？ (Python + Java + TS)
└─ 是 → API Gateway（統一入口）或 BFF（各前端獨立）

資料需要強一致？ (訂單/庫存/金融)
└─ 是 → Outbox Pattern（Transaction 內發布事件）

資料量大？ (>10萬筆/日)
└─ 是 → CDC (Debezium + Kafka)
```

---

### Step 2: 認證設計 (20分鐘) ✅
**產出**: Auth_Design.md、Cross_System_Auth_Design.md

**關鍵任務**:
- [ ] 設計 Token 取得與更新流程
- [ ] 規劃 Token 儲存方式 (環境變數/資料庫/快取)
- [ ] 處理認證失敗情境
- [ ] 設計 Token 過期自動更新機制
- [ ] **多系統整合**：設計 JWT Federation 或 OAuth2/OIDC 統一認證（含 Python + Java 共用 Public Key 驗證）

**快速決策樹**:
```
第三方認證方式？
├─ OAuth 2.0 → 實作授權碼流程 + Refresh Token
├─ API Key → 環境變數儲存 + Header 傳遞
└─ JWT → 取得 Token + 過期自動更新

異質技術棧統一認證？
├─ 輕量 → JWT Federation（共享 RSA 公鑰）
└─ 企業級 → Keycloak / Auth0 OIDC
```

---

### Step 3: 資料轉換設計 (30分鐘) ✅
**產出**: Data_Mapping.md

**關鍵任務**:
- [ ] 建立欄位映射表 (我方 ↔ 第三方)
- [ ] 定義資料類型轉換規則
- [ ] 設計狀態碼映射
- [ ] 處理資料驗證邏輯
- [ ] 確認必填欄位與預設值

**欄位映射範例**:
| 我方欄位 | 第三方欄位 | 轉換邏輯 |
|---------|----------|---------|
| user_id | userId | 直接映射 |
| created_at | createdDate | ISO8601 → Unix |
| status | userStatus | active→1, inactive→0 |

---

### Step 4: 錯誤處理策略 (20分鐘) ✅
**產出**: Error_Handling_Strategy.md

**關鍵任務**:
- [ ] 定義錯誤分類 (4xx用戶錯誤 vs 5xx系統錯誤)
- [ ] 設計重試機制 (指數退避)
- [ ] 規劃失敗通知機制
- [ ] 設計資料補償方案

**快速配置**:
```yaml
重試策略:
  最大重試次數: 3
  初始延遲: 1秒
  最大延遲: 60秒
  重試 HTTP Status: [500, 502, 503, 504, 429]

通知:
  連續失敗 > 3次: 發送 Slack 通知
  成功率 < 95%: 發送 Email 告警
```

---

### Step 5: 測試計畫 (30分鐘) ✅
**產出**: Integration_Test_Plan.md

**關鍵任務**:
- [ ] 規劃單元測試 (Mock 第三方API)
- [ ] 規劃整合測試 (測試環境驗證)
- [ ] 準備測試資料 (正常/邊界/異常)
- [ ] 設計效能測試場景
- [ ] 建立監控指標

**最小測試集**:
| 測試場景 | 優先級 |
|---------|-------|
| 正常請求/回應 | P0 |
| 認證失敗處理 | P0 |
| 網路逾時重試 | P0 |
| 資料驗證失敗 | P1 |
| Rate Limit 處理 | P1 |

---

## 🔴 關鍵決策點

**必須在開始前確認**:
- [ ] **同步方式**: 即時 (Webhook) / 批次 (排程) / 混合?
- [ ] **認證方式**: OAuth / API Key / JWT / 其他?
- [ ] **資料流向**: 雙向 / 單向讀取 / 單向寫入?
- [ ] **錯誤處理**: 重試策略 + 通知機制已定義?
- [ ] **SLA要求**: 第三方 SLA 是否滿足我們的需求?

---

## ⚠️ 常見陷阱

### 1. Rate Limiting 未考慮
**症狀**: 頻繁收到 429 Too Many Requests
**解法**: 實作 Token Bucket 或使用 Queue 控制請求速率

### 2. 資料格式驗證不足
**症狀**: 生產環境出現意外的資料格式導致系統崩潰
**解法**: 嚴格驗證所有輸入，使用 JSON Schema 驗證

### 3. 錯誤日誌不完整
**症狀**: 出問題時無法快速定位原因
**解法**: 記錄完整的 Request/Response (脫敏後)

### 4. 測試環境與生產環境不一致
**症狀**: 測試通過但生產環境失敗
**解法**: 確認測試環境使用相同的 API 版本與配置

### 5. 忽略第三方 API 變更
**症狀**: 第三方 API 升級後整合失效
**解法**: 訂閱第三方 API 變更通知，版本鎖定

---

## 📊 必要產出物

| 產出物 | 負責 Agent | 適用情境 |
|--------|-----------|---------|
| **System_of_Record_Map.md** | SA + Integration Specialist | 多系統整合必備 🆕 |
| **Integration_FRD.md** | SA | 整合需求完整、追蹤鏈建立 |
| **API_Research_Report.md** | Integration Specialist | 所有整合 |
| **Integration_Architecture.md** | SD + Integration Specialist | 所有整合 |
| **Canonical_Data_Model.md** | SA + SD | 多領域整合必備 🆕 |
| **Cross_System_Auth_Design.md** | Security + SD | 異質技術棧 SSO 🆕 |
| **Auth_Design.md** | Integration Specialist | 所有整合 |
| **Data_Sync_Strategy.md** | SD + Dev | 雙 DB 同步 🆕 |
| **Data_Mapping.md** | SA + Integration Specialist | 所有整合 |
| **Error_Handling_Strategy.md** | Integration Specialist | 所有整合 |
| **Integration_Test_Plan.md** | QA + Integration Specialist | 所有整合 |

---

## 🚀 快速檢查清單

**開始前** (10分鐘):
- [ ] 第三方 API 文檔已取得
- [ ] 測試環境帳號已申請
- [ ] 團隊已了解整合範圍
- [ ] Stakeholders 已確認整合優先級

**執行中** (每日):
- [ ] API 請求成功率 > 95%
- [ ] 回應時間符合預期
- [ ] 錯誤日誌已檢視
- [ ] 監控指標正常

**完成前** (驗收):
- [ ] 所有測試場景通過
- [ ] 效能符合要求
- [ ] 監控與告警已建立
- [ ] 文檔已更新
- [ ] Runbook 已準備

---

## 💡 Quick Wins (30分鐘內可完成)

1. **使用現成的SDK** (如果第三方提供)
   - 節省認證與請求封裝的時間
   - 減少錯誤處理的複雜度

2. **設定請求超時**
   - 避免無限等待
   - 建議: 10-30秒

3. **實作健康檢查端點**
   - 定期驗證第三方API可用性
   - 提早發現問題

4. **建立請求日誌**
   - 記錄所有API呼叫
   - 方便除錯與審計

5. **使用環境變數管理配置**
   - API URL, Token, Timeout 等
   - 方便切換環境

---

## ❌ 不適用場景

- ❌ 全新系統開發（請用 **Greenfield**）
- ❌ 既有系統功能修改/Bug修復（請用 **Brownfield**）
- ❌ 代碼品質改善/架構重組（請用 **Refactoring**）
- ❌ 全技術棧遷移（請用 **Migration**）
- ❌ 純效能優化（請用 **Performance**）

### 📌 情境區分指引

| 情境 | 判斷標準 | 適用範例 |
|------|---------|---------|
| **Integration** | 串接外部第三方 API/服務 | Stripe 支付、SendGrid 郵件、OAuth |
| **Brownfield** | 修改既有系統內部功能 | 新增報表、修 Bug、功能增強 |
| **Migration** | 替換整個技術棧/框架 | Oracle→PostgreSQL、Vue→React |

---

## 📖 詳細流程請看

**完整 SOP**: [SOP.md](./SOP.md) - 標準操作手冊 (約500行)
**深度指南**: [SOP_DeepDive.md](./SOP_DeepDive.md) - 複雜場景與故障排除

---

## 🆘 緊急求助

**整合失敗怎麼辦？**
1. 檢查第三方 API 狀態頁面
2. 確認認證 Token 是否過期
3. 查看錯誤日誌定位問題
4. 參考 [SOP_DeepDive.md](./SOP_DeepDive.md) 故障排除章節

**效能不符預期？**
1. 檢查 Rate Limiting 設定
2. 確認是否有 N+1 查詢問題
3. 考慮使用快取減少API呼叫
4. 參考 [Performance SOP](../performance/SOP.md)

---

## 🔗 延伸閱讀

- [Integration SOP 完整版](./SOP.md)
- [Integration DeepDive 深度指南](./SOP_DeepDive.md)
- [Integration 快速啟動指令集](../../prompts/scenario-prompts/integration-prompts.md)
- [integration-analysis-flow Workflow](../../workflow/scenario-specific/integration-analysis-flow.md)
- [AISDLC_INIT.md](../../AISDLC_INIT.md)

### 相關 Agents
- [integration-specialist-zh.yaml](../../agent/specialized/integration-specialist-zh.yaml) - Integration Specialist（主導）
- [sa-analyst-zh.yaml](../../agent/core/04.sa-analyst-zh.yaml) - Amanda（整合需求分析、SoR 識別）🆕
- [sd-architect-zh.yaml](../../agent/core/05.sd-architect-zh.yaml) - Marcus（整合架構、規範模型設計）
- [qa-tester-zh.yaml](../../agent/core/07.qa-tester-zh.yaml) - Quincy（整合測試規劃、Contract Testing）
- [dev-developer-zh.yaml](../../agent/core/06.dev-developer-zh.yaml) - David（認證授權、Outbox Pattern 實作）
- [devops-engineer-zh.yaml](../../agent/specialized/devops-engineer-zh.yaml) - DevOps Engineer（監控、分散式追蹤）
- [security-engineer-zh.yaml](../../agent/specialized/security-engineer-zh.yaml) - Security Engineer（跨系統 SSO/OAuth，異質技術棧安全，選用）
- [performance-engineer-zh.yaml](../../agent/specialized/performance-engineer-zh.yaml) - Performance Engineer（高頻 API/大量資料同步，選用）
- [sd-mobile-architect-zh.yaml](../../agent/specialized/sd-mobile-architect-zh.yaml) - Mobile Architect（Android/macOS 掃碼整合架構，選用）
- [qa-mobile-tester-zh.yaml](../../agent/specialized/qa-mobile-tester-zh.yaml) - Mobile QA（掃碼/離線同步測試，選用）

### 相關 Skills
- `/sa-analyst` - 整合需求分析、System of Record 識別 🆕
- `/integration-api-client` - 跨語言 API 客戶端建立（Python/Java/TypeScript）
- `/integration-oauth` - OAuth 2.0 / SSO / JWT Federation 整合 🆕
- `/integration-stripe` - Stripe 支付整合
- `/integration-webhook` - Webhook 處理系統
- `/integration-database` - 資料庫整合（PostgreSQL、Outbox Pattern）🆕
- `/integration-redis` - Redis 快取整合
- `/documentation-api` - API 文檔生成
- `/security-audit` - 安全審查
- `/qa-testing` - 測試策略與測試計畫
- `/devops-monitoring` - 監控告警系統
- `/mobile-development` - 行動端整合開發（涉及 Android/iOS/macOS 時）

---

**QuickRef 版本: v0.01
**最後更新**: 2026-02-12
**維護者**: AISDLC Framework Team
**預計閱讀時間**: 5 分鐘
**適用情境**: 快速執行與提醒
