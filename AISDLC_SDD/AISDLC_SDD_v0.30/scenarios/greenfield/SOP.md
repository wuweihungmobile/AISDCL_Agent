# Greenfield Project 新專案開發 SOP

**版本**: v0.01 | **最後更新**: 2026-04-01
**本版更新**：補充多領域 ID 命名空間預警（Stage 2）、企業級附加技術必填清單（Stage 3）、security-audit 雙階段觸發說明（Stage 5）、Mobile User Story 差異化 AC 撰寫指引（Stage 6）、合規驗收 Sprint 引導（Stage 7）、多語言 CI/CD 統一規範（Stage 8）、搜尋索引 MVP 漸進方案（Stage 8）、CIA 合規影響評估欄位（Stage 10）、Greenfield 早期 Breaking Change 決策指引（Stage 10）、手動追蹤鏈驗證替代方案（Stage 9）、Rolling Update 跨域 API 相容性保證機制（Stage 11）、Skills 表補充 integration-stripe/integration-webhook（基於 Greenfield QA 模擬測試 2026-03-29）、多領域 SRD 文件組織策略（Stage 5 5.2.1.4）、合規驗收 Sprint 具體拆分建議含 User Stories（Stage 7）（基於 Greenfield QA 模擬測試 2026-04-01）
> 📝 **關於範例連結說明**:
> 本 SOP 中部分連結（如文檔路徑、配置檔案等）為示例性質，
> 展示一般專案的文檔結構。實際使用時，請根據您的專案結構調整路徑。

## 🎯 情境概述

**適用場景**：從零開始的全新專案開發

**預計時間**:
- 📋 **AISDLC 規劃階段**: 3-5 天
  - **規劃時間** (AI 分析 + 人工確認): 3-5 天
  - **執行時間** (依專案規模):
    - 小型專案 (2-3人): 2-4 週
    - 中型專案 (5-10人): 1-3 個月
    - 大型專案 (10+人): 3-6 個月
- 🔨 **實際開發階段**: 1-6 個月 (依專案規模而定)

> 💡 **時間估算說明**:
> - **規劃時間**指使用 AISDLC 流程進行需求分析、架構設計、文檔產出的時間
> - **執行時間**指實際開發實施的時間，會因團隊規模、技術複雜度、需求變更而有很大差異
> - 小型專案通常指功能較單純的 MVP 或工具型應用
> - 中型專案指具備完整業務流程的應用系統
> - 大型專案指複雜的企業級系統或平台

**涉及角色**：PM/PO, SA, BA, SD-Architect, QA, Dev

**最終產出**：完整的 PRD/FRD/SRD + User Stories + Sprint 計畫 + 技術架構

---

## 🤝 協作模式 (Phase 2: v0.03)

### 主要協作模式

#### 1. Lead-Support (主導-支援)
- **主導 Agent**: PM/PO
- **支援 Agents**: SA, BA, SD, QA, Dev
- **使用階段**: 需求優先級決策、產品方向確認
- **模式說明**: PM/PO 主導產品決策，其他 Agents 提供專業建議和驗證

#### 2. Sequential-Handoff (順序交接)
- **流程**: PM/PO → 🔴 → SA → 🔴 → SD → 🔴 → Dev → 🔴 → QA
- **交接點**: PRD → FRD → SRD/API → Implementation → Testing
- **模式說明**: 文檔依序產出，每個交接點需人類確認

### 次要協作模式

#### 3. Peer-Review (同儕審查)
- **使用階段**: FRD 審查 (SA ↔ BA)、SRD 審查 (SD ↔ Dev)
- **模式說明**: 產出文檔後由相關 Agent 交叉審查

---

## 📋 前置準備檢查清單

### 必要材料
- [ ] 專案願景和目標描述
- [ ] 目標使用者群體資訊
- [ ] 核心功能需求描述 (可以是截圖、文字、或原型)
- [ ] 預算和時間限制
- [ ] 團隊技能盤點

### 選擇性材料
- [ ] 競品分析資料
- [ ] 設計稿或 UI 原型 (Figma/Adobe XD/截圖)
- [ ] 業務流程圖
- [ ] 現有系統說明 (如需整合)

---

## 🔧 材料缺失應對方案

> 💡 **現實情況**: 新專案啟動時常因資訊不完整而延遲。以下提供實用的替代方案。

| 缺失材料 | 影響程度 | 應對方案 | 預計額外時間 |
|---------|---------|---------|-------------|
| **專案願景和目標描述** | 🔴 高 | • **方案 1**: 與利害關係人進行願景工作坊,使用「北極星目標」方法<br>• **方案 2**: 參考競品和市場調研,推導潛在目標<br>• **方案 3**: 使用 PM/PO Agent 協助結構化願景訪談問題清單<br>• **方案 4**: 先定義 MVP 最小範圍,後續迭代補充願景 | +2-4 小時 |
| **目標使用者群體資訊** | 🔴 高 | • **方案 1**: 進行使用者訪談或問卷調查<br>• **方案 2**: 分析競品的目標使用者<br>• **方案 3**: 建立臨時 Persona (後續驗證調整)<br>• **方案 4**: 使用 BA Agent 協助設計使用者調研問卷 | +1-3 小時 |
| **核心功能需求描述** | 🔴 高 | • **方案 1**: 與需求提出者進行結構化訪談<br>• **方案 2**: 參考類似產品功能清單<br>• **方案 3**: 使用「User Story Mapping」工作坊<br>• **方案 4**: 先定義核心使用場景,再推導功能需求 | +2-4 小時 |
| **預算和時間限制** | 🟡 中 | • **方案 1**: 與管理層或投資方確認預算上限<br>• **方案 2**: 根據團隊規模和市場行情估算<br>• **方案 3**: 使用 T-shirt sizing (S/M/L/XL) 粗估<br>• **方案 4**: 先規劃 MVP,後續根據實際進度調整 | +0.5-1 小時 |
| **團隊技能盤點** | 🟡 中 | • **方案 1**: 進行團隊技能評估問卷<br>• **方案 2**: 檢視團隊過往專案經驗<br>• **方案 3**: 進行簡單技術測試或 Coding Challenge<br>• **方案 4**: 根據現有技能選擇技術棧,避免學習曲線 | +1-2 小時 |
| **競品分析資料** | 🟢 低 | • **方案 1**: 快速桌面調研 (Google 搜尋、產品官網)<br>• **方案 2**: 使用免費分析工具 (SimilarWeb、App Annie)<br>• **方案 3**: 暫時跳過,聚焦自身需求<br>• **方案 4**: 安排專人後續補充競品分析 | +0.5-1 小時 |
| **設計稿或 UI 原型** | 🟢 低 | • **方案 1**: 使用線框圖工具快速繪製 (Balsamiq、Excalidraw)<br>• **方案 2**: 參考類似產品 UI 作為參考<br>• **方案 3**: 先開發功能,後續補充 UI 設計<br>• **方案 4**: 使用 UI Kit 快速搭建原型 (Material UI、Ant Design) | +1-2 小時 |

### 需求完全模糊時的應對流程

若專案需求極度模糊,建議採用「**設計思考 (Design Thinking) 工作坊**」:

#### 階段 1: 同理 (Empathize) - 2-4 小時
1. **使用者訪談**
   - 訪談潛在使用者,了解痛點和需求
   - 記錄使用者故事和場景

2. **利害關係人對齊**
   - 召開 Kick-off Meeting
   - 對齊專案目標和成功標準

#### 階段 2: 定義 (Define) - 1-2 小時
1. **問題陳述**
   - 使用「How Might We」方法定義問題
   - 範例: "How might we 讓使用者更快完成訂單流程?"

2. **使用者 Persona**
   - 建立 2-3 個典型使用者角色
   - 定義使用者目標和行為模式

#### 階段 3: 發想 (Ideate) - 1-2 小時
1. **腦力激盪**
   - 團隊討論可能的解決方案
   - 不限制創意,鼓勵大膽想法

2. **優先級排序**
   - 使用 RICE 或 Kano 模型排序功能
   - 定義 MVP 範圍

#### 階段 4: 原型 (Prototype) - 2-4 小時
1. **低保真原型**
   - 使用紙筆或線框圖工具快速繪製
   - 聚焦核心流程,不糾結細節

2. **快速驗證**
   - 與利害關係人或使用者驗證原型
   - 收集回饋並調整

### 快速啟動策略 (時間緊迫時)

若時間極度緊迫,建議採用「**Lean Startup MVP 策略**」:

1. **定義核心假設** (30 分鐘)
   - 最重要的業務假設是什麼?
   - 最小可驗證的功能是什麼?

2. **快速原型** (4-8 小時)
   - 使用 No-Code/Low-Code 工具快速驗證
   - 或開發最簡單的功能原型

3. **快速驗證** (1-2 天)
   - 小範圍使用者測試
   - 收集回饋決定是否繼續

4. **迭代或轉向** (視回饋而定)
   - 若驗證成功,進入正式開發
   - 若驗證失敗,調整方向或中止專案

---

## 🛠️ 免費工具替代方案

> 💡 **成本考量**: 新專案開發常需使用專案管理、協作、設計、開發等工具，商業方案成本高昂（Jira $7-14/月/人, Figma $12-45/月/人）。以下提供功能相近的免費/開源替代方案。

### 新專案開發工具對照表

| 工具類別 | 商業方案 | 免費/開源替代 | 功能對比 | 適用場景 |
|---------|---------|-------------|---------|---------|
| **專案管理** | Jira<br>Asana<br>Monday.com | **Taiga**<br>**Plane**<br>**OpenProject** | 核心功能齊全<br>缺少: 進階報表、時間追蹤 | Sprint 規劃、User Story 管理<br>團隊協作、任務追蹤 |
| **原型設計** | Figma<br>Sketch<br>Adobe XD | **Penpot**<br>**Quant-UX**<br>**Figma Free** (3檔案) | 向量編輯完整<br>缺少: 進階協作功能 | UI/UX 設計<br>原型製作與測試 |
| **需求管理** | Aha!<br>ProductBoard | **Fibery**<br>**Notion**<br>**Obsidian + Plugin** | 免費版有限制<br>開源方案彈性高 | PRD/FRD 文檔管理<br>需求追蹤與版本控制 |
| **版本控制** | GitHub Teams<br>GitLab Premium | **GitHub Free**<br>**GitLab CE**<br>**Gitea** | 核心功能完全相同<br>免費版夠用 | 程式碼管理<br>分支策略、PR Review |
| **CI/CD** | CircleCI<br>Travis CI Pro | **GitHub Actions**<br>**GitLab CI**<br>**Drone CI** | 免費額度充足<br>(GitHub: 2000分鐘/月) | 自動化測試<br>自動化部署 |
| **API 設計** | Postman Teams<br>Insomnia Pro | **Postman Free**<br>**Hoppscotch**<br>**Swagger Editor** | 基本功能完整<br>缺少: 團隊協作 | API 規格設計<br>API 測試與文檔 |
| **資料庫設計** | DbSchema<br>Navicat | **DBeaver CE**<br>**dbdiagram.io**<br>**SchemaSpy** | 開源版功能完整 | ER Diagram 設計<br>資料庫模型管理 |
| **文檔協作** | Confluence<br>Notion Teams | **Notion Free**<br>**BookStack**<br>**Outline** | 免費版功能足夠<br>(Notion: 無頁數限制) | 技術文檔<br>知識庫管理 |

### 推薦工具組合 (依專案規模)

| 專案規模 | 專案管理 | 設計工具 | 版本控制 | CI/CD | 文檔協作 | 年度成本 |
|---------|---------|---------|---------|-------|---------|---------|
| **小型** (<5人) | Taiga / GitHub Projects | Figma Free / Penpot | GitHub Free | GitHub Actions | Notion Free | $0 |
| **中型** (5-20人) | Plane (自架) / Taiga | Penpot / Figma Free | GitLab CE (自架) | GitLab CI | BookStack | $0 (自架) |
| **大型** (20+人) | OpenProject / Plane | 混合使用 | GitHub Teams / GitLab | GitHub Actions | Confluence / Outline | $1k-5k/年 |

### 成本對比

| 方案 | 月度成本 (10人團隊) | 年度成本 | 工具組合 | 維護成本 |
|------|-------------------|---------|---------|---------|
| **完全免費 (雲端)** | $0 | $0 | GitHub + Taiga + Penpot + Notion | 低 (雲端服務) |
| **完全免費 (自架)** | $0 | $0 | GitLab CE + Plane + Penpot + BookStack | 中 (需DevOps維護) |
| **混合方案** | $50-150 | $600-1,800 | GitHub Teams + Figma + 其他免費 | 低-中 |
| **全商業方案** | $300-700 | $3,600-8,400 | Jira + Figma + Confluence + GitHub | 低 (廠商支援) |

### 各階段工具建議

#### 需求階段
- **需求收集**: Notion Free / Google Forms
- **原型設計**: Penpot / Figma Free / Excalidraw
- **流程圖**: Draw.io / Mermaid.js
- **訪談記錄**: Notion / Obsidian

#### 設計階段
- **UI 設計**: Penpot / Figma Free
- **協作白板**: Excalidraw / tldraw
- **設計系統**: Storybook (免費開源)
- **圖標資源**: Heroicons / Lucide Icons (免費)

#### 開發階段
- **IDE**: VS Code / IntelliJ CE
- **API 測試**: Hoppscotch / Postman Free
- **資料庫工具**: DBeaver CE / TablePlus (免費版)
- **除錯工具**: Chrome DevTools / React DevTools (免費)

#### 測試階段
- **單元測試**: Jest / Vitest / pytest (開源)
- **E2E 測試**: Playwright / Cypress (開源)
- **效能測試**: Lighthouse / WebPageTest (免費)
- **API 測試**: Hoppscotch / REST Client (VS Code)

---

## 🎯 Claude Code Skill 快速參考

> 💡 **使用方式**: 在 Claude Code 中輸入 `/skill-name` 即可啟動對應的專業 Skill。
> 每個階段建議使用的 Skill 如下表所示，可依需求靈活搭配。

| SOP 階段 | 建議啟動 Skill | 用途說明 |
|---------|---------------|---------|
| **階段 1** 啟動和情境確認 | `/pm-planning` | 產品規劃、專案範圍定義 |
| **階段 2** 需求提取與分析 | `/sa-analyst`、`/ba-analyst` | 需求分析、FRD 產出、利害關係人驗證 |
| **階段 3** 技術選型 | `/sd-architect` | 系統架構設計、技術棧評估 |
| **階段 4** 需求驗證與文件化 | `/sa-analyst`、`/qa-testing` | 需求文件化、驗收標準定義 |
| **階段 5** 架構設計 | `/sd-architect`、`/documentation-api`、`/security-audit`（🔴 金流/個資必做）| SRD 產出、API 規格設計、安全架構設計 |
| **階段 5** 涉及支付整合 | `/integration-stripe`（🔴 電商/民宿必用）| Stripe 支付流程、Webhook 設計 |
| **階段 6** User Story 撰寫 | `/sa-analyst`、`/sprint-planning` | User Story、Sprint 規劃 |
| **階段 7** Sprint 規劃 | `/sprint-planning`、`/pm-planning` | Sprint Backlog、工時估算 |
| **階段 8** 開發準備 | `/devops-github-actions`、`/devops-docker`、`/integration-database` | CI/CD Pipeline、Docker 容器化、資料庫整合 |
| **階段 8** 涉及 Webhook 整合 | `/integration-webhook`（涉及 Stripe/第三方 Webhook 必用）| Webhook 處理設計、靜默失敗防護 |
| **階段 9** 移交開發團隊 | `/dev-review`、`/code-review` | 開發 Kickoff、Code Review 標準建立 |
| **實施階段** 開發與測試 | `/dev-review`、`/qa-testing`、`/testing-strategy` | 代碼審查、測試策略、測試執行 |
| **部署階段** 部署準備 | `/devops-github-actions`、`/devops-docker`、`/security-audit`、`/release-management` | CI/CD 部署、安全掃描、版本發布 |

> ⚠️ **重要說明 - `/security-audit` 觸發時機**：
> - 🔴 **架構設計階段（Stage 5）**：涉及金流（Stripe）、個人資料（個資法/GDPR）、認證授權時，**必須在 Stage 5 完成 C4 Level 2 後立即觸發**，確保安全架構在早期就正確設計。
> - 🟡 **部署前（Stage 11）**：執行 OWASP ZAP 等動態安全掃描，補充架構審查。
> - ❌ 錯誤做法：只在部署前做安全審查 → 可能導致架構層面的安全問題需要大改。

### 其他可選 Skill（依專案需求）

| Skill | 適用場景 |
|-------|---------|
| `/performance-optimization` | 效能分析與優化 |
| `/security-audit` | 安全漏洞掃描與修復（Stage 5 架構設計 + Stage 11 部署前）|
| `/compliance-audit` | 🔴 旅宿業/金融/個資法合規審查（含合規業務必用）|
| `/refactoring-code-quality` | 代碼品質改善與技術債處理 |
| `/integration-oauth` | OAuth 2.0 認證整合 |
| `/integration-redis` | Redis 快取策略設計 |
| `/integration-stripe` | 🔴 Stripe 支付整合（電商/民宿必用，Stage 5 設計期介入）|
| `/integration-webhook` | 🔴 Webhook 處理設計（有第三方 Webhook 必用，Stage 8 介入）|
| `/mobile-development` | Android/iOS/macOS App 開發（Phase 2 行動端）|
| `/integration-api-client` | 多領域 API 客戶端建置（五合一系統多 API 整合，Stage 8 開發準備）|
| `/database-migration` | 多領域 DB Schema 版本管理（Flyway/Liquibase，Stage 5 架構設計 / Stage 8 開發準備）|
| `/brownfield-analysis` | 既有系統分析（整合場景適用）|
| `/release-management` | 版本發布流程管理 |

---

## 🚀 完整執行流程

### 📊 階段間依賴關係與執行順序 🆕

> 💡 **說明**: 以下為 11 個階段的依賴關係圖。各階段需按照依賴順序執行，
> 部分階段可並行執行以節省時間。

```
📋 階段依賴關係圖：

Stage 1: 啟動確認
    │
    ▼
Stage 2: 需求提取與分析 ──────────────────┐
    │                                      │
    │  ⚠️ 需求必須充分提取後才能技術選型      │
    ▼                                      │
Stage 3: 技術選型                           │
    │                                      │
    │  💡 技術選型與需求驗證可交互參考         │
    ▼                                      ▼
Stage 4: 需求驗證與文件化 (PRD/FRD) ◄──── 需求回饋
    │
    │  ⚠️ PRD/FRD 確認後才能進行架構設計
    ▼
Stage 5: 架構設計 (SRD/API/DB)
    │
    ▼
Stage 6: User Story 撰寫
    │
    ▼
Stage 7: Sprint 規劃 ──┐
    │                   │ 可並行
    ▼                   ▼
Stage 8: 開發準備    Stage 9: 移交開發
    │
    ▼
Stage 10: 實施與測試
    │
    ▼
Stage 11: 部署與上線
```

**關鍵依賴說明**：

| 關係 | 前置條件 | 原因 |
|------|---------|------|
| Stage 2 → Stage 3 | 需求提取完成 | 技術選型需基於已確認的功能和非功能需求 |
| Stage 3 → Stage 4 | 技術選型完成 | FRD 需包含技術可行性評估結果 |
| Stage 2 ↔ Stage 4 | 雙向參考 | 需求驗證可能觸發新的需求提取 |
| Stage 4 → Stage 5 | PRD/FRD 確認 | 架構設計需以正式需求文件為基礎 |
| Stage 5 → Stage 6 | SRD/API 完成 | User Story 需參考技術架構和 API 設計 |
| Stage 7 ∥ Stage 8 | 可並行執行 | Sprint 規劃與開發準備可同步進行 |

> 🔴 **重要提醒**: Stage 3（技術選型）必須以 Stage 2 的完整需求為基礎，
> 避免「先選技術再套需求」的反模式。若 Stage 3 過程中發現需求不足，
> 應回到 Stage 2 補充需求後再繼續。

---

### 階段 1：啟動和情境確認 (30 分鐘)

#### 步驟 1.1：載入 AISDLC 框架
```
執行指令：
「請載入 AISDLC_SDD_INIT.md (v0.01)，我要開發新專案」

或指定平台：
「請載入 AISDLC_INIT.md，我要開發新的 Web 電商平台」
「請載入 AISDLC_INIT.md，我要開發新的 iOS 健身 App」
```

#### 步驟 1.2：回答情境識別問題
系統會詢問：
- 專案類型 (Web/iOS/Android/macOS Desktop/跨平台/後端/混合架構)
- 專案規模 (MVP/中型/大型)
- 團隊情況 (人數、技能)

🆕 **多平台快速識別引導**（當使用者提及多個平台時）:

> 💡 若使用者描述中包含多個平台關鍵字（如「Web + 手機 App」、「前端 + Android + macOS」），
> 系統應在 Stage 1 立即進行架構類型快速判斷，無需等到 Stage 3：

| 使用者描述特徵 | 快速識別結果 | 架構類型 |
|--------------|------------|---------|
| 多平台**共用同一後端 API** | Type A: 共享後端混合架構 | Web + Mobile + Desktop → 共用 REST API |
| 各平台**獨立後端**，資料同步 | Type B: 獨立後端混合架構 | 各平台獨立開發，透過 Message Queue 同步 |
| **單一代碼庫**跨平台（Flutter/RN） | Type C: 跨平台框架架構 | 一份代碼多平台編譯 |
| **漸進式**平台擴展（先 Web 再 Mobile） | Type D: 階段式擴展架構 | Phase 1 先做核心平台，後續擴展 |

> **AI 快速確認問題**: 「您的多平台系統是共用同一個後端 API，還是各平台獨立運作？」
> 根據回答即可在 Stage 1 初步確認架構類型，Stage 3 再做詳細技術選型。

🆕 **多領域融合識別引導**（當專案涉及多個業務領域時）:

> 💡 若使用者描述中包含多個業務領域關鍵字（如「電商 + 民宿」、「進銷存 + CRM」、「物流 + 倉儲 + 零售」），
> 系統應在 Stage 1 識別「領域融合複雜度」，影響後續所有階段的規劃方式：

| 領域融合類型 | 特徵 | 範例 | 架構影響 |
|------------|------|------|---------|
| **單領域系統** | 一個核心業務領域 | 純電商、純 CRM、純民宿管理 | 標準設計，無需特殊處理 |
| **雙領域融合** | 兩個業務領域共用客戶/資料 | 電商+民宿、零售+物流、醫療+保險 | 需識別「共用實體」vs「領域專屬實體」 |
| **多領域平台** | 三個以上領域整合 | ERP（採購+庫存+銷售+財務+HR） | 建議微服務架構，按領域分離服務 |

> **AI 快速確認問題**:
> 1. 「您的系統涉及幾個業務領域？（如：電商是一個領域，民宿管理是另一個領域）」
> 2. 「各領域之間是否共用客戶/會員資料？」
> 3. 「各領域的資料模型是否有交叉？（如：電商訂單與民宿訂房是否合併管理）」

**雙領域融合的特殊注意事項**:
- 🔴 **Stage 2**: 需按領域分別確認業務規則，再處理交叉規則
- 🔴 **Stage 4**: MVP 需按領域分別評估，再合併優先級
- 🔴 **Stage 5**: 資料模型需區分「共用實體」（如：客戶）和「領域專屬實體」（如：商品 vs 房間）
- 🔴 **Stage 7**: 需識別跨領域依賴（如：電商積分可用於民宿折扣）

#### 步驟 1.3：確認載入結果

期待回應：
```
✅ 識別情境：Greenfield Project (新專案開發)
✅ 識別平台：[您的平台]

🔄 正在載入 Primary Agents...
✅ PM/PO Agent (Victoria) - 業務價值決策
✅ SA Agent (Amanda) - 需求分析主導

⏳ Supporting Agents 將在對應階段載入:
   - BA (Beatrice) → 階段 2 需求驗證
   - SD-Architect (Marcus) → 階段 3 技術選型
   - QA (Quincy) → 階段 4 驗收準則定義
   - Dev (David) → 階段 5 工時估算與實施開發
   - DevOps (devops-engineer) → 階段 8 CI/CD 與部署準備

✅ 推薦 Workflow：greenfield-complete-flow
準備開始新專案開發流程...
```

#### 步驟 1.4：執行專案初始化（建立 docs/ 目錄結構）

> 🔴 **重要**: 在進入階段 2 前，必須先建立專案的文檔目錄結構！

使用 AISDLC 提供的自動初始化腳本建立 8 層 docs/ 目錄：

```bash
# macOS / Linux / Git Bash
bash AISDLC/framework/tools/init_project.sh

# Windows PowerShell
PowerShell -ExecutionPolicy Bypass -File "AISDLC\framework\tools\init_project.ps1"
```

🆕 **AI Agent 操作模式說明**:

> 💡 當開發流程由 AI Agent（如 Claude Code）主導時，專案初始化有以下執行方式：

| 操作模式 | 說明 | 適用場景 |
|---------|------|---------|
| **自動執行** | AI Agent 直接透過 Bash 工具執行 `init_project.sh` | AI 有 Shell 執行權限（如 Claude Code、Cursor） |
| **指令產出** | AI Agent 產出完整的 `mkdir -p` 指令，由人類複製執行 | AI 無 Shell 權限（如 ChatGPT Web） |
| **手動建立** | AI Agent 列出目錄結構，由人類手動建立 | 無法執行腳本的環境 |

> **AI Agent 自動執行範例**:
> ```bash
> # AI Agent 偵測到腳本不存在時，可直接建立目錄
> mkdir -p docs/{01_requirements,02_architecture,03_testing,04_planning,05_development,06_quality,07_design,08_deployment}
> ```

**腳本會自動建立**：
- `docs/01_requirements/` - PRD/FRD/User Stories
- `docs/02_architecture/` - SRD/API Specification
- `docs/03_testing/` - Test Plan/Test Cases
- `docs/04_planning/` - Roadmap/Estimation
- `docs/05_development/` - Iteration Plans/Progress
- `docs/06_quality/` - Code Quality/Security
- `docs/07_design/` - UI/UX/Database Design
- `docs/08_deployment/` - CI/CD/Release Notes
- 🆕 `AISDLC_PROJECT_CONFIG.md` - **專案配置檔**（記錄技術棧、團隊規模、情境選擇等）

> ⚠️ **手動操作注意**: 若未使用自動初始化腳本（如手動建立目錄），請務必同時建立 `AISDLC_PROJECT_CONFIG.md`。
> 此檔案由 AISDLC_INIT.md 定義（line 103, 120），用於記錄專案基本配置，後續階段會參考此檔。
> ```bash
> # 手動建立時，從範本複製
> cp AISDLC/framework/guides/user/onboarding/templates/AISDLC_PROJECT_CONFIG_Template.md ./AISDLC_PROJECT_CONFIG.md
> ```

> 📋 **詳細說明**: 參考 [AISDLC_INIT.md - 專案初始化指南](../../AISDLC_INIT.md#-專案初始化指南-v008-新增)

**Agent 載入時序說明**:

根據 AISDLC 的 **On-Demand Loading 機制**（參考 [AISDLC_INIT.md](../../AISDLC_INIT.md)），Agents 會依階段按需載入，以優化 Token 使用效率：

##### Primary Agents（立即載入）
在階段 1 啟動時立即載入，全程參與：
- **PM/PO Agent (Victoria)**: 負責業務價值決策、產品方向確認、優先級排序
- **SA Agent (Amanda)**: 負責需求分析主導、需求提取、需求文件化

##### Supporting Agents（按需載入）
在特定階段觸發時才載入，完成任務後可釋放：
- **BA Agent (Beatrice)** - 階段 2 載入
  - 觸發時機: 需求驗證階段開始
  - 主要任務: 利害關係人驗證、需求可行性確認、業務流程驗證
  - 載入確認: `✅ BA Agent (Beatrice) 已載入 - 準備進行需求驗證`

- **SD-Architect Agent (Marcus)** - 階段 3 載入
  - 觸發時機: 技術選型階段開始
  - 主要任務: 技術架構設計、技術棧選擇、架構決策記錄 (ADR)
  - 平台選擇: 若為跨平台 Mobile (如 React Native)，可同時載入 `sd-web-architect` 和 `sd-mobile-architect`
  - 載入確認: `✅ SD-Architect (Marcus) 已載入 - 準備進行技術選型`

- **QA Agent (Quincy)** - 階段 4 載入
  - 觸發時機: 驗收準則定義階段
  - 主要任務: 定義驗收準則 (AC)、測試場景設計、品質標準制定
  - 載入確認: `✅ QA Agent (Quincy) 已載入 - 準備定義驗收準則`

- **Dev Agent (David)** - 階段 5 載入
  - 觸發時機: 技術可行性評估階段
  - 主要任務: 技術實作評估、開發工時估算、技術風險識別
  - 載入確認: `✅ Dev Agent (David) 已載入 - 準備進行技術可行性評估`

##### 平台 Architect 選擇指引

根據專案平台類型，選擇對應的 SD-Architect（參考 [Platform_Agent_Selection_Guide.md](../../guides/system/agent/Platform_Agent_Selection_Guide.md)）：

| 使用者描述 | 平台識別 | SD-Architect 選擇 | 說明 |
|----------|---------|-----------------|------|
| iOS App | iOS Native | `sd-mobile-architect` | 原生 Swift/SwiftUI |
| Android App | Android Native | `sd-mobile-architect` | 原生 Kotlin/Jetpack |
| React Native App | Cross-platform Mobile | `sd-web-architect` + `sd-mobile-architect` | 混合：RN 架構 + 原生整合 |
| Flutter App | Cross-platform Mobile | `sd-mobile-architect` | Flutter 原生編譯 |
| Web App | Web | `sd-web-architect` | React/Vue/Angular |
| macOS Desktop App (Electron/Tauri) | macOS Native | `sd-web-architect` | Web 技術棧桌面應用 |
| macOS Desktop App (SwiftUI) | macOS Native (Apple) | `sd-mobile-architect` | Apple 原生框架，與 iOS 共用設計模式 |
| Windows Desktop App | Windows Native | `sd-web-architect` | Electron / Tauri / .NET WPF |
| Web + Mobile + Desktop | Type A 混合架構 | `sd-web-architect` + `sd-mobile-architect` | 共用後端 API，前端多平台 |
| Backend API | Backend | `sd-backend-architect` | Node.js/Python/Java/Spring Boot |

##### 為什麼要按需載入？

✅ **優點**:
1. **Token 效率**: 初始載入僅需 ~200 tokens（vs 完全載入 ~2000 tokens）
2. **聚焦任務**: 每個階段只載入相關 Agents，減少干擾
3. **靈活擴展**: 可根據專案需求動態調整 Agents 組合
4. **成本優化**: 減少 70-85% 的 Token 使用量

⚠️ **注意事項**:
- Primary Agents 會全程保持載入狀態
- Supporting Agents 在任務完成後可以釋放，但記憶會保留在文檔中
- 若需要重新諮詢某個 Agent，可以明確要求重新載入

---

## 📊 九階段 Agent 載入對照表

以下是 Greenfield 情境下，9 個階段的 Agent 載入時序、主要職責及產出文檔的完整對照表：

| 階段 | 階段名稱 | 載入 Agents | Agent 主要職責 | 主要產出 | 預估時間 |
|------|---------|------------|--------------|---------|---------|
| **Stage 1** | 啟動和情境確認 | **PM/PO** (Victoria)<br>**SA** (Amanda) | • PM/PO: 專案目標確認、業務價值評估<br>• SA: 專案情境識別、前置材料檢查 | • 專案 Kick-off 記錄<br>• 情境確認清單<br>• 前置準備檢查結果 | 30 分鐘 |
| **Stage 2** | 需求提取與分析 | PM/PO, SA<br>**+ BA** (Beatrice) | • SA: 需求提取主導、需求初步分析<br>• BA: 利害關係人驗證、業務可行性確認<br>• PM/PO: 產品方向確認 | • 初步需求分析文檔<br>• 需求提取會議記錄<br>• 利害關係人訪談記錄 | 4-8 小時 |
| **Stage 3** | 技術選型 | PM/PO, SA, BA<br>**+ SD-Architect** (Marcus) | • SD-Architect: 技術棧選擇、架構決策、ADR 撰寫<br>• SA: 技術需求確認<br>• PM/PO: 技術方向決策 | • 技術選型報告<br>• 架構決策記錄 (ADR)<br>• 技術風險評估<br>• 技術棧確認清單 | 2-4 小時 |
| **Stage 4** | 需求驗證與文件化 | PM/PO, SA, BA, SD<br>**+ QA** (Quincy) | • SA: PRD/FRD 撰寫主導<br>• BA: 需求驗證與利害關係人確認<br>• QA: 驗收準則定義、測試場景設計<br>• SD: 技術可行性驗證 | • **PRD** (Product Requirements Doc)<br>• **FRD** (Functional Requirements Doc)<br>• **AC** (Acceptance Criteria)<br>• MVP 範圍確認 | 3-5 小時 |
| **Stage 5** | 架構設計 | PM/PO, SA, SD, QA<br>**+ Dev** (David) | • SD: 系統架構設計主導、SRD 撰寫<br>• Dev: 技術可行性評估、工時估算<br>• QA: 測試架構設計、NFR 驗證 | • **SRD** (System Requirements Doc)<br>• C4 架構圖 (Context/Container/Component)<br>• 資料庫 Schema 設計<br>• 技術可行性報告 | 4-6 小時 |
| **Stage 6** | User Story 撰寫 | SA, SD, QA, Dev | • SA: User Story 撰寫主導、AC 定義<br>• QA: 測試場景設計、AT 設計<br>• Dev: 技術任務拆分、工時評估<br>• SD: 技術依賴確認 | • **User Stories** (US-XXX)<br>• **Acceptance Criteria** (AC-XXX-X)<br>• **Acceptance Tests** (AT-XXX-X-Y)<br>• User Story Mapping | 3-4 小時 |
| **Stage 7** | Sprint 規劃 | PM/PO, SA, SD, Dev | • PM/PO: Sprint 優先級決策<br>• SA: Sprint 範圍確認<br>• Dev: 工時估算與任務分配<br>• SD: 技術依賴排序 | • Sprint Backlog<br>• Sprint 計畫文檔<br>• 團隊分工表<br>• 開發時程表 | 2-3 小時 |
| **Stage 8** | 開發準備 | SD, Dev, QA<br>**+ DevOps** (devops-engineer) | • Dev: 開發環境建置、Git 設定<br>• SD: 技術框架搭建、Coding Standards<br>• QA: 測試環境建置、自動化測試框架<br>• **DevOps: CI/CD Pipeline 配置、容器化** | • 開發環境設定指南<br>• Git Workflow 規範<br>• Coding Standards<br>• CI/CD Pipeline 配置 | 1-2 天 |
| **Stage 9** | 移交開發團隊 | PM/PO, SA, SD, QA, Dev | • SA: 文檔完整性檢查<br>• SD: 技術架構 Walkthrough<br>• QA: 測試計畫說明<br>• Dev: 開發注意事項說明<br>• PM/PO: 專案目標與成功標準確認 | • 文檔一致性檢查報告<br>• 移交 Checklist<br>• 開發團隊 Q&A 記錄<br>• 專案 Kickoff Deck | 1 小時 |

### Agent 載入時機流程圖

```
Stage 1: 啟動
   ├── PM/PO (Victoria) ✅ 載入
   └── SA (Amanda) ✅ 載入

Stage 2: 需求提取
   └── + BA (Beatrice) ✅ 載入

Stage 3: 技術選型
   └── + SD-Architect (Marcus) ✅ 載入
       ├── 平台選擇: Web → sd-web-architect
       ├── 平台選擇: iOS/Android → sd-mobile-architect
       └── 平台選擇: React Native → sd-web-architect + sd-mobile-architect

Stage 4: 需求驗證
   └── + QA (Quincy) ✅ 載入

Stage 5: 架構設計
   └── + Dev (David) ✅ 載入

Stage 8: 開發準備
   └── + DevOps (devops-engineer) ✅ 載入
       └── CI/CD Pipeline、容器化、部署環境

Stage 6-9: 持續協作
   └── 所有 Agents 協同工作（含 Stage 11 部署階段 DevOps 主導）
```

### 平台特化 Agent 選擇表

根據專案平台類型，在 **Stage 3 技術選型階段** 選擇對應的 SD-Architect：

| 專案平台 | SD-Architect 選擇 | Agent 檔案 | 說明 |
|---------|-----------------|-----------|------|
| **Web 應用** | sd-web-architect | `agent/specialized/sd-web-architect-zh.yaml` | React/Vue/Angular 等前端框架 |
| **iOS Native** | sd-mobile-architect | `agent/specialized/sd-mobile-architect-zh.yaml` | Swift/SwiftUI 原生開發 |
| **Android Native** | sd-mobile-architect | `agent/specialized/sd-mobile-architect-zh.yaml` | Kotlin/Jetpack 原生開發 |
| **React Native** | sd-web-architect<br>+ sd-mobile-architect | 兩個 Agent 協作 | RN 架構設計 + 原生模組整合 |
| **Flutter** | sd-mobile-architect | `agent/specialized/sd-mobile-architect-zh.yaml` | Flutter 原生編譯 |
| **Backend API** | sd-architect (通用) | `agent/core/05.sd-architect-zh.yaml` | Node.js/Python/Java 後端 |
| **macOS (Electron/Tauri)** | sd-web-architect | `agent/specialized/sd-web-architect-zh.yaml` | Web 技術棧桌面應用 |
| **macOS (SwiftUI)** | sd-mobile-architect | `agent/specialized/sd-mobile-architect-zh.yaml` | Apple 原生框架，與 iOS 共用設計模式 |
| **跨平台 (Web+Mobile)** | sd-web-architect<br>+ sd-mobile-architect | 兩個 Agent 協作 | 統一技術棧或分離設計 |

### 專業化 QA Agent 選擇表

根據測試需求複雜度，在 **Stage 4 需求驗證階段** 或之後選擇對應的 QA Agents：

| 測試需求 | QA Agent 選擇 | Agent 檔案 | 推薦載入時機 |
|---------|--------------|-----------|-------------|
| **基礎測試** | qa-tester (通用) | `agent/core/07.qa-tester-zh.yaml` | Stage 4 (預設載入) |
| **Web 應用測試** | + qa-web-tester | `agent/specialized/qa-web-tester-zh.yaml` | Stage 6 (User Story 撰寫) |
| **Mobile 應用測試** | + qa-mobile-tester | `agent/specialized/qa-mobile-tester-zh.yaml` | Stage 6 (User Story 撰寫) |
| **自動化測試** | + qa-automation | `agent/specialized/qa-automation-zh.yaml` | Stage 8 (開發準備) |
| **測試策略制定** | + qa-lead | `agent/specialized/qa-lead-zh.yaml` | Stage 7 (Sprint 規劃) |

### Agent 載入確認訊息範例

當 AI 載入新的 Agent 時，你會看到類似以下的確認訊息：

```
🔔 階段 2 開始 - 需求提取與分析

✅ BA Agent (Beatrice) 已載入
   角色: 業務分析師
   主要職責:
   - 利害關係人驗證
   - 業務可行性確認
   - 需求完整性檢查

📋 當前載入的 Agents:
   - PM/PO (Victoria) - 產品經理
   - SA (Amanda) - 系統分析師
   - BA (Beatrice) - 業務分析師 [新載入]

🎯 本階段目標:
   - 提取和分析需求
   - 驗證業務可行性
   - 確認利害關係人需求

準備開始需求提取流程...
```

### 重要注意事項

1. **Primary Agents 全程保持載入**:
   - PM/PO 和 SA 從 Stage 1 到 Stage 9 全程參與
   - 確保需求和業務價值的一致性

2. **Supporting Agents 按需載入**:
   - BA (Stage 2), SD (Stage 3), QA (Stage 4), Dev (Stage 5)
   - 在特定階段載入，完成任務後記憶保留在文檔中

3. **平台特化 Agent 動態選擇**:
   - 根據專案平台在 Stage 3 選擇對應的 SD-Architect
   - 跨平台專案可同時載入多個 Architect Agents

4. **專業化 QA Agent 選擇性載入**:
   - 基礎專案使用通用 qa-tester 即可
   - 複雜專案根據需求載入專業化 QA Agents

5. **Specialized Agents 推薦時機**:
   - `code-analyzer`: 若有既有代碼需要評估（Brownfield 轉換）
   - `performance-engineer`: Stage 5 架構設計階段（效能敏感專案）
   - `security-engineer`: Stage 3 技術選型階段（安全敏感專案）
   - `compliance-officer`: Stage 3 合規需求確認（涉及 GDPR/PCI-DSS/ISO 27001）⭐ v0.01 新增
   - `integration-specialist`: Stage 2 需求分析階段（需要硬體整合/第三方 API）
   - `sd-mobile-architect`: Stage 3 平台架構設計（涉及 iOS/Android/macOS）⭐ v0.01 新增
   - `qa-mobile-tester`: Stage 6 User Story 撰寫（行動端專業測試）⭐ v0.01 新增
   - `devops-engineer`: Stage 8 開發準備階段（需要 CI/CD）

📖 **詳細 Specialized Agent 推薦條件**: 參考 [guides/system/agent/Specialized_Agent_Selection_Guide.md](../../guides/system/agent/Specialized_Agent_Selection_Guide.md)

---

### 階段 2：需求提取與分析 (4-8 小時)

> 🆕 **多領域系統命名空間預警（Multi-Domain Naming Warning）**
>
> 若本系統涉及**多個業務領域**（如「電商 + 民宿 + CMS + KMS」），請在開始需求提取**之前**確認 ID 命名空間策略：
>
> | 問題 | 原因 | 解決方案 |
> |------|------|---------|
> | 電商 F-001 vs 民宿 F-001 命名衝突 | 多域功能 ID 不區分會造成追蹤鏈混亂 | 使用**領域前綴**：`SHOP-F-001`、`STAY-F-001`、`CMS-F-001`、`KMS-F-001` |
> | 共用功能歸屬不清 | 會員/支付/通知屬於哪個域？ | 建立 `SHARED-F-XXX` 命名空間，供所有領域共用 |
>
> **🔴 立即決策**：在本階段開始前，請確認你的領域前綴縮寫（可參考範例）：
> - 電商：`SHOP` | 民宿：`STAY` | 內容發布：`CMS` | 知識管理：`KMS` | 共用：`SHARED`
>
> **後續階段適用**：此前綴貫穿 Feature ID（F）、Business Rule ID（BR）、Epic ID（EPIC）、User Story（US）、API ID（API）。
>
> 💡 詳細命名規範：[AISDLC_ID_Naming_Convention.md](../../guides/system/naming/AISDLC_ID_Naming_Convention.md)

> 🤖 **Agent 載入時機** - BA Agent (Beatrice) **首次載入**
>
> **觸發時機**: 當階段 2 開始需求驗證時，BA Agent (Beatrice) 會被載入，負責業務可行性驗證和利害關係人確認。
>
> **載入確認訊息**:
> ```
> ✅ BA Agent (Beatrice) 已載入 - 準備進行需求驗證
> ```
>
> **主要職責** (階段 2):
> - 利害關係人驗證（確認需求符合業務期望）
> - 需求可行性確認（業務層面評估）
> - 業務流程驗證（確認業務邏輯正確）
> - 需求完整性檢查（使用 [Completeness_Checklist.md](checklists/Completeness_Checklist.md)）
> - 標準確認問題引導（使用 [Standard_Confirmation_Questions.md](checklists/Standard_Confirmation_Questions.md)）
>
> **協作模式**:
> - 與 SA Agent (Amanda) 協作：需求深化分析
> - 與 PM/PO Agent (Victoria) 協作：業務優先級確認
> - **後續階段延續參與**: Stage 4 (需求驗證與文件化核心角色)

#### 步驟 2.1：提供需求輸入

> 🔧 **建議 Skill**: `/sa-analyst`（需求分析主導）、`/ba-analyst`（業務驗證與利害關係人管理）
> - `/sa-analyst`: 啟動需求提取、功能分析、FRD 產出
> - `/ba-analyst`: 業務邏輯驗證、利害關係人需求對齊、業務規則確認

```
執行指令：
「開始需求提取流程，以下是我的專案需求：
[貼上你的需求描述、截圖、或設計稿]」
```

#### 步驟 2.2：配合人機協作確認點

> 🔴 **人機協作點 1：輸入理解確認與非功能需求引導** (20 分鐘)
>
> **AI 需完成**:
> 1. **重述輸入理解**（功能需求）
>    - 系統會呈現對需求的初步理解
>    - 確認理解是否準確
>    - 補充缺失的資訊
>
> 2. **提前引導非功能需求**（參考 [Standard_Confirmation_Questions.md](checklists/Standard_Confirmation_Questions.md)）
>
>    **效能需求**:
>    - App 啟動時間目標？（例如：< 2 秒）
>    - 頁面載入速度要求？（例如：< 1 秒）
>    - 支援的最大資料量？（例如：10,000 筆交易記錄）
>
>    **安全需求**:
>    - 資料是否需要加密？（本地儲存加密）
>    - 是否需要身份驗證？（PIN / 生物辨識）
>    - 敏感資料處理方式？（密碼、個資）
>
>    **可用性需求**:
>    - 是否需要離線支援？（完全離線 / 部分離線）
>    - 錯誤處理策略？（友善錯誤訊息、錯誤回報）
>    - 資料備份與還原需求？
>
>    **相容性需求**:
>    - iOS 最低支援版本？（例如：iOS 15+）
>    - Android 最低支援版本？（例如：Android 8.0+）
>    - 支援的裝置類型？（手機 / 平板）
>
>    **可維護性需求**:
>    - 是否需要監控和日誌？（Crash reporting, Analytics）
>    - 是否需要 A/B 測試支援？
>    - 遠端配置需求？（Feature flags）
>
>    🆕 **Web/Backend 系統專用 NFR 引導問題**:
>
>    **瀏覽器與前端相容性**:
>    - 支援哪些瀏覽器？（Chrome/Firefox/Safari/Edge，最低版本？）
>    - 是否需要 RWD 響應式設計？（桌面 / 平板 / 手機）
>    - 是否需要 PWA（Progressive Web App）支援？
>    - 是否需要 i18n 多語系支援？
>
>    **資料庫與後端效能**:
>    - 預估資料量規模？（如：百萬級商品、千萬級交易紀錄）
>    - 資料庫查詢回應時間要求？（如：列表查詢 < 500ms）
>    - 是否需要全文檢索？（Elasticsearch / PostgreSQL Full-text Search）
>    - 是否需要讀寫分離或分庫分表？
>    - 批次處理需求？（如：月結報表、大量匯入匯出）
>
>    **並發與擴展性**:
>    - 預估同時在線使用者數？（如：100 / 1,000 / 10,000）
>    - API 每秒請求量（RPS）目標？（如：100 RPS / 1,000 RPS）
>    - 是否需要水平擴展能力？（Auto Scaling）
>    - 是否需要 CDN 加速？（靜態資源、圖片）
>
>    **整合與外部系統**:
>    - 是否需要印表機整合？（標籤列印、報表列印、POS 收據）
>    - 是否需要掃碼裝置整合？（條碼掃描器、QR Code Reader）
>    - 是否需要第三方 ERP/會計系統對接？
>    - 是否需要電子發票 / 電子支付整合？
>    - 是否需要 Email/SMS 通知整合？
>
>    🆕 **內容編輯與媒體管理**（適用於 CMS/KMS/內容平台）:
>    - 富文本編輯器是否需要協作編輯（多人同時編輯同一文檔）？
>    - 支援哪些媒體類型？（圖片/影片/音頻/PDF/程式碼片段）
>    - 單一檔案上傳大小限制？（如：圖片 < 10MB、影片 < 500MB）
>    - 是否需要圖片自動壓縮/裁切/WebP 轉換？
>    - 是否需要內容版本自動保存？（保存頻率、版本數量上限）
>    - 是否需要內容複製/範本/遷移功能？
>
>    🆕 **知識管理專屬 NFR**（適用於 KMS/Wiki/知識庫系統）:
>    - 協作編輯的並發人數上限？（如：同一文檔最多 10 人同時編輯）
>    - 協作編輯衝突解決策略？（OT / CRDT / 樂觀鎖 + 手動合併）
>    - 知識過期檢查頻率？（如：每月自動標記超過 6 個月未更新的文檔）
>    - 知識圖譜深度？（如：最多顯示 3 層關聯、是否支援雙向連結）
>    - 知識權限粒度？（文檔級 / 章節級 / 欄位級；部門隔離 vs 全企業共享）
>    - 版本比對效能要求？（如：Diff 計算 < 2 秒，保留歷史版本數量上限）
>    - 匯入匯出格式？（Markdown / HTML / PDF / Confluence / Notion 匯入）
>
>    🆕 **搜尋與索引**（適用於需要全文搜尋的系統）:
>    - 搜尋索引更新策略？（即時索引 vs 週期性批次索引）
>    - 搜尋回應時間要求？（如：< 200ms / < 500ms）
>    - 是否需要進階搜尋功能？（模糊搜尋、同義詞、自動完成、搜尋建議）
>    - 是否需要搜尋分析？（熱門搜尋詞、零結果查詢追蹤）
>
>    🆕 **SEO 與內容發布**（適用於面向公眾的內容平台）:
>    - 是否需要自動生成 Meta 標籤（Title/Description/Keywords）？
>    - 是否需要自訂 URL Slug？
>    - 是否需要結構化資料支援（Schema.org / JSON-LD）？
>    - 是否需要自動生成 Sitemap？
>    - 是否需要排程發布功能？（定時發布、定時下架）
>    - 是否需要多渠道發布？（Web/App/Email 通訊/社群媒體）
>
>    **資料合規與稽核**:
>    - 是否需要操作稽核日誌？（誰在何時做了什麼）
>    - 資料保留政策？（如：交易紀錄保留 7 年）
>    - 是否有個資法（GDPR / 台灣個資法）合規需求？
>    - 是否需要資料匯出/刪除權（Right to Erasure）？
>
> **使用者需確認**:
> - 功能理解是否正確
> - 非功能需求是否有遺漏或需補充
> - 優先處理哪些非功能需求

> 🔴 **人機協作點 2：功能清單確認** (20 分鐘)
> - 系統會列出識別的功能清單
> - 確認功能是否完整
> - 補充遺漏的功能
> - 確認功能優先級

> 🔴 **人機協作點 3：使用者角色確認** (15 分鐘)
> - 系統會列出識別的使用者角色
> - 確認角色是否完整
> - 補充角色權限和特性

> 🔴 **人機協作點 4：業務規則確認** (20 分鐘)
> - 系統會列出關鍵業務規則
> - 確認規則是否準確
> - 補充約束條件
>
> 🆕 **常見產業領域業務規則提示**（AI 應主動詢問）:
>
> | 產業領域 | 常見業務規則（AI 需主動確認） |
> |---------|--------------------------|
> | **經銷存/ERP** | 庫存計價方式（FIFO/LIFO/加權平均）、稅金計算（含稅/未稅/營業稅）、帳款對帳週期、安全庫存警戒值、批號/效期管理 |
> | **電商/零售** | 促銷折扣疊加規則、庫存預扣機制、退貨退款政策、會員等級折扣、運費計算規則 |
> | **金融/保險** | 利率計算方式、風控審核規則、KYC/AML 合規、交易限額、帳務沖銷規則 |
> | **醫療/健康** | 病歷保存年限、處方籤規則、HIPAA/個資法合規、掛號排班邏輯、保險給付規則 |
> | **製造/生產** | BOM 表管理、工序排程規則、品質檢驗標準（AQL）、物料需求計畫（MRP）、良率計算 |
> | **物流/運輸** | 路線最佳化規則、貨物追蹤狀態機、運費計算（重量/材積）、配送時段管理、溫控物流要求 |
> | **旅宿/民宿/飯店** | 入住退房規則（Check-in/Check-out 時間、提前/延遲規則）、取消政策（免費取消期限/階梯式扣款）、季節動態定價（平日/假日/旺季/特殊日）、房態管理（可售/維護/預留/超賣控制）、OTA 渠道同步（Booking.com/Airbnb/Agoda 庫存同步、價格一致性）、清潔排程與翻房管理 |
> | **租賃/共享經濟** | 租賃計費模式（按時/按日/按月）、押金與損壞賠償規則、資源調度與可用性管理、預約衝突處理、延期歸還處罰規則 |
> | **媒體/出版/內容管理** | 內容生命週期管理（草稿→編輯→審核→排程→發布→歸檔）、多層審核流程（編輯→主編→內容主管）、排程發布與即時發布規則、內容版本管理與回滾、多渠道發布同步（Web/App/Email/社群）、SEO 最佳化規則（Meta 標籤、URL Slug、結構化資料）、內容授權與版權管理、評論與互動審核規則、媒體資產管理（圖片/影片/文檔上傳限制與格式要求） |
> | **知識管理/Wiki** | 知識分類架構（樹狀/標籤/多維分類）、知識版本追蹤與比對（Diff）、協作編輯衝突處理（樂觀鎖/OT/CRDT）、知識評分與推薦機制、知識過期檢查與更新提醒、部門知識隔離 vs 全企業共享策略、知識圖譜關係定義、全文搜尋與索引策略 |
>
> **AI 通用詢問模板**: 「您的 {產業} 系統是否有特定的業務規則需要遵循？例如：{該產業常見規則}。請列舉您系統中最重要的 3-5 條業務規則。」

> 🔴 **人機協作點 5：初步 MVP 意向確認** (10 分鐘)
>
> **目的**: 確認是否需要進行 MVP 範圍界定
>
> **AI 需詢問**:
> - 「這個專案是否需要分階段發布（MVP 方式）？」
> - 「如果需要，您希望 MVP 版本包含哪些核心功能？」
> - 「預計的 MVP 發布時間？」
>
> **使用者需決策**:
> - ✅ **需要 MVP**: 記錄初步 MVP 意向，階段 4 進行正式界定
>   - 記錄核心功能清單（初步）
>   - 記錄目標發布時間
>   - 標記後續需要進行 RICE/Kano 評估
> - ❌ **不需要 MVP**: 所有功能都在首次發布，跳過 MVP 相關步驟
>
> **注意**: 此階段只是「初步意向」，正式的 MVP 範圍界定在**階段 4 步驟 4.2**進行（使用 RICE 模型和 Kano 模型）

#### 步驟 2.3：使用標準化確認問題

> 📋 **使用工具**: [Standard_Confirmation_Questions.md](checklists/Standard_Confirmation_Questions.md)

系統會使用 **72 個標準確認問題**確保需求完整性，涵蓋 9 大類別：

1. **功能需求類** (F1-F8): 核心功能、使用者流程
2. **使用者與角色類** (U1-U8): 目標使用者、權限管理
3. **資料與儲存類** (D1-D8): 資料來源、儲存方式、備份策略
4. **技術與平台類** (T1-T10): 平台選擇、技術棧、跨平台需求
5. **整合與 API 類** (I1-I8): 第三方整合、API 設計
6. **效能與擴展類** (P1-P8): 效能指標、併發量、擴展性
7. **安全與合規類** (S1-S8): 資料安全、法規遵循
8. **成本與預算類** (C1-C6): 預算限制、成本估算
9. **時程與里程碑類** (M1-M8): 時程限制、發布計畫

> 💡 **擴充確認問題 (v0.01 新增)**:
> 若專案涉及以下場景，需額外確認：

**硬體整合確認問題** (H1-H12)（適用於掃碼器、印表機、電子秤、POS、RFID 等周邊設備）:

| 編號 | 確認問題 | 範例回答 |
|------|---------|---------|
| H1 | 需要整合哪些硬體設備？ | 條碼掃描器、標籤印表機、電子秤 |
| H2 | 各設備的通訊協定？ | 掃碼：Camera API / USB HID；印表機：ESC/POS |
| H3 | 需要支援哪些掃碼格式？ | EAN-13、Code 128、QR Code |
| H4 | 掃碼成功率要求？ | ≥ 99%（正常光線條件下） |
| H5 | 離線操作需求？ | 掃碼入庫可離線操作，上線後自動同步 |
| H6 | 硬體相容性測試範圍？ | Android 主流機型 (2020 年後)、macOS 12+ |
| H7 | 是否需要 POS 收銀機整合？ | POS 機型號、收銀軟體版本、錢箱控制協定 |
| H8 | 是否需要電子秤整合？ | 秤的通訊協定（RS-232/USB）、重量單位、精度要求 |
| H9 | 是否需要 RFID 讀取器整合？ | RFID 頻率（HF/UHF）、讀取距離、批次讀取需求 |
| H10 | 是否需要收據/標籤印表機？ | 印表機類型（熱感應/熱轉印）、標籤尺寸、列印速度要求 |
| H11 | 是否需要門禁/刷卡設備？ | 卡片類型（NFC/磁條/IC 卡）、讀卡器介面 |
| H12 | 硬體設備的維護與故障處理？ | 設備離線降級方案、自動重連機制、故障通報流程 |
| H13 | 是否需要智慧門鎖整合？ | 門鎖品牌/協定（BLE/Wi-Fi/Zigbee）、遠端密碼生成、入住自動開鎖、退房自動換碼 |
| H14 | 是否需要自助入住機/Kiosk？ | Kiosk 硬體規格、護照/身分證掃描、房卡發放、多語言介面 |
| H15 | 是否需要房間感應器整合？ | 感應器類型（溫濕度/煙霧/門磁/動態偵測）、數據回報頻率、異常告警門檻 |
| H16 | 是否需要智慧家電控制？ | 控制項目（空調/燈光/窗簾/電視）、控制協定（MQTT/HomeKit/Matter）、入住自動情境、退房自動關閉 |

> 💡 H13-H16 適用於旅宿/民宿/智慧空間場景。若涉及 IoT 設備整合，建議額外載入 `integration-specialist` Agent 評估設備互通性與安全性。

**跨平台需求管理確認問題** (X1-X5)（適用於多平台專案）:

| 編號 | 確認問題 | 範例回答 |
|------|---------|---------|
| X1 | 各平台功能是否完全一致？ | Web 全功能、Mobile 掃碼+查詢、Desktop 報表+管理 |
| X2 | 各平台的開發優先序？ | Phase 1: Web、Phase 2: Android、Phase 3: macOS |
| X3 | 各平台是否共用同一 API？ | 是，共用 REST API，但各平台 SDK 不同 |
| X4 | 資料同步策略？ | 即時同步（WebSocket）+ 離線快取（IndexedDB/SQLite）|
| X5 | 各平台的 UI/UX 差異？ | Web 響應式設計、Mobile Material/HIG、Desktop 原生風格 |

> 💡 若專案涉及硬體整合，建議額外載入 `integration-specialist` Agent 協助評估。

🆕 **多領域混合流量分析引導問題** (ML1-ML4)（適用於多業務領域融合系統）:

| 編號 | 確認問題 | 範例回答 |
|------|---------|---------|
| ML1 | 各領域的流量模式是否不同？ | 電商：促銷期間爆發（10x+）；民宿：旺季持續高峰（3-5x，但持續數週） |
| ML2 | 各領域的尖峰時段是否重疊？ | 電商尖峰（雙11）與民宿尖峰（春節）不重疊，但部分假日重疊 |
| ML3 | 各領域的流量是否需要獨立擴展？ | 是，電商模組需在大促期間獨立擴容，不影響民宿模組 |
| ML4 | 共用基礎設施（DB/快取）能否承受多領域同時尖峰？ | 需評估，建議 DB 讀寫分離 + 各領域獨立連線池 |

🆕 **OTA/訂房平台渠道整合引導問題** (OTA1-OTA4)（適用於旅宿/租賃系統）:

| 編號 | 確認問題 | 範例回答 |
|------|---------|---------|
| OTA1 | 需要整合哪些 OTA 渠道？ | Booking.com、Airbnb、Agoda、自有官網 |
| OTA2 | 庫存同步策略？ | Channel Manager 中心化管理，各渠道即時同步 |
| OTA3 | 價格策略是否各渠道不同？ | 官網最低價保證，OTA 平台加 10% 佣金 |
| OTA4 | OTA 訂單與直客訂單是否合併管理？ | 是，統一進入訂房系統，但標記來源渠道 |

**使用範例** (MoneyTracker):
```
Q1.1.1: 誰是這個 App 的主要使用者？
→ 答：25-45 歲上班族，收入穩定但缺乏理財習慣

Q3.1.1: 使用者資料儲存在哪裡？
→ 答：混合模式（本地 SQLite + 雲端 Firebase 同步）

Q4.1.1: 這個專案需要支援哪些平台？
→ 答：iOS + Android 跨平台 Mobile App
```

#### 步驟 2.4：需求完整性檢查

> 📋 **使用工具**: [Completeness_Checklist.md](checklists/Completeness_Checklist.md)

使用 **120 項完整性檢查清單**驗證需求是否完整，涵蓋 9 大類別：

| 類別 | 檢查項目數 | 關鍵檢查點 |
|-----|----------|----------|
| **功能完整性** | 15 項 | 核心功能、使用者流程、錯誤處理 |
| **使用者與角色** | 12 項 | 使用者角色、權限管理、使用者體驗 |
| **資料與儲存** | 15 項 | 資料模型、儲存策略、備份與恢復 |
| **技術與平台** | 12 項 | 平台選擇、技術棧、跨平台考量 |
| **整合與 API** | 12 項 | 第三方整合、API 設計、錯誤處理 |
| **效能與擴展** | 15 項 | 效能指標、負載測試、擴展策略 |
| **安全與合規** | 15 項 | 資料安全、身份驗證、法規遵循 |
| **成本與預算** | 12 項 | 成本估算、預算控管、ROI 分析 |
| **時程與交付** | 12 項 | 時程規劃、里程碑、風險管理 |

🆕 **關鍵檢查項目摘要**（減少 Token 消耗，快速檢查最常遺漏的項目）:

> 💡 以下為 120 項中最常遺漏的 15 項「必查項目」，可在不載入完整 Checklist 時快速自查。
> 完整檢查仍建議載入 [Completeness_Checklist.md](checklists/Completeness_Checklist.md)。

| # | 類別 | 必查項目 | 遺漏後果 |
|---|------|---------|---------|
| 1 | 功能 | 所有 CRUD 操作的刪除策略（軟刪除/硬刪除）是否已定義？ | 資料遺失、無法追溯 |
| 2 | 功能 | 錯誤處理和異常流程是否都有定義？（不只有 Happy Path） | 使用者遇錯無提示 |
| 3 | 功能 | 批次操作（匯入/匯出/批次刪除）是否有考慮？ | 大量資料操作困難 |
| 4 | 角色 | 每個角色的權限矩陣是否已定義？ | 越權操作風險 |
| 5 | 資料 | 資料備份頻率和還原策略是否已定義？ | 資料遺失無法復原 |
| 6 | 資料 | 資料保留政策和歸檔策略是否已定義？ | 資料庫膨脹、合規風險 |
| 7 | 技術 | 多平台間的資料同步策略是否已定義？ | 資料不一致 |
| 8 | 整合 | 第三方服務的降級/重試策略是否已定義？ | 第三方故障時系統癱瘓 |
| 9 | 效能 | 併發量和效能基線是否已量化？ | 上線後效能問題 |
| 10 | 安全 | 認證授權機制（JWT/OAuth）是否已明確？ | 安全漏洞 |
| 11 | 安全 | 敏感資料（密碼/個資/金額）的加密方式是否已定義？ | 資料洩漏 |
| 12 | 安全 | 操作稽核日誌的範圍和保留期限是否已定義？ | 無法追溯問題 |
| 13 | 成本 | 第三方服務的費用（API 呼叫次數/儲存量）是否已估算？ | 預算超支 |
| 14 | 時程 | 外部依賴的前置時間是否已納入？（帳號申請、審核） | 時程延遲 |
| 15 | 時程 | MVP 和後續 Phase 的功能劃分是否已確認？ | 範圍蔓延 |

---

#### 步驟 2.5：安全威脅建模（🆕 v0.01 新增）

> 📋 **使用工具**: [Security_Threat_Modeling_Guide.md](../../guides/system/quality/Security_Threat_Modeling_Guide.md)
>
> **目的**: 使用 STRIDE 方法系統化識別安全威脅，產出安全需求清單（NFR-SEC-xxx）
>
> **執行時機**: 完成需求完整性檢查後，進入需求驗證階段前
>
> **參與角色**: SA (主導) + Security Engineer（如有） + BA（驗證）

**執行流程**:

**1. 識別系統資產** (15 分鐘)

列出需要保護的核心資產：

| 資產類別 | 資產項目範例 | 敏感等級 |
|---------|------------|---------|
| **使用者資料** | 個人資訊、聯絡方式、Email | 🔴 高 |
| **認證資料** | 密碼、OAuth Token、JWT、Session | 🔴 高 |
| **金流資料** | 信用卡、交易記錄、帳務資訊 | 🔴 高 |
| **業務資料** | 訂單、庫存、房源、會員等級 | 🟡 中 |
| **系統元件** | API 金鑰、Database 連線字串 | 🔴 高 |

**2. 繪製資料流圖 (DFD)** (20 分鐘)

繪製 Level 1 資料流圖，標示信任邊界：

```
[使用者] → [前端] → [API Gateway] → [應用服務] → [資料庫]
             ↑            ↓               ↓
        [JWT Token]  [快取服務]    [第三方 API]

信任邊界:
- 邊界 1: 使用者 ↔ 前端（HTTPS）
- 邊界 2: 前端 ↔ API Gateway（JWT 驗證）
- 邊界 3: API Gateway ↔ 內部服務（內網）
- 邊界 4: 內部服務 ↔ 第三方 API（外部整合）
```

**3. 應用 STRIDE 分析** (30 分鐘)

對每個資料流應用 STRIDE 威脅分析：

| STRIDE 類別 | 威脅場景範例 | 風險等級評估 |
|------------|-------------|-------------|
| **S**poofing（欺騙） | 攻擊者竊取 JWT Token 假冒登入 | 可能性 × 影響 = 風險 |
| **T**ampering（篡改） | 修改 Request 提升權限或修改價格 | 🟡 中 × 🔴 高 = 🔴 高 |
| **R**epudiation（否認） | 缺少操作日誌，無法追蹤惡意行為 | 🟡 中 × 🟡 中 = 🟡 中 |
| **I**nformation Disclosure（資訊洩露） | API 回傳其他使用者的敏感資料 | 🟡 中 × 🔴 高 = 🔴 高 |
| **D**enial of Service（阻斷服務） | 暴力破解攻擊耗盡 API 資源 | 🔴 高 × 🟡 中 = 🔴 高 |
| **E**levation of Privilege（權限提升） | 繞過權限檢查存取管理功能 | 🟡 中 × 🔴 高 = 🔴 高 |

**風險等級**:
- 🔴 高風險：必須立即處理（轉為安全需求 NFR-SEC-xxx）
- 🟡 中風險：應優先處理（Stage 3 架構設計時考慮）
- 🟢 低風險：建議處理（視時程決定）

**4. 產出安全需求清單** (20 分鐘)

將 🔴 高風險威脅轉換為可驗證的安全需求（NFR-SEC-xxx）：

```markdown
### NFR-SEC-001: 認證與授權

**需求來源**: STRIDE 分析 - Spoofing & Elevation of Privilege

**需求描述**:
- 所有 API 請求必須包含有效的 JWT Token
- JWT Token 必須簽名（使用 RS256 或 HS256）
- Token 有效期限：15 分鐘（Access Token）、7 天（Refresh Token）
- 權限檢查：每個 API 端點驗證使用者角色

**驗收標準**:
- [ ] 未認證請求回傳 401 Unauthorized
- [ ] 過期 Token 回傳 401 Token Expired
- [ ] 未授權請求回傳 403 Forbidden
- [ ] 測試案例：嘗試使用一般使用者 Token 呼叫管理員 API

---

### NFR-SEC-002: 輸入驗證與防篡改

**需求來源**: STRIDE 分析 - Tampering

**需求描述**:
- 所有使用者輸入必須驗證（前端 + 後端雙層驗證）
- 防止 SQL Injection（使用 ORM Prepared Statements）
- 防止 XSS（HTML 編碼輸出）
- API Request Schema 驗證（使用 JSON Schema）

**驗收標準**:
- [ ] SQL Injection 測試無效
- [ ] XSS 測試被編碼
- [ ] 不符合 Schema 的 Request 回傳 400
```

**5. 威脅建模檢查清單**

完成威脅建模後，確認：
- [ ] 已識別 3-5 個核心資產
- [ ] 已繪製資料流圖（Level 1）
- [ ] 已標示 3-5 個信任邊界
- [ ] 已執行 STRIDE 分析（至少識別 10 個威脅）
- [ ] 已識別 5-10 個 🔴 高風險威脅
- [ ] 已產出 5-10 個安全需求（NFR-SEC-xxx）
- [ ] 安全需求包含可驗證的驗收標準

**產出文檔**:
- 威脅分析報告（包含 DFD、STRIDE 矩陣、風險評估）
- 安全需求清單（將納入 FRD「非功能性需求」章節）

**預期效益**:
- ✅ 安全需求涵蓋率從 20% 提升至 90%+
- ✅ 上線後安全漏洞數減少 70%
- ✅ 安全審查通過率提升至 95%

---

**完整性評分機制**：
```
完整性分數 = (已確認項目數 / 適用項目數) × 100%

90-100%: ✅ 優秀 - 可進入 PRD 撰寫
70-89%:  ⚠️ 良好 - 補充遺漏項目後進入
<70%:    ❌ 不足 - 需補充關鍵資訊
```

**MoneyTracker 驗證範例**：
- 總適用項目：108 項
- 已確認項目：100 項
- **完整性分數：93%** ✅ 優秀

**產出文件**：
- 需求提取報告 (Requirement Extraction Report)
- 人機協作記錄 (Collaboration Log)
- **標準確認問題回答記錄** (72 問答)
- **需求完整性檢查報告** (120 項檢查結果)

#### 🔄 需求變更回溯機制（後續階段觸發時使用）

> **適用場景**: 當後續階段（Stage 3-11）發現需求遺漏或需要修改時，需透過此機制回溯至 Stage 2 補充。
>
> **觸發條件**:
> - Stage 3 技術選型時發現功能需求描述不足以做技術決策
> - Stage 4 PRD/FRD 撰寫時發現業務規則遺漏
> - Stage 5 架構設計時發現非功能需求未明確（如效能指標、併發量）
> - Stage 6 User Story 撰寫時發現 Acceptance Criteria 無法定義（缺少業務規則）
>
> **回溯流程**:
> 1. 記錄變更來源：哪個階段、哪個 Agent 提出、原因
> 2. 評估影響範圍：僅需補充 vs 需要修改已確認的需求
> 3. 執行補充/修改：回到 Stage 2 相關人機協作點重新確認
> 4. 更新追溯鏈：確保變更反映到所有下游文檔（PRD → FRD → SRD → API）
> 5. 通知相關 Agent：受影響的 Agent 需重新審查其產出
>
> **變更記錄格式**:
> ```
> [REQ-CHG-001] 來源: Stage 5 / SD-Architect (Marcus)
> 原因: 知識管理模組協作編輯併發人數未定義，無法設計 WebSocket 架構
> 影響: NFR 補充（協作編輯最多 10 人同時操作）
> 處理: 回溯 Stage 2 人機協作點 1 補充確認
> ```

---

### 階段 3：技術選型 (2-4 小時)

> 🤖 **Agent 載入時機** - SD-Architect Agent (Marcus) **首次載入**
>
> **觸發時機**: 當階段 3 開始時，SD-Architect Agent (Marcus) 會被載入，負責技術選型和架構決策。
>
> **載入確認訊息**:
> ```
> ✅ SD-Architect Agent (Marcus) 已載入 - 準備進行技術選型
> ```
>
> **主要職責** (階段 3):
> - 平台識別與技術棧選擇
> - 技術架構決策 (ADR - Architecture Decision Record)
> - 技術風險評估
> - 技術成本估算（雲端服務、基礎設施）
> - Specialized Agent 選擇建議 (Web-Architect, Mobile-Architect)
>
> **協作模式**:
> - 與 SA Agent (Amanda) 協作：技術可行性驗證
> - 與 PM/PO Agent (Victoria) 協作：技術選型的商業價值評估
> - **後續階段延續參與**: Stage 4 (技術可行性驗證), Stage 5 (架構設計核心角色), Stage 6-9 (技術諮詢角色)

#### 步驟 3.1：觸發技術選型流程

> 🔧 **Workflow 觸發**: 此階段使用 `requirements-extraction` workflow 的技術需求產出作為輸入
> **建議 Skill**: `/sd-architect`（架構設計與技術選型）、`/sa-analyst`（技術需求確認）

```
執行指令：
「基於以上需求，請進行技術選型分析」
```

> 💡 **技術選型依據**: 確保階段 2 的需求提取已充分完成（功能需求 + 非功能需求），
> 技術選型需以驗證過的需求為基礎，避免先選技術再套需求。

> 🆕 **使用者技術預選驗證流程**（當使用者已指定技術棧時）:
>
> **適用場景**: 使用者在需求描述中已明確指定技術（如「前端用 React + Next.js，後端用 Spring Boot」）
>
> **驗證步驟**:
> 1. **記錄預選技術**: 將使用者指定的技術棧作為「技術約束」記錄
> 2. **需求適配驗證**: SD-Architect (Marcus) 需驗證預選技術是否能滿足 Stage 2 產出的所有需求
>    - ✅ 功能需求：預選技術是否有對應的成熟套件/框架支援
>    - ✅ 非功能需求：效能、併發、安全等指標是否可達成
>    - ✅ 多平台需求：預選技術是否支援所有目標平台
> 3. **風險標記**: 若發現不適配項目，標記為 ⚠️ 風險並提出替代建議
> 4. **人機確認**: 將驗證結果和風險項目回報使用者，由使用者決定是否調整
>
> **範例**:
> ```
> 使用者預選: React (Next.js) + Spring Boot + PostgreSQL
> 驗證結果:
> ✅ 電商模組 - Spring Boot 生態成熟，支援良好
> ✅ CMS 模組 - Next.js SSR/ISR 適合內容類網站
> ⚠️ 知識管理協作編輯 - 需額外評估 WebSocket 框架（Spring WebSocket vs Socket.io）
> ⚠️ macOS App - Next.js 無法直接產出桌面應用，需評估 Electron/Tauri 方案
> ```

#### 步驟 3.2：平台識別與 Agent 選擇

> 📋 **使用工具**:
> - [Platform_Agent_Selection_Guide.md](../../guides/system/agent/Platform_Agent_Selection_Guide.md) - 平台選擇指南
> - [Web_Architecture_Decision_Tree.md](../../guides/system/architecture/Web_Architecture_Decision_Tree.md) - **Web 平台架構決策樹** 🆕

> 🌐 **Web App 專案特別注意**：如果您的專案是 Web App，請務必參考 [Web_Architecture_Decision_Tree.md](../../guides/system/architecture/Web_Architecture_Decision_Tree.md) 進行架構決策（SSR/SSG/SPA/ISR 選擇）。

**平台識別檢查表** (5 個關鍵問題)：

| 問題 | 範例答案 | 建議平台 |
|-----|---------|---------|
| Q1. 使用者主要使用場景？ | 通勤路上、等待結帳時 | Mobile |
| Q2. 是否需要離線功能？ | 是 (需離線記帳) | Native App |
| Q3. 是否需要硬體功能？ | 相機 (拍攝收據)、推送通知 | Native/跨平台 App |
| Q4. 目標使用者裝置分佈？ | iOS + Android 均衡 | 跨平台 Mobile |
| Q5. 預算與時程限制？ | 預算有限、需快速上線 | 跨平台 (React Native/Flutter) |

**決策樹**：
```
使用者主要在哪裡使用此產品？
├─ 📱 手機/平板
│  ├─ 僅 iOS → 原生 iOS (Swift) + Mobile-Architect Agent
│  ├─ 僅 Android → 原生 Android (Kotlin) + Mobile-Architect Agent
│  └─ iOS + Android → 跨平台 Mobile (React Native/Flutter) + Mobile-Architect Agent
├─ 💻 桌機/筆電
│  ├─ 僅瀏覽器 → Web App (React/Vue) + Web-Architect Agent
│  └─ 需離線/硬體 → Desktop App (Electron) + Web-Architect Agent
└─ 🌐 多平台 (Hybrid 場景)
   ├─ Web + Mobile（共享 API） → 詳見「Hybrid 架構決策」
   ├─ Web + Desktop → Web App + Electron
   └─ Mobile + Desktop → 跨平台 Mobile + Electron
```

---

##### 🔄 Hybrid 架構決策指引 (新增 v0.01)

**適用場景判斷**：

當專案符合以下任一條件時，應考慮 Hybrid 混合架構：

1. **多裝置使用需求** - 使用者需要在手機、平板、桌機間切換使用
2. **功能互補需求** - Web 提供管理後台，Mobile 提供使用者端 App
3. **市場擴展需求** - 現有 Web/Mobile 產品需要擴展到另一平台
4. **使用情境差異** - 桌機用於複雜操作，手機用於快速互動

**Hybrid 架構類型**：

| 架構類型 | 說明 | 技術棧建議 | Agent 組合 | 適用場景 |
|---------|------|-----------|-----------|---------|
| **Type A: Web + Mobile (共享後端)** | 共用 Backend API，分別開發前端 | Backend API + Web Frontend + Mobile App | Backend-Architect + Web-Architect + Mobile-Architect | ✅ 最常見（電商、社群、SaaS） |
| **Type B: Web 為主 + Mobile 輕量** | Web 全功能，Mobile 提供核心功能 | Web App (Next.js) + Mobile App (React Native) | Web-Architect (主) + Mobile-Architect (輔) | ⭐ CRM/ERP 企業系統 |
| **Type C: Mobile 為主 + Web 後台** | Mobile 使用者端，Web 管理後台 | Mobile App (Flutter) + Web Admin (React) | Mobile-Architect (主) + Web-Architect (輔) | ⭐ 外送/物流/現場服務 App |
| **Type D: Progressive Web App (PWA)** | 單一程式碼，跨平台執行 | PWA (React/Vue + Service Worker) | Web-Architect + Dev-Senior | ⚠️ 功能要求簡單、預算有限 |

**Hybrid 架構決策流程**：

```mermaid
graph TD
    A[多平台需求] --> B{使用者主要平台?}
    B -->|Web 為主| C{需要 Mobile App?}
    B -->|Mobile 為主| D{需要 Web 管理?}
    B -->|平衡| E{預算與時程?}

    C -->|是，全功能| F[Type A: Web + Mobile 共享後端]
    C -->|是，輕量功能| G[Type B: Web 主 + Mobile 輔]
    C -->|否，但需手機| H[Type D: PWA]

    D -->|是，管理後台| I[Type C: Mobile 主 + Web 後台]
    D -->|是，全功能| F
    D -->|否| J[僅 Mobile App]

    E -->|充足| F
    E -->|有限| H

    F --> K[Backend API + Web Frontend + Mobile App]
    G --> L[Web App Full + Mobile App Lite]
    H --> M[PWA Single Codebase]
    I --> N[Mobile App + Web Admin]
```

**Type A: Web + Mobile (共享後端) - 詳細指引**

> **最推薦的 Hybrid 架構** - 90% 的多平台專案應選擇此方案

**架構組成**：
```
┌─────────────────────────────────────────┐
│          Backend API Layer               │
│   (RESTful/GraphQL + WebSocket)          │
│   Spring Boot / NestJS / FastAPI         │
└───────────┬─────────────────────────────┘
            │
   ┌────────┴────────┐
   │                 │
┌──▼──────────┐  ┌──▼──────────┐
│  Web Client │  │Mobile Client│
│  Next.js    │  │React Native │
│  React      │  │  Flutter    │
└─────────────┘  └─────────────┘
```

**技術棧推薦**：

| 層級 | 推薦技術 | 替代方案 | 選擇理由 |
|-----|---------|---------|---------|
| **Backend API** | NestJS + PostgreSQL + Redis | Spring Boot / FastAPI | TypeScript 全棧統一、模組化、企業級 |
| **Web Frontend** | Next.js 14 + Tailwind CSS | Nuxt 3 / React + Vite | SEO 優化、SSR/SSG、App Router |
| **Mobile App** | React Native + Redux Toolkit | Flutter | 與 Web 共享邏輯、團隊技能復用 |
| **認證授權** | JWT + OAuth 2.0 | Session-based | 跨平台無狀態、可擴展 |
| **即時通訊** | WebSocket (Socket.io) | SSE / Firebase | 雙向通訊、跨平台支援 |

**開發團隊配置**：

| 角色 | 人數 | 職責 | 技能要求 |
|-----|-----|------|---------|
| **Backend Developer** | 2-3 人 | API 開發、資料庫設計、部署維運 | Node.js/Java/Python + SQL + DevOps |
| **Web Frontend Developer** | 2 人 | Web UI/UX、SEO 優化、狀態管理 | React/Vue + Next.js/Nuxt + CSS |
| **Mobile Developer** | 2 人 | Mobile UI/UX、原生功能整合 | React Native/Flutter + iOS/Android |
| **Full-stack Developer** | 1 人 (可選) | 跨平台協調、共享邏輯抽取 | Backend + Frontend + Mobile |

**成本估算係數**：

- **開發成本係數**: 1.8x (相對於單一平台)
  - Backend API: 1.0x
  - Web Frontend: 0.6x
  - Mobile App: 0.8x
  - 整合測試: 0.2x

- **時程估算**: 1.5x (相對於單一平台)
  - 並行開發可降低時程影響
  - 前 2 週先完成 Backend API 設計
  - 第 3-8 週 Web/Mobile 並行開發

**常見挑戰與應對**：

| 挑戰 | 問題描述 | 解決方案 |
|-----|---------|---------|
| **API 版本管理** | Web/Mobile 更新節奏不同 | 使用 API 版本控制 (v1/v2)，保留向下相容 2 版本 |
| **功能差異** | Web 功能豐富，Mobile 功能簡化 | API 設計採用「最大集合」，前端按需使用 |
| **測試複雜度** | 需測試 Web/Mobile/API 三層 | 建立 3 層測試策略：API 單元測試 70%、前端整合測試 20%、E2E 10% |
| **部署協調** | 三端版本需同步 | 建立 Feature Flag 機制，允許分階段發布 |
| **團隊協作** | Backend/Web/Mobile 團隊溝通成本高 | 每日站會 + 每週同步會議 + OpenAPI Spec 作為溝通標準 |

**實施檢查清單**：

架構設計階段（Stage 3）：
- [ ] 已確認 Type A 架構適合專案需求
- [ ] Backend API 設計已完成（RESTful/GraphQL 選擇）
- [ ] 認證授權方案已選定（JWT/OAuth 2.0）
- [ ] WebSocket 即時通訊需求已確認（如需要）
- [ ] API 版本管理策略已定義（v1/v2/v3）
- [ ] Web 與 Mobile 功能範圍已劃分（全功能 vs 核心功能）

團隊配置階段（Stage 3）：
- [ ] Backend Developer 已分配（2-3 人）
- [ ] Web Frontend Developer 已分配（2 人）
- [ ] Mobile Developer 已分配（2 人）
- [ ] Specialized Agents 已選擇（Backend-Architect + Web-Architect + Mobile-Architect）

技術選型階段（Stage 3）：
- [ ] Backend 技術棧已選定並評估（參考上表）
- [ ] Web Frontend 技術棧已選定並評估（參考上表）
- [ ] Mobile 技術棧已選定並評估（參考上表）
- [ ] 團隊技能匹配度 ≥ 70%（需評估學習曲線）
- [ ] 共享邏輯層策略已定義（共用 TypeScript types/API client）
- [ ] 🆕 **v0.01 新增**: 技術選型已進行系統化評估（使用 [Tech_Stack_Selection_Matrix.md](../../guides/system/planning/Tech_Stack_Selection_Matrix.md)）

---

**Type B/C/D 架構簡要指引**：

**Type B: Web 為主 + Mobile 輕量**
- **適用**: CRM、ERP、後台管理系統
- **特徵**: Web 100% 功能，Mobile 提供 30-50% 核心功能
- **技術**: Web App (Next.js) + Mobile App Lite (React Native)
- **團隊**: Web Dev 3 人 + Mobile Dev 1 人
- **成本**: 1.3x（相對於單一 Web）

**Type C: Mobile 為主 + Web 後台**
- **適用**: 外送、物流、現場服務、消費者 App
- **特徵**: Mobile 100% 使用者功能，Web 提供管理後台
- **技術**: Mobile App (Flutter) + Web Admin (React)
- **團隊**: Mobile Dev 3 人 + Web Dev 1 人
- **成本**: 1.3x（相對於單一 Mobile）

**Type D: Progressive Web App (PWA)**
- **適用**: 預算有限、功能簡單、快速上線
- **特徵**: 單一程式碼庫，跨平台執行
- **技術**: React/Vue + Service Worker + PWA Manifest
- **團隊**: Web Dev 2-3 人
- **成本**: 1.1x（相對於純 Web）
- **限制**: 無法使用進階原生功能（藍牙、NFC、背景執行）

**Hybrid 架構 Agent 選擇建議**：

| 架構類型 | Primary Agent | Supporting Agents | 原因 |
|---------|--------------|------------------|------|
| Type A | Backend-Architect | Web-Architect + Mobile-Architect | 共享後端是核心，需專注 API 設計 |
| Type B | Web-Architect | Mobile-Architect (輔) | Web 為主，Mobile 為輔 |
| Type C | Mobile-Architect | Web-Architect (輔) | Mobile 為主，Web 為輔 |
| Type D | Web-Architect | Dev-Senior | PWA 本質是 Web，需前端專家 |

**後續步驟**：

完成 Hybrid 架構決策後，請：
1. 記錄決策理由至「平台識別決策記錄」（步驟 3.4）
2. 更新「技術選型報告」（步驟 3.3）
3. 調整「成本估算」（步驟 3.4），套用對應的成本係數
4. 載入對應的 Specialized Agents（Backend/Web/Mobile Architects）
5. 進入 Stage 4 PRD/FRD 撰寫階段

---

**MoneyTracker 平台決策範例**：
- 使用場景：通勤路上、等待結帳時 → **Mobile**
- 離線功能：需要 → **Native/跨平台 App**
- 硬體功能：相機、推送通知 → **Native/跨平台 App**
- 裝置分佈：iOS + Android 均衡 → **跨平台 Mobile**
- 預算時程：有限 + 快速 → **React Native**
- **最終決策：跨平台 Mobile App (React Native)**
- **Specialized Agent：Mobile-Architect + Dev-Senior**

#### 步驟 3.3：技術棧評估與成本估算

系統會分析並推薦：
- **前端技術** (React/Vue/Angular/Next.js/Nuxt)
- **後端技術** (Node.js/Python/Java/Go/PHP)
- **資料庫** (PostgreSQL/MySQL/MongoDB)
- **基礎設施** (Cloud provider, hosting)
- **第三方服務** (Auth, Payment, Storage)

> 🆕 **企業級/多領域系統「附加技術必填確認清單」** 🔴
>
> 核心三件組（前端/後端/資料庫）之外，企業級系統通常還需要確認以下附加技術。**未確認的項目可能在 Sprint 中臨時引入，導致架構調整和延遲。**
>
> | 附加技術類別 | 觸發條件 | 推薦選項 | 確認 |
> |------------|---------|---------|------|
> | **全文搜尋引擎** | 系統含 CMS/KMS/商品搜尋 | Meilisearch / Elasticsearch | [ ] |
> | **富文本編輯器** | 有內容創作/文章編輯需求 | TipTap / Quill | [ ] |
> | **媒體存儲** | 有圖片/影片上傳需求 | MinIO（自託管）/ AWS S3 | [ ] |
> | **CDN 加速** | 有靜態資源/媒體分發需求 | Cloudflare / CloudFront | [ ] |
> | **快取層** | 高頻讀取、Session 管理 | Redis（強烈推薦）| [ ] |
> | **支付整合** | 電商/訂房付款 | Stripe + `/integration-stripe` | [ ] |
> | **電子發票** | 台灣合規（電商/民宿）| 綠界 / 藍新 | [ ] |
> | **推播通知** | Web Push / Mobile 通知 | Firebase FCM / OneSignal | [ ] |
> | **郵件服務** | 訂單/通知 Email | SendGrid / AWS SES / SMTP | [ ] |
> | **WebSocket** | 即時通訊、庫存即時更新 | Spring WebSocket / Socket.io | [ ] |
> | **訊息佇列** | 非同步處理、搜尋索引同步 | RabbitMQ（MVP 推薦）/ Kafka | [ ] |
> | **日曆/預約引擎** | 民宿/場地預約管理 | FullCalendar + PostgreSQL 並發控制 | [ ] |
>
> **🔴 規則**：所有「已選定」項目必須在 Stage 3.4 確認點一併列出，否則後續 Stage 5 架構設計可能不完整。

**📊 技術棧評估表格（依平台類型）**

根據您在步驟 3.2 選定的平台類型，參考以下對應的技術評估表格：

##### 🌐 Web App 技術評估表格

| 技術類別 | 選項 | 優點 | 缺點 | 適用情境 |
|---------|------|------|------|---------|
| **前端框架** | React 18 | 生態系豐富、招募容易、社群活躍 | 樣板代碼多、配置複雜 | ✅ 通用推薦（中大型專案） |
| | Vue 3 | 學習曲線平緩、文件完善、輕量 | 生態系較小、大型專案工具鏈弱 | ⭐ 小型專案、快速開發 |
| | Angular 17 | 完整框架、TypeScript 原生、企業級 | 學習曲線陡峭、程式碼量大 | ⚠️ 大型企業專案 |
| **SSR 框架** | Next.js 14 | SEO 優化、App Router、ISR 支援 | 學習曲線、伺服器成本 | ✅ 需 SEO 的 Web App |
| | Nuxt 3 | Vue 生態、SSR/SSG 彈性、Nitro 引擎 | 生態系較小 | ⭐ Vue 團隊、需 SEO |
| **狀態管理** | Redux Toolkit | 成熟穩定、DevTools 完善 | 樣板代碼多、學習曲線 | ✅ 複雜狀態管理 |
| | Zustand | 輕量、API 簡潔、TypeScript 友善 | 社群較小、中間件少 | ⭐ 中小型專案 |
| | Pinia | Vue 官方推薦、TypeScript 支援 | 僅限 Vue | ✅ Vue 專案首選 |
| **UI 組件庫** | Ant Design | 企業級、組件豐富、中文友善 | 體積大、定製困難 | ✅ 後台管理系統 |
| | Material-UI | Material Design、客製化強 | 學習曲線、打包體積 | ⭐ C2C/B2B 平台 |
| | Tailwind CSS | 高效、體積小、設計靈活 | 需學習 utility-first | ✅ 現代 Web 開發推薦 |
| **後端框架** | Spring Boot | 企業級、生態成熟、安全性佳 | 開發速度慢、資源消耗高 | ✅ 大型企業專案 |
| | Node.js + Express | 輕量、全端 JS、快速開發 | 單執行緒、需處理並發 | ⭐ 中小型專案、Prototype |
| | NestJS | TypeScript、模組化、企業級 | 學習曲線、較重 | ✅ Node.js 企業專案 |
| **資料庫** | PostgreSQL | 功能豐富、ACID、擴展性佳 | 配置複雜、學習曲線 | ✅ 通用推薦 |
| | MySQL | 成熟穩定、社群大、招募容易 | 功能較少、擴展性弱 | ⭐ 中小型專案 |
| | MongoDB | 靈活 Schema、水平擴展、開發快 | 無 ACID、數據一致性弱 | ⚠️ 非關聯數據、原型開發 |

> 🆕 **富文本編輯器選型提示**（適用於內容編輯/CMS/KMS 系統）:
>
> | 編輯器 | 優勢 | 劣勢 | 適用場景 |
> |-------|------|------|---------|
> | **TipTap** | Headless 架構、協作編輯友善（Y.js）、Vue/React/Svelte 支援、擴展性佳 | 文檔相對簡單、部分功能需付費（TipTap Cloud） | ✅ 推薦內容管理系統、協作編輯 |
> | **ProseMirror** | 底層引擎強大、高度可自訂、精確控制 DOM | 配置複雜、學習曲線陡峭、需大量開發 | ⭐ 追求完全控制、大型編輯器專案 |
> | **Slate** | React 原生友善、高自訂性、插件架構 | 文檔較少、需自行開發基礎功能、API 不穩定 | ⭐ React 專案、需高度客製化 |
> | **Quill** | 簡單易用、開箱即用、社群成熟 | 功能相對基礎、深度定制困難、架構較舊 | ⚠️ 簡單內容編輯、快速原型 |
>
> **AI 選型建議**: 若需要協作編輯功能，首選 TipTap（基於 ProseMirror）；若需完全控制，直接使用 ProseMirror；簡單場景可選 Quill。

##### 📱 Mobile App 技術評估表格

| 技術類別 | 選項 | 優點 | 缺點 | 適用情境 |
|---------|------|------|------|---------|
| **跨平台框架** | React Native | 單一程式碼、社群大、熱更新 | 效能稍差、原生整合複雜 | ✅ 通用推薦（中型專案） |
| | Flutter | 效能佳、UI 美觀、熱重載 | Dart 學習曲線、生態系較小 | ⭐ 重視 UI/UX 的專案 |
| | Ionic | Web 技術、快速開發、跨平台 | 效能最差、原生感弱 | ⚠️ 簡單 App、快速原型 |
| **原生開發** | Swift (iOS) | 效能最佳、系統整合完美 | 僅限 iOS、開發成本高 | ⚠️ 僅 iOS 且重視效能 |
| | Kotlin (Android) | 效能最佳、系統整合完美 | 僅限 Android、開發成本高 | ⚠️ 僅 Android 且重視效能 |
| **狀態管理** | Redux / Redux Toolkit | 成熟穩定、可預測 | 樣板代碼多 | ✅ React Native 推薦 |
| | MobX | 簡單易用、響應式 | 除錯困難、魔法較多 | ⭐ 中小型專案 |
| | Riverpod | 編譯安全、測試友善 | Flutter 專用、學習曲線 | ✅ Flutter 推薦 |
| **本地存儲** | Realm | 效能佳、離線優先、同步方便 | 學習曲線、遷移困難 | ✅ 需離線功能 |
| | SQLite | 輕量、跨平台、穩定 | 功能較少、手動管理 | ⭐ 簡單數據存儲 |
| | AsyncStorage | 簡單、原生支援 | 效能差、無加密 | ⚠️ 僅存簡單設定 |
| **推送通知** | Firebase Cloud Messaging | 免費、跨平台、穩定 | 需 Google 服務 | ✅ 通用推薦 |
| | OneSignal | 功能豐富、分析完善 | 付費方案、複雜配置 | ⭐ 需進階推送功能 |

##### 🖥️ Backend API 技術評估表格

| 技術類別 | 選項 | 優點 | 缺點 | 適用情境 |
|---------|------|------|------|---------|
| **API 框架** | Spring Boot | 企業級、安全、生態成熟 | 開發速度慢、資源重 | ✅ 大型企業 API |
| | NestJS | TypeScript、模組化、裝飾器 | Node.js 單執行緒限制 | ✅ Node.js 企業 API |
| | FastAPI | 高效能、自動文件、Type Hints | Python 非同步生態不成熟 | ⭐ AI/ML API、快速開發 |
| | Express.js | 輕量、靈活、快速 | 缺乏標準結構、需自行組織 | ⚠️ 原型開發、小型 API |
| | Go + Gin | 高效能、並發佳、編譯型 | 學習曲線、生態系較小 | ⭐ 高並發、微服務 |
| **API 規範** | RESTful API | 成熟、廣泛支援、易理解 | 過度獲取/不足、版本管理 | ✅ 通用推薦 |
| | GraphQL | 精確查詢、類型系統、單端點 | 複雜度高、快取困難 | ⭐ 複雜數據關聯 |
| | gRPC | 高效能、雙向串流、Protocol Buffers | HTTP/2 需求、除錯困難 | ⚠️ 微服務間通訊 |
| **認證授權** | JWT + Redis | 無狀態、可擴展、效能佳 | Token 管理、刷新機制 | ✅ 通用推薦 |
| | OAuth 2.0 | 標準化、第三方登入 | 配置複雜、安全風險 | ⭐ 需第三方登入 |
| | Session-based | 簡單、安全 | 伺服器狀態、擴展困難 | ⚠️ 小型單體應用 |
| **資料庫** | PostgreSQL | 功能豐富、JSONB、效能佳 | 配置複雜 | ✅ 通用推薦 |
| | MySQL | 成熟、穩定、招募容易 | 功能較少 | ⭐ 中小型專案 |
| | MongoDB | Schema 靈活、水平擴展 | 無 ACID、一致性弱 | ⚠️ 非關聯數據 |

> 🆕 **搜尋引擎選型提示**（適用於需要全文搜尋的系統）:
>
> | 搜尋引擎 | 優勢 | 劣勢 | 適用場景 |
> |---------|------|------|---------|
> | **Elasticsearch** | 功能豐富、分散式架構、支援複雜聚合查詢、生態完善（ELK Stack） | 配置複雜、資源消耗大（記憶體 2GB+）、學習曲線陡 | ✅ 企業級內容管理、日誌分析、大規模知識庫 |
> | **Meilisearch** | 輕量級、開箱即用、搜尋體驗極佳（typo-tolerance）、RESTful API | 功能相對簡單、不支援複雜聚合、擴展能力有限 | ⭐ 中小型內容平台、產品搜尋、知識庫 |
> | **PostgreSQL FTS** | 無額外服務、與資料庫整合、維運簡單 | 功能有限（無同義詞/模糊匹配）、大資料量效能差 | ⚠️ 小型系統、搜尋需求簡單 |
> | **Algolia** | SaaS 即用、搜尋體驗最佳、全球 CDN | 付費成本高（按搜尋量計費）、資料需同步至外部、廠商鎖定 | ⭐ 偏好 SaaS 方案、預算充足 |
>
> **AI 選型建議**: 若系統以「內容搜尋」為核心功能（如 CMS/KMS），建議 Elasticsearch 或 Meilisearch；若搜尋僅為輔助功能，PostgreSQL FTS 即可滿足。

> 🆕 **媒體存儲與 CDN 方案選型提示**（適用於含媒體資產的系統）:
>
> | 存儲方案 | 優勢 | 劣勢 | 適用場景 |
> |---------|------|------|---------|
> | **AWS S3** | 功能完整、全球可用、與 CloudFront 整合、99.999999999% 耐久性 | 成本複雜（按量計費）、需 IAM 配置 | ✅ 企業級方案、AWS 生態 |
> | **MinIO** | S3 API 相容、可自託管、開源免費 | 需自行維運、擴展需規劃 | ⭐ 私有部署、成本敏感 |
> | **Cloudflare R2** | S3 相容、零出口費用、全球邊緣 | 功能較新、生態尚在成長 | ⭐ 出口流量大的場景 |
>
> | CDN 方案 | 優勢 | 劣勢 | 適用場景 |
> |---------|------|------|---------|
> | **CloudFront** | AWS 原生整合、Lambda@Edge 可程式化 | 費用較高、配置複雜 | ✅ AWS 生態 |
> | **Cloudflare** | 性價比高、免費方案足夠、安全防護完整 | 進階功能需付費 | ⭐ 推薦通用方案 |
>
> **AI 選型建議**: 若已使用 AWS，首選 S3 + CloudFront；若注重成本，考慮 MinIO + Cloudflare。媒體處理建議使用 Sharp（Node.js 圖片處理）或 FFmpeg（影片轉碼）。

| **快取** | Redis | 高效能、資料結構豐富、Pub/Sub | 記憶體成本、持久化限制 | ✅ 通用推薦 |
| | Memcached | 極簡、高效、穩定 | 功能單一、無持久化 | ⭐ 簡單快取需求 |
| **訊息佇列** | RabbitMQ | 功能豐富、可靠、AMQP 標準 | 配置複雜、效能中等 | ✅ 企業級非同步處理 |
| | Kafka | 高吞吐、持久化、分散式 | 配置複雜、資源消耗大 | ⭐ 大數據、事件溯源 |
| | Redis Streams | 輕量、與 Redis 整合 | 功能較少、社群小 | ⚠️ 簡單非同步任務 |

##### ☕ Java/Spring Boot 生態系統評估（企業級推薦）

> 💡 Spring Boot 是企業級後端的主流選擇，以下為常用技術組合評估：

| 技術類別 | 推薦選項 | 說明 | 替代方案 |
|---------|---------|------|---------|
| **建置工具** | Gradle (Kotlin DSP) | 效能優、彈性大 | Maven（穩定、生態成熟） |
| **ORM** | Spring Data JPA + Hibernate | 標準 JPA 實作、自動 CRUD | MyBatis（SQL 控制力強）|
| **資料庫遷移** | Flyway | 簡潔、Spring Boot 原生整合 | Liquibase（XML/YAML 格式）|
| **安全框架** | Spring Security + JWT | 企業級認證授權 | Apache Shiro |
| **API 文件** | SpringDoc OpenAPI (Swagger) | 自動生成 API 文件 | Spring REST Docs |
| **快取** | Spring Cache + Redis | 註解式快取、效能佳 | Caffeine（本地快取）|
| **訊息佇列** | Spring AMQP + RabbitMQ | 企業級非同步處理 | Spring Kafka |
| **測試框架** | JUnit 5 + Mockito + TestContainers | 完整測試覆蓋 | Spock (Groovy) |
| **監控** | Spring Actuator + Micrometer | 內建健康檢查、指標 | - |
| **日誌** | SLF4J + Logback | Spring Boot 預設 | Log4j2 |

**Spring Boot 專案結構範例**:
```
src/
├── main/java/com/example/invmaster/
│   ├── config/          # 配置類 (Security, CORS, etc.)
│   ├── controller/      # REST API Controller
│   ├── service/         # 業務邏輯 Service
│   ├── repository/      # JPA Repository
│   ├── model/           # Entity / DTO
│   ├── exception/       # 自訂例外處理
│   └── util/            # 工具類
└── test/java/           # 測試（與 main 結構對映）
```

##### 🔄 全端應用（Full-stack）技術組合建議

| 技術組合 | 前端 | 後端 | 資料庫 | 優點 | 適用情境 |
|---------|------|------|--------|------|---------|
| **MERN Stack** | React + Next.js | Node.js + Express | MongoDB | 全 JavaScript、快速開發 | ⭐ 原型開發、小型專案 |
| **MEAN Stack** | Angular | Node.js + Express | MongoDB | 企業級前端、TypeScript | ⚠️ 大型企業前端需求 |
| **T3 Stack** | React + Next.js | tRPC + Prisma | PostgreSQL | Type-safe、現代化、效率高 | ✅ 現代全端開發推薦 |
| **Java Full-stack** | React/Vue | Spring Boot | PostgreSQL/MySQL | 企業級、安全、成熟 | ✅ 大型企業專案 |
| **Next.js + Spring Boot** | React (Next.js) | Spring Boot | PostgreSQL | SSR/SSG + 企業級後端、前後端分離 | ✅ 企業級 Web + API 系統（經銷存/ERP） |
| **Python Full-stack** | React/Vue | FastAPI/Django | PostgreSQL | AI/ML 整合、快速開發 | ⭐ AI/ML 專案、數據密集 |

**🎯 技術選型決策指引**

> 📋 **使用工具**: [Tech_Stack_Selection_Matrix.md](../../guides/system/planning/Tech_Stack_Selection_Matrix.md) - 技術選型評估矩陣 🆕 (v0.01 新增)
>
> **重要**: 對於重大技術選型決策（Backend/Database/Cloud Provider），建議使用評估矩陣進行系統化評估，確保考慮所有關鍵維度。

選擇技術棧時，請綜合考慮以下因素（按重要性排序）：

1. **功能性** (30%)：是否滿足核心功能需求、支援未來擴展
2. **成本** (25%)：TCO 3 年總持有成本（授權+雲端+開發+維護）
3. **學習曲線** (20%)：團隊現有技能與學習曲線
4. **社群支援** (15%)：生態系統成熟度、招募容易度、長期維護性
5. **風險評估** (10%)：技術成熟度、供應商風險、遷移風險

**💰 技術選型成本評估矩陣** 🆕 (v0.01 新增)

針對每個技術選項，使用以下矩陣進行成本評估：

| 成本維度 | 評估項目 | 計算方式 | 權重 |
|---------|---------|---------|------|
| **授權費用** | 軟體授權、訂閱費 | 年度費用 × 使用年限 | 20% |
| **雲端成本** | 運算、儲存、網路 | 月費 × 12 × 使用年限 | 30% |
| **開發成本** | 人力 × 時間 | 人日單價 × 預估工時 | 25% |
| **維護成本** | 更新、監控、支援 | 年度開發成本 × 15-20% | 15% |
| **學習成本** | 培訓、上手時間 | 人數 × 學習週數 × 週薪 | 10% |

**技術選項成本比較範例**：

| 技術選項 | 授權費/年 | 雲端成本/月 | 學習曲線 | 開發效率 | TCO 3年 |
|---------|----------|------------|---------|---------|---------|
| **React + Node.js** | $0 (OSS) | $50-200 | 中 (4週) | 高 | ⭐ $15,000-25,000 |
| **Angular + Java** | $0 (OSS) | $100-300 | 高 (8週) | 中 | $25,000-40,000 |
| **Vue + Python** | $0 (OSS) | $50-150 | 低 (2週) | 高 | ⭐ $12,000-20,000 |
| **.NET + Azure** | $0-500 | $150-400 | 中 (6週) | 中 | $30,000-50,000 |

**成本紅旗警示** ⚠️：
- 授權費超過年度預算 20% → 考慮開源替代方案
- 學習成本超過 3 個月 → 評估團隊技能匹配度
- 雲端成本年增超過 50% → 檢視架構可擴展性
- 單一供應商依賴超過 80% → 評估 Vendor Lock-in 風險

🆕 **企業級系統成本估算範例**（中型經銷存系統）:

| 成本項目 | 細項 | 月費/一次性 | 3 年 TCO |
|---------|------|-----------|---------|
| **雲端基礎設施** | AWS EC2 (t3.large×2) + RDS (db.r5.large) + ElastiCache | ~$400/月 | $14,400 |
| **儲存與 CDN** | S3 (100GB) + CloudFront | ~$30/月 | $1,080 |
| **開發人力** | 2 人團隊 × 6 個月開發 | 一次性 | $60,000-90,000 |
| **維護與監控** | Datadog/CloudWatch + 年維護 15% | ~$200/月 + 年維護 | $7,200 + $9,000-13,500 |
| **第三方服務** | 電子發票 API、簡訊通知、郵件服務 | ~$100/月 | $3,600 |
| **Mobile 開發** | Android + macOS（Phase 2） | 一次性 | $30,000-50,000 |
| **合計** | | | **$125,280 - $192,780** |

> 💡 **對比**: 小型 App（如 MoneyTracker）TCO 約 $12,000-25,000；中型企業系統（如經銷存）TCO 約 $125,000-190,000，差距主要來自開發人力和多平台需求。

**📋 技術選型報告範本**

完成技術評估後，請產出以下報告：

```markdown
## 技術選型報告

### 1. 平台類型
- 選定平台：[Web App / Mobile App / Backend API / Full-stack]
- 選擇理由：[依據步驟 3.2 平台識別結果]

### 2. 推薦技術棧
- 前端框架：[選項] - 理由：[...]
- 後端框架：[選項] - 理由：[...]
- 資料庫：[選項] - 理由：[...]
- 其他技術：[快取/訊息佇列/...]

### 3. 替代方案對比
| 技術類別 | 推薦方案 | 替代方案 | 選擇理由 |
|---------|---------|---------|---------|
| ... | ... | ... | ... |

### 4. 團隊技能評估
- 現有技能：[...]
- 需學習技術：[...]
- 學習曲線評估：[低/中/高]
- 預估學習時間：[X 週]

### 5. 技術風險評估
- 技術成熟度：[成熟/中等/新興]
- 社群支援：[活躍/中等/小]
- 招募難度：[容易/中等/困難]
- 長期維護風險：[低/中/高]

### 6. Specialized Agent 建議
- 需引入的 Specialized Agent：[Web-Architect / Mobile-Architect / ...]
- 引入時機：[Stage X]
- 協作重點：[...]
```

> 📋 **使用工具**: [Cost_Estimation_Template.md](checklists/Cost_Estimation_Template.md)

**完整成本估算模板**，涵蓋 5 大成本類別：

| 成本類別 | 項目 | MoneyTracker 範例 |
|---------|-----|------------------|
| **1. 開發成本** | 人力成本、設計成本、測試成本 | $68,000 (首年) |
| **2. 雲端服務成本** | AWS/GCP/Azure 服務費用 | $8,340 (首年) |
| **3. 開發者帳號成本** | App Store, Google Play | $124 (首年) |
| **4. 基礎設施成本** | 網域、SSL、CDN | $228 (首年) |
| **5. 維護成本** | 年度維護、更新、支援 | $48,000 (後續年度) |

**MoneyTracker 成本範例**：
- **首年總成本**：$124,590
- **後續年度成本**：$41,293
- **使用者規模成長成本**：詳見成本成長試算表

**雲服務成本計算器**：
- AWS Pricing Calculator: https://calculator.aws/
- Azure Pricing Calculator: https://azure.microsoft.com/pricing/calculator/
- GCP Pricing Calculator: https://cloud.google.com/products/calculator

🆕 **預約/訂房引擎技術選型提示**（適用於旅宿/租賃/場地預約系統）:

> 💡 若系統包含「日曆型預約」功能，技術選型需額外考慮以下組件：

| 組件 | 選項 | 考量因素 |
|------|------|---------|
| **日曆 UI 元件** | FullCalendar / react-big-calendar / 自建 | 是否需要拖拉調整、多月檢視、房態色碼 |
| **並發控制** | DB 鎖（PostgreSQL FOR UPDATE）/ Redis 分散式鎖 / 訊息佇列 | 併發量級、部署架構（單節點 vs 多節點） |
| **價格引擎** | 規則引擎（Drools/自建）/ 設定表驅動 | 定價規則複雜度、是否需動態定價 |
| **渠道管理** | Channel Manager API / 自建同步 / SaaS（如 SiteMinder） | OTA 渠道數量、同步即時性要求 |

#### 步驟 3.4：技術選型確認點 🔴

系統會呈現：
1. **平台選擇決策** (Web/Mobile/Desktop/混合)
2. **推薦技術棧** (含理由)
3. **替代方案對比** (原生 vs 跨平台)
4. **學習曲線評估** (團隊技能匹配度)
5. **完整成本估算** (首年 + 後續年度 + 成長成本)
6. **Specialized Agent 建議** (需引入哪些專業 Agent)

你需要選擇或調整推薦方案。

**產出文件**：
- 技術選型報告 (Tech Stack Selection Report)
- 技術風險評估 (Technical Risk Assessment)
- **平台識別決策記錄** (Platform Selection Decision)
- **完整成本估算報告** (5 大類別成本明細)
- **Agent 協作計畫** (Specialized Agent 分工)

---

### 階段 4：需求驗證與文件化 (3-5 小時)

> 💡 **階段 4 與階段 6 的 User Story 定位釐清** 🆕
>
> | 項目 | 階段 4（本階段）| 階段 6 |
> |------|---------------|--------|
> | **目的** | 需求驗證、PRD/FRD 文件化 | 詳細 User Story 撰寫 |
> | **User Story 深度** | 初步識別 Epic 和高層 Story（用於需求完整性驗證）| 完整拆分 EPIC → US → AC → AT |
> | **產出** | PRD、FRD、MVP 範圍、初步 AC | 完整 User Stories、Story Points、依賴關係圖 |
> | **為什麼分兩階段** | 先驗證需求正確性和完整性，再投入詳細撰寫 | 基於已確認的 PRD/FRD + SRD/API 進行精確拆分 |

> 🤖 **Agent 載入時機** - QA Agent (Quincy) **首次載入**
>
> **觸發時機**: 當階段 4 開始需求驗證與文件化時，QA Agent (Quincy) 會被載入，負責品質標準制定和需求可測試性驗證。
>
> **載入確認訊息**:
> ```
> ✅ QA Agent (Quincy) 已載入 - 準備定義驗收準則
> ```
>
> **主要職責** (階段 4):
> - 定義驗收準則 (Acceptance Criteria)
> - 測試場景設計
> - 品質標準制定
> - 需求可測試性驗證
> - 測試策略規劃
>
> **協作模式**:
> - 與 **SA Agent (Amanda)** 協作：需求完整性驗證
> - 與 **BA Agent (Beatrice)** 協作：業務驗收標準確認
> - 與 **SD-Architect (Marcus)** 協作：架構可測試性評估
> - 與 **PM/PO Agent (Victoria)** 協作：品質標準優先級
> - **後續階段延續參與**: Stage 7 (文檔品質檢查), Stage 9 (最終驗收)

> 🤖 **Agent 參與角色** - SD-Architect Agent (Marcus) **技術可行性驗證**
>
> **參與狀態**: SD-Architect Agent (Marcus) 在此階段參與**技術可行性驗證**，評估需求的技術實現複雜度。
>
> **主要職責** (階段 4):
> - 評估技術實現複雜度和可行性
> - 識別技術風險和挑戰
> - 提供技術實現時間和資源估算建議
> - 驗證技術架構能否支撐需求
> - 參與 MVP 範圍技術評估
>
> **協作模式**:
> - 與 **SA Agent (Amanda)** 協作：需求完整性驗證
> - 與 **BA Agent (Beatrice)** 協作：業務可行性驗證
> - 與 **QA Agent (Quincy)** 協作：需求可測試性驗證
> - 與 **PM/PO Agent (Victoria)** 協作：MVP 範圍技術評估

#### 步驟 4.1：觸發驗證流程
```
執行指令：
「請對需求進行深度驗證並生成正式文件」
```

#### 步驟 4.2：正式 MVP 範圍界定（若階段 2 已確認需要）

> **前置條件**: 階段 2 人機協作點 5 已確認需要 MVP

> 📋 **使用工具**: [MVP_Definition_Template.md](../../docs_template/prd/MVP_Definition_Template.md)

**執行內容**:

**1. 多維度驗證**

**完整性驗證** (SA Agent)
- 檢查需求是否完整無遺漏
- 驗證邏輯一致性
- 確認使用者故事完整性

**業務價值驗證** (PM/PO Agent)
- 評估每個功能的業務價值
- 使用 RICE 模型進行功能優先級評分
- 使用 Kano 模型分類功能
- 確認 MVP 範圍

**2. 使用 MVP 定義模板**

**MVP 定義模板**包含：

**1. MVP 目標與成功指標**
- 產品願景（一句話描述）
- 目標使用者群體
- 3 個核心目標與成功指標

**2. RICE 評分與 Kano 分類**

> 📋 **使用工具**:
> - [RICE_Scoring_Template.md](../checklists/RICE_Scoring_Template.md) - RICE 評分範本（詳細計算流程與案例）
> - [Kano_Model_Guide.md](../../guides/system/planning/Kano_Model_Guide.md) - **🆕 Kano 模型完整指引**（問卷設計、結果分析、與 RICE 整合）

**RICE 評分法** (Reach × Impact × Confidence / Effort):
- Reach (觸及人數): 預估使用此功能的使用者數量
- Impact (影響程度): 對使用者的影響 (3=巨大, 2=高, 1=中, 0.5=低, 0.25=微小)
- Confidence (信心指數): 估算的可信度 (100%=高, 80%=中, 50%=低)
- Effort (工作量): 預估開發所需人月
- **RICE 分數 = (R × I × C) / E**

**Kano 模型分類** (快速參考):
- 🔴 **必備型 (Must-be)**: 缺少會不滿,具備不會特別滿意 → **Phase 1 (MVP) 必須包含**
- 🟡 **期望型 (One-dimensional)**: 越好越滿意 → **Phase 1 (Top 30%) 或 Phase 2**
- 🟢 **魅力型 (Attractive)**: 有會驚喜,沒有也不會不滿 → **Phase 2 或 Phase 3**（可選 1 個高分魅力型放 Phase 1 作為產品亮點）
- ⚪ **無差異 (Indifferent)**: 有沒有都一樣 → **不開發**（浪費資源）
- 🔵 **反向 (Reverse)**: 有了反而不滿 → **絕對不開發**（負面影響）

**💡 Kano 與 RICE 整合應用**：

| Kano 分類 | RICE 分數 | Phase 分配 | 理由 |
|----------|----------|----------|------|
| 🔴 必備型 | 任何分數 | **Phase 1** | 缺少會導致產品無法使用 |
| 🟡 期望型 | ≥ 70th percentile | **Phase 1** | 高價值期望型，必須優先開發 |
| 🟡 期望型 | 30-70th percentile | **Phase 2** | 中等價值期望型，強化產品體驗 |
| 🟡 期望型 | <30th percentile | **Phase 3** | 低價值期望型，視資源決定是否開發 |
| 🟢 魅力型 | ≥ 2000 | **Phase 1** (可選 1 個) | 高價值魅力型，作為產品亮點 ⭐ |
| 🟢 魅力型 | 1000-2000 | **Phase 2** | 中等價值魅力型，提升使用者驚喜感 |
| 🟢 魅力型 | <1000 | **Phase 3** | 創新實驗，視預算決定 |
| ⚪ 無差異 | 任何分數 | **不開發** | 浪費資源 |
| 🔵 反向 | 任何分數 | **不開發** | 負面影響 |

**🎯 建議執行流程**（總時程約 1 週）：

1. **列出候選功能清單**（15 分鐘）- 從 Stage 2 產出的功能清單整理
2. **設計 Kano 問卷**（30 分鐘）- 每個功能 2 題（正向 + 反向），建議 10-15 個功能
3. **發放問卷給目標使用者**（3-7 天）- 目標 30-50 位受訪者
   > 🆕 **小團隊替代方案**（< 5 人團隊或無法取得大量受訪者時）：
   > - **專家評估法**: 由 PM/PO + 1-2 位領域專家，針對每個功能直接判斷 Kano 分類
   > - **利害關係人深度訪談**: 訪談 3-5 位關鍵使用者（1 小時/人），取代大量問卷
   > - **競品分析法**: 分析 3-5 個競品的功能覆蓋度，推斷必備型/期望型/魅力型
   > - **AI 輔助分類**: 請 AI Agent 依據需求描述和產業慣例，提出 Kano 分類建議，再由人類確認
4. **分析問卷結果，歸類功能**（2 小時）- 使用 Kano 分類判斷表
5. **計算 RICE 分數**（1 小時）- 團隊估算 Reach/Impact/Confidence/Effort
6. **制定 MVP Phase 分配**（30 分鐘）- 結合 Kano 分類 + RICE 排序

**📚 詳細說明與範例**：請參考 [Kano_Model_Guide.md](../../guides/system/planning/Kano_Model_Guide.md)，包含：
- Kano 模型理論詳解（5 種分類的判斷標準）
- Kano 問卷設計範本（完整問卷範例）
- Kano 結果分析與解讀（分類判斷表、統計方法）
- 與 RICE 整合的完整案例分析（B&B 民宿平台 20 個功能完整分析）
- 常見問題 FAQ（7 個常見疑問解答）

**3. MVP 範圍定義 (3 Phases)**

| Phase | 目標 | 功能範圍 | 時程 |
|-------|-----|---------|-----|
| **Phase 1 (MVP)** | 最小可行產品，驗證核心假設 | 必備型 + RICE Top 30% 期望型 | 2-3 個月 |
| **Phase 2** | 強化核心體驗，增加使用者黏性 | RICE 30-70% 期望型 + 高分魅力型 | 3-4 個月 |
| **Phase 3** | 差異化功能，提升競爭力 | RICE <30% 期望型 + 創新魅力型 | 待定 |

🆕 **多領域 MVP 定義策略**（適用於跨領域融合系統）:

> 💡 當系統涉及多個業務領域（如「電商 + 民宿」、「零售 + 物流」）時，
> MVP 不能只看整體 RICE 分數排序，需**按領域分別評估**後再合併優先級。

**Step 1: 按領域分別列出必備功能**

| 領域 | 必備型功能（Must-be） | 說明 |
|------|---------------------|------|
| 電商領域 | 商品管理、購物車、訂單流程、庫存扣減 | 缺少任一即無法交易 |
| 民宿領域 | 房型管理、日曆可用性、訂房流程、入住退房 | 缺少任一即無法營運 |
| 共用基礎 | 會員系統、支付整合、通知系統 | 兩領域共同依賴 |

**Step 2: 識別跨領域 MVP 衝突**

> 🔴 **常見衝突場景**:
> - 兩個領域各自的 Must-be 加起來已超出 MVP 開發量
> - 共用基礎設施（如支付）需同時滿足兩個領域的不同需求
> - 領域 A 的 MVP 功能依賴領域 B 的非 MVP 功能

**衝突解決策略**:

| 策略 | 適用情況 | 做法 |
|------|---------|------|
| **分領域 MVP** | 兩領域可獨立運作 | 先上線領域 A MVP → 再上線領域 B MVP |
| **共用核心 MVP** | 兩領域高度耦合 | Phase 1 只做共用基礎 + 各領域最小必備 |
| **主次領域法** | 一個領域為主營業務 | 主領域完整 MVP + 次領域僅核心 1-2 功能 |

**Step 3: 跨領域 RICE 調整**

在計算 RICE 分數時，為跨領域共用功能加入**領域覆蓋加成**：
- 覆蓋 1 個領域：標準 RICE 分數
- 覆蓋 2 個領域：RICE × 1.3（30% 加成）
- 覆蓋 3+ 個領域：RICE × 1.5（50% 加成）

> 原因：共用功能的投資報酬率更高，應優先開發。

**MoneyTracker MVP 範例**：
- **Phase 1 功能** (37 Story Points, 4 週):
  - F-001: 快速記帳 (8 SP) - 必備型
  - F-002: 支出總覽 (3 SP) - 必備型
  - F-003: 分類統計圖表 (8 SP) - 期望型, RICE=747

- **Phase 2 功能** (37 Story Points, 4 週):
  - F-004: 預算設定與提醒 (8 SP) - 期望型, RICE=700
  - F-007: 雲端備份與同步 (13 SP) - 魅力型, RICE=360

**4. 明確排除的功能 (Out of Scope)**
- F-015: 投資理財功能（超出產品定位）
- F-016: 信用卡自動同步（法規風險高）
- F-017: Web 版網站（資源有限，先專注 Mobile）

**技術可行性驗證** (SD Agent)
- 評估技術實現複雜度
- 識別技術風險
- 時間和資源評估

> 📋 **參考工具**: [Estimation_Standards.md](../../guides/system/planning/Estimation_Standards.md)

使用 **估算標準化指南** 評估開發工作量：
- Story Points 估算 (1-21 SP)
- Planning Poker 方法
- 三點估算法 (樂觀/可能/悲觀)
- 估算影響因子 (複雜度、學習曲線、風險)

**產出文件**:
- MVP_Definition.md（使用 MVP_Definition_Template.md）
- 功能優先級清單（RICE 評分結果）
- Phase 1/2/3 功能分配表
- 時程規劃表

**時間**: 30-45 分鐘

> 💡 **兩階段 MVP 界定法**：
>
> - **階段 2 人機協作點 5**：初步 MVP 意向確認（10 分鐘）
>   - 快速決定是否需要 MVP
>   - 記錄初步核心功能意向
>
> - **階段 4 步驟 4.2**：正式 MVP 範圍界定（30-45 分鐘）
>   - 使用 RICE 模型量化評分
>   - 使用 Kano 模型分類功能
>   - 產出正式 MVP 定義文件
>
> **優點**: 避免階段 2 花費過多時間在詳細評估，同時確保 MVP 範圍經過嚴謹分析

#### 步驟 4.3：統一 ID 命名規範

> 📋 **使用工具**: [AISDLC_ID_Naming_Convention.md](../../guides/system/naming/AISDLC_ID_Naming_Convention.md)

在撰寫 PRD/FRD 時，使用 **10 種統一 ID 命名規範**：

| ID 類型 | 格式 | 範例 | 使用階段 | 文檔 |
|---------|------|------|---------|------|
| **Feature ID** | F-XXX | F-001 | 階段 4 | PRD |
| **Non-Functional Req ID** | NFR-XXX | NFR-001 | 階段 4 | PRD |
| **Business Rule ID** | BR-XXX | BR-001 | 階段 4 | FRD |
| **Epic ID** | EPIC-XXX | EPIC-001 | 階段 6 | User Story |
| **User Story ID** | US-XXX | US-001 | 階段 6 | User Story |
| **Acceptance Criteria ID** | AC-XXX-Y | AC-001-1 | 階段 6 | User Story |
| **API ID** | API-XXX | API-001 | 階段 5 | API Spec |
| **Test Case ID** | TC-XXX-Y-Z | TC-001-1-1 | 階段 8 | Test Plan |
| **Bug ID** | BUG-XXX | BUG-001 | 開發中 | Bug Tracker |
| **Change Request ID** | CR-XXX | CR-001 | 需求變更 | Change Log |

**完整追蹤鏈範例** (MoneyTracker):
```
F-001 (快速記帳功能)
  └─ BR-001 (金額必須 > 0)
      └─ EPIC-001 (記帳管理)
          └─ US-001 (作為使用者，我想快速記帳)
              ├─ AC-001-1 (可輸入金額)
              ├─ AC-001-2 (可選擇分類)
              ├─ AC-001-3 (可新增備註)
              └─ AC-001-4 (可儲存記錄)
                  └─ API-101 (POST /api/transactions)
                      └─ TC-001-1-1 (測試正常記帳)
```

#### 步驟 4.4：文件生成確認點 🔴

系統會呈現：
1. **PRD 草稿** (含 Feature ID: F-XXX)
2. **FRD 草稿** (含 Business Rule ID: BR-XXX)
3. **MVP 定義文檔** (Phase 1/2/3 功能劃分)
4. **功能優先級排序** (RICE 評分 + Kano 分類)
5. **ID 追蹤鏈** (Feature → BR → Epic → US → AC)

你需要確認文件準確性和 MVP 範圍。

---

#### 步驟 4.5：BA-SA 協作審查流程 🔴

> **🤝 為什麼需要 BA-SA 協作審查？**
>
> PRD/FRD 是專案的基石文檔，品質直接影響後續開發效率和成功率。BA-SA 協作審查機制確保：
> - ✅ **業務需求正確性**：BA 驗證業務邏輯、流程、規則是否符合 Stakeholder 期待
> - ✅ **技術實現可行性**：SA 驗證需求定義是否清晰、完整、可實現
> - ✅ **文檔一致性**：PRD ↔ FRD ↔ MVP 三者之間的邏輯一致性
> - ✅ **追蹤鏈完整性**：Feature ID → Business Rule ID → Epic ID 的追蹤鏈完整
> - ✅ **品質保證**：雙重審查降低需求遺漏、錯誤、模糊的風險

**參與角色**：
- **BA Agent (Beatrice)** - 業務分析師，主導業務邏輯和流程審查
- **SA Agent (Amanda)** - 系統分析師，主導需求定義和技術可行性審查
- **PM/PO Agent (Victoria)** - 產品經理，最終決策者和仲裁者
- **SD Agent (Marcus)** - 系統設計師（可選），技術複雜度高時參與

---

##### 4.5.1 審查流程概覽

**時間**: 1-2 小時（視專案規模）

**輸入文檔**：
- PRD 草稿（含 Feature ID: F-XXX）
- FRD 草稿（含 Business Rule ID: BR-XXX）
- MVP 定義文檔（若有）
- 需求驗證報告（RICE 評分 + Kano 分類）

**輸出結果**：
- 審查檢查清單（已完成打勾）
- 問題清單（Issue List）
- 修正建議（Action Items）
- 審查通過/有條件通過/不通過決策

🆕 **AI Agent 協作模式下的審查簡化方案**:

> 💡 **適用條件**: 當團隊規模 ≤ 3 人，且 BA/SA 均為 AI Agent 時，
> 可採用以下簡化審查流程，確保效率同時維持品質。

| 傳統審查 | AI 協作簡化方案 | 說明 |
|---------|---------------|------|
| BA 和 SA 分開審查各 30-45 分鐘 | **BA→SA 串接審查** 一輪 30 分鐘 | BA 先審業務邏輯，直接傳遞給 SA 續審技術面 |
| 會議形式的問題討論 | **文件標註式審查** | AI 直接在文件中標註問題和修正建議，人類做最終裁決 |
| PM/PO 仲裁 | **人類一次性確認** | 所有 AI 審查意見彙總後，由人類一次確認 |

**AI 互審操作指引**:
```
1. SA Agent 完成 PRD/FRD 撰寫
2. BA Agent 自動觸發業務邏輯審查
   → 產出：業務規則正確性 ✅/❌ + 問題清單
3. SA Agent 根據 BA 回饋自動修正
4. SA Agent 執行技術可行性自查
   → 產出：需求完整性 ✅/❌ + 技術風險清單
5. 彙總所有 AI 審查結果 → 提交人類做最終確認（🔴 人機協作點）
```

🆕 **多領域/跨領域專案額外審查項目**（適用於融合多產業領域的系統）:

> **跨領域業務規則衝突檢查**:
>
> 當系統融合多個領域（如電商 + 民宿 + CMS + KMS）時，BA-SA 需額外審查：
>
> | 審查項目 | 說明 | 範例 |
> |---------|------|------|
> | **共用實體一致性** | 跨領域共用的實體（User, Payment）定義是否一致 | 電商的「訂單」與民宿的「預約」共用同一支付流程，退款規則是否統一？ |
> | **權限模型衝突** | 不同領域的角色權限是否有衝突或重疊 | CMS 編輯者是否自動有 KMS 編輯權限？需明確定義 |
> | **業務規則跨域影響** | 一個領域的規則變更是否影響其他領域 | 電商的促銷折扣是否影響民宿的定價策略？ |
> | **資料流向合理性** | 跨領域的資料流向是否有安全或效能風險 | KMS 文檔引用電商商品資料時，商品下架後 KMS 引用如何處理？ |
> | **ID 命名空間隔離** | 各領域 ID 是否有命名衝突 | 電商 F-001 vs 民宿 F-001 需加領域前綴（SHOP-F-001, STAY-F-001） |

**流程圖**：
```
步驟 4.4: 文件生成確認點 🔴
     │
     ▼
步驟 4.5: BA-SA 協作審查流程 🔴
     │
     ├─ 4.5.2 BA 業務邏輯審查 (30-45 分鐘)
     │   ├─ Business Rule 正確性
     │   ├─ 業務流程完整性
     │   └─ Stakeholder 需求對齊
     │
     ├─ 4.5.3 SA 需求定義審查 (30-45 分鐘)
     │   ├─ Feature 定義清晰度
     │   ├─ 需求可測試性
     │   └─ 技術可行性
     │
     ├─ 4.5.4 文檔一致性聯合審查 (15-20 分鐘)
     │   ├─ PRD ↔ FRD 一致性
     │   ├─ 追蹤鏈完整性
     │   └─ MVP 範圍合理性
     │
     ├─ 4.5.5 問題討論與決策 (10-15 分鐘)
     │   ├─ 問題優先級排序
     │   ├─ 修正方案討論
     │   └─ PM/PO 最終決策
     │
     ▼
審查結果：通過/有條件通過/不通過
     │
     ├─ 通過 ──────────────────┐
     ├─ 有條件通過（修正後通過）─┤
     └─ 不通過（重新撰寫）───────┘
                               │
                               ▼
                         步驟 4.6: 產出文件
```

---

##### 4.5.2 BA 業務邏輯審查（Beatrice 主導）

**審查時間**: 30-45 分鐘

**審查重點**：

**A. Business Rule 正確性檢查**

| 檢查項目 | 說明 | 範例 |
|---------|------|------|
| **BR 完整性** | 所有業務規則都已記錄？ | 訂單金額計算規則、折扣套用順序、退款條件 |
| **BR 正確性** | 業務規則邏輯正確？ | 金額計算公式：`總金額 = Σ(商品單價 × 數量) - 折扣 + 運費` ✓ |
| **BR 一致性** | 多處提及的規則是否一致？ | FRD 說「滿 $1000 免運」，PRD 也必須一致 |
| **BR 可操作性** | 規則是否可被系統執行？ | 「適當的折扣」❌ → 「8 折優惠」✓ |
| **BR 例外處理** | 是否定義例外情況？ | 當折扣 > 訂單金額時，最低收取 $1 |

**檢查清單**：

- [ ] **FRD Business Rules 章節完整性**
  - [ ] 所有業務規則都有唯一 BR-XXX ID
  - [ ] 每個 BR 都有明確的觸發條件和結果
  - [ ] 每個 BR 都有優先級（P0/P1/P2）
  - [ ] 每個 BR 都追溯到至少一個 Feature (F-XXX)

- [ ] **業務規則邏輯正確性**
  - [ ] 金額計算規則正確（加總、折扣、稅金、運費）
  - [ ] 狀態轉換規則正確（訂單狀態、使用者狀態）
  - [ ] 權限控制規則正確（誰可以做什麼）
  - [ ] 時間相關規則正確（有效期、逾期處理）

- [ ] **業務規則一致性**
  - [ ] PRD Feature 描述與 FRD Business Rule 一致
  - [ ] 多處提及的規則（如「免運門檻」）數值一致
  - [ ] 專有名詞使用一致（「訂單」vs「交易」選其一）

**B. 業務流程完整性檢查**

| 檢查項目 | 說明 | 範例 |
|---------|------|------|
| **主流程完整** | 正常流程的每一步都有定義？ | 下單 → 付款 → 出貨 → 收貨 → 完成 |
| **分支流程完整** | 所有分支情況都考慮？ | 付款失敗、取消訂單、退貨退款 |
| **異常流程完整** | 異常情況處理完整？ | 庫存不足、地址錯誤、配送失敗 |
| **角色完整** | 所有使用者角色都定義？ | 買家、賣家、平台管理員、客服 |
| **權限完整** | 每個角色的權限都明確？ | 買家可下單but不可取消已出貨訂單 |

**檢查清單**：

- [ ] **使用者角色與權限**
  - [ ] FRD 定義了所有使用者角色（User Role ID: UR-XXX）
  - [ ] 每個角色的權限範圍明確
  - [ ] 角色之間的關係清楚（如：賣家也可以是買家）
  - [ ] 特殊角色（管理員、客服）權限範圍明確

- [ ] **業務流程圖完整性**
  - [ ] FRD 包含主要業務流程圖（如訂單處理流程）
  - [ ] 流程圖涵蓋正常流程和異常流程
  - [ ] 流程圖中每個步驟都有對應的 BR-XXX
  - [ ] 流程圖中決策點（菱形）條件明確

- [ ] **Stakeholder 需求對齊**
  - [ ] 所有 Stakeholder 的核心需求都被滿足
  - [ ] 沒有遺漏的關鍵功能（與階段 2 確認問題答案對照）
  - [ ] MVP 範圍包含 Stakeholder 的最小可接受功能集

**C. 業務價值驗證**

- [ ] **RICE 評分合理性**
  - [ ] Reach 估算有數據支持（不是拍腦袋）
  - [ ] Impact 評分符合業務目標
  - [ ] Confidence 分數反映真實不確定性
  - [ ] Effort 估算包含業務流程複雜度

- [ ] **Kano 模型分類合理**
  - [ ] 必備型 (Must-be) 功能確實是最低標準
  - [ ] 期望型 (One-dimensional) 功能有商業價值
  - [ ] 魅力型 (Attractive) 功能有創新性

**輸出**：BA 審查問題清單（Issue List）

---

##### 4.5.3 SA 需求定義審查（Amanda 主導）

**審查時間**: 30-45 分鐘

**審查重點**：

**A. Feature 定義清晰度檢查**

| 檢查項目 | 說明 | 範例 |
|---------|------|------|
| **Feature 可理解性** | 開發團隊能理解需求？ | 「快速記帳」❌ → 「使用者在 3 秒內完成單筆支出記錄」✓ |
| **Feature 邊界清楚** | In-Scope vs Out-of-Scope？ | 「搜尋功能」包含自動完成，但不包含語音搜尋 |
| **Feature 優先級合理** | P0/P1/P2 分類合理？ | 登入系統 (P0) > 社交分享 (P2) |
| **Feature 可拆分性** | 是否可拆解為 User Stories？ | F-001 可拆解為 US-001, US-002, US-003 |
| **Feature 可測試性** | 是否有明確的驗收標準？ | 「效能良好」❌ → 「頁面載入時間 < 3 秒」✓ |

**檢查清單**：

- [ ] **PRD Feature 章節品質**
  - [ ] 所有 Feature 都有唯一 F-XXX ID
  - [ ] 每個 Feature 都有清晰的功能描述（What + Why）
  - [ ] 每個 Feature 都有明確的驗收標準（Acceptance Criteria）
  - [ ] 每個 Feature 都有優先級標記（P0/P1/P2）
  - [ ] 每個 Feature 都可追溯到業務目標

- [ ] **Non-Functional Requirements 完整性**
  - [ ] PRD 定義了所有 NFR（使用 NFR-XXX ID）
  - [ ] 效能需求量化（回應時間、吞吐量、並發數）
  - [ ] 安全需求明確（認證、授權、資料加密）
  - [ ] 可用性需求明確（Uptime SLA、災難恢復）
  - [ ] 相容性需求明確（瀏覽器、裝置、OS 版本）

**B. 需求定義的 SMART 原則檢查**

**SMART 原則**：
- **S**pecific（具體）：需求描述清楚明確
- **M**easurable（可衡量）：有量化指標
- **A**chievable（可達成）：技術上可實現
- **R**elevant（相關）：與業務目標相關
- **T**ime-bound（有時限）：有交付時程

**檢查清單**：

- [ ] **Specific（具體）**
  - [ ] 需求描述避免模糊詞彙（「快速」、「容易」、「良好」）
  - [ ] 使用量化指標（「< 3 秒」、「≥ 99.9% Uptime」）
  - [ ] 明確定義專有名詞（什麼是「訂單」、「使用者」）

- [ ] **Measurable（可衡量）**
  - [ ] 每個 Feature 都有可測試的驗收標準
  - [ ] NFR 有明確的衡量指標（效能、安全、可用性）
  - [ ] Success Criteria 可客觀驗證（不是主觀感受）

- [ ] **Achievable（可達成）**
  - [ ] SD Agent 已確認技術可行性
  - [ ] Effort 估算合理（不過度樂觀）
  - [ ] 技術風險已識別並有緩解計畫

- [ ] **Relevant（相關）**
  - [ ] 每個 Feature 都追溯到業務目標
  - [ ] MVP 範圍符合產品願景
  - [ ] 沒有「Nice-to-have 但無商業價值」的功能

- [ ] **Time-bound（有時限）**
  - [ ] PRD 包含時程與里程碑（Timeline & Milestones）
  - [ ] MVP 有明確的交付時間（Phase 1: 2-3 個月）
  - [ ] 關鍵 Feature 有優先級和排序

**C. 技術可行性驗證**

- [ ] **技術複雜度評估**
  - [ ] 高複雜度 Feature 已進行技術 Spike
  - [ ] 第三方整合的依賴性已確認
  - [ ] 新技術的學習曲線已考慮

- [ ] **架構影響評估**
  - [ ] Feature 是否需要架構調整（如新增微服務）
  - [ ] 資料庫設計是否支撐需求（如高並發查詢）
  - [ ] 效能瓶頸是否已識別（如大量資料處理）

**輸出**：SA 審查問題清單（Issue List）

---

##### 4.5.4 文檔一致性聯合審查（BA + SA 協作）

**審查時間**: 15-20 分鐘

**審查重點**：

**A. PRD ↔ FRD 一致性檢查**

| 檢查項目 | 說明 | 範例 |
|---------|------|------|
| **Feature ↔ BR 對應** | PRD 的每個 Feature 都有對應的 BR？ | F-001 → BR-001, BR-002 |
| **術語一致性** | PRD 和 FRD 使用相同術語？ | 「訂單」vs「交易」選其一 |
| **數值一致性** | 金額、數量、時間等數值一致？ | PRD 說「1000 元免運」，FRD 也是 1000 |
| **流程一致性** | PRD 描述的流程與 FRD 流程圖一致？ | 訂單狀態轉換順序一致 |

**檢查清單**：

- [ ] **Feature ID ↔ Business Rule ID 追蹤鏈**
  - [ ] PRD 的每個 F-XXX 都在 FRD 中有對應的 BR-XXX
  - [ ] FRD 的每個 BR-XXX 都可追溯到 PRD 的 F-XXX
  - [ ] 追蹤鏈記錄在文檔的「Traceability」章節

- [ ] **術語與定義一致性**
  - [ ] PRD 和 FRD 使用相同的專有名詞
  - [ ] 縮寫定義一致（如「MAU」= Monthly Active Users）
  - [ ] 角色名稱一致（如「使用者」vs「會員」選其一）

- [ ] **數值與參數一致性**
  - [ ] 金額門檻一致（免運金額、優惠門檻）
  - [ ] 時間限制一致（有效期、逾期時間）
  - [ ] 數量限制一致（最大購買數、最小訂單量）

**B. MVP 定義一致性檢查**

- [ ] **MVP ↔ PRD 一致性**
  - [ ] MVP Phase 1 的功能都在 PRD 中有定義
  - [ ] MVP 的 RICE 評分與 PRD Feature 優先級一致
  - [ ] MVP 的時程與 PRD Timeline 一致

- [ ] **MVP ↔ FRD 一致性**
  - [ ] MVP Phase 1 的 Business Rules 都在 FRD 中定義
  - [ ] MVP 範圍的業務流程在 FRD 中完整

**C. ID 追蹤鏈完整性檢查**

**完整追蹤鏈格式**：
```
F-XXX (Feature)
  └─ BR-XXX (Business Rule in FRD)
      └─ EPIC-XXX (Epic in User Story - 階段 6)
          └─ US-XXX (User Story - 階段 6)
              └─ AC-XXX-Y (Acceptance Criteria - 階段 6)
                  └─ API-XXX (API Spec - 階段 5)
```

**檢查清單**：

- [ ] **Feature → Business Rule 追蹤鏈**
  - [ ] PRD 的 F-XXX 在 FRD 中有對應的 BR-XXX 引用
  - [ ] FRD 的 BR-XXX 在 PRD 中有對應的 F-XXX 引用
  - [ ] 雙向追蹤鏈無斷裂

- [ ] **ID 命名規範一致性**
  - [ ] 所有 ID 符合 [AISDLC_ID_Naming_Convention.md](../../guides/system/naming/AISDLC_ID_Naming_Convention.md)
  - [ ] Feature ID: F-001, F-002, F-003（連續編號）
  - [ ] Business Rule ID: BR-001, BR-002, BR-003（連續編號）
  - [ ] 無重複 ID、無跳號

**輸出**：一致性問題清單（Issue List）

---

##### 4.5.5 問題討論與決策（PM/PO 主導）

**時間**: 10-15 分鐘

**流程**：

1. **彙整問題清單**（2 分鐘）
   - BA 提出的業務邏輯問題
   - SA 提出的需求定義問題
   - 一致性檢查發現的問題

2. **問題優先級排序**（3 分鐘）
   - 🔴 **Critical（阻塞性）**：必須立即修正，否則無法進入下一階段
   - 🟡 **High（重要）**：需要修正，但可延後到文檔更新時處理
   - 🟢 **Low（次要）**：建議優化，但不影響整體品質

3. **問題分類與責任分配**（3 分鐘）

| 問題類型 | 負責人 | 處理方式 |
|---------|-------|---------|
| 業務規則錯誤 | BA + PM/PO | 重新與 Stakeholder 確認 |
| 需求定義模糊 | SA + PM/PO | 補充具體描述和量化指標 |
| 技術可行性疑慮 | SD + SA | 進行技術 Spike 或調整需求 |
| 文檔一致性問題 | SA + BA | 修正不一致處 |
| ID 追蹤鏈斷裂 | SA | 補充遺漏的 ID 和引用 |

4. **修正方案討論**（3 分鐘）
   - 針對 Critical 和 High 問題討論修正方案
   - 明確修正責任人和時間
   - 記錄 Action Items

5. **PM/PO 最終決策**（2 分鐘）

**決策選項**：

| 決策 | 條件 | 後續行動 |
|------|------|---------|
| **✅ 通過** | 無 Critical 問題，High 問題 ≤ 2 個 | 進入步驟 4.6 產出文件 |
| **🟡 有條件通過** | 有 Critical 問題，但可在 1-2 小時內修正 | 修正後重新審查（快速審查 15 分鐘）|
| **❌ 不通過** | Critical 問題 > 3 個，或需重新與 Stakeholder 確認 | 回到步驟 4.1 重新撰寫文件 |

**輸出文檔**：

- **BA-SA 協作審查報告**（`BA_SA_Review_Report_[Date].md`）
  - 審查時間、參與人員
  - 審查檢查清單（已完成項目打勾）
  - 問題清單（Issue List）含優先級
  - 修正建議（Action Items）含責任人和時限
  - 審查決策（通過/有條件通過/不通過）

---

##### 4.5.6 審查檢查清單範本

**BA 業務邏輯審查檢查清單**：

- [ ] **Business Rule 正確性**
  - [ ] 所有 BR 都有唯一 BR-XXX ID
  - [ ] BR 邏輯正確（金額計算、狀態轉換、權限控制）
  - [ ] BR 一致性（PRD ↔ FRD 一致）

- [ ] **業務流程完整性**
  - [ ] 使用者角色與權限完整
  - [ ] 業務流程圖完整（正常+異常流程）
  - [ ] Stakeholder 需求對齊

- [ ] **業務價值驗證**
  - [ ] RICE 評分合理
  - [ ] Kano 模型分類合理

**SA 需求定義審查檢查清單**：

- [ ] **Feature 定義清晰度**
  - [ ] 所有 Feature 都有唯一 F-XXX ID
  - [ ] Feature 描述清楚（可理解、可拆分、可測試）
  - [ ] NFR 定義完整（效能、安全、可用性）

- [ ] **SMART 原則**
  - [ ] Specific（具體）- 無模糊詞彙
  - [ ] Measurable（可衡量）- 有量化指標
  - [ ] Achievable（可達成）- 技術可行
  - [ ] Relevant（相關）- 對應業務目標
  - [ ] Time-bound（有時限）- 有交付時程

- [ ] **技術可行性驗證**
  - [ ] 高複雜度 Feature 已 Spike
  - [ ] 架構影響已評估

**文檔一致性聯合審查檢查清單**：

- [ ] **PRD ↔ FRD 一致性**
  - [ ] Feature ↔ BR 對應
  - [ ] 術語一致性
  - [ ] 數值一致性

- [ ] **MVP 定義一致性**
  - [ ] MVP ↔ PRD 一致
  - [ ] MVP ↔ FRD 一致

- [ ] **ID 追蹤鏈完整性**
  - [ ] F-XXX → BR-XXX 追蹤鏈完整
  - [ ] ID 命名規範一致

**審查決策**：

- [ ] ✅ **通過**（無 Critical 問題）
- [ ] 🟡 **有條件通過**（Critical 問題可在 1-2 小時內修正）
- [ ] ❌ **不通過**（Critical 問題 > 3 個，需重新撰寫）

---

#### 步驟 4.6：產出文件

> 📌 **PRD 草稿與模板結構對齊重要說明**
>
> **AI 產出的 PRD 草稿完全對應 [PRD_Universal_Template.md](../../docs_template/core/prd/PRD_Universal_Template.md) 的 Greenfield 情境使用方式。**
>
> **PRD 草稿章節結構**（Greenfield 必讀章節 1-8）:
> 1. 專案願景與目標 (Vision & Objectives)
> 2. 目標使用者與利害關係人 (Target Users & Stakeholders)
> 3. 產品範圍與邊界 (Product Scope & Boundaries)
> 4. 功能需求 (Functional Requirements) - 使用 Feature ID: F-XXX
> 5. 非功能需求 (Non-Functional Requirements) - 使用 NFR ID: NFR-XXX
> 6. 使用者體驗要求 (User Experience Requirements)
> 7. 驗收標準 (Acceptance Criteria)
> 8. 時程與里程碑 (Timeline & Milestones)
>
> **使用者應依此草稿結構，使用 PRD_Universal_Template.md 填寫完整版 PRD。**
>
> **驗證清單**:
> - [ ] PRD 草稿章節與模板章節完全一致
> - [ ] 所有 Feature 使用 F-XXX 格式
> - [ ] 所有 NFR 使用 NFR-XXX 格式
> - [ ] 包含 MVP 定義（若階段 2 已確認需要）
> - [ ] 追蹤鏈完整（Feature → BR → Epic → US）

**產出文件**：

> 📋 **階段 4 產出文件分類說明**

**主要產出（獨立文件）**：
- **PRD** (Product Requirements Document)
  - 檔名: `PRD_[ProjectName]_v1.0.md`
  - 模板: [PRD_Universal_Template.md](../../docs_template/core/prd/PRD_Universal_Template.md)
  - 使用 Feature ID: F-XXX, NFR ID: NFR-XXX

- **FRD** (Functional Requirements Document)
  - 檔名: `FRD_[ProjectName]_v1.0.md`
  - 模板: [FRD_Universal_Template.md](../../docs_template/core/frd/FRD_Universal_Template.md)
  - 使用 Business Rule ID: BR-XXX, User Role ID: UR-XXX

- **MVP Definition**（若階段 2 已確認需要）
  - 檔名: `MVP_Definition_[ProjectName].md`
  - 模板: [MVP_Definition_Template.md](../../docs_template/prd/MVP_Definition_Template.md)

**附屬產出（整合到主要文件或獨立附件）**：
- **需求驗證報告 (Requirement Validation Report)**
  - **選項 A（建議用於小型專案）**: 整合到 FRD 的「附件」章節
  - **選項 B（建議用於大型專案）**: 獨立文件 `Requirement_Validation_Report_[ProjectName].md`
  - **內容**: RICE 評分結果、Kano 模型分析、需求完整性檢查結果、驗證結論
  - **建議**: 小型專案（< 50 功能）用選項 A，大型專案（≥ 50 功能）用選項 B

---

### 階段 5：架構設計 (4-8 小時)

> ⚠️ **時間估算說明** 🆕
>
> 本階段涵蓋多個子任務，原估算 4-6 小時適用於**簡單 Web App**。
> 對於**企業級系統**（含多平台、硬體整合、複雜安全需求），建議 **6-8 小時**。
>
> | 子任務 | 簡單專案 | 中型專案 | 企業級專案 |
> |--------|---------|---------|-----------|
> | 5.2.1 系統架構設計 (C4 Model) | 1-1.5 小時 | 1.5-2 小時 | 2-3 小時 |
> | 5.2.2 資料庫設計 | 0.5-1 小時 | 1-1.5 小時 | 1.5-2 小時 |
> | 5.2.3 API 設計 | 1-1.5 小時 | 1.5-2 小時 | 2-3 小時 |
> | 5.2.4 即時通訊 API（如適用）| - | 0.5 小時 | 1 小時 |
> | 5.2.5 多平台版本策略（如適用）| - | - | 0.5-1 小時 |
> | 安全元件設計 (5.2.1.1) | 0.5 小時 | 1 小時 | 1-1.5 小時 |
> | 高可用性設計 (5.2.1.2) | - | 0.5 小時 | 1 小時 |
> | **合計** | **3-4.5 小時** | **5-7.5 小時** | **8-11.5 小時** |
>
> 💡 **建議**: 企業級專案可將 Stage 5 拆為兩個工作日執行。

> 🤖 **Agent 載入時機** - Dev Agent (David) **首次載入**
>
> **觸發時機**: 當階段 5 開始架構設計時，Dev Agent (David) 會被載入，負責技術可行性評估和開發工時估算。
>
> **載入確認訊息**:
> ```
> ✅ Dev Agent (David) 已載入 - 準備進行技術可行性評估
> ```
>
> **主要職責** (階段 5):
> - 技術實作可行性評估
> - 開發工時估算
> - 技術風險識別
> - 實作複雜度評估
> - 開發最佳實踐建議
>
> **協作模式**:
> - 與 **SD-Architect (Marcus)** 協作：架構設計的實作可行性評估
> - 與 **QA Agent (Quincy)** 協作：測試可行性評估
> - 與 **PM/PO Agent (Victoria)** 協作：資源分配與時程規劃
> - **後續階段延續參與**: Stage 6 (API 技術實作規劃), Stage 8 (開發實作主導)

> 🤖 **Agent 參與角色** - SD-Architect Agent (Marcus) **核心主導階段**
>
> **參與狀態**: SD-Architect Agent (Marcus) 在此階段擔任**核心主導角色**，負責所有架構設計工作。
>
> **主要職責** (階段 5):
> - **系統架構設計** (C4 Model Level 1-4)
> - **資料庫設計** (Schema, ER 圖, 遷移策略)
> - **API 設計** (若需要後端) 或 Data Access Layer 設計 (本地 App)
> - **前端架構設計** (與 Web-Architect/Mobile-Architect 協作)
> - **部署架構設計** (雲端基礎設施、CI/CD 策略)
> - **技術文件產出** (SRD - System Requirements Document)
>
> **協作模式**:
> - 與 **Specialized Agents** 協作：
>   - Web-Architect: 前端架構細節設計
>   - Mobile-Architect: Mobile 平台特定架構
> - 與 **Dev Agent (David)** 協作：技術實作可行性評估
> - 與 **QA Agent (Quincy)** 協作：架構可測試性驗證

#### 步驟 5.1：觸發架構設計流程
```
執行指令：
「基於確認的需求和技術選型，請進行系統架構設計」
```

#### 步驟 5.2：架構設計內容

**5.2.1 系統架構設計** (SD-Architect Agent - Marcus 主導)
- 整體架構圖 (C4 Model - 參考 [C4_Model_Guidelines.md](../../guides/system/architecture/C4_Model_Guidelines.md))
  - Level 1: System Context Diagram（所有專案必須）
  - Level 2: Container Diagram（所有專案必須）
  - Level 3: Component Diagram（中大型專案必須）
  - Level 4: Code Diagram（選用）
- 模組劃分
- 資料流設計
- 部署架構

**📊 C4 Level 3 必要性判斷矩陣** 🆕 (v0.01 新增)

針對複雜系統，建議提供 Level 3 Component Diagram 以確保架構清晰：

| 判斷條件 | 閾值 | Level 3 建議 |
|---------|------|-------------|
| **Container 數量** | > 5 個 | ⚠️ 建議提供 |
| **Container 數量** | > 10 個 | 🔴 **必須提供** |
| **外部整合點** | > 3 個第三方 API | ⚠️ 建議提供 |
| **微服務數量** | > 5 個微服務 | 🔴 **必須提供** |
| **資料流複雜度** | 跨 3+ Container | ⚠️ 建議提供 |
| **團隊規模** | > 5 人開發 | ⚠️ 建議提供 |

**複雜系統定義**（符合任一條件即視為複雜系統）：
- 🔴 Container 數量 > 10 個
- 🔴 微服務數量 > 5 個
- 🔴 涉及 3+ 不同技術棧
- 🔴 跨 2+ 團隊協作

**Level 3 範圍建議**：
- **優先繪製**：核心業務模組、安全元件、資料存取層
- **可選繪製**：工具類模組、日誌監控模組
- **不需繪製**：純 UI 元件（除非有複雜狀態管理）

🆕 **C4 Level 3 Component Diagram 範例**（經銷存系統 - 庫存管理 Container）:

```
[Container: 庫存管理服務 (Spring Boot)]
┌─────────────────────────────────────────────────────┐
│                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────┐ │
│  │ Inventory    │  │ Stock Alert  │  │ Barcode   │ │
│  │ Controller   │  │ Service      │  │ Service   │ │
│  │ (REST API)   │  │ (安全庫存警示)│  │ (條碼解析) │ │
│  └──────┬───────┘  └──────┬───────┘  └─────┬─────┘ │
│         │                 │                │       │
│  ┌──────▼───────┐  ┌──────▼───────┐  ┌────▼──────┐ │
│  │ Inventory    │  │ Notification │  │ Product   │ │
│  │ Service      │  │ Publisher    │  │ Lookup    │ │
│  │ (庫存核心邏輯)│  │ (WebSocket)  │  │ Service   │ │
│  └──────┬───────┘  └──────────────┘  └───────────┘ │
│         │                                           │
│  ┌──────▼───────┐  ┌──────────────┐                │
│  │ Stock        │  │ Audit Trail  │                │
│  │ Repository   │  │ Logger       │                │
│  │ (JPA/Flyway) │  │ (異動紀錄)    │                │
│  └──────┬───────┘  └──────────────┘                │
│         │                                           │
└─────────┼───────────────────────────────────────────┘
          ▼
  [PostgreSQL: inventory_db]
```

**Component 說明**:
| Component | 職責 | 關鍵技術 |
|-----------|------|---------|
| Inventory Controller | REST API 端點、請求驗證 | Spring MVC, @RestController |
| Inventory Service | 庫存增減、盤點、調撥核心邏輯 | Spring Service, @Transactional |
| Stock Alert Service | 安全庫存監控、低庫存警示觸發 | Spring Scheduler, Threshold Config |
| Barcode Service | 條碼格式解析（EAN-13/Code128/QR） | ZXing Library |
| Notification Publisher | WebSocket 即時推送庫存變更 | Spring WebSocket, STOMP |
| Stock Repository | 資料庫存取、查詢優化 | Spring Data JPA, QueryDSL |
| Audit Trail Logger | 所有庫存異動的稽核紀錄 | Spring AOP, @Aspect |

---

**5.2.1.1 安全元件設計檢查** (🆕 v0.01 新增)

> 📋 **使用工具**: [Security_Architecture_Checklist.md](../../guides/system/architecture/Security_Architecture_Checklist.md)
> **目的**: 確保 C4 Model Level 2/3 包含完整安全元件設計
> **執行時機**: 完成 C4 Level 2 Container Diagram 後
> **參與角色**: SD (主導) + Security Engineer（如有） + SA（驗證）

> 🔧 **建議 Skill（架構階段安全審查）**：
> ```
> 觸發條件（符合任一即觸發）：
> 🔴 系統含支付/金流（Stripe 等）→ 必須觸發 /security-audit（PCI-DSS 合規）
> 🔴 系統處理個人資料（個資法/GDPR）→ 必須觸發 /security-audit + /compliance-audit
> 🔴 系統含認證授權（OAuth/JWT）→ 必須觸發 /security-audit（安全架構審查）
> 🟡 系統含旅宿業（旅宿業法規）→ 必須觸發 /compliance-audit
>
> 觸發指令：「請執行安全架構審查（/security-audit），重點審查 C4 Level 2 的安全元件設計」
> ```
> ⚠️ **注意**：架構階段的 `/security-audit` 是「設計時審查」，與部署階段的「運行時掃描」互補，兩者都需要執行。

**強制檢查 4 大安全元件類別**:

根據 Stage 2 STRIDE 威脅建模產出的 NFR-SEC 安全需求，以下安全元件 **必須** 在 C4 Model 中明確設計：

**1️⃣ 認證與授權元件** (對應 NFR-SEC-001)
- [ ] **C4 Level 2**: Authentication Service / Authorization Engine 已標示
- [ ] **C4 Level 3**: JWT Handler / Permission Checker / MFA Component 已設計
- [ ] **技術選型**: JWT / OAuth 2.0 / SAML 2.0 已選定
- [ ] **Token 管理**: Access Token / Refresh Token 機制已說明

**2️⃣ 加密元件** (對應 NFR-SEC-003)
- [ ] **C4 Level 2**: TLS/SSL Termination / Encryption Service / KMS 已標示
- [ ] **C4 Level 3**: Password Hash / Data Encryption / HTTPS Redirect Component 已設計
- [ ] **加密範圍**: 密碼 (bcrypt) / PII (AES-256) / 傳輸 (TLS 1.2+) 已定義
- [ ] **金鑰管理**: KMS (AWS KMS / Azure Key Vault) 整合已規劃

**3️⃣ 輸入驗證與防護元件** (對應 NFR-SEC-002)
- [ ] **C4 Level 2**: API Gateway / WAF / Input Validation Service 已標示
- [ ] **C4 Level 3**: Request Validator / SQL Injection Prevention / XSS Prevention / CSRF Prevention Component 已設計
- [ ] **驗證層次**: 前端驗證 + 後端驗證雙層機制已說明
- [ ] **Schema Validation**: JSON Schema Validator 已整合

**4️⃣ 日誌與審計元件** (對應 NFR-SEC-004, NFR-SEC-005)
- [ ] **C4 Level 2**: Centralized Logging Service / Audit Trail Database 已標示
- [ ] **C4 Level 3**: Security Event Logger / Audit Trail / Data Masking / Anomaly Detection Component 已設計
- [ ] **日誌範圍**: 認證操作 / 業務操作 / 安全事件 已定義
- [ ] **日誌保留**: ≥ 90 天保留期限已規劃

**完成標準**:
- ✅ C4 Level 2 Container Diagram 包含 4 大類安全容器
- ✅ C4 Level 3 Component Diagram 包含對應安全元件
- ✅ 每個安全元件有明確技術選型說明
- ✅ SRD「安全架構設計」章節已撰寫

**預期效益**:
- ✅ 架構審查安全性完整度從 40% 提升至 90%
- ✅ 安全元件遺漏率從 60% 降至 10%
- ✅ 事後安全補丁成本減少 75%

---

**5.2.1.2 高可用性架構設計檢查** (🆕 v0.01 新增)

> 📋 **使用工具**: [High_Availability_Architecture_Checklist.md](../../guides/system/architecture/High_Availability_Architecture_Checklist.md)
> **目的**: 確保 C4 Model Level 2 及部署架構包含完整 HA 元件設計
> **執行時機**: 完成 C4 Level 2 Container Diagram 後
> **參與角色**: SD (主導) + DevOps Engineer（如有） + SA（驗證）

**強制檢查 4 大 HA 元件類別**:

根據系統 SLA 需求（通常 ≥ 99.9%），以下 HA 元件 **必須** 在 C4 Model 及部署架構中明確設計：

**1️⃣ 負載均衡器** (對應 NFR-AVL-001)
- [ ] **C4 Level 2**: Application Load Balancer (ALB/NGINX) 已標示
- [ ] **技術選型**: AWS ALB / NGINX / Azure LB 已選定
- [ ] **健康檢查**: Health Check 機制已說明 (30s interval)
- [ ] **Auto Scaling**: Scaling Policy 已定義 (CPU > 70%)

**2️⃣ 應用層高可用性** (對應 NFR-AVL-002)
- [ ] **多實例部署**: Application Server ≥ 2 instances 已標示
- [ ] **部署策略**: Blue-Green / Rolling Update / Canary 已選定
- [ ] **Session 管理**: Stateless / Redis Session Store 已說明
- [ ] **Container Orchestration**: Kubernetes / ECS 已規劃

**3️⃣ 資料庫高可用性** (對應 NFR-AVL-003)
- [ ] **Replication**: Master-Slave / Multi-AZ Deployment 已標示
- [ ] **讀寫分離**: Read Replicas 數量已定義 (≥ 2)
- [ ] **自動故障轉移**: Automatic Failover 機制已說明
- [ ] **RTO/RPO**: Recovery Time/Point Objective 已定義 (< 5min / < 1min)

**4️⃣ 快取與佇列高可用性** (對應 NFR-AVL-004)
- [ ] **Redis Cluster**: Sentinel / Cluster Mode 已標示
- [ ] **節點配置**: Master + Slave (≥ 2) + Sentinel (≥ 3) 已定義
- [ ] **Message Queue HA**: RabbitMQ Cluster / Kafka Replication 已規劃
- [ ] **持久化策略**: RDB / AOF 已說明

**完成標準**:
- ✅ C4 Level 2 Container Diagram 包含 4 大類 HA 容器
- ✅ Deployment Architecture 包含 Multi-AZ 部署設計
- ✅ 每個 HA 元件有明確技術選型說明
- ✅ SRD「部署架構設計」章節已撰寫

**預期效益**:
- ✅ 系統可用性從 95% 提升至 99.9%
- ✅ 單點故障 (SPOF) 從 5 個降至 0 個
- ✅ 平均故障恢復時間 (MTTR) 從 30 分鐘降至 5 分鐘

---

🆕 **5.2.1.3 多領域系統架構決策指引**（適用於多業務領域融合系統）

> 📋 **適用條件**: 當系統涉及 2+ 業務領域（如電商+民宿+CMS+KMS）時，
> 必須在 Stage 5 架構設計階段決定「模組化策略」和「領域邊界」。
> **參與角色**: SD (主導) + SA（領域邊界定義）+ Dev（實作可行性）

**架構模式決策樹**:

| 判斷條件 | 建議架構 | 說明 |
|---------|---------|------|
| 團隊 ≤ 5 人 + MVP 階段 | **Modular Monolith** | 單一部署單元，按領域分模組，未來可拆微服務 |
| 團隊 5-15 人 + 各領域獨立迭代 | **Modular Monolith → 微服務過渡** | 先 Monolith 快速交付，穩定後按領域拆分 |
| 團隊 15+ 人 + 各領域獨立部署需求 | **微服務架構** | 各領域獨立 repo/部署/資料庫 |

**Modular Monolith 結構範例**（推薦四領域融合系統初期使用）:

```
src/main/java/com/example/platform/
├── shared/          # 共用模組（會員、支付、通知）
│   ├── auth/        # 認證授權
│   ├── payment/     # 統一支付
│   ├── notification/# 統一通知
│   └── search/      # 統一搜尋
├── shop/            # 電商領域
│   ├── product/     # 商品管理
│   ├── cart/        # 購物車
│   └── order/       # 電商訂單
├── stay/            # 民宿領域
│   ├── property/    # 房源管理
│   ├── booking/     # 訂房管理
│   └── calendar/    # 房態日曆
├── cms/             # 內容發布領域
│   ├── article/     # 文章管理
│   ├── media/       # 媒體資產
│   └── publish/     # 發布排程
└── kms/             # 知識管理領域
    ├── knowledge/   # 知識文檔
    ├── wiki/        # Wiki 協作
    └── taxonomy/    # 分類體系
```

**領域邊界定義原則**:

| 原則 | 說明 | 範例 |
|------|------|------|
| **共用實體最小化** | 跨領域共用的實體應集中在 shared 模組 | User, Payment, Notification |
| **領域內聚合根** | 各領域應有獨立的聚合根（Aggregate Root） | Shop→Order, Stay→Booking, CMS→Article, KMS→Knowledge |
| **跨領域通訊** | 領域間透過事件（Event）或共用服務通訊，禁止直接引用 | 電商下單 → 發送事件 → 積分模組處理 |
| **資料隔離** | 各領域的資料表應有明確的 Schema 或前綴 | `shop_products`, `stay_properties`, `cms_articles`, `kms_documents` |

**🔴 強制檢查點 - 多領域架構設計**:
- [ ] 已識別所有業務領域及其邊界
- [ ] 已定義共用實體清單（User/Payment/Notification/Search）
- [ ] 已決定架構模式（Modular Monolith / 微服務）
- [ ] 各領域的聚合根已明確定義
- [ ] 跨領域通訊機制已設計（事件驅動 / 共用服務）
- [ ] C4 Level 2 Container Diagram 反映領域劃分

---

🆕 **5.2.1.4 多領域 SRD 文件組織策略**（適用於多業務領域融合系統）

> 📋 **決策時機**：Stage 5 架構設計早期（決定架構模式後立即決定）
> **影響**：SRD 組織方式決定後影響後續所有文件的維護成本，不易更改。

| 組織方式 | 適用條件 | 優點 | 缺點 |
|---------|---------|------|------|
| **單一 SRD（模組化章節）** | ≤ 3 模組、團隊 ≤ 8 人、模組高度共享基礎設施 | 維護成本低、追蹤容易 | 文件超過 1000 行、並行編輯衝突 |
| **各領域獨立 SRD** | > 5 模組、各領域獨立迭代、未來計劃微服務拆分 | 各領域獨立演進、無並行衝突 | 多份文件一致性維護成本高 |
| **混合方案（推薦）** | 五合一等多領域融合系統 | 共用部分統一管理 + 各領域獨立，均衡兼顧 | 需明確劃分共用與領域邊界 |

**推薦目錄結構（五合一系統）**：

```
docs/02_architecture/
├── SRD_Shared.md          # 共用模組（Auth/Payment/Notification/Search）
├── SRD_Shop.md            # 電商模組
├── SRD_Stay.md            # 民宿模組
├── SRD_CMS.md             # 內容發布模組
├── SRD_KMS.md             # 知識管理模組
├── SRD_Inventory.md       # 進銷存模組
├── SRD_Mobile.md          # 行動端架構（Android/macOS）
└── SRD_Index.md           # SRD 導航索引（追蹤各 SRD 關係）
```

**SRD_Index.md 必備欄位**：

| SRD 文件 | 領域 | 版本 | 狀態 | 關聯 API Spec | 關聯 User Stories |
|---------|------|------|------|--------------|----------------|
| SRD_Shared.md | 共用 | 1.0 | 確認 | API_Auth_*, API_Payment_* | US-001~US-010 |
| SRD_Shop.md | 電商 | 1.0 | 確認 | API_Shop_* | US-011~US-030 |
| SRD_Stay.md | 民宿 | 1.0 | 草稿 | API_Stay_* | US-031~US-050 |

**各領域 SRD 必含「跨模組依賴聲明」章節範例**：

```markdown
## 跨模組依賴聲明
| 依賴模組 | 依賴功能 | 說明 |
|---------|---------|------|
| SRD_Shared | Auth | 訂房需登入驗證 |
| SRD_Shared | Payment | 訂房支付流程 |
```

**🔴 SRD 組織決策確認點**：
- [ ] 已決定 SRD 組織方式（單一 / 獨立 / 混合）
- [ ] 已建立 SRD_Index.md（混合方案必須）
- [ ] 各 SRD 包含「跨模組依賴聲明」章節
- [ ] 各 SRD 模板一致（使用相同的 SRD_Module_Template.md）

---

**5.2.2 資料庫設計**

🆕 **多領域共用實體資料庫設計指引**（適用於多業務領域融合系統）:

> ⚠️ **重要**: 多領域系統的資料庫設計需區分「共用表」和「領域專屬表」，
> 避免不同領域的資料耦合過深。

**共用表 vs 領域專屬表範例**:

| 分類 | 表名 | 說明 | 各領域如何使用 |
|------|------|------|--------------|
| **共用** | `users` | 統一會員 | 所有領域共用，user_id 為外鍵 |
| **共用** | `payments` | 統一支付紀錄 | 各領域訂單引用 payment_id |
| **共用** | `notifications` | 統一通知 | 各領域觸發通知事件 |
| **電商** | `shop_products` | 商品 | 僅電商領域使用 |
| **電商** | `shop_orders` | 電商訂單 | 引用 user_id + payment_id |
| **民宿** | `stay_properties` | 房源 | 僅民宿領域使用 |
| **民宿** | `stay_bookings` | 訂房 | 引用 user_id + payment_id |
| **CMS** | `cms_articles` | 文章 | 引用 user_id（作者） |
| **KMS** | `kms_documents` | 知識文檔 | 引用 user_id（貢獻者） |

**表命名規範**:
- 共用表：不加前綴（如 `users`, `payments`）
- 領域表：加領域前綴（如 `shop_`, `stay_`, `cms_`, `kms_`）
- PostgreSQL Schema 方案（替代前綴）：`shared.users`, `shop.products`, `stay.properties`

依資料庫類型選擇對應的設計方法：

**關聯式資料庫 (SQL)**:
- ER 圖 (Entity-Relationship Diagram)
- 資料表結構
- 索引策略
- **資料遷移計畫** 🔴 (必須產出)
  - 初始化 Schema (v1.0)
  - 遷移腳本命名規範 (例: `V001__Initial_Schema.sql`)
  - 版本升級策略 (v1.0 → v1.1)
  - 資料備份與回滾計畫
  - 測試環境遷移驗證流程
- 工具推薦: dbdiagram.io, draw.io, MySQL Workbench, Flyway, Liquibase

**🔴 強制檢查點 - SQL 資料遷移計畫**:
- [ ] 已完成資料遷移計畫文檔（必須包含：初始化 Schema、遷移腳本規範、版本升級策略、備份回滾計畫）
- [ ] 遷移腳本命名符合規範（例：Flyway `V001__Initial_Schema.sql`、Liquibase `db.changelog-master.xml`）
- [ ] 測試環境遷移驗證流程已定義

🆕 **JPA (Hibernate) + Flyway 搭配最佳實踐**（適用 Spring Boot + PostgreSQL/MySQL）:

> ⚠️ **常見陷阱**: Spring Boot JPA 的 `spring.jpa.hibernate.ddl-auto` 設定，
> 若與 Flyway 同時使用不當，可能導致 Schema 衝突或資料遺失。

| 環境 | `ddl-auto` 設定 | Flyway | 說明 |
|------|----------------|--------|------|
| **開發環境** | `validate` | ✅ 啟用 | Flyway 管理 Schema，JPA 僅驗證 Entity 與 DB 一致 |
| **測試環境** | `validate` | ✅ 啟用 | 與開發環境一致，確保遷移腳本正確 |
| **生產環境** | `validate` | ✅ 啟用 | 絕不使用 `create`/`update`/`create-drop` |
| **單元測試** | `create-drop` | ❌ 關閉 | 使用 H2 記憶體 DB，每次測試重建 Schema |

**推薦設定**（application.yml）:
```yaml
spring:
  jpa:
    hibernate:
      ddl-auto: validate  # ⚠️ 生產環境必須用 validate
    show-sql: false
  flyway:
    enabled: true
    locations: classpath:db/migration
    baseline-on-migrate: true
```

**Flyway 遷移腳本範例**:
```sql
-- V001__Initial_Schema.sql（初始化）
CREATE TABLE products (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    sku VARCHAR(50) UNIQUE NOT NULL,
    price DECIMAL(12,2) NOT NULL,
    -- 軟刪除欄位
    is_active BOOLEAN DEFAULT TRUE,
    deleted_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- V002__Add_inventory_table.sql（新增庫存表）
CREATE TABLE inventory (
    id BIGSERIAL PRIMARY KEY,
    product_id BIGINT REFERENCES products(id),
    quantity INTEGER NOT NULL DEFAULT 0,
    safety_stock INTEGER NOT NULL DEFAULT 10,
    warehouse_id BIGINT NOT NULL
);
```

**Object Database (Realm, CoreData)**:
- Object Model Schema
- Properties (含型別)
- Relationships (LinkingObjects)
- 索引策略
- **Schema 遷移策略** 🔴 (必須產出)
  - Schema Version 定義 (例: schemaVersion = 1)
  - Migration Block 實作範例
  - 資料轉換邏輯 (舊版本 → 新版本)
  - 測試環境遷移驗證流程

**🔴 強制檢查點 - Object Database Schema 遷移策略**:
- [ ] 已完成 Schema 遷移策略文檔（必須包含：Schema Version 定義、Migration Block 範例、資料轉換邏輯）
- [ ] Schema Version 初始值已設定（建議從 1 開始）
- [ ] 測試環境遷移驗證流程已定義

**關鍵差異說明**:
- Realm 不用 Foreign Key，直接參考物件
- Realm 用 LinkingObjects 反向查詢
- Realm 不用 JOIN，直接 traverse 物件

**MoneyTracker Realm Schema 範例** (TypeScript):

```typescript
// Realm Object Model Schema
class Transaction extends Realm.Object {
  _id!: Realm.BSON.ObjectId;
  amount!: number;
  type!: 'income' | 'expense';
  category!: Category; // Relationship: many-to-one
  date!: Date;
  note?: string;

  static schema = {
    name: 'Transaction',
    primaryKey: '_id',
    properties: {
      _id: 'objectId',
      amount: 'double',
      type: 'string',
      category: 'Category', // 直接參考物件
      date: 'date',
      note: 'string?',
    },
  };
}

class Category extends Realm.Object {
  _id!: Realm.BSON.ObjectId;
  name!: string;
  icon!: string;
  transactions!: Realm.List<Transaction>; // Inverse relationship

  static schema = {
    name: 'Category',
    primaryKey: '_id',
    properties: {
      _id: 'objectId',
      name: { type: 'string', indexed: true }, // 索引
      icon: 'string',
      transactions: {
        type: 'linkingObjects',
        objectType: 'Transaction',
        property: 'category',
      },
    },
  };
}
```

**Realm vs SQL 對比**:

| 特性 | Realm (Object Database) | SQL (Relational Database) |
|------|------------------------|--------------------------|
| 資料建模 | 物件導向（Class） | 關聯式（Table） |
| 關聯定義 | 直接物件參考 | Foreign Key |
| 反向查詢 | LinkingObjects | JOIN |
| 查詢方式 | 物件 traverse | SQL Query |
| 工具 | Realm Studio | dbdiagram.io, MySQL Workbench |
| 遷移 | Schema Migration | ALTER TABLE |

範例請參考 [Data_Access_Layer_Template.md](../../docs_template/srd/Data_Access_Layer_Template.md)

##### 🆕 刪除策略設計（Soft Delete vs Hard Delete）

> ⚠️ **重要**: 企業級系統（如經銷存、ERP、CRM）幾乎所有刪除操作都應採用**軟刪除**，
> 以確保資料可追溯、可稽核、可還原。請在資料庫設計階段就明確定義刪除策略。

**刪除策略選擇矩陣**:

| 策略 | 適用場景 | 實作方式 | 優點 | 缺點 |
|------|---------|---------|------|------|
| **軟刪除 (Soft Delete)** | 商業資料、交易紀錄、訂單、客戶資料 | `deleted_at` 時間戳 + `is_active` 旗標 | 可還原、可稽核、保留歷史 | 查詢需加條件、資料量增長 |
| **硬刪除 (Hard Delete)** | 暫存資料、快取、Session、測試資料 | `DELETE FROM table` | 釋放空間、簡單直接 | 不可逆、無法追溯 |
| **歸檔刪除 (Archive Delete)** | 超過保留期限的歷史資料 | 移至 Archive Table 後刪除 | 兼顧效能與歷史保留 | 需維護歸檔表、查詢較複雜 |

**軟刪除標準欄位設計**:

```sql
-- ✅ 推薦：每張需要軟刪除的資料表加入以下欄位
ALTER TABLE {table_name} ADD COLUMN deleted_at TIMESTAMP NULL DEFAULT NULL;
ALTER TABLE {table_name} ADD COLUMN deleted_by VARCHAR(50) NULL;
ALTER TABLE {table_name} ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE;

-- ✅ 建議：建立部分索引提升查詢效能（PostgreSQL）
CREATE INDEX idx_{table}_active ON {table_name} (is_active) WHERE is_active = TRUE;

-- ✅ 建議：建立軟刪除查詢 View
CREATE VIEW v_{table_name}_active AS
  SELECT * FROM {table_name} WHERE is_active = TRUE;
```

**刪除策略決策指引**:

| 資料類型 | 建議策略 | 原因 |
|---------|---------|------|
| 客戶/供應商資料 | 軟刪除 | 歷史訂單關聯、法規要求 |
| 訂單/交易紀錄 | 軟刪除（禁止硬刪除） | 財務稽核、帳務追溯 |
| 商品/產品資料 | 軟刪除 | 歷史訂單引用、價格追溯 |
| 庫存異動紀錄 | 軟刪除（禁止硬刪除） | 庫存追溯、盤點依據 |
| 使用者帳號 | 軟刪除 + 匿名化 | GDPR/個資法合規 |
| 系統日誌 | 歸檔刪除（超過保留期限） | 效能 vs 稽核平衡 |
| 暫存/快取資料 | 硬刪除 | 無保留價值 |
| 檔案附件 | 軟刪除（metadata）+ 延遲硬刪除（檔案） | 防誤刪、儲存空間管理 |

**🔴 強制檢查點 - 刪除策略設計**:
- [ ] 已為每張資料表標註刪除策略（軟刪除 / 硬刪除 / 歸檔刪除）
- [ ] 軟刪除資料表已包含 `deleted_at`、`deleted_by`、`is_active` 欄位
- [ ] 已建立軟刪除資料的查詢 View 或 Repository 層過濾機制
- [ ] 已定義資料保留政策（保留期限、歸檔週期）
- [ ] 已考慮關聯資料的級聯軟刪除策略（如：刪除訂單時，明細是否一併軟刪除）
- [ ] 已驗證軟刪除不影響 Unique Constraint（建議使用 Partial Unique Index）

🆕 **多領域差異化歸檔策略提示**（多業務領域系統適用）:

> 💡 不同業務領域的資料保留期限和歸檔需求可能不同：

| 領域 | 資料類型 | 建議保留期限 | 歸檔策略 | 法規依據 |
|------|---------|------------|---------|---------|
| 電商 | 訂單/交易 | 7 年（稅務稽核） | 年度歸檔至 Archive DB | 稅捐稽徵法 |
| 電商 | 購物車/瀏覽紀錄 | 90 天 | 超期硬刪除 | 無特殊要求 |
| 民宿 | 訂房/住宿紀錄 | 5 年（觀光法規） | 年度歸檔 | 觀光發展條例 |
| 民宿 | 旅客身分資料 | 退房後 1 年 | 匿名化後歸檔 | 個人資料保護法 |
| 共用 | 會員基本資料 | 帳號存續期 + 2 年 | 匿名化 | GDPR / 個資法 |
| 共用 | 系統日誌 | 180 天 | 壓縮歸檔至冷儲存 | 資安管理需求 |

> **關鍵原則**: 各領域歸檔排程可獨立執行，但共用實體的歸檔需確認所有領域都不再引用。

**級聯軟刪除範例**（經銷存系統）:

```
刪除供應商 → 軟刪除供應商資料
            → 停用該供應商的進貨管道（不刪除歷史進貨單）
            → 標記相關商品為「供應商已停用」

作廢銷貨單 → 軟刪除銷貨單（status='VOIDED'）
            → 回沖庫存（增加庫存數量）
            → 產生庫存異動紀錄（類型='銷貨作廢回沖'）
            → 更新應收帳款（如已開立）
```

🆕 **軟刪除前「未來承諾檢查」流程**:

> ⚠️ **重要**: 在執行軟刪除之前，必須檢查該實體是否存在「未來承諾」——
> 即已確認但尚未履行的訂單、預約、預購等。直接軟刪除會導致未來承諾無法履行。

**未來承諾檢查流程**:

```
軟刪除請求 → 查詢未來承諾
    ↓
有未來承諾？
    ├─ 是 → 🔴 阻擋刪除，提示處理方式：
    │       ├─ 方案 A: 先完成/取消所有未來承諾，再執行刪除
    │       ├─ 方案 B: 標記為「即將停用」，待承諾履行完畢後自動軟刪除
    │       └─ 方案 C: 強制刪除（需主管審核 + 記錄原因）
    └─ 否 → ✅ 正常執行軟刪除
```

**常見未來承諾場景**:

| 刪除對象 | 需檢查的未來承諾 | 處理建議 |
|---------|---------------|---------|
| 商品 | 未出貨的訂單、未到貨的預購單 | 標記「即將下架」→ 完成訂單後軟刪除 |
| 供應商 | 未到貨的進貨單、未結清的帳款 | 先完成進貨 + 結清帳款 → 再軟刪除 |
| 房型 | 未來的訂房（Check-in 日期 > 今天） | 聯繫旅客改房型或退款 → 再軟刪除 |
| 客戶 | 進行中的訂單、未使用的儲值/點數 | 完成訂單 + 退還儲值 → 再軟刪除 |
| 員工帳號 | 指派的未完成工單、審核中的流程 | 重新指派工單 → 再停用帳號 |

**SQL 範例（檢查商品是否有未來承諾）**:

```sql
-- 軟刪除商品前，檢查是否有未完成的訂單
SELECT COUNT(*) AS pending_orders
FROM order_items oi
JOIN orders o ON oi.order_id = o.id
WHERE oi.product_id = :productId
  AND o.status IN ('PENDING', 'CONFIRMED', 'PROCESSING', 'SHIPPED')
  AND o.is_active = TRUE;

-- 若 pending_orders > 0，阻擋軟刪除並提示使用者
```

##### 🆕 時間維度庫存設計模式（Calendar-based Inventory）

> ⚠️ **適用場景**: 當系統涉及「日曆型可用性」（如旅宿房間、租車、場地預約、課程預約）時，
> 傳統的「數量型庫存」（quantity-based）無法滿足需求，需採用「時間維度庫存」模式。

**庫存模型比較**:

| 特性 | 數量型庫存（傳統電商） | 時間維度庫存（旅宿/預約） |
|------|---------------------|------------------------|
| 庫存單位 | 商品數量（件/個/箱） | 日期 × 資源（間/台/位） |
| 庫存查詢 | `WHERE product_id = ? AND quantity > 0` | `WHERE resource_id = ? AND date BETWEEN ? AND ? AND available > 0` |
| 扣減方式 | `quantity -= order_qty` | 逐日扣減：每個入住日期的 available -= 1 |
| 超賣風險 | 單一數量競爭 | **每一天**都可能超賣，需逐日檢查 |
| 定價模型 | 固定價格 / 促銷價 | 依日期浮動（平日/假日/旺季/特殊日） |
| 典型衝突 | 最後一件商品 | 最後一間房 × 多天入住（任一天滿房即不可訂） |

**日曆型可用性表 Schema 設計**:

```sql
-- ✅ 資源定義表（房型、車型、場地等）
CREATE TABLE resource_type (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,          -- 例: '標準雙人房', '豪華套房'
    domain VARCHAR(50) NOT NULL,         -- 'accommodation', 'rental', 'venue'
    total_quantity INT NOT NULL,          -- 該資源總數量
    -- ... 其他屬性
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- ✅ 日曆型庫存表（核心：每天每資源一列）
CREATE TABLE resource_availability (
    id BIGSERIAL PRIMARY KEY,
    resource_type_id BIGINT NOT NULL REFERENCES resource_type(id),
    date DATE NOT NULL,                   -- 具體日期
    total_inventory INT NOT NULL,         -- 當日總庫存
    booked INT NOT NULL DEFAULT 0,        -- 已預訂數量
    blocked INT NOT NULL DEFAULT 0,       -- 維護/封鎖數量
    available INT GENERATED ALWAYS AS (total_inventory - booked - blocked) STORED,
    -- 動態定價欄位
    base_price DECIMAL(10,2) NOT NULL,    -- 基礎價格
    adjusted_price DECIMAL(10,2),         -- 調整後價格（季節/需求）
    price_rule_id BIGINT,                 -- 對應定價規則
    -- 約束
    UNIQUE(resource_type_id, date),
    CHECK (booked >= 0),
    CHECK (blocked >= 0),
    CHECK (total_inventory - booked - blocked >= 0)  -- 防止超賣
);

-- ✅ 建立查詢索引
CREATE INDEX idx_availability_lookup
    ON resource_availability(resource_type_id, date, available);
```

**季節定價規則表 Schema**:

```sql
-- ✅ 定價規則表
CREATE TABLE pricing_rule (
    id BIGSERIAL PRIMARY KEY,
    resource_type_id BIGINT REFERENCES resource_type(id),
    rule_name VARCHAR(100) NOT NULL,       -- '春節加價', '平日優惠'
    rule_type VARCHAR(30) NOT NULL,        -- 'SEASONAL', 'DAY_OF_WEEK', 'DEMAND', 'EVENT'
    priority INT NOT NULL DEFAULT 0,       -- 規則優先級（高覆蓋低）
    -- 適用條件
    start_date DATE,                       -- 適用開始日
    end_date DATE,                         -- 適用結束日
    days_of_week INT[],                    -- 適用星期（1=Mon...7=Sun）
    -- 定價方式
    price_modifier_type VARCHAR(20) NOT NULL, -- 'FIXED', 'PERCENTAGE', 'ABSOLUTE'
    modifier_value DECIMAL(10,2) NOT NULL,    -- 加減金額或百分比
    -- metadata
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ✅ 特殊日期定價（國定假日、活動期間）
CREATE TABLE special_date_pricing (
    id BIGSERIAL PRIMARY KEY,
    date DATE NOT NULL,
    label VARCHAR(100),                    -- '中秋連假', '跨年'
    resource_type_id BIGINT REFERENCES resource_type(id),
    override_price DECIMAL(10,2),          -- 直接覆蓋價格
    UNIQUE(date, resource_type_id)
);
```

**🔴 預約/庫存並發控制策略（防止雙重預訂）**:

> ⚠️ 時間維度庫存的並發風險遠高於傳統庫存——因為一筆預訂跨越多天，
> **每一天**都必須同時有剩餘庫存，任一天失敗即整筆失敗。

| 策略 | 實作方式 | 適用場景 | 優缺點 |
|------|---------|---------|--------|
| **樂觀鎖（Optimistic Lock）** | `WHERE available >= 1` + 檢查影響列數 | 中低併發（民宿、小型旅館） | 實作簡單，高併發時重試率高 |
| **悲觀鎖（Pessimistic Lock）** | `SELECT ... FOR UPDATE` 鎖定日期範圍列 | 高併發（OTA 平台、熱門飯店） | 保證一致性，可能造成鎖等待 |
| **分散式鎖（Redis Lock）** | Redis `SETNX` 鎖定資源+日期 | 微服務架構、多節點部署 | 適合分散式，需處理鎖逾時 |

**樂觀鎖實作範例**:

```sql
-- Step 1: 嘗試扣減每一天的庫存（在 Transaction 中）
BEGIN;

UPDATE resource_availability
SET booked = booked + 1
WHERE resource_type_id = :resourceTypeId
  AND date BETWEEN :checkInDate AND :checkOutDate - INTERVAL '1 day'
  AND available >= 1;  -- 只有有庫存的日期才會更新

-- Step 2: 檢查影響列數是否等於入住天數
-- 若 affected_rows < 預期天數 → 某天已滿，ROLLBACK
-- 若 affected_rows = 預期天數 → 全部成功，COMMIT

COMMIT;  -- 或 ROLLBACK;
```

**悲觀鎖實作範例**:

```sql
BEGIN;

-- Step 1: 鎖定日期範圍（防止其他交易同時修改）
SELECT * FROM resource_availability
WHERE resource_type_id = :resourceTypeId
  AND date BETWEEN :checkInDate AND :checkOutDate - INTERVAL '1 day'
FOR UPDATE;

-- Step 2: 檢查所有日期是否都有剩餘庫存
-- (application code 逐日檢查 available >= 1)

-- Step 3: 扣減庫存
UPDATE resource_availability
SET booked = booked + 1
WHERE resource_type_id = :resourceTypeId
  AND date BETWEEN :checkInDate AND :checkOutDate - INTERVAL '1 day';

COMMIT;
```

**🔴 強制檢查點 - 時間維度庫存設計**:
- [ ] 已識別系統中「時間維度庫存」vs「數量型庫存」的資源
- [ ] 日曆型可用性表已設計，包含 total_inventory / booked / blocked / available
- [ ] 已設計季節定價規則（平日/假日/旺季/特殊日）
- [ ] 已選擇並發控制策略（樂觀鎖/悲觀鎖/分散式鎖）並驗證
- [ ] 已處理跨日預訂的原子性（一筆訂單跨多天，需全部成功或全部失敗）
- [ ] 已考慮「最後一間房」問題的 race condition 防護

> 💡 **混合系統提示**：若系統同時包含「數量型庫存」（商品）和「時間維度庫存」（房間/預約），
> 建議在 Stage 5 資料模型設計時明確區分兩套庫存管理機制，避免用同一套模型硬套不同需求。

##### 🆕 內容版本管理架構設計（Content Versioning）

> ⚠️ **適用場景**: 當系統需要追蹤內容修改歷史（如 CMS 文章版本、Wiki 知識庫、文檔協作），
> 需要設計「版本鏈」資料模型，支援版本比對（Diff）、版本回滾、審計追蹤。

> **版本儲存策略比較**:
>
> | 策略 | 原理 | 優勢 | 劣勢 | 適用場景 |
> |------|------|------|------|---------|
> | **完整副本** | 每次修改保存完整內容 | 查詢簡單、回滾快速 | 儲存空間大 | 文章/知識庫（內容 < 100KB） |
> | **差量儲存** | 只保存與前一版的 diff | 儲存空間小 | 查詢需重組、效能較差 | 大型文檔、程式碼 |
> | **混合策略** | 每 N 版保存完整副本 + 中間用 diff | 平衡空間與效能 | 實作複雜 | 大型內容平台 |

> **推薦資料模型**（完整副本策略）:
>
> ```sql
> -- 文章主表（永遠指向最新發布版）
> CREATE TABLE articles (
>     id UUID PRIMARY KEY,
>     current_version_id UUID REFERENCES article_versions(id),
>     slug VARCHAR(255) UNIQUE,        -- URL 友善路徑
>     status VARCHAR(20),               -- DRAFT/PUBLISHED/ARCHIVED
>     author_id UUID REFERENCES users(id),
>     created_at TIMESTAMP DEFAULT NOW(),
>     updated_at TIMESTAMP DEFAULT NOW()
> );
>
> -- 版本表（保存每次修改的完整內容）
> CREATE TABLE article_versions (
>     id UUID PRIMARY KEY,
>     article_id UUID REFERENCES articles(id),
>     version_number INTEGER NOT NULL,   -- 遞增版本號
>     title VARCHAR(500),
>     content JSONB,                     -- 富文本內容（JSON 格式）
>     summary TEXT,                      -- 版本摘要（修改說明）
>     editor_id UUID REFERENCES users(id),
>     content_hash VARCHAR(64),          -- SHA-256 雜湊（快速比對）
>     word_count INTEGER,
>     created_at TIMESTAMP DEFAULT NOW(),
>     UNIQUE(article_id, version_number)
> );
> ```

> **版本保留策略**:
> - 已發布版本：永久保留
> - 草稿版本：保留最近 50 個，超過後自動清理最舊的
> - 版本比對：使用 content_hash 快速判斷內容是否變更，避免建立空版本
> - 版本清理：使用排程任務（Cron）定期執行，避免影響線上效能

##### 🆕 多領域共用實體建模指引

> 💡 在多領域融合系統中，某些實體（如會員、支付、通知）被多個領域共用，
> 而其他實體則為各領域專屬。錯誤的建模會導致領域耦合過深或資料重複。

**實體分類原則**:

| 類型 | 定義 | 範例 | 建模策略 |
|------|------|------|---------|
| **共用核心實體** | 被所有領域引用、不屬於任何單一領域 | 會員(Member)、支付(Payment)、通知(Notification) | 放在「共用模組」，各領域透過 ID 引用 |
| **領域專屬實體** | 只在單一領域使用 | 商品(Product)、房型(RoomType)、購物車(Cart) | 放在各自領域模組內 |
| **領域延伸實體** | 共用實體在特定領域的擴展屬性 | 會員的電商偏好、會員的住宿偏好 | 使用「擴展表」模式，避免汙染共用實體 |

**擴展表模式範例**:

```sql
-- ✅ 共用核心：會員主表（不含任何領域專屬欄位）
CREATE TABLE member (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    phone VARCHAR(20),
    level VARCHAR(20) DEFAULT 'BASIC',
    total_points INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ✅ 電商領域擴展：會員電商偏好
CREATE TABLE member_shop_profile (
    member_id BIGINT PRIMARY KEY REFERENCES member(id),
    preferred_categories TEXT[],     -- 偏好商品類別
    shipping_address_id BIGINT,      -- 預設收貨地址
    cart_reminder_enabled BOOLEAN DEFAULT TRUE
);

-- ✅ 民宿領域擴展：會員住宿偏好
CREATE TABLE member_stay_profile (
    member_id BIGINT PRIMARY KEY REFERENCES member(id),
    preferred_room_type VARCHAR(50), -- 偏好房型
    dietary_restrictions TEXT,        -- 飲食限制
    loyalty_tier VARCHAR(20),        -- 住宿忠誠等級
    total_nights INT DEFAULT 0       -- 累計住宿天數
);
```

> **🔴 關鍵原則**: 共用實體表**絕不**放領域專屬欄位。若需要擴展，使用 1:1 擴展表。
> 這樣當新增領域時，只需新增擴展表，不需修改共用表。

---

**5.2.3 API / Data Access Layer 設計（情境適配）**

> ⚠️ **重要**: 並非所有專案都需要 Backend API！請先判斷您的專案類型。

##### 步驟 5.2.3.1: 判斷是否需要 Backend API

**判斷準則**:

✅ **需要 Backend API 的情況**:
- [ ] Web App（前後端分離架構）
- [ ] Mobile App 需要雲端同步功能
- [ ] 多平台共用資料（Web + Mobile）
- [ ] 需要伺服器端計算或驗證
- [ ] 需要第三方服務整合（支付、簡訊、Email）
- [ ] 需要即時通訊功能（WebSocket, Socket.IO）
- [ ] 需要背景任務處理（排程、批次處理）

❌ **不需要 Backend API 的情況**:
- [ ] 純本地 Mobile App（所有資料存本地）
- [ ] 單機應用程式
- [ ] 工具型 App（無需同步）
- [ ] 100% 離線可用的 App
- [ ] 簡單計算或轉換工具

**判斷結果**: [請勾選] ☐ 需要 Backend API  ☐ 不需要 Backend API

---

##### 步驟 5.2.3.2: 依判斷結果執行對應設計

**情境 A: 需要 Backend API**

執行指令：
```
「請設計 RESTful API 規格」
```

系統會產出：
- **API Specification** (使用 [API_Specification_Template.md](../../docs_template/core/api/API_Specification_Template.md))
  - RESTful API 端點列表
  - Request/Response 格式（JSON Schema）
  - 認證授權機制（JWT / OAuth）
  - API 版本策略（URL versioning / Header versioning）
  - 錯誤處理設計（統一錯誤碼）
  - Rate Limiting 策略
  - API 文檔（Swagger / OpenAPI 3.0）

**產出文件**:
- ✅ API Specification (必須)
- ✅ API Index (API 導覽文件)
- ✅ 認證授權設計文件
- ✅ API 錯誤碼對照表
- ✅ API-SRD 追溯矩陣 (必須)

**📋 API-SRD 追溯矩陣範例** 🆕 (v0.01 新增)

確保每個 API 端點都能追溯到 SRD 功能需求：

| API 端點 | HTTP Method | SRD 功能 | User Story | 狀態 |
|---------|-------------|---------|------------|------|
| `/api/v1/users/register` | POST | SRD-AUTH-001 | US-001 | ✅ |
| `/api/v1/users/login` | POST | SRD-AUTH-002 | US-001 | ✅ |
| `/api/v1/transactions` | GET | SRD-TXN-001 | US-003 | ✅ |
| `/api/v1/transactions` | POST | SRD-TXN-002 | US-004 | ✅ |
| `/api/v1/reports/monthly` | GET | SRD-RPT-001 | US-006 | ✅ |

**追溯矩陣用途**：
- 🔍 **需求覆蓋驗證**：確保所有 SRD 功能都有對應 API
- 🔍 **變更影響分析**：SRD 變更時快速識別受影響的 API
- 🔍 **測試規劃**：依據 API-SRD 對應關係規劃測試案例
- 🔍 **文檔一致性**：確保 API 文檔與 SRD 描述一致

**追溯矩陣檢查項目**：
- [ ] 每個 API 都有對應的 SRD 功能編號
- [ ] 每個 SRD 功能都有對應的 API（或標註「不需要 API」）
- [ ] API 與 SRD 描述一致（命名、參數、回傳值）
- [ ] 跨 API 的資料流有清楚標示

**範例**:
- Web 電商平台（前後端分離）→ 需要 Backend API
- Mobile 社交 App（雲端同步）→ 需要 Backend API
- 跨平台記帳 App（雲端備份）→ 需要 Backend API

---

**情境 B: 不需要 Backend API（本地 App）**

執行指令：
```
「請設計 Data Access Layer（資料訪問層）」
```

系統會產出：
- **Data Access Layer Design** (使用 [Data_Access_Layer_Template.md](../../docs_template/srd/Data_Access_Layer_Template.md))
  - 資料訪問層架構概述
  - Repository Pattern 定義
  - Service Layer 設計
  - 資料模型 Schema（Realm / SQLite / CoreData）
  - 業務查詢方法
  - 錯誤處理策略
  - Schema 遷移策略

**產出文件**:
- ✅ Data Access Layer Design (必須)
- ✅ Repository Interface 定義
- ✅ Service Layer 設計
- ✅ 資料初始化策略（Seed Data）

**範例**:
- 純本地記帳 App（資料存 Realm）→ 不需要 Backend API，使用 Data Access Layer
- 離線筆記 App（資料存 SQLite）→ 不需要 Backend API，使用 Data Access Layer
- 計算器 App（無需資料持久化）→ 不需要 Backend API，不需要 Data Access Layer

---

##### 步驟 5.2.3.3: 特殊情況處理

**情境 C: 混合架構（本地 + 雲端）**

若專案需要「本地優先 + 選擇性雲端同步」（如記帳 App 的雲端備份功能）：

執行指令：
```
「請設計混合架構：本地 Data Access Layer + 雲端同步 API」
```

系統會產出：
- **Data Access Layer Design** (本地資料訪問)
- **Sync API Specification** (雲端同步 API)
- **資料同步策略文件**
  - 同步時機（手動 / 自動）
  - 衝突解決策略
  - 離線佇列機制
  - 資料版本控制

**產出文件**:
- ✅ Data Access Layer Design
- ✅ Sync API Specification
- ✅ Data Sync Strategy Document
- ✅ Conflict Resolution Policy

**範例**:
- 記帳 App（本地優先 + 雲端備份）
- 待辦事項 App（離線可用 + 跨裝置同步）
- 筆記 App（本地儲存 + 選擇性雲端同步）

---

**判斷流程圖**:

```
開始架構設計
      │
      ▼
是否需要雲端資料存取？
      │
      ├─ 是 ──────────────────────┐
      │                          │
      ▼                          ▼
是否需要伺服器端處理？      是否需要跨裝置同步？
      │                          │
      ├─ 是 ─┐                  ├─ 是 ─┐
      │      │                  │      │
      ▼      ▼                  ▼      ▼
   情境 A       情境 C              情境 C
Backend API   混合架構            混合架構
      │          │                  │
      ▼          ▼                  ▼
  產出 API    產出 DAL           產出 DAL
   Spec     + Sync API          + Sync API
      │          │                  │
      └──────────┴──────────────────┘
                 │
                 ▼
              完成設計


   否 ──────────────────────────┐
                                │
                                ▼
                          是否需要本地資料儲存？
                                │
                                ├─ 是 ─┐
                                │      │
                                ▼      ▼
                             情境 B
                          Data Access Layer
                                │
                                ▼
                            產出 DAL
                             Design
                                │
                                ▼
                            完成設計
```

**5.2.4 效能需求量化設計** 🔴 **v0.01 新增**

> 💡 **為什麼需要量化效能指標**：
> - 避免後期效能問題重構成本高昂
> - 提供明確的測試驗收標準
> - 協助技術選型和架構決策
> - 建立效能監控基準線

**核心效能指標（Performance Metrics）**：

根據專案類型選擇適用的指標類別：

**類別 1：響應時間指標 (Response Time Metrics)**

適用情境：所有 Web/Mobile App、API 服務

| 指標名稱 | 定義 | 建議目標值 | 測量方式 |
|---------|------|-----------|---------|
| **API Response Time** | API 請求到回應的時間 | • 簡單查詢: < 200ms<br>• 複雜查詢: < 500ms<br>• 批次處理: < 2s | Server logs, APM tools |
| **Page Load Time (FCP)** | First Contentful Paint 時間 | • < 1.5s (良好)<br>• 1.5-2.5s (需改善)<br>• > 2.5s (差) | Lighthouse, WebPageTest |
| **Time to Interactive (TTI)** | 頁面可互動時間 | • < 3.5s (良好)<br>• 3.5-5.5s (需改善)<br>• > 5.5s (差) | Lighthouse, Chrome DevTools |
| **Database Query Time** | 資料庫查詢執行時間 | • 單筆查詢: < 50ms<br>• JOIN 查詢: < 200ms<br>• 聚合查詢: < 500ms | DB profiling tools |

**類別 2：吞吐量指標 (Throughput Metrics)**

適用情境：高流量 API、資料處理服務、批次作業

| 指標名稱 | 定義 | 建議目標值 | 測量方式 |
|---------|------|-----------|---------|
| **Requests Per Second (RPS)** | 每秒處理請求數 | • 小型專案: 100 RPS<br>• 中型專案: 500 RPS<br>• 大型專案: 2000+ RPS | Load testing (JMeter, k6) |
| **Transactions Per Second (TPS)** | 每秒完成交易數 | • 電商系統: 50-200 TPS<br>• 金融系統: 500+ TPS | APM, Database metrics |
| **Data Processing Rate** | 資料處理速率 | • 批次匯入: 1000 records/s<br>• ETL 流程: 依業務需求 | Custom logging |

**類別 3：並發性指標 (Concurrency Metrics)**

適用情境：多使用者系統、即時通訊、電商平台

| 指標名稱 | 定義 | 建議目標值 | 測量方式 |
|---------|------|-----------|---------|
| **Concurrent Users** | 系統同時支援的使用者數 | • 小型: 100 並發<br>• 中型: 500 並發<br>• 大型: 5000+ 並發 | Load testing |
| **Connection Pool Size** | 資料庫連線池大小 | • 初始: 10<br>• 最大: 50-100<br>• 依 CPU 核心數調整 | Connection pool config |
| **Thread Pool Size** | 執行緒池大小 | • CPU-bound: CPU 核心數 × 2<br>• I/O-bound: CPU 核心數 × 10 | Thread pool monitoring |

**類別 4：資源使用指標 (Resource Utilization Metrics)**

適用情境：所有專案（避免資源浪費或不足）

| 指標名稱 | 定義 | 建議目標值 | 測量方式 |
|---------|------|-----------|---------|
| **CPU Utilization** | CPU 使用率 | • 正常: < 70%<br>• 警告: 70-85%<br>• 緊急: > 85% | Server monitoring |
| **Memory Usage** | 記憶體使用量 | • 正常: < 70%<br>• 警告: 70-85%<br>• 緊急: > 85% | Server monitoring |
| **Disk I/O** | 磁碟讀寫速度 | • SSD: > 500 MB/s<br>• HDD: > 100 MB/s | iostat, iotop |
| **Network Bandwidth** | 網路頻寬使用 | • 依業務需求<br>• 預留 30% buffer | Network monitoring |

**類別 5：使用者體驗指標 (User Experience Metrics)**

適用情境：面向使用者的 Web/Mobile App

| 指標名稱 | 定義 | 建議目標值 | 測量方式 |
|---------|------|-----------|---------|
| **Error Rate** | 錯誤率 | • < 0.1% (優秀)<br>• 0.1-1% (可接受)<br>• > 1% (需改善) | Error tracking (Sentry) |
| **Availability (Uptime)** | 系統可用率 | • 99.9% (三個九)<br>• 99.99% (四個九) | Uptime monitoring |
| **Crash-Free Rate** | App 無崩潰率 | • iOS/Android: > 99.5% | Crashlytics, Firebase |

---

**效能指標設計流程**：

**步驟 1：識別關鍵效能場景**

根據專案類型，識別 3-5 個最重要的效能場景：

```markdown
範例：電商平台

1. 🔴 **關鍵場景 1**：使用者瀏覽商品列表
   - 預期 QPS: 500 requests/s
   - 頁面載入時間: < 1.5s (FCP)
   - API 響應時間: < 200ms

2. 🔴 **關鍵場景 2**：使用者搜尋商品
   - 預期 QPS: 200 requests/s
   - API 響應時間: < 500ms
   - 資料庫查詢時間: < 200ms

3. 🔴 **關鍵場景 3**：使用者結帳付款
   - 預期 TPS: 50 transactions/s
   - 端到端交易時間: < 3s
   - 並發使用者數: 100 concurrent checkouts
```

**步驟 2：制定量化目標**

針對每個關鍵場景，制定具體的效能目標：

| 場景 | 指標類型 | 目標值 | 測試條件 | 驗收標準 |
|------|---------|--------|---------|---------|
| 商品列表 | Response Time | < 1.5s | 1000 並發 | 95th percentile < 1.5s |
| 商品搜尋 | Response Time | < 500ms | 500 並發 | 99th percentile < 800ms |
| 結帳付款 | TPS | 50 TPS | 100 並發 | 無錯誤，成功率 100% |

**步驟 3：定義效能測試策略**

```yaml
效能測試類型：
  - 負載測試 (Load Testing):
      目的: 驗證系統在預期負載下的表現
      工具: JMeter, k6, Gatling
      執行時機: 每個 Sprint 結束前

  - 壓力測試 (Stress Testing):
      目的: 找出系統崩潰點
      工具: JMeter, Locust
      執行時機: 上線前

  - 浸泡測試 (Soak Testing):
      目的: 驗證長時間運行穩定性
      工具: k6, JMeter
      執行時機: UAT 階段

  - 尖峰測試 (Spike Testing):
      目的: 驗證突發流量處理能力
      工具: Gatling, k6
      執行時機: 重大活動前（如促銷、行銷活動）
```

**步驟 4：建立效能監控計畫**

```markdown
監控工具選擇：

前端效能監控：
  - Google Lighthouse (Web Vitals)
  - WebPageTest
  - Chrome User Experience Report (CrUX)

後端效能監控：
  - APM 工具: New Relic, Datadog, Dynatrace
  - 日誌分析: ELK Stack (Elasticsearch, Logstash, Kibana)
  - 資料庫監控: pgAdmin, MySQL Workbench, MongoDB Compass

基礎設施監控：
  - Prometheus + Grafana
  - CloudWatch (AWS), Azure Monitor, GCP Monitoring
```

**步驟 5：效能優化預算分配**

預留時間和資源進行效能優化：

| 專案規模 | 效能設計時間 | 效能測試時間 | 效能優化時間 | 總時間佔比 |
|---------|------------|------------|------------|----------|
| 小型專案 | 4 小時 | 8 小時 | 16 小時 | 10% |
| 中型專案 | 8 小時 | 16 小時 | 32 小時 | 12% |
| 大型專案 | 16 小時 | 32 小時 | 64 小時 | 15% |

---

**效能指標文件化範本**：

```markdown
# 效能需求規格書 (Performance Requirements Specification)

## 1. 效能目標總覽

| 指標類別 | 關鍵指標 | 目標值 | 優先級 |
|---------|---------|--------|--------|
| 響應時間 | API Response Time | < 200ms (P95) | 🔴 P0 |
| 吞吐量 | Requests Per Second | 500 RPS | 🟡 P1 |
| 並發性 | Concurrent Users | 1000 concurrent | 🟡 P1 |
| 可用性 | Uptime | 99.9% | 🔴 P0 |

## 2. 關鍵場景效能需求

### 場景 1：[場景名稱]

**業務描述**: [描述業務場景]

**效能指標**:
- Response Time: < [時間] (P95)
- Throughput: [數量] requests/s
- Error Rate: < [百分比]

**測試條件**:
- 並發使用者數: [數量]
- 測試時長: [時間]
- 資料量: [數量] records

**驗收標準**:
- [ ] P95 Response Time < [時間]
- [ ] Error Rate < [百分比]
- [ ] 無記憶體洩漏

## 3. 效能測試計畫

[詳細測試計畫...]

## 4. 效能監控方案

[監控工具和指標...]
```

---

**產出文件**：
- [ ] **Performance Requirements Specification** (效能需求規格書)
- [ ] **Performance Testing Plan** (效能測試計畫) 🆕 **v0.01 強化** - 使用 [Performance_Test_Plan_Template.md](../../guides/system/testing/Performance_Test_Plan_Template.md)
- [ ] **Performance Monitoring Dashboard** (效能監控儀表板設計)

**相關文件範本**：
- [Performance_Test_Plan_Template.md](../../docs_template/core/tests/Performance_Test_Plan_Template.md) (v0.01 新增)

---

#### 步驟 5.2.4：即時通訊 API 設計（WebSocket/SSE）（🆕 v0.01 新增）

> 💡 若專案需要即時數據更新（如庫存即時同步、聊天、通知推送），需額外設計即時通訊 API。

**判斷條件**: 以下任一需求存在時，需設計即時 API：
- 多使用者同時操作同一筆資料（如庫存）
- 即時通知推送（如訂單狀態變更）
- 即時數據面板（如 Dashboard 即時更新）
- 多平台資料同步（如 Web 操作後 Mobile 即時反映）

**技術選項**:

| 技術 | 適用場景 | 優點 | 缺點 |
|------|---------|------|------|
| **WebSocket** | 雙向即時通訊 | 低延遲、雙向、全雙工 | 連線管理複雜、負載均衡困難 |
| **SSE (Server-Sent Events)** | 伺服器單向推送 | 簡單、HTTP 相容、自動重連 | 單向、IE 不支援 |
| **Long Polling** | 簡易即時更新 | 最簡單、相容性最佳 | 延遲高、資源浪費 |
| **Socket.io** | WebSocket + Fallback | 自動降級、房間功能 | 非標準協定、伺服器端限制 |

**Spring Boot WebSocket 配置範例**:

> ⚠️ **安全警告**: 以下範例中 `setAllowedOrigins("*")` 僅適用於**開發環境**。
> 生產環境**必須**限制允許的 Origin，避免跨站 WebSocket 劫持攻擊。

```java
@Configuration
@EnableWebSocketMessageBroker
public class WebSocketConfig implements WebSocketMessageBrokerConfigurer {
    @Override
    public void registerStompEndpoints(StompEndpointRegistry registry) {
        // ⚠️ 開發環境：允許所有來源（僅限開發！）
        // registry.addEndpoint("/ws").setAllowedOrigins("*").withSockJS();

        // ✅ 生產環境：限制允許的 Origin
        registry.addEndpoint("/ws")
            .setAllowedOrigins("https://your-domain.com", "https://admin.your-domain.com")
            .withSockJS();
    }
    @Override
    public void configureMessageBroker(MessageBrokerRegistry registry) {
        registry.enableSimpleBroker("/topic", "/queue");
        registry.setApplicationDestinationPrefixes("/app");
    }
}
```

**🔴 WebSocket 安全檢查清單**:
- [ ] `setAllowedOrigins` 已設定為具體域名（非 `*`）
- [ ] WebSocket 連線需要 JWT Token 驗證（在 handshake 階段）
- [ ] 已設定連線數上限（防止 DoS）
- [ ] 已設定訊息大小上限（防止記憶體溢出）

**API 規格文檔格式** (WebSocket):
```yaml
WebSocket Endpoint: /ws/inventory-updates
  Protocol: STOMP over WebSocket
  Subscribe: /topic/inventory/{productId}
  Message Format: JSON
  Message Example:
    { "productId": "P001", "quantity": 150, "updatedAt": "2026-01-15T10:30:00Z" }
  Authentication: JWT Token in handshake header
```

---

#### 步驟 5.2.5：多平台 API 版本: v0.01 新增）

> 💡 當專案支援多平台（Web + Mobile + Desktop）且各平台版本可能不同步時，需制定 API 版本策略。

**API 版本策略選項**:

| 策略 | 格式 | 適用場景 | 說明 |
|------|------|---------|------|
| **URI 路徑版本** | `/api/v1/products` | ✅ 推薦、最常用 | 清晰、易理解、易快取 |
| **Header 版本** | `Accept: application/vnd.api.v1+json` | 進階場景 | RESTful、URL 不變 |
| **Query 參數版本** | `/api/products?version=1` | 簡單場景 | 快速實作 |

**多平台版本管理建議**:

```
API v1 (基礎版) ──── Web v1.0、Android v1.0、macOS v1.0
    │
API v1.1 (相容擴充) ── Web v1.1（新增欄位，向下相容）
    │
API v2 (破壞性變更) ── Web v2.0、Android v2.0
                        macOS v1.x 仍使用 API v1（過渡期）
```

**強制規則**:
- 新版 API 必須保持向下相容至少 2 個 Sprint
- 棄用 API 必須標註 `@Deprecated` 並設定移除日期
- 各平台 SDK 版本與 API 版本對照表必須維護在 API Index 中

🆕 **多領域 API 模組化策略**（多業務領域系統適用）:

> 💡 當系統包含多個業務領域（如電商 + 民宿）時，API 路徑需按領域模組化，
> 讓各領域可獨立演進、獨立部署，避免單一領域的 API 變更影響其他領域。

**API 路徑模組化策略比較**:

| 策略 | 路徑格式 | 適用場景 | 優缺點 |
|------|---------|---------|--------|
| **按領域前綴** | `/api/v1/shop/products`<br>`/api/v1/stay/rooms` | 中小型融合系統（Monolith） | ✅ 簡單清晰；❌ 仍在同一服務中 |
| **按子域名** | `shop-api.example.com/v1/products`<br>`stay-api.example.com/v1/rooms` | 微服務架構 | ✅ 完全獨立部署；❌ 需 API Gateway |
| **按 API Gateway 路由** | `/api/v1/products` → Shop Service<br>`/api/v1/rooms` → Stay Service | API Gateway 架構 | ✅ 統一入口 + 獨立服務；❌ Gateway 維護成本 |

**共用 API vs 領域專屬 API**:

```
共用 API（兩個領域共用）:
  /api/v1/members/*       ← 會員管理（電商+民宿共用）
  /api/v1/payments/*      ← 支付處理（共用支付模組）
  /api/v1/notifications/* ← 通知系統（共用通知模組）

電商領域專屬 API:
  /api/v1/shop/products/* ← 商品管理
  /api/v1/shop/orders/*   ← 電商訂單
  /api/v1/shop/cart/*     ← 購物車
  /api/v1/shop/inventory/*← 數量型庫存

民宿領域專屬 API:
  /api/v1/stay/rooms/*         ← 房型管理
  /api/v1/stay/bookings/*      ← 訂房管理
  /api/v1/stay/availability/*  ← 日曆可用性
  /api/v1/stay/checkin/*       ← 入住管理
```

**領域獨立演進範例**:

```
Sprint 5: 電商領域需要新增「限時搶購」功能
  → 只需修改 /api/v1/shop/* 相關 API
  → 民宿領域 /api/v1/stay/* 完全不受影響
  → 可獨立測試、獨立部署電商模組

Sprint 6: 民宿領域需要整合 OTA 渠道
  → 只需新增 /api/v1/stay/channels/* API
  → 電商領域 /api/v1/shop/* 完全不受影響
```

🆕 **跨領域合併報表 API 提示**:

> 💡 多領域系統常需要「統一報表」（彙總各領域數據），建議設計獨立的報表 API：

```
跨領域報表 API（獨立於各領域）:
  /api/v1/reports/member-summary    ← 會員跨領域消費彙總（電商+民宿）
  /api/v1/reports/revenue-dashboard ← 收入儀表板（各領域營收佔比）
  /api/v1/reports/cross-domain-audit← 跨領域稽核報表
```

> 報表 API 應**只讀取**各領域的資料（透過各領域 API 或共用讀取副本），不直接存取領域內部表。

🆕 **多渠道內容發布架構設計**（適用於 CMS/內容平台）：

> 💡 當系統需要將同一內容發布到多個渠道（Web 網站、Mobile App、Email 通訊、社群媒體）時，
> 需要設計「渠道無關的核心內容 + 渠道特定的轉換層」架構。

> **架構設計**:
>
> ```
> [核心內容] → [轉換引擎] → [Web HTML + SEO Meta]
>                          → [App Push + 摘要]
>                          → [Email Template + 純文字]
>                          → [Social Media + OG Tags + 縮圖]
> ```

> **發布狀態機**:
>
> ```
> [DRAFT] → [SUBMITTED] → [APPROVED] → [SCHEDULED] → [PUBLISHING] → [PUBLISHED]
>                                           ↓                            ↓
>                                      [CANCELLED]                 [PARTIALLY_FAILED]
>                                                                       ↓
>                                                                  [RETRY_PENDING]
> ```
>
> - `PUBLISHING`: 正在逐一發布到各渠道（非瞬間完成）
> - `PARTIALLY_FAILED`: 部分渠道發布失敗（如：Email 成功但社群 API 失敗）
> - `RETRY_PENDING`: 失敗渠道等待重試（最多重試 3 次，間隔 1/5/15 分鐘）

> **API 設計**:
> - `POST /api/v1/content/{id}/publish` - 觸發即時發布（指定渠道列表）
> - `POST /api/v1/content/{id}/schedule` - 排程發布（指定時間 + 渠道）
> - `GET /api/v1/content/{id}/publish-status` - 查詢各渠道發布狀態
> - `POST /api/v1/content/{id}/publish-retry` - 手動重試失敗渠道
> - `DELETE /api/v1/content/{id}/channels/{channel}` - 從指定渠道下架

> **渠道配置表**:
>
> ```sql
> CREATE TABLE publish_channels (
>     id UUID PRIMARY KEY,
>     name VARCHAR(50),          -- web, mobile_app, email, twitter, facebook
>     adapter_class VARCHAR(200), -- 渠道適配器類名
>     config JSONB,               -- 渠道特定配置（API Key 等）
>     is_active BOOLEAN DEFAULT true,
>     retry_policy JSONB          -- 重試策略（max_retries, backoff）
> );
>
> CREATE TABLE content_publications (
>     id UUID PRIMARY KEY,
>     content_id UUID REFERENCES articles(id),
>     channel_id UUID REFERENCES publish_channels(id),
>     status VARCHAR(20),         -- PENDING/PUBLISHING/PUBLISHED/FAILED
>     published_at TIMESTAMP,
>     external_url VARCHAR(500),  -- 外部平台發布後的 URL
>     error_message TEXT,
>     retry_count INTEGER DEFAULT 0,
>     created_at TIMESTAMP DEFAULT NOW()
> );
> ```

🆕 **SEO 友善設計指引**（適用於面向公眾的內容平台）：

> 💡 當系統產出的內容需要被搜尋引擎收錄（如 CMS 文章、知識庫公開頁面），需在架構設計階段考慮 SEO。

> **SEO 資料模型設計**:
> - 每篇內容需包含：`meta_title`（≤60 字元）、`meta_description`（≤160 字元）、`slug`（URL 友善路徑）
> - `slug` 需全局唯一，支援自動生成（從標題轉換）和手動覆蓋
> - `canonical_url` 欄位：防止多渠道發布造成重複內容
>
> **技術實作要點**:
> - 使用 SSR/SSG（Next.js `getStaticProps` / `getServerSideProps`）確保搜尋引擎可爬取
> - 自動生成 `sitemap.xml`（包含所有已發布頁面，排除草稿和歸檔）
> - 結構化資料（JSON-LD）：Article、FAQPage、BreadcrumbList
> - Open Graph / Twitter Cards Meta 標籤自動生成
> - `robots.txt` 配置：允許爬取公開內容，禁止管理後台

> **URL Slug 設計規則**:
> - 格式：`/articles/{slug}` 或 `/knowledge/{category}/{slug}`
> - 自動生成規則：標題 → 小寫 → 空格轉 `-` → 移除特殊字元 → 截斷至 100 字元
> - 中文 Slug：轉換為拼音或使用短 UUID（`/articles/a1b2c3`）
> - Slug 變更時自動建立 301 重定向（保留舊 URL 的 SEO 權重）

🆕 **內容管理系統細粒度權限設計提示**：

> 💡 內容管理系統的權限模型通常比傳統 CRUD 更複雜，需考慮「內容所有權」、「審核權限」、「發布權限」的分離。

> **CMS 常見角色與權限矩陣**:
> | 權限操作 | 作者(Author) | 編輯(Editor) | 主編(Chief Editor) | 管理員(Admin) |
> |---------|-------------|-------------|-------------------|-------------|
> | 建立草稿 | ✅ | ✅ | ✅ | ✅ |
> | 編輯自己的文章 | ✅ | ✅ | ✅ | ✅ |
> | 編輯他人文章 | ❌ | ✅ | ✅ | ✅ |
> | 提交審核 | ✅ | ✅ | ✅ | ✅ |
> | 審核文章 | ❌ | ❌ | ✅ | ✅ |
> | 發布/下架 | ❌ | ❌ | ✅ | ✅ |
> | 刪除文章 | 自己的 | 自己的 | ✅ | ✅ |
> | 管理分類/標籤 | ❌ | ✅ | ✅ | ✅ |
> | 管理使用者 | ❌ | ❌ | ❌ | ✅ |
>
> **設計要點**:
> - 「資源所有權」優先：作者對自己的內容有完整 CRUD，但不能操作他人內容
> - 「審核與發布分離」：審核人和發布人可以是不同角色
> - 「欄位級權限」：某些欄位只有特定角色可修改（如 SEO Meta 只有編輯可改）
> - 權限快取策略：角色變更後需即時失效（建議 JWT 搭配短 TTL 或即時校驗）

🆕 **知識圖譜功能設計提示**（適用於知識管理/KMS 系統）：

> 💡 知識圖譜是 KMS 的進階功能，通常不納入 MVP。建議在 Stage 4 MVP 定義時將其列為 Phase 2/3 功能。

> **簡易知識圖譜實作方案**（使用關聯式資料庫）:
> ```sql
> -- 知識關係表（無需專用圖資料庫）
> CREATE TABLE knowledge_relations (
>     id UUID PRIMARY KEY,
>     source_id UUID REFERENCES articles(id),
>     target_id UUID REFERENCES articles(id),
>     relation_type VARCHAR(50),  -- RELATED_TO, PREREQUISITE, SEE_ALSO, PARENT_OF
>     strength DECIMAL(3,2),      -- 關聯強度 0.00~1.00
>     created_by UUID REFERENCES users(id),
>     created_at TIMESTAMP DEFAULT NOW()
> );
> ```
> - 若知識節點 < 10 萬，關聯式 DB + 遞迴查詢（CTE）足夠
> - 若需要複雜圖遍歷（如：最短路徑、社群偵測），考慮 Neo4j 或 Apache AGE（PostgreSQL 圖擴展）
> - 前端視覺化：D3.js / vis.js / Cytoscape.js

---

#### 步驟 5.3：架構設計確認點 🔴
系統會呈現：
1. 系統架構圖和說明
2. 技術架構決策 (ADR)
3. 可擴展性分析
4. **安全性設計** 🔴 **v0.01 強化** - 必須使用 [Security_Design_Checklist.md](checklists/Security_Design_Checklist.md) 檢查
   - **必須涵蓋項目**：
     - 認證與授權機制（Session/JWT/OAuth）
     - OWASP Top 10 評估與防護措施
     - 資料加密策略（傳輸層 TLS + 儲存層敏感欄位加密）
     - 稽核日誌設計（安全事件記錄）
     - API 安全設計（Rate Limiting、輸入驗證）
     - 敏感資料處理（個資保護、資料遮罩）
   - **檢查清單完成度**: 必須達到 ≥ 90%（未完成項目需評估風險並制定處理計畫）
5. **效能需求量化指標** 🔴 **v0.01 新增** (必須包含)
   - 響應時間目標 (Response Time)
   - 吞吐量目標 (Throughput)
   - 並發性目標 (Concurrency)
   - 資源使用目標 (Resource Utilization)
   - 效能測試計畫

   🆕 **季節性/事件驅動尖峰場景**（適用於有明顯流量波動的系統）:
   > 💡 若系統存在可預測的流量尖峰（如電商大促、旅遊旺季、開學季），
   > 效能指標不能只設「平均值」，需額外定義「尖峰場景」的效能目標。

   | 尖峰場景 | 典型倍率 | 效能目標調整 | 準備策略 |
   |---------|---------|------------|---------|
   | **電商大促**（雙11/黑五） | 平日 10-50x | 響應時間 ≤ 3s（可適度放寬）、零超賣 | 提前擴容、快取預熱、限流降級 |
   | **旅遊旺季搶房**（春節/暑假） | 平日 5-20x | 訂房 API ≤ 2s、並發鎖正確 | 庫存快取、佇列化訂房、CDN 靜態頁 |
   | **限時搶購/Flash Sale** | 瞬間 100x+ | 首頁 ≤ 1s、下單 ≤ 5s | 佇列削峰、預生成頁面、庫存預扣 |
   | **日常高峰**（午餐/下班時段） | 平日 2-3x | 維持標準效能目標 | Auto-scaling 自動擴縮 |

   > **AI 應主動詢問**：「您的系統是否有季節性或事件驅動的流量尖峰？若有，請描述尖峰場景和預估倍率。」

你需要確認架構是否符合需求和未來擴展性。

---

**產出文件檢查（情境適配版）**：

**所有情境必須產出**:
- [x] **SRD** (System Requirements Document - 系統需求文件)
- [x] **Architecture Decision Records (ADR)** - 架構決策記錄
- [x] **Database Schema** - 資料庫結構設計
- [x] **Data Migration Plan** 🔴 - 資料遷移計畫 (強制檢查)
  - 針對 SQL: 遷移腳本、版本管理、回滾計畫
  - 針對 Realm/CoreData: Schema Version、Migration Block
- [x] **Security Design Document** 🔴 **v0.01 強化** - 安全設計文件
  - **必須使用** [Security_Design_Checklist.md](checklists/Security_Design_Checklist.md) 完成全面檢查
  - **必須包含**: 認證授權、OWASP Top 10 防護、資料加密、稽核日誌、API 安全、敏感資料處理
  - **完成度要求**: ≥ 90%

**情境專屬產出**:

根據步驟 5.2.3 的判斷結果，勾選對應的產出文件：

**☐ 情境 A: Backend API 專案**
- [x] API Specification（使用 [API_Specification_Template.md](../../docs_template/core/api/API_Specification_Template.md)）
- [x] API Index（API 導覽文件）
- [x] 認證授權設計文件
- [❌] Data Access Layer Design（不適用）

**☐ 情境 B: 本地 App 專案**
- [❌] API Specification（不適用）
- [x] Data Access Layer Design（使用 [Data_Access_Layer_Template.md](../../docs_template/srd/Data_Access_Layer_Template.md)）
- [x] Repository Interface 定義
- [x] Service Layer 設計

**☐ 情境 C: 混合架構專案**
- [x] Data Access Layer Design（本地）
- [x] Sync API Specification（雲端同步）
- [x] Data Sync Strategy Document（資料同步策略）
- [x] Conflict Resolution Policy（衝突解決策略）

---

**產出文件快速檢查範例**:

**範例 1: 純本地記帳 App (MoneyTracker)**
- 情境判斷: ✅ 情境 B (本地 App)
- 必須產出:
  - [x] SRD
  - [x] ADR (3 個決策)
  - [x] Database Schema (Realm)
  - [x] Data Access Layer Design
  - [x] Security Design Document
- 不需要產出:
  - [❌] API Specification (無 Backend)

**範例 2: 電商平台 (Web App)**
- 情境判斷: ✅ 情境 A (Backend API)
- 必須產出:
  - [x] SRD
  - [x] ADR
  - [x] Database Schema (PostgreSQL)
  - [x] API Specification
  - [x] Security Design Document
- 不需要產出:
  - [❌] Data Access Layer (前端使用 API Client)

**範例 3: 筆記 App (本地 + 雲端同步)**
- 情境判斷: ✅ 情境 C (混合架構)
- 必須產出:
  - [x] SRD
  - [x] ADR
  - [x] Database Schema (本地 SQLite + 雲端 PostgreSQL)
  - [x] Data Access Layer Design
  - [x] Sync API Specification
  - [x] Data Sync Strategy Document
  - [x] Security Design Document

---

### 階段 6：User Story 撰寫 (3-4 小時)

> 💡 **與階段 4 的關係** 🆕
>
> 本階段基於 **階段 4 已確認的 PRD/FRD** + **階段 5 已完成的 SRD/API 設計**，
> 進行完整的 User Story 拆分和估算。階段 4 的初步 Epic 和高層 Story 為本階段的輸入，
> 但本階段需結合技術架構進行更精確的拆分（含 Story Points、技術依賴、API 對應）。

> 🤖 **Agent 參與角色** - 多 Agent 協作階段
>
> **活躍 Agents**: PM/PO (Victoria), SA (Amanda), SD-Architect (Marcus), Dev (David)
>
> **協作模式**:
> - **PM/PO (Victoria)**: Story 優先級排序、業務價值評估
> - **SA (Amanda)**: User Story 撰寫主導、需求轉換
> - **SD-Architect (Marcus)**: API 架構設計、資料流程定義
> - **Dev (David)**: API 技術實作規劃、工時估算
>
> **主要產出**: User Stories (EPIC → US → AC)、前後端互動流程、API Specifications

#### 步驟 6.1：觸發 User Story 生成

> 🔧 **建議 Skill**: `/sa-analyst`（User Story 撰寫）、`/sprint-planning`（Sprint 規劃）
> - 🆕 若專案涉及行動端（Android/iOS/macOS），額外使用 `/mobile-development`
>
> **`/mobile-development` 行動端 User Story 差異說明**：
>
> | AC 類型 | Web 撰寫方式 | Mobile 撰寫方式差異 |
> |---------|-------------|-----------------|
> | **裝置權限** | 不適用 | 需明確寫出：`AC: App 首次啟動時請求相機/位置/通知權限，使用者拒絕時顯示引導訊息` |
> | **離線操作** | 不適用 | 需明確寫出：`AC: 無網路時操作暫存至本地，網路恢復後自動同步（顯示同步進度）` |
> | **推播通知** | 不適用 | 需明確寫出：`AC: 訂單狀態變更時傳送 FCM 推播，使用者點擊後跳至訂單詳情頁` |
> | **效能測試** | 瀏覽器測試 | 需標注：`AT: 此 Story 需裝置實機測試，模擬器無法完整驗證（相機/藍牙/掃碼）` |
> | **深層連結** | URL 導航 | 需明確：`AC: 點擊推播通知可直接開啟 App 並跳至對應頁面（Deep Link）` |

```
執行指令：
「請將需求轉換為 User Stories 和 Acceptance Criteria」
```

> 📋 **使用工具**: [User_Story_Template.md](../../docs_template/core/prd/User_Story_Template.md)

#### 步驟 6.2：Story 生成過程

**6.2.1 Epic 識別與定義** (SA Agent)

> 💡 **什麼是 Epic？**
>
> Epic 是一個大型的使用者故事，通常無法在單一 Sprint 內完成，需要拆分成多個 User Stories。
> - **典型大小**: 3-6 個 Sprint（6-12 週）
> - **Story Points**: 通常 > 13 SP（超過 Fibonacci 估算上限）
> - **業務價值**: 代表一個完整的業務能力或使用者旅程

**Epic 識別標準**:

```yaml
Epic 特徵:
  ✅ 具備獨立的業務價值
  ✅ 可以獨立交付給使用者（即使功能不完整）
  ✅ 代表完整的使用者旅程或業務能力
  ✅ 太大無法在 1-2 個 Sprint 完成

Epic 範例:
  - EPIC-001: 使用者註冊與登入系統
  - EPIC-002: 商品瀏覽與搜尋功能
  - EPIC-003: 購物車與結帳流程
  - EPIC-004: 訂單管理與追蹤
```

**Epic 命名格式**:
- **格式**: `EPIC-XXX: [業務能力簡述]`
- **範例**: `EPIC-001: 使用者帳號管理系統`

> 📋 **ID 命名規範**: [AISDLC_ID_Naming_Convention.md](../../guides/system/naming/AISDLC_ID_Naming_Convention.md)

🆕 **多領域系統 Epic 拆分指引**（適用於融合多產業的系統）:

> **原則**: 優先按「領域」拆分 Epic，而非按「技術層」拆分。
>
> **共用 vs 領域專屬 Epic 分離規則**:
>
> | Epic 類型 | 定義 | 範例 | 優先級 |
> |----------|------|------|--------|
> | **共用基礎 Epic** | 所有領域共用的基礎功能 | EPIC-SHARED-001: 使用者認證與授權、EPIC-SHARED-002: 通知系統 | 🔴 最高（其他領域依賴此基礎） |
> | **領域核心 Epic** | 各領域獨立的核心業務 | EPIC-SHOP-001: 商品管理、EPIC-STAY-001: 房源管理 | 🟡 高（按業務價值排序） |
> | **跨域整合 Epic** | 涉及兩個以上領域交互 | EPIC-CROSS-001: 統一搜尋（跨商品+房源+文章+知識） | 🟢 中（依賴各領域核心完成） |
>
> **Epic 命名規範（多領域）**:
> - 共用: `EPIC-SHARED-XXX`
> - 電商: `EPIC-SHOP-XXX`
> - 民宿: `EPIC-STAY-XXX`
> - CMS: `EPIC-CMS-XXX`
> - KMS: `EPIC-KMS-XXX`
> - 進銷存: `EPIC-INV-XXX`
> - 跨域: `EPIC-CROSS-XXX`
>
> **依賴排序原則**: 共用基礎 → 領域核心（並行） → 跨域整合

---

**6.2.2 Epic 拆解標準** 🔴 **v0.01 新增**

> **⚠️ 為什麼需要明確的 Epic 拆解標準？**
>
> 常見問題：
> - Epic 拆解過大 → Sprint 無法完成，延遲交付
> - Epic 拆解過小 → 過多協調成本，管理負擔重
> - Epic 拆解不當 → 無法獨立測試驗證，阻塞依賴多
>
> 明確的拆解標準可以確保：
> - ✅ User Story 大小適中（1-3 天完成）
> - ✅ 每個 Story 可獨立測試驗證
> - ✅ 減少 Sprint 間依賴阻塞

**核心拆解原則**:

**原則 1：垂直切分 (Vertical Slicing)** 🔴

**定義**: 每個 User Story 應該涵蓋「前端 → 後端 → 資料庫」的完整技術棧，而非按技術層切分。

**為什麼垂直切分？**
- ✅ 每個 Story 可獨立部署和測試
- ✅ 減少團隊間等待和依賴
- ✅ 每個 Sprint 都有可展示的完整功能
- ✅ 提早發現整合問題

**對比範例**:

```markdown
❌ 錯誤拆分（水平切分 - Horizontal Slicing）:
  US-001: 設計使用者登入 UI
  US-002: 實作使用者登入 API
  US-003: 建立使用者資料表

  問題：
  - US-001 完成後無法測試（沒有後端）
  - US-002 完成後無法測試（沒有資料庫）
  - 需要等所有 3 個 Story 完成才能測試完整功能
  - 跨 Story 依賴強，容易阻塞

✅ 正確拆分（垂直切分 - Vertical Slicing）:
  US-001: 使用者帳號密碼登入功能
    - 前端登入表單（含基本驗證）
    - 後端登入 API（含 JWT 生成）
    - 資料庫使用者表查詢
    - 完整端到端測試

  US-002: 使用者 Google OAuth 登入功能
    - 前端 Google 登入按鈕
    - 後端 Google OAuth 驗證
    - 資料庫使用者關聯處理
    - 完整端到端測試

  優點：
  - 每個 Story 完成後可立即測試驗證
  - 無跨 Story 依賴
  - Sprint 結束可展示完整功能
```

**垂直切分技巧**:

| 切分維度 | 說明 | 範例 |
|---------|------|------|
| **按使用者角色** | 不同角色的相同功能分開 | US-001: 一般使用者登入<br>US-002: 管理員登入 |
| **按操作類型** | CRUD 操作分開 | US-003: 新增商品<br>US-004: 編輯商品<br>US-005: 刪除商品 |
| **按資料類型** | 不同資料對象分開 | US-006: 文字貼文發布<br>US-007: 圖片貼文發布<br>US-008: 影片貼文發布 |
| **按業務流程** | 流程步驟分開 | US-009: 基本個人資料設定<br>US-010: 進階偏好設定<br>US-011: 隱私權限設定 |
| **按功能複雜度** | 簡單版本優先，進階功能後續 | US-012: 基本搜尋（關鍵字匹配）<br>US-013: 進階搜尋（多條件篩選） |
| 🆕 **按業務領域** | 多領域系統按領域切分同一功能 | US-014: 電商訂單查詢<br>US-015: 民宿訂房查詢<br>US-016: 統一訂單報表（跨領域彙總） |

---

**原則 2：獨立價值 (Independent Value)** 🔴

**定義**: 每個 User Story 應該為使用者提供獨立的價值，即使其他 Story 未完成也能使用。

**獨立價值檢查清單**:

```markdown
檢查問題：
  ☑ 這個 Story 完成後，使用者能做什麼？
  ☑ 不依賴其他 Story，這個 Story 是否仍有意義？
  ☑ 產品負責人可以單獨展示這個 Story 嗎？
  ☑ 這個 Story 可以單獨部署到生產環境嗎？

若答案都是「是」，則符合獨立價值原則。
```

**範例對比**:

```markdown
❌ 無獨立價值:
  US-015: 建立購物車資料結構
  US-016: 實作加入購物車邏輯
  US-017: 顯示購物車內容

  問題：
  - US-015 完成後使用者看不到任何變化
  - US-016 完成後使用者仍無法看到購物車
  - 必須等 US-017 完成才有價值

✅ 有獨立價值:
  US-015: 使用者可以將商品加入購物車並查看
    - 加入購物車按鈕
    - 購物車圖示顯示數量
    - 點擊圖示查看購物車清單
    - 可以移除購物車商品

  US-016: 使用者可以在購物車中修改商品數量
    - 數量增減按鈕
    - 即時更新小計金額

  優點：
  - US-015 完成後立即可用
  - US-016 是增強功能，不影響 US-015 的價值
```

---

**原則 3：INVEST 原則檢查** 🔴

**INVEST 是優秀 User Story 的黃金標準**:

| 字母 | 原則 | 說明 | 檢查方法 |
|-----|------|------|---------|
| **I** | **Independent** (獨立的) | Story 之間盡量減少依賴 | 能否單獨開發、測試、部署？ |
| **N** | **Negotiable** (可協商的) | 細節可在開發過程中調整 | 是否只描述「做什麼」而非「怎麼做」？ |
| **V** | **Valuable** (有價值的) | 對使用者或業務有明確價值 | 使用者能從中獲得什麼？ |
| **E** | **Estimable** (可估算的) | 團隊能夠估算工作量 | 需求是否清晰到可以估算時間？ |
| **S** | **Small** (小的) | 適合在 1 個 Sprint 內完成 | 是否可在 1-3 天內完成？ |
| **T** | **Testable** (可測試的) | 有明確的驗收標準 | 能否寫出清晰的測試案例？ |

**INVEST 檢查範例**:

```markdown
User Story: 使用者可以使用信用卡付款

INVEST 檢查:
  ✅ I - Independent: 不依賴其他付款方式的實作
  ✅ N - Negotiable: 可討論是否包含分期付款功能
  ✅ V - Valuable: 使用者可以完成購買，商家可以收款
  ✅ E - Estimable: 團隊可估算為 5 Story Points
  ✅ S - Small: 預估 2-3 天完成
  ✅ T - Testable: AC-001-1: 使用有效卡號可成功扣款
                  AC-001-2: 使用無效卡號顯示錯誤訊息

結論：符合 INVEST 原則 ✅
```

**不符合 INVEST 的常見問題**:

| 問題 | 違反原則 | 解決方法 |
|------|---------|---------|
| Story 太大（> 5 天） | **S** (Small) | 拆分成多個更小的 Story |
| Story 描述實作細節 | **N** (Negotiable) | 改為描述使用者需求，不描述技術實作 |
| Story 沒有驗收條件 | **T** (Testable) | 補充清晰的 Acceptance Criteria |
| Story 依賴其他 Story 完成 | **I** (Independent) | 重新切分，確保可獨立完成 |
| Story 沒有業務價值 | **V** (Valuable) | 合併到其他 Story 或刪除 |

---

**6.2.3 Epic 拆解流程** 🔴

**4 步驟拆解法**:

```markdown
步驟 1: 識別使用者旅程 (User Journey)
  - 列出完整的使用者操作流程
  - 範例（電商結帳）:
    1. 查看購物車
    2. 填寫配送地址
    3. 選擇配送方式
    4. 選擇付款方式
    5. 確認訂單
    6. 完成付款
    7. 查看訂單確認

步驟 2: 按旅程步驟垂直切分
  - 每個步驟作為獨立 Story
  - US-020: 使用者可以查看購物車並修改數量
  - US-021: 使用者可以填寫配送地址（含驗證）
  - US-022: 使用者可以選擇配送方式（標準/快速）
  - US-023: 使用者可以選擇付款方式（信用卡）
  - US-024: 使用者可以確認訂單並提交
  - US-025: 使用者可以完成付款並收到確認
  - US-026: 使用者可以查看訂單詳情

步驟 3: INVEST 原則檢查
  - 逐一檢查每個 Story 是否符合 INVEST 原則
  - 若不符合，進一步拆分或調整

步驟 4: 優先級排序（參考 RICE 評分）
  - 按業務價值和依賴關係排序
  - 標記 MVP 範圍內的 Story
```

**拆解大小指南**:

| Story 大小 | Story Points | 工時估算 | 適用性 | 處理建議 |
|-----------|-------------|---------|--------|---------|
| **極小** | 1-2 SP | < 1 天 | ⚠️ 可能太小 | 考慮合併相關 Story |
| **小** | 3 SP | 1 天 | ✅ 理想大小 | 保持 |
| **中** | 5 SP | 2-3 天 | ✅ 可接受 | 保持或稍微拆分 |
| **大** | 8 SP | 4-5 天 | ⚠️ 偏大 | 建議拆分 |
| **極大** | 13+ SP | > 1 週 | ❌ 必須拆分 | 重新拆解 |

> 📋 **參考工具**: [Estimation_Standards.md](../../guides/system/planning/Estimation_Standards.md)

---

**6.2.4 Epic 拆解範例** 🔴

**完整範例：電商平台「商品搜尋功能」**

```markdown
EPIC-002: 商品搜尋與篩選系統

Epic 描述:
  使用者可以透過關鍵字搜尋商品，並使用多種條件篩選結果，
  快速找到想要的商品。

Epic 大小: 21 Story Points (預估)

拆解後的 User Stories:

📋 US-010: 基本關鍵字搜尋 (5 SP) [MVP]
  描述: 使用者可以輸入關鍵字搜尋商品
  AC-010-1: 輸入商品名稱關鍵字，顯示匹配結果
  AC-010-2: 搜尋結果包含商品圖片、名稱、價格
  AC-010-3: 沒有結果時顯示友善提示訊息
  垂直切分: ✅ 前端搜尋框 + 後端搜尋 API + DB 查詢
  獨立價值: ✅ 使用者可以立即搜尋商品
  INVEST: ✅ 全部符合

📋 US-011: 搜尋結果排序 (3 SP) [MVP]
  描述: 使用者可以對搜尋結果進行排序
  AC-011-1: 可選擇「價格由低到高」排序
  AC-011-2: 可選擇「價格由高到低」排序
  AC-011-3: 可選擇「最新上架」排序
  垂直切分: ✅ 前端排序選單 + 後端排序邏輯
  獨立價值: ✅ 增強搜尋體驗（不影響 US-010）
  INVEST: ✅ 全部符合

📋 US-012: 價格區間篩選 (3 SP)
  描述: 使用者可以設定價格區間篩選商品
  AC-012-1: 可輸入最低價格和最高價格
  AC-012-2: 篩選結果即時更新
  AC-012-3: 可清除價格篩選條件
  垂直切分: ✅ 前端價格輸入框 + 後端篩選邏輯
  獨立價值: ✅ 幫助使用者縮小搜尋範圍
  INVEST: ✅ 全部符合

📋 US-013: 商品類別篩選 (3 SP)
  描述: 使用者可以按商品類別篩選搜尋結果
  AC-013-1: 顯示所有可用類別（含商品數量）
  AC-013-2: 可選擇多個類別同時篩選
  AC-013-3: 可清除類別篩選條件
  垂直切分: ✅ 前端類別選單 + 後端類別篩選
  獨立價值: ✅ 幫助使用者精準搜尋
  INVEST: ✅ 全部符合

📋 US-014: 搜尋歷史記錄 (5 SP) [Post-MVP]
  描述: 使用者可以查看最近的搜尋記錄
  AC-014-1: 顯示最近 10 筆搜尋關鍵字
  AC-014-2: 點擊歷史記錄快速搜尋
  AC-014-3: 可清除搜尋歷史
  垂直切分: ✅ 前端歷史清單 + LocalStorage 儲存
  獨立價值: ✅ 提升使用便利性
  INVEST: ✅ 全部符合

📋 US-015: 熱門搜尋推薦 (2 SP) [Post-MVP]
  描述: 搜尋框顯示熱門搜尋關鍵字
  AC-015-1: 顯示前 5 個熱門搜尋關鍵字
  AC-015-2: 點擊熱門關鍵字快速搜尋
  垂直切分: ✅ 前端推薦顯示 + 後端統計 API
  獨立價值: ✅ 幫助使用者發現熱門商品
  INVEST: ✅ 全部符合

拆解檢查:
  ✅ 垂直切分: 每個 Story 都是端到端完整功能
  ✅ 獨立價值: 每個 Story 都可獨立交付
  ✅ INVEST 原則: 全部 Story 符合 INVEST
  ✅ 大小適中: 2-5 SP（1-3 天完成）
  ✅ MVP 識別: US-010, US-011 為 MVP 核心功能

優先級排序 (RICE):
  1. US-010 (RICE: 85) - 最高優先級
  2. US-011 (RICE: 60)
  3. US-012 (RICE: 45)
  4. US-013 (RICE: 45)
  5. US-014 (RICE: 20)
  6. US-015 (RICE: 15)
```

🆕 **業務流程型 Epic 拆解範例：含審核節點的進貨驗收流程**

> 💡 **適用場景**: 當 Epic 涉及多步驟業務流程（含審核、簽核、狀態流轉）時，
> 不能只按功能拆分，需要按「流程節點」垂直切分，確保每個 Story 涵蓋完整的狀態轉換。

```markdown
EPIC-005: 進貨驗收與入庫流程

Epic 描述:
  採購人員建立進貨單後，倉管人員掃碼驗收實際到貨數量，
  主管審核驗收結果，審核通過後自動入庫更新庫存。
  驗收異常需走退貨/補貨流程。

Epic 大小: 34 Story Points (預估)

業務流程圖:
  建立進貨單 → 到貨通知 → 掃碼驗收 → 主管審核 → 入庫/退貨

拆解後的 User Stories（按流程節點垂直切分）:

📋 US-050: 建立進貨單 (5 SP) [MVP]
  描述: 採購人員可建立進貨單，選擇供應商和商品
  AC-050-1: Given 採購人員登入, When 建立進貨單, Then 可選擇供應商並新增商品明細
  AC-050-2: Given 進貨單已建立, When 提交, Then 狀態變更為「待到貨」
  AC-050-3: Given 進貨單已提交, When 供應商確認, Then 發送到貨通知給倉管
  垂直切分: ✅ 前端表單 + 後端 API + DB 訂單表 + 通知推送
  狀態流轉: DRAFT → SUBMITTED → AWAITING_DELIVERY

📋 US-051: 掃碼驗收到貨 (8 SP) [MVP]
  描述: 倉管人員使用 Android 掃碼器逐項驗收到貨商品
  AC-051-1: Given 到貨通知已收到, When 開啟掃碼驗收, Then 顯示該進貨單的待驗收商品清單
  AC-051-2: Given 掃碼驗收中, When 掃描商品條碼, Then 自動匹配並填入實收數量（+1）
  AC-051-3: Given 驗收完成, When 實收數量 = 訂購數量, Then 標記為「驗收完成-數量正確」
  AC-051-4: Given 驗收完成, When 實收數量 ≠ 訂購數量, Then 標記為「驗收完成-數量異常」並記錄差異
  垂直切分: ✅ Android 掃碼 UI + 後端驗收 API + DB 驗收紀錄 + WebSocket 即時同步
  狀態流轉: AWAITING_DELIVERY → RECEIVING → RECEIVED_OK / RECEIVED_DISCREPANCY

📋 US-052: 主管審核驗收結果 (5 SP) [MVP]
  描述: 主管審核驗收結果，決定入庫、退貨或補貨
  AC-052-1: Given 驗收完成, When 主管開啟審核頁面, Then 顯示驗收明細與差異報告
  AC-052-2: Given 數量正確, When 主管點擊「審核通過」, Then 狀態變更為「待入庫」
  AC-052-3: Given 數量異常, When 主管點擊「部分入庫+退貨」, Then 生成退貨單 + 狀態為「部分入庫」
  AC-052-4: Given 審核中, When 主管點擊「退回重驗」, Then 狀態回到「待驗收」
  垂直切分: ✅ Web 審核頁面 + 後端審核 API + DB 狀態更新 + 通知推送
  狀態流轉: RECEIVED → APPROVED / PARTIAL_APPROVE / REJECTED

📋 US-053: 自動入庫與庫存更新 (5 SP) [MVP]
  描述: 審核通過後，系統自動更新庫存數量
  AC-053-1: Given 審核通過, When 系統處理入庫, Then 庫存數量增加（實收數量）
  AC-053-2: Given 入庫完成, When 查詢庫存, Then 庫存異動紀錄包含「進貨入庫」類型
  AC-053-3: Given 入庫完成, When 庫存低於安全庫存, Then 不再觸發補貨警示（已到貨）
  垂直切分: ✅ 庫存更新邏輯 + DB 異動紀錄 + WebSocket 庫存同步至所有平台
  狀態流轉: APPROVED → STOCKED

📋 US-054: 驗收異常處理（退貨/補貨）(8 SP)
  描述: 處理驗收數量異常的退貨或補貨流程
  AC-054-1: Given 部分入庫, When 產生退貨單, Then 退貨單關聯原進貨單
  AC-054-2: Given 退貨單已建立, When 供應商確認, Then 排定退貨物流
  AC-054-3: Given 需要補貨, When 產生補貨單, Then 自動帶入差額數量
  垂直切分: ✅ 退貨/補貨表單 + 後端退貨 API + DB 退貨表 + 供應商通知

📋 US-055: 進貨歷史查詢與報表 (3 SP)
  描述: 管理者可查詢進貨歷史並匯出報表
  AC-055-1: Given 管理者登入, When 查詢進貨紀錄, Then 支援日期、供應商、狀態篩選
  AC-055-2: Given 查詢結果, When 匯出 Excel, Then 包含完整驗收明細
  垂直切分: ✅ macOS 報表頁面 + 後端查詢/匯出 API + DB 查詢優化

拆解檢查:
  ✅ 流程節點覆蓋: 建立→驗收→審核→入庫→異常處理→報表
  ✅ 狀態流轉完整: 每個 Story 明確定義進入/離開狀態
  ✅ 審核節點獨立: 主管審核是獨立 Story，可配置審核規則
  ✅ 異常流程覆蓋: 退貨/補貨有獨立 Story 處理
  ✅ 多平台覆蓋: Web(管理)+Android(掃碼)+macOS(報表)
```

🆕 **日曆型業務 Epic 拆解範例：訂房與入住管理流程**

> 💡 **適用場景**: 當 Epic 涉及「時間維度庫存」（旅宿/租賃/預約）時，
> User Story 拆分需特別處理「日曆可用性查詢」、「跨日預訂原子性」、「入住退房狀態流轉」等特殊需求。

```markdown
EPIC-006: 訂房與入住管理系統

Epic 描述:
  旅客可透過網站搜尋可用房型與日期、完成線上訂房，
  入住當天進行 Check-in（支援線上自助或現場辦理），
  退房時自動結算附加費用並更新房態。
  業者可在後台管理房態、設定季節價格、處理取消與改期。

Epic 大小: 42 Story Points (預估)

業務流程圖:
  搜尋房型 → 選擇日期 → 確認訂房 → 付款 → 入住(Check-in) → 住房期間 → 退房(Check-out)

拆解後的 User Stories（按流程節點垂直切分）:

📋 US-060: 日曆可用性搜尋 (5 SP) [MVP]
  描述: 旅客可選擇入住/退房日期，查看該期間可用房型與價格
  AC-060-1: Given 旅客選擇日期區間, When 搜尋房型, Then 只顯示「每一天」都有空房的房型
  AC-060-2: Given 搜尋結果, When 顯示價格, Then 顯示入住期間每日價格明細與總價
  AC-060-3: Given 某房型部分日期已滿, When 搜尋, Then 該房型不出現（非顯示部分日期可用）
  垂直切分: ✅ 前端日曆選擇器 + 後端可用性查詢 API + DB resource_availability 查詢
  獨立價值: ✅ 旅客可立即搜尋可用房型
  INVEST: ✅ 全部符合

📋 US-061: 線上訂房 (8 SP) [MVP]
  描述: 旅客選擇房型後完成訂房，系統扣減日曆庫存
  AC-061-1: Given 旅客選擇房型, When 確認訂房, Then 入住期間每日 booked +1（原子操作）
  AC-061-2: Given 兩位旅客同時訂最後一間, When 並發提交, Then 只有一筆成功，另一筆提示「已被預訂」
  AC-061-3: Given 訂房成功, When 系統確認, Then 發送確認郵件含訂房編號與入住須知
  AC-061-4: Given 訂房未付款, When 超過 30 分鐘, Then 自動釋放庫存（booked -1）
  垂直切分: ✅ 前端訂房流程 + 後端訂房 API（含並發控制）+ DB 庫存扣減 + 郵件通知
  狀態流轉: PENDING → CONFIRMED → (AUTO_CANCELLED if unpaid)
  🔴 並發控制: 使用樂觀鎖或悲觀鎖（參考 Stage 5 時間維度庫存設計）

📋 US-062: 訂房取消與改期 (5 SP) [MVP]
  描述: 旅客或業者可取消訂房或修改入住日期
  AC-062-1: Given 入住日前 7 天取消, When 旅客取消, Then 全額退款 + 庫存釋放
  AC-062-2: Given 入住日前 3-7 天取消, When 旅客取消, Then 退 50% + 庫存釋放
  AC-062-3: Given 入住日前 3 天內取消, When 旅客取消, Then 不退款 + 庫存釋放
  AC-062-4: Given 旅客改期, When 新日期有空房, Then 釋放舊日期庫存 + 扣減新日期庫存
  垂直切分: ✅ 前端取消/改期 UI + 後端退款計算 API + DB 庫存回沖 + 金流退款
  狀態流轉: CONFIRMED → CANCELLED / MODIFIED

📋 US-063: 線上自助 Check-in (5 SP) [MVP]
  描述: 旅客可在入住當天透過手機完成線上 Check-in
  AC-063-1: Given 入住日當天, When 旅客開啟 Check-in, Then 顯示身分驗證與入住表單
  AC-063-2: Given Check-in 完成, When 系統確認, Then 發送房間號碼與門鎖密碼
  AC-063-3: Given 旅客未 Check-in, When 超過當日 22:00, Then 標記為 No-show
  垂直切分: ✅ 前端 Check-in 表單 + 後端入住 API + DB 狀態更新 + 智慧門鎖整合
  狀態流轉: CONFIRMED → CHECKED_IN / NO_SHOW

📋 US-064: Check-out 與費用結算 (5 SP) [MVP]
  描述: 旅客退房時自動結算額外費用（minibar、延遲退房等）
  AC-064-1: Given 退房日當天, When 旅客發起 Check-out, Then 顯示額外費用明細
  AC-064-2: Given 費用確認, When 旅客支付, Then 狀態變更為「已退房」
  AC-064-3: Given 退房完成, When 系統更新, Then 該房間狀態變為「待清潔」
  垂直切分: ✅ 前端結算頁面 + 後端結算 API + DB 房態更新 + 清潔排程通知
  狀態流轉: CHECKED_IN → CHECKED_OUT → CLEANING → AVAILABLE

📋 US-065: 後台房態管理與季節定價 (8 SP) [MVP]
  描述: 業者可在後台管理房態、批量設定季節價格
  AC-065-1: Given 業者登入後台, When 查看房態日曆, Then 以日曆視圖顯示每日每房型的狀態（可售/已訂/維護/清潔）
  AC-065-2: Given 業者選擇日期範圍, When 設定定價規則, Then 該期間價格自動更新
  AC-065-3: Given 業者標記房間維護, When 設定封鎖日期, Then 該期間 blocked +1, available 自動減少
  垂直切分: ✅ Web 後台日曆管理 + 後端房態/定價 API + DB pricing_rule + resource_availability
  獨立價值: ✅ 業者可即時管理房態與價格

📋 US-066: OTA 渠道庫存同步 (6 SP) [Post-MVP]
  描述: 系統庫存與 OTA 平台（Booking.com/Airbnb）雙向同步
  AC-066-1: Given 直客訂房, When 庫存變更, Then 即時同步至已連接的 OTA 渠道
  AC-066-2: Given OTA 平台訂房, When 收到 Webhook, Then 扣減本地庫存
  AC-066-3: Given 同步失敗, When 重試 3 次仍失敗, Then 發送告警通知業者手動處理

拆解檢查:
  ✅ 流程節點覆蓋: 搜尋→訂房→取消改期→Check-in→Check-out→後台管理→OTA同步
  ✅ 狀態流轉完整: PENDING→CONFIRMED→CHECKED_IN→CHECKED_OUT→CLEANING→AVAILABLE
  ✅ 日曆庫存特殊處理: US-060(跨日可用性查詢), US-061(並發控制), US-062(庫存回沖)
  ✅ 取消政策覆蓋: 階梯式取消扣款（7天/3-7天/3天內）
  ✅ 跨領域注意: 若與電商共用會員系統，US-061 訂房需引用共用會員 ID
```

🆕 **編輯型工作流 Epic 拆解範例：內容審核與發布流程**

> 💡 **適用場景**: 當 Epic 涉及「多層審核工作流」（內容管理/出版/知識庫/審批系統）時，
> User Story 拆分需按「流程節點」垂直切分，並特別處理「審核駁回迴圈」、「條件分支」、「狀態流轉」等特殊需求。

```markdown
EPIC-007: 內容審核與發布管理

📋 業務流程概述:
  撰寫內容 → 提交審核 → 主編審核（通過/駁回）→ [駁回]編輯修改 → 重新提交
  → [通過]內容主管最終審核 → 排程發布/即時發布 → 多渠道同步 → 歸檔

📋 狀態機定義:
  DRAFT → SUBMITTED → EDITOR_REVIEW → REJECTED → DRAFT (修改後重新提交)
  EDITOR_REVIEW → DIRECTOR_REVIEW → APPROVED → SCHEDULED → PUBLISHED → ARCHIVED
  任何狀態 → WITHDRAWN (作者主動撤回)

📋 拆解後 User Stories:

US-070: 編輯建立與編輯內容草稿
  AC-070-1: 編輯可建立新文章，填寫標題、正文（富文本）、分類、標籤
  AC-070-2: 系統每 30 秒自動保存草稿，保留最近 50 個版本
  AC-070-3: 編輯可預覽文章在各渠道的呈現效果
  對應 API: POST /api/v1/content/articles, PUT /api/v1/content/articles/{id}

US-071: 編輯提交內容至審核
  AC-071-1: 編輯點擊「提交審核」，狀態從 DRAFT → SUBMITTED
  AC-071-2: 系統驗證必填欄位（標題、正文、分類），缺欄位時阻擋提交
  AC-071-3: 提交成功後通知主編（站內通知 + Email）
  對應 API: POST /api/v1/content/articles/{id}/submit

US-072: 主編審核與評論
  AC-072-1: 主編可查看待審核文章列表（按提交時間排序）
  AC-072-2: 主編可在文章段落上添加行內評論
  AC-072-3: 主編選擇「通過」（→ DIRECTOR_REVIEW）或「駁回」（→ REJECTED）
  AC-072-4: 駁回時必須填寫駁回原因
  對應 API: POST /api/v1/content/articles/{id}/review, POST /api/v1/content/articles/{id}/comments

US-073: 編輯根據審核意見修改
  AC-073-1: 編輯收到駁回通知，可查看審核意見
  AC-073-2: 編輯修改後可標記評論為「已解決」
  AC-073-3: 修改完成後重新提交審核（REJECTED → SUBMITTED）
  對應 API: PUT /api/v1/content/articles/{id}, PATCH /api/v1/content/comments/{id}/resolve

US-074: 內容主管最終審核與發布決策
  AC-074-1: 內容主管可查看通過主編審核的文章
  AC-074-2: 主管選擇「即時發布」或「排程發布」（設定發布時間）
  AC-074-3: 排程發布時，系統在指定時間自動將狀態從 SCHEDULED → PUBLISHED
  AC-074-4: 發布後自動觸發多渠道同步（Web/App/Email Newsletter）
  對應 API: POST /api/v1/content/articles/{id}/approve, POST /api/v1/content/articles/{id}/schedule

US-075: 內容歸檔與版本管理
  AC-075-1: 已發布文章超過保留期限後，系統建議歸檔
  AC-075-2: 歸檔文章保留所有版本歷史，可隨時恢復
  AC-075-3: 歸檔不影響已分享的外部連結（返回「內容已歸檔」提示）
  對應 API: POST /api/v1/content/articles/{id}/archive

📋 評論子系統資料模型（IMP-22 合併）:

  ContentComment:
    - id: UUID
    - article_id: FK → Article
    - article_version: INTEGER (綁定特定版本)
    - author_id: FK → User (審核人)
    - parent_id: FK → ContentComment (回覆線程)
    - content: TEXT
    - paragraph_ref: VARCHAR (段落定位，如 "p3" / "h2-1")
    - status: ENUM(OPEN, RESOLVED, WONT_FIX)
    - created_at, updated_at: TIMESTAMP

📋 Sprint 拆分建議:
  Sprint 1: US-070（草稿 CRUD）+ 基礎狀態機框架
  Sprint 2: US-071 + US-072（提交與審核流程）
  Sprint 3: US-073 + US-074（駁回修改 + 最終審核與發布）
  Sprint 4: US-075 + 評論子系統（歸檔 + 行內評論）
```

> 🔑 **狀態機設計要點**:
> - **狀態轉換必須原子性**: 使用資料庫交易確保狀態變更 + 通知 + 日誌三者一致
> - **審核駁回迴圈**: 設計「最大駁回次數」防止無限迴圈（建議 3-5 次）
> - **並行審核 vs 序列審核**: 根據業務需求決定（內容管理通常為序列，法規審批可能為並行）
> - **狀態回退限制**: 已發布內容不可直接回退至草稿，需走「下架→編輯→重新審核」流程
> - **審計追蹤**: 每次狀態變更記錄操作人、時間、原因，形成完整審計日誌

---

**6.2.5 常見拆解錯誤與修正** 🔴

| 錯誤類型 | 範例 | 問題 | 修正方法 |
|---------|------|------|---------|
| **技術層拆分** | US-001: 設計 UI<br>US-002: 開發 API<br>US-003: 建資料表 | 無法獨立測試驗證 | 垂直切分：<br>US-001: 使用者登入功能（含 UI/API/DB） |
| **過度拆分** | US-004: 新增按鈕<br>US-005: 按鈕樣式<br>US-006: 按鈕事件 | Story 太小，管理成本高 | 合併：<br>US-004: 使用者可以送出表單 |
| **過大 Story** | US-007: 完整電商平台 | 無法在 Sprint 完成 | 拆分為多個 Epic 和 Stories |
| **無獨立價值** | US-008: 建立資料庫連線 | 使用者看不到價值 | 合併到有價值的 Story 中 |
| **缺少 AC** | US-009: 優化效能 | 無法測試驗證 | 補充明確 AC：<br>AC-009-1: 頁面載入時間 < 2s |

---

**6.2.6 Acceptance Criteria 定義** (SA + QA Agent)

- **Given-When-Then 格式**: 使用標準 BDD 格式撰寫
- **明確的驗收條件**: 可量化、可測試的標準
- **Edge cases 考慮**: 邊界情況和異常處理

> 💡 **AC 撰寫標準**: 關於 Edge Cases 的處理方式（整合到 AC 或獨立區塊），請參考 [User_Story_Template.md - AC 撰寫標準指引](../../docs_template/core/prd/User_Story_Template.md#-ac-撰寫標準指引-edge-cases-處理方式)
> - **小型專案** (< 50 US): 建議使用選項 A（Edge Cases 整合到 AC 中）
> - **大型專案** (> 50 US): 建議使用選項 B（Edge Cases 獨立區塊）

**硬體整合功能的 AC 撰寫指引** 🆕

> 📋 **適用場景**: 條碼/QR Code 掃描、NFC 讀取、藍牙裝置、印表機整合等硬體相關功能

硬體整合功能的 AC 需額外考慮**裝置相容性、權限、離線模式、錯誤恢復**等因素：

| AC 類別 | 撰寫重點 | 範例 |
|---------|---------|------|
| **裝置權限** | 權限請求、拒絕處理 | Given 使用者拒絕相機權限，When 點擊掃描，Then 顯示權限引導提示 |
| **掃描成功** | 回應時間、格式支援 | Given 商品有條碼，When 掃描 EAN-13 條碼，Then 2 秒內識別並帶入商品資訊 |
| **掃描失敗** | 降級方案、手動輸入 | Given 條碼模糊無法辨識，When 掃描失敗 3 次，Then 自動切換為手動輸入模式 |
| **多格式支援** | 條碼類型覆蓋 | Given 系統支援掃描，When 掃描不同格式，Then 支援 EAN-13、Code 128、QR Code |
| **環境適應** | 光線、距離、角度 | Given 環境光線不足，When 掃描條碼，Then 自動開啟閃光燈輔助 |
| **離線模式** | 無網路時的行為 | Given 無網路連線，When 掃描條碼，Then 暫存掃描結果，連線後自動同步 |
| **硬體降級** | 裝置不支援時的替代方案 | Given 裝置無相機，When 開啟掃描功能，Then 僅顯示手動輸入介面 |

🆕 **連續掃描模式 AC 範例**（適用於批次入庫/出庫/盤點）:

> 💡 **適用場景**: 經銷存系統的掃碼入庫、掃碼出庫、庫存盤點等需要連續快速掃描的操作。
> 與「單次掃描」不同，連續掃描模式需考慮速度、重複偵測、計數、批次提交等因素。

| AC 編號 | 條件 (Given) | 動作 (When) | 預期結果 (Then) |
|---------|-------------|------------|----------------|
| AC-SCAN-C1 | 倉管開啟連續掃描模式 | 連續掃描多個商品條碼 | 每次掃描成功後自動聚焦等待下一次掃描（無需手動點擊） |
| AC-SCAN-C2 | 連續掃描中 | 掃描同一商品條碼 2 次 | 該商品數量 +1（累加），並顯示已掃描次數 |
| AC-SCAN-C3 | 連續掃描中 | 掃描不屬於當前進貨單的商品 | 發出警告音 + 顯示「此商品不在本次進貨單中」，不中斷掃描模式 |
| AC-SCAN-C4 | 已掃描 50 筆以上 | 查看掃描清單 | 顯示已掃描商品摘要（品名、已掃數量、預期數量、差異），支援搜尋篩選 |
| AC-SCAN-C5 | 完成所有掃描 | 點擊「提交驗收」 | 批次提交所有掃描結果，與進貨單明細比對，標示差異項 |
| AC-SCAN-C6 | 掃描過程中網路斷線 | 繼續掃描 | 掃描結果暫存本地，網路恢復後自動上傳同步 |
| AC-SCAN-C7 | 連續掃描超過 30 分鐘 | 自動儲存 | 每 5 分鐘自動暫存掃描進度，防止資料遺失 |

---

**6.2.7 Story Point 估算** (Team)

- **使用 Planning Poker 方法**: 團隊共同估算，避免錨定效應
- **參考估算標準**: 使用 Fibonacci 數列（1, 2, 3, 5, 8, 13）
- **歷史資料校準**: 參考過去類似 Story 的實際工時

> 📋 **參考工具**: [Estimation_Standards.md](../../guides/system/planning/Estimation_Standards.md) - 包含 Planning Poker 詳細流程和歷史對照機制

#### 步驟 6.3：User Story 確認點 🔴
系統會呈現：
1. 完整 User Story 清單（含 EPIC-XXX → US-XXX → AC-XXX-Y 追蹤鏈）
2. Story 優先級排序
3. Story Point 估算
4. **依賴關係圖** 🔴 **v0.01 新增詳細說明**

你需要確認 Stories 是否完整且可執行。

---

**6.3.1 依賴關係圖呈現方式** 🔴 **v0.01 新增**

> **💡 為什麼需要視覺化依賴關係圖？**
>
> 文字描述的依賴關係難以快速理解全貌，容易遺漏：
> - 複雜的多層依賴鏈（A → B → C → D）
> - 循環依賴（A → B → A，需要解開）
> - 阻塞路徑（Critical Path，影響交付時間）
> - 可平行執行的 Stories（無依賴，可同時開發）
>
> 使用 Mermaid 格式的依賴關係圖，可以：
> - ✅ 一目了然看清所有依賴關係
> - ✅ 識別關鍵路徑和阻塞點
> - ✅ 規劃合理的開發順序
> - ✅ 在 Markdown 中直接渲染（GitHub、GitLab、VS Code 都支援）

**Mermaid 依賴關係圖格式**：

**基礎格式（簡單依賴）**：

```mermaid
graph LR
    US-001[US-001: 使用者註冊] --> US-002[US-002: 使用者登入]
    US-002 --> US-003[US-003: 編輯個人資料]
```

**完整格式（含顏色標記和優先級）**：

```mermaid
graph TD
    %% 定義樣式
    classDef mvp fill:#90EE90,stroke:#228B22,stroke-width:2px,color:#000
    classDef high fill:#FFD700,stroke:#FF8C00,stroke-width:2px,color:#000
    classDef medium fill:#87CEEB,stroke:#4682B4,stroke-width:2px,color:#000
    classDef low fill:#D3D3D3,stroke:#808080,stroke-width:2px,color:#000
    classDef blocked fill:#FF6B6B,stroke:#C92A2A,stroke-width:3px,color:#fff

    %% MVP 核心功能 (綠色)
    US-001[US-001: 使用者註冊<br/>5 SP | P0]:::mvp
    US-002[US-002: 使用者登入<br/>5 SP | P0]:::mvp
    US-003[US-003: 快速記帳<br/>8 SP | P0]:::mvp

    %% 高優先級功能 (金色)
    US-004[US-004: 支出統計<br/>5 SP | P1]:::high
    US-005[US-005: 分類管理<br/>3 SP | P1]:::high

    %% 中優先級功能 (藍色)
    US-006[US-006: 預算設定<br/>8 SP | P2]:::medium
    US-007[US-007: 匯出報表<br/>3 SP | P2]:::medium

    %% 低優先級功能 (灰色)
    US-008[US-008: 主題切換<br/>2 SP | P3]:::low

    %% 依賴關係
    US-001 --> US-002
    US-002 --> US-003
    US-003 --> US-004
    US-005 --> US-003
    US-004 --> US-006
    US-004 --> US-007
```

**顏色標記說明**：

| 顏色 | 優先級 | 用途 | Mermaid Class |
|------|--------|------|---------------|
| 🟢 **綠色** | P0 (MVP) | MVP 核心功能，必須完成 | `:::mvp` |
| 🟡 **金色** | P1 (高優先級) | 重要功能，盡快完成 | `:::high` |
| 🔵 **藍色** | P2 (中優先級) | 增強功能，後續完成 | `:::medium` |
| ⚪ **灰色** | P3 (低優先級) | 次要功能，時間允許時完成 | `:::low` |
| 🔴 **紅色** | 阻塞 (Blocked) | 被依賴阻塞，無法開始 | `:::blocked` |

---

**完整範例：電商平台 User Story 依賴關係圖**

```mermaid
graph TD
    %% 樣式定義
    classDef mvp fill:#90EE90,stroke:#228B22,stroke-width:2px,color:#000
    classDef high fill:#FFD700,stroke:#FF8C00,stroke-width:2px,color:#000
    classDef medium fill:#87CEEB,stroke:#4682B4,stroke-width:2px,color:#000
    classDef low fill:#D3D3D3,stroke:#808080,stroke-width:2px,color:#000
    classDef blocked fill:#FF6B6B,stroke:#C92A2A,stroke-width:3px,color:#fff

    %% EPIC-001: 使用者帳號管理 (MVP)
    US-001[US-001: 使用者註冊<br/>5 SP | P0<br/>無依賴]:::mvp
    US-002[US-002: 使用者登入<br/>5 SP | P0<br/>依賴 US-001]:::mvp
    US-003[US-003: 編輯個人資料<br/>3 SP | P0<br/>依賴 US-002]:::mvp

    %% EPIC-002: 商品瀏覽與搜尋 (MVP)
    US-010[US-010: 商品列表顯示<br/>5 SP | P0<br/>無依賴]:::mvp
    US-011[US-011: 商品搜尋<br/>5 SP | P0<br/>無依賴]:::mvp
    US-012[US-012: 商品詳情頁<br/>5 SP | P0<br/>依賴 US-010]:::mvp

    %% EPIC-003: 購物車與結帳 (MVP)
    US-020[US-020: 加入購物車<br/>5 SP | P0<br/>依賴 US-002, US-012]:::mvp
    US-021[US-021: 查看購物車<br/>3 SP | P0<br/>依賴 US-020]:::mvp
    US-022[US-022: 修改購物車數量<br/>3 SP | P0<br/>依賴 US-021]:::mvp
    US-023[US-023: 結帳流程<br/>8 SP | P0<br/>依賴 US-022]:::mvp

    %% EPIC-004: 訂單管理 (高優先級)
    US-030[US-030: 訂單列表<br/>5 SP | P1<br/>依賴 US-023]:::high
    US-031[US-031: 訂單詳情<br/>3 SP | P1<br/>依賴 US-030]:::high
    US-032[US-032: 取消訂單<br/>5 SP | P1<br/>依賴 US-031]:::high

    %% EPIC-005: 進階功能 (中優先級)
    US-040[US-040: 商品收藏<br/>3 SP | P2<br/>依賴 US-002, US-012]:::medium
    US-041[US-041: 商品評價<br/>5 SP | P2<br/>依賴 US-031]:::medium
    US-042[US-042: 優惠券系統<br/>8 SP | P2<br/>依賴 US-023]:::medium

    %% EPIC-006: 次要功能 (低優先級)
    US-050[US-050: 主題切換<br/>2 SP | P3<br/>無依賴]:::low
    US-051[US-051: 多語系支援<br/>5 SP | P3<br/>無依賴]:::low

    %% 依賴關係連線
    US-001 --> US-002
    US-002 --> US-003
    US-002 --> US-020

    US-010 --> US-012
    US-012 --> US-020

    US-020 --> US-021
    US-021 --> US-022
    US-022 --> US-023

    US-023 --> US-030
    US-030 --> US-031
    US-031 --> US-032
    US-031 --> US-041

    US-002 --> US-040
    US-012 --> US-040
    US-023 --> US-042
```

**圖表解讀**：

1. **關鍵路徑 (Critical Path)**：
   ```
   US-001 → US-002 → US-020 → US-021 → US-022 → US-023 → US-030 → US-031
   總 Story Points: 5 + 5 + 5 + 3 + 3 + 8 + 5 + 3 = 37 SP
   ```
   這是最長的依賴鏈，決定了 MVP 的最短完成時間。

2. **可平行開發的 Stories**：
   - US-001, US-010, US-011, US-050, US-051 無依賴，可同時開始
   - US-003, US-040 都依賴 US-002，可在 US-002 完成後平行開發

3. **阻塞點識別**：
   - US-002 (使用者登入) 阻塞了 4 個 Story (US-003, US-020, US-040)
   - US-023 (結帳流程) 阻塞了 3 個 Story (US-030, US-042)
   - 這些 Stories 應優先完成，避免阻塞後續開發

---

**使用建議**：

**1. 繪製時機**：
- Sprint Planning 會議中，由 Scrum Master 或 Tech Lead 繪製
- 使用線上工具即時編輯：
  - [Mermaid Live Editor](https://mermaid.live/)
  - VS Code + Mermaid Extension
  - GitHub/GitLab Markdown (直接渲染)

**2. 更新頻率**：
- Sprint Planning 時初次繪製
- Sprint 進行中，若有新依賴或變更，即時更新
- 每日 Stand-up 時，檢視被阻塞的 Stories

**3. 複雜專案處理**：
- 若 Stories 超過 20 個，建議按 Epic 分別繪製
- 範例：
  ```markdown
  ## EPIC-001 依賴關係圖
  [Mermaid 圖表]

  ## EPIC-002 依賴關係圖
  [Mermaid 圖表]

  ## 跨 Epic 依賴關係圖
  [Mermaid 圖表 - 只顯示 Epic 之間的依賴]
  ```

**4. 工具推薦**：

| 工具 | 用途 | 優點 | 缺點 |
|------|------|------|------|
| **Mermaid** | Markdown 內嵌圖表 | 文字化、版本控制友善、自動渲染 | 複雜圖表排版較難控制 |
| **draw.io** | 手動繪製流程圖 | 自由度高、美觀 | 需手動維護、不易版本控制 |
| **Jira 內建** | 專案管理工具 | 與 Sprint 整合、自動更新 | 僅限 Jira 用戶 |
| **PlantUML** | 程式碼生成 UML | 強大、支援複雜圖表 | 語法較複雜 |

**推薦使用 Mermaid**，原因：
- ✅ Markdown 原生支援，文件和圖表合一
- ✅ GitHub/GitLab 自動渲染，無需匯出圖片
- ✅ 文字化格式，易於版本控制和 Code Review
- ✅ 學習成本低，語法簡單直觀

---

**Mermaid 語法快速參考**：

```markdown
基本節點：
  US-001[US-001: 標題]         # 矩形節點
  US-001(US-001: 標題)         # 圓角矩形
  US-001{{US-001: 標題}}       # 菱形（決策）
  US-001[(US-001: 標題)]       # 圓柱形（資料庫）

箭頭類型：
  A --> B                      # 實線箭頭
  A -.-> B                     # 虛線箭頭
  A ==> B                      # 粗箭頭（強依賴）
  A --文字--> B                # 帶標籤的箭頭

圖表方向：
  graph TD                     # Top Down（由上到下）
  graph LR                     # Left to Right（由左到右）
  graph BT                     # Bottom to Top
  graph RL                     # Right to Left

樣式定義：
  classDef className fill:#color,stroke:#color,color:#color
  US-001:::className           # 套用樣式到節點
```

**完整 Mermaid 範本（可直接複製使用）**：

```mermaid
graph TD
    %% 樣式定義
    classDef mvp fill:#90EE90,stroke:#228B22,stroke-width:2px,color:#000
    classDef high fill:#FFD700,stroke:#FF8C00,stroke-width:2px,color:#000
    classDef medium fill:#87CEEB,stroke:#4682B4,stroke-width:2px,color:#000
    classDef low fill:#D3D3D3,stroke:#808080,stroke-width:2px,color:#000
    classDef blocked fill:#FF6B6B,stroke:#C92A2A,stroke-width:3px,color:#fff

    %% 節點定義（根據實際 Stories 修改）
    US-001[US-001: Story 標題<br/>X SP | P0<br/>依賴說明]:::mvp
    US-002[US-002: Story 標題<br/>X SP | P1<br/>依賴說明]:::high

    %% 依賴關係連線
    US-001 --> US-002
```

---

**產出文件**：
- User Stories (完整清單，使用 User_Story_Template.md)
- Acceptance Criteria（使用 AC-XXX-Y 格式）
- **Story Dependencies (依賴關係文字描述)**
- **Dependency Graph (Mermaid 格式依賴關係圖)** 🔴 **v0.01 新增**
- Estimation (Story Points)

**檢查清單**：
- [ ] 所有 User Stories 都已識別依賴關係
- [ ] Mermaid 依賴關係圖已繪製並渲染成功
- [ ] 關鍵路徑 (Critical Path) 已識別
- [ ] 可平行開發的 Stories 已標記
- [ ] 阻塞點 (Blocking Stories) 已標記並優先排程

---

### 階段 7：Sprint 規劃 (2-3 小時)

> 🤖 **Agent 參與角色** - PM/PO + SA + SD + Dev 協作階段
>
> **活躍 Agents**: PM/PO (Victoria), SA (Amanda), SD-Architect (Marcus), Dev (David)
>
> **協作模式**:
> - **PM/PO (Victoria)**: Sprint 優先級決策、資源分配、時程規劃
> - **SA (Amanda)**: User Story 依賴分析、Sprint 範圍確認
> - **SD-Architect (Marcus)**: 技術依賴排序、架構風險識別
> - **Dev (David)**: 工時估算、任務分配、技術可行性確認
>
> **主要產出**: Sprint Plan、Story Points 估算、依賴關係圖

#### 步驟 7.1：觸發 Sprint 規劃
```
執行指令：
「請根據 User Stories 進行 Sprint 規劃」
```

#### 步驟 7.2：Sprint 劃分

> 💡 **Sprint 編號慣例說明**:
> - **前置準備階段** (Preparation Phase): 環境建置、技術 Spike（不編號為 Sprint 0，避免與業界慣例混淆）
> - **Sprint 1-N**: 正式開發階段（從 Sprint 1 開始）
> - **時間線範例**: Week 0-1 前置準備 → Week 2-3 Sprint 1 → Week 4-5 Sprint 2 → ...

**前置準備階段 (Preparation Phase)**
- 開發環境建置（IDE、SDK、工具安裝）
- CI/CD Pipeline 設定（自動化測試、部署流程）
- 專案架構搭建（基礎程式碼結構、資料夾規劃）
- 技術 Spike（技術驗證、POC 開發）
- 預估時間: 1-2 週

##### 🔴 前置準備階段時間估算依據 (v0.01 新增)

> **問題來源**: 改進計畫問題 #11 - 前置準備階段時間估算依據不足
>
> **為什麼需要詳細估算？**
> - ⚠️ 前置準備時間經常被低估，導致 Sprint 1 延遲開始
> - ⚠️ 不同專案類型和技術棧的準備時間差異極大
> - ⚠️ 缺乏明確依據，難以向 Stakeholder 說明時程

**估算方法: 活動分解法 (Activity-Based Estimation)**

將前置準備階段拆解為具體活動，逐項估算：

**📦 1. 開發環境建置 (Environment Setup)**

| 活動項目 | 簡單專案 | 中等專案 | 複雜專案 | 說明 |
|---------|---------|---------|---------|------|
| **IDE & 工具安裝** | 0.5 人日 | 1 人日 | 2 人日 | IDE、Git、Docker、資料庫工具等 |
| **SDK & 依賴套件** | 0.5 人日 | 1 人日 | 2 人日 | Node.js、Python、Java SDK 等 |
| **本地資料庫設定** | 0.5 人日 | 1 人日 | 1.5 人日 | PostgreSQL、MySQL、MongoDB 等 |
| **API 測試工具** | 0.25 人日 | 0.5 人日 | 1 人日 | Postman、Insomnia、curl 腳本 |
| **文檔與知識庫** | 0.25 人日 | 0.5 人日 | 1 人日 | Wiki、Notion、Confluence 設定 |
| **小計** | **2 人日** | **4 人日** | **7.5 人日** | |

**專案類型定義**:
- **簡單**: 單一技術棧 (如純前端 React SPA)
- **中等**: 前後端分離 (React + Node.js + PostgreSQL)
- **複雜**: 微服務架構 (多個後端服務 + Message Queue + Redis + K8s)

---

**🔧 2. CI/CD Pipeline 設定 (CI/CD Setup)**

| 活動項目 | 簡單專案 | 中等專案 | 複雜專案 | 說明 |
|---------|---------|---------|---------|------|
| **版本控制設定** | 0.25 人日 | 0.5 人日 | 1 人日 | GitHub/GitLab Repo、分支策略 |
| **CI Pipeline (Build & Test)** | 1 人日 | 2 人日 | 4 人日 | GitHub Actions、GitLab CI、Jenkins |
| **CD Pipeline (Deploy)** | 1 人日 | 3 人日 | 6 人日 | 自動部署腳本、環境配置 |
| **環境管理** | 0.5 人日 | 1.5 人日 | 3 人日 | Dev、Staging、Prod 環境設定 |
| **監控與日誌** | 0.25 人日 | 1 人日 | 2 人日 | Sentry、CloudWatch、ELK Stack |
| **小計** | **3 人日** | **8 人日** | **16 人日** | |

**調整因子**:
- **使用雲端平台 (AWS/GCP/Azure)**: +20% 時間 (學習曲線、權限設定)
- **使用 Kubernetes**: +50% 時間 (Helm Charts、Ingress、ConfigMap)
- **多租戶架構**: +30% 時間 (隔離性設定、安全配置)

---

**🏗️ 3. 專案架構搭建 (Project Scaffolding)**

| 活動項目 | 簡單專案 | 中等專案 | 複雜專案 | 說明 |
|---------|---------|---------|---------|------|
| **專案初始化** | 0.5 人日 | 1 人日 | 2 人日 | create-react-app、nestjs new、etc. |
| **資料夾結構規劃** | 0.5 人日 | 1 人日 | 2 人日 | 目錄結構、命名規範 |
| **基礎程式碼範本** | 1 人日 | 2 人日 | 4 人日 | Utils、Constants、Base Components |
| **路由與導航** | 0.5 人日 | 1 人日 | 2 人日 | React Router、Vue Router、等 |
| **狀態管理設定** | 0.5 人日 | 1.5 人日 | 3 人日 | Redux、Zustand、Pinia、等 |
| **API Client 設定** | 0.5 人日 | 1 人日 | 2 人日 | Axios、Fetch、Request Interceptors |
| **樣式系統設定** | 0.5 人日 | 1.5 人日 | 2 人日 | Tailwind、Styled-Components、SCSS |
| **小計** | **4 人日** | **9 人日** | **17 人日** | |

**技術棧影響**:
- **使用成熟腳手架** (Next.js、Nuxt.js): -30% 時間
- **從零搭建** (Custom Webpack Config): +50% 時間
- **微前端架構** (Module Federation): +100% 時間

---

**🔬 4. 技術 Spike (Technical Spike)**

| 活動項目 | 簡單專案 | 中等專案 | 複雜專案 | 說明 |
|---------|---------|---------|---------|------|
| **核心技術驗證** | 1 人日 | 2 人日 | 5 人日 | 驗證關鍵技術可行性 |
| **第三方整合 POC** | 0.5 人日 | 2 人日 | 4 人日 | 支付、地圖、簡訊服務整合測試 |
| **效能基準測試** | 0 人日 | 1 人日 | 2 人日 | 負載測試、回應時間測試 |
| **安全性評估** | 0 人日 | 0.5 人日 | 2 人日 | OWASP 檢查、漏洞掃描 |
| **小計** | **1.5 人日** | **5.5 人日** | **13 人日** | |

**Spike 決策原則**:
- **必須 Spike**: 使用未驗證的新技術、複雜的第三方整合
- **可選 Spike**: 技術棧成熟且團隊熟悉
- **範例**:
  - ✅ 必須: 首次使用 GraphQL、首次整合 Stripe 支付
  - ⚠️ 可選: 使用團隊熟悉的 React + Express 技術棧

---

**📊 總時間估算彙整**

| 專案類型 | 環境建置 | CI/CD | 架構搭建 | 技術 Spike | 總計 (人日) | 團隊規模 | 預估週數 |
|---------|---------|-------|---------|-----------|-----------|---------|---------|
| **簡單專案** | 2 | 3 | 4 | 1.5 | **10.5** | 2 人 | **1-1.5 週** |
| **中等專案** | 4 | 8 | 9 | 5.5 | **26.5** | 4 人 | **1.5-2 週** |
| **複雜專案** | 7.5 | 16 | 17 | 13 | **53.5** | 6 人 | **2-2.5 週** |

**週數計算公式**:
```
預估週數 = 總人日 / (團隊規模 × 每週工作日數 × 並行效率)

範例 (中等專案):
預估週數 = 26.5 人日 / (4 人 × 5 日/週 × 0.8 並行效率)
         = 26.5 / 16
         = 1.66 週
         ≈ 1.5-2 週
```

**並行效率說明**:
- **0.8 (80%)**: 團隊成員無法 100% 並行工作，需要溝通協調時間
- **常見干擾因子**:
  - 環境問題互相協助 (10%)
  - 技術選型討論會議 (5%)
  - 文檔撰寫與知識分享 (5%)

---

**⚠️ 調整因子總覽**

根據以下因素調整基準估算：

| 因素 | 影響 | 調整係數 | 範例 |
|------|------|---------|------|
| **團隊經驗** | 🔴 Critical | | |
| - 團隊熟悉技術棧 | 減少時間 | × 0.7 | 團隊有 3+ React 專案經驗 |
| - 團隊首次接觸技術棧 | 增加時間 | × 1.5 | 團隊首次使用 K8s |
| **基礎設施成熟度** | 🟠 High | | |
| - 公司有標準 DevOps 範本 | 減少時間 | × 0.6 | 公司有內部 Terraform 模組 |
| - 從零建置基礎設施 | 增加時間 | × 1.3 | 新創公司首個專案 |
| **第三方依賴數量** | 🟡 Medium | | |
| - 無第三方整合 | 減少時間 | × 0.9 | 純內部系統 |
| - 3+ 第三方服務整合 | 增加時間 | × 1.4 | 支付、簡訊、地圖、AI API |
| **合規要求** | 🟡 Medium | | |
| - 一般商業應用 | 無調整 | × 1.0 | 電商、CRM |
| - 高度合規要求 | 增加時間 | × 1.3 | 金融、醫療 (GDPR/HIPAA) |

**實際範例計算**:

```markdown
## 範例 1: 新創公司電商平台 (中等專案 + 多個調整因子)

**基準估算**: 26.5 人日 (中等專案)

**調整因子**:
- 團隊首次使用 Next.js: × 1.3 (學習曲線)
- 整合 Stripe + Twilio + Google Maps: × 1.2 (3 個第三方)
- 公司首個專案 (無 DevOps 範本): × 1.2 (基礎設施)

**調整後總計**:
26.5 × 1.3 × 1.2 × 1.2 = 49.6 人日

**團隊配置**: 4 人
**預估週數**: 49.6 / (4 × 5 × 0.8) = 3.1 週
**建議時程**: **3-3.5 週** (含 buffer)
```

```markdown
## 範例 2: 企業內部工具 (簡單專案 + 有利因子)

**基準估算**: 10.5 人日 (簡單專案)

**調整因子**:
- 團隊熟悉 React + Node.js: × 0.7 (經驗豐富)
- 公司有標準 AWS ECS 部署範本: × 0.6 (DevOps 成熟)
- 無第三方整合: × 0.9 (純內部系統)

**調整後總計**:
10.5 × 0.7 × 0.6 × 0.9 = 3.97 人日

**團隊配置**: 2 人
**預估週數**: 3.97 / (2 × 5 × 0.8) = 0.5 週
**建議時程**: **0.5-1 週** (含 buffer)
```

---

**✅ 估算檢查清單 (Estimation Checklist)**

在估算前置準備時間時，確認以下項目：

**環境與工具**:
- [ ] 確認開發環境需求 (IDE、SDK、資料庫)
- [ ] 確認 CI/CD 平台選擇 (GitHub Actions、GitLab CI、Jenkins)
- [ ] 確認雲端平台選擇 (AWS、GCP、Azure、Self-hosted)
- [ ] 確認監控工具選擇 (Sentry、Datadog、Prometheus)

**團隊經驗**:
- [ ] 評估團隊對技術棧的熟悉度 (1-5 分)
- [ ] 確認團隊是否有類似專案經驗
- [ ] 確認是否需要技術培訓或 Workshop

**基礎設施**:
- [ ] 確認是否有公司級 DevOps 範本可用
- [ ] 確認是否有內部基礎設施可重用 (VPC、K8s Cluster)
- [ ] 確認基礎設施權限申請時間 (可能需 1-2 週)

**第三方依賴**:
- [ ] 列出所有第三方服務 (支付、簡訊、地圖、AI)
- [ ] 確認第三方服務申請與審核時間
- [ ] 確認第三方服務 POC 測試需求

**風險與緩衝**:
- [ ] 識別高風險項目 (新技術、複雜整合)
- [ ] 為高風險項目增加 30-50% 緩衝時間
- [ ] 預留 10-20% 整體緩衝時間應對不可預見問題

---

**📚 參考文檔**:
- [Estimation_Standards.md](../../guides/system/planning/Estimation_Standards.md) - 估算標準與 Story Points 方法
- [Velocity 歷史數據收集指引](../../guides/system/planning/Estimation_Standards.md#15-velocity-歷史數據收集指引-v007-新增) - 團隊 Velocity 追蹤

---

**Sprint 1-N (開發階段)**
- MVP 核心功能優先
- 垂直切片 (end-to-end 功能)
- 依賴關係考量
- 風險平衡
- 每個 Sprint 時長: 2 週（建議）

🆕 **多領域系統 Sprint 優先排序指引**（適用於融合多產業的系統）:

> **跨領域 Sprint 排序原則**:
>
> ```
> Sprint 排序策略（多領域系統）:
>
> 前置準備階段: 共用基礎建設（認證授權、DB Schema、CI/CD）
>      ↓
> Sprint 1-2: 共用核心模組（User、Payment、Notification）
>      ↓
> Sprint 3-N: 各領域核心功能（可依業務價值並行）
>      ↓
> Sprint N+1: 跨域整合功能（統一搜尋、跨域報表）
>      ↓
> Sprint N+2: 跨域測試與效能優化
> ```
>
> **領域間並行開發判斷**:
> - ✅ 可並行：電商商品管理 ∥ 民宿房源管理（無直接依賴）
> - ✅ 可並行：CMS 文章編輯 ∥ KMS 知識編輯（獨立功能）
> - ❌ 不可並行：統一搜尋（依賴所有領域的資料模型完成）
> - ❌ 不可並行：跨域報表（依賴各領域的交易資料完成）
>
> **Sprint 分配建議**（2 人團隊）:
> - 每個 Sprint 最多處理 **2 個領域** 的功能
> - 優先完成高業務價值 + 低技術依賴的領域
> - 跨域整合功能放在各領域核心完成之後的 Sprint

#### 步驟 7.2.1：跨 Sprint 依賴管理 🔴 (Critical - v0.01 新增)

> **⚠️ 為什麼需要跨 Sprint 依賴管理？**
>
> 在多 Sprint 規劃中，常見以下問題：
> - Sprint 2 的 US-015 需要 Sprint 1 的 US-003 提供的 API
> - Sprint 3 的前端功能依賴 Sprint 2 的資料庫 Schema 變更
> - Sprint 4 的整合測試需要 Sprint 1-3 的所有功能完成
>
> 若未提前識別和管理這些依賴，將導致：
> - 🚨 Sprint 阻塞 (Blocked Sprint)
> - 🚨 技術債累積 (Technical Debt)
> - 🚨 交付延遲 (Delayed Delivery)

**步驟 7.2.1.1: 依賴識別與分類**

**依賴類型定義**:

1. **技術依賴 (Technical Dependency)**
   - **定義**: 某個 User Story 需要另一個 Story 提供的技術組件（API、資料庫 Schema、SDK）
   - **範例**:
     - `US-015` (前端訂單列表) 依賴 `US-003` (後端訂單 API)
     - `US-022` (支付整合) 依賴 `US-010` (訂單資料表建立)
   - **識別方法**: 檢查 SRD 和 API Specification，找出跨 Sprint 的 API 呼叫

2. **資料依賴 (Data Dependency)**
   - **定義**: 某個功能需要特定資料結構或資料遷移完成
   - **範例**:
     - `US-030` (報表生成) 依賴 `US-012` (資料統計表建立)
     - `US-025` (使用者權限) 依賴 `US-005` (使用者資料表遷移)
   - **識別方法**: 檢查 Database Schema 和 Data Migration Plan

3. **業務依賴 (Business Dependency)**
   - **定義**: 某個功能必須在另一個功能之後才能實作（業務邏輯順序）
   - **範例**:
     - `US-020` (訂單退款) 依賴 `US-010` (訂單建立)
     - `US-035` (VIP 會員優惠) 依賴 `US-008` (會員系統)
   - **識別方法**: 檢查 PRD/FRD 的業務流程圖

4. **測試依賴 (Testing Dependency)**
   - **定義**: 整合測試需要多個功能模組完成
   - **範例**:
     - `US-040` (端到端測試) 依賴 Sprint 1-3 的所有核心功能
     - `US-033` (效能測試) 依賴 `US-015`, `US-020`, `US-025` 的完成
   - **識別方法**: 檢查 Test Plan 和 Acceptance Test 定義

5. 🆕 **環境依賴 (Environment Dependency)**
   - **定義**: 某個功能需要外部環境、帳號、憑證或第三方服務就緒
   - **範例**:
     - `US-045` (Android App 發布) 依賴 Google Play Developer 帳號（申請需 1-3 天）
     - `US-046` (macOS App 公證) 依賴 Apple Developer Program 會員資格（年費 $99）
     - `US-050` (電子發票整合) 依賴財政部電子發票 API 測試帳號（申請需 5-10 工作天）
     - `US-055` (SSL 憑證) 依賴 Domain 購買和 DNS 設定完成
     - `US-060` (簡訊通知) 依賴 Twilio/SMS 服務帳號開通
   - **識別方法**: 檢查 DevOps 部署清單和第三方服務整合清單
   - **⚠️ 特別注意**: 環境依賴通常需要**提前數天至數週**準備，建議在 Sprint 0（前置準備）階段即開始處理

6. 🆕 **跨領域依賴 (Cross-Domain Dependency)**
   - **定義**: 在多領域融合系統中，某個領域的功能依賴另一個領域的資料、服務或流程
   - **範例**:
     - `US-070` (電商會員積分折抵房費) 依賴電商領域的「積分系統」+ 民宿領域的「訂房系統」
     - `US-071` (住客導購推薦) 依賴民宿領域的「入住紀錄」+ 電商領域的「推薦引擎」
     - `US-072` (統一會員報表) 依賴兩個領域各自的「交易紀錄」彙總
   - **識別方法**: 檢查 Stage 1 識別的「領域融合類型」，列出跨領域資料流
   - **緩解策略**:
     - **介面隔離**: 透過明確定義的 API/事件介面連接領域，避免直接存取對方 DB
     - **契約先行**: 跨領域依賴的 API 契約在 Sprint 0 就定義好（OpenAPI Spec）
     - **Mock 服務**: 被依賴領域未完成時，使用 Mock 服務解耦開發
     - **優先排序**: 共用基礎設施（會員、支付）安排在早期 Sprint
   - **🔴 特別注意**: 跨領域依賴的風險通常高於同領域依賴，因為涉及不同的業務邏輯和資料模型，修改一側可能意外影響另一側

**步驟 7.2.1.2: 依賴追蹤矩陣 (Dependency Tracking Matrix)**

使用以下表格記錄所有跨 Sprint 依賴：

| 依賴 ID | User Story | Sprint | 依賴於 | 依賴 Sprint | 依賴類型 | 風險等級 | 緩解策略 | 負責人 |
|---------|-----------|--------|--------|------------|---------|---------|---------|-------|
| DEP-001 | US-015 (訂單列表) | Sprint 2 | US-003 (訂單 API) | Sprint 1 | 技術依賴 | 🔴 High | Mock API 優先開發 | David (Dev) |
| DEP-002 | US-022 (支付整合) | Sprint 3 | US-010 (訂單表) | Sprint 1 | 資料依賴 | 🟡 Medium | 預先定義 Schema | Marcus (SD) |
| DEP-003 | US-030 (報表) | Sprint 4 | US-012 (統計表) | Sprint 2 | 資料依賴 | 🟢 Low | 可並行開發 | David (Dev) |
| DEP-004 | US-040 (E2E Test) | Sprint 5 | US-015, US-020, US-025 | Sprint 2-4 | 測試依賴 | 🔴 High | 分階段測試計畫 | Quincy (QA) |

**風險等級定義**:
- 🔴 **High (高風險)**: 若依賴項延遲，將直接阻塞當前 Sprint
- 🟡 **Medium (中風險)**: 可透過 workaround 暫時繞過，但需最終解決
- 🟢 **Low (低風險)**: 可並行開發或延後處理

**步驟 7.2.1.3: 依賴風險評估與緩解策略**

**風險評估檢查清單**:

針對每個依賴項，回答以下問題：

1. **時間風險**
   - [ ] 依賴項是否在同一 Sprint 完成？
   - [ ] 若跨 Sprint，是否有足夠的 buffer time？
   - [ ] 依賴項是否有延遲風險（新技術、複雜度高）？

2. **技術風險**
   - [ ] 依賴項的 API/Schema 是否已明確定義？
   - [ ] 是否有技術不確定性（第三方服務、未驗證技術）？
   - [ ] 是否需要技術 Spike 驗證可行性？

3. **團隊風險**
   - [ ] 依賴項和當前 Story 是否由不同團隊開發？
   - [ ] 團隊間溝通機制是否建立？
   - [ ] 是否有跨團隊協調的負責人？

**常見緩解策略**:

| 依賴類型 | 緩解策略 | 實施方法 | 範例 |
|---------|---------|---------|------|
| **技術依賴** | **Mock API 優先開發** | 在依賴項完成前，使用 Mock API 進行前端開發 | 前端使用 JSON Server 模擬後端 API |
| **技術依賴** | **API Contract First** | 提前定義 API Spec，雙方同時開發 | 使用 OpenAPI 3.0 定義 API，前後端並行 |
| **資料依賴** | **Schema 預先定義** | Sprint 1 完成 Schema 設計，Sprint 2 使用 | 在 Sprint 1 完成所有資料表 DDL |
| **資料依賴** | **分階段遷移** | 將資料遷移拆分為多個階段，降低依賴 | Sprint 1 基礎表，Sprint 2 擴充欄位 |
| **業務依賴** | **垂直切片重排** | 調整 Sprint 順序，確保依賴項優先完成 | 將 US-010 從 Sprint 2 移至 Sprint 1 |
| **業務依賴** | **Feature Toggle** | 使用功能開關，允許部分功能延後啟用 | 支付功能先開發，Sprint 3 才啟用 |
| **測試依賴** | **分階段測試計畫** | 將整合測試拆分為多個階段，逐步驗證 | Sprint 2 測試訂單流程，Sprint 3 測試支付流程 |
| **測試依賴** | **Contract Testing** | 使用契約測試，提前驗證介面整合 | 使用 Pact 進行前後端契約測試 |

**步驟 7.2.1.4: 依賴溝通與協調機制**

**溝通機制**:

1. **每日同步會議 (Daily Sync)**
   - **時間**: 每日早上 10:00 (15 分鐘)
   - **參與者**: 涉及依賴關係的團隊成員
   - **議程**:
     - 依賴項進度更新
     - 阻塞問題回報
     - 緩解策略調整

2. **依賴追蹤看板 (Dependency Board)**
   - **工具**: Jira / Linear / Notion
   - **欄位**:
     - `Blocked` (等待依賴項)
     - `In Progress` (依賴項進行中)
     - `Ready` (依賴項已完成)
   - **更新頻率**: 每日更新

3. **依賴變更通知 (Change Notification)**
   - **觸發時機**: 依賴項的 API/Schema 變更時
   - **通知方式**: Slack / Teams 自動通知
   - **範例訊息**:
     ```
     ⚠️ API 變更通知
     - API: POST /api/orders
     - 變更: 新增 `deliveryDate` 欄位 (required)
     - 影響 User Story: US-015, US-022
     - 負責人: @David
     ```

4. **Sprint 邊界檢查 (Sprint Boundary Check)**
   - **時機**: 每個 Sprint 結束前 2 天
   - **目的**: 確認依賴項是否如期完成
   - **檢查清單**:
     - [ ] 所有依賴項的 API/Schema 是否已交付？
     - [ ] 下個 Sprint 是否有阻塞風險？
     - [ ] 是否需要調整下個 Sprint 的計畫？

**步驟 7.2.1.5: 依賴解決策略範例**

**範例 1: 技術依賴 - Mock API 優先開發**

**情境**:
- `US-015` (前端訂單列表) 在 Sprint 2
- `US-003` (後端訂單 API) 在 Sprint 1
- 若 Sprint 1 延遲，Sprint 2 將無法開始

**解決策略**:
1. **Sprint 1 Week 1**: 後端團隊完成 API Specification
2. **Sprint 1 Week 2**: 前端團隊使用 Mock API 開始開發
   ```javascript
   // Mock API (JSON Server)
   {
     "orders": [
       { "id": 1, "userId": 101, "total": 1200, "status": "completed" },
       { "id": 2, "userId": 102, "total": 800, "status": "pending" }
     ]
   }
   ```
3. **Sprint 2 Week 1**: 後端 API 完成後，前端切換到真實 API
4. **Sprint 2 Week 2**: 整合測試

**範例 2: 資料依賴 - Schema 預先定義**

**情境**:
- `US-022` (支付整合) 在 Sprint 3 需要訂單資料表
- `US-010` (訂單資料表建立) 在 Sprint 1

**解決策略**:
1. **Sprint 1 開始前**: 完成所有資料表的 Schema 設計 (DDL)
   ```sql
   -- Sprint 1: 建立基礎訂單表
   CREATE TABLE orders (
     id BIGINT PRIMARY KEY,
     user_id BIGINT NOT NULL,
     total DECIMAL(10, 2) NOT NULL,
     status VARCHAR(20) NOT NULL,
     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
   );

   -- Sprint 2: 擴充欄位 (預留)
   ALTER TABLE orders ADD COLUMN delivery_date DATE;

   -- Sprint 3: 支付相關欄位
   ALTER TABLE orders ADD COLUMN payment_method VARCHAR(50);
   ALTER TABLE orders ADD COLUMN payment_status VARCHAR(20);
   ```
2. **Sprint 1**: 執行基礎表建立
3. **Sprint 2-3**: 執行欄位擴充（使用 Migration Script）

**範例 3: 業務依賴 - 垂直切片重排**

**情境**:
- `US-020` (訂單退款) 依賴 `US-010` (訂單建立)
- 原計畫: `US-010` 在 Sprint 2, `US-020` 在 Sprint 3
- 問題: 若 Sprint 2 延遲，Sprint 3 無法進行

**解決策略**:
1. **重新排序**: 將 `US-010` 移至 Sprint 1 (高優先級)
2. **調整後計畫**:
   - Sprint 1: `US-010` (訂單建立)
   - Sprint 2: `US-015` (訂單列表)
   - Sprint 3: `US-020` (訂單退款)
3. **優點**: 降低依賴風險，確保核心功能優先完成

**步驟 7.2.1.6: 依賴管理檢查清單**

在完成 Sprint 規劃前，使用此檢查清單驗證依賴管理是否完整：

- [ ] **依賴識別完整性**
  - [ ] 所有跨 Sprint 的技術依賴已識別
  - [ ] 所有資料依賴已記錄在 Dependency Matrix
  - [ ] 所有業務依賴已確認（檢查 PRD/FRD）
  - [ ] 所有測試依賴已規劃

- [ ] **風險評估完整性**
  - [ ] 每個依賴項都有風險等級評估 (🔴/🟡/🟢)
  - [ ] 所有 🔴 High Risk 依賴都有緩解策略
  - [ ] 所有 🟡 Medium Risk 依賴都有 backup plan

- [ ] **緩解策略可行性**
  - [ ] Mock API 的 API Spec 已定義
  - [ ] Schema 預先定義已完成（所有資料表 DDL）
  - [ ] Feature Toggle 機制已設計
  - [ ] Contract Testing 工具已選定 (如需要)

- [ ] **溝通機制建立**
  - [ ] 依賴追蹤看板已建立 (Jira/Linear)
  - [ ] 每日同步會議時間已排定
  - [ ] 依賴變更通知機制已設定 (Slack/Teams)
  - [ ] Sprint 邊界檢查責任人已指派

- [ ] **文件記錄完整性**
  - [ ] Dependency Tracking Matrix 已建立
  - [ ] 每個依賴項都有負責人
  - [ ] 緩解策略已記錄在 Sprint Backlog
  - [ ] 依賴關係圖已繪製 (視覺化)

**產出文件**:
- **Dependency Tracking Matrix** (依賴追蹤矩陣)
- **Dependency Graph** (依賴關係圖 - 使用 Mermaid 或 draw.io)
- **Risk Mitigation Plan** (風險緩解計畫)
- **Communication Protocol** (溝通協議文件)

**品質標準**:
- ✅ 所有 🔴 High Risk 依賴必須有明確的緩解策略
- ✅ 依賴追蹤矩陣必須每日更新
- ✅ 跨團隊依賴必須有指定的協調負責人
- ✅ API Contract 必須在依賴項開始前完成定義

---

#### 步驟 7.2.2：Buffer Time 計算標準 🔴 **v0.01 新增**

> **⚠️ 為什麼需要 Buffer Time？**
>
> 實際開發中常見以下不確定因素：
> - 🚨 技術難度預估不準（新技術學習曲線）
> - 🚨 需求變更或澄清（需求理解偏差）
> - 🚨 團隊成員請假或離職
> - 🚨 外部依賴延遲（第三方 API、審批流程）
> - 🚨 意外問題（環境故障、資料遷移失敗）
>
> 若未預留 Buffer Time，將導致：
> - Sprint 超載 (Sprint Overload)
> - 交付延遲 (Delayed Delivery)
> - 團隊壓力過大 (Team Burnout)

**定義**：

**Buffer Time** 是在 Sprint 容量規劃中預留的額外時間緩衝，用於應對不確定性和風險。

**Buffer Time 不是**：
- ❌ 團隊偷懶的藉口
- ❌ 隨意增加的額外時間
- ❌ 固定的 20% 比例（需依據風險和經驗調整）

**Buffer Time 是**：
- ✅ 基於風險評估的科學預留
- ✅ 隨著團隊成熟度逐漸減少的調整機制
- ✅ 確保可持續交付的關鍵因素

---

##### 1. Buffer Time 計算公式

**標準公式**:

```
Sprint Buffer = Sprint Capacity × Risk Factor × Experience Factor
```

**參數說明**:

| 參數 | 定義 | 取值範圍 | 說明 |
|------|------|---------|------|
| **Sprint Capacity** | Sprint 總容量 (Story Points) | 實際 Velocity | 團隊在一個 Sprint 可完成的 SP 總和 |
| **Risk Factor** | 風險係數 | 0.10 - 0.20 | 基於 Sprint 的技術風險和不確定性 |
| **Experience Factor** | 經驗係數 | 0.8 - 1.3 | 基於團隊成熟度和專案熟悉度 |

---

##### 2. Risk Factor (風險係數) 定義

**Risk Factor 取值標準**:

| 風險等級 | Risk Factor | 適用情境 | 範例 |
|---------|------------|---------|------|
| **低風險 Sprint** | **0.10** (10%) | - 技術成熟穩定<br/>- 需求明確清晰<br/>- 無外部依賴 | - 純 CRUD 功能<br/>- UI 調整<br/>- 文案修改 |
| **中風險 Sprint** | **0.15** (15%) | - 中等技術複雜度<br/>- 需求有少量不確定性<br/>- 少量外部依賴 | - 新功能開發<br/>- 第三方 API 整合<br/>- 資料遷移 |
| **高風險 Sprint** | **0.20** (20%) | - 技術未經驗證 (POC)<br/>- 需求有較多不確定性<br/>- 多個外部依賴 | - 新技術導入<br/>- 架構重構<br/>- 複雜整合 |

**風險評估檢查清單**:

回答以下問題以判斷風險等級：

1. **技術風險**
   - [ ] 是否使用團隊不熟悉的技術或框架？
   - [ ] 是否需要技術 POC 驗證可行性？
   - [ ] 是否涉及複雜演算法或效能優化？

2. **需求風險**
   - [ ] 需求是否有模糊或待澄清的部分？
   - [ ] Stakeholder 是否經常變更需求？
   - [ ] AC (Acceptance Criteria) 是否完整明確？

3. **依賴風險**
   - [ ] 是否依賴第三方服務或外部團隊？
   - [ ] 是否需要等待審批或簽核流程？
   - [ ] 是否依賴尚未完成的前置任務？

4. **團隊風險**
   - [ ] 是否有團隊成員計畫請假？
   - [ ] 是否有新成員加入需要 onboarding？
   - [ ] 團隊規模是否小於 3 人（單點故障風險高）？

**評估規則**:
- ✅ 0-2 個 ☑️: 低風險 (Risk Factor = 0.10)
- ⚠️ 3-5 個 ☑️: 中風險 (Risk Factor = 0.15)
- 🔴 6+ 個 ☑️: 高風險 (Risk Factor = 0.20)

---

##### 3. Experience Factor (經驗係數) 定義

**Experience Factor 取值標準**:

| 團隊類型 | Experience Factor | 適用情境 | 說明 |
|---------|------------------|---------|------|
| **專家團隊** | **0.8** (減少 20%) | - 團隊協作 > 6 個月<br/>- 專案領域熟悉<br/>- 技術棧精通 | 團隊成熟度高，預留較少緩衝 |
| **成熟團隊** | **1.0** (標準) | - 團隊協作 3-6 個月<br/>- 專案領域了解<br/>- 技術棧熟悉 | 標準緩衝時間 |
| **新團隊** | **1.3** (增加 30%) | - 團隊協作 < 3 個月<br/>- 專案領域陌生<br/>- 技術棧學習中 | 團隊磨合期，需要更多緩衝 |

**團隊成熟度評估**:

| 評估項目 | 專家團隊 | 成熟團隊 | 新團隊 |
|---------|---------|---------|-------|
| **協作時間** | > 6 個月 | 3-6 個月 | < 3 個月 |
| **Velocity 穩定性** | 連續 3 Sprint 變化 < 10% | 連續 3 Sprint 變化 < 20% | Velocity 波動大或無歷史數據 |
| **技術棧熟悉度** | 全員精通 | 大部分成員熟悉 | 多數成員學習中 |
| **專案領域知識** | 深入了解業務邏輯 | 了解核心業務流程 | 仍在學習業務知識 |
| **溝通效率** | 高度默契，少量溝通即可 | 溝通順暢，偶有誤解 | 需大量溝通澄清 |

**特殊情境調整**:

| 特殊情境 | Experience Factor 調整 | 說明 |
|---------|---------------------|------|
| **團隊成員新加入** | +0.1 | 新成員需要 onboarding 時間 |
| **技術棧更換** | +0.2 | 學習新技術/框架需要額外時間 |
| **跨時區協作** | +0.1 | 溝通延遲增加協調成本 |
| **兼職團隊成員** | +0.15 | 可投入時間不穩定 |

---

##### 4. Buffer Time 計算範例

**範例 1: 中風險 + 新團隊**

**情境**:
- 團隊規模: 6 人
- Sprint 容量: 40 Story Points
- 風險評估: 中風險（第三方 API 整合、需求有少量不確定性）
- 團隊狀態: 新團隊（協作 2 個月）

**計算**:
```
Sprint Buffer = Sprint Capacity × Risk Factor × Experience Factor
Sprint Buffer = 40 SP × 0.15 × 1.3
Sprint Buffer = 7.8 SP ≈ 8 SP
```

**結論**:
- **可用容量**: 40 SP - 8 SP = **32 SP**（可分配給 User Stories 的容量）
- **Buffer 比例**: 8 / 40 = **20%**

**實際操作**:
- Sprint Backlog 規劃 32 SP 的 User Stories
- 預留 8 SP 作為緩衝（不分配具體任務）
- 若 Sprint 進度順利，可從 Product Backlog 拉取額外 Stories

---

**範例 2: 低風險 + 成熟團隊**

**情境**:
- 團隊規模: 8 人
- Sprint 容量: 60 Story Points
- 風險評估: 低風險（純 CRUD 功能、需求明確）
- 團隊狀態: 成熟團隊（協作 5 個月、技術棧熟悉）

**計算**:
```
Sprint Buffer = 60 SP × 0.10 × 1.0
Sprint Buffer = 6 SP
```

**結論**:
- **可用容量**: 60 SP - 6 SP = **54 SP**
- **Buffer 比例**: 6 / 60 = **10%**

---

**範例 3: 高風險 + 新團隊 + 技術棧更換**

**情境**:
- 團隊規模: 5 人
- Sprint 容量: 35 Story Points
- 風險評估: 高風險（新技術導入、架構重構）
- 團隊狀態: 新團隊（協作 1 個月）+ 技術棧更換 (+0.2)

**計算**:
```
Sprint Buffer = Sprint Capacity × Risk Factor × (Experience Factor + 技術棧調整)
Sprint Buffer = 35 SP × 0.20 × (1.3 + 0.2)
Sprint Buffer = 35 SP × 0.20 × 1.5
Sprint Buffer = 10.5 SP ≈ 11 SP
```

**結論**:
- **可用容量**: 35 SP - 11 SP = **24 SP**
- **Buffer 比例**: 11 / 35 = **31.4%**

**建議**:
- 考慮將 Sprint 1 定位為「探索 Sprint」（Spike Sprint）
- 減少功能交付目標，增加技術驗證和學習時間
- 預計 Sprint 2-3 後 Buffer 比例可降至 20%

---

##### 5. Buffer Time 應用層級

**Buffer Time 應用於 Sprint 容量，而非專案總時程**

| 應用層級 | 是否適用 | 說明 |
|---------|---------|------|
| **Sprint 容量** | ✅ **適用** | Buffer 用於單個 Sprint 的容量規劃，確保 Sprint 目標可達成 |
| **專案總時程** | ❌ **不適用** | 專案時程已包含多個 Sprint，無需額外 Buffer（除非高風險專案需專案層級 Buffer） |
| **User Story 估算** | ❌ **不適用** | User Story 的 Story Points 已包含不確定性，無需額外 Buffer |

**範例說明**:

假設專案有 4 個 Sprint，團隊 Velocity = 40 SP，中風險，新團隊：

```
每個 Sprint Buffer = 40 SP × 0.15 × 1.3 = 7.8 SP ≈ 8 SP
可用容量 = 40 SP - 8 SP = 32 SP

專案總容量 = 4 Sprint × 32 SP = 128 SP（可分配給 User Stories）
專案總 Buffer = 4 Sprint × 8 SP = 32 SP
```

**不應該**:
- ❌ 計算專案總容量時再額外加 20% Buffer（雙重計算）
- ❌ 在 User Story 估算時已加入 Buffer，Sprint 規劃時再加 Buffer（雙重計算）

---

##### 6. Buffer Time 動態調整策略

**隨著團隊成熟度，Buffer Time 應逐漸減少**

| Sprint | 團隊狀態 | Experience Factor | Buffer 比例 | 說明 |
|--------|---------|------------------|-----------|------|
| **Sprint 1** | 新團隊 | 1.3 | 20% | 團隊磨合期，預留較多緩衝 |
| **Sprint 2-3** | 學習中 | 1.2 | 18% | 團隊逐漸熟悉流程 |
| **Sprint 4-6** | 成熟團隊 | 1.0 | 15% | 團隊進入穩定期 |
| **Sprint 7+** | 專家團隊 | 0.8 | 12% | 團隊高度協作，減少緩衝 |

**調整觸發條件**:

| 條件 | 調整方向 | 說明 |
|------|---------|------|
| **連續 2 Sprint 提前完成** | ⬇️ 減少 Buffer 5% | 團隊容量評估偏保守，可適當增加挑戰 |
| **連續 2 Sprint 未完成目標** | ⬆️ 增加 Buffer 5% | 團隊壓力過大或容量預估過高 |
| **Velocity 穩定 (變化 < 10%)** | ⬇️ 減少 Buffer 至標準值 | 團隊進入穩定期 |
| **團隊成員離職/加入** | ⬆️ 臨時增加 Buffer 10% | 團隊穩定性受影響 |

---

##### 7. Buffer Time 最佳實踐

**7.1 Buffer Time 不等於 Slack Time（閒置時間）**

- ✅ **正確使用**: Buffer 用於應對意外情況（Bug 修復、需求澄清）
- ❌ **錯誤使用**: Buffer 成為團隊偷懶的藉口

**7.2 透明化 Buffer 使用情況**

在 Sprint Review 中報告 Buffer 使用情況：

| Sprint | 規劃容量 | Buffer | 實際完成 | Buffer 使用率 | 分析 |
|--------|---------|--------|---------|-------------|------|
| Sprint 1 | 32 SP | 8 SP | 35 SP | 37.5% | Buffer 不足，部分 Stories 延遲至 Sprint 2 |
| Sprint 2 | 32 SP | 8 SP | 38 SP | 75% | Buffer 充足，額外完成 6 SP |
| Sprint 3 | 32 SP | 8 SP | 40 SP | 100% | Buffer 完全使用，如期完成 |

**7.3 Buffer 使用優先順序**

當 Sprint 容量不足時，Buffer 的使用優先順序：

1. **🔴 P0**: 阻塞性 Bug 修復（影響主流程）
2. **🟡 P1**: 需求澄清和變更（Stakeholder 確認）
3. **🟢 P2**: 技術債償還（重構、測試覆蓋率提升）
4. **⚪ P3**: 額外 User Stories（從 Product Backlog 拉取）

**7.4 避免 Buffer 濫用**

| 濫用行為 | 正確做法 |
|---------|---------|
| ❌ 所有 Sprint 都設定 20% Buffer | ✅ 根據風險和經驗動態調整 Buffer |
| ❌ Buffer 用於填補需求不明確的 Stories | ✅ 需求不明確的 Stories 應延後至下個 Sprint |
| ❌ Buffer 成為團隊偷懶的藉口 | ✅ 透明化 Buffer 使用情況，定期回顧 |
| ❌ Buffer 從不使用，堆積越來越多 | ✅ 調整 Buffer 比例，增加 Sprint 挑戰性 |

---

##### 8. Buffer Time 與其他估算概念的關係

**8.1 Buffer Time vs Story Points 的 Uncertainty**

| 概念 | 層級 | 目的 | 範例 |
|------|------|------|------|
| **Story Points Uncertainty** | User Story 層級 | 反映單個 Story 的複雜度和不確定性 | US-001: 5 SP（中等複雜度） |
| **Buffer Time** | Sprint 層級 | 反映整個 Sprint 的風險和團隊不確定性 | Sprint 1: 40 SP，Buffer 8 SP |

**不應該**:
- ❌ User Story 已估算為 5 SP（含不確定性），Sprint 規劃時再乘以 1.2 倍（雙重計算）

**應該**:
- ✅ User Story 照實估算 (5 SP)
- ✅ Sprint 層級統一預留 Buffer (8 SP)

**8.2 Buffer Time vs Velocity 的關係**

| 概念 | 定義 | 計算方式 |
|------|------|---------|
| **Velocity** | 團隊實際完成能力 | 過去 3 Sprint 平均完成的 SP |
| **Sprint Capacity** | Sprint 可分配容量 | Velocity - Buffer Time |

**範例**:
```
Velocity = 40 SP（過去 3 Sprint 平均值）
Buffer = 40 SP × 0.15 × 1.3 = 7.8 SP ≈ 8 SP
Sprint Capacity = 40 SP - 8 SP = 32 SP（可分配容量）
```

---

##### 9. Buffer Time 檢查清單

在完成 Sprint 規劃前，使用此檢查清單驗證 Buffer Time 計算是否正確：

- [ ] **風險評估已完成**
  - [ ] 技術風險已評估（使用風險檢查清單）
  - [ ] 需求風險已評估（AC 完整性、需求明確度）
  - [ ] 依賴風險已評估（外部依賴、跨團隊協作）
  - [ ] 團隊風險已評估（請假、新成員）

- [ ] **Risk Factor 已確定**
  - [ ] 低風險 Sprint: Risk Factor = 0.10
  - [ ] 中風險 Sprint: Risk Factor = 0.15
  - [ ] 高風險 Sprint: Risk Factor = 0.20

- [ ] **Experience Factor 已確定**
  - [ ] 團隊成熟度已評估（協作時間、Velocity 穩定性）
  - [ ] 特殊情境調整已考慮（新成員、技術棧更換、跨時區）

- [ ] **Buffer Time 已計算**
  - [ ] 使用標準公式: `Sprint Buffer = Sprint Capacity × Risk Factor × Experience Factor`
  - [ ] Buffer Time 已四捨五入至整數 Story Points
  - [ ] Buffer 比例在合理範圍內（10%-35%）

- [ ] **可用容量已確定**
  - [ ] `Sprint Capacity = Velocity - Buffer Time`
  - [ ] Sprint Backlog 規劃的 Stories 總和 ≤ Sprint Capacity

- [ ] **Buffer 使用策略已明確**
  - [ ] Buffer 使用優先順序已定義（Bug 修復 > 需求澄清 > 技術債 > 額外 Stories）
  - [ ] Buffer 使用情況將在 Sprint Review 中報告

---

**產出文件**:
- **Buffer Time 計算表** (記錄 Risk Factor、Experience Factor、計算結果)
- **風險評估檢查清單** (技術/需求/依賴/團隊風險)
- **Sprint 容量規劃表** (Velocity、Buffer、可用容量)

**品質標準**:
- ✅ Buffer Time 計算公式正確應用
- ✅ Risk Factor 和 Experience Factor 有明確依據
- ✅ Buffer 比例在合理範圍內（10%-35%）
- ✅ Sprint Backlog 不超過可用容量

**參考文檔**:
- [Estimation_Standards.md](../../guides/system/planning/Estimation_Standards.md) - Story Points 估算標準
- [Velocity 預估指引](../../guides/system/planning/Estimation_Standards.md#14-新團隊-velocity-預估指引-v007-新增) - 新團隊 Velocity 預估

---

#### 步驟 7.3：Sprint 規劃確認點 🔴
系統會呈現：
1. Sprint Roadmap (時間線)
2. 每個 Sprint 的目標和 Stories
3. 風險和依賴
4. 里程碑定義
5. **跨 Sprint 依賴追蹤矩陣** 🔴 (v0.01 新增)

你需要確認規劃是否可行。

> 🆕 **合規驗收 Sprint 提示**（適用於涉及金流/個資/旅宿業/食品法規的系統）：
>
> 若系統涉及以下情境，建議在 Sprint Plan 中明確規劃「合規驗收 Sprint」（通常在最後 1-2 Sprint）：
>
> | 合規類型 | 觸發條件 | 建議 Sprint 任務 |
> |---------|---------|----------------|
> | **金流/支付（PCI-DSS）** | 含 Stripe、信用卡支付 | PCI-DSS 自評問卷（SAQ）、Stripe Dashboard 設定驗證、Webhook 靜默失敗測試 |
> | **電子發票（台灣稅法）** | 台灣電商/民宿 B2C | 綠界/藍新串接測試、發票格式驗證、作廢重開流程測試 |
> | **個資保護（GDPR/個資法）** | 收集個人資料 | GDPR Right to Erasure 測試、個資存取日誌驗證、隱私政策頁面 |
> | **旅宿業法規** | 民宿/旅館訂房系統 | 實名制旅客資料記錄、資料保留期限設定、民宿業登記文件 |
> | **合規掃描自動化** | 所有含個資系統 | 加入 CI Pipeline 的 Gitleaks 金鑰掃描、依賴漏洞定期掃描設定 |
>
> 🔧 **觸發 Skill**: `/compliance-audit`（在識別出合規需求時）

> 🆕 **合規驗收 Sprint 具體拆分建議**（基於 Greenfield QA 模擬測試 2026-04-01）：
>
> **拆分策略**：建議在 Sprint Roadmap 末段安排 1-2 個專屬合規 Sprint。
>
> | Sprint 名稱 | 安排時機 | 主要目標 | 參與角色 |
> |------------|---------|---------|---------|
> | **合規準備 Sprint**（Sprint N-1）| 上線前倒數第 2 Sprint | 合規缺口分析、修復任務清單 | PM + SA + Security Engineer + Compliance Officer |
> | **合規驗收 Sprint**（Sprint N）| 上線前最後 Sprint | 缺口修復、合規測試、文件補齊、最終審核 | Dev + QA + Security Engineer + Compliance Officer |
>
> **各合規類型具體 Sprint User Stories**：
>
> **PCI-DSS（含 Stripe 支付）**：
> - [ ] `US: 管理員可執行 Stripe PCI 自評問卷（SAQ-A/SAQ-A-EP）` AC: SAQ 完成率 100%
> - [ ] `US: 系統不儲存完整信用卡號（PAN）` AC: 通過 PCI Scan 零缺口
> - [ ] `US: Stripe Webhook 靜默失敗時系統自動重試` AC: 最多重試 3 次，記錄失敗日誌
> - [ ] `US: 支付金鑰可在後台輪替且不中斷服務` AC: 輪替後現有訂單不受影響
>
> **GDPR / 個資法**：
> - [ ] `US: 使用者可申請帳號資料刪除` AC: 30 天內完成匿名化，保留必要稽核軌跡
> - [ ] `US: 個資存取日誌可供稽核` AC: 保留 90 天，欄位含操作者/時間/IP
> - [ ] `US: 隱私政策頁符合個資法揭露要求` AC: 通過 Compliance Officer 審核
> - [ ] `US: Cookie Consent Banner 符合 GDPR` AC: 使用者拒絕後第三方追蹤停止
>
> **旅宿業法規**（民宿模組）：
> - [ ] `US: 訂房記錄實名制旅客資料` AC: 含身分證字號、入住/退房日期，格式符合觀光局規範
> - [ ] `US: 旅客資料超過保留期限後自動封存` AC: 法定期限（5年）後封存，不可直接查詢
>
> **🔴 合規 Sprint 完成標準**：
> - [ ] `/compliance-audit` Skill 執行完畢，無 P0/P1 缺口
> - [ ] Security Engineer 執行最終安全掃描確認
> - [ ] Compliance Officer 簽核合規驗收報告
> - [ ] 合規驗收報告歸檔至 `docs/06_quality/`

**產出文件**：
- Sprint Roadmap
- Sprint Backlog (每個 Sprint)
- Release Plan
- Risk Register
- **Dependency Tracking Matrix** 🔴 (v0.01 新增 - 依賴追蹤矩陣)
- **Dependency Graph** 🔴 (v0.01 新增 - 依賴關係視覺化圖)
- **Risk Mitigation Plan** 🔴 (v0.01 新增 - 風險緩解計畫)
- **Communication Protocol** 🔴 (v0.01 新增 - 跨 Sprint 溝通協議)

---

#### 步驟 7.4：Release Plan 版本: v0.01 新增**

> **重要性說明**:
> Release Plan 是產品版本發布的藍圖，清楚定義版本號、發布時程、功能清單與風險評估。
> 良好的版本規劃有助於團隊對齊目標、管理利害關係人期望，並確保發布品質。

##### 📋 Release Plan 必備元素

**1. 版本號規範 (Semantic Versioning)**

使用語義化版本控制 (SemVer)：`MAJOR.MINOR.PATCH`

| 版本類型 | 說明 | 範例 | 觸發條件 |
|---------|------|------|---------|
| **MAJOR** | 重大更新，破壞性變更 | 1.0.0 → 2.0.0 | API 不向後相容、架構重構、商業模式改變 |
| **MINOR** | 功能新增，向後相容 | 1.0.0 → 1.1.0 | 新功能上線、UI 改版、整合新服務 |
| **PATCH** | 錯誤修復，小改進 | 1.0.0 → 1.0.1 | Bug 修復、效能優化、文案調整 |

**版本號範例**：
- `0.1.0` - MVP 第一版 (Beta)
- `1.0.0` - 正式上線版本 (GA - General Availability)
- `1.1.0` - 新增次要功能
- `1.1.1` - 修正 1.1.0 的 Bug
- `2.0.0` - 重大架構升級或商業模式改變

**2. 發布時程規劃**

**時程規劃方法**：

| 方法 | 說明 | 適用場景 | 優點 | 缺點 |
|------|------|---------|------|------|
| **Time-boxed (固定時間)** | 每 2-4 週固定發布 | Agile/Scrum 團隊、SaaS 產品 | 節奏穩定、易於規劃 | 功能可能未完成需延後 |
| **Feature-based (功能驅動)** | 功能完成即發布 | Startup MVP、重大功能上線 | 靈活、功能完整性高 | 時程不可預測 |
| **Hybrid (混合式)** | 固定週期 + 重大功能例外發布 | 成熟產品、企業級應用 | 兼具穩定性與彈性 | 需更多協調與溝通 |

**發布時程範例** (Time-boxed)：

```
Sprint 1 (Week 1-2)  →  v0.1.0 (MVP Core)      - 2025-12-15
Sprint 2 (Week 3-4)  →  v0.2.0 (Feature Set A) - 2025-12-29
Sprint 3 (Week 5-6)  →  v0.3.0 (Feature Set B) - 2026-01-12
Sprint 4 (Week 7-8)  →  v1.0.0 (GA Release)    - 2026-01-26
```

**3. 功能清單與 Sprint 對應**

**Release-Sprint-Feature 映射表**：

| Release | Sprint | 功能 ID | 功能名稱 | 優先級 | 狀態 |
|---------|--------|---------|---------|--------|------|
| v0.1.0  | Sprint 1 | F-001 | 使用者註冊登入 | P0 | ✅ Done |
| v0.1.0  | Sprint 1 | F-002 | 基礎個人資料管理 | P0 | ✅ Done |
| v0.2.0  | Sprint 2 | F-003 | 搜尋與篩選功能 | P1 | 🔄 In Progress |
| v0.2.0  | Sprint 2 | F-004 | 收藏功能 | P1 | ⏳ Planned |
| v0.3.0  | Sprint 3 | F-005 | 通知系統 | P2 | ⏳ Planned |
| v1.0.0  | Sprint 4 | F-006 | 金流整合 | P0 | ⏳ Planned |

**優先級定義**：
- **P0** (Critical) - 產品核心功能，缺少無法上線
- **P1** (High) - 重要功能，影響使用者體驗
- **P2** (Medium) - 次要功能，可延後發布
- **P3** (Low) - Nice-to-have，視資源決定

**4. 風險評估與緩解計畫**

**Release Risk Assessment Table**：

| 風險 ID | 風險描述 | 影響版本 | 嚴重性 | 發生機率 | 緩解策略 | 負責人 |
|---------|---------|---------|--------|---------|---------|--------|
| R-001 | 第三方 API 整合延遲 | v0.2.0 | 高 | 中 | 提前 1 週開始整合測試，準備 Mock API | Dev Lead |
| R-002 | 金流測試環境申請時程 | v1.0.0 | 高 | 低 | Sprint 1 即提出申請 | PM |
| R-003 | 效能測試未達標 | v1.0.0 | 中 | 中 | Sprint 3 開始效能優化，設定監控指標 | SD |
| R-004 | 使用者驗收測試回饋負面 | v0.3.0 | 中 | 低 | Sprint 2 結束前進行內部測試 | QA + PM |

**風險嚴重性評估**：
- **高**: 可能導致發布延遲 > 1 週或功能無法上線
- **中**: 影響部分功能品質或延遲 < 1 週
- **低**: 輕微影響，不影響發布時程

**風險發生機率**：
- **高** (>60%): 幾乎確定會發生
- **中** (30-60%): 可能發生
- **低** (<30%): 不太可能發生

**5. Release Readiness Checklist (發布前檢查清單)**

在每個 Release 發布前，必須確認以下檢查項目：

**功能完整性** ✅
- [ ] 所有 P0 功能已完成且通過 QA
- [ ] P1 功能完成率 ≥ 80% (或明確記錄延後原因)
- [ ] 所有 Critical/High Bug 已修復
- [ ] Regression Testing 通過 (回歸測試)

**文件完整性** 📄
- [ ] Release Notes 已撰寫 (面向使用者)
- [ ] API Documentation 已更新 (若有 API 變更)
- [ ] User Guide / FAQ 已更新
- [ ] Migration Guide 已撰寫 (若有破壞性變更)

**技術準備** 🔧
- [ ] Production 環境已準備就緒
- [ ] Database Migration Script 已測試
- [ ] CI/CD Pipeline 已驗證
- [ ] Rollback Plan 已建立 (回滾計畫)
- [ ] Monitoring & Alerting 已設定

**利害關係人溝通** 📢
- [ ] 內部團隊已同步發布時程
- [ ] 客戶/使用者已提前通知 (若有停機維護)
- [ ] Customer Support 已完成訓練
- [ ] Marketing 已準備發布宣傳

---

##### 📝 Release Plan 完整範例

**專案名稱**: 民宿訂房平台 (B&B Booking Platform)

**Release: v1.0.0 - GA Release (正式上線版本)**

**目標發布日期**: 2026-01-26

**版本概述**:
這是民宿訂房平台的第一個正式上線版本 (General Availability)，包含使用者註冊登入、房源搜尋與預訂、金流整合、通知系統等核心功能，可支援基本的訂房流程。

---

**1. 版本資訊**

| 項目 | 內容 |
|------|------|
| **版本號** | v1.0.0 |
| **版本類型** | MAJOR - 正式上線版本 (GA) |
| **發布日期** | 2026-01-26 (Sprint 4 結束) |
| **前一版本** | v0.3.0 (2026-01-12) |
| **下一版本** | v1.1.0 (預計 2026-02-23) |

---

**2. 功能清單 (Feature List)**

**包含在此版本的功能** (Must-Have - P0/P1)：

| Sprint | 功能 ID | 功能名稱 | Kano 分類 | 優先級 | 完成狀態 |
|--------|---------|---------|----------|--------|---------|
| Sprint 1 | F-001 | 使用者註冊登入 (Email/Google/Facebook) | 🔴 必備型 | P0 | ✅ Done |
| Sprint 1 | F-002 | 基礎個人資料管理 | 🔴 必備型 | P0 | ✅ Done |
| Sprint 2 | F-003 | 房源搜尋與篩選 (地點/日期/價格/人數) | 🔴 必備型 | P0 | ✅ Done |
| Sprint 2 | F-004 | 房源詳細資訊頁面 (照片/描述/評論) | 🟡 期望型 | P1 | ✅ Done |
| Sprint 2 | F-005 | 收藏功能 (Wishlist) | 🟢 魅力型 | P1 | ✅ Done |
| Sprint 3 | F-006 | 訂房流程 (選擇房源 → 填寫資料 → 確認訂單) | 🔴 必備型 | P0 | ✅ Done |
| Sprint 3 | F-007 | 訂單管理 (查看訂單/取消訂單) | 🔴 必備型 | P0 | ✅ Done |
| Sprint 3 | F-008 | Email 通知 (訂單確認/取消通知) | 🟡 期望型 | P1 | ✅ Done |
| Sprint 4 | F-009 | 金流整合 (信用卡/LINE Pay) | 🔴 必備型 | P0 | 🔄 In Progress |
| Sprint 4 | F-010 | 房東後台 (房源管理/訂單管理) | 🔴 必備型 | P0 | 🔄 In Progress |

**延後到下一版本的功能** (Nice-to-Have - P2/P3)：

| 功能 ID | 功能名稱 | 優先級 | 延後原因 | 預計版本 |
|---------|---------|--------|---------|---------|
| F-011 | 即時聊天功能 (房客與房東) | P2 | WebSocket 整合複雜度高 | v1.1.0 |
| F-012 | App 推播通知 (Push Notification) | P2 | 需 iOS/Android 原生整合 | v1.1.0 |
| F-013 | 優惠券系統 | P3 | 非 MVP 核心功能 | v1.2.0 |
| F-014 | 多語系支援 (i18n) | P3 | 初期僅支援繁體中文 | v2.0.0 |

---

**3. 發布時程 (Release Schedule)**

**Sprint Timeline**：

```mermaid
gantt
    title Release v1.0.0 Timeline
    dateFormat  YYYY-MM-DD
    section Sprint 1
    使用者註冊登入 (F-001)       :done, s1-f1, 2025-12-01, 14d
    基礎個人資料管理 (F-002)     :done, s1-f2, 2025-12-01, 14d
    section Sprint 2
    房源搜尋與篩選 (F-003)       :done, s2-f1, 2025-12-15, 14d
    房源詳細資訊頁面 (F-004)     :done, s2-f2, 2025-12-15, 14d
    收藏功能 (F-005)             :done, s2-f3, 2025-12-15, 14d
    section Sprint 3
    訂房流程 (F-006)             :done, s3-f1, 2025-12-29, 14d
    訂單管理 (F-007)             :done, s3-f2, 2025-12-29, 14d
    Email 通知 (F-008)           :done, s3-f3, 2025-12-29, 14d
    section Sprint 4
    金流整合 (F-009)             :active, s4-f1, 2026-01-12, 14d
    房東後台 (F-010)             :active, s4-f2, 2026-01-12, 14d
    整合測試 & Bug Fix           :crit, s4-test, 2026-01-20, 6d
    GA Release                   :milestone, ga, 2026-01-26, 0d
```

**重要里程碑 (Milestones)**：

| 日期 | 里程碑 | 說明 |
|------|--------|------|
| 2025-12-15 | **v0.1.0 Release** | MVP Core - 使用者註冊登入完成 |
| 2025-12-29 | **v0.2.0 Release** | 房源搜尋與瀏覽功能完成 |
| 2026-01-12 | **v0.3.0 Release** | 訂房流程與訂單管理完成 |
| 2026-01-20 | **UAT Start** | 使用者驗收測試開始 (User Acceptance Testing) |
| 2026-01-24 | **Code Freeze** | 程式碼凍結，僅修復 Critical Bug |
| 2026-01-26 | **v1.0.0 GA** | 正式上線 (General Availability) 🎉 |

---

**4. 風險評估與緩解計畫 (Risk Assessment)**

| 風險 ID | 風險描述 | 影響 | 嚴重性 | 機率 | 緩解策略 | 負責人 | 狀態 |
|---------|---------|------|--------|------|---------|--------|------|
| **R-001** | 金流測試環境申請延遲 | v1.0.0 無法如期上線 | 🔴 高 | 🟡 中 | **已執行**: Sprint 1 即提出申請；**備案**: 準備 Mock Payment API | PM (Victoria) | ✅ 已緩解 |
| **R-002** | 第三方 API (Google Maps) 整合問題 | 房源地圖功能異常 | 🟡 中 | 🟢 低 | Sprint 2 提前整合測試；備案：使用靜態地圖 | Dev (David) | ✅ 已通過 |
| **R-003** | UAT 回饋負面，需大量修改 | 發布延遲 1-2 週 | 🟡 中 | 🟡 中 | Sprint 3 結束前進行內部 Alpha Testing | QA (Quincy) | 🔄 監控中 |
| **R-004** | Production 環境效能未達標 | 使用者體驗不佳、負評 | 🟡 中 | 🟢 低 | Sprint 3 開始效能測試；目標: API 回應 < 500ms | SD (Marcus) | 🔄 監控中 |
| **R-005** | 關鍵成員請假 (農曆新年) | 開發進度延遲 | 🟢 低 | 🟡 中 | 提前規劃 Sprint 4 任務分配；Cross-training | PM (Victoria) | ✅ 已規劃 |

**風險圖例**：
- 🔴 高嚴重性 / 🟡 中嚴重性 / 🟢 低嚴重性
- 🔴 高機率 / 🟡 中機率 / 🟢 低機率

---

**5. Release Readiness Checklist (發布前檢查清單)**

**功能完整性** ✅

- [x] 所有 P0 功能 (F-001/002/003/006/007/009/010) 已完成且通過 QA
- [x] P1 功能完成率 100% (F-004/005/008)
- [x] 所有 Critical Bug 已修復 (0 個待修復)
- [x] 所有 High Priority Bug 已修復 (2 個待修復 → 已全數修復)
- [x] Regression Testing 通過 (回歸測試 - 150 個測試案例全數通過)

**文件完整性** 📄

- [x] Release Notes 已撰寫 ([Release_Notes_v1.0.0.md](docs/release-notes/v1.0.0.md))
- [x] API Documentation 已更新 ([API_Index.md](docs/api/API_Index.md) - 25 個端點)
- [x] User Guide 已撰寫 ([User_Guide_v1.0.md](docs/user-guide/v1.0.md))
- [x] FAQ 已更新 (新增 15 個常見問題)
- [ ] Migration Guide - **不適用** (v1.0.0 為首次上線，無需遷移)

**技術準備** 🔧

- [x] Production 環境已準備就緒 (AWS EC2 + RDS + S3)
- [x] Database Migration Script 已測試 (10 個 migration scripts)
- [x] CI/CD Pipeline 已驗證 (GitHub Actions - 自動測試 + 部署)
- [x] Rollback Plan 已建立 ([Rollback_Plan_v1.0.0.md](docs/operations/rollback-v1.0.0.md))
- [x] Monitoring & Alerting 已設定 (CloudWatch + Sentry)
- [x] Backup Strategy 已執行 (每日自動備份 Database)

**安全性檢查** 🔒

- [x] Security Audit 完成 (OWASP Top 10 檢查)
- [x] Penetration Testing 完成 (第三方安全測試)
- [x] SSL Certificate 已安裝 (HTTPS)
- [x] API Rate Limiting 已設定 (100 requests/min per user)
- [x] Sensitive Data Encryption 已實作 (密碼 bcrypt / 信用卡 Tokenization)

**利害關係人溝通** 📢

- [x] 內部團隊已同步發布時程 (Kickoff Meeting - 2026-01-10)
- [x] Beta Users 已提前通知 (50 位種子使用者已收到邀請)
- [x] Customer Support 已完成訓練 (3 場訓練課程 + FAQ 文件)
- [ ] Marketing 已準備發布宣傳 - **進行中** (Landing Page + Social Media 貼文)
- [x] Legal Compliance 確認 (隱私權政策 + 服務條款已審核)

**效能驗證** ⚡

- [x] Load Testing 通過 (1000 concurrent users - 99.9% 成功率)
- [x] API Response Time < 500ms (平均 320ms)
- [x] Page Load Time < 3s (平均 1.8s)
- [x] Database Query Optimization 完成 (慢查詢已優化)

---

**6. 發布後計畫 (Post-Release Plan)**

**第一週監控重點** (2026-01-26 ~ 02-02)：

| 監控項目 | 監控指標 | 警示閾值 | 負責人 |
|---------|---------|---------|--------|
| **系統穩定性** | Error Rate | > 1% | DevOps |
| **效能監控** | API Response Time | > 1000ms | Backend Dev |
| **使用者行為** | 註冊轉換率 | < 10% | PM + Marketing |
| **金流成功率** | Payment Success Rate | < 95% | Backend Dev |
| **客服回報** | Critical Issues | > 5 issues/day | Customer Support |

**Hotfix 機制**：
- **Critical Bug** (P0): 24 小時內修復並發布 Hotfix (v1.0.1)
- **High Bug** (P1): 3 天內修復，併入下次 Patch Release
- **Medium/Low Bug** (P2/P3): 納入 v1.1.0 規劃

**下一版本規劃** (v1.1.0 - 預計 2026-02-23)：
- 新增即時聊天功能 (F-011)
- 新增 App 推播通知 (F-012)
- 根據使用者回饋進行 UX 優化

---

**7. 簽核 (Sign-off)**

| 角色 | 姓名 | 簽核日期 | 狀態 |
|------|------|---------|------|
| **Product Manager** | Victoria | 2026-01-24 | ✅ 已簽核 |
| **System Analyst** | Amanda | 2026-01-24 | ✅ 已簽核 |
| **System Designer** | Marcus | 2026-01-24 | ✅ 已簽核 |
| **Dev Lead** | David | 2026-01-24 | ✅ 已簽核 |
| **QA Lead** | Quincy | 2026-01-24 | ✅ 已簽核 |

---

**📝 Release Plan Template 位置**: `checklists/Release_Plan_Template.md` 🚧 (v0.01+ 預留)

---

🆕 **複雜工作流 Sprint 拆分方法論**（IMP-13 合併）:

> 💡 當系統包含「複雜業務工作流」（如多層審核、多狀態流轉、多角色依賴）時，
> Sprint 拆分需額外考慮以下因素：

> **1. 狀態機拆分原則**:
> - 每個 Sprint 實現 2-3 個狀態轉換（而非整個流程）
> - 第一個 Sprint 必須包含「基礎狀態機框架 + 核心路徑」（Happy Path）
> - 後續 Sprint 逐步添加「異常路徑」（駁回、超時、取消等）
>
> **2. 循環依賴識別**:
> - 繪製「功能依賴圖」，識別雙向依賴（如：審核依賴權限，權限設定依賴審核結果）
> - 使用「介面抽象」打破循環：先定義介面 → 分別實作 → 整合測試
>
> **3. 業務規則優先級排序**:
> | 優先級 | 規則類型 | 範例 | Sprint 安排 |
> |-------|---------|------|------------|
> | P0 | 核心流程規則 | 提交→審核→發布 | Sprint 1-2 |
> | P1 | 異常處理規則 | 駁回迴圈、超時自動關閉 | Sprint 3 |
> | P2 | 邊界情況 | 並行審核衝突、角色變更中的審核 | Sprint 4 |
> | P3 | 優化規則 | 自動分派審核人、智慧推薦 | Sprint 5+ |

---

#### 步驟 7.5：Sprint Retrospective 指引 🔴 **v0.01 新增**

> **重要性說明**:
> Sprint Retrospective (Sprint 回顧會議) 是敏捷開發中持續改進的核心機制。
> 每個 Sprint 結束時，團隊應聚焦於「流程改進」而非「功能檢討」，
> 識別問題、總結經驗、制定行動計畫，確保團隊持續成長。

**執行時機**: 每個 Sprint 結束時 (建議 Sprint Demo 之後立即進行)

**參與人員**: 全體開發團隊 (PM/PO, SA, SD, Dev, QA) + Scrum Master/Facilitator

**建議時長**:
- 2-week Sprint: 1.5 小時
- 3-week Sprint: 2 小時
- 4-week Sprint: 2.5 小時

---

##### 📋 Sprint Retrospective 標準流程

**1. 開場與氛圍營造** (5-10 分鐘)

**目的**: 建立安全、開放的討論氛圍

**Facilitator 開場話術**:
> "這次 Retrospective 的目的是改進我們的工作流程，而不是指責個人。
> 所有回饋都是建設性的，我們專注於「我們可以做得更好」，而不是「誰做錯了」。
> 請大家誠實、開放地分享想法。"

**重要原則**:
- ✅ **Vegas Rule**: What happens in retro, stays in retro (會議內容保密，營造信任)
- ✅ **No Blame Culture**: 專注流程改進，不指責個人
- ✅ **Everyone Participates**: 每個人都應發言，避免沉默的大多數
- ❌ **不討論功能細節**: Retrospective 專注於「如何工作」，不討論「做什麼功能」

---

**2. 使用 4L 回顧法進行數據收集** (30-40 分鐘)

**4L Framework**:

| 維度 | 英文 | 問題引導 | 範例 |
|------|------|---------|------|
| 💚 **Liked** | What we Liked | 這個 Sprint 中，你喜歡/欣賞的事情是什麼？ | "Daily Standup 時間縮短到 15 分鐘，更有效率" |
| 📚 **Learned** | What we Learned | 這個 Sprint 中，你學到了什麼新知識/技能？ | "學會使用 React Query 處理 Server State" |
| 😞 **Lacked** | What we Lacked | 這個 Sprint 中，我們缺少什麼？需要什麼幫助？ | "缺乏 API 文檔，前後端協作時常需要確認" |
| 🔥 **Longed For** | What we Longed For | 這個 Sprint 中，你渴望擁有但沒有的是什麼？ | "希望有 Code Review 的標準流程和 Checklist" |

**執行方式**:

**Step 1: 個人書寫** (10 分鐘)
- 每個人使用便利貼/線上白板工具 (Miro, FigJam) 寫下自己的想法
- 每張便利貼只寫一個想法 (簡短、具體)
- 匿名或具名皆可 (視團隊文化決定)

**Step 2: 分享與分組** (15 分鐘)
- 每個人輪流分享自己的便利貼內容
- Facilitator 將相似的便利貼分組 (Affinity Grouping)
- 為每組命名主題 (例: "溝通問題", "技術債務", "流程改進")

**Step 3: 投票優先化** (5 分鐘)
- 每個人有 3 票，投給自己認為最重要的議題
- 統計票數，選出 Top 3-5 議題進行深入討論

**4L 範例表格** (Sprint 2 Retrospective):

| 維度 | 內容 | 票數 | 優先級 |
|------|------|------|--------|
| 💚 **Liked** | Daily Standup 改為 15 分鐘，更聚焦 | 5 票 | - |
| 💚 **Liked** | SD (Marcus) 提供的 C4 架構圖非常清楚 | 3 票 | - |
| 📚 **Learned** | 學會使用 React Query 管理 Server State | 2 票 | - |
| 📚 **Learned** | 理解 Semantic Versioning 對 Release 的重要性 | 1 票 | - |
| 😞 **Lacked** | API 文檔不完整，前後端協作效率低 | **8 票** | **P0** |
| 😞 **Lacked** | Code Review 標準不一致，有時太嚴格有時太鬆散 | **7 票** | **P1** |
| 😞 **Lacked** | 測試環境不穩定，QA 常被 Block | **6 票** | **P2** |
| 🔥 **Longed For** | 希望有 Pair Programming 時間，減少知識孤島 | 4 票 | P3 |
| 🔥 **Longed For** | 希望每週有 Tech Sharing 時間 | 2 票 | P4 |

---

**3. 根本原因分析與行動計畫** (30-40 分鐘)

針對 Top 3-5 議題，使用 **5 Whys 技巧**找出根本原因，並制定行動計畫。

**5 Whys 範例** (針對 "API 文檔不完整" 問題):

| Why | 問題 | 答案 |
|-----|------|------|
| Why 1 | 為什麼 API 文檔不完整？ | 因為 Backend Dev 沒有時間寫文檔 |
| Why 2 | 為什麼沒有時間？ | 因為開發任務排太滿，沒有預留文檔時間 |
| Why 3 | 為什麼沒有預留時間？ | 因為 Sprint 規劃時沒有將文檔工作納入 Story Point |
| Why 4 | 為什麼沒有納入？ | 因為團隊認為文檔是「額外工作」，不是「必要工作」 |
| Why 5 | 為什麼這樣認為？ | 因為過去沒有明確的文檔標準和 Definition of Done |

**根本原因**: 缺乏明確的文檔標準，且 Sprint 規劃時未將文檔納入 DoD

**行動計畫範例表格**:

| 議題 | 根本原因 | 行動計畫 | 負責人 | 目標完成時間 | 驗收標準 |
|------|---------|---------|--------|-------------|---------|
| **API 文檔不完整** | Sprint 規劃未將文檔納入 DoD | 1. 更新 Definition of Done，明確要求每個 API 都需文檔<br>2. Sprint 規劃時，為文檔工作預留 10-15% SP<br>3. 使用 Swagger/OpenAPI 自動生成文檔 | **PM (Victoria)**: DoD 更新<br>**Dev (David)**: Swagger 導入 | Sprint 3 開始前 (2026-01-10) | ✅ DoD Checklist 已更新<br>✅ Swagger 已整合到專案<br>✅ 至少 80% API 有文檔 |
| **Code Review 標準不一致** | 缺乏明確的 Code Review Checklist | 1. 建立 Code Review Checklist<br>2. 制定 Review 時間限制 (24 小時內完成)<br>3. 每週 Code Review 回顧會議 | **Dev (David)** | Sprint 3 第一週 (2026-01-05) | ✅ Checklist 已建立並分享<br>✅ 團隊已同意 Review SLA<br>✅ 至少執行 1 次回顧會議 |
| **測試環境不穩定** | 缺乏自動化部署和健康檢查 | 1. 導入 Docker Compose 統一環境<br>2. 建立 Staging 環境健康檢查 (Health Check)<br>3. 每日自動重置測試資料 | **DevOps / SD (Marcus)** | Sprint 3 第二週 (2026-01-12) | ✅ Docker Compose 已設定<br>✅ Health Check API 已建立<br>✅ 測試環境穩定度 > 95% |

---

**4. 行動計畫追蹤機制** 🔴 **Critical**

**追蹤方式**:
- 每個行動計畫都需要明確的**負責人**、**目標完成時間**、**驗收標準**
- 在下一次 Retrospective 開始前，先檢查上次行動計畫的完成狀況
- 未完成的行動計畫需說明原因，並決定是否延續或取消

**下次 Retrospective 開場檢查清單**:

| 上次行動計畫 | 負責人 | 狀態 | 完成度 | 備註 |
|------------|--------|------|--------|------|
| 更新 DoD，明確要求 API 文檔 | Victoria | ✅ Done | 100% | DoD Checklist 已更新並分享給團隊 |
| 導入 Swagger 自動生成文檔 | David | ✅ Done | 100% | Swagger UI 已整合，80% API 有文檔 |
| 建立 Code Review Checklist | David | 🔄 In Progress | 70% | Checklist 已建立，但尚未執行回顧會議 → **延續到下個 Sprint** |
| 導入 Docker Compose | Marcus | ❌ Blocked | 30% | 因資源限制，優先級降低 → **討論是否取消或延後** |

---

##### 📝 完整 Retrospective 範例

**專案**: 民宿訂房平台 (B&B Booking Platform)

**Sprint**: Sprint 2 (2025-12-15 ~ 2025-12-29)

**參與人員**: Victoria (PM), Amanda (SA), Marcus (SD), David (Dev Lead), Quincy (QA), + 3 位 Developers

**會議時間**: 2025-12-29 14:00-15:30 (1.5 小時)

**Facilitator**: Victoria (PM)

---

**1. 開場** (5 分鐘)

Victoria: "大家好，歡迎來到 Sprint 2 的 Retrospective。這次 Sprint 我們完成了房源搜尋與瀏覽功能，辛苦大家了！今天的重點是檢討我們的工作流程，看看有哪些可以改進的地方。請大家放心分享真實想法，這裡沒有對錯，只有改進的機會。"

---

**2. 4L 數據收集** (30 分鐘)

**個人書寫** (10 分鐘) - 使用 Miro 白板

**分享與分組** (15 分鐘):

| 維度 | 便利貼內容 | 分組主題 | 票數 |
|------|-----------|---------|------|
| 💚 **Liked** | - Daily Standup 改為 15 分鐘，更聚焦<br>- SD (Marcus) 的 C4 架構圖很清楚<br>- QA 提早介入，減少後期 Bug | 流程改進 (3 票) | 3 票 |
| 📚 **Learned** | - React Query 管理 Server State<br>- Google Maps API 整合技巧<br>- 理解 Semantic Versioning | 技術成長 (2 票) | 2 票 |
| 😞 **Lacked** | - **API 文檔不完整**，前後端常需確認<br>- **Code Review 標準不一致**<br>- **測試環境不穩定**，QA 被 Block | **協作痛點** | **8+7+6 = 21 票** |
| 🔥 **Longed For** | - 希望有 Pair Programming 時間<br>- 希望每週 Tech Sharing | 團隊文化 (4 票) | 4 票 |

**投票結果 (Top 3)**:
1. **API 文檔不完整** (8 票) → P0
2. **Code Review 標準不一致** (7 票) → P1
3. **測試環境不穩定** (6 票) → P2

---

**3. 根本原因分析與行動計畫** (40 分鐘)

**議題 1: API 文檔不完整** (8 票)

**5 Whys 分析**:
- Why 1: 為什麼 API 文檔不完整？ → Backend Dev 沒有時間寫
- Why 2: 為什麼沒有時間？ → Sprint 規劃時沒有預留文檔時間
- Why 3: 為什麼沒有預留？ → 團隊認為文檔是「額外工作」
- Why 4: 為什麼這樣認為？ → 過去沒有明確的文檔標準和 DoD

**根本原因**: Sprint 規劃未將文檔納入 Definition of Done

**行動計畫**:
| 行動項目 | 負責人 | 完成時間 | 驗收標準 |
|---------|--------|---------|---------|
| 更新 DoD，明確要求每個 API 需 Swagger 文檔 | Victoria | 2026-01-05 | DoD Checklist 已更新 |
| 導入 Swagger/OpenAPI 自動生成文檔 | David | 2026-01-10 | 至少 80% API 有文檔 |
| Sprint 規劃時為文檔工作預留 10% SP | Victoria + Amanda | Sprint 3 開始 | Sprint 3 Backlog 已包含文檔工作 |

---

**議題 2: Code Review 標準不一致** (7 票)

**5 Whys 分析**:
- Why 1: 為什麼標準不一致？ → 沒有明確的 Checklist
- Why 2: 為什麼沒有 Checklist？ → 團隊各自經驗不同，標準不同

**根本原因**: 缺乏統一的 Code Review 標準和流程

**行動計畫**:
| 行動項目 | 負責人 | 完成時間 | 驗收標準 |
|---------|--------|---------|---------|
| 建立 Code Review Checklist (安全、效能、可讀性) | David | 2026-01-07 | Checklist 已建立並分享 |
| 制定 Review SLA: 24 小時內完成 | Team | 2026-01-05 | 團隊已同意並執行 |
| 每週五 Code Review 回顧會議 (15 分鐘) | David | 每週五 | 至少執行 1 次 |

---

**議題 3: 測試環境不穩定** (6 票)

**5 Whys 分析**:
- Why 1: 為什麼測試環境不穩定？ → 資料庫資料常被污染
- Why 2: 為什麼會被污染？ → 多人共用同一環境，沒有隔離
- Why 3: 為什麼沒有隔離？ → 沒有自動化重置機制

**根本原因**: 缺乏測試環境管理與自動化重置機制

**行動計畫**:
| 行動項目 | 負責人 | 完成時間 | 驗收標準 |
|---------|--------|---------|---------|
| 導入 Docker Compose 統一測試環境 | Marcus | 2026-01-15 | Docker Compose 已設定 |
| 建立每日自動重置測試資料腳本 | David | 2026-01-12 | 每日凌晨 2:00 自動重置 |
| 建立 Staging 環境健康檢查 API | David | 2026-01-10 | Health Check 正常運作 |

---

**4. 總結與會議結尾** (5 分鐘)

Victoria: "非常感謝大家的積極參與！這次我們識別了 3 個重要議題，並制定了 9 個具體行動計畫。我會將這些行動計畫整理成文檔，並在下次 Retrospective 開始時檢查完成狀況。希望 Sprint 3 我們能看到這些改進帶來的效果。大家辛苦了！"

**會議記錄位置**: [Sprint_2_Retrospective.md](docs/retrospectives/sprint-2-retro.md)

---

##### ⚠️ Retrospective 常見問題與反模式

**問題 1: 會議變成指責大會**
- ❌ **錯誤**: "David 的 Code Review 太慢，拖累進度"
- ✅ **正確**: "Code Review 時效性有待改進，我們可以制定 24 小時 SLA"

**問題 2: 只有少數人發言**
- **解決方案**: 使用 Round-robin (輪流發言) 或匿名便利貼

**問題 3: 行動計畫從不執行**
- **解決方案**:
  - 每次 Retrospective 開始前先檢查上次行動計畫
  - 未完成的行動計畫需說明原因
  - 限制行動計畫數量 (每次最多 3-5 個)

**問題 4: 討論功能細節而非流程**
- ❌ **錯誤**: "這個功能應該用 Redux 還是 Context API？"
- ✅ **正確**: "技術選型決策流程不明確，我們需要建立 Architecture Decision Record (ADR)"

**問題 5: 缺乏 Facilitator 控場**
- **解決方案**: 指定專門的 Facilitator (通常是 Scrum Master 或 PM)，負責控制時間和引導討論

---

##### 📊 Retrospective 成效評估指標

**定性指標**:
- ✅ 團隊滿意度提升 (每季進行團隊滿意度調查)
- ✅ 行動計畫完成率 > 70%
- ✅ 重複出現的問題減少

**定量指標**:
- ✅ Sprint Velocity 穩定度提升 (標準差降低)
- ✅ Bug 數量減少
- ✅ Code Review 週轉時間縮短
- ✅ CI/CD Pipeline 成功率提升

---

**📝 Sprint Retrospective Template 位置**: `checklists/Sprint_Retrospective_Template.md` 🚧 (v0.01+ 預留)

---

#### 步驟 7.6：技術債務追蹤機制 🔴 **v0.01 新增**

> **重要性說明**:
> 技術債務 (Technical Debt) 是軟體開發中無法避免的現實。為了快速交付功能，
> 團隊常會採取「暫時性」的解決方案，但這些捷徑會累積成技術債務，
> 影響未來的開發速度和程式碼品質。系統化的技術債務追蹤機制能確保債務可見、可控、可償還。

**執行時機**:
- **識別時機**: Sprint Planning、Code Review、Retrospective、Daily Standup
- **評估時機**: Sprint Planning (每個 Sprint 評估是否償還)
- **償還時機**: 併入 Sprint Backlog (每個 Sprint 預留 10-20% 時間償還債務)

---

##### 📋 技術債務定義與分類

**什麼是技術債務？**

技術債務是指為了短期目標（快速交付、趕上 deadline）而採取的「非最佳解決方案」，
導致長期維護成本增加的技術選擇。

**技術債務 vs Bug**：

| 維度 | 技術債務 (Technical Debt) | Bug (缺陷) |
|------|-------------------------|-----------|
| **定義** | 功能正常運作，但實作方式不佳 | 功能異常或不符合需求 |
| **範例** | 「這個 API 用 Callback Hell 寫的，未來很難維護」 | 「使用者無法登入」 |
| **影響** | 長期維護成本增加、開發速度變慢 | 使用者體驗受損、功能無法使用 |
| **優先級** | 可策略性延後處理 | 必須立即修復 (Critical/High) |
| **處理方式** | 重構 (Refactoring) | Bug Fix |

---

##### 📊 技術債務分類標準

**技術債務類型分類** (7 大類型):

| 類型 | 說明 | 範例 | 識別方式 |
|------|------|------|---------|
| **1. Code Quality Debt<br>(程式碼品質債務)** | 程式碼可讀性差、重複程式碼、命名不清 | - 200 行的巨型函式<br>- 複製貼上的程式碼<br>- 變數名稱 `a`, `b`, `temp` | Code Review<br>SonarQube<br>ESLint |
| **2. Architecture Debt<br>(架構債務)** | 架構設計不良、模組耦合度高、缺乏擴展性 | - 前後端混在同一個 Repo<br>- 所有邏輯寫在 Controller<br>- 缺乏 Service Layer | 架構審查<br>依賴關係圖分析 |
| **3. Test Debt<br>(測試債務)** | 測試覆蓋率不足、缺乏自動化測試 | - 核心功能無單元測試<br>- E2E 測試覆蓋率 < 30%<br>- 手動測試佔比過高 | 測試覆蓋率報告<br>CI/CD Pipeline |
| **4. Documentation Debt<br>(文檔債務)** | 文檔過時、缺失或不完整 | - API 文檔與實作不一致<br>- README 過時<br>- 沒有架構圖 | 文檔審查<br>新人 Onboarding 回饋 |
| **5. Infrastructure Debt<br>(基礎設施債務)** | 部署流程手動、環境不一致、缺乏監控 | - 手動部署 (無 CI/CD)<br>- Dev/Staging/Prod 環境不一致<br>- 沒有 Logging/Monitoring | DevOps 審查<br>部署時間統計 |
| **6. Dependency Debt<br>(依賴債務)** | 套件版本過舊、有安全漏洞 | - React 15 (已不維護)<br>- npm audit 顯示 10+ 漏洞<br>- 使用已棄用的 API | `npm audit`<br>`dependabot` alerts |
| **7. Performance Debt<br>(效能債務)** | 效能瓶頸、未優化的查詢 | - API 回應時間 > 2s<br>- N+1 Query 問題<br>- 沒有 Cache 機制 | APM 工具 (New Relic)<br>Database Query Profiling |

---

##### 🎯 技術債務優先級評估機制

使用 **Impact-Effort Matrix (影響-工作量矩陣)** 評估技術債務優先級：

```
影響度 (Impact)
    ↑
高  │ [P1] 高影響、低工作量    │ [P0] 高影響、高工作量
    │ ✅ 快速償還              │ ⚠️ 分階段償還
    │ (Quick Wins)             │ (Strategic Debt)
    ├─────────────────────────┼─────────────────────────
低  │ [P3] 低影響、低工作量    │ [P2] 低影響、高工作量
    │ 💤 視情況處理            │ ❌ 暫不處理
    │ (Minor Debt)             │ (Avoid)
    └─────────────────────────┴────────────────────────→
                              工作量 (Effort)
                         低                    高
```

**優先級定義**：

| 優先級 | 名稱 | 影響 | 工作量 | 處理策略 | 範例 |
|--------|------|------|--------|---------|------|
| **P0** | Critical Debt | 高 | 高 | **分階段償還**：每個 Sprint 預留 20% 時間逐步處理 | 核心模組缺乏測試、架構耦合度過高 |
| **P1** | High-Value Quick Wins | 高 | 低 | **快速償還**：下個 Sprint 立即處理 | 重複程式碼重構、API 文檔補齊 |
| **P2** | Low-Value High-Effort | 低 | 高 | **暫不處理**：ROI 不高，除非有明確需求 | 舊功能的小幅優化 |
| **P3** | Minor Debt | 低 | 低 | **視情況處理**：有空時處理，不強制 | 變數命名改進、註解補充 |

---

##### 📝 技術債務追蹤表格範本

**技術債務登記表** (Tech Debt Register)

| Debt ID | 類型 | 描述 | 影響 | 工作量 | 優先級 | 負責人 | 記錄日期 | 目標償還時間 | 狀態 |
|---------|------|------|------|--------|--------|--------|---------|------------|------|
| **TD-001** | Code Quality | `UserService.js` 單一檔案 800 行，職責不清 | 高 (新功能開發困難) | 中 (2-3 天) | **P0** | David | 2025-12-20 | Sprint 3 | 🔄 In Progress |
| **TD-002** | Test Debt | 支付模組缺乏單元測試，覆蓋率 0% | 高 (風險極高) | 高 (5 天) | **P0** | Quincy | 2025-12-22 | Sprint 3-4 分階段 | ⏳ Planned |
| **TD-003** | Documentation | API 文檔與實作不一致 (20 個端點) | 高 (前後端協作效率低) | 低 (1 天) | **P1** | David | 2025-12-15 | Sprint 3 第一週 | ⏳ Planned |
| **TD-004** | Architecture | 前端 State Management 缺乏統一規範 | 中 (程式碼維護困難) | 中 (3 天) | **P1** | Marcus | 2025-12-18 | Sprint 4 | 📋 Backlog |
| **TD-005** | Performance | 房源列表 API 回應時間 3.5s (目標 < 500ms) | 高 (使用者體驗差) | 中 (2 天) | **P0** | David | 2025-12-25 | Sprint 3 | ✅ Done |
| **TD-006** | Dependency | React Router v5 (v6 已發布 1 年) | 低 (功能正常) | 高 (4 天 + 回歸測試) | **P2** | David | 2025-12-10 | v2.0.0 再處理 | 📋 Backlog |
| **TD-007** | Infrastructure | 手動部署到 Production (耗時 30 分鐘) | 中 (效率低) | 低 (1 天設定 CI/CD) | **P1** | Marcus | 2025-12-12 | Sprint 3 | ✅ Done |

**欄位說明**：
- **Debt ID**: 債務編號 (格式: `TD-XXX`)
- **類型**: 7 大類型之一 (Code Quality, Architecture, Test, Documentation, Infrastructure, Dependency, Performance)
- **描述**: 具體問題描述
- **影響**: 高/中/低 (對開發效率、使用者體驗的影響)
- **工作量**: 高/中/低 (預估處理時間: 高 > 3 天, 中 1-3 天, 低 < 1 天)
- **優先級**: P0/P1/P2/P3
- **負責人**: 指定負責償還的人員
- **記錄日期**: 債務識別日期
- **目標償還時間**: 預計償還時程 (可以是 Sprint 編號或版本號)
- **狀態**: 📋 Backlog / ⏳ Planned / 🔄 In Progress / ✅ Done / ❌ Cancelled

---

##### 🔄 技術債務管理流程

**1. 識別 (Identification)** - 誰都可以提出技術債務

**識別來源**：
- **Code Review**: Reviewer 發現程式碼品質問題
- **Sprint Retrospective**: 團隊回顧時識別流程或架構問題
- **Daily Standup**: 開發者提出遇到的技術障礙
- **Architecture Review**: SD/Architect 定期審查架構
- **自動化工具**: SonarQube, ESLint, npm audit

**識別範例**：
```
Developer (David): "我在開發新功能時發現 UserService.js 已經 800 行了，
職責不清，很難找到對應的邏輯。我建議拆分成多個 Service。"

→ 登記為 TD-001: Code Quality Debt
```

---

**2. 評估 (Assessment)** - 團隊共同評估優先級

**評估時機**: Sprint Planning 時討論

**評估問題**：
- **影響**: 這個債務對開發效率/使用者體驗的影響有多大？ (高/中/低)
- **工作量**: 償還這個債務需要多少時間？ (高/中/低)
- **緊急性**: 如果不處理，會有什麼後果？ (風險評估)

**評估範例**：
```
Team 討論 TD-001 (UserService.js 800 行):
- PM (Victoria): "影響新功能開發速度，每次改動都很擔心破壞既有功能"
- Dev (David): "我估計需要 2-3 天重構，拆分成 AuthService, ProfileService, NotificationService"
- SD (Marcus): "這是核心模組，建議優先處理"
→ 評估為 P0 (高影響、中工作量 → 分階段償還)
```

---

**3. 規劃 (Planning)** - 併入 Sprint Backlog

**償還策略**：
- **P0 (Critical Debt)**: 每個 Sprint 預留 **20%** 時間償還 (例: 10 天 Sprint → 2 天處理技術債務)
- **P1 (Quick Wins)**: 下個 Sprint 立即處理
- **P2/P3**: 視 Sprint 容量決定是否處理

**Sprint Backlog 範例** (包含技術債務):

| 類型 | 任務 | Story Points | 負責人 |
|------|------|-------------|--------|
| 功能開發 | F-009 金流整合 | 8 SP | David |
| 功能開發 | F-010 房東後台 | 5 SP | Alice |
| **技術債務** | **TD-001 重構 UserService** | **5 SP** | **David** |
| **技術債務** | **TD-005 優化房源列表 API** | **3 SP** | **Bob** |
| Bug 修復 | BUG-015 修正登入錯誤訊息 | 1 SP | Charlie |

**總 SP**: 22 SP (其中技術債務佔 8 SP ≈ 36%)

---

**4. 償還 (Repayment)** - 執行技術債務工作

**償還執行**：
- 將技術債務視為正式的 User Story，納入 Sprint Backlog
- Code Review 時特別檢查債務是否真正解決
- 更新技術債務追蹤表狀態

**償還範例**：
```
TD-001 重構 UserService (David 執行):
1. 拆分為 AuthService, ProfileService, NotificationService
2. 撰寫單元測試 (覆蓋率 > 80%)
3. 更新相關文檔
4. Code Review (由 Marcus 審查)
5. 合併到主分支
→ 更新 TD-001 狀態為 ✅ Done
```

---

**5. 追蹤 (Tracking)** - 定期檢視債務狀況

**追蹤時機**：
- **每週**: Dev Lead 檢視技術債務清單
- **每個 Sprint**: Sprint Planning 時評估是否償還
- **每季**: 技術債務回顧會議 (Tech Debt Review)

**追蹤指標**：
- **總債務數量**: 新增 vs 償還 (目標: 償還數量 ≥ 新增數量)
- **P0 債務數量**: Critical 債務應優先償還 (目標: P0 < 5 個)
- **債務平均年齡**: 債務存在時間 (目標: < 2 個月)
- **償還率**: 每個 Sprint 償還的債務數量 (目標: 2-3 個/Sprint)

**Dashboard 範例**：

```
技術債務儀表板 (2025-12-29)

總債務數量: 12 個
├─ P0 (Critical): 3 個 ⚠️
├─ P1 (High-Value): 5 個
├─ P2 (Low-Value): 2 個
└─ P3 (Minor): 2 個

本月償還: 4 個 ✅
本月新增: 3 個 📈
淨減少: 1 個 ✅

平均年齡: 3.2 週
最老債務: TD-006 (React Router v5) - 19 週 ⚠️
```

---

##### 📋 技術債務完整範例

**專案**: 民宿訂房平台 (B&B Booking Platform)

**Sprint**: Sprint 3 (2025-12-29 ~ 2026-01-12)

**技術債務清單**:

| Debt ID | 類型 | 描述 | 影響 | 工作量 | 優先級 | 負責人 | 記錄日期 | 目標償還時間 | 狀態 |
|---------|------|------|------|--------|--------|--------|---------|------------|------|
| **TD-001** | Code Quality | `UserService.js` 單一檔案 800 行 | 高 | 中 (3 天) | **P0** | David | 2025-12-20 | **Sprint 3** | **🔄 In Progress** |
| **TD-002** | Test Debt | 支付模組缺乏單元測試 | 高 | 高 (5 天) | **P0** | Quincy | 2025-12-22 | Sprint 3-4 | ⏳ Planned |
| **TD-003** | Documentation | API 文檔不一致 (20 端點) | 高 | 低 (1 天) | **P1** | David | 2025-12-15 | **Sprint 3 Week 1** | **✅ Done** |
| **TD-005** | Performance | 房源列表 API 3.5s → 目標 < 500ms | 高 | 中 (2 天) | **P0** | Bob | 2025-12-25 | **Sprint 3** | **✅ Done** |
| **TD-007** | Infrastructure | 手動部署 (30 分鐘) | 中 | 低 (1 天) | **P1** | Marcus | 2025-12-12 | **Sprint 3** | **✅ Done** |

---

**Sprint 3 償還計畫**：

**總 SP**: 25 SP
**技術債務 SP**: 8 SP (32% - 符合 20-40% 建議範圍)

| 任務 | SP | 負責人 | 狀態 |
|------|------|--------|------|
| F-011 即時聊天功能 | 13 SP | Alice + Bob | 🔄 In Progress |
| F-012 App 推播通知 | 4 SP | Charlie | ⏳ Planned |
| **TD-001 重構 UserService** | **5 SP** | **David** | **🔄 In Progress** |
| **TD-003 補齊 API 文檔** | **2 SP** | **David** | **✅ Done** |
| **TD-007 建立 CI/CD Pipeline** | **1 SP** | **Marcus** | **✅ Done** |

---

**償還執行細節**：

**TD-003: 補齊 API 文檔** (已完成 ✅)
- **執行人**: David
- **完成時間**: 2025-12-30 (Sprint 3 Day 2)
- **工作內容**:
  1. 導入 Swagger/OpenAPI
  2. 補齊 20 個 API 端點文檔
  3. 建立 API Index 文檔
- **驗收標準**: ✅ 80% API 有完整文檔 (實際達成 95%)
- **效果**: 前後端協作效率提升，減少溝通成本

**TD-007: 建立 CI/CD Pipeline** (已完成 ✅)
- **執行人**: Marcus
- **完成時間**: 2026-01-03 (Sprint 3 Day 5)
- **工作內容**:
  1. 設定 GitHub Actions
  2. 建立自動測試 + 自動部署流程
  3. 設定 Staging/Production 環境
- **驗收標準**: ✅ 部署時間從 30 分鐘降至 5 分鐘
- **效果**: 部署效率提升 6 倍，減少人為錯誤

**TD-001: 重構 UserService** (進行中 🔄)
- **執行人**: David
- **預計完成**: 2026-01-08 (Sprint 3 Day 10)
- **工作內容**:
  1. 拆分為 AuthService, ProfileService, NotificationService
  2. 撰寫單元測試 (目標覆蓋率 80%)
  3. 更新相關文檔
- **目前進度**: 70% (已完成拆分，正在撰寫測試)

---

##### ⚠️ 技術債務管理常見問題

**問題 1: 技術債務越積越多，永遠還不完**
- **原因**: 每個 Sprint 都專注於新功能，沒有預留償還時間
- **解決方案**: 強制每個 Sprint 預留 **10-20% 時間**償還技術債務

**問題 2: 開發者不願意登記技術債務**
- **原因**: 擔心被視為「寫出爛 code」
- **解決方案**:
  - 建立 No Blame Culture，技術債務是團隊共同責任
  - 獎勵主動識別和償還技術債務的行為

**問題 3: PM 不願意排技術債務，只想要新功能**
- **原因**: 技術債務對業務價值不明顯
- **解決方案**:
  - 量化技術債務的成本 (例: "因為 UserService 過於複雜，每次新功能開發多花 2 天")
  - 展示技術債務對使用者體驗的影響 (例: "API 回應時間 3.5s 導致使用者流失")

**問題 4: 技術債務清單變成垃圾場，充滿過時的債務**
- **原因**: 缺乏定期清理機制
- **解決方案**:
  - 每季進行技術債務大掃除 (Tech Debt Spring Cleaning)
  - 超過 3 個月未處理的 P2/P3 債務，考慮關閉或降級

---

##### 📊 技術債務成效指標

**短期指標** (每個 Sprint):
- ✅ 技術債務償還數量 ≥ 2 個/Sprint
- ✅ P0 技術債務數量 < 5 個
- ✅ Sprint 容量的 10-20% 用於償還技術債務

**長期指標** (每季/每半年):
- ✅ 程式碼品質分數提升 (SonarQube Score)
- ✅ 測試覆蓋率提升 (目標 > 80%)
- ✅ CI/CD Pipeline 成功率 > 95%
- ✅ 新功能開發速度提升 (Velocity 穩定或提升)
- ✅ Bug 數量減少 (特別是 Production Bug)

---

**📝 技術債務追蹤表格 Template 位置**: `checklists/Tech_Debt_Register_Template.md` 🚧 (v0.01+ 預留)

**📊 技術債務儀表板範例**: `checklists/Tech_Debt_Dashboard_Example.md` 🚧 (v0.01+ 預留)

---

### 階段 8：開發準備 (1-2 天)

> 🤖 **Agent 參與角色** - Dev + QA 主導階段
>
> **活躍 Agents**: PM/PO (Victoria), Dev (David), QA (Quincy)
>
> **協作模式**:
> - **PM/PO (Victoria)**: 需求變更決策、開發優先級確認
> - **Dev (David)**: 開發實作主導、開發規範制定、環境建置
> - **QA (Quincy)**: 測試執行、缺陷追蹤、測試環境建置
>
> **主要產出**: 開發環境、CI/CD Pipeline、Coding Standards、測試環境

> **🔒 CI/CD 強制要求 (v0.01 CI/CD 強化)**
>
> CI/CD Pipeline 配置**必須包含 Layer 0 + Layer 1**：
>
> **Layer 0 — Security Baseline（安全基線）**:
> - 🔴 **Secret Detection**: Pre-commit Hook + CI Pipeline 機密偵測
> - 🔴 **Dependency Scan (SCA)**: 依賴漏洞掃描（Critical/High 阻塞 PR）
> - 🔴 **License Compliance**: 開源授權合規檢查
>
> **Layer 1 — Build & Verify（建置驗證）**:
> - 🔴 **Lint + Format Check**: 程式碼風格一致性驗證
> - 🔴 **Compile / Build**: 編譯成功、依賴正確安裝
> - 🔴 **Unit Test + Coverage Gate**: 單元測試通過、覆蓋率 ≥ 80%
>
> **增強安全掃描（Standard 等級）**:
> - 🔴 **SAST**: Semgrep / CodeQL 靜態程式碼安全分析（Critical/High 阻塞）
> - ⚠️ **Container Scan**: 有 Docker 時啟用 Trivy 映像掃描
>
> 📖 **Layer 0 指南**: [Layer0_Security_Baseline_Template.md](../../docs_template/scenario_specific/devops/Layer0_Security_Baseline_Template.md)
> 📖 **Layer 1 指南**: [Layer1_Build_Verify_Template.md](../../docs_template/scenario_specific/devops/Layer1_Build_Verify_Template.md)
> 📖 **安全掃描整合**: [Security_Scan_Integration_Template.md](../../docs_template/scenario_specific/devops/Security_Scan_Integration_Template.md)
> 📋 **完整流程**: 參考 [devops-setup-flow.md](../../workflow/scenario-specific/devops-setup-flow.md) 步驟 0 ~ 0.10
>
> **⚡ Performance Benchmark Gate（⚠️ 選配）**:
> - ⚠️ **Micro-Benchmark**: PR 階段效能退化偵測（退化 > 10% 阻塞，< 2 分鐘）
> - 📖 **配置範本**: [Performance_Benchmark_Gate_Template.md](../../docs_template/scenario_specific/devops/Performance_Benchmark_Gate_Template.md)
>
> **📝 Documentation Pipeline（⚠️ 選配）**:
> - ⚠️ **Doc Lint + Link Check**: PR 階段文檔品質檢查
> - 📖 **配置範本**: [Documentation_Pipeline_Template.md](../../docs_template/scenario_specific/devops/Documentation_Pipeline_Template.md)
>
> **🔔 Event-Driven Agent Notification（🔴 強制）**:
> - 🔴 **PR 事件通知**: PR 建立/更新 → Agent 結果匯聚 → PR Comment + Slack
> - 🔴 **部署通知**: Staging/Production 部署 → 全員通知
> - 📖 **配置範本**: [Event_Driven_Agent_Notification_Template.md](../../docs_template/scenario_specific/devops/Event_Driven_Agent_Notification_Template.md)
>
> 🆕 **多模組/多領域 CI/CD 策略提示**（多業務領域系統適用）:
>
> 若系統包含多個領域模組（如 shop-service, stay-service, shared-service），CI/CD Pipeline 需決定：
>
> | 策略 | 適用架構 | Pipeline 設計 | 優缺點 |
> |------|---------|-------------|--------|
> | **Mono-repo 統一 Pipeline** | Monolith / Modular Monolith | 一個 Pipeline 統一建置所有模組 | ✅ 簡單統一；❌ 任一模組修改觸發全量建置 |
> | **Mono-repo 模組觸發** | Mono-repo + 模組化 | 偵測變更檔案路徑，只建置受影響模組 | ✅ 精準建置；❌ 需維護路徑觸發規則 |
> | **Multi-repo 獨立 Pipeline** | 微服務架構 | 每個服務 repo 有獨立 Pipeline | ✅ 完全獨立；❌ 跨服務整合測試複雜 |
>
> **建議**：
> - 初期（MVP）使用 Mono-repo 統一 Pipeline，降低複雜度
> - 成長期切換至 Mono-repo 模組觸發，提升建置效率
> - 成熟期（若需獨立擴展）再拆分為 Multi-repo

> 🆕 **搜尋索引部署與同步策略**（適用於使用 Elasticsearch/Meilisearch 的系統）:
>
> **索引同步方案比較**:
> | 方案 | 原理 | 延遲 | 適用場景 |
> |------|------|------|---------|
> | **同步更新** | 資料庫寫入時同步更新索引 | 即時 | 小型系統、低寫入量 |
> | **訊息佇列（MQ）** | 應用層發送事件至 MQ → Consumer 更新索引 | 秒級 | ✅ **MVP 階段推薦**，解耦性好，基礎設施簡單（RabbitMQ 即可）|
> | **CDC（Change Data Capture）** | 監聽 DB binlog/WAL 自動同步（Debezium + Kafka）| 秒級 | ✅ 成長期推薦，資料一致性高，但需維護 Kafka + ZooKeeper |
> | **定時批次** | Cron Job 定期全量/增量同步 | 分鐘級 | 搜尋即時性要求低 |
>
> **⚠️ 漸進式升級建議**（避免 MVP 過度設計）：
> - **Phase 1（MVP）**：使用「訊息佇列（RabbitMQ）」方案，基礎設施簡單，維運成本低
> - **Phase 2（成長期）**：若搜尋更新量 > 1,000 次/秒或需要精確一致性，才升級至 CDC（Kafka + Debezium）
> - **原因**：CDC 方案需額外維護 Kafka（ZooKeeper/KRaft）+ Debezium Connector，對小型團隊 MVP 成本過高
>
> **CI/CD 索引管理**:
> - 索引 Schema 變更需版本化管理（如 `index_v1`, `index_v2`）
> - 使用索引別名（Alias）實現零停機切換：`articles_current` → `articles_v2`
> - CI Pipeline 增加「索引相容性檢查」步驟：新版應用是否與現有索引相容
> - 部署流程：建立新索引 → 資料遷移 → 切換別名 → 驗證 → 刪除舊索引

> 🆕 **CDN 快取管理策略**（適用於面向公眾的 Web 系統）:
>
> **快取分層策略**:
> | 資源類型 | Cache-Control 設定 | 說明 |
> |---------|-------------------|------|
> | HTML 頁面 | `no-cache` 或 `max-age=60` | 確保內容更新即時可見 |
> | JS/CSS（含 hash） | `max-age=31536000, immutable` | 檔名含 hash，永久快取 |
> | 圖片/媒體 | `max-age=86400` (1 天) | 平衡快取與更新頻率 |
> | API 回應 | `no-store` 或 `max-age=0` | 動態資料不快取 |
>
> **部署時 CDN 操作**:
> - 發布前：預熱關鍵頁面（首頁、熱門文章）
> - 發布後：清除 HTML 快取（保留含 hash 的靜態資源）
> - 緊急修復：全量清除（`/*` invalidation）
> - CI/CD 整合：部署腳本自動調用 CDN API 清除快取

> **⚠️ 階段 7 與階段 8 的並行協調說明**
>
> 階段 8 (開發準備) 可與階段 7 (Sprint 規劃) 並行執行，但需明確任務分工：
>
> **可並行執行的任務**:
> - ✅ 階段 7: PM/PO + SA 進行 Sprint 規劃 (人力資源規劃、時間線制定)
> - ✅ 階段 8: SD + Dev 進行技術準備 (環境建置、CI/CD 配置)
> - **前提**: FRD/SRD/API Spec 已確認完成
>
> **必須順序執行的任務**:
> - ❌ 階段 7 的「Sprint Backlog 最終確認」必須等階段 8 的「環境驗證」完成
> - ❌ 階段 9 的「團隊 Kickoff」必須等階段 7 + 8 都完成
>
> **協調機制**:
> - 每日同步會議 (15 分鐘) 確認進度和依賴
> - 使用共享文檔記錄完成狀態
> - 遇到阻礙立即通知相關人員
>
> 📋 **並行執行參考**: [Parallel_Execution_Guide.md](Parallel_Execution_Guide.md)

> 🆕 **多語言技術棧 CI/CD 統一規範指引**（適用於包含 Java + TypeScript + Kotlin + Swift 的多語言專案）:
>
> 當系統同時包含多種語言（如本框架的企業級四域融合系統），CI/CD Pipeline 的 Layer 0/1 工具需分語言配置：
>
> | 語言/平台 | Layer 0 安全基線 | Layer 1 建置驗證 | 覆蓋率工具 |
> |----------|----------------|----------------|----------|
> | **Java/Spring Boot** | OWASP Dependency Check + git-secrets | Checkstyle + `./gradlew build` | JaCoCo（目標 ≥ 80%）|
> | **TypeScript/Next.js** | npm audit + Gitleaks | ESLint + `npm run build` | Jest Coverage（目標 ≥ 80%）|
> | **Kotlin/Android** (Phase 2) | OWASP Dependency Check + Android Lint | `./gradlew assembleDebug` + Android Lint | JaCoCo（目標 ≥ 70%）|
> | **Swift/macOS** (Phase 2) | `swift package audit` | `swift build` / `xcodebuild` | Xcode Code Coverage（目標 ≥ 70%）|
>
> **CI Pipeline 觸發策略（Mono-repo 多模組觸發）**：
> ```yaml
> # .github/workflows/backend.yml - 只在 backend/ 有變更時觸發
> on:
>   push:
>     paths:
>       - 'backend/**'
>       - '.github/workflows/backend.yml'
>
> # .github/workflows/frontend.yml
> on:
>   push:
>     paths:
>       - 'frontend/**'
>
> # .github/workflows/shared.yml - 共用程式碼變更觸發全量建置
> on:
>   push:
>     paths:
>       - 'shared/**'  # 任何共用模組變更 → 觸發所有 Pipeline
> ```
>
> **推薦工具對照表（減少重複工具引入）**：
> - Secret Detection：**Gitleaks**（統一支援所有語言，pre-commit hook）
> - License Compliance：**FOSSA**（支援 Java + TypeScript + Kotlin + Swift）
> - SAST：**SonarQube Community**（Java/TypeScript）+ **Semgrep**（多語言規則）

#### 步驟 8.1：開發規範制定
```
執行指令：
「請制定開發規範和最佳實踐指南」
```

系統會生成：
- Coding Standards
- Git Workflow
- Code Review Guidelines
- Testing Standards
- Documentation Standards

---

**🔍 步驟 8.1.1：Testing Standards 詳細規範** 🔴 **v0.01 新增**

> **重要性說明**:
> 測試覆蓋率直接影響產品品質與長期維護成本。明確的測試標準可確保團隊一致性，
> 避免「過度測試」或「測試不足」的問題。

##### 1. 測試覆蓋率目標

**基礎覆蓋率要求**

| 測試類型 | 最低覆蓋率 | 建議覆蓋率 | 優秀覆蓋率 | 適用範圍 |
|---------|-----------|-----------|-----------|---------|
| **單元測試 (Unit Test)** | 70% | 80% | 90%+ | 所有業務邏輯、工具函式、服務層 |
| **整合測試 (Integration Test)** | 50% | 60% | 75%+ | API 端點、資料庫互動、第三方服務整合 |
| **E2E 測試 (End-to-End Test)** | 30% | 40% | 60%+ | 關鍵使用者流程、核心業務場景 |

**覆蓋率計算方式**:
- **單元測試**: Line Coverage（行覆蓋率）或 Branch Coverage（分支覆蓋率）
- **整合測試**: API Endpoint Coverage（API 端點覆蓋率）
- **E2E 測試**: User Journey Coverage（使用者旅程覆蓋率）

##### 2. 測試金字塔策略

```
                  ┌─────────────┐
                  │  E2E Tests  │  ← 少量（10-20 個關鍵流程）
                  │    30-40%   │
                ┌─┴─────────────┴─┐
                │ Integration Tests│ ← 中量（50-100 個 API/模組）
                │      50-60%      │
             ┌──┴──────────────────┴──┐
             │     Unit Tests          │ ← 大量（數百至數千個測試）
             │        70-90%           │
             └─────────────────────────┘
```

**測試比例建議**:
- **Unit Tests**: 70% 的測試數量（快速、易維護、高穩定性）
- **Integration Tests**: 20% 的測試數量（中等速度、中等維護成本）
- **E2E Tests**: 10% 的測試數量（慢速、高維護成本、易受環境影響）

**反模式警告** ❌:
- ❌ **冰淇淋錐模式（Anti-Pattern）**: E2E 測試過多（> 50%），導致測試緩慢、易失敗
- ❌ **沙漏模式（Anti-Pattern）**: 缺少整合測試，單元測試與 E2E 測試無法有效銜接

##### 3. 各測試類型詳細標準

**3.1 單元測試 (Unit Test)** 🔴

**定義**: 測試單一函式、類別或模組的最小可測試單元

**強制覆蓋範圍**:
| 項目 | 覆蓋率要求 | 說明 |
|------|-----------|------|
| **業務邏輯函式** | ≥ 90% | 計算、驗證、轉換邏輯必須完整測試 |
| **工具函式 (Utils)** | ≥ 85% | 日期處理、字串處理、數學運算等 |
| **Service 層** | ≥ 80% | 業務邏輯服務（不含 I/O 操作） |
| **Controller/Presenter** | ≥ 70% | 輸入驗證、錯誤處理 |
| **UI Components** | ≥ 60% | 核心業務組件（非純展示組件） |

**測試範例**:
```typescript
// ✅ 良好的單元測試範例

describe('calculateDiscount', () => {
  test('should apply 10% discount for orders over $100', () => {
    const result = calculateDiscount(150, 'DISCOUNT10');
    expect(result).toBe(135); // 150 * 0.9
  });

  test('should return original price if discount code is invalid', () => {
    const result = calculateDiscount(150, 'INVALID');
    expect(result).toBe(150);
  });

  test('should throw error if price is negative', () => {
    expect(() => calculateDiscount(-10, 'DISCOUNT10')).toThrow('Invalid price');
  });

  test('should handle zero price', () => {
    const result = calculateDiscount(0, 'DISCOUNT10');
    expect(result).toBe(0);
  });
});
```

**最佳實踐**:
- ✅ 每個函式至少包含 3-5 個測試案例（正常情境、邊界條件、錯誤處理）
- ✅ 測試名稱清楚描述測試目的（使用 `should` 或 `when...then` 格式）
- ✅ 單一測試只驗證一個行為（Single Assertion Principle）
- ✅ 使用 Mock/Stub 隔離外部依賴（資料庫、API、時間）
- ✅ 測試執行時間 < 5 秒（整體單元測試套件）

**覆蓋率工具**:
- JavaScript/TypeScript: Jest (內建覆蓋率報告)
- Python: pytest + coverage.py
- Java: JUnit + JaCoCo
- Go: go test -cover

---

**3.2 整合測試 (Integration Test)** 🔴

**定義**: 測試多個模組或系統間的互動（API、資料庫、第三方服務）

**強制覆蓋範圍**:
| 項目 | 覆蓋率要求 | 說明 |
|------|-----------|------|
| **API 端點** | 100% | 所有 REST/GraphQL 端點必須測試 |
| **資料庫操作** | ≥ 80% | CRUD 操作、事務處理、資料驗證 |
| **第三方服務整合** | ≥ 70% | 支付、Email、簡訊、雲端服務 |
| **訊息佇列** | ≥ 60% | RabbitMQ、Kafka、Redis Pub/Sub |
| **檔案系統操作** | ≥ 60% | 上傳、下載、儲存 |

**測試範例**:
```typescript
// ✅ 良好的整合測試範例（API 測試）

describe('POST /api/orders', () => {
  test('should create order and return 201', async () => {
    const response = await request(app)
      .post('/api/orders')
      .send({
        userId: 123,
        items: [{ productId: 456, quantity: 2 }],
        totalAmount: 50.00
      })
      .set('Authorization', 'Bearer valid-token');

    expect(response.status).toBe(201);
    expect(response.body).toHaveProperty('orderId');
    expect(response.body.status).toBe('pending');

    // 驗證資料庫寫入
    const order = await db.orders.findById(response.body.orderId);
    expect(order.userId).toBe(123);
    expect(order.items.length).toBe(1);
  });

  test('should return 400 when items array is empty', async () => {
    const response = await request(app)
      .post('/api/orders')
      .send({ userId: 123, items: [], totalAmount: 0 })
      .set('Authorization', 'Bearer valid-token');

    expect(response.status).toBe(400);
    expect(response.body.error).toContain('items cannot be empty');
  });

  test('should return 401 when authorization token is missing', async () => {
    const response = await request(app)
      .post('/api/orders')
      .send({ userId: 123, items: [{ productId: 456, quantity: 2 }] });

    expect(response.status).toBe(401);
  });
});
```

**最佳實踐**:
- ✅ 使用測試資料庫（Docker + Testcontainers）
- ✅ 每個測試獨立（Test Isolation）：前置準備 → 執行 → 清理
- ✅ Mock 外部服務（支付、Email），使用 Test Doubles
- ✅ 測試 Happy Path + Error Path（成功與失敗情境）
- ✅ 執行時間 < 30 秒（整體整合測試套件）

**測試環境**:
- 使用 Docker Compose 建立隔離測試環境
- 資料庫使用測試專用 Schema（自動建立/清理）
- 第三方服務使用 Mock Server（如 WireMock、Mockoon）

---

**3.3 E2E 測試 (End-to-End Test)** 🔴

**定義**: 模擬真實使用者操作，測試完整的業務流程

**強制覆蓋範圍**:
| 項目 | 覆蓋率要求 | 說明 |
|------|-----------|------|
| **關鍵使用者流程** | 100% | 註冊、登入、結帳、支付等核心流程 |
| **核心業務場景** | ≥ 60% | 商品瀏覽、購物車、訂單管理 |
| **跨平台一致性** | ≥ 40% | Web/iOS/Android 核心功能 |
| **錯誤處理流程** | ≥ 30% | 支付失敗、網路錯誤、資料驗證失敗 |

**關鍵使用者流程範例**（電商專案）:

| 流程 ID | 流程名稱 | 測試步驟 | 預期結果 | 優先級 |
|---------|---------|---------|---------|--------|
| **E2E-001** | 使用者註冊 | 1. 開啟註冊頁面<br/>2. 填寫 Email/密碼<br/>3. 驗證 Email | 註冊成功，收到驗證信 | P0 |
| **E2E-002** | 使用者登入 | 1. 開啟登入頁面<br/>2. 輸入正確帳密<br/>3. 點擊登入 | 登入成功，導向首頁 | P0 |
| **E2E-003** | 商品購買流程 | 1. 瀏覽商品<br/>2. 加入購物車<br/>3. 結帳<br/>4. 選擇配送方式<br/>5. 填寫付款資訊<br/>6. 完成付款 | 訂單建立成功，收到確認 Email | P0 |
| **E2E-004** | 訂單查詢 | 1. 登入<br/>2. 進入「我的訂單」<br/>3. 查看訂單詳情 | 顯示正確的訂單資訊與狀態 | P1 |
| **E2E-005** | 忘記密碼 | 1. 點擊「忘記密碼」<br/>2. 輸入 Email<br/>3. 收到驗證碼<br/>4. 重設密碼 | 密碼重設成功，可用新密碼登入 | P1 |

**測試範例**:
```typescript
// ✅ 良好的 E2E 測試範例（使用 Playwright）

test('Complete checkout flow', async ({ page }) => {
  // 步驟 1: 登入
  await page.goto('https://example.com/login');
  await page.fill('[data-testid="email"]', 'test@example.com');
  await page.fill('[data-testid="password"]', 'Test@1234');
  await page.click('[data-testid="login-button"]');
  await expect(page).toHaveURL('https://example.com/dashboard');

  // 步驟 2: 瀏覽商品並加入購物車
  await page.goto('https://example.com/products/123');
  await page.click('[data-testid="add-to-cart"]');
  await expect(page.locator('[data-testid="cart-count"]')).toHaveText('1');

  // 步驟 3: 結帳
  await page.click('[data-testid="cart-icon"]');
  await page.click('[data-testid="checkout-button"]');

  // 步驟 4: 填寫配送資訊
  await page.fill('[data-testid="address"]', '123 Test St');
  await page.fill('[data-testid="city"]', 'Test City');
  await page.selectOption('[data-testid="shipping"]', 'standard');
  await page.click('[data-testid="continue-button"]');

  // 步驟 5: 填寫付款資訊（使用測試卡號）
  await page.fill('[data-testid="card-number"]', '4242424242424242');
  await page.fill('[data-testid="expiry"]', '12/25');
  await page.fill('[data-testid="cvv"]', '123');
  await page.click('[data-testid="pay-button"]');

  // 步驟 6: 驗證訂單成功
  await expect(page).toHaveURL(/\/orders\/[0-9]+/);
  await expect(page.locator('[data-testid="order-status"]')).toHaveText('Order Confirmed');

  // 步驟 7: 驗證 Email 通知（選填，需整合 Email 測試服務）
  // const email = await mailSlurp.waitForLatestEmail();
  // expect(email.subject).toContain('Order Confirmation');
});
```

**最佳實踐**:
- ✅ 使用 `data-testid` 屬性定位元素（避免依賴 CSS 選擇器）
- ✅ 測試隔離：每個測試使用獨立帳號/資料
- ✅ 使用 Page Object Model（POM）封裝頁面互動
- ✅ 並行執行測試（Playwright 支援 Multi-Browser Parallelism）
- ✅ 截圖與錄影：測試失敗時自動保存
- ✅ 執行時間 < 5 分鐘（整體 E2E 測試套件）

**E2E 測試工具**:
- **Web**: Playwright（推薦）、Cypress、Selenium
- **Mobile**: Appium、Detox、XCUITest/Espresso
- **API**: Postman/Newman、REST Assured

---

##### 4. 測試覆蓋率監控與報告

**4.1 覆蓋率報告自動化**

**CI/CD 整合**:
```yaml
# GitHub Actions 範例
name: Test Coverage

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      # 執行測試並生成覆蓋率報告
      - name: Run Unit Tests
        run: npm run test:coverage

      - name: Run Integration Tests
        run: npm run test:integration

      # 上傳覆蓋率報告至 Codecov
      - name: Upload Coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          token: ${{ secrets.CODECOV_TOKEN }}
          files: ./coverage/lcov.info
          fail_ci_if_error: true

      # 檢查覆蓋率閾值
      - name: Coverage Threshold Check
        run: |
          COVERAGE=$(cat coverage/coverage-summary.json | jq '.total.lines.pct')
          if (( $(echo "$COVERAGE < 80" | bc -l) )); then
            echo "Coverage $COVERAGE% is below threshold 80%"
            exit 1
          fi
```

**4.2 覆蓋率趨勢追蹤**

| 週期 | 檢查項目 | 目標 | 處理方式 |
|------|---------|------|---------|
| **每次 PR** | 覆蓋率不可下降 | 維持或提升 | PR 阻擋（CI 失敗） |
| **每週** | 覆蓋率趨勢圖 | 穩定上升 | Team Meeting 回顧 |
| **每月** | 各模組覆蓋率分析 | 找出低覆蓋率模組 | 規劃改善計畫 |
| **每季** | 測試品質評估 | 減少 Flaky Tests | 重構測試程式碼 |

**4.3 覆蓋率報告範本**

```markdown
# 測試覆蓋率報告

**專案**: E-Commerce Platform
**日期**: 2025-11-21
**版本**: v1.5.0

## 整體覆蓋率

| 測試類型 | 覆蓋率 | 目標 | 狀態 |
|---------|--------|------|------|
| 單元測試 | 85.3% | 80% | ✅ 達標 |
| 整合測試 | 62.1% | 60% | ✅ 達標 |
| E2E 測試 | 38.7% | 40% | ⚠️ 略低 |

## 模組覆蓋率分析

| 模組 | 單元測試 | 整合測試 | 改善建議 |
|------|---------|---------|---------|
| Auth Module | 92% | 75% | ✅ 優秀 |
| Payment Module | 88% | 70% | ✅ 良好 |
| Order Module | 78% | 55% | ⚠️ 需加強整合測試 |
| Product Module | 65% | 50% | ❌ 需優先改善 |

## 改善行動計畫

1. **Product Module**: 本週內補充 10 個單元測試（預計提升至 75%）
2. **E2E Tests**: 下週新增 3 個關鍵流程測試（預計提升至 42%）
3. **Code Review**: 強化測試覆蓋率檢查（PR 必須包含測試）
```

---

##### 5. 測試覆蓋率的例外情況

**不需強制測試的程式碼** ✅:
- 純展示型 UI 組件（無業務邏輯）
- 自動生成的程式碼（Swagger、Prisma Schema）
- 第三方套件的 Wrapper（已有測試）
- 簡單的 Getter/Setter（無邏輯）
- 設定檔案（config.ts, constants.ts）

**使用覆蓋率排除**:
```javascript
// Jest 設定範例
module.exports = {
  coveragePathIgnorePatterns: [
    '/node_modules/',
    '/dist/',
    '/__tests__/',
    '/coverage/',
    '\\.config\\.ts$',
    '\\.constants\\.ts$'
  ]
};
```

---

##### 6. 測試品質指標（補充覆蓋率）

**除了覆蓋率，還需追蹤**:

| 指標 | 目標值 | 說明 |
|------|--------|------|
| **Flaky Test Rate** | < 2% | 不穩定測試比例（偶爾失敗的測試） |
| **Test Execution Time** | < 5 分鐘 | 完整測試套件執行時間 |
| **Bug Escape Rate** | < 5% | 測試未捕捉的 Bug 比例 |
| **Mutation Test Score** | > 70% | 突變測試分數（測試品質指標） |

---

##### 7. 測試覆蓋率的漸進式達成計畫

**新專案（Greenfield）**:
- **第 1 個月**: 單元測試 ≥ 60%、整合測試 ≥ 40%、E2E 測試 ≥ 20%
- **第 2-3 個月**: 單元測試 ≥ 75%、整合測試 ≥ 50%、E2E 測試 ≥ 30%
- **第 4 個月起**: 達成目標覆蓋率（單元 ≥ 80%、整合 ≥ 60%、E2E ≥ 40%）

**既有專案（Brownfield）**:
- **第 1 季**: 優先測試核心模組（支付、訂單、會員）
- **第 2 季**: 補足次要模組測試
- **第 3 季**: 達成整體覆蓋率目標

**測試覆蓋率納入 Definition of Done (DoD)**:
- ✅ 新功能必須包含單元測試（覆蓋率 ≥ 80%）
- ✅ API 變更必須包含整合測試
- ✅ 關鍵功能必須包含 E2E 測試
- ✅ 所有測試必須通過（無 Flaky Tests）

---

**📋 相關工具與資源**:
- **覆蓋率工具**: Jest (JS/TS), coverage.py (Python), JaCoCo (Java), simplecov (Ruby)
- **E2E 工具**: Playwright, Cypress, Selenium
- **測試報告**: Codecov, Coveralls, SonarQube
- **參考文檔**: [Code_Review_Guidelines.md](../../guides/user/process/Code_Review_Guidelines.md)

---

#### 步驟 8.2：環境與工具設定

> 🔧 **建議 Skill**: `/devops-github-actions`（CI/CD Pipeline）、`/devops-docker`（容器化配置）
> 🆕 **依專案需求選用的 Skill**（SOP Skill 對照表 line 236-244 列出，此處提醒常用項目）:
> - `/integration-redis` — 若專案需要快取策略（Session、API 回應快取、佇列）
> - `/integration-stripe` — 若專案涉及電商支付整合（結帳流程、Webhook、訂閱管理）
> - `/integration-database` — 若專案需 ORM 配置（Prisma/Spring Data JPA）
> - `/devops-monitoring` — 若專案需要 Prometheus/Grafana 監控告警
> - `/devops-kubernetes` — 若部署目標為 Kubernetes 集群

- 開發環境 Setup 指南
- CI/CD Pipeline 配置
- 測試環境建置
- 監控和日誌設定
- 專案管理工具整合 (Jira/Linear)

**產出文件**：
- Developer Setup Guide
- CI/CD Configuration
- Team Collaboration Guidelines

---

**🔍 步驟 8.2.1：CI/CD Pipeline 標準配置** 🔴 **v0.01 新增**

> **重要性說明**:
> CI/CD Pipeline 是確保程式碼品質與自動化部署的關鍵基礎設施。
> 明確的 Pipeline Stage 定義可確保團隊一致性，避免配置差異導致的品質問題。

##### 1. CI/CD Pipeline 必要 Stage 定義

**標準 Pipeline 包含 9 個必要 Stage**

| Stage | 目的 | 執行內容 | 失敗處理 | 執行時間 |
|-------|------|---------|---------|---------|
| **1. lint** | 程式碼風格檢查 | ESLint, Prettier, 靜態分析 | 阻擋 (Block) | 30 秒 - 1 分鐘 |
| **2. test** | 單元測試 + 覆蓋率 | Jest/Mocha 單元測試，覆蓋率檢查 | 阻擋 (Block) | 2-5 分鐘 |
| **3. security** | 安全掃描 (SAST) | 依賴掃描 (npm audit), SAST 工具 | 警告 (Warn) 或阻擋 | 2-3 分鐘 |
| **4. build** | 應用程式建置 | 編譯、打包、建立 Docker Image | 阻擋 (Block) | 3-5 分鐘 |
| **5. deploy-dev** | 部署到開發環境 | 自動部署至 Dev 環境 | 警告 (Warn) | 2-3 分鐘 |
| **6. integration** | 整合測試 | API 測試、資料庫整合測試 | 阻擋 (Block) | 5-10 分鐘 |
| **7. deploy-staging** | 部署到測試環境 | 自動部署至 Staging 環境 | 警告 (Warn) | 2-3 分鐘 |
| **8. e2e** | E2E 測試 | Playwright/Cypress E2E 測試 | 阻擋 (Block) | 5-10 分鐘 |
| **9. deploy-prod** | 部署到生產環境 | 手動審批 + 自動部署至 Prod | 需人工審批 | 3-5 分鐘 |

**總執行時間**: 約 25-45 分鐘（完整 Pipeline）

---

##### 2. GitHub Actions 標準範本

**2.1 完整 CI/CD Pipeline 配置**

```yaml
# .github/workflows/ci-cd-pipeline.yml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

env:
  NODE_VERSION: '20.x'
  DOCKER_REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  # ========================================
  # Stage 1: Lint - 程式碼風格檢查
  # ========================================
  lint:
    name: 'Stage 1: Lint'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: 'npm'

      - name: Install Dependencies
        run: npm ci

      - name: Run ESLint
        run: npm run lint

      - name: Run Prettier Check
        run: npm run format:check

  # ========================================
  # Stage 2: Test - 單元測試 + 覆蓋率
  # ========================================
  test:
    name: 'Stage 2: Unit Tests'
    runs-on: ubuntu-latest
    needs: lint
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: 'npm'

      - name: Install Dependencies
        run: npm ci

      - name: Run Unit Tests
        run: npm run test:coverage

      - name: Check Coverage Threshold
        run: |
          COVERAGE=$(cat coverage/coverage-summary.json | jq '.total.lines.pct')
          echo "Coverage: $COVERAGE%"
          if (( $(echo "$COVERAGE < 80" | bc -l) )); then
            echo "❌ Coverage $COVERAGE% is below threshold 80%"
            exit 1
          fi
          echo "✅ Coverage $COVERAGE% meets threshold"

      - name: Upload Coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          token: ${{ secrets.CODECOV_TOKEN }}
          files: ./coverage/lcov.info
          fail_ci_if_error: false

  # ========================================
  # Stage 3: Security - 安全掃描 (SAST)
  # ========================================
  security:
    name: 'Stage 3: Security Scan'
    runs-on: ubuntu-latest
    needs: lint
    permissions:
      security-events: write
    steps:
      - uses: actions/checkout@v4

      - name: Run npm audit
        run: |
          npm audit --audit-level=high || echo "⚠️ Security vulnerabilities found"

      - name: Run Snyk Security Scan
        uses: snyk/actions/node@master
        continue-on-error: true
        env:
          SNYK_TOKEN: ${{ secrets.SNYK_TOKEN }}
        with:
          command: test

      - name: Run Trivy Vulnerability Scanner
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scan-ref: '.'
          format: 'sarif'
          output: 'trivy-results.sarif'

      - name: Upload Trivy Results to GitHub Security
        uses: github/codeql-action/upload-sarif@v2
        with:
          sarif_file: 'trivy-results.sarif'

  # ========================================
  # Stage 4: Build - 建置應用程式
  # ========================================
  build:
    name: 'Stage 4: Build'
    runs-on: ubuntu-latest
    needs: [test, security]
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: 'npm'

      - name: Install Dependencies
        run: npm ci

      - name: Build Application
        run: npm run build

      - name: Upload Build Artifacts
        uses: actions/upload-artifact@v4
        with:
          name: build-artifacts
          path: dist/
          retention-days: 7

      - name: Build Docker Image
        run: |
          docker build -t ${{ env.DOCKER_REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }} .
          docker tag ${{ env.DOCKER_REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }} \
                     ${{ env.DOCKER_REGISTRY }}/${{ env.IMAGE_NAME }}:latest

      - name: Log in to Docker Registry
        if: github.event_name != 'pull_request'
        uses: docker/login-action@v3
        with:
          registry: ${{ env.DOCKER_REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Push Docker Image
        if: github.event_name != 'pull_request'
        run: |
          docker push ${{ env.DOCKER_REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }}
          docker push ${{ env.DOCKER_REGISTRY }}/${{ env.IMAGE_NAME }}:latest

  # ========================================
  # Stage 5: Deploy to Dev - 部署到開發環境
  # ========================================
  deploy-dev:
    name: 'Stage 5: Deploy to Dev'
    runs-on: ubuntu-latest
    needs: build
    if: github.ref == 'refs/heads/develop'
    environment:
      name: development
      url: https://dev.example.com
    steps:
      - name: Deploy to Dev Environment
        run: |
          echo "🚀 Deploying to Development Environment..."
          # 使用 kubectl, helm, 或雲端 CLI 工具部署
          # kubectl set image deployment/myapp myapp=${{ env.DOCKER_REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }}

      - name: Wait for Deployment
        run: |
          echo "⏳ Waiting for deployment to stabilize..."
          sleep 30

      - name: Health Check
        run: |
          curl --fail https://dev.example.com/health || exit 1

  # ========================================
  # Stage 6: Integration Tests - 整合測試
  # ========================================
  integration:
    name: 'Stage 6: Integration Tests'
    runs-on: ubuntu-latest
    needs: deploy-dev
    if: github.ref == 'refs/heads/develop'
    services:
      postgres:
        image: postgres:18
        env:
          POSTGRES_PASSWORD: test
          POSTGRES_DB: test_db
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}

      - name: Install Dependencies
        run: npm ci

      - name: Run Integration Tests
        run: npm run test:integration
        env:
          DATABASE_URL: postgresql://postgres:test@localhost:5432/test_db
          API_URL: https://dev.example.com

  # ========================================
  # Stage 7: Deploy to Staging - 部署到測試環境
  # ========================================
  deploy-staging:
    name: 'Stage 7: Deploy to Staging'
    runs-on: ubuntu-latest
    needs: integration
    if: github.ref == 'refs/heads/main'
    environment:
      name: staging
      url: https://staging.example.com
    steps:
      - name: Deploy to Staging Environment
        run: |
          echo "🚀 Deploying to Staging Environment..."
          # kubectl set image deployment/myapp myapp=${{ env.DOCKER_REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }}

      - name: Health Check
        run: |
          curl --fail https://staging.example.com/health || exit 1

  # ========================================
  # Stage 8: E2E Tests - E2E 測試
  # ========================================
  e2e:
    name: 'Stage 8: E2E Tests'
    runs-on: ubuntu-latest
    needs: deploy-staging
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}

      - name: Install Dependencies
        run: npm ci

      - name: Install Playwright Browsers
        run: npx playwright install --with-deps

      - name: Run E2E Tests
        run: npm run test:e2e
        env:
          BASE_URL: https://staging.example.com

      - name: Upload E2E Test Results
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: playwright-report
          path: playwright-report/
          retention-days: 7

  # ========================================
  # Stage 9: Deploy to Production - 部署到生產環境
  # ========================================
  deploy-prod:
    name: 'Stage 9: Deploy to Production'
    runs-on: ubuntu-latest
    needs: e2e
    if: github.ref == 'refs/heads/main'
    environment:
      name: production
      url: https://example.com
    steps:
      - name: Manual Approval Required
        run: echo "⚠️ Manual approval required for production deployment"

      - name: Deploy to Production Environment
        run: |
          echo "🚀 Deploying to Production Environment..."
          # kubectl set image deployment/myapp myapp=${{ env.DOCKER_REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }}

      - name: Health Check
        run: |
          curl --fail https://example.com/health || exit 1

      - name: Send Deployment Notification
        run: |
          echo "✅ Production deployment successful!"
          # 發送 Slack/Teams/Discord 通知
```

---

##### 3. GitLab CI 標準範本（參考）

```yaml
# .gitlab-ci.yml
stages:
  - lint
  - test
  - security
  - build
  - deploy-dev
  - integration
  - deploy-staging
  - e2e
  - deploy-prod

variables:
  NODE_VERSION: "20"
  DOCKER_REGISTRY: "registry.gitlab.com"

# Stage 1: Lint
lint:
  stage: lint
  image: node:${NODE_VERSION}
  script:
    - npm ci
    - npm run lint
    - npm run format:check
  cache:
    key: ${CI_COMMIT_REF_SLUG}
    paths:
      - node_modules/

# Stage 2: Test
test:
  stage: test
  image: node:${NODE_VERSION}
  script:
    - npm ci
    - npm run test:coverage
  artifacts:
    reports:
      coverage_report:
        coverage_format: cobertura
        path: coverage/cobertura-coverage.xml
  coverage: '/Lines\s*:\s*(\d+\.\d+)%/'

# Stage 3: Security
security:
  stage: security
  image: node:${NODE_VERSION}
  script:
    - npm audit --audit-level=moderate
  allow_failure: true

# Stage 4: Build
build:
  stage: build
  image: docker:latest
  services:
    - docker:dind
  script:
    - docker build -t ${DOCKER_REGISTRY}/${CI_PROJECT_PATH}:${CI_COMMIT_SHA} .
    - docker push ${DOCKER_REGISTRY}/${CI_PROJECT_PATH}:${CI_COMMIT_SHA}
  only:
    - main
    - develop

# Stage 5-9: Deploy Stages (類似 GitHub Actions)
# ...
```

---

##### 4. CI/CD Pipeline 最佳實踐

**4.1 失敗處理策略**

| Stage | 失敗影響 | 處理方式 |
|-------|---------|---------|
| **lint, test, build** | ❌ 阻擋部署 | CI 失敗，必須修復 |
| **security** | ⚠️ 警告 | 記錄問題，視嚴重程度決定是否阻擋 |
| **integration, e2e** | ❌ 阻擋部署 | 必須修復或回退 |
| **deploy-prod** | 🔴 Critical | 需手動審批，失敗立即回退 |

**4.2 環境變數管理**

使用 GitHub Secrets 或 GitLab CI/CD Variables 管理敏感資訊：

- `CODECOV_TOKEN` - Codecov 上傳 Token
- `SNYK_TOKEN` - Snyk 安全掃描 Token
- `DOCKER_REGISTRY_TOKEN` - Docker Registry 認證
- `DEPLOY_KEY` - 部署金鑰（SSH Key）
- `SLACK_WEBHOOK_URL` - 通知 Webhook

**4.3 快取策略**

```yaml
# GitHub Actions Cache 範例
- name: Cache Node Modules
  uses: actions/cache@v3
  with:
    path: ~/.npm
    key: ${{ runner.os }}-node-${{ hashFiles('**/package-lock.json') }}
    restore-keys: |
      ${{ runner.os }}-node-
```

**4.4 並行執行優化**

```yaml
# 可並行執行的 Stage
jobs:
  lint:
    # ...

  test:
    needs: lint  # 依賴 lint

  security:
    needs: lint  # 可與 test 並行
```

---

##### 5. CI/CD Pipeline 監控與告警

**5.1 Pipeline 執行時間監控**

| 指標 | 目標值 | 處理方式 |
|------|--------|---------|
| **完整 Pipeline 時間** | < 30 分鐘 | 超過時優化瓶頸 Stage |
| **Unit Test 時間** | < 5 分鐘 | 拆分測試、使用並行執行 |
| **E2E Test 時間** | < 10 分鐘 | 減少測試數量、使用並行執行 |
| **Build 時間** | < 5 分鐘 | 使用快取、優化 Dockerfile |

**5.2 Pipeline 成功率監控**

- **目標成功率**: ≥ 95%
- **失敗原因分析**: 每週回顧，找出常見失敗原因
- **Flaky Test 處理**: 識別並修復不穩定測試

**5.3 告警通知設定**

```yaml
# Slack 通知範例
- name: Send Slack Notification
  if: failure()
  uses: slackapi/slack-github-action@v1
  with:
    payload: |
      {
        "text": "❌ CI/CD Pipeline Failed",
        "blocks": [
          {
            "type": "section",
            "text": {
              "type": "mrkdwn",
              "text": "*Pipeline*: ${{ github.workflow }}\n*Branch*: ${{ github.ref }}\n*Commit*: ${{ github.sha }}\n*Status*: Failed"
            }
          }
        ]
      }
  env:
    SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
```

---

##### 6. CI/CD Pipeline 產出文件檢查清單

- [ ] **Pipeline 配置檔案已建立**（`.github/workflows/ci-cd-pipeline.yml` 或 `.gitlab-ci.yml`）
- [ ] **所有 9 個 Stage 已定義**（lint, test, security, build, deploy-dev, integration, deploy-staging, e2e, deploy-prod）
- [ ] **測試覆蓋率閾值已設定**（單元測試 ≥ 80%）
- [ ] **安全掃描工具已整合**（npm audit, Snyk, Trivy 至少一種）
- [ ] **環境變數已配置**（Secrets 管理）
- [ ] **手動審批流程已設定**（Production 部署需審批）
- [ ] **失敗通知已設定**（Slack/Teams/Email）
- [ ] **部署目標環境已定義**（Dev, Staging, Production URL）
- [ ] **健康檢查端點已驗證**（`/health` 或 `/api/health`）
- [ ] **Pipeline 執行時間已優化**（目標 < 30 分鐘）

---

**📋 相關文檔**:
- [Testing Standards (Stage 8.1.1)](#步驟-811testing-standards-詳細規範-)
- [QUICK_START_GUIDE](../../guides/user/onboarding/QUICK_START_GUIDE.md)
- [PROJECT_INITIALIZATION_GUIDE](../../guides/user/onboarding/PROJECT_INITIALIZATION_GUIDE.md)

---

### 階段 9：移交開發團隊 (1 小時)

> 🤖 **Agent 參與角色** - 全 Agent 最終驗收階段
>
> **活躍 Agents**: PM/PO (Victoria), SA (Amanda), QA (Quincy)
>
> **協作模式**:
> - **PM/PO (Victoria)**: 業務驗收、產品交付確認
> - **SA (Amanda)**: 需求追蹤驗證、文檔完整性檢查
> - **QA (Quincy)**: 品質閘門檢查、文檔一致性驗證
>
> **主要產出**: 文檔檢查報告、最終交付包、團隊 Kickoff

#### 步驟 9.1：文件檢查

**9.1.1 文件完整性檢查**

確認所有文件完整：
- [ ] PRD（含 Feature ID: F-XXX）
- [ ] FRD（含 Business Rule ID: BR-XXX）
- [ ] SRD（含完整架構設計）
- [ ] Architecture Documents（C4 Model 圖表）
- [ ] API Specifications（含 API ID: API-XXX）
- [ ] User Stories（含 EPIC-XXX → US-XXX → AC-XXX-Y）
- [ ] Sprint Plan（含 Story Points 估算）
- [ ] Developer Guidelines

> 📋 **完整性檢查**: [Completeness_Checklist.md](checklists/Completeness_Checklist.md)

**9.1.2 文件品質檢查（新增）**

> 📋 **參考工具**: [Document_Quality_Checklist.md](../../guides/system/quality/Document_Quality_Checklist.md)

確認文件品質：

- [ ] **可讀性檢查**
  - [ ] 所有專有名詞有定義或首次出現時解釋
  - [ ] 所有縮寫有說明（PRD, FRD, RICE, MVP 等）
  - [ ] 章節編號一致，標題層級正確（H1 → H2 → H3）

- [ ] **視覺元素檢查**
  - [ ] 圖表清晰可讀（解析度足夠）
  - [ ] 圖表有標題和說明
  - [ ] 流程圖箭頭方向正確

- [ ] **連結檢查**
  - [ ] 文件間交叉連結正確（無 404）
  - [ ] 外部連結有效
  - [ ] 相對路徑正確

- [ ] **一致性檢查**
  - [ ] ID 命名規範一致（F-XXX, US-XXX, AC-XXX-Y）
  - [ ] 術語使用一致（統一用「交易」而非混用「記錄」）
  - [ ] 日期格式一致（YYYY-MM-DD）

**9.1.3 文件可讀性測試**

> 💡 **測試方法**: 找一位非專案成員閱讀文件 15 分鐘，確認是否理解核心內容

**通過標準**（能回答以下問題）：
- [ ] 這個專案要做什麼？
- [ ] 主要功能有哪些？
- [ ] 技術架構是什麼？
- [ ] Sprint 1 要完成什麼？

如果無法回答 ≥ 3 個問題，建議優化文檔的可讀性和結構。

#### 步驟 9.2：文檔一致性檢查（🔴 獨立 Workflow 觸發）

> 🔴 **CRITICAL**: 此步驟必須觸發 `consistency-check` workflow，不可簡化為人工抽查！
> **觸發 Workflow**: `consistency-check`（[workflow/core/consistency-check.md](../../workflow/core/consistency-check.md)）

**執行指令**:
```
「請執行文檔一致性檢查 workflow (consistency-check)」
```

**檢查內容**:
- [ ] PRD → FRD 需求追蹤完整（每個 Feature 都有對應 FRD 描述）
- [ ] FRD → SRD 技術追蹤完整（每個功能需求都有技術方案）
- [ ] SRD → API Spec 實作追蹤完整（每個 API 都有 SRD 依據）
- [ ] API Spec → User Stories 驗收追蹤完整
- [ ] ID 編號一致性（F-XXX, US-XXX, AC-XXX-Y, API-XXX 無衝突或遺漏）
- [ ] 術語一致性（同一概念在各文檔使用相同名稱）
- [ ] 非功能需求在 SRD 中都有對應設計

**追蹤鏈驗證**:
```
F-XXX (Feature) → BR-XXX (Business Rule) → EPIC-XXX → US-XXX → AC-XXX-Y → API-XXX
```

> 📋 **追蹤鏈參考**: [AISDLC_ID_Naming_Convention.md](../../guides/system/naming/AISDLC_ID_Naming_Convention.md)

**自動化驗證工具** 🆕:
```bash
# 執行追溯鏈自動驗證
bash AISDLC/framework/tools/verify_traceability.sh docs

# 驗證項目包括：
# 1. 各類型 ID 統計（F/BR/EPIC/US/AC/API/TC/BUG/NFR）
# 2. Feature → User Story → AC 追溯鏈完整性
# 3. 孤立 ID 檢查（定義但未被引用的 ID）
# 4. Markdown 內部連結有效性
```

> 💡 **工具說明**: `verify_traceability.sh` 掃描 docs/ 目錄中所有 Markdown 文件，
> 自動檢查 AISDLC 標準 ID 的定義、引用和追溯鏈完整性。
> 詳見 [verify_traceability.sh](../../tools/verify_traceability.sh)

> ⚠️ **若自動化工具尚未就緒，使用以下手動替代方案**（適用於多領域系統）：
>
> ```bash
> # 手動追蹤鏈驗證（grep 方式）
>
> # 1. 確認所有 Feature ID 在 FRD 都有對應的 BR
> grep -rn "SHOP-F-\|STAY-F-\|CMS-F-\|KMS-F-\|INV-F-\|SHARED-F-" docs/01_requirements/PRD.md
> grep -rn "SHOP-BR-\|STAY-BR-\|CMS-BR-\|KMS-BR-\|INV-BR-\|SHARED-BR-" docs/01_requirements/FRD.md
>
> # 2. 確認所有 US 都有對應的 AC
> grep -c "US-" docs/01_requirements/UserStories.md
> grep -c "AC-" docs/01_requirements/UserStories.md
>
> # 3. 確認所有 API 都在 SRD 有對應的設計
> grep -rn "API-SHOP-\|API-STAY-\|API-CMS-\|API-KMS-\|API-INV-" docs/02_architecture/
> ```
>
> 🔴 **多領域系統特別提醒**：五域系統（電商/民宿/CMS/KMS/進銷存）的 API 文件約 25+ 份，手動驗證工作量大。建議規劃「文檔驗證 Sprint」或使用 AI 輔助 consistency-check workflow 自動分析。

**🔴 人類確認點**: 一致性檢查結果確認，不一致項目須修正後才能繼續

🆕 **跨領域資料模型一致性檢查**（多業務領域系統額外檢查）:

> 💡 多領域系統除了標準的文檔一致性檢查外，需額外驗證跨領域的資料模型一致性。

- [ ] **共用實體一致性**: 各領域引用的共用實體（Member, Payment 等）欄位名稱、型別一致
- [ ] **ID 編碼不衝突**: 各領域的 ID 前綴不重複（如 shop-order vs stay-booking）
- [ ] **列舉值一致性**: 跨領域共用的列舉（如 PaymentStatus, MemberLevel）定義相同
- [ ] **API 命名規範一致**: 各領域 API 遵循相同的命名慣例（RESTful 路徑、欄位命名風格）
- [ ] **日期時區一致**: 所有領域使用相同的時區處理策略（建議 UTC 儲存 + 前端轉換）
- [ ] **金額精度一致**: 所有領域的金額欄位使用相同精度（建議 DECIMAL(10,2)）

> 🆕 **SEO 元資料一致性檢查**（適用於內容平台）:
> - ✅ 所有已發布內容是否都有 `meta_title` 和 `meta_description`
> - ✅ `slug` 是否全局唯一（無重複）
> - ✅ `canonical_url` 是否正確指向主要版本
> - ✅ `sitemap.xml` 是否包含所有已發布頁面
> - ✅ 結構化資料（JSON-LD）是否符合 Schema.org 規範

---

#### 步驟 9.3：前後端互動分析（🔴 獨立 Workflow 觸發）

> 🔴 **CRITICAL**: 此步驟必須觸發 `interaction-analysis` workflow！
> **觸發 Workflow**: `interaction-analysis`（[workflow/core/interaction-analysis.md](../../workflow/core/interaction-analysis.md)）
> **適用條件**: 專案包含前後端分離架構時（Web/Mobile + Backend API）

**執行指令**:
```
「請執行前後端互動分析 workflow (interaction-analysis)」
```

**分析內容**:
- [ ] 前端 → Backend API 呼叫流程設計
- [ ] API 資料流序列圖（Sequence Diagram）
- [ ] 錯誤處理與回饋機制（4xx/5xx → UI 提示）
- [ ] 載入狀態與使用者體驗設計
- [ ] 跨平台（Web/Mobile/Desktop）呼叫差異處理
- [ ] 即時通訊（WebSocket/SSE）互動流程（如適用）

**🔴 人類確認點**: 互動流程確認

---

#### 步驟 9.4：團隊 Kickoff Meeting
召開專案啟動會議，說明：
- 專案願景和目標
- 技術架構和決策理由（展示 C4 Model 圖表）
- Sprint 計畫和里程碑
- ID 命名規範和追蹤鏈使用
- 開發流程和規範
- Q&A

#### 🆕 步驟 9.5：移交確認清單（Handoff Checklist）

> **目的**: 確保所有必要文檔和環境已準備就緒，開發團隊可以無阻礙地開始工作。

**🔴 移交確認清單**（全部打勾才可進入 Stage 10）:

**A. 文檔完備性**:
- [ ] PRD 已正式簽核（人類確認）
- [ ] FRD 已正式簽核（人類確認）
- [ ] SRD + API Spec 已正式簽核
- [ ] User Stories 已估算 Story Points
- [ ] Sprint Backlog 已排序並分配
- [ ] 文檔一致性檢查通過（consistency-check workflow）

**B. 技術環境**:
- [ ] 開發環境可正常編譯和運行
- [ ] CI/CD Pipeline 運作正常（至少 Layer 0 + Layer 1）
- [ ] 資料庫 Schema 初始化腳本已驗證
- [ ] API Mock Server 已建立（供前端平行開發）

**C. 開發規範**:
- [ ] Git Branching Strategy 已確認
- [ ] Coding Standards 文檔已發布
- [ ] Code Review 流程已建立
- [ ] Testing Standards 已確認（覆蓋率門檻）

**D. 多領域專屬（如適用）**:
- [ ] 各領域模組邊界已確認（共用 vs 專屬）
- [ ] 跨領域 API Contract 已雙方確認
- [ ] 共用實體的資料表結構已統一
- [ ] 跨領域事件定義已文件化

**E. 多平台專屬（如適用）**:
- [ ] 各平台開發環境已建立（Web/Android/macOS）
- [ ] API 版本策略已確認
- [ ] 各平台功能差異已文件化

---

### 階段 10：實施與測試 (依 Sprint 規劃)

> 🔴 **CRITICAL**: 此階段為 AISDLC-SDD v0.01 **開發專注版**的核心重點！
> 必須嚴格遵循「開發-編譯-測試循環」，詳見 [Development_Build_Test_Cycle.md](../../guides/user/process/Development_Build_Test_Cycle.md)
> **觸發 Workflow**: `sprint-execution`
> **建議 Skill**: `/dev-review`、`/qa-testing`、`/testing-strategy`、`/code-review`

#### 步驟 10.1：Sprint 啟動確認

**主導**: Dev Agent (David) + QA Agent (Quincy)

**🔴 人類確認點**: Sprint 目標與開發順序

- [ ] 確認本 Sprint User Stories 清單（從 Sprint Backlog 取得）
- [ ] 確認每個 Story 的 Acceptance Criteria
- [ ] 確認技術實施方案（參考 SRD + API Spec）
- [ ] 確認開發順序與依賴關係
- [ ] 驗證開發環境可正常編譯與測試

#### 步驟 10.2：開發-編譯-測試循環（🔴 強制執行）

> **原則**: 每完成一支程式（或一個功能單元），**必須立即執行**編譯→測試，**絕不累積開發**。

對於每個 User Story：

```
📝 拆解為最小可編譯單元（建議 < 100 行/單元）
    ↓
🔨 開發 1 個單元 → 立即編譯
    ↓
❌ 編譯失敗？ → 🔴 停止！修復後重新編譯
    ↓
✅ 編譯成功 → 執行單元測試
    ↓
❌ 測試失敗？ → 🔴 停止！對照規格修復後重新測試
    ↓
✅ 測試通過 → Commit → 繼續下一個單元
```

**各技術棧命令參考**:

| 技術棧 | 編譯命令 | 測試命令 |
|--------|---------|---------|
| Java/Spring Boot | `mvn compile` / `gradle build` | `mvn test` / `gradle test` |
| TypeScript/Next.js | `npx tsc --noEmit` | `npm test` / `jest` |
| Kotlin/Android | `./gradlew assembleDebug` | `./gradlew test` |
| Swift/macOS | `swift build` / `xcodebuild` | `swift test` / `xcodebuild test` |
| Python | `python -m py_compile <file>` | `pytest` |

**禁止行為**:
- ❌ 累積開發多支程式後才編譯
- ❌ 編譯失敗後繼續開發其他功能
- ❌ 跳過單元測試直接開發下一支
- ❌ 測試失敗後註解掉測試繼續開發

#### 🆕 步驟 10.2.1：變更影響分析（CIA - Change Impact Analysis）

> ⚠️ **適用時機**: 當 Sprint 中包含「修改」或「刪除」操作的 User Story 時，
> 必須在開發前執行變更影響分析，避免修改操作產生連鎖影響。

**主導**: Dev Agent (David) + SA Agent (Amanda)

**為什麼需要 CIA？**
- 修改商品單價 → 可能影響所有未結帳訂單的金額
- 刪除供應商 → 可能影響進行中的進貨單
- 修改庫存數量 → 可能觸發安全庫存警示或影響出貨

**CIA 檢查清單**（每個修改/刪除操作必須填寫）:

```markdown
## 變更影響分析表

**變更項目**: [描述要修改/刪除的內容]
**變更類型**: [ ] 修改 [ ] 刪除 [ ] 狀態變更

### 1. 資料影響分析
- [ ] 該資料被哪些其他資料表引用？（Foreign Key 關聯）
- [ ] 修改後是否影響歷史紀錄的正確性？
- [ ] 是否需要級聯更新關聯資料？
- [ ] 是否影響報表/統計數據的正確性？

### 2. 業務邏輯影響
- [ ] 修改後是否影響進行中的業務流程？（如：未完成訂單）
- [ ] 是否需要重新計算衍生欄位？（如：訂單總金額、庫存成本）
- [ ] 是否影響其他使用者正在操作的資料？（並發衝突）
- [ ] 是否需要通知相關人員？（如：價格變更通知業務人員）

### 3. API 影響
- [ ] 哪些 API 端點會受影響？
- [ ] 是否需要 API 版本控制（避免破壞現有客戶端）？
- [ ] 回傳資料格式是否變更？

### 3.1 🆕 Greenfield 早期重構的 Breaking Change 決策
> **適用時機**：Greenfield 開發初期（Sprint 1-4），需要修改已設計但尚未被外部客戶端使用的 API 格式時。
>
> | 情境 | 是否需要 API 版本控制 | 決策依據 |
> |------|---------------------|---------|
> | API 只有 Web 前端使用，尚未有 Mobile App | ❌ 可直接改格式 | 所有客戶端由同一團隊控制，可同步更新 |
> | API 已被 Mobile App（內測版）使用 | ⚠️ 評估影響範圍 | 內測版可強制更新，但需協調發布時機 |
> | API 已對外公開（第三方整合/SDK）| 🔴 **必須版本控制** | 無法強制外部客戶端更新 |
> | 資料格式變更（如 HTML→JSON）但無外部客戶端 | ❌ 可直接改，需含 DB Migration | 開發初期改格式成本低，不需版本控制 |
> | 欄位新增（向下相容）| ❌ 不需版本控制 | 新增欄位不破壞現有客戶端 |
> | 欄位移除/重命名 | 🔴 **必須版本控制** | 破壞性變更，即使是 Greenfield 也需評估 |
>
> **Greenfield 黃金規則**：Sprint 1-4 的 Breaking Change 成本最低，建議一次改好，不要累積到有外部依賴後才改。

### 4. 多平台影響
- [ ] 變更是否影響所有平台（Web/Android/macOS）？
- [ ] 是否需要各平台同步更新？
- [ ] 離線模式下的資料是否需要同步處理？

### 5. 回滾方案
- [ ] 如果變更出錯，如何回滾？
- [ ] 是否需要備份原始資料？
- [ ] 回滾後是否影響其他已完成的操作？

### 6. 🆕 合規影響評估（涉及個資/金流/法規時必填）
- [ ] 是否涉及個人資料（PII）？→ 確認加密存儲方式（AES-256）、存取記錄（Audit Log）
- [ ] 是否涉及支付資料（Card/Token）？→ 確認 PCI-DSS 不儲存 CVV，Stripe Tokenization 正確
- [ ] 是否涉及旅宿業資料（訂客資料）？→ 確認資料保留期限（依旅宿業法規）
- [ ] 是否影響 GDPR Right to Erasure？→ 個資刪除需級聯至相關備份和日誌
- [ ] 是否需要記錄操作稽核記錄（Audit Trail）？→ 確認新操作類型已加入 Audit Log
```

**常見修改操作的影響範例**:

| 修改操作 | 直接影響 | 間接影響 | 建議處理 |
|---------|---------|---------|---------|
| 修改商品單價 | 商品表 price 欄位 | 未結帳訂單金額、報價單 | 只影響新訂單，歷史訂單保留原價 |
| 修改客戶等級 | 客戶表 level 欄位 | 折扣計算、信用額度 | 立即生效，但不追溯歷史訂單 |
| 刪除商品 | 商品表軟刪除 | 歷史訂單引用、庫存紀錄 | 軟刪除 + 標記「已停售」 |
| 修改庫存數量（盤點） | 庫存表 quantity | 安全庫存警示、可銷售數量 | 產生盤點異動紀錄，記錄調整原因 |
| 作廢訂單 | 訂單狀態 → VOIDED | 庫存回沖、應收帳款調整 | 級聯：回沖庫存 + 沖銷帳款 |

🆕 **跨領域修改操作的影響範例**（多領域融合系統適用）:

| 修改操作 | 直接影響（本領域） | 間接影響（跨領域） | 建議處理 |
|---------|-----------------|------------------|---------|
| 修改會員等級規則 | 會員表等級欄位更新 | **電商**：折扣計算變更；**民宿**：升等規則變更、積分折抵上限變更 | 兩個領域的折扣/權益邏輯需同步更新，發布需同時部署 |
| 取消民宿訂房（含積分折抵） | 訂房表狀態 → CANCELLED、日曆庫存釋放 | **電商**：已折抵的積分需回補至會員帳戶；退款需經電商支付模組 | 積分回補與庫存釋放需在同一交易中完成（分散式事務或 Saga） |
| 下架共用供應商 | 供應商表軟刪除 | **電商**：該供應商商品標記「供應商已停用」；**民宿**：該供應商提供的備品/消耗品需切換供應來源 | 需通知兩個領域的負責人，分別處理各自的影響 |

> 💡 **辨識跨領域影響的技巧**：當修改操作涉及「共用實體」（會員、支付、供應商）時，
> 必須檢查所有使用該共用實體的領域，確認是否有連鎖影響。

🆕 **跨領域刪除依賴檢查流程**（多領域系統必須執行）:

> **適用時機**: 當刪除操作涉及共用實體或跨領域資料時。
>
> **檢查步驟**:
> ```
> 1. 識別刪除目標的所有 FK 關聯（本領域 + 跨領域）
>    SELECT table_name, constraint_name
>    FROM information_schema.table_constraints
>    WHERE constraint_type = 'FOREIGN KEY'
>    AND referenced_table = '刪除目標表';
>
> 2. 按領域分類影響範圍
>    - shared.* → 影響所有領域，需全域評估
>    - shop.* → 僅電商，通知電商負責人
>    - stay.* → 僅民宿，通知民宿負責人
>    - 跨多個 schema → 需跨領域會議確認
>
> 3. 定義每個關聯的處理策略
>    - CASCADE: 自動級聯刪除（⚠️ 跨領域禁止使用）
>    - SET NULL: 設為 null（需確認業務邏輯允許）
>    - RESTRICT: 阻止刪除（預設安全策略）
>    - 應用層處理: 軟刪除 + 標記引用為「已失效」
>
> 4. 執行前必須確認
>    - [ ] 所有跨領域影響已識別並通知負責人
>    - [ ] 刪除策略已獲各領域確認
>    - [ ] 回滾方案已準備（跨領域回滾需同步）
> ```

#### 步驟 10.3：整合測試

**主導**: QA Agent (Quincy)
**建議 Skill**: `/qa-testing`

- [ ] API 整合測試：驗證端點回應、錯誤處理、認證授權
- [ ] 前後端整合測試：驗證資料流完整性（UI → API → DB → API → UI）
- [ ] 跨平台測試（如適用）：Web、Mobile、Desktop 功能一致性
- [ ] 效能基準測試：回應時間、併發處理能力

#### 🆕 步驟 10.3.1：跨平台整合測試（多平台專案適用）

> ⚠️ **適用條件**: 當專案涉及多平台（Web + Mobile + Desktop）共享後端 API 時，
> 必須執行跨平台整合測試，確保端到端資料流在所有平台上一致。

**主導**: QA Agent (Quincy)
**協作**: Dev Agent (David) + SD Architect (Marcus)

**跨平台測試策略矩陣**:

| 測試層級 | 測試內容 | 工具建議 | 優先級 |
|---------|---------|---------|--------|
| **API 一致性測試** | 同一 API 在不同客戶端的回應一致性 | Postman Collection Runner, REST Assured | 🔴 必要 |
| **資料同步測試** | 多客戶端同時操作時的資料一致性 | 自訂測試腳本 + WebSocket 監控 | 🔴 必要 |
| **認證授權測試** | JWT/OAuth Token 在各平台的行為一致性 | Security Test Suite | 🔴 必要 |
| **離線/線上切換測試** | Mobile 離線操作後同步至 Server 的正確性 | 手動測試 + 自動化輔助 | 🟡 重要 |
| **推播通知測試** | 跨平台推播的觸發與接收 | Firebase Test Lab | 🟡 重要 |
| **效能對比測試** | 各平台相同操作的回應時間對比 | JMeter, k6 | 🟢 建議 |

**跨平台端到端測試流程**（以經銷存系統為例）:

```
測試場景：Web 建立訂單 → Android 掃碼出庫 → macOS 查看報表

Step 1: [Web] 業務人員建立銷貨單 (POST /api/v1/sales-orders)
   ├── 驗證：API 回應 201, 訂單狀態 = 'PENDING'
   └── 驗證：WebSocket 推送「新訂單通知」至所有已連線客戶端

Step 2: [Android] 倉管人員接收通知，開啟掃碼出庫
   ├── 驗證：Android 收到 WebSocket 推送通知
   ├── 驗證：掃碼後呼叫 PUT /api/v1/inventory/ship 成功
   └── 驗證：庫存即時更新，WebSocket 推送庫存變更

Step 3: [macOS] 管理者查看即時庫存報表
   ├── 驗證：報表資料反映最新庫存（Step 2 的變更已同步）
   ├── 驗證：報表數據與 API 回傳一致
   └── 驗證：匯出報表功能正常（PDF/Excel）

Step 4: [All] 資料一致性最終驗證
   ├── 驗證：三個平台查詢同一訂單，狀態一致
   ├── 驗證：庫存數量在三個平台顯示一致
   └── 驗證：操作日誌完整記錄（含操作平台來源）
```

**WebSocket 多客戶端同步測試**:

```
測試場景：多平台即時同步驗證

1. 同時連接 3 個 WebSocket 客戶端（Web, Android, macOS）
2. 從任一客戶端執行操作（如：修改庫存）
3. 驗證其餘 2 個客戶端在 < 2 秒內收到更新
4. 驗證訊息內容一致（JSON Schema 驗證）
5. 模擬網路斷線重連，驗證資料補推機制
```

**🔴 強制檢查點 - 跨平台整合測試**:
- [ ] 已定義跨平台端到端測試場景（至少覆蓋核心業務流程）
- [ ] 已驗證 API 回應在所有平台的一致性
- [ ] 已驗證 WebSocket/推播在多客戶端的同步正確性
- [ ] 已測試離線/線上切換的資料同步（Mobile 平台）
- [ ] 已記錄各平台效能基準數據（回應時間對比）
- [ ] 跨平台整合測試報告已產出 → `docs/03_testing/`

🆕 **跨領域端到端測試場景**（多業務領域融合系統適用）:

> 💡 當系統包含多個業務領域時，除了跨平台測試，還需要驗證**跨領域**的資料流與業務邏輯一致性。

```
測試場景 1：電商積分折抵民宿房費
  Step 1: [電商] 會員購買商品累積 500 點積分
    ├── 驗證：會員積分餘額 = 500
  Step 2: [民宿] 會員訂房時選擇積分折抵（100 點 = NT$50）
    ├── 驗證：訂房金額正確扣除折抵金額
    ├── 驗證：會員積分餘額 = 400（即時同步）
  Step 3: [民宿] 會員取消訂房
    ├── 驗證：已折抵積分回補至會員帳戶（餘額 = 500）
    ├── 驗證：退款金額不含積分折抵部分
  Step 4: [電商] 查詢會員積分明細
    └── 驗證：積分明細包含「折抵」和「回補」兩筆紀錄

測試場景 2：共用供應商跨領域影響
  Step 1: [共用] 停用供應商 A
    ├── 驗證：供應商 A 軟刪除成功
  Step 2: [電商] 查看供應商 A 的商品
    ├── 驗證：商品標記「供應商已停用」，不可再進貨
  Step 3: [民宿] 查看供應商 A 的備品訂單
    └── 驗證：進行中的備品訂單顯示警示，提示更換供應商

測試場景 3：統一會員跨領域報表
  Step 1: [電商] 會員完成 3 筆訂單
  Step 2: [民宿] 同一會員完成 2 筆訂房
  Step 3: [共用] 查看會員統一消費報表
    └── 驗證：報表正確彙總兩個領域的消費金額和次數
```

> 🆕 **跨平台內容工作流端到端測試**（適用於多平台內容管理系統）:
>
> | 測試場景 | 操作流程 | 驗證重點 |
> |---------|---------|---------|
> | **跨平台審核** | Web 建立文章 → Mobile 審核通過 | 狀態同步、通知送達 |
> | **多渠道發布驗證** | 發布文章 → 檢查 Web/App/Email 各渠道 | 所有渠道內容一致 |
> | **離線編輯同步** | Mobile 離線編輯 → 恢復網路後同步 | 內容正確合併、無資料遺失 |
> | **即時通知** | Web 發起審核 → Mobile 收到推播 | 通知延遲 < 5 秒 |
> | **並行編輯衝突** | 兩人同時編輯同一文章 | 衝突提示或自動合併 |

> 🆕 **搜尋索引一致性測試規範**（適用於使用外部搜尋引擎的系統）:
>
> | 測試場景 | 驗證項目 | 預期結果 |
> |---------|---------|---------|
> | 新增資料後搜尋 | DB 新增記錄 → 搜尋該記錄 | 索引延遲 ≤ 預期值（如 2 秒） |
> | 更新資料後搜尋 | DB 更新記錄 → 搜尋驗證最新內容 | 搜尋結果反映最新資料 |
> | 刪除資料後搜尋 | DB 刪除/軟刪除 → 搜尋驗證消失 | 已刪除資料不出現在搜尋結果 |
> | 批次匯入後搜尋 | 批次匯入 1000 筆 → 搜尋驗證 | 所有記錄均可搜尋 |
> | 索引重建後驗證 | 觸發全量重建 → 比對 DB 與索引筆數 | 筆數一致、內容正確 |
> | 索引故障恢復 | 模擬索引服務中斷 → 恢復後驗證 | 自動補回中斷期間的變更 |

> 🆕 **排程任務與後臺作業測試規範**（適用於含 Cron Job/排程發布/批次處理的系統）:
>
> | 測試類型 | 測試場景 | 驗證重點 |
> |---------|---------|---------|
> | **正常執行** | 排程時間到達，任務正常執行 | 任務完成、狀態更新、通知發送 |
> | **時區處理** | 不同時區用戶設定排程 | 使用者看到的時間 vs UTC 儲存時間一致 |
> | **重複防護** | 多節點環境同時觸發 | 分散式鎖確保只執行一次（如 ShedLock / Quartz Cluster） |
> | **失敗重試** | 任務執行失敗（如 API 超時） | 重試機制啟動、重試次數正確、最終失敗告警 |
> | **大量排程** | 同一時間 100+ 任務觸發 | 佇列處理、無遺漏、效能可接受 |
> | **過期處理** | 伺服器重啟後，過期排程如何處理 | 過期任務立即執行或標記為 MISSED |
> | **取消排程** | 已排程任務被取消 | 任務不執行、狀態更新為 CANCELLED |
>
> **時間模擬測試技巧**: 使用 `Clock` 抽象（Java: `java.time.Clock`）或環境變數覆蓋系統時間，避免測試依賴真實時間等待。

> 🆕 **RBAC 權限綜合測試規範**（適用於多角色系統）:
>
> | 測試類型 | 測試場景 | 驗證重點 |
> |---------|---------|---------|
> | **正向授權** | 每個角色執行其允許的操作 | 操作成功 |
> | **負向授權** | 每個角色嘗試其禁止的操作 | 返回 403 Forbidden |
> | **資源所有權** | 使用者嘗試操作他人資源 | 非擁有者被拒絕 |
> | **角色變更即時生效** | 管理員降級使用者角色 | 降級後立即失去權限（無需重新登入） |
> | **跨平台一致性** | Web 與 Mobile 執行相同操作 | 權限結果一致 |
> | **API 直接呼叫** | 繞過 UI 直接呼叫 API | 後端同樣拒絕未授權操作 |

> 🆕 **富文本內容與媒體儲存測試規範**（適用於 CMS/內容編輯系統）:
>
> | 測試類型 | 測試場景 | 驗證重點 |
> |---------|---------|---------|
> | **XSS 防護** | 在富文本中插入 `<script>alert('xss')</script>` | 腳本被過濾或轉義 |
> | **HTML 清理** | 貼上含危險標籤的 HTML | 保留安全標籤，移除 `<iframe>`, `<object>` |
> | **大型內容** | 上傳 10MB+ 圖片、超長文章（50000 字） | 系統正常處理，不超時 |
> | **媒體格式相容** | 上傳 WebP/HEIC/SVG 等格式 | 跨平台正確顯示 |
> | **CDN 路徑** | 媒體 URL 是否正確重寫至 CDN 域名 | CDN URL 可正常訪問 |
> | **檔案大小限制** | 上傳超過限制的檔案 | 前端+後端都拒絕 |

> 🆕 **內容版本回退測試規範**（適用於支援版本追蹤的系統）:
>
> | 測試場景 | 驗證重點 |
> |---------|---------|
> | 回退至前一版本 | 內容恢復正確、版本號遞增（非覆蓋） |
> | 回退已發布文章 | 發布狀態是否維持、SEO URL 是否不變 |
> | 回退後搜尋索引 | 搜尋結果反映回退後的內容 |
> | 回退帶有媒體的版本 | 媒體檔案仍可存取（非已刪除） |
> | 版本比對（Diff） | 兩個版本之間的差異正確標示 |
> | 版本數量上限 | 超過保留上限時，最舊草稿版本被清理 |

> 🆕 **資料庫遷移測試規範**:
> - 遷移腳本在空白 DB 上從頭執行成功（驗證完整遷移鏈）
> - 遷移腳本在含測試資料的 DB 上執行成功
> - 回滾腳本（Down Migration）可正確回滾
> - 遷移後應用層所有 API 端點 Smoke Test 通過

> 🆕 **多語言與國際化測試提示**（適用於支援多語言的系統）:
> - 繁簡體中文搜尋一致性（搜尋「數據」是否匹配「資料」等同義詞）
> - 多語言內容 URL Slug 處理（中文 Slug 編碼正確性）
> - 日期/時間格式依 Locale 顯示（如：2026-03-23 vs 03/23/2026）
> - RTL（右至左）語言排版正確性（如適用）

#### 步驟 10.4：Code Review 與合併

**主導**: Dev Agent (David)
**建議 Skill**: `/dev-review`、`/code-review`

Code Review 檢查清單：
- [ ] 程式碼符合團隊 Coding Standard
- [ ] 無安全漏洞（OWASP Top 10）
- [ ] 單元測試覆蓋率 ≥ 80%
- [ ] API 實作符合 API Spec
- [ ] 無 TODO/FIXME 殘留

**🔴 人類確認點**: Code Review 通過後合併

#### 步驟 10.5：Sprint 驗收

**主導**: QA Agent (Quincy) + PM/PO (Victoria)

- [ ] 逐項執行每個 User Story 的 AC 驗收
- [ ] 記錄測試結果（Pass/Fail）
- [ ] 失敗項建立 Bug 報告並修復
- [ ] 完成 Sprint 回顧，記錄 Velocity
- [ ] 未完成項目移回 Backlog

**🔴 人類確認點**: Sprint 驗收結果確認

**階段產出**:
- Sprint 測試報告 → `docs/03_testing/`
- Code Review 紀錄 → `docs/06_quality/`
- Sprint 進度日誌 → `docs/05_development/`

---

### 階段 11：部署準備與上線 (1-3 天)

> **觸發 Workflow**: 參考 [devops-setup-flow.md](../../workflow/scenario-specific/devops-setup-flow.md) 完整部署流程
> **建議 Skill**: `/devops-github-actions`、`/devops-docker`、`/security-audit`、`/release-management`
>
> 💡 **部署流程參照**: Stage 8 已建立的 CI/CD Pipeline 基礎配置，本階段著重於「Production 環境建置」與「正式上線」。
> 完整的 DevOps 設定流程（含 Docker、GitHub Actions、監控）請參考 [devops-setup-flow.md](../../workflow/scenario-specific/devops-setup-flow.md)。

#### 步驟 11.1：部署環境建置

**主導**: DevOps Agent (devops-engineer)

- [ ] 配置多環境：Development / Staging / Production
- [ ] Docker 容器化配置（Dockerfile + docker-compose）
- [ ] CI/CD Pipeline 完善（GitHub Actions / GitLab CI）
- [ ] 資料庫遷移腳本驗證（Flyway / Liquibase）

> 🆕 **資料庫遷移管理最佳實踐**（適用於使用 Flyway/Liquibase 的系統）:
>
> **遷移前檢查清單**:
> - ✅ 大表（>100 萬筆）的 Schema 變更需評估鎖表時間
> - ✅ 新增欄位使用 `DEFAULT NULL` 避免長時間鎖表
> - ✅ 索引變更使用 `CONCURRENTLY`（PostgreSQL）避免阻塞讀寫
> - ✅ 遷移腳本在 Staging 環境先行驗證
> - ✅ 準備回滾腳本（Down Migration）
>
> **遷移驗證**:
> - 遷移後比對表結構（Schema Diff）
> - 抽樣驗證資料完整性（筆數、關鍵欄位值）
> - 應用層 Smoke Test 確認功能正常
>
> **遷移失敗回滾時間估算**:
> | 資料量級 | 回滾耗時（估算） | 建議 |
> |---------|---------------|------|
> | < 100 萬筆 | < 1 分鐘 | 可接受即時回滾 |
> | 100 萬~1000 萬筆 | 1~10 分鐘 | 需預留維護視窗 |
> | > 1000 萬筆 | 10 分鐘~小時級 | 建議使用 Online DDL 工具（如 gh-ost、pt-online-schema-change） |

> 🆕 **合規性檢查 CI/CD 整合提示**（適用於處理個人資料的系統）:
> - CI Pipeline 增加「敏感資料掃描」步驟（如 Gitleaks / TruffleHog 偵測硬編碼金鑰）
> - 審計日誌必須記錄：誰（user_id）在何時（timestamp）對什麼（resource）做了什麼（action）
> - 個資匯出/刪除 API 必須包含在自動化測試中（GDPR Right to Erasure）
> - 定期（如每季）執行合規性自動掃描（依賴套件漏洞、授權協議檢查）

**各技術棧 Docker 配置參考**:

```dockerfile
# Spring Boot 後端
FROM eclipse-temurin:17-jre-alpine
COPY target/*.jar app.jar
ENTRYPOINT ["java", "-jar", "/app.jar"]

# Next.js 前端
FROM node:18-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build
FROM node:18-alpine
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
CMD ["npm", "start"]
```

#### 🆕 步驟 11.1.1：多平台發布指引（Mobile/Desktop 適用）

> ⚠️ **適用條件**: 當專案包含 Mobile App（Android/iOS）或 Desktop App（macOS/Windows）時，
> 除了 Server 端的 Docker 部署外，還需要規劃客戶端 App 的打包與發布流程。

**多平台發布流程總覽**:

| 平台 | 打包格式 | 發布管道 | 簽章需求 | 審核週期 |
|------|---------|---------|---------|---------|
| **Android** | APK / AAB | Google Play Store / 內部分發 | Keystore 簽章 | 數小時 ~ 3 天 |
| **iOS** | IPA | App Store / TestFlight | Apple Certificate + Provisioning Profile | 1 ~ 7 天 |
| **macOS (SwiftUI)** | .app / .dmg | Mac App Store / 公證 (Notarization) | Apple Developer ID | 1 ~ 7 天 |
| **macOS (Electron)** | .dmg / .zip | 官網下載 / Homebrew Cask | Apple Notarization (建議) | 即時 |
| **Windows** | .exe / .msi | Microsoft Store / 官網下載 | Code Signing Certificate | 即時 ~ 3 天 |

**Android 發布流程**:

```
1. 構建 Release APK/AAB
   ./gradlew assembleRelease  (APK)
   ./gradlew bundleRelease    (AAB - Google Play 推薦)

2. 簽章
   - 使用 Release Keystore（⚠️ 必須安全保管，遺失無法更新 App）
   - CI/CD 中使用環境變數存放 Keystore 密碼

3. Google Play Console 上傳
   - Internal Testing → Closed Testing → Open Testing → Production
   - 填寫版本說明（Release Notes）
   - 設定逐步推出比例（如：先推 10% → 50% → 100%）

4. 驗證
   - 驗證 Google Play 上的 App 可正常下載安裝
   - 驗證 App 連線至正確的 Production API
```

**macOS App 發布流程**:

```
1. SwiftUI App 打包
   - Xcode → Product → Archive → Distribute App
   - 選擇 Mac App Store 或 Developer ID 分發

2. 公證 (Notarization)
   - xcrun notarytool submit {app}.zip --apple-id {email} --team-id {team}
   - 等待 Apple 審核通過（通常數分鐘）
   - xcrun stapler staple {app}.app

3. 分發方式選擇
   - Mac App Store：提交審核 → 通過後上架
   - 企業內部分發：透過 MDM 或官網下載
   - Homebrew Cask：適合開發者工具類 App
```

**🔴 強制檢查點 - 多平台發布**:
- [ ] 各平台的 Release 簽章金鑰已安全保管（Keystore / Certificate）
- [ ] CI/CD Pipeline 包含各平台的自動化構建流程
- [ ] 各平台已完成 Staging 環境測試
- [ ] 版本號策略已統一（Server API + Web + Mobile + Desktop）
- [ ] 各平台的 Release Notes 已準備
- [ ] 已規劃逐步推出策略（避免全量推出出問題）

#### 步驟 11.2：上線前驗證

**主導**: QA Agent (Quincy) + DevOps Agent
**建議 Skill**: `/security-audit`、`/performance-optimization`

- [ ] 安全掃描（OWASP ZAP / SonarQube）
- [ ] 效能測試（Load Testing / Stress Testing）
- [ ] 資料庫備份與還原驗證
- [ ] Staging 環境完整功能測試
- [ ] 回滾方案準備與驗證

🆕 **回滾策略選項與決策指引**:

> ⚠️ **重要**: 部署前必須確定回滾策略，並在 Staging 環境驗證回滾流程可行。

| 回滾策略 | 適用場景 | 回滾速度 | 風險等級 | 成本 |
|---------|---------|---------|---------|------|
| **Blue-Green Deployment** | 全新部署 / 大版本更新 | ⚡ 秒級（切換流量） | 低 | 高（雙倍資源） |
| **Canary Release** | 漸進式發布 / 高流量系統 | 中（逐步回切） | 低 | 中（部分額外資源） |
| **Rolling Update** | 容器化部署 / K8s 環境 | 中（逐個替換） | 中 | 低 |
| **版本回退 (Revert)** | 小型更新 / 單一服務 | 快（重部署前版本） | 中 | 低 |
| **資料庫回滾** | Schema 變更 / 資料遷移 | 慢（需執行回滾腳本） | 高 | 中 |

**回滾決策流程**:

```
1. 部署前準備
   ├── 確認前一個穩定版本的 Docker Image Tag / Artifact
   ├── 準備 DB Migration 回滾腳本（DOWN migration）
   ├── 確認回滾操作的執行權限和操作人員
   └── 在 Staging 環境演練回滾流程

2. 回滾觸發條件（任一條件觸發即回滾）
   ├── 🔴 健康檢查連續失敗 > 3 次
   ├── 🔴 錯誤率 > 5%（對比部署前基線）
   ├── 🔴 P95 回應時間 > 基線的 200%
   └── 🔴 關鍵業務功能異常（如：無法建立訂單）

3. 回滾執行步驟
   ├── Step 1: 停止新版本流量（切換 Load Balancer）
   ├── Step 2: 部署前一穩定版本
   ├── Step 3: 執行 DB 回滾腳本（如有 Schema 變更）
   ├── Step 4: 驗證回滾後系統正常
   └── Step 5: 通知團隊並記錄回滾原因
```

**🔴 強制檢查點 - 回滾準備**:
- [ ] 已確認前一穩定版本可快速部署（Image/Artifact 已保留）
- [ ] DB Migration 有對應的回滾腳本（DOWN migration 已測試）
- [ ] 回滾流程已在 Staging 環境演練通過
- [ ] 已定義回滾觸發條件和決策人員
- [ ] Mobile App 回滾策略已確認（強制更新 / 版本相容）

🆕 **多模組/多領域回滾策略**（多業務領域系統額外考量）:

> ⚠️ 當系統由多個領域模組組成時，回滾需考慮「部分回滾」vs「全部回滾」的決策。

| 情境 | 回滾策略 | 說明 |
|------|---------|------|
| **單一領域異常** | 部分回滾（只回滾該領域） | 前提：領域間 API 向下相容，不影響其他領域 |
| **共用模組異常** | 全部回滾（所有領域一起） | 共用模組（會員、支付）影響所有領域，必須整體回滾 |
| **跨領域資料不一致** | 全部回滾 + 資料修復 | 如積分折抵訂房後回滾電商模組，需修復積分紀錄 |
| **DB Schema 跨領域變更** | 全部回滾 | Schema 變更可能影響多個領域的查詢和寫入 |

**部分回滾前置條件**:
- [ ] 各領域模組獨立部署（微服務或獨立部署單元）
- [ ] 領域間 API 版本相容（新版 API 向下相容）
- [ ] 無跨領域的 DB Schema 變更
- [ ] 共用模組未變更

> 🆕 **多領域滾動升級（Rolling Update）跨域 API 相容性保證機制**：
>
> 當使用 Rolling Update 部署時，多領域系統在升級期間（新舊版本並存）需確保跨域 API 呼叫的相容性：
>
> **問題場景**：電商模組 v1.2 已升級，但民宿模組仍在 v1.1 → 若兩者共用「統一支付 API」，需確保 v1.2 的支付 API 格式向下相容 v1.1 的呼叫方式。
>
> **保證機制**：
> | 機制 | 說明 | 實作方式 |
> |------|------|---------|
> | **API 向下相容設計** | 新版 API 新增欄位，不移除舊欄位 | 使用 `@JsonInclude(NON_NULL)` 或 Optional 欄位 |
> | **Consumer-Driven Contract Testing** | 消費方主導的 API 合約測試 | Spring Cloud Contract / Pact 框架 |
> | **共用模組最後升級** | 先升級各領域模組，共用模組（支付/會員）最後升級 | Deployment 順序規劃：領域服務 → 共用服務 |
> | **Smoke Test 覆蓋跨域呼叫** | 每次 Rolling Update 後自動執行跨域 Smoke Test | GitHub Actions 部署後 Smoke Test 步驟 |
>
> **版本相容期承諾**：建議各領域 API 向下相容前一個大版本（如 v1.x 相容 v1.0），確保 Rolling Update 期間無服務中斷。

> 🆕 **CDN 快取回滾處理**:
> - 應用回滾時，必須同步清除 CDN 快取（避免新頁面請求舊 API）
> - 回滾操作清單：回滾應用版本 → 清除 CDN HTML 快取 → 驗證頁面內容 → 監控錯誤率
> - 若使用含 hash 的靜態資源，回滾後舊版 JS/CSS 仍在 CDN 上可用（無需額外處理）

> 🆕 **搜尋索引回滾策略**（適用於使用 Elasticsearch/Meilisearch 的系統）:
>
> | 場景 | 回滾方案 | 耗時估算 | 風險 |
> |------|---------|---------|------|
> | **索引 Schema 不相容** | 切換索引別名至舊版（`articles_v1`） | 秒級 | 低（前提：保留舊索引） |
> | **索引資料損壞** | 從備份快照恢復 | 分鐘～小時級（視資料量） | 中（備份時間點後的資料遺失） |
> | **索引欄位型別變更** | 重建索引（Reindex） | 小時級（千萬級資料） | 高（重建期間搜尋功能降級） |
> | **應用版本回滾** | 確認舊版應用與當前索引相容 | 秒級 | 低（通常向下相容） |
>
> **最佳實踐**:
> - 索引變更前必須保留舊版索引至少 24 小時（勿立即刪除）
> - 使用索引別名（Alias）作為應用層唯一入口，切換無需改程式碼
> - 定期建立索引快照（Snapshot），建議每日一次
> - 重建索引時使用「背景重建 + 別名切換」模式，避免服務中斷
> - 若搜尋功能降級，應用層需有「降級方案」（如：回退至 DB LIKE 查詢）

> 🆕 **Feature Flag 與 A/B 測試配置提示**（適用於需要漸進式發布的系統）:
>
> **常見 Feature Flag 工具**:
> | 工具 | 類型 | 適用場景 |
> |------|------|---------|
> | **Unleash** | 開源自託管 | ✅ 推薦、成本低、功能完整 |
> | **LaunchDarkly** | SaaS | 企業級、功能最全 |
> | **GrowthBook** | 開源 | ⭐ A/B 測試專用、整合分析 |
> | **應用內實作** | 自建 | 簡單場景、DB 存儲 Flag |
>
> **內容平台 A/B 測試場景**:
> - 新推薦算法 vs 舊算法（比較 CTR/停留時間）
> - 新編輯器 vs 舊編輯器（比較編輯效率/錯誤率）
> - 新版文章版面 vs 舊版面（比較閱讀完成率）
>
> **漸進式發布策略**:
> - Phase 1: 內部團隊（1%）→ Phase 2: Beta 使用者（10%）→ Phase 3: 全量（100%）
> - 每個 Phase 觀察 24 小時，確認無異常後進入下一 Phase

**🔴 人類確認點**: 上線前最終確認

#### 步驟 11.3：正式部署

**主導**: DevOps Agent

- [ ] 執行資料庫遷移
- [ ] 部署應用程式至 Production
- [ ] 驗證健康檢查端點
- [ ] 設定監控告警（建議 Skill: `/devops-monitoring`）
- [ ] 執行煙霧測試 (Smoke Test)

#### 步驟 11.4：發布與文檔

**主導**: PM/PO (Victoria)
**建議 Skill**: `/release-management`

- [ ] 撰寫 Release Notes → `docs/08_deployment/`
- [ ] 更新使用者文檔
- [ ] 通知利害關係人
- [ ] 紀錄部署日誌

**🔴 人類確認點**: 確認發布成功

**階段產出**:
- 部署配置文件 → `docs/08_deployment/`
- Release Notes → `docs/08_deployment/`
- 監控設定文件 → `docs/08_deployment/`

---

## 🎯 成功標準

### 文件完整性
- [ ] 所有必要文件已產生
- [ ] 文件間追蹤鏈完整 (PRD→FRD→SRD→Stories)
- [ ] 文件通過一致性檢查

### 人機協作品質
- [ ] 所有確認點都已完成
- [ ] 無自主臆測，所有決策有人類確認
- [ ] 協作記錄完整可追溯

### 可執行性
- [ ] User Stories 清楚且可執行
- [ ] Sprint 規劃符合團隊 Velocity
- [ ] 技術架構經過驗證可行

### 團隊準備度
- [ ] 開發團隊理解需求和架構
- [ ] 開發環境已就緒
- [ ] 工具和流程已建立

---

## 📊 時間分配參考

| 階段 | 預估時間 | 可彈性調整 |
|------|---------|-----------|
| 階段 1-9 規劃階段 | 3-5 天 | 視專案複雜度 |
| 啟動和情境確認 | 30 分鐘 | ±10 分鐘 |
| 需求提取與分析 | 4-8 小時 | 視需求複雜度 |
| 技術選型 | 2-4 小時 | 新技術棧需更多時間 |
| 需求驗證與文件化 | 3-5 小時 | - |
| 架構設計 | 4-8 小時 | 企業級系統建議 6-8 小時 |
| User Story 撰寫 | 3-4 小時 | - |
| Sprint 規劃 | 2-3 小時 | - |
| 開發準備 | 1-2 天 | 可與階段 7 並行 |
| 移交開發團隊 | 1 小時 | - |
| **階段 10 實施與測試** | **依 Sprint 規劃** | **每 Sprint 1-4 週** |
| **階段 11 部署與上線** | **1-3 天** | **視環境複雜度** |

---

## 💡 最佳實踐

### 1. 充分的人機協作
- 不要跳過任何確認點
- 詳細回答系統的問題
- 主動補充背景資訊

### 2. MVP First 思維
- 先確定核心價值
- 將 Nice-to-have 功能延後
- 保持首版簡單可行

### 3. 技術選型平衡
- 考慮團隊現有技能
- 不要盲目追求新技術
- 評估學習曲線和風險

### 4. 持續驗證
- 每個階段完成後回顧
- 確保文件一致性
- 及時調整方向

---

## 🔄 專案暫停與恢復機制 (Checkpoint Mechanism)

### 何時需要暫停專案？
- 需求重大變更，需要重新評估
- 關鍵資源(人力/預算)暫時不可用
- 外部依賴(第三方 API/合作夥伴)未就緒
- 市場環境變化需要策略調整

### Checkpoint 設計

每個階段結束時自動建立 Checkpoint,包含:

| Checkpoint | 階段 | 保存內容 | 恢復時間 |
|-----------|------|---------|---------|
| **CP-1** | 需求提取完成 | 需求提取報告、人機協作記錄 | 30 分鐘 |
| **CP-2** | 技術選型完成 | 技術選型報告、成本評估 | 20 分鐘 |
| **CP-3** | PRD/FRD 完成 | PRD、FRD、MVP Definition | 30 分鐘 |
| **CP-4** | SRD/架構完成 | SRD、架構圖、API Spec、ADR | 1 小時 |
| **CP-5** | User Stories 完成 | User Stories、AC、Story Points | 20 分鐘 |
| **CP-6** | Sprint 規劃完成 | Sprint Roadmap、Sprint Backlog | 30 分鐘 |
| **CP-7** | 開發準備完成 | 開發規範、CI/CD 配置、環境 | 1 小時 |

### 如何保存 Checkpoint

**方法 A: 文檔快照** (建議)
```bash
# 每個階段完成後執行
mkdir -p project-checkpoints/CP-X-YYYYMMDD
cp docs/* project-checkpoints/CP-X-YYYYMMDD/
echo "Checkpoint CP-X saved at $(date)" >> checkpoint-log.txt
```

**方法 B: Git Tag**
```bash
git add docs/
git commit -m "Checkpoint CP-X: [階段名稱] completed"
git tag -a CP-X -m "Checkpoint: [階段描述]"
```

**方法 C: 專案管理工具**
- 在 Jira/Linear 建立 Milestone
- 附加所有相關文檔連結
- 標記完成日期和負責人

### 如何恢復專案

**步驟 1: 識別最近的有效 Checkpoint**
```bash
# 查看 Checkpoint 歷史
cat checkpoint-log.txt

# 或查看 Git tags
git tag -l "CP-*"
```

**步驟 2: 恢復文檔和狀態**
```
執行指令給 AI:
「請載入 AISDLC_INIT.md,我要恢復專案 [專案名稱]
- 最後 Checkpoint: CP-X
- Checkpoint 日期: YYYY-MM-DD
- 暫停原因: [簡述]
- 變更事項: [如有需求/技術/團隊變更,請描述]」
```

**步驟 3: 差異檢查**

AI 會協助你檢查:
- [ ] 需求是否有變化？
- [ ] 技術選型是否仍然有效？
- [ ] 團隊成員是否有變動？
- [ ] 時間預算是否需要調整？
- [ ] 外部依賴是否已解決？

**步驟 4: 增量更新或重新驗證**
- **若變更 <20%**: 增量更新受影響的文檔,繼續執行
- **若變更 20-50%**: 重新驗證受影響階段,重跑驗證流程
- **若變更 >50%**: 建議從頭重新執行,視為新專案

### Checkpoint 最佳實踐

✅ **DO:**
- 每個階段完成後立即保存 Checkpoint
- Checkpoint 描述清晰,包含日期和關鍵決策
- 重要決策和變更原因詳細記錄
- Checkpoint 檔案納入版控

❌ **DON'T:**
- 跳過 Checkpoint 保存「專案不會暫停」
- Checkpoint 描述模糊,恢復時不知道進度
- 僅保存程式碼,不保存規劃文檔
- Checkpoint 檔案散落各處,難以管理

---

## 🚨 常見陷阱

### ❌ 避免這些錯誤

**1. 需求階段**
- 需求過於籠統，缺少細節
- 未充分考慮非功能需求
- 跳過業務規則定義

**2. 技術選型**
- 選擇團隊不熟悉的技術棧
- 忽視成本和維護複雜度
- 過度設計 (over-engineering)

**3. 架構設計**
- 架構過於複雜，超出需求
- 未考慮擴展性和維護性
- 安全性設計不足

**4. Story 撰寫**
- Story 過大，無法在 Sprint 內完成
- Acceptance Criteria 模糊
- 忽略 Story 間依賴關係

**5. Sprint 規劃**
- Sprint 範圍過大
- 未考慮風險緩衝
- 忽視技術債務處理

---

## 📞 需要幫助？

### 卡在某個階段
使用以下指令尋求幫助：
```
「我在 [階段名稱] 遇到困難，具體是 [描述問題]」
```

### 想跳過某個階段
如果團隊已有部分產出，可以說明：
```
「我們已經有 [文件名稱]，請直接從 [階段名稱] 開始」
```

### 需要調整流程
如果需要客製化流程：
```
「我們團隊的特殊情況是 [描述]，需要調整 [哪個部分]」
```

---

## 📚 實際案例走查

> 💡 **學習價值**: 透過真實專案案例,了解 Greenfield SOP 的實際應用、常見挑戰與解決方案。

### 案例 1: 新創電商平台 MVP 開發

**專案背景**:
- **專案類型**: Web App (電商平台)
- **團隊規模**: 3 人 (1 全端開發 + 1 前端 + 1 後端)
- **技術棧**: Next.js 14, TypeScript, PostgreSQL, Stripe, Vercel
- **專案週期**: 6 週 (規劃 1 週 + 開發 4 週 + 測試部署 1 週)
- **專案目標**: 快速驗證「訂閱制手工藝品電商」商業模式,目標 3 個月內獲得 100 名付費訂閱用戶

**執行過程** (依 SOP 階段):

#### 階段 1-2: 啟動與需求提取 (實際耗時: 4 天)
- ✅ **完成項目**:
  - 使用 User Story Mapping 工作坊識別出 3 大核心功能 (商品瀏覽、訂閱管理、支付)
  - 定義 MVP 範圍: 20 個 User Stories (Must-have: 12, Should-have: 8)
  - 建立 Product Vision Board 確認目標市場
- ⚠️ **遇到問題**: 創辦人希望第一版包含「AI 推薦系統」,超出 MVP 範圍
- 💡 **解決方案**: 使用 MoSCoW 方法說服創辦人將 AI 功能移至 v2.0,先用「編輯精選」替代
- 📊 **階段產出**: PRD (8 頁)、User Story Map、20 個詳細 User Stories

#### 階段 3-5: 技術選型與架構設計 (實際耗時: 3 天)
- ✅ **完成項目**:
  - 技術選型: Next.js (SSR + ISR 提升 SEO)、PostgreSQL (關聯資料)、Stripe (快速整合支付)
  - 系統架構: Vercel 部署 (零維運成本)、Supabase (PostgreSQL + Auth + Storage)
  - 決策記錄: 使用 ADR 記錄「為何選 Next.js 而非 React SPA」
- ⚠️ **遇到問題**: 團隊對 Next.js 13 App Router 不熟悉
- 💡 **解決方案**: 投入 1 天時間全團隊共學 Next.js 官方教學,建立 Demo 專案練習
- 📊 **階段產出**: FRD (12 頁)、系統架構圖、資料庫 Schema (12 個資料表)、3 份 ADR

#### 階段 6-7: 詳細設計與 Sprint 規劃 (實際耗時: 2 天)
- ✅ **完成項目**:
  - 設計 12 個 API 端點規格 (OpenAPI 3.0 格式)
  - 規劃 4 個 2 週 Sprints (實際執行 2 個 2 週 Sprints 完成 MVP)
  - 定義 Acceptance Criteria (平均每個 Story 3-5 條 AC)
- ⚠️ **遇到問題**: Stripe 訂閱機制比預期複雜 (Webhook、訂閱狀態管理)
- 💡 **解決方案**: 提前 1 天進行 Stripe 技術 Spike,建立 POC 驗證可行性
- 📊 **階段產出**: SRD (18 頁)、12 個 API 規格文件、Sprint Backlog

#### 階段 8-9: 開發準備與專案移交 (實際耗時: 1 天)
- ✅ **完成項目**:
  - 建立 GitHub Repository + GitHub Projects 看板
  - 配置 CI/CD: GitHub Actions (自動測試 + Vercel 部署)
  - 建立開發環境: Docker Compose (PostgreSQL + Redis)
  - 團隊 Kickoff Meeting: 確認 Definition of Done
- 📊 **階段產出**: GitHub Projects 配置完成、CI/CD Pipeline、開發環境文檔

**關鍵經驗**:
- 💡 **成功經驗 1**: User Story Mapping 工作坊幫助團隊快速達成 MVP 共識,避免範圍蔓延
- 💡 **成功經驗 2**: 技術 Spike 提前驗證 Stripe 整合,避免開發期間卡關
- 💡 **成功經驗 3**: ADR 記錄技術決策原因,新成員加入時快速了解背景
- ⚠️ **避坑指南 1**: 創辦人往往低估 MVP 範圍,需要用 MoSCoW 方法明確優先級
- ⚠️ **避坑指南 2**: 新技術棧 (Next.js App Router) 需要預留學習時間,不要高估團隊熟悉度
- ⚠️ **避坑指南 3**: 第三方服務 (Stripe) 的複雜度常被低估,建議提前進行技術 Spike
- 🔄 **流程調整**: 原訂 3 個 Sprints,因 MVP 範圍精簡,實際 2 個 Sprints 完成核心功能

**量化成果**:
- **規劃時間**: 10 天 (原估 14 天,效率提升 29%)
- **MVP 開發週期**: 4 週完成 (原估 6 週)
- **文檔完整度**: PRD/FRD/SRD 三份文檔齊全,總計 38 頁
- **技術債**: 0 個已知重大技術債 (因規劃充分)
- **團隊滿意度**: 9/10 (團隊回饋: 流程清晰、溝通順暢)
- **商業成果**: 上線後 6 週獲得 87 名訂閱用戶 (目標 100 名,達成率 87%)

---

### 案例 2: SaaS 產品 MVP - 團隊協作工具

**專案背景**:
- **專案類型**: Web App (SaaS - 團隊協作工具)
- **團隊規模**: 5 人 (1 PM + 2 前端 + 1 後端 + 1 QA)
- **技術棧**: React, Node.js, MongoDB, WebSocket, AWS
- **專案週期**: 8 週
- **專案目標**: 驗證「遠端團隊即時協作白板」市場需求

**執行過程摘要**:

#### 階段 1-3: 需求與技術選型 (6 天)
- ✅ **成功**: Persona 分析識別出 3 類核心使用者 (PM、設計師、工程師)
- ⚠️ **挑戰**: WebSocket 即時同步技術複雜度高
- 💡 **解決**: 使用成熟方案 Socket.io,避免自建即時同步引擎
- 📊 **產出**: PRD (10 頁)、FRD (15 頁)、技術 POC

#### 階段 4-6: 架構設計與 API 規劃 (5 天)
- ✅ **成功**: 採用 CRDT (Conflict-free Replicated Data Types) 處理多人編輯衝突
- ⚠️ **挑戰**: MongoDB 對 CRDT 支援不足
- 💡 **解決**: 改用 PostgreSQL + JSONB 欄位儲存 CRDT 狀態
- 📊 **產出**: SRD (20 頁)、15 個 API 規格

**關鍵經驗**:
- 💡 **成功經驗**: 技術 POC 及早發現 MongoDB 限制,避免開發期間重構
- ⚠️ **避坑指南**: 即時協作功能的技術複雜度常被低估,需額外 30-50% 緩衝時間
- 🔄 **流程調整**: 原訂使用 NoSQL,實際改用 PostgreSQL 以支援複雜查詢

**量化成果**:
- **規劃時間**: 11 天
- **技術風險降低**: 透過 POC 提前發現 2 個重大技術風險
- **架構調整成本**: 因及早發現問題,架構調整僅花費 1 天 (vs 開發期間調整需 1-2 週)

---

## 🎓 相關資源

- [Greenfield Prompt Templates](../../prompts/scenario-prompts/greenfield-prompts.md)
- [平台特化 Agent 說明](../../agent/specialized/)
- [文檔模板](../../docs_template/)
- [範例專案](./examples/)

---

**下一步**：準備好材料後，執行 [階段 1](#階段-1啟動和情境確認-30-分鐘) 開始你的新專案開發旅程！

---

## AutoClaude 自動化執行（Phase Z / v0.02 新增）

> 規格凍結（SPEC_FROZEN）後，本場景的 AT 契約可交由 AutoClaude 引擎自動執行實作與雙重驗證。
> 標準作業全文：`workflow/sdd-autoclaude-bridge/SDD_AUTOCLAUDE_BRIDGE.md`；
> 翻譯保真規則：`governance/rules/R-9.38-playbook-translation-fidelity.yaml`。

1. **編譯**（AutoClaude/ 目錄）：`python -m autoclaude.tools.sdd_compile --spec-dir <docs path> --out playbooks/sdd_bridge.yaml`
   - 規格未凍結 → exit 2 拒絕（Spec-First 硬閘）；weak_regex 斷言入 audit log。
2. **人工 review** 生成的 playbook YAML（SCG-4 精神：生成物 = 待審工件）。
3. **執行**：`python -m autoclaude playbooks/sdd_bridge.yaml` — SddGovernancePlugin 自動守 SCG 閘門、記帳契約違反、防規格 drift。
4. 🔴 人工確認閘門不可由自動化跳過（Rule 8）；ESCALATION 後必等人工。
