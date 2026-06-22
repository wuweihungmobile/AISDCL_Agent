# Documentation Reconstruction Flow
# 文檔重建流程

## 強制執行配置
```yaml
workflow_metadata:
  id: "documentation-reconstruction-flow"
  version: "v0.01"
  priority: "HIGH"
  scenario_applicable: ["brownfield", "refactoring", "documentation"]

agent_binding:
  primary:
    - agent/specialized/code-analyzer-zh.yaml
    - agent/specialized/technical-writer-zh.yaml
  supporting:
    - agent/core/04.sa-analyst-zh.yaml
    - agent/core/05.sd-architect-zh.yaml
    - agent/core/06.dev-developer-zh.yaml
    - agent/specialized/dev-senior-zh.yaml
  optional:
    - agent/core/07.qa-tester-zh.yaml
    - agent/specialized/devops-engineer-zh.yaml
  rules_enforcement: MANDATORY
  auto_load: true

workflow_priority: AGENT_RULES_FIRST
```

## Workflow 名稱
**documentation-reconstruction-flow** - 既有系統文檔重建流程

## 描述
針對缺乏文檔或文檔嚴重過時的既有系統，透過代碼分析、逆向工程和知識萃取，重建系統架構文檔、API 文檔、資料庫 Schema 文檔等核心技術文件。此流程是 Brownfield 和 Refactoring 情境的前置作業，確保在進行系統改造前建立充分的文檔基線。

## 適用場景
- **使用時機**：既有系統缺乏文檔、文檔嚴重過時、接手他人系統、系統改造前置準備
- **適用專案**：Legacy 系統、文檔缺失的維護專案、Brownfield/Refactoring 前置作業
- **執行頻率**：按需執行（通常在 Brownfield/Refactoring SOP Stage 1 觸發）

## 觸發條件
- 既有系統的文檔缺失或嚴重過時
- Brownfield SOP Stage 1 發現文檔不足
- 接手缺乏文檔的系統
- 系統代碼庫可存取

---

# 角色與責任

## 主要負責人
**Agent 角色**：Code-Analyzer + Technical-Writer
**責任**：代碼分析與架構逆向、文檔產出與結構化

## Supporting Agents（依階段載入）
- **SA (System Analyst)**：Step 2 - 業務邏輯還原與功能盤點
- **SD (Architect)**：Step 3 - 架構圖繪製與技術棧評估
- **Dev (Developer)**：Step 4 - 代碼註解補充與 API 端點確認
- **Dev-Senior**：Step 2 - 複雜代碼邏輯分析

## Optional Agents（按需載入）
- **QA**：需同步重建測試文檔時
- **DevOps**：需重建部署文檔時

---


---

## SDD SCG 閘門整合（v0.01）

> 文件重建是 Brownfield 的逆向規格工程，目標是從代碼重建 SCG-0 所需的規格文件。

| 步驟 | 對應 SCG 閘門 | 強制產出 |
|------|-------------|---------|
| 代碼逆向分析 | **SCG-0 準備** | 逆向 FRD 草稿 |
| 架構重建 | **SCG-1 準備** | As-Is SRD + C4 現況圖 |
| ADR 考古 | **SCG-2 準備** | ADR Archaeology 結果 |
| 文件驗證 | **🔴 SCG-0 凍結** | 逆向規格文件（人工確認後凍結） |

**🔷 整合閘門**：SCG-0（逆向規格）→ SCG-1（架構重建）→ SCG-2（決策補建）
**📌 SDD 規則**：參考 `scenarios/brownfield/SDD_BROWNFIELD_ENHANCEMENT.md`


---

## SDD SCG 閘門整合（v0.01）

> 文件重建是 Brownfield 的逆向規格工程，目標是從代碼重建 SCG-0 所需的規格文件。

| 步驟 | 對應 SCG 閘門 | 強制產出 |
|------|-------------|---------|
| 代碼逆向分析 | **SCG-0 準備** | 逆向 FRD 草稿 |
| 架構重建 | **SCG-1 準備** | As-Is SRD + C4 現況圖 |
| ADR 考古 | **SCG-2 準備** | ADR Archaeology 結果 |
| 文件驗證 | **[SCG-0 凍結]** | 逆向規格文件（人工確認後凍結） |

