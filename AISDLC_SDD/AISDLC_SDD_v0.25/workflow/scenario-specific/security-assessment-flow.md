# Security Assessment Flow
# 安全評估與合規檢查流程

## Workflow 名稱
**security-assessment-flow** - 安全評估與合規完整流程

## 描述
建立完整的安全體系，包含威脅建模、漏洞掃描、安全架構設計、安全加固實施、合規檢查和安全文檔交付。

## 適用場景
- **使用時機**：安全評估、合規檢查、安全加固、滲透測試後改善
- **適用專案**：需要安全認證（ISO 27001/SOC2/PCI-DSS/GDPR）或處理敏感資料的專案
- **執行頻率**：專案初期建立，定期覆核（季度/年度）

## 觸發條件
- 專案需求已明確且涉及敏感資料處理
- 系統架構已確定
- 合規標準已識別

---

# 角色與責任

## 主要負責人
**Agent 角色**：Security-Engineer + Compliance-Officer
**責任**：安全評估與設計、合規差距分析與稽核準備

## 參與者
- **QA-Lead**：安全測試策略與規劃
- **SA (Amanda)**：需求分析、威脅建模資料流圖
- **SD (Marcus)**：安全架構設計、加密策略
- **Dev-Senior**：安全加固實施、漏洞修復
- **DevOps-Engineer**：安全 CI/CD Pipeline 建置

## 選用參與者
- **BA (Beatrice)**：業務合規需求分析（金融/醫療/電商法規）
- **PM/PO (Victoria)**：安全預算和優先級決策
- **Technical-Writer**：安全文檔與合規報告撰寫
- **QA-Web-Tester**：Web 前端安全測試（XSS/CSRF/CSP 驗證）
- **QA-Mobile-Tester**：行動端安全測試（Android/iOS/macOS）
- **SD-Mobile-Architect**：行動端安全架構設計

---


---

## SDD SCG 閘門整合（v0.01）

> 安全設計使用 STRIDE 威脅模型，必須在架構凍結前完成，才能進入 SCG-2。

| 步驟 | 對應 SCG 閘門 | 強制產出 |
|------|-------------|---------|
| STRIDE 威脅建模 | **SCG-1 準備** | STRIDE 分析報告 + Trust Boundary Map |
| 安全架構設計 | **🔴 SCG-2 凍結** | 安全 ADR + 安全架構文件 |
| 安全測試設計 | SCG-3 通過後 | 安全測試案例（基於 STRIDE） |
| 安全驗收 | **🔴 SCG-5 準備** | STRIDE 所有威脅已緩解 |

**🔷 整合閘門**：SCG-1（STRIDE）→ SCG-2（安全架構凍結）→ SCG-5（安全驗收）
**📌 SDD CI/CD 規格**：參考 `cicd/SDD_SECURITY_CICD.md`


# 執行步驟

## 步驟 1：安全評估與合規分析 (1-2 天)
**執行者**：Security-Engineer + Compliance-Officer + SA

**作業內容**：
1. 情境確認與範圍界定
2. 威脅建模（STRIDE 方法）
3. 安全漏洞掃描（SAST/DAST/SCA）
4. 合規差距分析（GDPR/PCI-DSS/SOC2）
5. 風險評級與優先排序（CVSS）

**確認點** 🔴：安全評估範圍與威脅優先級確認
- 審查資料流圖完整性
- 確認信任邊界劃分
- 確認 STRIDE 威脅識別全面性
- 確認風險等級評估

**產出**：安全評估報告、威脅模型、合規檢查清單

## 步驟 2：安全需求與架構設計 (1-2 天)
**執行者**：Security-Engineer + SD-Architect + DevOps-Engineer

**作業內容**：
1. 安全需求文件制定
2. 安全架構設計（Zero Trust）
3. 認證授權方案（OAuth 2.0/OIDC）
4. 加密策略（傳輸中/靜態）
5. 安全 CI/CD Pipeline 設計

**確認點** 🔴：安全架構設計確認
- 審查安全架構圖
- 確認認證授權方案
- 確認加密策略

**產出**：安全需求文件、安全架構圖、CI/CD 安全配置

## 步驟 3：安全實施與修復 (2-5 天)
**執行者**：Dev-Senior + Security-Engineer + DevOps-Engineer

**作業內容**：
1. OWASP Top 10 漏洞修復
2. 安全加固實施（輸入驗證、存取控制）
3. 安全 CI/CD Pipeline 建置（SAST/DAST/SCA）
4. 容器安全（Golden Image、Trivy 掃描）
5. 安全配置（HTTPS、Security Headers、CSP）

