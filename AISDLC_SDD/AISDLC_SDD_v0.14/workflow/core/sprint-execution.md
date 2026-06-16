# Sprint 執行與開發測試工作流程 (Sprint Execution & Dev-Test Workflow)

## 🔒 強制執行配置
```yaml
# AISDLC-SDD v0.01 執行配置
workflow_metadata:
  id: "sprint-execution"
  version: "v0.01"
  priority: "HIGH"
  scenario_applicable: ["greenfield", "brownfield", "refactoring"]

agent_binding:
  primary:
    - agent/core/06.dev-developer-zh.yaml
  supporting:
    - agent/core/07.qa-tester-zh.yaml
    - agent/core/05.sd-architect-zh.yaml
    - agent/specialized/devops-engineer-zh.yaml
  rules_enforcement: MANDATORY
  auto_load: true

execution_control:
  skip_confirmation: false
  require_human_interaction: true
  validation_checkpoints: enabled
  zero_speculation: true

workflow_priority: AGENT_RULES_FIRST
scenario_applicability:
  - greenfield
  - brownfield
  - refactoring
```

> ⚠️ **LLM 注意**：此 workflow 用於指導 Sprint 內的實際程式碼開發與測試。必須嚴格遵循「開發-編譯-測試循環」（Development-Build-Test Cycle），絕不可累積開發。

---

# 📋 Workflow 基本資訊

## Workflow 識別
- **Workflow ID**: `sprint-execution`
- **版本**: v0.01
- **狀態**: Active
- **優先級**: Core - High

## 描述
指導團隊在 Sprint 內進行程式碼實施、編譯驗證、單元測試、整合測試，並遵循 AISDLC 的「開發-編譯-測試循環」強制規則。

## 適用場景
- ✅ Greenfield: 新系統功能開發
- ✅ Brownfield: 既有系統功能擴充
- ✅ Refactoring: 重構與程式碼品質改善

## 觸發條件
- Sprint Backlog 已確定，User Stories 已分配
- 開發環境已建置完成
- CI/CD Pipeline 已設定

## 前置 Workflows
- `user-story-design` - User Story 與驗收標準已定義
- `api-specification` - API 規格已完成
- `devops-setup-flow` (Step 0 + 0.5) - 🔒 Layer 0 Security Baseline + Layer 1 Build & Verify 已配置
- `devops-setup-flow` (Step 0.6) - 🔒 Migration Pipeline 已配置（僅 Migration 情境需要）
- `devops-setup-flow` (Step 0.7) - 🛡️ Security Integration 增強安全掃描已配置（依情境安全等級：Standard/Advanced/Enhanced）
- `devops-setup-flow` (Step 0.8) - ⚡ Performance Benchmark Gate 已配置（performance 強制，greenfield/brownfield/refactoring/migration 選配）
- `devops-setup-flow` (Step 0.9) - 📝 Documentation Pipeline 已配置（documentation 強制，greenfield/brownfield/migration/integration 選配）
- `devops-setup-flow` (Step 0.10) - 🔔 Event-Driven Agent Notification 已配置（所有程式碼情境強制，documentation 選配）

---

# 🚀 執行流程

## 步驟 1: Sprint 啟動確認

**主導 Agent**: Dev (David) + QA (Quincy)

### 1.1 Sprint Backlog 確認
- [ ] 確認本 Sprint 的 User Stories 清單
- [ ] 確認每個 Story 的 AC (Acceptance Criteria)
- [ ] 確認技術實施方案（參考 SRD + API Spec）
- [ ] 確認開發順序與依賴關係

### 1.2 開發環境驗證
- [ ] 確認開發環境可正常編譯
- [ ] 確認測試環境可正常執行
- [ ] 確認 CI/CD Pipeline 可正常觸發
- [ ] 確認資料庫遷移腳本可執行

**🔴 人類確認點**: 確認 Sprint 目標和開發順序

---

## 步驟 2: 開發-編譯-測試循環（核心流程）

**主導 Agent**: Dev (David)
**建議 Skill**: `/dev-review`

> 🔴 **CRITICAL**: 此為 AISDLC 最核心的開發規則，必須嚴格遵守！
> 詳細規範參考: [Development_Build_Test_Cycle.md](../../guides/user/process/Development_Build_Test_Cycle.md)

### 2.1 單一功能單元開發

對於每個 User Story，拆解為最小可編譯單元，逐一執行以下循環：

```
📝 開發 1 支程式（或 1 個功能單元，建議 < 100 行）
    ↓
🔨 立即編譯 (Compile/Build)
    ↓
❌ 編譯失敗？ → 🔴 立即停止 → 依照錯誤訊息修復 → 重新編譯
    ↓
✅ 編譯成功
    ↓
🧪 執行單元測試 (Unit Test)
    ↓
❌ 測試失敗？ → 🔴 立即停止 → 依照規格文檔修復 → 重新測試
    ↓
✅ 測試通過
    ↓
💾 Commit（有意義的 commit message）
    ↓
📝 繼續開發下一支程式
```

### 2.2 各技術棧編譯測試命令