**整合閘門**：SCG-0（逆向規格）-> SCG-1（架構重建）-> SCG-2（決策補建）
**SDD 規則**：參考 `scenarios/brownfield/SDD_BROWNFIELD_ENHANCEMENT.md`

# 執行步驟

## 步驟 1：文檔現況盤點 (30-40 分鐘)
**執行者**：Technical-Writer + SA
**建議 Skill**：`/brownfield-analysis`、`/sa-analyst`

**作業內容**：
1. 盤點現有文檔清單（README、Wiki、註解、歷史文件）
2. 評估每份文檔的完整度與時效性
3. 識別完全缺失的關鍵文檔
4. 建立文檔重建優先級清單

**文檔完整度評估矩陣**：
| 文檔類型 | 狀態 | 完整度 | 時效性 | 重建優先級 |
|---------|------|--------|--------|-----------|
| 系統架構文檔 | 存在/缺失/過時 | 0-100% | 最後更新日期 | P1/P2/P3 |
| API 文檔 | 存在/缺失/過時 | 0-100% | 最後更新日期 | P1/P2/P3 |
| 資料庫 Schema | 存在/缺失/過時 | 0-100% | 最後更新日期 | P1/P2/P3 |
| 部署文檔 | 存在/缺失/過時 | 0-100% | 最後更新日期 | P1/P2/P3 |
| 業務邏輯說明 | 存在/缺失/過時 | 0-100% | 最後更新日期 | P1/P2/P3 |

**確認點** 🔴：文檔盤點結果確認
- 確認文檔現況評估正確
- 確認重建優先級排序
- 決定本次重建範圍

**產出**：文檔現況盤點報告、重建優先級清單

## 步驟 2：代碼逆向分析 (1-2 小時)
**執行者**：Code-Analyzer + Dev-Senior
**建議 Skill**：`/brownfield-analysis`、`/refactoring-code-quality`

**作業內容**：
1. 掃描代碼庫結構，識別模組邊界
2. 分析模組間依賴關係（使用 dependency-cruiser / Madge）
3. 識別入口點（API routes、Controllers、main 函數）
4. 提取資料模型定義（ORM models、Schema、migrations）
5. 識別第三方服務整合點
6. 分析設定檔與環境變數

**逆向分析工具建議**：
| 分析目標 | 建議工具 | 產出 |
|---------|---------|------|
| 模組依賴 | dependency-cruiser, Madge | 依賴關係圖 |
| API 端點 | Swagger 註解掃描, 路由分析 | API 清單 |
| DB Schema | ORM 反向工程, pg_dump --schema-only | Schema 文件 |
| 代碼結構 | tree, cloc, SonarQube | 結構概覽 |

**確認點** 🔴：逆向分析結果確認
- 驗證模組邊界識別正確
- 確認依賴關係完整
- 補充分析工具未能偵測的隱性依賴

**產出**：模組清單、依賴關係圖、API 端點清單、資料模型清單

## 步驟 3：架構文檔重建 (1-1.5 小時)
**執行者**：SD (Architect) + Technical-Writer
**建議 Skill**：`/sd-architect`、`/documentation-api`

**作業內容**：
1. 繪製系統架構圖（C4 Model - Context + Container 層級）
2. 記錄技術棧清單與版本
3. 描述各模組職責與互動方式
4. 記錄外部整合點（第三方 API、訊息佇列等）
5. 記錄部署拓撲（如可取得）

**C4 Model 重建層級**：
- **Level 1 (Context)**：系統邊界、外部使用者、外部系統
- **Level 2 (Container)**：應用程式、資料庫、訊息佇列、檔案儲存
- **Level 3 (Component)**：各 Container 內部主要模組（視複雜度選擇性繪製）

**確認點** 🔴：架構文檔確認
- 驗證架構圖與實際系統一致
- 確認技術棧資訊正確
- 補充架構圖未涵蓋的資訊

**產出**：系統架構文檔（含 C4 架構圖）、技術棧清單

