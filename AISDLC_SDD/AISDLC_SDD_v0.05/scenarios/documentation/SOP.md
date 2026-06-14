# Documentation 技術文檔撰寫 SOP

**版本**: v0.01 | **最後更新**: 2026-02-12
> 📝 **關於範例連結說明**:
> 本 SOP 中部分連結（如 `docs/architecture/overview.md`、`docs/api/overview.md`、`CONTRIBUTING.md`）為示例性質，
> 展示一般專案的文檔結構。實際使用時，請根據您的專案結構調整路徑。

## 🎯 情境概述

**適用場景**：技術文檔建立、API 文檔生成、開發者指南撰寫、架構文檔維護

**預計時間**:
- 📋 **AISDLC 規劃階段**: 3-4 小時
  - **規劃時間** (AI 分析 + 人工確認): 3-4 小時
  - **執行時間** (依專案規模):
    - 小型專案: 1 週 (README + API 文檔)
    - 中型專案: 1-2 週 (完整文檔站 + 開發者指南)
    - 大型專案: 2-4 週 (多語言文檔系統 + 影片教學)
- 🔨 **實際執行階段**: 1-2 週 (依文檔範圍而定)

> 💡 **時間估算說明**:
> - **規劃時間**指使用 AISDLC 流程進行文檔架構設計、內容規劃、風格指南制定的時間
> - **執行時間**指實際撰寫技術文檔的時間
> - 小型專案指基礎文檔(README + 快速開始 + API 基本說明)
> - 中型專案指完整文檔(API 詳細文檔 + 架構文檔 + 開發指南 + FAQ)
> - 大型專案指企業級文檔(多版本文檔站 + 多語言支援 + 互動式教學 + 影片教學)

**涉及角色**：Technical-Writer, SA, SD, Dev-Senior, Security-Engineer (選用), Compliance-Officer (選用), SD-Mobile-Architect (選用)

**最終產出**：文檔架構 + README + API 文檔 + 開發者指南 + 架構文檔 + 故障排除指南 + 安全與合規文檔 (選用)

---

## 🤝 協作模式 (Phase 2: v0.03)

### 主要協作模式

#### 1. Sequential-Handoff (順序交接) + Peer-Review (同儕審查)
- **主導 Agent**: Technical-Writer
- **內容提供**: SA (功能文檔), SD (架構文檔)
- **審查角色**: Dev-Senior ⭐ (技術審查)
- **使用階段**: 全流程
- **模式說明**: 順序產出文檔，結合同儕審查確保品質

#### 2. Sequential-Handoff + Peer-Review 流程
```
SA/SD 產出技術內容
    ↓
Technical-Writer 轉化為文檔
    ↓
Dev-Senior peer review ⭐
    ↓
Technical-Writer 修訂
    ↓
> 🔴 **人機協作點：文檔最終批准**
>
> **AI 提供**：
> - 修訂後的技術文檔
>
> **需人工確認**：
> - ✅ 文檔內容準確無誤
> - ✅ 技術細節正確
> - ✅ 範例程式碼可執行
>
> **產出文件**：
> - 已批准的技術文檔
```

### 第二階段優化
- **新增**: dev-senior 為 Supporting Agent
- **理由**: 複雜技術文檔需要資深開發者審查
- **貢獻**: 深度技術細節審查、代碼範例、技術準確性驗證

#### 4. Security-Documentation 協作模式 (Stage 6, 選用) ⭐ v0.01 新增
- **觸發條件**: 專案涉及敏感資料、合規要求、安全認證時
- **載入 Agents**: Security-Engineer + Compliance-Officer + SD-Mobile-Architect (如適用)
- **模式說明**: Technical-Writer 主導撰寫，安全/合規專家提供專業內容

```
Security-Engineer 提供安全架構/威脅模型
    ↓
Compliance-Officer 提供合規要求/差距分析
    ↓
SD-Mobile-Architect 提供行動端安全規範 (如適用)
    ↓
Technical-Writer 整合撰寫安全合規文檔
    ↓
> 🔴 **人機協作點：安全合規文檔批准**
>
> **需人工確認**：
> - ✅ 安全架構涵蓋認證/授權/加密
> - ✅ 威脅模型覆蓋主要攻擊面
> - ✅ 合規對照表對應適用法規
```

### 次要協作模式

#### 3. Iterative-Refinement (迭代精煉)
- **使用階段**: 根據審查意見持續改進文檔
- **模式說明**: 多輪審查和修訂直到達到品質標準

---

## 📋 Skills 整合對照表

> 下表列出 Documentation 各階段建議搭配的 Claude Code Skills，確保每個步驟都能觸發正確的自動化輔助。

| Skill | 階段 1<br>盤點規劃 | 階段 2<br>核心文檔 | 階段 3<br>開發指南 | 階段 4<br>故障排除 | 階段 5<br>版本管理 | 階段 6<br>安全合規 | 說明 |
|-------|:---:|:---:|:---:|:---:|:---:|:---:|------|
| `/documentation-api` | | ✅ | ✅ | | | | API 文檔生成（OpenAPI/Swagger） |
| `/sa-analyst` | ✅ | ✅ | | | | | 需求文檔分析與撰寫 |
| `/sd-architect` | ✅ | ✅ | | | | | 架構文檔（C4 Model） |
| `/code-review` | | | ✅ | | | | 程式碼範例品質審查 |
| `/integration-database` | | ✅ | ✅ | | | | 資料庫文檔（PostgreSQL Schema） |
| `/devops-github-actions` | | | | | ✅ | | Docs as Code CI/CD Pipeline |
| `/devops-docker` | | | | ✅ | | | 部署文檔（Docker 環境） |
| `/security-audit` | | | | | | ✅ | 安全架構文檔（OWASP Top 10） |
| `/compliance-audit` | | | | | | ✅ | 合規對照文檔（GDPR/PCI-DSS） |
| `/mobile-development` | | ✅ | ✅ | | | ✅ | 行動端文檔（Android/macOS） |
| `/qa-testing` | | | | | | | 文檔驗收測試（準確性驗證） |
| `/integration-oauth` | | ✅ | | | | ✅ | 認證授權文檔（OAuth 2.0） |

---

## 📋 前置準備檢查清單

### 必要材料
- [ ] 專案代碼庫存取權限
- [ ] 系統架構資訊
- [ ] API 規格 (OpenAPI/Swagger)
- [ ] 目標讀者定義 (開發者/使用者/維運人員)
- [ ] 文檔目標和範圍

### 選擇性材料
- [ ] 現有文檔 (如有)
- [ ] 使用者回饋和常見問題
- [ ] 架構決策記錄 (ADR)
- [ ] 技術債清單
- [ ] 設計稿或原型

### 安全合規文檔材料 (Stage 6 觸發時需要) ⭐ v0.01 新增
- [ ] 現有安全政策或安全架構文檔
- [ ] 適用法規/標準清單 (個資法、PCI-DSS、ISO 27001 等)
- [ ] 威脅模型或風險評估報告 (如有)
- [ ] 滲透測試報告 (如有)
- [ ] 第三方整合清單 (含安全等級)
- [ ] 行動端安全需求 (如涉及 Android/iOS/macOS)

---

## 🔧 材料缺失應對方案

> 💡 **現實情況**: 文檔專案常因代碼缺乏註解或系統複雜而難以撰寫。以下提供實用的替代方案。

| 缺失材料 | 影響程度 | 應對方案 | 預計額外時間 |
|---------|---------|---------|-------------|
| **現有文檔** | 🔴 高 | • **方案 1**: 使用 Code-Analyzer 掃描代碼生成初步文檔架構<br>• **方案 2**: 訪談開發團隊或系統維護者,記錄口頭說明<br>• **方案 3**: 分析代碼註解和 README,提取現有資訊<br>• **方案 4**: 從零開始建立文檔架構,採用標準模板 | +2-4 小時 |
| **代碼註解** | 🔴 高 | • **方案 1**: 使用 IDE 工具生成基本註解 (JSDoc、docstring)<br>• **方案 2**: 分析代碼邏輯,推測功能用途<br>• **方案 3**: 執行代碼並觀察行為,記錄實際功能<br>• **方案 4**: 請開發者補充關鍵函式註解 | +2-4 小時 |
| **使用者回饋** | 🟡 中 | • **方案 1**: 檢查 Issue Tracker 或客服記錄<br>• **方案 2**: 進行小規模使用者訪談<br>• **方案 3**: 分析常見問題,推測使用者痛點<br>• **方案 4**: 暫時跳過,聚焦技術文檔 | +1-2 小時 |
| **API 規格** | 🟡 中 | • **方案 1**: 使用工具從代碼生成 OpenAPI 規格 (Swagger, Spectral)<br>• **方案 2**: 使用 Postman/Insomnia 逆向工程實測 API<br>• **方案 3**: 掃描路由定義自動生成 API 清單<br>• **方案 4**: 使用網路抓包工具觀察實際 API 呼叫 | +1-3 小時 |
| **架構決策記錄 (ADR)** | 🟢 低 | • **方案 1**: 訪談架構師或資深開發者,記錄重要決策<br>• **方案 2**: 分析 Git 歷史,推測技術選型原因<br>• **方案 3**: 使用 ADR 模板從頭建立<br>• **方案 4**: 暫時跳過,優先建立基礎文檔 | +1-2 小時 |
| **技術債清單** | 🟢 低 | • **方案 1**: 使用代碼分析工具生成 (SonarQube、CodeClimate)<br>• **方案 2**: 團隊討論識別已知技術債<br>• **方案 3**: 檢查 TODO/FIXME 註解<br>• **方案 4**: 暫時跳過,聚焦功能文檔 | +0.5-1 小時 |
| **設計稿或原型** | 🟢 低 | • **方案 1**: 截圖現有系統 UI<br>• **方案 2**: 使用螢幕錄影展示操作流程<br>• **方案 3**: 使用簡易工具重繪關鍵畫面 (Excalidraw)<br>• **方案 4**: 暫時使用文字描述 UI | +0.5-1 小時 |

