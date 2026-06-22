# Core Agents — 載入說明與 SDD 角色

**框架版本**: AISDLC-SDD v0.18
**最後更新**: v0.18

---

## 7 個 Core Agents

| 檔案 | Agent 角色 | SDD 主要職責 |
|------|-----------|------------|
| `01.agent-template-zh.yaml` | Agent 模板 | 新建 Agent 的基礎模板 |
| `02.ba-business-analyst-zh.yaml` | 業務分析師 | 利害關係人管理、需求驗證、業務對齊 |
| `03.pm-po-agent-zh.yaml` | PM/PO | 產品規劃、Sprint 管理、MVP 定義 |
| `04.sa-analyst-zh.yaml` | SA 分析師 | 需求提取、**逆向規格工程**、Gap Analysis、Invariants 提取 |
| `05.sd-architect-zh.yaml` | SD 架構師 | 系統設計、**As-Is/To-Be SRD**、C4 圖、**ADR 生成** |
| `06.dev-developer-zh.yaml` | 開發工程師 | 代碼實作、Spec-First 遵從、SCG-4 驗證 |
| `07.qa-tester-zh.yaml` | QA 測試師 | **RTM 生成**、**Invariant Test Contract**、RTM 覆蓋率支援（SCG-5 閘門 owner：qa-lead） |

---

## SDD 特殊職責（SDD v0.01 新增）

### SA 分析師（04）— SDD 核心
- **逆向規格工程**：從既有代碼/系統提取規格（Brownfield 必用）
- **Gap Analysis**：As-Is vs To-Be 差距分析
- **Invariants 提取**：識別 Business Invariants（INV-XXX）
- **SCG-0 驗證**：確認 PRD/FRD 完整性

### SD 架構師（05）— SDD 核心
- **As-Is SRD**：現有系統架構文件化
- **ADR 生成**：每個技術決策必須有 ADR（`adr-generate` skill）
- **C4 Model**：Context + Container + Component 架構圖
- **SCG-1~2 驗證**：設計凍結 + 架構凍結

### QA 測試師（07）— SDD 核心
- **RTM 生成**：需求追蹤矩陣（F-XXX → TC-XXX）
- **Invariant Test Contract**：Invariant 保護測試合約
- **RTM 100% 覆蓋**：產出 RTM 供 SCG-5 閘門驗證（SCG-5 RTM Completeness Gate 之 owner 為 qa-lead）

---

## 載入規則

### 基本載入（所有情境）
框架初始化時自動載入所有 7 個 Core Agents：
```
AISDLC_SDD_INIT.md 的 auto_load_config.primary_agents
```

### 情境特化載入
根據場景，以下 Core Agents 會被指定為主要 Agent：

| 情境 | Primary Core Agent |
|------|-------------------|
| Greenfield | SA 04 + SD 05 + PM 03 |
| Brownfield | SA 04 + SD 05 |
| Refactoring | SA 04 + Dev 06 + QA 07 |
| Documentation | SD 05（ADR）+ QA 07（RTM）|
| Testing | QA 07 |
| 其他情境 | 依場景 Enhancement 文件說明 |

---

## 參考

- Specialized Agents：[../specialized/README.md](../specialized/README.md)
- 完整 Agent 使用指南：[../../guides/system/agent/](../../guides/system/agent/)
- 場景 Agent 對應表：[../../scenarios/SCENARIO_AGENT_MAPPING.md](../../scenarios/SCENARIO_AGENT_MAPPING.md)