## 步驟 4：API 與資料庫文檔重建 (1-1.5 小時)
**執行者**：Dev + Technical-Writer
**建議 Skill**：`/documentation-api`、`/integration-database`

**作業內容**：
1. 整理 API 端點清單（路徑、方法、參數、回應格式）
2. 從代碼提取 Request/Response 範例
3. 匯出資料庫 Schema 並加註說明
4. 記錄表之間的關聯關係（ER Diagram）
5. 識別資料流向（哪些 API 操作哪些表）

**API 文檔重建格式**：
```
端點: [METHOD] /api/v1/resource
描述: [從代碼推導的功能說明]
參數: [從 Controller/Handler 提取]
回應: [從 Response DTO/Serializer 提取]
認證: [從 Middleware 推導]
來源: [代碼檔案路徑與行號]
```

**確認點** 🔴：API 與資料庫文檔確認
- 驗證 API 清單完整
- 確認 Schema 描述正確
- 補充業務含義說明

**產出**：API 文檔、資料庫 Schema 文檔、ER Diagram

## 步驟 5：文檔整合與品質檢查 (30-40 分鐘)
**執行者**：Technical-Writer + SA
**建議 Skill**：`/code-review`

**作業內容**：
1. 整合所有重建的文檔到統一結構
2. 檢查文檔間的交叉引用一致性
3. 標註「推導」與「確認」的資訊（區分逆向推導 vs 人工確認）
4. 建立文檔維護指引
5. 建立文檔更新日誌

**文檔可信度標註**：
| 標記 | 含義 | 說明 |
|------|------|------|
| `[已確認]` | 經人工驗證 | 與實際系統行為一致 |
| `[推導]` | 從代碼逆向推導 | 高度可信但未經完整驗證 |
| `[待驗證]` | 需要進一步確認 | 可能不完整或有歧義 |

**確認點** 🔴：最終文檔確認
- 審查文檔完整性
- 確認可信度標註正確
- 確認文檔可作為後續工作基線

**產出**：完整文檔包、文檔維護指引

---

# 輸出與交付

## 主要交付物
- 文檔現況盤點報告
- 系統架構文檔（含 C4 架構圖）
- API 文檔
- 資料庫 Schema 文檔（含 ER Diagram）
- 模組依賴關係圖
- 文檔維護指引

## 交付標準
- 架構圖與實際系統一致
- API 文檔涵蓋所有已識別端點
- 資料模型描述完整
- 所有資訊標註可信度等級
- 文檔結構符合 AISDLC 模板規範

---

# 品質控制
- 所有確認點必須完成
- 零臆測原則：不確定的資訊必須標註 `[待驗證]`
- 文檔與代碼版本對應
- 交叉引用一致性

---

# 相關資源

## 相關 Workflow
- [Brownfield Analysis Flow](brownfield-analysis-flow.md) - 既有系統分析與變更流程
- [Documentation Flow](documentation-flow.md) - 一般技術文檔撰寫流程
- [Code Analysis Flow](code-analysis-flow.md) - 代碼分析流程
- [Consistency Check](../core/consistency-check.md) - 文檔一致性檢查

## 相關 SOP
- [Brownfield SOP](../../scenarios/brownfield/SOP.md) - Stage 1 文檔缺失時觸發
- [Refactoring SOP](../../scenarios/refactoring/SOP.md) - Stage 1 現況分析前置
- [Documentation SOP](../../scenarios/documentation/SOP.md) - 文檔情境完整 SOP

## 相關模板
- [Legacy System Analysis](../../docs_template/scenario_specific/analysis/Legacy_System_Analysis_Template.md) - 既有系統分析模板
- [Gap Analysis](../../docs_template/scenario_specific/analysis/Gap_Analysis_Template.md) - 差距分析模板

## 建議 Skill
- `/brownfield-analysis` - 既有系統分析
- `/documentation-api` - API 文檔生成
- `/sa-analyst` - 需求分析
- `/sd-architect` - 架構設計
- `/refactoring-code-quality` - 代碼品質分析

**版本**：v0.01
**最後更新**：2026-04-17
