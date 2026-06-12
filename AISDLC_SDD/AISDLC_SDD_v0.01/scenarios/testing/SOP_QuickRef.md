# Testing & QA Strategy - 快速參考指南
# Quick Reference Guide

**版本**: v0.01
**閱讀時間**: 5 分鐘
**適用情境**: 測試策略規劃、QA 流程建立、測試自動化

---

## 🎯 一頁總覽

### 適用場景
✅ 建立完整測試策略
✅ 提升測試覆蓋率
✅ 實施測試自動化
✅ 建立 QA 流程和規範

### 不適用場景
❌ 單純寫測試案例（使用測試模板）
❌ Bug 修復（請用 Brownfield）
❌ 效能測試（請用 Performance）

---

## 📋 6 階段快速流程

```
總時間: 1-2 天

┌─────────────────────────────────────────────┐
│ 階段 1: 測試需求分析 (2-3 小時) 🔴           │
│ └─ 專案特性 → 風險評估 → 測試範圍           │
├─────────────────────────────────────────────┤
│ 階段 2: 測試策略設計 (2-3 小時) 🔴           │
│ └─ 測試金字塔 → 工具選擇 → 流程定義         │
├─────────────────────────────────────────────┤
│ 階段 3: 測試環境規劃 (2-3 小時) 🟡           │
│ └─ 環境配置 → 測試資料 → CI/CD 整合         │
├─────────────────────────────────────────────┤
│ 階段 4: 測試案例設計 (3-4 小時) 🟡           │
│ └─ 測試場景 → 用例撰寫 → 優先級排序         │
├─────────────────────────────────────────────┤
│ 階段 5: 自動化實施 (4-6 小時) 🟡             │
│ └─ 框架搭建 → 腳本開發 → 執行驗證           │
├─────────────────────────────────────────────┤
│ 階段 6: 持續改進 (ongoing) ✅                │
│ └─ 指標監控 → 流程優化 → 團隊培訓           │
└─────────────────────────────────────────────┘
```

---

## 🚀 快速啟動

### Step 1: 載入框架
```
提示詞:
「請載入 AISDLC (v0.01)，我需要建立測試策略」

或具體描述:
「新專案需要建立完整的測試體系」
「現有專案測試覆蓋率低，需要改善」
「需要實施測試自動化」
```

### Step 2: 提供專案資訊
```
必須提供:
□ 專案類型（Web/Mobile/Backend/Desktop）
□ 技術棧
□ 團隊規模和能力
□ 時程限制

建議提供:
□ 風險評估
□ 現有測試狀況
□ 預算限制
□ 品質目標
```

---

## 🏗️ 測試金字塔快速參考

### 標準測試金字塔

```
        ╱ ╲
       ╱ E2E ╲         10% - 少量端到端測試
      ╱───────╲
     ╱ Integration ╲   20% - 適量整合測試
    ╱─────────────╲
   ╱ Unit Tests     ╲  70% - 大量單元測試
  ╱─────────────────╲
```

### 各層級測試對比

| 測試類型 | 數量 | 速度 | 成本 | 維護 | 信心 |
|---------|------|------|------|------|------|
| **Unit** | 多 | ⚡ 快 | 💰 低 | 🔧 易 | 🎯 低 |
| **Integration** | 中 | ⚡ 中 | 💰💰 中 | 🔧🔧 中 | 🎯🎯 中 |
| **E2E** | 少 | 🐌 慢 | 💰💰💰 高 | 🔧🔧🔧 難 | 🎯🎯🎯 高 |

### 測試配置建議

```yaml
小型專案 (< 3 個月):
- Unit: 60%
- Integration: 30%
- E2E: 10%
工具: Jest/Vitest, Supertest, Playwright

中型專案 (3-12 個月):
- Unit: 70%
- Integration: 20%
- E2E: 10%
工具: Jest, Testing Library, Cypress

大型專案 (> 12 個月):
- Unit: 70%
- Integration: 20%
- E2E: 8%
- Contract: 2%
工具: Jest, Pact, Cypress, K6
```