| 技術棧 | 編譯命令 | 測試命令 |
|--------|---------|---------|
| **Java/Spring Boot** | `mvn compile` / `gradle build` | `mvn test` / `gradle test` |
| **TypeScript/Next.js** | `npx tsc --noEmit` | `npm test` / `jest` |
| **Python/Flask/Django** | `python -m py_compile <file>` | `pytest` |
| **Go** | `go build` | `go test` |
| **Kotlin/Android** | `./gradlew assembleDebug` | `./gradlew test` |
| **Swift/macOS** | `swift build` / `xcodebuild` | `swift test` / `xcodebuild test` |

### 2.3 禁止行為
- ❌ 禁止累積開發多支程式後才編譯
- ❌ 禁止編譯失敗後繼續開發
- ❌ 禁止跳過單元測試
- ❌ 禁止測試失敗後「先跳過」或註解掉測試

---

## 步驟 3: 整合測試

**主導 Agent**: QA (Quincy)
**建議 Skill**: `/qa-testing`、`/testing-strategy`

### 3.1 API 整合測試
- [ ] 驗證 API endpoint 回應正確
- [ ] 驗證 API 錯誤處理（4xx, 5xx）
- [ ] 驗證 API 認證授權機制
- [ ] 驗證跨模組 API 呼叫鏈

### 3.2 前後端整合測試
- [ ] 驗證前端頁面可正確呼叫 API
- [ ] 驗證資料流完整性（前端 → API → DB → API → 前端）
- [ ] 驗證錯誤狀態的 UI 回饋
- [ ] 驗證載入狀態和使用者體驗

### 3.3 跨平台整合測試（如適用）
- [ ] Web 版功能驗證
- [ ] Mobile 版功能驗證
- [ ] Desktop 版功能驗證
- [ ] 平台間資料一致性驗證

---

## 步驟 4: Code Review

**主導 Agent**: Dev (David)
**建議 Skill**: `/dev-review`、`/code-review`

### 4.1 Code Review 檢查清單
- [ ] 程式碼符合團隊 Coding Standard
- [ ] 沒有安全漏洞（OWASP Top 10）
- [ ] 單元測試覆蓋率 ≥ 80%
- [ ] 沒有 TODO/FIXME 殘留
- [ ] 效能無明顯瓶頸
- [ ] API 實作符合 API Spec

### 4.2 PR 提交規範
```
feat: 新增商品管理 CRUD API
  - 實作 ProductController.java (GET/POST/PUT/DELETE)
  - 新增 ProductService 業務邏輯
  - 新增 ProductRepository JPA 介面
  - 單元測試覆蓋率 85%

  Closes: US-001
```

**🔴 人類確認點**: Code Review 通過後合併

---

## 步驟 5: Sprint 驗收

**主導 Agent**: QA (Quincy) + PM/PO (Victoria)

### 5.1 驗收測試 (AT) 執行
- [ ] 逐項執行每個 User Story 的 Acceptance Criteria
- [ ] 記錄測試結果（Pass/Fail）
- [ ] 失敗項目建立 Bug 報告
- [ ] Bug 修復後重新驗收

### 5.2 Sprint 回顧
- [ ] 完成的 User Stories 統計
- [ ] 未完成項移回 Backlog
- [ ] 記錄 Sprint Velocity
- [ ] 識別改善事項

**🔴 人類確認點**: Sprint 驗收結果確認

---

# 📊 產出文檔

| 文檔 | 存放位置 | 說明 |
|------|---------|------|
| Sprint 測試報告 | `docs/03_testing/` | 每個 Sprint 的測試結果 |
| Code Review 紀錄 | `docs/06_quality/` | 代碼審查記錄 |
| Sprint 進度日誌 | `docs/05_development/` | 每日/每 Sprint 進度 |
| Bug 報告 | `docs/03_testing/` | 已發現缺陷清單 |

---

# 🔗 相關資源

## 相關 Workflow
- [User Story Design](user-story-design.md) - 前置：User Story 定義
- [API Specification](api-specification.md) - 前置：API 規格
- [Consistency Check](consistency-check.md) - Sprint 完成後執行

## 相關 Agent
- [Dev - Developer](../../agent/core/06.dev-developer-zh.yaml) - 開發主導
- [QA - QA Engineer](../../agent/core/07.qa-tester-zh.yaml) - 測試主導
- [SD - Architect](../../agent/core/05.sd-architect-zh.yaml) - 架構諮詢
- [DevOps Engineer](../../agent/specialized/devops-engineer-zh.yaml) - CI/CD 支援

## 相關指南
- [Development_Build_Test_Cycle.md](../../guides/user/process/Development_Build_Test_Cycle.md) - 開發-編譯-測試循環
- [Code_Review_Guidelines.md](../../guides/user/process/Code_Review_Guidelines.md) - Code Review 標準

## 建議 Skill
- `/dev-review` - 代碼審查
- `/qa-testing` - 測試策略與執行
- `/testing-strategy` - 測試策略設計
- `/code-review` - 標準化 Code Review 流程

---

**版本**：v0.01
**建立日期**：2026-02-11
**維護者**：AISDLC Framework Team
