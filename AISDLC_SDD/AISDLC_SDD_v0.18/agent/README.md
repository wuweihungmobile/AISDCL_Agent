# AISDLC Agent 配置目錄

本目錄包含 AISDLC 框架的所有 Agent 配置檔案。

## 📂 目錄結構

```
agent/
├── core/                              # 核心 Agent (中文版 - 主要維護)
│   ├── 01.agent-template-zh.yaml
│   ├── 02.ba-business-analyst-zh.yaml
│   ├── 03.pm-po-agent-zh.yaml
│   ├── 04.sa-analyst-zh.yaml
│   ├── 05.sd-architect-zh.yaml
│   ├── 06.dev-developer-zh.yaml
│   ├── 07.qa-tester-zh.yaml
│   └── README.md
├── specialized/                        # 專業化 Agent (中文版)
│   ├── code-analyzer-zh.yaml
│   ├── compliance-officer-zh.yaml
│   ├── dev-senior-zh.yaml
│   ├── devops-engineer-zh.yaml
│   ├── integration-specialist-zh.yaml
│   ├── performance-engineer-zh.yaml
│   ├── qa-automation-zh.yaml
│   ├── qa-lead-zh.yaml
│   ├── qa-mobile-tester-zh.yaml
│   ├── qa-web-tester-zh.yaml
│   ├── sd-mobile-architect-zh.yaml
│   ├── sd-web-architect-zh.yaml
│   ├── sdd-diagnostic-zh.yaml          # 系統級 runtime agent
│   ├── sdd-evaluator-zh.yaml           # 系統級 runtime agent
│   ├── sdd-gc-zh.yaml                  # 系統級 runtime agent
│   ├── sdd-orchestrator-zh.yaml        # 系統級 runtime agent
│   ├── sdd-playbook-compiler-zh.yaml   # 系統級 runtime agent
│   ├── security-engineer-zh.yaml
│   ├── technical-writer-zh.yaml
│   └── README.md
├── AGENT_COLLABORATION_PATTERNS.md
├── AGENT_PHASE2_UPDATE_GUIDE.md
└── README.md (本檔案)
```

## 🎯 維護策略

### ✅ 主要維護版本：中文版

- **位置**：`core/*-zh.yaml`、`specialized/*-zh.yaml`
- **狀態**：**主要維護版本，所有更新在此進行**
- **使用者**：所有開發團隊（主要為中文使用者）
- **更新頻率**：隨框架演進持續更新

### 📦 英文版備份說明

> **SDD v0.01 設計決策**：`backup_en/` 目錄已從 SDD v0.01 中刻意移除。
> SDD 框架僅維護中文版 Agent（`*-zh.yaml`），英文版備份不再包含於此框架中。
> 如需英文版參考，請查閱 `AISDLC_v0.09/agent/` 目錄（歷史版本保留）。

## 📋 核心 Agent 清單 (Core Agents)

所有核心 Agent 均已包含 Phase 2 擴充內容 (v0.03-phase2)：

| # | 檔案 | 名稱 | 角色 | 情境使用頻率 | 不可替代性 |
|---|------|------|------|------------|-----------|
| 1 | 01.agent-template-zh.yaml | Template | Agent 模板 | - | - |
| 2 | 02.ba-business-analyst-zh.yaml | Beatrice | 業務分析師 | Medium (4/10) | ⭐⭐⭐⭐⭐ |
| 3 | 03.pm-po-agent-zh.yaml | Victoria | 產品經理/產品負責人 | Medium (5/10) | ⭐⭐⭐⭐ |
| 4 | 04.sa-analyst-zh.yaml | Amanda | 系統分析師 | High (10/10) | ⭐⭐⭐⭐⭐ |
| 5 | 05.sd-architect-zh.yaml | Marcus | 系統設計師/架構師 | High (9/10) | ⭐⭐⭐⭐⭐ |
| 6 | 06.dev-developer-zh.yaml | David | 軟體開發者 | Medium-High (7/10) | ⭐⭐⭐⭐⭐ |
| 7 | 07.qa-tester-zh.yaml | Quincy | 品質保證工程師 | High (7/10) | ⭐⭐⭐⭐⭐ |

