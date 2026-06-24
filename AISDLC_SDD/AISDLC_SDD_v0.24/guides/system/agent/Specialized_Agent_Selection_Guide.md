# Specialized Agent 選擇指南
# Specialized Agent Selection Guide

> **文檔用途**: 幫助您快速判斷何時應該載入特定的 Specialized Agent

**版本**: v0.01
**最後更新**: 2025-12-01
**相關文檔**: [AISDLC_INIT.md](../AISDLC_INIT.md), [Platform_Agent_Selection_Guide.md](Platform_Agent_Selection_Guide.md)

---

## 📋 Specialized Agent 推薦條件表

以下表格提供明確的 Specialized Agent 推薦條件，幫助您快速判斷何時應該載入特定的 Specialized Agent：

| Specialized Agent | 推薦載入條件 | 典型觸發關鍵詞 | 不推薦場景 |
|------------------|------------|--------------|-----------|
| **code-analyzer** | - 需要代碼品質分析<br>- 重構既有代碼<br>- 技術債務評估 | 代碼審查、重構、品質改善、技術債 | 新專案開發初期 (無既有代碼) |
| **performance-engineer** | - 效能優化需求<br>- 回應時間 > 2s<br>- 併發量 > 1000 QPS | 效能、延遲、吞吐量、優化、基準測試 | 功能尚未實作完成 |
| **integration-specialist** | - 整合第三方 API/服務<br>- 跨系統數據交換<br>- OAuth/SSO 認證 | API 整合、第三方服務、認證、數據同步 | 純內部系統開發 |
| **devops-engineer** | - CI/CD 設定<br>- 容器化部署<br>- 基礎設施自動化 | CI/CD、Docker、K8s、部署、Pipeline | 本地開發環境設定 |
| **dev-senior** | - 複雜技術決策<br>- 架構評審<br>- 技術可行性評估 > 20 人日 | 技術評審、架構決策、複雜實作、技術選型 | 簡單 CRUD 功能開發 |
| **security-engineer** | - 安全需求 (OWASP)<br>- 敏感數據處理<br>- 合規要求 (GDPR/HIPAA) | 安全、加密、權限、合規、資安、漏洞 | 內部 POC 或原型開發 |
| **compliance-officer** | - 法規合規 (金融/醫療/個資)<br>- 稽核要求<br>- 資料保護規範 | GDPR、HIPAA、PCI-DSS、稽核、合規 | 一般企業內部工具 |
| **technical-writer** | - 技術文檔撰寫<br>- API 文檔生成<br>- 使用手冊編寫 | API 文檔、使用手冊、技術文件、文檔標準 | 內部開發文檔 (已有 SA) |
| **qa-lead** | - 測試策略制定<br>- QA 流程建立<br>- 測試團隊 > 3 人 | 測試策略、QA 流程、測試計畫、品質管理 | 簡單功能測試 (qa-tester 已足夠) |
| **qa-automation** | - 自動化測試<br>- 迴歸測試<br>- CI/CD 測試整合 | 自動化測試、Selenium、Cypress、測試框架 | 純手動測試專案 |
| **qa-web-tester** | - Web 應用測試<br>- 跨瀏覽器測試<br>- 前端 E2E 測試 | Web 測試、瀏覽器相容性、UI 測試 | Mobile App 或 Backend API 專案 |
| **qa-mobile-tester** | - Mobile App 測試<br>- iOS/Android 測試<br>- 裝置相容性測試 | Mobile 測試、iOS、Android、Appium | Web 或 Backend API 專案 |
| **sd-web-architect** | - Web 技術架構設計<br>- 前端架構選型<br>- Web 效能優化 | React、Vue、Angular、Web 架構、SPA | Mobile 或 Desktop 應用 |
| **sd-mobile-architect** | - Mobile 架構設計<br>- iOS/Android 原生開發<br>- 跨平台架構 | iOS、Android、React Native、Flutter | Web 或純後端專案 |

---

## 🎯 使用指引

### 1. 單一條件觸發
只要符合「推薦載入條件」中的**任一條件**，即可考慮載入該 Agent。

### 2. 關鍵詞偵測
AI 應自動偵測使用者描述中的「典型觸發關鍵詞」，主動詢問是否載入對應 Agent。

### 3. 排除場景
符合「不推薦場景」時，即使有觸發關鍵詞，也應提醒使用者可能不需要該 Agent。

### 4. 組合使用
複雜專案可能需要同時載入多個 Specialized Agents。

---

## 💡 範例應用

### 範例 1: 整合第三方支付

**使用者**: 「我需要整合 Stripe 支付 API」

**AI 判斷**:
```
✅ 觸發關鍵詞: 「整合」「API」
✅ 推薦載入: integration-specialist
✅ 同時推薦: security-engineer (涉及敏感支付數據)
```

**推薦理由**:
- `integration-specialist`: 專門處理第三方 API 整合
- `security-engineer`: Stripe 涉及支付數據，需要安全專家確保 PCI-DSS 合規

---

### 範例 2: 資料庫查詢效能優化

**使用者**: 「我要優化資料庫查詢效能」

**AI 判斷**:
```
✅ 觸發關鍵詞: 「優化」「效能」
✅ 推薦載入: performance-engineer
❌ 不推薦: qa-web-tester (與 Web 測試無關)
```

**推薦理由**:
- `performance-engineer`: 專門處理效能優化、基準測試、瓶頸分析

---

### 範例 3: 舊系統代碼重構

**使用者**: 「我需要重構既有的 Legacy 代碼，改善代碼品質」

