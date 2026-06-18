# Documentation Flow
# 技術文檔撰寫流程

## Workflow 名稱
**documentation-flow** - 技術文檔完整撰寫流程

## 描述
建立完整的技術文檔體系，包含文檔規劃、內容撰寫、範例程式碼、視覺化、審查、版本管理，以及安全與合規文檔（選用）。

## 適用場景
- **使用時機**：專案啟動、文檔建立、文檔更新
- **適用專案**：所有需要技術文檔的專案
- **執行頻率**：專案初期建立，持續維護

## 觸發條件
- 專案需要技術文檔
- 系統架構已確定
- API 設計已完成

---

# 角色與責任

## 主要負責人
**Agent 角色**：Technical-Writer + SD
**責任**：文檔架構設計、內容撰寫

## 參與者
- **SA**：需求文檔協助
- **Dev-Senior**：程式碼範例提供、技術審查 ⭐
- **Security-Engineer**：安全文檔撰寫（選用）
- **Compliance-Officer**：合規文檔撰寫（選用）
- **SD-Mobile-Architect**：行動端安全文檔（選用）

---


---

## SDD SCG 閘門整合（v0.01）

> Documentation 流程確保所有 SDD 文件符合 SCG 閘門標準，達到 RTM 100% 覆蓋。

| 步驟 | 對應 SCG 閘門 | 強制產出 |
|------|-------------|---------|
| 需求文件審查 | **SCG-4 準備** | FRD 與實作一致性確認 |
| 測試文件更新 | **SCG-5 準備** | RTM 100% + 測試案例完整 |
| 架構文件同步 | **SCG-5 準備** | ADR 更新 + C4 圖同步 |
| 發布文件 | **🔴 SCG-6 凍結** | Living Documentation 更新 |

**🔷 整合閘門**：SCG-4（文件與實作一致）→ SCG-5（RTM 完整）→ SCG-6（發布文件）
**📌 SDD 規則**：參考 `scenarios/documentation/SDD_DOCUMENTATION_ENHANCEMENT.md`


# 執行步驟

## 步驟 1：文檔現況盤點與規劃 (40-60 分鐘)
**執行者**：Technical-Writer + SD

**作業內容**：
1. 設計文檔架構
2. 識別目標讀者
3. 規劃文檔類型
4. 建立文檔標準
5. **識別是否需要安全與合規文檔**

**確認點** 🔴：文檔架構確認
- 審查文檔結構
- 確認目標讀者
- 確認文檔類型
- **確認是否觸發安全合規文檔階段**

**產出**：文檔架構設計、文檔標準

## 步驟 2：核心文檔撰寫 (1.5-2 小時)
**執行者**：Technical-Writer

**作業內容**：
1. 撰寫 README
2. 生成 API 文檔
3. 撰寫架構文檔（C4 Model）
4. 撰寫 ADR（架構決策記錄）

**確認點** 🔴：核心文檔確認
- 審查 README
- 審查 API 文檔
- 審查架構文檔

**產出**：README、API 文檔、架構文檔、ADR

## 步驟 3：開發者指南與範例 (1 小時)
**執行者**：Technical-Writer + Dev-Senior

**作業內容**：
1. 撰寫 Getting Started
2. 撰寫開發指南
3. 提供程式碼範例
4. 撰寫 API 使用範例

**確認點** 🔴：開發者指南確認

**產出**：Getting Started、開發指南、程式碼範例

## 步驟 4：故障排除與 FAQ (30-40 分鐘)
**執行者**：Technical-Writer + DevOps

**作業內容**：
1. 撰寫 Troubleshooting Guide
2. 建立 FAQ
3. 撰寫常見問題解決方案
4. 提供日誌查看指引

**產出**：Troubleshooting Guide、FAQ

## 步驟 5：文檔維護與版本管理 (20-30 分鐘)
**執行者**：Technical-Writer

**作業內容**：
1. 建立文檔更新流程
2. 設定版本管理
3. 建立 CHANGELOG
4. 設定文檔審查機制

**產出**：文檔維護指南、CHANGELOG 模板

