# Brownfield Analysis Flow
# 舊專案分析與改造流程

## 🔒 強制執行配置
```yaml
workflow_metadata:
  id: "brownfield-analysis-flow"
  version: "v0.01"
  priority: "HIGH"
  scenario_applicable: ["brownfield"]

agent_binding:
  primary:
    - agent/core/04.sa-analyst-zh.yaml
    - agent/specialized/dev-senior-zh.yaml
  supporting:
    - agent/specialized/code-analyzer-zh.yaml
    - agent/core/05.sd-architect-zh.yaml
    - agent/core/02.ba-business-analyst-zh.yaml
    - agent/core/03.pm-po-agent-zh.yaml
    - agent/core/07.qa-tester-zh.yaml
    - agent/core/06.dev-developer-zh.yaml
    - agent/specialized/devops-engineer-zh.yaml
  optional:
    - agent/specialized/integration-specialist-zh.yaml
    - agent/specialized/sd-mobile-architect-zh.yaml
    - agent/specialized/qa-mobile-tester-zh.yaml
    - agent/specialized/compliance-officer-zh.yaml
  rules_enforcement: MANDATORY
  auto_load: true

workflow_priority: AGENT_RULES_FIRST
```

## Workflow 名稱
**brownfield-analysis-flow** - 既有系統分析與變更實施流程

## 描述
針對既有系統進行功能改進、Bug 修復或技術改造的完整流程。包含代碼分析、影響評估、變更設計、相容性檢查、測試和部署。支援跨平台（Web/Mobile/Desktop）、合規驅動變更、功能停用等情境。

## 適用場景
- **使用時機**：既有系統功能增強、Bug 修復、技術升級、功能停用、跨平台擴展、合規變更
- **適用專案**：Legacy 系統改造、維護專案、漸進式升級
- **執行頻率**：按需執行（每次變更需求）

## 觸發條件
- 收到變更需求（Bug report / Feature request / Change request）
- 收到功能停用/刪除需求（Deprecation request）
- 收到合規/法規驅動變更需求
- 系統代碼庫可存取
- 變更目標和範圍明確

---

# 角色與責任

## 主要負責人
**Agent 角色**：SA (System Analyst) + Dev-Senior
**責任**：現況分析、需求提取、影響分析、技術評審、代碼分析、方案設計

## Supporting Agents（依階段載入）
- **Code-Analyzer**：Stage 2 - 代碼理解與架構分析
- **SD (Architect)**：Stage 4 - 變更設計與技術方案（新增功能或架構變更時）
- **BA (Business Analyst)**：Stage 3 - 業務邏輯變更的影響驗證
- **PM/PO**：Stage 3 - 變更優先級決策與商業價值評估
- **QA**：Stage 6 - 測試策略與測試計畫
- **Dev (Developer)**：Stage 10 - Sprint 執行與開發測試
- **DevOps**：Stage 8 - 部署方案與回滾計畫

## Optional Agents（按需載入）
- **Integration Specialist**：涉及第三方整合或硬體整合時
- **SD-Mobile-Architect**：平台識別為 Mobile 時
- **QA-Mobile-Tester**：涉及 Mobile 平台測試時
- **Compliance Officer**：涉及法規合規需求時

---


---

## SDD SCG 閘門整合（v0.01）

> Brownfield 情境以逆向規格工程為核心，SCG-0 基於 As-Is 現況分析。

| 步驟 | 對應 SCG 閘門 | 強制產出 |
|------|-------------|---------|
| 現況系統分析 | **SCG-0 準備** | As-Is SRD（現況規格化） |
| Gap Analysis | **SCG-0/1 準備** | GAP-ANALYSIS + Tech Debt 清單 |
| To-Be 架構設計 | **🔴 SCG-1 凍結** | To-Be SRD + Before/After 對比 |
| 架構遷移計畫 | **🔴 SCG-2 凍結** | C4（Before/After）+ ADR |
| API 相容性設計 | **🔴 SCG-3 凍結** | API-COMPAT 聲明 + 廢棄期 |

**🔷 整合閘門**：SCG-0（As-Is）→ SCG-1（Gap）→ SCG-2（To-Be 架構）→ SCG-3（API 相容）
**📌 SDD 規則**：參考 `scenarios/brownfield/SDD_BROWNFIELD_ENHANCEMENT.md`


---

## SDD SCG 閘門整合（v0.01）

> Brownfield 情境以逆向規格工程為核心，SCG-0 基於 As-Is 現況分析。

| 步驟 | 對應 SCG 閘門 | 強制產出 |
|------|-------------|---------|
| 現況系統分析 | **SCG-0 準備** | As-Is SRD（現況規格化） |
| Gap Analysis | **SCG-0/1 準備** | GAP-ANALYSIS + Tech Debt 清單 |
| To-Be 架構設計 | **[SCG-1 凍結]** | To-Be SRD + Before/After 對比 |
| 架構遷移計畫 | **[SCG-2 凍結]** | C4（Before/After）+ ADR |
| API 相容性設計 | **[SCG-3 凍結]** | API-COMPAT 聲明 + 廢棄期 |

**整合閘門**：SCG-0（As-Is）-> SCG-1（Gap）-> SCG-2（To-Be 架構）-> SCG-3（API 相容）
**SDD 規則**：參考 `scenarios/brownfield/SDD_BROWNFIELD_ENHANCEMENT.md`