**確認點** 🔴：安全實施確認
- 審查修復完整性
- 確認 CI/CD 安全 Pipeline 正常運作

**產出**：修復後程式碼、安全 CI/CD 配置、安全加固報告

## 步驟 4：安全測試與驗證 (1-3 天)
**執行者**：QA-Lead + Security-Engineer

**作業內容**：
1. 安全測試策略制定
2. 滲透測試（OWASP ZAP / Burp Suite）
3. 漏洞修復驗證
4. 合規檢查項驗證
5. 安全回歸測試

**確認點** 🔴：安全測試結果確認
- 審查漏洞掃描報告
- 確認 Critical/High 漏洞已全部修復
- 確認合規檢查項通過

**產出**：安全測試報告、漏洞修復驗證、合規驗證結果

## 步驟 5：文檔與交付 (0.5-1 天)
**執行者**：Security-Engineer + Compliance-Officer

**作業內容**：
1. 安全評估報告定稿
2. 合規報告撰寫
3. 安全架構文檔交付
4. 持續監控計畫制定

**產出**：安全評估報告、合規報告、安全架構文檔、監控計畫

---

# 輸出與交付

## 主要交付物
- 安全評估報告（Security Assessment Report）
- 威脅模型（Threat Model）
- 安全需求文件（Security Requirements Document）
- 合規檢查清單（Compliance Checklist）
- 安全測試計畫與報告（Security Test Plan & Report）
- 修復計畫（Remediation Plan）
- 安全架構圖（Security Architecture Diagram）
- 合規報告（Compliance Report）

## 交付標準
- Critical 漏洞數量: 0
- High 漏洞數量: ≤ 5（有緩解措施）
- 敏感資料加密率: 100%
- 合規檢查項完成度: ≥ 95%

---

## 📚 參考資源

- [Security SOP 完整版](../../scenarios/security/SOP.md)
- [Security QuickRef 快速參考](../../scenarios/security/SOP_QuickRef.md)
- [Security DeepDive 深度指南](../../scenarios/security/SOP_DeepDive.md)
- [Security 快速啟動指令集](../../prompts/scenario-prompts/security-prompts.md)
- [AISDLC_INIT.md](../../AISDLC_SDD_INIT.md)

### 相關 Agents
- [security-engineer-zh.yaml](../../agent/specialized/security-engineer-zh.yaml) - Security Engineer（主導）
- [compliance-officer-zh.yaml](../../agent/specialized/compliance-officer-zh.yaml) - Compliance Officer（合規審查）
- [qa-lead-zh.yaml](../../agent/specialized/qa-lead-zh.yaml) - QA Lead（安全測試策略）
- [04.sa-analyst-zh.yaml](../../agent/core/04.sa-analyst-zh.yaml) - Amanda（威脅建模）
- [05.sd-architect-zh.yaml](../../agent/core/05.sd-architect-zh.yaml) - Marcus（安全架構設計）
- [dev-senior-zh.yaml](../../agent/specialized/dev-senior-zh.yaml) - Dev Senior（安全加固）
- [devops-engineer-zh.yaml](../../agent/specialized/devops-engineer-zh.yaml) - DevOps（安全 CI/CD）
- [qa-web-tester-zh.yaml](../../agent/specialized/qa-web-tester-zh.yaml) - Web QA（選用）
- [qa-mobile-tester-zh.yaml](../../agent/specialized/qa-mobile-tester-zh.yaml) - Mobile QA（選用）
- [sd-mobile-architect-zh.yaml](../../agent/specialized/sd-mobile-architect-zh.yaml) - Mobile Architect（選用）
- [technical-writer-zh.yaml](../../agent/specialized/technical-writer-zh.yaml) - Technical Writer（選用）

### 相關 Skills
- `/security-audit` - OWASP Top 10 安全審計
- `/compliance-audit` - GDPR/PCI-DSS/SOC2 合規審查
- `/sd-architect` - 安全架構設計
- `/code-review` - 安全程式碼審查
- `/qa-testing` - 安全測試策略
- `/testing-strategy` - 安全測試金字塔
- `/integration-oauth` - OAuth 2.0/OIDC 認證
- `/integration-database` - 資料庫安全配置（PostgreSQL）
- `/integration-redis` - Session/Token 安全快取
- `/devops-github-actions` - 安全 CI/CD Pipeline
- `/devops-docker` - 容器安全（Golden Image）
- `/devops-monitoring` - 安全事件監控
- `/performance-optimization` - 安全措施效能評估
- `/mobile-development` - 行動端安全（Android/macOS）

---

**版本**：v0.01
**維護者**：AISDLC Framework Team
**最後更新**：2026-04-17