### 無現有文檔時的應對流程

若系統完全沒有文檔,建議採用「**文檔重建策略**」:

#### 階段 1: 快速建立骨架文檔 (3-6 小時)

1. **README.md** (1 小時)
   ```markdown
   # 專案名稱

   ## 快速開始
   - 如何安裝
   - 如何執行
   - 基本使用範例

   ## 專案結構
   - 目錄說明
   - 主要模組

   ## 聯絡方式
   ```

2. **API 清單** (1-2 小時)
   - 掃描路由定義生成端點清單
   - 使用 Postman 實測並記錄基本請求/回應
   - 生成簡易 API 索引

   ```bash
   # 使用工具自動生成 API 文檔
   # Node.js/Express
   npm install swagger-jsdoc swagger-ui-express

   # Python/Flask
   pip install flasgger

   # Java/Spring Boot
   # 使用 Springdoc OpenAPI
   ```

3. **架構概覽** (1-2 小時)
   - 使用工具生成依賴關係圖
   - 繪製簡易系統架構圖 (C4 Level 1)
   - 記錄主要技術棧

   ```bash
   # 生成依賴關係圖
   # JavaScript
   npx madge --image graph.png src/

   # Python
   pydeps myproject --max-bacon 2 -o deps.png
   ```

4. **配置說明** (30 分鐘)
   - 列出環境變數
   - 配置檔說明
   - 外部依賴清單

#### 階段 2: 補充核心文檔 (4-8 小時)

1. **開發者指南** (2-3 小時)
   - 開發環境設定
   - 程式碼風格
   - Git workflow
   - 測試執行

2. **API 詳細文檔** (2-3 小時)
   - 每個端點的詳細說明
   - 請求/回應範例
   - 錯誤碼說明
   - 認證方式

3. **故障排除** (1-2 小時)
   - 常見問題 FAQ
   - 錯誤訊息解釋
   - 日誌查看方法

### 無代碼註解時的應對流程

若代碼缺乏註解,建議採用「**逆向文檔策略**」:

#### 方法 A: 動態分析 (推薦) - 2-4 小時

1. **執行並觀察**
   - 執行系統,記錄實際行為
   - 使用除錯工具追蹤執行流程
   - 記錄輸入輸出範例

2. **API 實測**
   ```bash
   # 使用 Postman Collection Runner
   # 記錄所有 API 的實際回應

   # 或使用 curl
   curl -X GET https://api.example.com/users | jq '.'
   ```

3. **生成行為文檔**
   - 記錄「實際功能」而非「程式碼邏輯」
   - 使用截圖和範例說明

#### 方法 B: 靜態分析 - 1-2 小時

1. **使用 IDE 工具**
   - VS Code: 使用 Outline View 查看結構
   - IntelliJ: 使用 Structure Tool Window
   - 生成類別圖和方法清單

2. **自動生成基礎註解**
   ```javascript
   // VS Code Extension: Document This
   // 自動生成 JSDoc

   // Python: 使用 Sphinx
   sphinx-apidoc -o docs/source/ myproject/
   ```

### 無 API 規格時的快速生成

若缺少 API 文檔,建議採用「**API 文檔生成策略**」:

#### 工具 A: Swagger/OpenAPI 自動生成 - 1-2 小時

```javascript
// Node.js/Express 範例
const swaggerJsdoc = require('swagger-jsdoc');
const swaggerUi = require('swagger-ui-express');

const options = {
  definition: {
    openapi: '3.0.0',
    info: {
      title: 'My API',
      version: '1.0.0',
    },
  },
  apis: ['./routes/*.js'], // 掃描路由檔案
};

const specs = swaggerJsdoc(options);
app.use('/api-docs', swaggerUi.serve, swaggerUi.setup(specs));
```

#### 工具 B: Postman Collection 匯出 - 30 分鐘

1. 使用 Postman 實測所有 API
2. 組織成 Collection
3. 匯出為 OpenAPI 格式
4. 使用 Postman 自動生成文檔

#### 工具 C: 網路抓包分析 - 1 小時

```bash
# 使用 mitmproxy 抓取 API 請求
mitmproxy --set flow_detail=3

# 或使用瀏覽器 DevTools
# Network Tab → Export as HAR → 轉換為 API 文檔
```

### 文檔完全缺失時的最小方案 (緊急情況)

若時間極度緊迫,建議採用「**最小文檔集策略**」- 4 小時:

1. **README.md** (1 小時)
   - 專案簡介
   - 安裝步驟
   - 執行指令
   - 聯絡方式

2. **QUICKSTART.md** (1 小時)
   - 5 分鐘快速開始
   - 基本使用範例
   - 常見問題

3. **API_REFERENCE.md** (1 小時)
   - 端點清單 (URL、Method、簡述)
   - 1-2 個完整範例
   - 認證方式

4. **TROUBLESHOOTING.md** (1 小時)
   - 常見錯誤和解法
   - 日誌查看位置
   - 聯絡支援方式

**成果**: 雖不完整,但足以讓新開發者快速上手

---

## 🛠️ 免費工具替代方案

> 💡 **成本考量**: 文檔生成與管理需要文檔編輯、協作、版本控制、網站生成等工具，商業方案成本高昂（Confluence $5.75-11/月/人, GitBook $6.70-12.50/月/人）。以下提供功能相近的免費/開源替代方案。

### 文檔生成與管理工具對照表

| 工具類別 | 商業方案 | 免費/開源替代 | 功能對比 | 適用場景 |
|---------|---------|-------------|---------|---------|
| **文檔協作平台** | Confluence<br>Notion Teams<br>Coda | **Notion Free**<br>**BookStack**<br>**Outline**<br>**Wiki.js** | 免費版功能足夠<br>(Notion Free 無頁數限制) | 團隊知識庫<br>技術文檔協作<br>專案文檔管理 |
| **靜態網站生成** | GitBook Pro<br>ReadMe.io | **Docusaurus**<br>**VuePress**<br>**MkDocs**<br>**Docsify** | 完全免費<br>功能完整 | 技術文檔網站<br>API 文檔<br>開源專案文檔 |
| **API 文檔** | ReadMe.io<br>Redocly Enterprise | **Swagger UI**<br>**Redoc**<br>**RapiDoc**<br>**Scalar** | 免費且功能完整 | OpenAPI 文檔<br>互動式 API 文檔<br>自動生成 |
| **圖表繪製** | Lucidchart<br>Draw.io Desktop | **Draw.io (Web)**<br>**Mermaid.js**<br>**PlantUML**<br>**Excalidraw** | 完全免費<br>功能強大 | 架構圖<br>流程圖<br>ER Diagram<br>UML 圖 |
| **Markdown 編輯器** | Typora Pro<br>Ulysses | **Obsidian**<br>**VS Code**<br>**MarkText**<br>**Zettlr** | 開源方案完整 | 文檔撰寫<br>知識管理<br>筆記整理 |
| **版本控制** | Confluence Versioning<br>Notion Versioning | **Git + GitHub/GitLab**<br>**DokuWiki** | 版本控制更強大<br>完全免費 | 文檔版本管理<br>變更追蹤<br>協作審查 |
| **搜尋引擎** | Algolia DocSearch<br>Swiftype | **Algolia DocSearch (OSS)**<br>**Meilisearch**<br>**Lunr.js** | DocSearch 對開源免費 | 文檔全文搜尋<br>快速導航<br>關鍵字搜尋 |
| **文檔測試** | Vale Server<br>Grammarly Business | **Vale (OSS)**<br>**textlint**<br>**markdownlint** | 開源版功能完整 | 文檔風格檢查<br>術語一致性<br>Markdown Lint |

### 推薦工具組合 (依文檔類型)

| 文檔類型 | 協作平台 | 網站生成 | 圖表工具 | 編輯器 | 版本控制 | 年度成本 |
|---------|---------|---------|---------|--------|---------|---------|
| **技術文檔** | BookStack | Docusaurus | Mermaid.js | VS Code | Git + GitHub | $0 |
| **API 文檔** | Notion Free | Redoc / Scalar | Draw.io | VS Code | Git + GitHub | $0 |
| **內部知識庫** | Outline / Wiki.js | - | Excalidraw | Obsidian | Git (optional) | $0 (自架) |
| **使用者手冊** | GitBook Free | VuePress / Docsify | PlantUML | MarkText | Git + GitHub | $0 |

### 成本對比

| 方案 | 月度成本 (10人團隊) | 年度成本 | 工具組合 | 維護成本 |
|------|-------------------|---------|---------|---------|
| **完全免費 (雲端)** | $0 | $0 | Notion Free + GitHub + Docusaurus + Mermaid | 低 (雲端服務) |
| **完全免費 (自架)** | $0 | $0 | BookStack + GitLab + MkDocs + PlantUML | 中 (需維護) |
| **混合方案** | $50-100 | $600-1,200 | Notion + GitBook Teams + 其他免費 | 低 |
| **全商業方案** | $200-500 | $2,400-6,000 | Confluence + GitBook Pro + Lucidchart | 低 (廠商支援) |

### 各階段工具建議

#### 文檔規劃階段
- **架構設計**: Draw.io / Mermaid.js / C4-PlantUML
- **內容大綱**: Notion Free / Obsidian / MarkMap
- **協作討論**: GitHub Discussions / GitLab Issues
- **模板管理**: Git Repository / Cookiecutter

#### 文檔撰寫階段
- **技術文檔**: Markdown (VS Code / Obsidian)
- **API 文檔**: Swagger Editor / Stoplight Studio Free
- **使用者文檔**: Notion / BookStack / Docusaurus
- **架構圖**: Mermaid.js / PlantUML / Draw.io
- **流程圖**: Draw.io / Excalidraw / Mermaid.js