## 步驟 6：安全與合規文檔 (選用, 1-2 小時)
**執行者**：Technical-Writer + Security-Engineer + Compliance-Officer

> **⚠️ 觸發條件**：專案涉及敏感資料、合規要求、安全認證、多平台部署時執行

**作業內容**：
1. 撰寫安全架構文檔（認證、授權、加密策略）
2. 建立威脅模型（STRIDE 分析）
3. 繪製資料流圖（標示敏感資料保護點）
4. 撰寫合規對照表（法規要求 vs 實施措施）
5. 撰寫行動端安全文檔（如涉及 Mobile）
6. 建立安全文檔維護計畫

**確認點** 🔴：安全與合規文檔確認
- 安全架構文檔涵蓋認證、授權、加密
- 威脅模型覆蓋主要攻擊面
- 合規對照表對應適用法規
- 多平台安全文檔完整（如適用）

**產出**：安全架構文檔、威脅模型、合規對照表、資料流圖、安全測試計畫

---

# 輸出與交付

## 主要交付物
- 文檔架構
- README
- API 文檔
- 開發者指南
- 架構文檔
- Troubleshooting Guide
- 安全與合規文檔（選用）

## 交付標準
- 文檔完整
- 易於理解
- 範例可執行
- 持續更新
- 安全文檔涵蓋 OWASP Top 10（如適用）
- 合規文檔對應適用法規（如適用）

---

## 📚 參考資源

- [Documentation SOP 完整版](../../scenarios/documentation/SOP.md)
- [Documentation QuickRef 快速參考](../../scenarios/documentation/SOP_QuickRef.md)
- [Documentation DeepDive 深度指南](../../scenarios/documentation/SOP_DeepDive.md)
- [Documentation 快速啟動指令集](../../prompts/scenario-prompts/documentation-prompts.md)
- [AISDLC_INIT.md](../../AISDLC_SDD_INIT.md)

### 相關 Agents
- [technical-writer-zh.yaml](../../agent/specialized/technical-writer-zh.yaml) - Technical Writer（主導）
- [04.sa-analyst-zh.yaml](../../agent/core/04.sa-analyst-zh.yaml) - Amanda（需求文檔審查）
- [05.sd-architect-zh.yaml](../../agent/core/05.sd-architect-zh.yaml) - Marcus（架構文檔審查）
- [dev-senior-zh.yaml](../../agent/specialized/dev-senior-zh.yaml) - Dev Senior（程式碼範例、技術審查）
- [security-engineer-zh.yaml](../../agent/specialized/security-engineer-zh.yaml) - Security Engineer（選用）
- [compliance-officer-zh.yaml](../../agent/specialized/compliance-officer-zh.yaml) - Compliance Officer（選用）
- [sd-mobile-architect-zh.yaml](../../agent/specialized/sd-mobile-architect-zh.yaml) - Mobile Architect（選用）
- [07.qa-tester-zh.yaml](../../agent/core/07.qa-tester-zh.yaml) - Quincy（文檔驗收，選用）
- [devops-engineer-zh.yaml](../../agent/specialized/devops-engineer-zh.yaml) - DevOps（Docs as Code，選用）

### 相關 Skills
- `/documentation-api` - API 文檔生成（OpenAPI/Swagger）
- `/sa-analyst` - 需求文檔分析
- `/sd-architect` - 架構文檔（C4 Model）
- `/code-review` - 程式碼範例品質審查
- `/integration-database` - 資料庫文檔（PostgreSQL）
- `/integration-oauth` - 認證授權文檔（OAuth 2.0）
- `/devops-github-actions` - Docs as Code CI/CD Pipeline
- `/devops-docker` - 部署文檔（Docker 環境）
- `/security-audit` - 安全架構文檔（選用）
- `/compliance-audit` - 合規對照文檔（選用）
- `/mobile-development` - 行動端文檔（選用）
- `/qa-testing` - 文檔驗收測試

---

**版本**：v0.01
**維護者**：AISDLC Framework Team
**最後更新**：2026-04-17