**AI 判斷**:
```
✅ 觸發關鍵詞: 「重構」「代碼品質」
✅ 推薦載入: code-analyzer
✅ 同時推薦: dev-senior (複雜重構決策)
```

**推薦理由**:
- `code-analyzer`: 代碼品質分析、技術債務評估
- `dev-senior`: 複雜重構策略、技術決策

---

### 範例 4: CI/CD Pipeline 建置

**使用者**: 「我要設定 GitHub Actions 的 CI/CD Pipeline」

**AI 判斷**:
```
✅ 觸發關鍵詞: 「CI/CD」「Pipeline」
✅ 推薦載入: devops-engineer
✅ 同時推薦: qa-automation (測試自動化整合)
```

**推薦理由**:
- `devops-engineer`: CI/CD 設定、部署自動化
- `qa-automation`: 測試整合到 CI/CD Pipeline

---

## 🔄 Agent 組合建議

以下是常見專案類型的 Specialized Agent 組合建議：

### 1. 電商網站專案 (含支付整合)
```
Primary: pm-po, sa-analyst, sd-web-architect, qa-tester
Specialized:
  - integration-specialist (支付 API 整合)
  - security-engineer (支付安全、個資保護)
  - qa-automation (自動化測試)
  - performance-engineer (大流量處理)
```

### 2. 企業內部系統重構
```
Primary: pm-po, sa-analyst, sd-architect, dev-developer
Specialized:
  - code-analyzer (代碼品質分析)
  - dev-senior (重構策略)
  - qa-lead (測試策略制定)
```

### 3. SaaS 平台開發
```
Primary: pm-po, sa-analyst, sd-web-architect, qa-tester
Specialized:
  - devops-engineer (CI/CD、容器化部署)
  - security-engineer (資安、合規)
  - performance-engineer (多租戶效能優化)
  - technical-writer (API 文檔、使用手冊)
```

### 4. Mobile App 開發 (iOS/Android)
```
Primary: pm-po, sa-analyst, sd-mobile-architect, qa-tester
Specialized:
  - qa-mobile-tester (裝置相容性測試)
  - qa-automation (自動化測試)
  - integration-specialist (第三方 SDK 整合)
```

---

## 🚨 常見誤用場景

### ❌ 誤用 1: 新專案初期就載入 code-analyzer
**問題**: 新專案沒有既有代碼，code-analyzer 無用武之地
**建議**: 等到有一定代碼量後 (如第一版開發完成) 再載入

### ❌ 誤用 2: 功能未完成就進行效能優化
**問題**: 過早優化，浪費資源
**建議**: 先完成功能開發，確認有效能問題後再載入 performance-engineer

### ❌ 誤用 3: 簡單功能測試載入 qa-lead
**問題**: qa-tester 已足夠，qa-lead 用於複雜測試策略
**建議**: 僅在測試團隊 > 3 人或複雜測試場景時載入 qa-lead

### ❌ 誤用 4: 內部開發文檔使用 technical-writer
**問題**: SA Agent 已能處理內部技術文檔
**建議**: 僅在需要對外 API 文檔、使用手冊時載入 technical-writer

---

## 📊 決策流程圖

```
使用者描述專案需求
        │
        ▼
    關鍵詞匹配
        │
        ├─ 匹配到「整合」「API」 → 推薦 integration-specialist
        ├─ 匹配到「效能」「優化」 → 推薦 performance-engineer
        ├─ 匹配到「重構」「代碼品質」 → 推薦 code-analyzer
        ├─ 匹配到「CI/CD」「部署」 → 推薦 devops-engineer
        ├─ 匹配到「安全」「合規」 → 推薦 security-engineer
        └─ 其他關鍵詞 → 查詢推薦條件表
                │
                ▼
        檢查不推薦場景
                │
                ├─ 符合不推薦場景 → 提醒使用者 + 提供替代方案
                └─ 不符合 → 推薦載入 Agent
                        │
                        ▼
                檢查是否需要組合載入
                        │
                        ├─ 涉及敏感數據 → 同時推薦 security-engineer
                        ├─ 涉及 CI/CD → 同時推薦 qa-automation
                        └─ 其他 → 僅載入單一 Agent
```

---

## 🔍 快速查詢表 (按專案類型)

| 專案類型 | 推薦 Specialized Agents |
|---------|------------------------|
| 電商網站 | integration-specialist, security-engineer, performance-engineer |
| 企業內部系統 | code-analyzer, dev-senior |
| SaaS 平台 | devops-engineer, security-engineer, performance-engineer, technical-writer |
| Mobile App | qa-mobile-tester, qa-automation, integration-specialist |
| API 服務 | technical-writer, security-engineer, performance-engineer |
| 舊系統重構 | code-analyzer, dev-senior, qa-lead |
| 資料分析平台 | performance-engineer, security-engineer (敏感數據) |
| 金融/醫療系統 | security-engineer, compliance-officer |

---

## 📚 相關文檔

- [AISDLC_INIT.md](../AISDLC_INIT.md) - 框架初始化配置
- [Platform_Agent_Selection_Guide.md](Platform_Agent_Selection_Guide.md) - 平台特化 Agent 選擇
- [AGENT_COLLABORATION_PATTERNS.md](../agent/AGENT_COLLABORATION_PATTERNS.md) - Agent 協作模式
- [Specialized Agents 配置檔案](../agent/specialized/) - 各 Specialized Agent 的 YAML 配置

---

**維護者**: AISDLC Framework Team
**版本**: v0.01
**最後更新**: 2025-12-01