#### 文檔審查階段
- **風格檢查**: Vale / textlint / markdownlint
- **拼字檢查**: CSpell / Hunspell
- **連結檢查**: markdown-link-check / linkinator
- **PR Review**: GitHub PR / GitLab MR

#### 文檔發布階段
- **靜態網站**: Docusaurus / VuePress / MkDocs
- **API 文檔**: Redoc / Swagger UI / Scalar
- **部署平台**: Vercel / Netlify / GitHub Pages (免費)
- **搜尋引擎**: Algolia DocSearch (OSS免費) / Meilisearch

#### 文檔維護階段
- **版本控制**: Git + GitHub/GitLab
- **自動化更新**: GitHub Actions / GitLab CI
- **監控變更**: GitHub Webhooks / RSS Feed
- **連結監控**: Broken Link Checker (GitHub Action)

### 推薦文檔網站生成器比較

| 工具 | 技術棧 | 優勢 | 適用情境 | 學習曲線 |
|------|-------|------|---------|---------|
| **Docusaurus** | React | 功能完整、React 生態、版本管理 | 大型技術文檔、多版本 API 文檔 | 中 |
| **VuePress** | Vue.js | 簡單易用、Vue 生態、快速建置 | 中小型專案文檔、部落格 | 低 |
| **MkDocs** | Python | 簡潔、Material 主題美觀 | Python 專案文檔、快速原型 | 低 |
| **Docsify** | JavaScript | 無需建置、動態渲染、輕量 | 快速文檔、小型專案 | 極低 |
| **Nextra** | Next.js | 現代化、靈活、Next.js 生態 | 現代化文檔網站、混合內容 | 中 |

### 文檔自動化工具

#### 從程式碼生成文檔
- **JSDoc** (JavaScript/TypeScript): 從註解生成 API 文檔
- **TypeDoc** (TypeScript): TypeScript 專用文檔生成
- **Sphinx** (Python): Python docstring → 文檔
- **GoDoc** (Go): Go 內建文檔工具
- **Javadoc** (Java): Java 標準文檔工具

#### CI/CD 自動化
- **文檔建置**: GitHub Actions / GitLab CI
- **自動部署**: Vercel / Netlify / GitHub Pages
- **連結檢查**: Broken Link Checker (Action)
- **風格檢查**: Vale (Action) / Super-Linter

#### 文檔品質工具
- **markdownlint**: Markdown 語法檢查
- **textlint**: 文字風格和術語一致性
- **Vale**: 文檔風格指南執行
- **write-good**: 英文寫作建議

---

## 🔒 CI/CD 安全基線（強制前置）

> **⚠️ CRITICAL**: 開始文檔工作前，必須確認 CI/CD Pipeline 已配置基礎安全層級。
> **Documentation 情境安全等級: Basic** (僅 L0)

### Layer 0: Security Baseline（強制）

所有 PR 必須通過以下檢查：

| 檢查項 | 工具 | 阻塞等級 |
|--------|------|---------|
| Secret Detection | TruffleHog / gitleaks | 🔴 永遠阻塞 |
| Dependency Scan (SCA) | Trivy / npm audit | 🔴 Critical/High 阻塞 |
| License Compliance | license-checker | ⚠️ GPL-3.0/AGPL 阻塞 |

📖 **配置範本**: [Layer0_Security_Baseline_Template.md](../../docs_template/scenario_specific/devops/Layer0_Security_Baseline_Template.md)

> **💡 說明**: Documentation 情境為 Basic 等級，僅需 Layer 0 安全基線，不需要 SAST / Container Scan / DAST 增強掃描。

- [ ] Layer 0 Security Baseline 已配置

### 📝 Documentation Pipeline（🔴 強制）

Documentation 情境為文檔 Pipeline 的**核心適用情境**，Doc Lint + Link Check + Build + Deploy **均為強制**。

| 階段 | 觸發時機 | 耗時 | 阻塞策略 |
|------|---------|------|---------|
| **Doc Lint** | 每次 PR（.md 變更） | < 1 分鐘 | 🔴 格式錯誤阻塞 |
| **Link Check (內部)** | 每次 PR | < 2 分鐘 | 🔴 斷裂連結阻塞 |
| **Link Check (外部)** | Nightly | < 30 分鐘 | ⚠️ 僅警告 |
| **Doc Build** | Main 合併後 | < 5 分鐘 | 🔴 失敗通知 |
| **Deploy-Docs** | Main 合併後 | < 5 分鐘 | 🔴 失敗通知 |

**工具推薦**:
| 類型 | 工具 | 說明 |
|------|------|------|
| Markdown Lint | markdownlint-cli2 | 格式一致性 |
| Link Check | lychee | 連結完整性 |
| 拼字檢查 | cspell | 英文拼字（警告） |
| Doc Build | MkDocs Material | 靜態站點生成 |
| Deploy | GitHub Pages | 文檔部署 |

📖 **配置範本**: [Documentation_Pipeline_Template.md](../../docs_template/scenario_specific/devops/Documentation_Pipeline_Template.md)
📄 **CI 範本**: [docs-pipeline.yml](../../docs_template/scenario_specific/devops/github-actions/docs-pipeline.yml)
🔧 **建置流程**: [devops-setup-flow 步驟 0.9](../../workflow/scenario-specific/devops-setup-flow.md)

- [ ] Markdown Lint 已配置（.markdownlint.yml）
- [ ] Link Check 已配置（lychee）
- [ ] 拼字白名單已建立（.cspell.json）
- [ ] Doc Build 工具已選型並配置
- [ ] Deploy-Docs 已配置（GitHub Pages 或等效平台）

### 🔔 Event-Driven Agent Notification（⚠️ 選配）

> Documentation 情境因無程式碼變更，Agent 通知為選配。可配置文檔變更的 Slack 通知。

📖 **配置範本**: [Event_Driven_Agent_Notification_Template.md](../../docs_template/scenario_specific/devops/Event_Driven_Agent_Notification_Template.md)
🔧 **建置流程**: [devops-setup-flow 步驟 0.10](../../workflow/scenario-specific/devops-setup-flow.md)

---

## 🚀 完整執行流程

### 階段 1：文檔現況盤點與規劃 (40-60 分鐘)

#### 步驟 1.1：文檔架構設計 (Technical-Writer + SD)

> 🔴 **人機協作點：文檔架構設計確認**
>
> **AI 提供**：
> - 標準文檔結構建議
> - 文檔類型與目的說明
> - 目標讀者分析
> - 文檔架構圖
>
> **需人工確認**：
> - ✅ 文檔結構符合專案需求
> - ✅ 文檔類型覆蓋完整
> - ✅ 目標讀者定義明確
> - ✅ 架構設計可擴展
>
> **產出文件**：
> - 文檔架構設計 (Documentation Architecture)
> - 目標讀者 Persona
> - 文檔清單與優先順序

#### 步驟 1.2：文檔架構實施 (Technical-Writer + SD)

**標準文檔結構**：
```
docs/
├── README.md                 # 專案概覽和快速開始
├── CONTRIBUTING.md           # 貢獻指南（必要）
├── CHANGELOG.md              # 變更日誌
├── architecture/
│   ├── C4_Level1_Context.md      # 系統情境圖（必要）
│   ├── C4_Level2_Container.md    # 容器圖（必要）
│   ├── C4_Level3_Component.md    # 元件圖（推薦）
│   ├── data-flow.md              # 資料流與外部整合
│   └── adr/                      # 架構決策記錄（必要）
│       ├── ADR_INDEX.md          # ADR 索引
│       ├── ADR-001-tech-stack.md # 技術選型決策
│       └── ADR-002-database.md   # 資料庫選型決策
├── api/
│   ├── overview.md               # API 概覽（認證/版本/Rate Limiting）
│   ├── error_codes.md            # 統一錯誤碼定義（必要）
│   ├── webhook_events.md         # Webhook 事件規格（如有）
│   ├── versioning_strategy.md    # API 版本管理策略
│   ├── auth/
│   │   └── openapi.yaml          # 認證模組 OpenAPI（多模組時每模組獨立）
│   ├── ecommerce/
│   │   └── openapi.yaml          # 電商模組 OpenAPI
│   ├── homestay/
│   │   └── openapi.yaml          # 民宿模組 OpenAPI（如適用）
│   └── [module]/
│       └── openapi.yaml          # 各模組獨立 OpenAPI 規格
├── guides/
│   ├── getting-started.md    # 入門指南（含前置需求清單）
│   ├── development.md        # 開發指南（含 Git 工作流程）
│   ├── deployment.md         # 部署指南
│   └── troubleshooting.md    # 故障排除（含跨模組整合問題）
├── database/
│   ├── ERD_overview.md       # 整體 ERD（必要，見 Step 3.3）
│   ├── schema_overview.md    # Schema 說明（枚舉值/狀態機）
│   └── migration_strategy.md # Migration 策略
└── reference/
    ├── configuration.md      # 配置參考
    └── cli.md                # CLI 命令
```

**🔴 文件盤點強制項目（新增 / 現有系統評估）**：
```yaml
架構文件必要清單:
□ C4 Level 1 (System Context) 存在
□ C4 Level 2 (Container Diagram) 存在
□ ADR 索引存在，主要技術決策均有記錄
□ 系統邊界與外部整合說明完整

API 文件必要清單（多模組系統）:
□ 每個業務模組有獨立 OpenAPI 規格（非全部合併一個檔案）
□ 統一錯誤碼定義文件存在
□ Webhook 事件規格文件存在（若系統有 Webhook）
□ API 版本管理策略已說明

基礎文件必要清單:
□ README.md 包含所有先決條件（版本號明確）
□ CONTRIBUTING.md 存在且步驟完整
□ 快速啟動（5分鐘上手）流程可執行
```

**文檔類型與目的**：