## 🔧 專業化 Agent (Specialized Agents)

提供特定領域的專業能力，依需求選用。**v0.09 起全部中文化 (`-zh.yaml`)**。
共 **19 個 Specialized（14 persona/specialized + 5 系統級 runtime）**：

### 開發專業化
- `dev-senior-zh.yaml` - 資深開發者 (Senior)
- `code-analyzer-zh.yaml` - 代碼分析師 (CodeX)

### 架構專業化
- `sd-web-architect-zh.yaml` - Web 架構師 (WebArch)
- `sd-mobile-architect-zh.yaml` - Mobile 架構師 (MobileArch)

### QA 專業化
- `qa-lead-zh.yaml` - QA 主管 (QA-Lead)
- `qa-automation-zh.yaml` - 自動化測試工程師 (AutoQA)
- `qa-web-tester-zh.yaml` - Web 測試工程師 (WebQA)
- `qa-mobile-tester-zh.yaml` - Mobile 測試工程師 (MobileQA)

### 其他專業化
- `devops-engineer-zh.yaml` - DevOps 工程師 (DevOps)
- `security-engineer-zh.yaml` - 安全工程師 (SecEng)
- `performance-engineer-zh.yaml` - 效能工程師 (Perf)
- `integration-specialist-zh.yaml` - 整合專家 (IntegX)
- `technical-writer-zh.yaml` - 技術文件撰寫員 (DocX)
- `compliance-officer-zh.yaml` - 合規專員 (CompOff)

### 系統級 Runtime Agent
- `sdd-orchestrator-zh.yaml` - SDD 閉環總指揮
- `sdd-diagnostic-zh.yaml` - 自癒診斷 Agent
- `sdd-evaluator-zh.yaml` - 執行接地評估器
- `sdd-gc-zh.yaml` - 鷹架 GC Agent
- `sdd-playbook-compiler-zh.yaml` - Playbook 編譯器

> **系統級 runtime agent 採 runtime schema（responsibilities/inputs/workflow/outputs），刻意不遵 persona 模板**——其由 FSM Runtime 在對應事件觸發時載入，非情境式 persona 角色。

> 📖 **選擇指南**: [guides/system/agent/Specialized_Agent_Selection_Guide.md](../guides/system/agent/Specialized_Agent_Selection_Guide.md)

## 📝 Agent 配置結構

每個 Agent YAML 檔案包含以下區塊：

### 1. 基本資訊 (agent)
- `name`: Agent 名稱
- `id`: 唯一識別 ID
- `title`: 職位頭銜
- `icon`: 代表圖示
- `whenToUse`: 使用時機
- `customization`: 客製化設定

### 2. Phase 2: 協作模式與情境使用 (v0.03-phase2)
- `collaboration_patterns`: 協作模式定義
  - `primary_patterns`: 主要協作模式
  - `supporting_patterns`: 支援性協作模式
- `scenario_usage`: 情境使用說明
  - `frequency`: 使用頻率
  - `irreplaceability`: 不可替代性評級
  - `primary_scenarios`: 主要情境
  - `supporting_scenarios`: 支援性情境
  - `notes`: 補充說明

### 3. 人格設定 (persona)
- `role`: 角色定位
- `style`: 工作風格
- `identity`: 身份認同
- `focus`: 工作重點
- `core_principles`: 核心原則

### 4. 文檔責任 (document_responsibilities)
- `primary_documents`: 主要負責文檔
- `collaborative_documents`: 協作參與文檔
- `quality_standards`: 品質標準

### 5. 支援的工作流程 (supported_workflows)
- `primary_workflows`: 主要工作流程
- `supporting_workflows`: 支援的工作流程

### 6. 協作規則 (collaboration_rules)
- `upstream_collaboration`: 上游協作
- `downstream_collaboration`: 下游協作
- `peer_collaboration`: 同級協作

### 7. 依賴項目 (dependencies)
- `data`: 數據文件
- `tasks`: 任務文件
- `templates`: 模板文件
- `checklists`: 檢查清單

## 🚀 使用指南

### 新增或修改 Agent

