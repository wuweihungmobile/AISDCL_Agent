# Migration Planning Flow
# 技術棧遷移規劃流程

## 🔒 強制執行配置
```yaml
workflow_metadata:
  id: "migration-planning-flow"
  version: "v0.01"
  priority: "HIGH"
  scenario_applicable: ["migration"]

agent_binding:
  primary:
    - agent/core/05.sd-architect-zh.yaml
    - agent/core/04.sa-analyst-zh.yaml
  supporting:
    - agent/specialized/code-analyzer-zh.yaml
    - agent/core/02.ba-business-analyst-zh.yaml
    - agent/core/03.pm-po-agent-zh.yaml
    - agent/specialized/dev-senior-zh.yaml
    - agent/core/06.dev-developer-zh.yaml
    - agent/core/07.qa-tester-zh.yaml
    - agent/specialized/devops-engineer-zh.yaml
  optional:
    - agent/specialized/sd-mobile-architect-zh.yaml
    - agent/specialized/qa-mobile-tester-zh.yaml
    - agent/specialized/security-engineer-zh.yaml
    - agent/specialized/integration-specialist-zh.yaml
    - agent/specialized/performance-engineer-zh.yaml
  rules_enforcement: MANDATORY
  auto_load: true

workflow_priority: AGENT_RULES_FIRST
```

## Workflow 名稱
**migration-planning-flow** - 技術棧遷移規劃與執行流程

## 描述
針對全技術棧遷移（前端/後端/DB 框架替換）、資料庫平台遷移、系統現代化的完整規劃流程。包含現況分析、架構設計、DB 遷移、後端遷移、前端遷移、新平台開發、驗證測試、部署切換和知識沉澱。

## 適用場景
- ✅ 全技術棧遷移（前端+後端+DB 全面替換）
- ✅ 資料庫平台遷移（如 Oracle→PostgreSQL）
- ✅ 系統現代化 + 新平台擴展（Android/macOS）
- ❌ 不適用：同技術棧代碼改善 → 請用 [refactoring-planning-flow](./refactoring-planning-flow.md)
- ❌ 不適用：僅單層框架替換 → 請用 [refactoring-planning-flow](./refactoring-planning-flow.md)

## 前置條件
- AISDLC_INIT.md 已載入
- 情境識別為 `migration`
- 舊系統代碼庫可存取
- `devops-setup-flow` (Step 0 + 0.5 + 0.6 + 0.7 + 0.8 + 0.9 + 0.10) - 🔒 Layer 0 + Layer 1 + Migration Pipeline + 🛡️ Security Integration (Advanced) + ⚡ Performance Benchmark (選配) + 📝 Doc Pipeline (選配) + 🔔 Agent Notification (強制) 已配置

---


---

## SDD SCG 閘門整合（v0.01）

> Migration 使用 MCM（Migration Compatibility Matrix）確保零停機遷移規格先行。

| 步驟 | 對應 SCG 閘門 | 強制產出 |
|------|-------------|---------|
| 遷移評估與規格 | **SCG-0 準備** | 遷移需求規格（MCM 初版） |
| 遷移架構設計 | **🔴 SCG-2 凍結** | 遷移 C4 + ADR（雙軌策略） |
| API 相容性設計 | **🔴 SCG-3 凍結** | API-COMPAT 聲明 + 廢棄期計畫 |
| 遷移驗證 | **SCG-5 準備** | MCM Validate 通過 |

**🔷 整合閘門**：SCG-0（遷移規格）→ SCG-2（遷移架構）→ SCG-3（API 相容）→ SCG-5（驗證）
**📌 SDD CI/CD 規格**：參考 `cicd/SDD_MIGRATION_CICD.md`


---

## SDD SCG 閘門整合（v0.01）

> Migration 使用 MCM（Migration Compatibility Matrix）確保零停機遷移規格先行。