---

## ⚡ 測試策略速查表

### 按專案類型選擇策略

**Web Application**
```yaml
必須:
✅ 單元測試（Business Logic）
✅ 整合測試（API Endpoints）
✅ E2E 測試（關鍵流程）
✅ 視覺回歸測試

建議:
🟡 可訪問性測試（a11y）
🟡 跨瀏覽器測試
🟡 效能測試

工具:
- Jest + React Testing Library
- Cypress / Playwright
- Percy / Chromatic (視覺)
```

**Mobile Application**
```yaml
必須:
✅ 單元測試
✅ Widget/UI 測試
✅ 整合測試
✅ 裝置測試（真機 + 模擬器）

建議:
🟡 電量測試
🟡 網路狀況測試
🟡 多解析度測試

工具:
- iOS: XCTest, XCUITest
- Android: JUnit, Espresso
- Cross-platform: Appium, Detox
```

**Backend API**
```yaml
必須:
✅ 單元測試（Business Logic）
✅ API 整合測試
✅ 資料庫測試
✅ Contract Testing

建議:
🟡 負載測試
🟡 安全測試
🟡 Chaos Engineering

工具:
- Jest, Mocha, PyTest
- Supertest, RestAssured
- Pact (Contract)
- K6, JMeter (負載)
```

**Microservices**
```yaml
必須:
✅ 單元測試
✅ 整合測試
✅ Contract Testing (重要!)
✅ 端到端測試

建議:
🟡 服務間通訊測試
🟡 容錯測試
🟡 分散式追蹤測試

工具:
- Pact (Contract)
- TestContainers
- WireMock (Stub)
- Chaos Mesh
```

---

## 🎯 測試覆蓋率目標

### 覆蓋率標準

```yaml
最低要求 (Minimum):
- 關鍵業務邏輯: 80%+
- API Endpoints: 70%+
- 整體: 60%+

良好標準 (Good):
- 關鍵業務邏輯: 90%+
- API Endpoints: 80%+
- 整體: 75%+

優秀標準 (Excellent):
- 關鍵業務邏輯: 95%+
- API Endpoints: 90%+
- 整體: 85%+

⚠️ 注意: 100% 覆蓋率不是目標
- 投資報酬率低
- 維護成本高
- 關注關鍵路徑即可
```

### 覆蓋率類型

```yaml
Line Coverage (行覆蓋):
- 最常用
- 每行程式碼是否執行

Branch Coverage (分支覆蓋):
- 更嚴格
- 所有條件分支是否測試

Function Coverage (函數覆蓋):
- 基本要求
- 每個函數是否呼叫

Statement Coverage (語句覆蓋):
- 類似行覆蓋
- 每個語句是否執行

建議: 以 Branch Coverage 為準 (更可靠)
```

---

## 🛠️ 測試工具快速選擇

### 前端測試工具

| 工具 | 類型 | 特點 | 推薦指數 |
|------|------|------|---------|
| **Jest** | Unit | 零配置、快速 | ⭐⭐⭐⭐⭐ |
| **Vitest** | Unit | 極快、Vite 生態 | ⭐⭐⭐⭐⭐ |
| **React Testing Library** | Integration | 使用者視角 | ⭐⭐⭐⭐⭐ |
| **Cypress** | E2E | 開發體驗好 | ⭐⭐⭐⭐⭐ |
| **Playwright** | E2E | 跨瀏覽器、快 | ⭐⭐⭐⭐⭐ |
| **Storybook** | Component | 元件測試 | ⭐⭐⭐⭐ |

### 後端測試工具