| 文檔類型 | 目標讀者 | 目的 | 範例 |
|---------|---------|------|------|
| **README** | 所有人 | 專案概覽、快速開始 | GitHub README |
| **API 文檔** | 前端開發者、整合夥伴 | API 使用說明 | Stripe API Docs |
| **架構文檔** | 資深開發者、架構師 | 理解系統設計 | C4 Model |
| **開發者指南** | 新加入開發者 | 設定開發環境、貢獻代碼 | CONTRIBUTING.md |
| **使用者手冊** | 終端使用者 | 產品使用說明 | User Guide |
| **故障排除** | 維運人員、開發者 | 問題診斷和解決 | Troubleshooting |

---

### 階段 2：核心文檔撰寫 (1.5-2 小時)

> 🔴 **人機協作點：核心文檔審查確認**
>
> **AI 提供**：
> - README.md 初稿
> - API 文檔（OpenAPI 規格）
> - 架構文檔（C4 Model）
>
> **需人工確認**：
> - ✅ README 清晰易懂，快速開始可執行
> - ✅ API 文檔完整，範例正確
> - ✅ 架構文檔準確反映系統設計
> - ✅ 技術術語使用一致
>
> **產出文件**：
> - README.md
> - API 文檔 (OpenAPI/Swagger)
> - 架構文檔 (C4 Model)

#### 步驟 2.1：README.md 撰寫

**優秀 README 結構**：
```markdown
# 專案名稱

[![CI](https://github.com/user/repo/workflows/CI/badge.svg)](https://github.com/user/repo/actions)
[![Coverage](https://codecov.io/gh/user/repo/branch/main/graph/badge.svg)](https://codecov.io/gh/user/repo)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

> 一句話專案描述

## ✨ 特色

- 特色 1：簡短描述
- 特色 2：簡短描述
- 特色 3：簡短描述

## 📸 截圖 / 示範

![Demo](./docs/images/demo.gif)

## 🚀 快速開始

### 前置需求

- Node.js >= 18
- PostgreSQL >= 14
- Redis >= 7

### 安裝

\```bash
# Clone 專案
git clone https://github.com/user/repo.git
cd repo

# 安裝依賴
npm install

# 配置環境變數
cp .env.example .env
# 編輯 .env 填入你的配置

# 執行資料庫遷移
npm run migrate

# 啟動開發伺服器
npm run dev
\```

專案將在 http://localhost:3000 運行

## 📖 文檔

- [架構文檔](docs/architecture/overview.md)
- [API 文檔](docs/api/overview.md)
- [開發指南](docs/guides/development.md)
- [部署指南](docs/guides/deployment.md)

## 🧪 測試

\```bash
# 執行所有測試
npm test

# 測試覆蓋率
npm run test:coverage

# E2E 測試
npm run test:e2e
\```

## 🚢 部署

詳見 [部署指南](docs/guides/deployment.md)

## 🤝 貢獻

歡迎貢獻！請先閱讀 [CONTRIBUTING.md](CONTRIBUTING.md)

## 📝 授權

本專案採用 [MIT License](LICENSE)

## 👥 聯絡

- 作者：Your Name
- Email: your.email@example.com
- GitHub: [@username](https://github.com/username)
```

**🔴 多模組系統 README 強制項目** ⭐ v0.01 新增：
```yaml
多模組/四合一系統 README 必須包含:
□ 系統架構說明（哪些模組、模組間關係）
□ 完整前置需求清單（JDK 版本 + Node 版本 + Docker 版本 + DB 版本，每個均標明版本號）
□ 各模組啟動順序說明（避免依賴問題）
□ 模組依賴關係圖或說明（誰依賴誰）
□ CONTRIBUTING.md 連結（必要）
□ 快速啟動：10 分鐘內可驗證系統正常運作

❌ 常見缺失（必須確認不存在）:
□ 前置需求只寫「安裝 JDK」但不寫版本
□ 只有後端啟動說明，缺少前端 / DB 初始化
□ 無模組架構說明（讀者不知道有幾個 Service）
```

#### 步驟 2.2：API 文檔生成

**OpenAPI (Swagger) 規格**：
```yaml
# openapi.yaml
openapi: 3.0.0
info:
  title: My API
  version: 1.0.0
  description: API 說明

servers:
  - url: https://api.example.com/v1
    description: Production
  - url: https://staging-api.example.com/v1
    description: Staging

paths:
  /users:
    post:
      summary: 創建使用者
      description: 創建新的使用者帳號
      tags:
        - Users
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/CreateUserRequest'
            example:
              email: user@example.com
              password: SecurePass123!
              name: John Doe

      responses:
        '201':
          description: 使用者創建成功
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/User'
        '400':
          description: 請求資料無效
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Error'
        '409':
          description: Email 已存在

components:
  schemas:
    CreateUserRequest:
      type: object
      required:
        - email
        - password
        - name
      properties:
        email:
          type: string
          format: email
        password:
          type: string
          minLength: 8
        name:
          type: string
          minLength: 1

    User:
      type: object
      properties:
        id:
          type: string
          format: uuid
        email:
          type: string
        name:
          type: string
        createdAt:
          type: string
          format: date-time

    Error:
      type: object
      properties:
        code:
          type: string
        message:
          type: string
```

> **⚠️ API 文檔版本控制 (API Documentation Versioning)**
>
> API 演進時需同步維護文檔版本:
> ```yaml
> # 多版本文檔結構
> docs/api/
>   v1/
>     openapi.yaml
>     README.md
>   v2/
>     openapi.yaml  # Breaking changes
>     CHANGELOG.md  # 列出與 v1 差異
> ```
> **工具**: Redoc, Swagger UI 支援多版本切換

> **⚠️ 文檔測試 (Documentation Testing)**
>
> 確保文檔範例可執行:
> ```python
> # doctest 範例
> def add(a, b):
>     """
>     加法函數
>     
>     >>> add(2, 3)
>     5
>     >>> add(-1, 1)
>     0
>     """
>     return a + b
> 
> # 執行: python -m doctest mymodule.py
> ```
> **工具**: Jest (JS), doctest (Python), rustdoc (Rust)

> **⚠️ 互動式文檔工具 (Interactive Documentation)**
>
> 提供可執行的 API 範例:
> - **Swagger UI**: 內建 Try it out
> - **Postman Collections**: 可匯入測試
> - **Stoplight**: API 設計 + 互動文檔
> - **ReadMe.io**: 整合式文檔平台
> ```yaml
> # Swagger UI 配置
> swagger_ui:
>   url: "/openapi.yaml"
>   deepLinking: true
>   displayRequestDuration: true
>   tryItOutEnabled: true  # 啟用互動測試
> ```

```

**從代碼自動生成 API 文檔**：
```javascript
// 使用 JSDoc 註解
/**
 * Create a new user
 *
 * @route POST /api/users
 * @group Users - User management operations
 * @param {CreateUserRequest.model} user.body.required - User data
 * @returns {User.model} 201 - User created successfully
 * @returns {Error.model} 400 - Invalid request data
 * @returns {Error.model} 409 - Email already exists
 * @security JWT
 */
app.post('/api/users', async (req, res) => {
  // Implementation
});
```

**🔴 多模組系統 API 文件強制規格** ⭐ v0.01 新增：
```yaml
多模組系統 API 文件必要清單:
□ 每個業務模組有獨立 OpenAPI YAML（避免單一 3000 行規格檔）
  範例: api/auth/openapi.yaml, api/ecommerce/openapi.yaml, api/homestay/openapi.yaml
□ 統一錯誤碼文件（error_codes.md）- 定義所有 HTTP 狀態碼與 業務錯誤碼
  範例: { "code": "PAID_CONTENT_ACCESS_DENIED", "httpStatus": 403, "message": "..." }
□ Webhook 事件規格（webhook_events.md）- 若系統有 Webhook
  必須說明: 事件名稱、Payload 格式、HMAC 簽名驗證方式、重試策略
□ API 版本管理策略（versioning_strategy.md）
  必須說明: 版本策略（URL v1/v2 或 Header）、棄用流程、Breaking Change 定義
□ Rate Limiting 規則（在 overview.md 或獨立文件）
  必須說明: 各端點限制（req/min）、超限回應格式（429 + Retry-After header）

❌ 常見缺失（多模組合一規格的反模式）:
□ 四合一平台只有一個 openapi.yaml → 應拆分為各模組獨立規格
□ 付費內容 API 無認證說明 → 必須明確標示 security: [bearerAuth]
□ Webhook 無 HMAC 驗證說明 → 安全風險（見 Security SOP）
```

#### 步驟 2.3：架構文檔 (C4 Model)

**Level 1: System Context**
```markdown
# 系統架構文檔

## 系統上下文圖 (System Context)

\```
[使用者] --使用--> [電商平台]
[電商平台] --呼叫--> [支付網關]
[電商平台] --呼叫--> [物流 API]
[電商平台] --發送--> [Email 服務]
\```

## 容器圖 (Container Diagram)

\```
[Web 瀏覽器] --HTTPS--> [Load Balancer]
[Load Balancer] ---> [Web 應用] (Node.js)
[Web 應用] ---> [API 伺服器] (Express)
[API 伺服器] ---> [PostgreSQL]
[API 伺服器] ---> [Redis Cache]
[API 伺服器] ---> [Message Queue]
[Worker] ---> [Message Queue]
\```

## 關鍵設計決策

### ADR-001: 使用 PostgreSQL 作為主資料庫

**狀態**: 已接受

**背景**: 需要選擇關聯式資料庫

**決策**: 選擇 PostgreSQL

**理由**:
- 成熟穩定
- 豐富的資料類型 (JSON, Array)
- 強大的查詢能力
- 開源免費

**後果**:
- 需要學習 PostgreSQL 特有功能
- 水平擴展較複雜
```