| 步驟 | 對應 SCG 閘門 | 強制產出 |
|------|-------------|---------|
| 遷移評估與規格 | **SCG-0 準備** | 遷移需求規格（MCM 初版） |
| 遷移架構設計 | **[SCG-2 凍結]** | 遷移 C4 + ADR（雙軌策略） |
| API 相容性設計 | **[SCG-3 凍結]** | API-COMPAT 聲明 + 廢棄期計畫 |
| 遷移驗證 | **SCG-5 準備** | MCM Validate 通過 |

**整合閘門**：SCG-0（遷移規格）-> SCG-2（遷移架構）-> SCG-3（API 相容）-> SCG-5（驗證）
**SDD CI/CD 規格**：參考 `cicd/SDD_MIGRATION_CICD.md`

## 流程步驟

### Step 1: 情境識別與 Agent 載入
**執行者**: System
**輸入**: 使用者遷移需求描述

1. 識別為 `migration` 情境
2. 載入 Primary Agents: SD-Architect + SA-Analyst
3. 載入 Supporting Agents（依階段按需載入）

🔴 **確認點**: 確認遷移範圍（全棧/部分/僅 DB）

---

### Step 2: 舊系統全面分析
**執行者**: SA + Code-Analyzer + Performance-Engineer
**對應 SOP**: 階段 1

1. 前端分析（頁面/元件/路由/狀態管理/UI 庫）
2. 後端分析（API 端點/Service/Middleware/排程）
3. 資料庫分析（Schema/SP/View/Trigger/資料量）
4. 業務邏輯提取（計算邏輯/驗證規則/狀態流轉）
5. 效能基準線建立（回應時間/吞吐量/資源使用率）

**產出**: 舊系統分析報告 + 效能基準線

🔴 **確認點**: 分析結果完整性確認

---

### Step 3: 遷移架構設計
**執行者**: SD-Architect (Lead) + Dev-Senior + PM/PO
**對應 SOP**: 階段 2

1. 技術棧映射表（舊→新逐項對應）
2. 遷移策略選擇（分層漸進/Strangler/Big Bang）
3. 並行運行架構設計
4. 遷移順序與優先級排定
5. 時程估算與 ROI 評估

**產出**: 遷移映射報告 + 遷移架構圖

🔴 **確認點**: 技術棧映射 + 遷移策略 + 並行運行方案確認

---

### Step 4: 資料庫遷移規劃
**執行者**: SD + Dev-Senior
**對應 SOP**: 階段 3
**觸發 Skill**: `/database-migration`

1. Schema 轉換（資料型別映射）
2. SQL 語法轉換
3. Stored Procedure 遷移策略決策
4. 資料遷移步驟規劃（靜態→動態→增量同步）
5. 遷移工具選型

**產出**: DB 遷移計畫

🔴 **確認點**: DB 遷移計畫確認

---

### Step 5: 後端遷移規劃
**執行者**: SD + Dev-Senior + QA
**對應 SOP**: 階段 4

1. API 契約定義（RESTful 端點映射）
2. Service 層功能替換映射
3. 認證/授權機制遷移
4. 中介層/排程任務對應

**產出**: 後端遷移設計文檔

🔴 **確認點**: API 契約確認

---

### Step 6: 前端遷移規劃
**執行者**: SD + Dev-Senior
**對應 SOP**: 階段 5

1. 元件映射表
2. 狀態管理遷移
3. 路由系統映射
4. UI 元件庫替代方案
5. 頁面遷移優先順序

**產出**: 前端遷移設計文檔

🔴 **確認點**: 前端遷移計畫確認

---

### Step 7: 新平台開發規劃（條件觸發）
**執行者**: SD-Mobile-Architect + Integration-Specialist
**對應 SOP**: 階段 6
**觸發條件**: 遷移涉及新增行動端/桌面端平台
**觸發 Skill**: `/mobile-development`

1. 行動端架構設計（原生 vs 跨平台）
2. 共用 API 設計
3. 硬體整合規格（掃碼/NFC）
4. 離線支援策略

**產出**: 行動端架構設計文檔