| 工具 | 語言 | 類型 | 推薦指數 |
|------|------|------|---------|
| **Jest** | Node.js | Unit/Integration | ⭐⭐⭐⭐⭐ |
| **Mocha + Chai** | Node.js | Unit/Integration | ⭐⭐⭐⭐ |
| **Supertest** | Node.js | API Testing | ⭐⭐⭐⭐⭐ |
| **PyTest** | Python | Unit/Integration | ⭐⭐⭐⭐⭐ |
| **JUnit** | Java | Unit | ⭐⭐⭐⭐⭐ |
| **Go Test** | Go | Unit | ⭐⭐⭐⭐⭐ |
| **Pact** | Multi | Contract | ⭐⭐⭐⭐⭐ |

### E2E 測試工具對比

```yaml
Cypress:
優點: 開發體驗好、調試容易、自動等待
缺點: 僅 Chrome 系（有限支援 Firefox/Edge）
適用: Web 應用 E2E 測試

Playwright:
優點: 跨瀏覽器、平行執行、快速
缺點: 學習曲線稍高
適用: 需要跨瀏覽器測試

Selenium:
優點: 生態成熟、語言支援多
缺點: 配置複雜、不穩定
適用: 遺留專案、特殊需求

Puppeteer:
優點: 輕量、Chrome DevTools Protocol
缺點: 僅 Chrome
適用: 爬蟲、PDF 生成、測試

推薦: Playwright (新專案) / Cypress (快速上手)
```

---

## 📝 測試案例撰寫快速指南

### Given-When-Then 模式

```javascript
// ✅ 推薦寫法
describe('Shopping Cart', () => {
  it('should calculate total price correctly', () => {
    // Given (準備測試資料)
    const cart = new ShoppingCart();
    cart.addItem({ id: 1, price: 100, quantity: 2 });
    cart.addItem({ id: 2, price: 50, quantity: 1 });

    // When (執行操作)
    const total = cart.calculateTotal();

    // Then (驗證結果)
    expect(total).toBe(250);
  });
});

// ❌ 不推薦寫法
it('test1', () => {
  const cart = new ShoppingCart();
  cart.addItem({ id: 1, price: 100, quantity: 2 });
  expect(cart.calculateTotal()).toBe(200);
  cart.addItem({ id: 2, price: 50, quantity: 1 });
  expect(cart.calculateTotal()).toBe(250);
});
```

### AAA 模式（Arrange-Act-Assert）

```python
# ✅ 推薦寫法
def test_user_registration():
    # Arrange
    user_service = UserService()
    user_data = {"email": "test@example.com", "password": "secret"}

    # Act
    result = user_service.register(user_data)

    # Assert
    assert result.success == True
    assert result.user.email == "test@example.com"
```

### 測試命名最佳實踐

```yaml
✅ 好的命名:
- should_return_404_when_user_not_found
- should_calculate_discount_for_vip_users
- should_throw_error_when_email_invalid

❌ 不好的命名:
- test1
- testUser
- checkFunction
- works

原則:
- 描述「what」而非「how」
- 說明測試條件和預期結果
- 使用業務語言，非技術術語
```

---

## 🚨 測試常見陷阱

### ❌ 避免這些錯誤

**1. 測試實作細節而非行為**
```javascript
❌ 錯誤: 測試內部狀態
expect(component.state.isLoading).toBe(true);

✅ 正確: 測試使用者可見的行為
expect(screen.getByText('Loading...')).toBeInTheDocument();
```

**2. 測試間有依賴**
```javascript
❌ 錯誤: 測試順序影響結果
let user;
it('should create user', () => {
  user = createUser();
});
it('should update user', () => {
  updateUser(user); // 依賴前一個測試
});

✅ 正確: 每個測試獨立
it('should update user', () => {
  const user = createUser(); // 自己準備資料
  updateUser(user);
});
```

**3. 過度使用 Mock**
```javascript
❌ 錯誤: Mock 所有東西
const mockAdd = jest.fn(() => 3);
math.add = mockAdd;
expect(math.add(1, 2)).toBe(3); // 沒測試到真實邏輯

✅ 正確: 只 Mock 外部依賴
// 真實測試 add 函數
expect(math.add(1, 2)).toBe(3);
// 只 Mock API 呼叫
jest.mock('./api');
```