**🔴 架構文件強制規格** ⭐ v0.01 新增：
```yaml
C4 Model 強制層級:
□ Level 1 (System Context) - 必要
  內容: 系統、使用者角色、外部依賴（支付/推播/Email 等）
□ Level 2 (Container Diagram) - 必要
  內容: Next.js / Spring Boot / PostgreSQL / Redis / Android App 等容器
□ Level 3 (Component Diagram) - 推薦（複雜模組）
  內容: 各模組的主要元件與職責

ADR（架構決策記錄）強制項目:
□ ADR 索引（ADR_INDEX.md）存在
□ 技術選型主要決策均有記錄，包含:
  - 技術堆疊選型（為何選 Spring Boot + Next.js + PostgreSQL）
  - 多模組整合策略（Monorepo vs 多 Repo）
  - 認證機制選型（JWT 有效期、Refresh Token 策略）
  - 資料庫設計重大決策（如四合一共用 users 表設計）

ADR 標準模板（每筆 ADR 必須包含）:
  - 標題: ADR-XXX: [決策摘要]
  - 狀態: Proposed / Accepted / Deprecated / Superseded
  - 背景: 為什麼需要做這個決策
  - 決策: 選擇的方案
  - 考慮方案: 列出其他候選方案與取捨
  - 後果: 正面影響 + 負面影響 + 風險
```

---

### 階段 3：開發者指南與範例 (1-2 小時)

> 🔴 **人機協作點：開發者指南審查確認**
>
> **AI 提供**：
> - 開發環境設定指南
> - Git 工作流程說明
> - 程式碼範例
> - 測試執行指南
>
> **需人工確認**：
> - ✅ 設定步驟完整且可執行
> - ✅ Git 工作流程符合團隊實踐
> - ✅ 程式碼範例正確且實用
> - ✅ 測試指南清晰明確
> - ✅ 資料庫文件（ERD/Schema/Migration）存在且正確（Step 3.3）
> - ✅ 行動端架構文件存在且 QR Code 規格已定義（Step 3.4，如適用）
>
> **產出文件**：
> - 開發者指南 (Developer Guide)
> - 貢獻指南 (CONTRIBUTING.md)
> - 程式碼範例集
> - 資料庫文件（ERD / Schema 說明 / Migration 策略 / Seed 說明）⭐ v0.01 新增
> - 行動端架構文件（Android / macOS QR Code 規格 / Mobile API，如適用）⭐ v0.01 新增

#### 步驟 3.1：Getting Started 撰寫

```markdown
# 開發指南

## 設定開發環境

### 1. 安裝依賴

\```bash
# 安裝 Node.js 18+
nvm install 18
nvm use 18

# 安裝專案依賴
npm install
\```

### 2. 配置環境變數

\```bash
cp .env.example .env
\```

編輯 `.env`:

\```env
# 資料庫
DATABASE_URL=postgresql://localhost/myapp_dev

# Redis
REDIS_URL=redis://localhost:6379

# 第三方服務
STRIPE_SECRET_KEY=sk_test_xxx
\```

### 3. 初始化資料庫

\```bash
# 執行遷移
npm run migrate

# 填充種子資料
npm run seed
\```

### 4. 啟動開發伺服器

\```bash
npm run dev
\```

## 專案結構

\```
src/
├── controllers/    # 控制器
├── models/         # 資料模型
├── services/       # 業務邏輯
├── routes/         # 路由定義
├── middlewares/    # 中介軟體
├── utils/          # 工具函式
└── config/         # 配置
\```

## 開發流程

### Git 工作流程

1. 從 `main` 創建 feature branch
   \```bash
   git checkout -b feature/add-user-profile
   \```

2. 開發並提交
   \```bash
   git add .
   git commit -m "feat: add user profile page"
   \```

3. 推送並創建 Pull Request
   \```bash
   git push origin feature/add-user-profile
   \```

4. Code Review 後合併

### Commit Message 規範

遵循 [Conventional Commits](https://www.conventionalcommits.org/)

\```
feat: 新功能
fix: Bug 修復
docs: 文檔更新
style: 代碼格式調整
refactor: 重構
test: 測試相關
chore: 構建/工具變更
\```

## 程式碼風格

使用 ESLint + Prettier

\```bash
# 檢查代碼風格
npm run lint

# 自動修復
npm run lint:fix
\```

## 測試

\```bash
# 單元測試
npm run test:unit

# 整合測試
npm run test:integration

# 測試覆蓋率
npm run test:coverage
\```

## 常見問題

### Q: 資料庫連線失敗

A: 檢查 PostgreSQL 是否運行，DATABASE_URL 是否正確

### Q: Redis 錯誤

A: 確保 Redis 已啟動：`redis-server`
```

#### 步驟 3.2：程式碼範例

```markdown
# API 使用範例

## 認證

### 註冊新使用者

\```javascript
const response = await fetch('https://api.example.com/v1/users', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    email: 'user@example.com',
    password: 'SecurePass123!',
    name: 'John Doe'
  })
});

const data = await response.json();
console.log(data.token); // JWT Token
\```

### 使用 Token 呼叫 API

\```javascript
const response = await fetch('https://api.example.com/v1/profile', {
  headers: {
    'Authorization': `Bearer ${token}`
  }
});

const profile = await response.json();
\```

## 錯誤處理

\```javascript
try {
  const response = await createUser(userData);
} catch (error) {
  if (error.code === 'EMAIL_EXISTS') {
    console.error('Email 已被使用');
  } else if (error.code === 'INVALID_PASSWORD') {
    console.error('密碼強度不足');
  } else {
    console.error('未知錯誤', error);
  }
}
\```
```

#### 步驟 3.3：資料庫文件 (/integration-database) ⭐ v0.01 新增

> **重要性**：資料庫文件是開發者理解系統資料結構、維護資料完整性、安全執行 Schema 變更的核心依據。

> 🔴 **人機協作點：資料庫文件完整性確認**
>
> **AI 提供**：
> - ERD（實體關係圖）- 各模組及跨模組關聯
> - Schema 說明 - 關鍵欄位、枚舉值、狀態機
> - Migration 記錄與 Rollback 策略
> - 索引設計說明
> - 測試資料 Seed 說明
>
> **需人工確認**：
> - ✅ ERD 正確反映現行資料庫結構
> - ✅ 枚舉值與狀態機轉換規則準確
> - ✅ Migration Rollback 方案可執行
> - ✅ 測試 Seed 資料涵蓋各角色與場景
>
> **產出文件**：
> - ERD 文件（各模組 + 跨模組關聯）
> - Schema 說明文件（欄位/枚舉/狀態機）
> - Migration 策略文件
> - 索引設計說明
> - 測試資料 Seed 說明

**資料庫文件結構範例**：
```
docs/07_design/database/
├── ERD_overview.md              # 整體 ERD（跨模組關聯）
├── ERD_ecommerce.md             # 電商模組 ERD
├── ERD_homestay.md              # 民宿模組 ERD
├── ERD_content.md               # 內容發布 ERD（如適用）
├── ERD_knowledge.md             # 知識管理 ERD（如適用）
├── schema_overview.md           # Schema 總覽（關鍵表說明）
├── enum_definitions.md          # 枚舉值統一定義（狀態機）
├── migration_strategy.md        # Migration 策略與 Rollback 方案
├── index_design.md              # 索引設計說明與查詢最佳化
└── test_data_seed.md            # 測試資料 Seed 說明（各角色）

docs/03_testing/
├── test_data_setup.md           # 測試環境資料建置指南
└── test_accounts.md             # 測試帳號清單（各角色）
```

**🔴 資料庫文件強制項目（含電商/支付/訂閱系統）**：
```yaml
必須記錄：
□ ERD 圖（至少模組級別，推薦 dbdiagram.io / Mermaid）
□ 關鍵業務欄位說明（特別是 status/type 枚舉欄位）
□ 四合一跨模組 users 表關聯說明（電商客戶/民宿房客/內容作者/知識訂閱者）
□ 付費內容 access_token/subscription 相關欄位安全說明
□ Flyway Migration 命名規範與版本追蹤策略
□ 軟刪除策略（deleted_at 欄位使用規範）
□ 測試 Seed 資料（各角色：管理員/房東/作者/客戶/訂閱者）
```

#### 步驟 3.4：行動端架構文件（SD-Mobile-Architect，條件觸發）⭐ v0.01 新增

> **⚠️ 觸發條件**：專案含 Android / iOS / macOS 行動端時執行此步驟
> **⚠️ Agent 按需載入**：需載入 SD-Mobile-Architect Agent

> 🔴 **人機協作點：行動端架構文件確認**
>
> **AI 提供**：
> - 行動端 App 架構文件（技術棧選型、架構模式）
> - QR Code 掃描模組規格（掃描流程、格式、有效期）
> - Mobile-specific API 規格（與 Web API 差異）
> - 行動端 Auth Flow 說明（Token 刷新策略）
>
> **需人工確認**：
> - ✅ 技術選型（Android：CameraX + ML Kit vs ZXing）決策記錄
> - ✅ QR Code 格式與有效期設計合理
> - ✅ Mobile API 規格與後端實作一致
> - ✅ Android/macOS 版本相容性矩陣正確
>
> **產出文件**：
> - 行動端架構文件（Android / macOS）
> - QR Code 掃描模組規格
> - Mobile API 規格文件

**行動端文件結構範例**：
```
docs/02_architecture/mobile/
├── android_architecture.md      # Android App 架構（MVVM + Hilt + Room）
├── macos_architecture.md        # macOS App 架構（SwiftUI / AppKit 選型）
├── qr_scanner_spec.md           # QR Code 掃描規格（格式/流程/錯誤處理）
├── mobile_api_spec.md           # Mobile-specific API（差異說明）
├── mobile_auth_flow.md          # Mobile Auth Flow（Token 管理）
├── push_notification_setup.md   # 推播通知設定（FCM / APNs）
└── compatibility_matrix.md      # 版本相容性矩陣（Android / macOS 版本）
```

---

### 階段 4：故障排除與 FAQ (30-40 分鐘)