🔴 **確認點**: 行動端方案確認

---

### Step 8: 驗證與測試規劃
**執行者**: QA (Lead) + Code-Analyzer + Performance-Engineer
**對應 SOP**: 階段 7

1. DB 遷移驗證計畫
2. 跨系統一致性驗證
3. 效能基準對比計畫
4. 行動端驗證計畫
5. 部署驗證計畫

**產出**: 遷移驗證測試計畫

🔴 **確認點**: 測試計畫確認

---

### Step 9: 部署與切換規劃
**執行者**: DevOps + SD
**對應 SOP**: 階段 8
**觸發 Skill**: `/devops-github-actions`, `/release-management`

> **🔴 v0.01 CI/CD 強化**: Migration 情境需要完整 4 層 Pipeline（L0+L1+L2+L3）。

1. CI/CD Pipeline 建立（4 層架構）:
   - Layer 0: Security Baseline（強制）
   - Layer 1: Build & Verify（新棧+舊棧 Dual-Build）
   - Layer 2: Contract Test（API 相容性）+ Performance Comparison
   - Layer 3: Canary Deploy（5%→25%→50%→100%）+ Rollback Gate
2. Rollback 腳本與 DB Rollback SQL 建立
3. Canary 部署配置（漸進式流量切換）
4. 並行運行啟動（雙寫驗證機制）
5. 監控告警設定（錯誤率 > 1% 自動回滾）
6. 舊系統退役計畫（Expand-Contract Pattern）

**配置範本**: [Migration_Pipeline_Template.md](../../docs_template/scenario_specific/devops/Migration_Pipeline_Template.md)
**產出**: 部署切換計畫 + Canary 配置 + Rollback 腳本

🔴 **確認點**: 部署方案確認（含 Canary 閾值、Rollback 機制驗證）

---

### Step 10: 知識沉澱
**執行者**: Technical-Writer + SD
**對應 SOP**: 階段 9

1. 遷移映射手冊
2. 架構決策記錄 (ADR)
3. 經驗教訓文檔
4. 新技術棧開發規範

**產出**: 知識文檔包

---

## SOP-Workflow 步驟對照表

| Workflow Step | SOP 階段 | 主要 Agent | 觸發 Skill |
|--------------|---------|-----------|-----------|
| Step 1 | 情境識別 | System | - |
| Step 2 | 階段 1: 現況分析 | SA + CodeX + PerfEng | `/brownfield-analysis` |
| Step 3 | 階段 2: 架構設計 | SD (Lead) | `/sd-architect` |
| Step 4 | 階段 3: DB 遷移 | SD + DevSr | `/database-migration` |
| Step 5 | 階段 4: 後端遷移 | SD + DevSr + QA | `/integration-api-client` |
| Step 6 | 階段 5: 前端遷移 | SD + DevSr | `/dev-review` |
| Step 7 | 階段 6: 新平台 | MobileArch + IntSpec | `/mobile-development` |
| Step 8 | 階段 7: 測試驗證 | QA (Lead) | `/testing-strategy` |
| Step 9 | 階段 8: 部署切換 | DevOps + SD | `/devops-github-actions` |
| Step 10 | 階段 9: 知識沉澱 | TechWriter + SD | - |

---

## 相關文檔
- [Migration SOP](../../scenarios/migration/SOP.md)
- [Migration QuickRef](../../scenarios/migration/SOP_QuickRef.md)
- [Migration Pipeline Template](../../docs_template/scenario_specific/devops/Migration_Pipeline_Template.md) - Canary + Rollback Pipeline 配置
- [DevOps Setup Flow](./devops-setup-flow.md) - Pipeline 建置流程（Step 0 ~ 0.10）
- [Migration 快速啟動指令集](../../prompts/scenario-prompts/migration-prompts.md)
- [Refactoring DeepDive Part 11 - 技術棧遷移深度指南](../../scenarios/refactoring/SOP_DeepDive.md)

---

**版本**: v0.01
**最後更新**: 2026-04-17