**4. 測試覆蓋率迷思**
```
❌ 錯誤: 追求 100% 覆蓋率
- 花大量時間測試 Getters/Setters
- 測試框架程式碼
- 測試第三方套件

✅ 正確: 聚焦關鍵路徑
- 業務邏輯
- 容易出錯的部分
- 高價值功能
```

---

## 📊 測試指標監控

### 關鍵指標 (Key Metrics)

```yaml
Code Coverage (程式碼覆蓋率):
目標: 75%+
監控: 每次 CI 執行

Test Pass Rate (測試通過率):
目標: > 95%
警戒: < 90%

Test Execution Time (測試執行時間):
Unit Tests: < 10 分鐘
Integration Tests: < 30 分鐘
E2E Tests: < 1 小時

Flaky Test Rate (不穩定測試率):
目標: < 1%
行動: 超過 2% 立即修復

Bug Escape Rate (缺陷逃逸率):
計算: Production Bugs / Total Bugs
目標: < 5%

Test Maintenance Ratio (測試維護比):
計算: Test Code Changes / Production Code Changes
目標: < 1.5x
```

### Dashboard 範例

```
┌─────────────────────────────────────────┐
│ Test Health Dashboard                    │
├─────────────────────────────────────────┤
│ Coverage:  [████████░░] 82%   ✅        │
│ Pass Rate: [██████████] 98%   ✅        │
│ Exec Time: [████░░░░░░] 25min ✅        │
│ Flaky:     [█░░░░░░░░░] 0.8%  ✅        │
│ Bug Escape:[██░░░░░░░░] 3.2%  ✅        │
└─────────────────────────────────────────┘

Alerts:
⚠️ E2E Tests 執行時間超過 1 小時
✅ All other metrics healthy
```

---

## 🔄 CI/CD 整合快速配置

### GitHub Actions 範例

```yaml
name: Test

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Node
        uses: actions/setup-node@v3
        with:
          node-version: '18'

      - name: Install dependencies
        run: npm ci

      - name: Run unit tests
        run: npm run test:unit

      - name: Run integration tests
        run: npm run test:integration

      - name: Upload coverage
        uses: codecov/codecov-action@v3

      - name: Run E2E tests
        run: npm run test:e2e
        if: github.event_name == 'push' && github.ref == 'refs/heads/main'
```

### 測試執行策略

```yaml
Pull Request (PR):
✅ Unit Tests (必須)
✅ Integration Tests (必須)
✅ Linting + Type Check
🟡 E2E Tests (Smoke Tests 只測關鍵路徑)

Merge to Main:
✅ 完整 Test Suite
✅ E2E Tests (Full Suite)
✅ Coverage Report
✅ Security Scan

Nightly Build:
✅ 完整 Test Suite
✅ Performance Tests
✅ Compatibility Tests
✅ Visual Regression Tests
```

---

## 🎯 快速決策：測試優先級

### 決策樹

```
這個功能是核心業務邏輯嗎？
├─ 是 → 🔴 高優先級
│         - 單元測試 (必須)
│         - 整合測試 (必須)
│         - E2E 測試 (必須)
│
└─ 否 → 容易出錯嗎？
          ├─ 是 → 🟡 中優先級
          │         - 單元測試 (必須)
          │         - 整合測試 (建議)
          │
          └─ 否 → 🟢 低優先級
                    - 單元測試 (建議)
                    - 整合測試 (可選)
```

---

## ✅ 測試完成檢查清單