> 🔴 **人機協作點：故障排除指南審查確認**
>
> **AI 提供**：
> - 常見問題 FAQ
> - 故障排除步驟
> - 日誌查看方法
> - 效能問題診斷
>
> **需人工確認**：
> - ✅ FAQ 覆蓋常見問題
> - ✅ 故障排除步驟可執行
> - ✅ 診斷方法實用有效
> - ✅ 解決方案正確
>
> **產出文件**：
> - 故障排除指南 (Troubleshooting Guide)
> - FAQ 文檔

```markdown
# 故障排除指南

## 常見問題

### 應用程式無法啟動

**症狀**: `npm run dev` 失敗

**可能原因**:
1. Node.js 版本不符
2. 依賴未安裝
3. 環境變數未設定

**解決方法**:
\```bash
# 檢查 Node.js 版本
node --version  # 應該 >= 18

# 重新安裝依賴
rm -rf node_modules package-lock.json
npm install

# 檢查 .env 檔案
cat .env
\```

### 資料庫遷移失敗

**症狀**: `Error: relation "users" already exists`

**解決方法**:
\```bash
# 回滾遷移
npm run migrate:rollback

# 重新執行
npm run migrate
\```

### 測試失敗

**症狀**: 部分測試隨機失敗

**可能原因**: 測試間資料未清理

**解決方法**:
\```javascript
// 每個測試前清理
beforeEach(async () => {
  await db.users.deleteMany({});
});
\```

## 效能問題

### 回應時間過慢

**診斷步驟**:
1. 檢查慢查詢日誌
2. 使用 Profiler 找瓶頸
3. 檢查 N+1 查詢問題

**優化方法**:
- 新增資料庫索引
- 使用 Redis 快取
- 非同步處理耗時任務

## 日誌查看

\```bash
# 應用程式日誌
pm2 logs myapp

# 資料庫日誌
tail -f /var/log/postgresql/postgresql.log

# Nginx 日誌
tail -f /var/log/nginx/access.log
\```
```

**🔴 多模組整合故障排除（四合一/微服務系統）** ⭐ v0.01 新增：
```yaml
跨模組常見問題診斷:

1. 共用認證服務（Auth/JWT）問題:
   症狀: 某模組 API 回傳 401，但其他模組正常
   診斷:
     - 確認 JWT Secret 各模組一致（環境變數）
     - 確認 Token 有效期設定（Spring Boot vs Next.js 時鐘同步）
     - 確認 CORS 設定允許該模組域名
   解法: 統一從環境變數讀取 JWT_SECRET，不 hardcode

2. 資料庫 Migration 衝突:
   症狀: Spring Boot 啟動時 Flyway 報錯 "checksum mismatch"
   診斷:
     - git log db/migration/ 查看最近變更
     - flyway info 查看版本狀態
   解法: 不修改已執行的 migration，只新增新版本

3. 模組間服務依賴啟動順序:
   症狀: 電商模組啟動失敗（依賴認證服務未就緒）
   診斷:
     - docker compose logs auth-service
     - 確認 healthcheck 設定
   解法: docker-compose depends_on + healthcheck

4. 跨模組 API 呼叫失敗:
   症狀: 民宿模組呼叫電商 API 回傳 CORS 錯誤
   診斷:
     - 瀏覽器 Network Tab 查看 Preflight 請求
     - Spring Boot CorsConfig 設定
   解法: 統一 CORS 配置於 API Gateway 層

環境設定問題快速診斷清單:
□ JDK 版本是否符合（java -version）
□ Node.js 版本是否符合（node -v）
□ Docker Desktop 是否啟動
□ .env 檔案是否存在且完整
□ PostgreSQL port 5432 是否未被佔用（lsof -i :5432）
□ Spring Boot port 8080 是否未被佔用
□ Next.js port 3000 是否未被佔用
```

---

### 階段 5：文檔維護與版本管理 (20-30 分鐘)

> 🔴 **人機協作點：文檔維護機制確認**
>
> **AI 提供**：
> - 文檔更新流程
> - 版本管理策略
> - 文檔審查清單
> - 自動化工具建議
>
> **需人工確認**：
> - ✅ 更新流程明確可執行
> - ✅ 版本管理策略合理
> - ✅ 審查清單完整
> - ✅ 自動化工具適用
>
> **產出文件**：
> - 文檔維護 SOP
> - 版本管理指南
> - CHANGELOG 模板

**文檔更新流程**：
```markdown
# 文檔維護指南

## 更新時機

- 新增功能時更新 README 和 API 文檔
- 架構變更時更新架構文檔
- Bug 修復後更新 CHANGELOG
- 配置變更時更新配置文檔

## 版本管理

使用 Git 進行文檔版本控制，與代碼同步

## 文檔審查

所有文檔變更需要 Code Review

## 自動化

- API 文檔自動從 OpenAPI 生成
- CHANGELOG 自動從 Git commit 生成
```

**CHANGELOG 範例**：
```markdown
# Changelog

All notable changes to this project will be documented in this file.

## [1.2.0] - 2025-10-20

### Added
- User profile picture upload
- Email verification

### Changed
- Improved password validation

### Fixed
- Fix memory leak in WebSocket connection

### Deprecated
- `/api/v1/users/old-endpoint` will be removed in v2.0

## [1.1.0] - 2025-10-10

### Added
- OAuth 2.0 authentication
```

---

> **📖 Docs as Code（文檔即程式碼）最佳實踐**
>
> **核心原則**：將文檔視為程式碼，使用相同的工具和流程管理。
>
> **🔧 工具鏈推薦**
>
> | 用途 | 工具 | 優點 |
> |------|------|------|
> | **格式** | Markdown / AsciiDoc | 純文字、易於 diff |
> | **版本控制** | Git | 變更追蹤、協作 |
> | **靜態網站** | Docusaurus / MkDocs | 自動化部署 |
> | **API 文檔** | OpenAPI + Redoc | 程式碼生成 |
> | **圖表** | Mermaid / PlantUML | 文字描述即圖表 |
> | **CI/CD** | GitHub Actions | 自動化檢查和部署 |
>
> **📋 Docs as Code 工作流程**
>
> ```
> 1. 開發者在 /docs 目錄撰寫 Markdown
>      ↓
> 2. 提交 Pull Request
>      ↓
> 3. CI 自動執行：
>    - Markdown Lint 檢查格式
>    - Link Checker 檢查連結有效性
>    - Spell Checker 檢查拼字
>    - Build 測試是否可正常產生
>      ↓
> 4. 同儕審查（至少 1 人）
>      ↓
> 5. 合併到 main 分支
>      ↓
> 6. CI 自動部署到文檔網站
> ```
>
> **🛠️ CI Pipeline 範例 (GitHub Actions)**
>
> ```yaml
> # .github/workflows/docs.yml
> name: Documentation
> on:
>   push:
>     paths: ['docs/**', 'mkdocs.yml']
>   pull_request:
>     paths: ['docs/**']
>
> jobs:
>   lint:
>     runs-on: ubuntu-latest
>     steps:
>       - uses: actions/checkout@v4
>       - name: Markdown Lint
>         uses: DavidAnson/markdownlint-cli2-action@v14
>         with:
>           globs: 'docs/**/*.md'
>
>       - name: Check Links
>         uses: lycheeverse/lychee-action@v1
>         with:
>           args: --verbose docs/
>
>   deploy:
>     if: github.ref == 'refs/heads/main'
>     needs: lint
>     runs-on: ubuntu-latest
>     steps:
>       - uses: actions/checkout@v4
>       - uses: actions/setup-python@v5
>         with:
>           python-version: '3.x'
>       - run: pip install mkdocs-material
>       - run: mkdocs gh-deploy --force
> ```
>
> **✅ Docs as Code 檢查清單**
>
> - [ ] 文檔存放在 Git 版本控制中
> - [ ] 使用 Markdown 或 AsciiDoc 格式
> - [ ] 配置 Lint 工具（markdownlint）
> - [ ] 配置連結檢查（lychee/markdown-link-check）
> - [ ] PR 需經過審查才能合併
> - [ ] 自動化部署文檔網站

---

> **📝 Documentation Review Checklist（文檔審查檢查清單）**
>
> **審查者在核准文檔 PR 前，必須確認以下項目：**
>
> **1. 內容正確性**
> - [ ] 技術資訊準確無誤
> - [ ] 程式碼範例可正常執行
> - [ ] 指令和步驟經過測試
> - [ ] 版本號和日期正確
>
> **2. 完整性**
> - [ ] 涵蓋所有必要主題
> - [ ] 包含前置條件說明
> - [ ] 錯誤處理有說明
> - [ ] FAQ 涵蓋常見問題
>
> **3. 可讀性**
> - [ ] 使用清晰簡潔的語言
> - [ ] 標題層級正確
> - [ ] 段落長度適中（<5 句）
> - [ ] 專有名詞有解釋或連結
>
> **4. 格式一致性**
> - [ ] 符合專案文檔風格指南
> - [ ] 程式碼區塊有語法高亮
> - [ ] 圖片有 alt 文字
> - [ ] 連結格式正確
>
> **5. 可維護性**
> - [ ] 避免硬編碼版本號（使用變數）
> - [ ] 避免絕對路徑
> - [ ] 外部連結有效
> - [ ] 有最後更新日期
>
> **審查決策矩陣**
>
> | 問題嚴重度 | 範例 | 處理方式 |
> |-----------|------|---------|
> | **Blocker** | 程式碼範例有錯、指令會失敗 | 必須修正才能合併 |
> | **Major** | 缺少重要章節、邏輯不清 | 必須修正才能合併 |
> | **Minor** | 錯字、格式小問題 | 可合併，後續修正 |
> | **Suggestion** | 風格建議、最佳化 | 可選擇性採納 |

---