# 執行步驟

## 步驟 1：代碼理解與架構分析 (1-1.5 小時)
**執行者**：Code-Analyzer + SA
**建議 Skill**：`/brownfield-analysis`、`/sa-analyst`

**作業內容**：
1. 掃描代碼庫結構
2. 識別技術棧和框架
3. 分析模組相依性
4. 評估代碼品質
5. 識別 technical debt
6. **平台識別**：判斷變更是否涉及 Mobile/Desktop/硬體/合規

**平台識別與 Agent 推薦**：
| 平台/情境 | 觸發條件 | 推薦載入 Agent |
|-----------|---------|---------------|
| Mobile (Android/iOS) | 涉及行動應用 | sd-mobile-architect + qa-mobile-tester |
| 硬體整合 | 涉及條碼掃描/IoT | integration-specialist |
| 合規驅動 | 法規/會計準則變更 | compliance-officer |

**確認點** 🔴：架構理解確認
- 驗證架構分析正確性
- 確認平台識別結果與 Agent 推薦
- 補充背景資訊

**產出**：系統架構分析報告、代碼品質評估、平台識別報告

## 步驟 2：變更範圍界定與影響分析 (40-60 分鐘)
**執行者**：SA + Code-Analyzer + BA
**建議 Skill**：`/brownfield-analysis`、`/refactoring-code-quality`

**作業內容**：
1. 分析需修改的檔案
2. 識別影響的模組
3. 評估資料層影響
4. 檢查 API 相容性
5. 識別風險點（含合規風險、業務驗證風險、歷史資料影響）

**確認點** 🔴：影響範圍確認
- 審查影響分析結果
- 確認風險評估

**產出**：影響分析報告、風險矩陣、變更範圍文件

## 步驟 3：變更方案設計 (1-1.5 小時)
**執行者**：Dev-Senior + SD
**建議 Skill**：`/sd-architect`、`/integration-api-client`

**作業內容**：
1. 設計最小變更方案
2. 設計平衡改進方案
3. 評估重構可能性
4. 提供程式碼範例
5. 設計資料遷移方案（如需要）
6. 設計功能停用策略（如適用）

**確認點** 🔴：方案選擇確認
- 審查方案對比
- 選定實施方案
- 確認時程

**產出**：技術設計文件、實作計畫、資料遷移方案

## 步驟 4：相容性檢查 (30-40 分鐘)
**執行者**：SA + Dev-Senior
**建議 Skill**：`/sa-analyst`、`/compliance-audit`

**作業內容**：
1. 檢查向下相容性
2. 檢查依賴服務影響
3. 設計版本管理策略
4. 規劃 breaking changes 處理
5. 合規驗證（如適用）

**確認點** 🔴：相容性確認
- 審查相容性分析
- 確認緩解措施

**產出**：相容性分析報告、版本管理策略

## 步驟 5：測試策略規劃 (40-60 分鐘)
**執行者**：QA + QA-Automation
**建議 Skill**：`/qa-testing`、`/testing-strategy`

**作業內容**：
1. 設計單元測試
2. 規劃整合測試
3. 設計回歸測試範圍
4. 準備測試資料
5. 設計自動化測試
6. 跨平台整合測試（如適用）

**確認點** 🔴：測試計畫確認
- 審查測試覆蓋
- 確認測試案例

**產出**：測試計畫、測試案例清單、測試腳本

## 步驟 6：部署與回滾方案 (30-40 分鐘)
**執行者**：DevOps + Dev-Senior
**建議 Skill**：`/devops-github-actions`、`/devops-docker`、`/release-management`

**作業內容**：
1. 選擇部署策略
2. 設計部署步驟
3. 設計回滾計畫
4. 配置監控告警
5. 準備溝通計畫
6. Mobile App 發布流程（如適用：Android/macOS/iOS）

**確認點** 🔴：部署方案確認
- 審查部署流程
- 確認回滾可行性

**產出**：部署方案、回滾手冊、監控指標定義

---

# 輸出與交付

## 主要交付物
- 影響分析報告
- 技術設計文件
- 測試計畫
- 部署方案
- 回滾手冊
- 平台識別報告（如涉及跨平台）
- 功能停用計畫（如適用）

## 交付標準
- 影響評估完整
- 變更方案可行
- 測試覆蓋充分
- 部署方案安全
- 合規要求已驗證（如適用）

---

# 品質控制
- 所有確認點必須完成
- 零臆測原則
- 變更追蹤完整
- 回滾機制驗證

---

# 🔗 相關資源

## 相關 Workflow
- [Change Management](../core/change-management.md) - 變更管理流程
- [Sprint Execution](../core/sprint-execution.md) - 開發測試循環
- [Consistency Check](../core/consistency-check.md) - 文檔一致性檢查

## 相關 SOP
- [Brownfield SOP](../../scenarios/brownfield/SOP.md) - 完整 Brownfield 10 階段 SOP
- [SOP Quick Reference](../../scenarios/brownfield/SOP_QuickRef.md) - 快速參考

## 建議 Skill
- `/brownfield-analysis` - 既有系統分析
- `/sa-analyst` - 需求分析
- `/sd-architect` - 架構設計
- `/qa-testing` - 測試策略
- `/dev-review` - 代碼審查
- `/compliance-audit` - 合規審查
- `/release-management` - 發布管理

**版本**：v0.01
**最後更新**：2026-04-17