```yaml
測試策略:
□ 已定義測試範圍
□ 已選擇測試工具
□ 已建立測試環境
□ 已整合到 CI/CD

測試實施:
□ 單元測試覆蓋率 >= 70%
□ 關鍵路徑整合測試完成
□ E2E 測試覆蓋主要流程
□ 測試可獨立執行（無依賴）

測試品質:
□ 測試命名清晰
□ 測試執行速度合理
□ 無 Flaky Tests
□ 測試文檔完整

持續改進:
□ 測試指標監控就緒
□ 定期 Review 測試覆蓋
□ 團隊測試培訓完成
□ 測試最佳實踐文檔化

電商/訂閱/付費系統額外強制項 (適用時):
□ 付費內容 API 授權測試完成（PAID-001~004）
□ Server-side 金額驗算測試完成（PRICE-001~004）
□ Race Condition 並發安全測試完成（RACE-001~003）
□ 金流 Webhook 簽名驗證與冪等性測試完成
```

---

## 🔗 延伸閱讀

- [Testing SOP 完整版](./SOP.md)
- [Testing DeepDive 深度指南](./SOP_DeepDive.md)
- [Testing 快速啟動指令集](../../prompts/scenario-prompts/testing-prompts.md)
- [testing-strategy-flow Workflow](../../workflow/scenario-specific/testing-strategy-flow.md)
- [測試計畫模板](../../docs_template/core/tests/AT_Module_Template.md)
- [測試報告模板](../../docs_template/core/tests/Test_Report_Template.md)
- [AISDLC_INIT.md](../../AISDLC_INIT.md)

### 相關 Agents
- [qa-lead-zh.yaml](../../agent/specialized/qa-lead-zh.yaml) - QA Lead（主導）
- [qa-automation-zh.yaml](../../agent/specialized/qa-automation-zh.yaml) - QA Automation（自動化測試）
- [dev-developer-zh.yaml](../../agent/core/06.dev-developer-zh.yaml) - David（測試實作支援）
- [qa-tester-zh.yaml](../../agent/core/07.qa-tester-zh.yaml) - Quincy（驗收測試）
- [qa-web-tester-zh.yaml](../../agent/specialized/qa-web-tester-zh.yaml) - Web QA（Web 測試，選用）
- [qa-mobile-tester-zh.yaml](../../agent/specialized/qa-mobile-tester-zh.yaml) - Mobile QA（行動端測試，選用）
- [security-engineer-zh.yaml](../../agent/specialized/security-engineer-zh.yaml) - Security Engineer（安全測試，選用）
- [performance-engineer-zh.yaml](../../agent/specialized/performance-engineer-zh.yaml) - Performance Engineer（效能測試，選用）
- [devops-engineer-zh.yaml](../../agent/specialized/devops-engineer-zh.yaml) - DevOps Engineer（測試環境/CI，選用）
- [integration-specialist-zh.yaml](../../agent/specialized/integration-specialist-zh.yaml) - Integration Specialist（跨模組整合測試、Contract Testing、QR Code 掃碼整合，選用）
- [compliance-officer-zh.yaml](../../agent/specialized/compliance-officer-zh.yaml) - Compliance Officer（電商金流 PCI-DSS、付費內容保護、GDPR 合規測試，選用）

### 相關 Skills
- `/testing-strategy` - 測試策略設計
- `/qa-testing` - 測試計畫與測試案例
- `/security-audit` - 安全測試（OWASP Top 10）
- `/performance-optimization` - 效能/負載測試
- `/devops-github-actions` - CI 測試整合
- `/devops-docker` - Docker 測試環境
- `/devops-monitoring` - 測試指標監控
- `/mobile-development` - 行動端測試（涉及 Android/iOS/macOS 時）
- `/compliance-audit` - 合規測試（電商 PCI-DSS、付費內容保護、GDPR 驗證）
- `/integration-database` - 資料庫測試（PostgreSQL 索引、Testcontainers、並發查詢）
- `/code-review` - 測試程式碼品質審查（避免 Flaky Test、覆蓋率盲點）

---

**提示**:
- 測試不是越多越好，關注 ROI
- 測試速度很重要（開發體驗）
- 持續重構測試程式碼
- 測試是團隊責任，不只 QA

---

**文檔版本: v0.01
**最後更新**: 2026-02-17
