# Testing Strategy Flow
# 測試策略制定與實作流程

## Workflow 名稱
**testing-strategy-flow** - 測試策略完整規劃流程

## 描述
建立完整的測試體系，包含測試金字塔設計、測試案例生成、自動化實施、環境管理和報告。

## 適用場景
- **使用時機**：專案啟動、測試體系建立、測試自動化
- **適用專案**：所有需要系統性測試的專案
- **執行頻率**：專案初期建立，持續維護

## 觸發條件
- 專案需求已明確
- 代碼庫已建立
- 測試目標已定義

---

# 角色與責任

## 主要負責人
**Agent 角色**：QA-Lead + QA-Automation
**責任**：測試策略制定、測試自動化

## 參與者
- **Dev-Developer**：協助測試實作
- **QA-Tester (Quincy)**：驗收測試與品質驗證

## 選用參與者
- **QA-Web-Tester**：Web 前端測試（跨瀏覽器、視覺回歸）
- **QA-Mobile-Tester**：行動端測試（Android/iOS/macOS、Appium/Espresso/XCTest）
- **Security-Engineer**：安全測試（SAST/DAST/依賴掃描）
- **Performance-Engineer**：效能/負載測試（k6/JMeter）
- **DevOps-Engineer**：測試環境建置與 CI/CD 整合

---


---

## SDD SCG 閘門整合（v0.01）

> 測試策略在 SCG-3（Contract Freeze）後制定，RTM 100% 覆蓋是 SCG-5 必要條件。

| 步驟 | 對應 SCG 閘門 | 強制產出 |
|------|-------------|---------|
| 測試策略制定 | SCG-3 通過後 | Test Strategy Spec（測試金字塔） |
| Contract Testing | **SCG-4 準備** | Contract Test Cases（基於凍結 Contract） |
| 驗收測試設計 | **SCG-4 準備** | AC-XXX-Y → TC-XXX-Y 完整覆蓋 |
| RTM 100% 達標 | **🔴 SCG-5 凍結** | RTM Coverage = 100% |

**🔷 整合閘門**：SCG-3 後（測試設計）→ SCG-4（Contract Testing）→ SCG-5（RTM 100%）
**📌 SDD CI/CD 規格**：參考 `cicd/SDD_TESTING_CICD.md`


# 執行步驟

## 步驟 1：測試策略制定 (40-60 分鐘)
**執行者**：QA-Lead

**作業內容**：
1. 設計測試金字塔
2. 選擇測試工具
3. 規劃測試範圍
4. 設定測試覆蓋率目標

**確認點** 🔴：測試策略確認
- 審查測試金字塔
- 確認工具選擇
- 確認覆蓋率目標

**產出**：測試策略文件、工具選擇、覆蓋率目標

## 步驟 2：測試案例設計 (1-1.5 小時)
**執行者**：QA-Lead + QA-Automation

**作業內容**：
1. 設計單元測試案例
2. 設計 API 測試案例
3. 設計 E2E 測試案例
4. 設計效能測試案例
5. 設計安全性測試案例

**確認點** 🔴：測試案例確認
- 審查測試案例清單
- 確認覆蓋完整性

**產出**：測試案例清單、測試腳本範例

## 步驟 3：測試自動化實施 (1-1.5 小時)
**執行者**：QA-Automation + Dev

**作業內容**：
1. 設定測試框架
2. CI/CD 整合
3. 測試資料管理
4. Mock 和 Stub 設計

**確認點** 🔴：自動化實施確認

**產出**：測試自動化框架、CI/CD 整合配置

## 步驟 4：測試環境管理 (30-40 分鐘)
**執行者**：QA-Automation + DevOps

**作業內容**：
1. 設計環境隔離策略
2. Docker Compose 測試環境
3. 測試資料準備
4. 環境配置管理

**產出**：測試環境配置、Docker Compose 文件

## 步驟 5：測試報告與改進 (30 分鐘)
**執行者**：QA-Lead

**作業內容**：
1. 設計測試報告格式
2. 配置測試結果儀表板
3. 建立持續改進機制
4. Flaky Tests 管理

**產出**：測試報告模板、改進計畫

---

# 輸出與交付

## 主要交付物
- 測試策略文件
- 測試案例清單
- 測試自動化框架
- 測試環境配置
- 測試報告模板

## 交付標準
- 覆蓋率達標 (≥80%)
- 自動化程度高
- 測試穩定可靠

---

## 📚 參考資源

- [Testing SOP 完整版](../../scenarios/testing/SOP.md)
- [Testing QuickRef 快速參考](../../scenarios/testing/SOP_QuickRef.md)
- [Testing DeepDive 深度指南](../../scenarios/testing/SOP_DeepDive.md)
- [Testing 快速啟動指令集](../../prompts/scenario-prompts/testing-prompts.md)
- [AISDLC_INIT.md](../../AISDLC_SDD_INIT.md)

### 相關 Agents
- [qa-lead-zh.yaml](../../agent/specialized/qa-lead-zh.yaml) - QA Lead（主導）
- [qa-automation-zh.yaml](../../agent/specialized/qa-automation-zh.yaml) - QA Automation（自動化測試）
- [dev-developer-zh.yaml](../../agent/core/06.dev-developer-zh.yaml) - David（測試實作支援）
- [qa-tester-zh.yaml](../../agent/core/07.qa-tester-zh.yaml) - Quincy（驗收測試）
- [qa-web-tester-zh.yaml](../../agent/specialized/qa-web-tester-zh.yaml) - Web QA（選用）
- [qa-mobile-tester-zh.yaml](../../agent/specialized/qa-mobile-tester-zh.yaml) - Mobile QA（選用）
- [security-engineer-zh.yaml](../../agent/specialized/security-engineer-zh.yaml) - Security Engineer（選用）
- [performance-engineer-zh.yaml](../../agent/specialized/performance-engineer-zh.yaml) - Performance Engineer（選用）
- [devops-engineer-zh.yaml](../../agent/specialized/devops-engineer-zh.yaml) - DevOps Engineer（選用）

### 相關 Skills
- `/testing-strategy` - 測試策略設計、測試金字塔建立
- `/qa-testing` - 測試計畫、驗收測試、測試案例撰寫
- `/security-audit` - 安全測試（OWASP Top 10）
- `/performance-optimization` - 效能基準測試、負載測試
- `/devops-github-actions` - GitHub Actions CI 測試整合
- `/devops-docker` - Docker 測試環境建置
- `/devops-monitoring` - 測試指標監控
- `/code-review` - 程式碼審查與測試品質
- `/integration-database` - 資料庫測試（PostgreSQL）
- `/mobile-development` - 行動端測試（涉及 Android/iOS/macOS 時）

---

**版本**：v0.01
**維護者**：AISDLC Framework Team
**最後更新**：2026-04-17