> **🔄 OpenAPI Generator vs Swagger Codegen 比較**
>
> 兩者都能從 OpenAPI 規格自動產生 API 文檔和 SDK，以下是詳細比較：
>
> | 特性 | OpenAPI Generator | Swagger Codegen |
> |------|------------------|-----------------|
> | **維護者** | 社群 (OpenAPI-Generator) | SmartBear (商業公司) |
> | **授權** | Apache 2.0 | Apache 2.0 |
> | **支援語言** | 60+ 語言 | 40+ 語言 |
> | **更新頻率** | 較快（社群驅動）| 較慢 |
> | **OpenAPI 3.1** | ✅ 支援 | ⚠️ 部分支援 |
> | **客製化模板** | ✅ Mustache | ✅ Mustache |
> | **CLI 易用性** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
> | **Docker 映像** | ✅ 官方提供 | ✅ 官方提供 |
>
> **選擇建議**
>
> | 情境 | 推薦工具 | 原因 |
> |------|---------|------|
> | **新專案** | OpenAPI Generator | 社群活躍、更新快 |
> | **需要 OpenAPI 3.1** | OpenAPI Generator | 支援較完整 |
> | **已使用 Swagger 生態系** | Swagger Codegen | 整合較佳 |
> | **需要商業支援** | Swagger Codegen | SmartBear 提供 |
>
> **使用範例**
>
> ```bash
> # OpenAPI Generator（推薦）
> # 安裝
> npm install @openapitools/openapi-generator-cli -g
>
> # 產生 TypeScript Client SDK
> openapi-generator-cli generate \
>   -i openapi.yaml \
>   -g typescript-axios \
>   -o ./generated/client
>
> # 產生 API 文檔 (HTML)
> openapi-generator-cli generate \
>   -i openapi.yaml \
>   -g html2 \
>   -o ./docs/api
>
> # Swagger Codegen
> # 安裝
> brew install swagger-codegen  # macOS
>
> # 產生 Java Client SDK
> swagger-codegen generate \
>   -i openapi.yaml \
>   -l java \
>   -o ./generated/java-client
> ```
>
> **CI/CD 整合範例**
>
> ```yaml
> # GitHub Actions - 自動產生 SDK
> jobs:
>   generate-sdk:
>     runs-on: ubuntu-latest
>     steps:
>       - uses: actions/checkout@v4
>       - name: Generate TypeScript SDK
>         uses: openapi-generators/openapitools-generator-action@v1
>         with:
>           generator: typescript-axios
>           openapi-file: openapi.yaml
>           output-dir: ./sdk
>       - name: Publish SDK
>         run: |
>           cd sdk && npm publish
>         env:
>           NODE_AUTH_TOKEN: ${{ secrets.NPM_TOKEN }}
> ```

---

### 階段 6：安全與合規文檔 (選用, 1-2 小時) ⭐ v0.01 新增

> **🔴 觸發條件**：當專案涉及以下任一情況時，**必須執行**此階段：
> - 處理敏感資料（個資、金融資料、商業機密）
> - 需要合規認證（GDPR、PCI-DSS、ISO 27001 等）
> - 高合規性行業（金融、醫療、政府、經銷存管理等）
> - 多平台部署（Web + Mobile，涉及行動端安全）
> - 涉及第三方整合（支付、掃碼、外部 API）
>
> **⚠️ Agent 按需載入**：此階段需載入 Security-Engineer 和/或 Compliance-Officer Agent

#### 步驟 6.1：安全架構文檔 (Technical-Writer + Security-Engineer + SD)

> 🔴 **人機協作點：安全文檔架構確認**
>
> **AI 提供**：
> - 安全架構設計文檔（認證、授權、加密策略）
> - 資料流圖（標示敏感資料流向與保護措施）
> - 威脅模型概要（STRIDE 分析）
> - 安全設計決策記錄
>
> **需人工確認**：
> - ✅ 安全架構符合系統需求
> - ✅ 資料流圖完整且準確
> - ✅ 威脅模型覆蓋主要攻擊面
> - ✅ 安全設計決策合理
>
> **產出文件**：
> - 安全架構文檔 (Security Architecture Document)
> - 資料流圖 (Data Flow Diagram)
> - 威脅模型 (Threat Model)

**安全文檔結構範例**：
```
docs/06_quality/
├── security/
│   ├── Security_Architecture.md        # 安全架構設計
│   ├── Threat_Model.md                 # 威脅模型 (STRIDE)
│   ├── Data_Flow_Diagram.md            # 資料流圖（標示加密/脫敏點）
│   ├── Authentication_Authorization.md # 認證授權設計
│   ├── Data_Protection.md              # 資料保護策略
│   ├── API_Security.md                 # API 安全規範（含 Webhook HMAC）
│   ├── Secret_Management.md            # Secret 管理策略（JWT/API Key 輪換/撤銷）
│   ├── Key_Rotation_Procedure.md       # 金鑰輪換程序（緊急撤銷 SOP）
│   ├── Mobile_Security.md              # 行動端安全規範 (如適用)
│   └── Incident_Response_Plan.md       # 事件應變計畫
├── compliance/
│   ├── Compliance_Mapping.md           # 合規對照表
│   ├── Data_Privacy_Policy.md          # 資料隱私政策
│   ├── Audit_Checklist.md              # 稽核檢查清單
│   └── Third_Party_Security.md         # 第三方安全評估
└── security_testing/
    ├── Security_Test_Plan.md           # 安全測試計畫
    ├── Penetration_Test_Report.md      # 滲透測試報告
    └── Vulnerability_Assessment.md     # 漏洞評估報告
```

#### 步驟 6.2：合規對照文檔 (Technical-Writer + Compliance-Officer)

> 🔴 **人機協作點：合規文檔審查確認**
>
> **AI 提供**：
> - 適用法規/標準清單
> - 合規差距分析
> - 合規對照表（要求 vs 實施措施）
>
> **需人工確認**：
> - ✅ 適用法規識別正確
> - ✅ 合規措施完整
> - ✅ 差距分析準確
>
> **產出文件**：
> - 合規對照表 (Compliance Mapping)
> - 資料隱私政策 (Data Privacy Policy)

**常見合規標準對照**：

| 標準 | 適用場景 | 核心要求 |
|------|---------|---------|
| **個資法/GDPR** | 處理個人資料 | 資料最小化、同意機制、刪除權 |
| **PCI-DSS** | 支付相關 | 加密傳輸、安全存儲、存取控制 |
| **ISO 27001** | 資訊安全管理 | 風險評估、安全控制、持續改善 |
| **SOC 2** | SaaS 服務 | 安全性、可用性、處理完整性 |

#### 步驟 6.3：多平台安全文檔 (Technical-Writer + SD-Mobile-Architect，如適用)

> **⚠️ 觸發條件**：專案涉及行動端（Android/iOS/macOS）時執行

**行動端安全文檔要點**：
- 憑證安全存儲（Android Keystore / iOS Keychain）
- Certificate Pinning 策略
- 本地資料加密
- 條碼掃描安全（防偽造、防注入）
- 生物辨識認證整合
- 應用程式簽章與完整性驗證

#### 步驟 6.4：安全文檔維護計畫

**安全文檔更新時機**：
- 安全漏洞修復後，更新威脅模型和安全架構文檔
- 法規變更時，更新合規對照表
- 新平台上線時，新增平台安全文檔
- 滲透測試後，更新漏洞評估報告
- 第三方整合變更時，更新第三方安全評估

---

## 🎯 成功標準

### 文檔完整性
- [ ] README 清晰易懂
- [ ] API 文檔完整（含 OpenAPI 規格、錯誤碼、Webhook）
- [ ] 架構文檔準確（C4 Model + ADR）
- [ ] 範例程式碼可執行
- [ ] 安全與合規文檔完整（如適用）⭐ v0.01 新增

### 資料庫文件完整性 ⭐ v0.01 新增
- [ ] ERD 文件存在（至少模組級別）
- [ ] Schema 說明文件涵蓋關鍵枚舉值與狀態機
- [ ] Migration 策略與 Rollback 方案已文件化
- [ ] 索引設計說明已記錄
- [ ] 測試資料 Seed 文件存在（各角色帳號）

### 行動端文件（如適用）⭐ v0.01 新增
- [ ] Android / macOS App 架構文件存在
- [ ] QR Code 掃描模組規格已定義
- [ ] Mobile-specific API 規格與後端一致
- [ ] 推播通知設定文件完整

### 可用性
- [ ] 新人可依文檔快速上手
- [ ] 常見問題有解答
- [ ] 文檔搜尋方便

### 維護性
- [ ] 文檔與代碼同步更新
- [ ] 版本控制清晰
- [ ] 更新流程明確

### 安全與合規（如適用）⭐ v0.01 新增
- [ ] 安全架構文檔涵蓋認證、授權、加密
- [ ] 威脅模型覆蓋 OWASP Top 10
- [ ] 合規對照表對應適用法規
- [ ] 多平台安全文檔完整（如適用）
- [ ] 安全文檔定期審查機制建立

---

## 📊 時間分配參考

| 階段 | 預估時間 |
|------|---------|
| 文檔現況盤點與規劃 | 40-60 分鐘 |
| 核心文檔撰寫 | 1.5-2 小時 |
| 開發者指南與範例（含資料庫/行動端文件） | 1-2 小時 |
| 故障排除與 FAQ | 30-40 分鐘 |
| 文檔維護與版本管理 | 20-30 分鐘 |
| 安全與合規文檔 (選用) ⭐ | 1-2 小時 |
| **總計** | **3-4 小時** (無安全) / **4-6 小時** (含安全) |

---

## 💡 最佳實踐

### 1. 以使用者為中心
- 了解目標讀者（開發者/使用者/維運）
- 提供清晰的範例
- 使用簡單易懂的語言

### 2. 保持更新
- 代碼變更時同步更新文檔
- 定期審查文檔準確性

### 3. 視覺化輔助
- 使用圖表說明架構
- 截圖展示 UI
- 流程圖說明流程

### 4. 可搜尋
- 清晰的標題結構
- 關鍵字豐富
- 提供索引

---

## 📚 實際案例走查

> 💡 **學習價值**: 透過真實專案案例,了解技術文檔建立的實際應用、常見挑戰與解決方案。