1. **使用模板**：複製 `01.agent-template-zh.yaml` 作為起點
2. **填寫欄位**：根據註釋指導填寫所有必要欄位
3. **Phase 2 內容**：確保包含協作模式和情境使用定義
4. **測試整合**：驗證與 AISDLC 工作流程的整合
5. **文檔更新**：更新本 README 的 Agent 清單

### 引用 Agent

在工作流程或其他配置中引用 Agent：

```yaml
# 引用核心 Agent (中文版)
agent: "../agent/core/04.sa-analyst-zh.yaml"

# 引用專業化 Agent (中文版)
agent: "../agent/specialized/qa-automation-zh.yaml"
```

### 選擇合適的 Agent

參考以下指標：

- **使用頻率**：該 Agent 在多少情境中被使用
- **不可替代性**：該 Agent 的核心價值和重要性
- **協作模式**：該 Agent 如何與其他 Agent 協作
- **主要情境**：該 Agent 在哪些情境中扮演關鍵角色

## 📚 相關文檔

- `AGENT_COLLABORATION_PATTERNS.md` - Agent 協作模式詳細說明
- `AGENT_PHASE2_UPDATE_GUIDE.md` - Phase 2 更新指南
- `../AISDLC_SDD_INIT.md` - AISDLC-SDD 框架初始化與 Agent 載入配置

## 🔄 版本歷史

### v0.01-SDD (2026-04-16)
- ✅ 全框架升級為 AISDLC-SDD v0.01（Spec-First Design）
- ✅ 所有 Specialized Agents `agent.version` 更新為 `v0.01`
- ✅ Core Agents（04.sa-analyst, 05.sd-architect）template_path 修正至 `docs_template/core/`
- ✅ 新增 SDD 技能：逆向規格工程、Gap Analysis、Invariants 提取、STRIDE 驅動、PBS Gate
- ✅ 支援 10 個 SDD 場景（新增 devops/integration/migration/performance/security/testing）

### v0.09 (2026-03-20)
- ✅ 所有 Specialized Agents 完成中文化 (`-zh.yaml`)
- ✅ `archive_en/` 重命名為 `backup_en/`（core 和 specialized）
- ✅ 模板檔名更新：`01.agent-template-zh_OK.yaml` → `01.agent-template-zh.yaml`
- ✅ 新增十大情境完整 Agent 自動載入配置（含 migration 情境）

### v0.06 (2025-10-30)
- ✅ 補全所有核心 Agent 的 Phase 2 內容
- ✅ 將英文版移至 `backup_en/` 作為歷史參考
- ✅ 確立中文版為主要維護版本
- ✅ 所有 Agent 行數與英文版對齊 (包含 Phase 2)

### v0.03 (Phase 2)
- 新增 Phase 2: Collaboration Patterns & Scenario Usage
- 新增 14 個專業化 Agent

### v0.02
- 建立 specialized/ 目錄結構

### v0.01
- 初始版本，7 個核心 Agent

## ❓ 常見問題

### Q: 為什麼改為只維護中文版？

A: 主要使用者為中文團隊，維護單一語言版本可以：
- 降低維護成本
- 避免版本不一致
- 專注於功能改進而非翻譯同步

### Q: 還能找到英文版嗎？

A: SDD v0.01 已刻意移除 `backup_en/` 目錄（設計決策：僅維護中文版降低維護成本）。如需英文版參考，請查閱歷史版本 `AISDLC_v0.09/agent/core/backup_en/` 和 `AISDLC_v0.09/agent/specialized/backup_en/`。

### Q: Specialized Agents 都有中文版嗎？

A: 是的！v0.09 起所有 14 個 persona/specialized Agents 均已中文化（`-zh.yaml` 後綴），與核心 Agent 保持一致。另有 5 個系統級 runtime agent（`sdd-*`，採 runtime schema），合計 19 個 Specialized（計數見上方第 71 行與 FRAMEWORK_STATUS.md）。

### Q: 如何貢獻新的 Agent？

A:
1. 使用 `01.agent-template-zh.yaml` 作為模板
2. 填寫完整的 Phase 2 內容
3. 確保與現有 Agent 的協作關係定義清楚
4. 提交 Pull Request 並更新本 README

---

**維護者**：AISDLC Framework Team
**最後更新**：v0.18
**版本**：v0.18