### 案例 1: API 文檔從零重建 - 提升前後端協作效率

**專案背景**:
- **專案類型**: Web API (電商後端服務)
- **團隊規模**: 8 人 (3 前端 + 3 後端 + 1 PM + 1 Technical Writer)
- **技術棧**: Node.js, Express, PostgreSQL, Swagger/OpenAPI 3.0
- **專案週期**: 4 週
- **專案目標**: 為完全無 API 文檔的系統重建完整文檔,提升前後端協作效率

**執行過程** (依 SOP 階段):

#### 階段 1: 文檔需求分析 (實際耗時: 3 天)
- ✅ **完成項目**:
  - 訪談前端團隊:識別 32 個 API 端點需要文檔
  - 識別目標讀者: 前端工程師 (主要)、第三方整合夥伴 (次要)
  - 確定文檔格式: OpenAPI 3.0 (可自動生成互動式文檔)
- ⚠️ **遇到問題**: 後端代碼缺少註解,難以理解 API 行為
- 💡 **解決方案**: 結合代碼分析 + Postman 實測 + 訪談後端工程師
- 📊 **階段產出**: 文檔需求清單、32 個 API 端點清單、目標讀者 Persona

#### 階段 2-3: 文檔撰寫與自動生成 (實際耗時: 2 週)
- ✅ **完成項目**:
  - 使用 `swagger-jsdoc` 從代碼註解自動生成 OpenAPI 規格
  - 手動補充缺少的欄位說明、範例、錯誤碼
  - 建立 Swagger UI 互動式文檔網站
  - 補充 5 個常見使用場景的程式碼範例
- ⚠️ **遇到問題**: 自動生成的文檔不完整,缺少業務邏輯說明
- 💡 **解決方案**:
  - 80% 由自動生成 (基本資訊)
  - 20% 手動補充 (業務邏輯、範例、注意事項)
- 📊 **階段產出**:
  - OpenAPI 3.0 規格文件 (32 個端點)
  - Swagger UI 互動式文檔網站
  - 5 個使用場景範例

#### 階段 4-5: 文檔審查與發布 (實際耗時: 1 週)
- ✅ **完成項目**:
  - 前端團隊審查: 發現 8 處描述不清楚的地方並修正
  - 建立文檔更新流程: PR 必須同步更新 API 文檔
  - 部署文檔網站至 GitHub Pages (自動部署)
  - 建立文檔版本控制: 使用 Git tag 標記版本
- ⚠️ **遇到問題**: 如何確保代碼變更時文檔同步更新?
- 💡 **解決方案**:
  - CI/CD 檢查: PR 必須包含文檔更新 (否則提示警告)
  - Code Review Checklist: 包含「API 文檔已更新」檢查項
  - 每月文檔審查會議,檢查文檔與代碼一致性
- 📊 **階段產出**:
  - 已發布的 API 文檔網站
  - 文檔更新 SOP
  - CI/CD 自動檢查腳本

**關鍵經驗**:
- 💡 **成功經驗 1**: OpenAPI 自動生成減少 80% 手動工作量
- 💡 **成功經驗 2**: Swagger UI 互動式文檔讓前端可以直接測試 API
- 💡 **成功經驗 3**: 文檔更新流程制度化,避免文檔過時
- ⚠️ **避坑指南 1**: 不要完全依賴自動生成,業務邏輯需要手動補充
- ⚠️ **避坑指南 2**: 文檔範例要實際可執行,避免複製貼上錯誤
- ⚠️ **避坑指南 3**: 文檔版本要與 API 版本對應,避免混淆
- 🔄 **流程調整**: 原訂「一次性完成所有文檔」調整為「先完成核心 API,再逐步補充」

**量化成果**:
- **API 文檔覆蓋率**: 從 0% 提升至 100% (32 個端點)
- **前後端協作效率**: 溝通時間減少 60% (從每天 2 小時 → 0.8 小時)
- **Bug 率**: API 使用錯誤減少 75% (因文檔清楚)
- **新人上手時間**: 前端新人從 2 週 → 5 天 (有完整 API 文檔)
- **第三方整合**: 新增 3 個第三方整合夥伴 (因有公開 API 文檔)
- **文檔維護成本**: 每週約 1 小時更新文檔 (可接受)

---

### 案例 2: 技術知識庫建立 - 新人上手時間從 4 週到 1.5 週

**專案背景**:
- **專案類型**: 內部技術知識庫 (Notion)
- **團隊規模**: 15 人 (10 工程師 + 3 QA + 2 PM)
- **技術棧**: Notion (知識庫平台)、Mermaid (流程圖)、Loom (錄影教學)
- **專案週期**: 8 週
- **專案目標**: 建立完整技術知識庫,降低新人上手門檻

**執行過程摘要**:

#### 階段 1-2: 知識盤點與架構設計 (2 週)
- ✅ **成功**:
  - 盤點現有文檔散落於 Slack/Email/Google Docs
  - 設計知識庫架構: 入門指南 / 開發流程 / 技術規範 / FAQ
- ⚠️ **挑戰**: 知識散落各處,整理耗時
- 💡 **解決**: 發動全團隊「文檔大掃除」,每人貢獻自己領域的文檔
- 📊 **產出**: 知識庫架構圖、文檔清單 (87 份待整理)

#### 階段 3-4: 文檔撰寫與整合 (4 週)
- ✅ **成功**:
  - 建立「新人 Onboarding Guide」(20 頁)
  - 整理「技術決策記錄」(ADR) 15 份
  - 製作「開發環境設定」影片教學 (Loom)
  - 建立「常見問題 FAQ」(32 個問題)
- ⚠️ **挑戰**: 文檔品質參差不齊
- 💡 **解決**: 建立「文檔品質檢查清單」,每份文檔須經 Peer Review
- 📊 **產出**:
  - Notion 知識庫 (87 份文檔)
  - 影片教學 8 支
  - 開發流程圖 12 個

#### 階段 5: 文檔發布與維護 (2 週)
- ✅ **成功**:
  - 全團隊 Notion 培訓 (2 小時工作坊)
  - 建立文檔更新機制: 每月第一個週五「文檔日」
  - 指定文檔 Owner: 每個領域有專人負責維護
- 📊 **產出**: 已發布的知識庫、文檔維護 SOP

**關鍵經驗**:
- 💡 **成功經驗**: 影片教學比文字更容易理解 (環境設定、操作流程)
- ⚠️ **避坑指南**: 文檔要有 Owner,否則容易過時無人維護
- 🔄 **流程調整**: 從「集中撰寫」調整為「分散貢獻 + 集中審查」

**量化成果**:
- **知識庫規模**: 87 份文檔 + 8 支影片 + 12 個流程圖
- **新人上手時間**: 從 4 週 → 1.5 週 (降低 **62.5%**)
- **重複問題**: FAQ 減少 Slack 問題 40%
- **文檔使用率**: 平均每人每週查閱 3.2 次
- **團隊滿意度**: 知識分享滿意度從 4/10 → 8/10
- **維護成本**: 每月「文檔日」約 2 小時 (可接受)

---

## 🎓 相關資源

### Workflows
- [documentation-flow.md](../../workflow/scenario-specific/documentation-flow.md) - 技術文檔撰寫流程
- [documentation-reconstruction-flow.md](../../workflow/scenario-specific/documentation-reconstruction-flow.md) - 文檔重建流程
- [consistency-check.md](../../workflow/core/consistency-check.md)
- [api-specification.md](../../workflow/core/api-specification.md)
- [interaction-analysis.md](../../workflow/core/interaction-analysis.md)

### 相關 Agents

**Primary Agent（主要負責）**:
- [technical-writer-zh.yaml](../../agent/specialized/technical-writer-zh.yaml) - Technical Writer（主導文檔撰寫）

**Supporting Agents（按需載入）**:
- [04.sa-analyst-zh.yaml](../../agent/core/04.sa-analyst-zh.yaml) - Amanda（需求文檔審查）
- [05.sd-architect-zh.yaml](../../agent/core/05.sd-architect-zh.yaml) - Marcus（架構文檔審查）
- [dev-senior-zh.yaml](../../agent/specialized/dev-senior-zh.yaml) - Dev Senior（程式碼範例、技術審查）

**Optional Agents（選用）**:
- [security-engineer-zh.yaml](../../agent/specialized/security-engineer-zh.yaml) - Security Engineer（安全文檔）
- [compliance-officer-zh.yaml](../../agent/specialized/compliance-officer-zh.yaml) - Compliance Officer（合規文檔）
- [sd-mobile-architect-zh.yaml](../../agent/specialized/sd-mobile-architect-zh.yaml) - Mobile Architect（行動端文檔）
- [07.qa-tester-zh.yaml](../../agent/core/07.qa-tester-zh.yaml) - Quincy（文檔驗收測試）
- [devops-engineer-zh.yaml](../../agent/specialized/devops-engineer-zh.yaml) - DevOps（Docs as Code CI/CD）

### 相關 Skills

- `/documentation-api` - API 文檔生成（OpenAPI/Swagger）
- `/sa-analyst` - 需求文檔分析與撰寫
- `/sd-architect` - 架構文檔（C4 Model、ADR）
- `/code-review` - 程式碼範例品質審查
- `/integration-database` - 資料庫文檔（PostgreSQL Schema）
- `/integration-oauth` - 認證授權文檔（OAuth 2.0）
- `/devops-github-actions` - Docs as Code CI/CD Pipeline
- `/devops-docker` - 部署文檔（Docker 環境）
- `/security-audit` - 安全架構文檔（OWASP Top 10）
- `/compliance-audit` - 合規對照文檔（GDPR/PCI-DSS）
- `/mobile-development` - 行動端文檔（Android/macOS）
- `/qa-testing` - 文檔驗收測試

### Prompts
- [documentation-prompts.md](../../prompts/scenario-prompts/documentation-prompts.md)

---

**下一步**：開始建立你的技術文檔體系！

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
