# 架構圖版本控制與維護指引
# Architecture Diagram Version Control and Maintenance Guide

**版本**: v0.01
**最後更新**: 2025-11-27
**文檔類型**: 操作指引 | Architecture Guide
**適用範圍**: 所有使用 C4 Model 或其他架構圖的專案
**相關文檔**: [C4_Model_Guidelines.md](C4_Model_Guidelines.md)

---

## 🎯 文檔目的

本指引提供架構圖的版本控制、命名規範、變更追蹤和維護最佳實踐,確保架構圖與系統演進保持同步。

---

## 📋 目錄

1. [架構圖類型與命名規範](#架構圖類型與命名規範)
2. [版本控制策略](#版本控制策略)
3. [變更追蹤機制](#變更追蹤機制)
4. [維護工作流程](#維護工作流程)
5. [工具與格式選擇](#工具與格式選擇)
6. [常見問題與解決方案](#常見問題與解決方案)

---

## 架構圖類型與命名規範

### 架構圖類型分類

根據 C4 Model,架構圖分為 4 個層級:

| 層級 | 名稱 | 用途 | 更新頻率 | 維護者 |
|------|------|------|---------|--------|
| **Level 1** | System Context Diagram | 系統與外部實體的關係 | 低 (每季度或重大變更) | SD-Architect |
| **Level 2** | Container Diagram | 系統內部容器 (應用、資料庫等) | 中 (每 Sprint 或重大變更) | SD-Architect |
| **Level 3** | Component Diagram | 容器內部組件 | 高 (每 Sprint) | SD-Architect + Dev |
| **Level 4** | Code Diagram | 類別/函數層級 (較少使用) | 極高 (每個 Feature) | Dev |

### 檔案命名規範

**格式**: `{Project}_{DiagramType}_v{Version}_{Date}.{Extension}`

**範例**:
- `ECommerce_Context_v1.0_20250115.puml`
- `ECommerce_Container_v2.1_20250227.drawio`
- `UserModule_Component_v1.3_20250310.mmd`

**命名規則說明**:
1. **Project**: 專案名稱 (PascalCase)
2. **DiagramType**: 圖表類型
   - `Context`: Level 1 系統上下文圖
   - `Container`: Level 2 容器圖
   - `Component`: Level 3 組件圖
   - `Code`: Level 4 代碼圖
   - `Deployment`: 部署架構圖
   - `Sequence`: 序列圖
3. **Version**: 語意版本號 (參考下方版本號規則)
4. **Date**: 創建/更新日期 (YYYYMMDD)
5. **Extension**: 檔案格式
   - `.puml`: PlantUML 格式 (推薦 - 純文本,易於版本控制)
   - `.drawio`: Draw.io 格式
   - `.mmd`: Mermaid 格式
   - `.png/.svg`: 輸出圖片格式

---

## 版本控制策略

### 語意版本號規則 (Semantic Versioning)

**格式**: `v{Major}.{Minor}.{Patch}`

| 版本類型 | 觸發條件 | 範例 | 說明 |
|---------|---------|------|------|
| **Major (主版本)** | - 架構重大變更<br>- 移除/新增主要容器<br>- 技術棧大幅改變 | v1.0 → v2.0 | 不向下相容的重大變更 |
| **Minor (次版本)** | - 新增容器/組件<br>- 修改容器間關係<br>- 新增重要整合 | v1.0 → v1.1 | 向下相容的功能新增 |
| **Patch (修訂版本)** | - 修正錯誤標示<br>- 更新註解<br>- 視覺優化 | v1.0 → v1.0.1 | Bug 修復或文檔更新 |

### Git 版本控制最佳實踐

#### 1. 目錄結構

```
project-root/
├── docs/
│   └── architecture/
│       ├── context/
│       │   ├── System_Context_v1.0_20250115.puml
│       │   └── System_Context_v1.1_20250227.puml
│       ├── container/
│       │   ├── Container_v2.0_20250227.puml
│       │   └── Container_v2.1_20250310.puml
│       ├── component/
│       │   └── UserModule_Component_v1.3_20250310.puml
│       ├── sequence/
│       │   └── Login_Sequence_v1.0_20250115.puml
│       ├── exported/                          # 匯出的圖片
│       │   ├── System_Context_v1.1.png
│       │   └── Container_v2.1.svg
│       └── CHANGELOG.md                        # 架構圖變更日誌
└── README.md
```

#### 2. Git Commit 訊息規範

**格式**: `[ARCH] {DiagramType}: {Action} - {Brief Description}`

**範例**:
```bash
git commit -m "[ARCH] Container: Add Redis cache layer - v2.1"
git commit -m "[ARCH] Component: Refactor UserModule components - v1.3"
git commit -m "[ARCH] Context: Update third-party integrations - v1.1"
```

#### 3. 分支策略

| 變更類型 | 分支名稱 | 合併目標 |
|---------|---------|---------|
| 重大架構變更 | `arch/major-redesign` | `main` (經過 Review) |
| 功能架構更新 | `arch/feature-xxx` | `develop` |
| 架構圖修正 | `arch/fix-diagram` | `develop` |

---

## 變更追蹤機制

### 架構圖 CHANGELOG.md

在 `docs/architecture/CHANGELOG.md` 維護變更記錄:

```markdown
# Architecture Diagram Changelog

## v2.1 - 2025-03-10

### Container Diagram
- **Added**: Redis Cache Layer for session management
- **Modified**: API Gateway now routes to Cache before Backend
- **Reason**: Performance optimization - reduce DB load by 40%
- **Impact**: Low - backward compatible change
- **Reviewer**: Marcus (SD-Architect)

### Component Diagram (UserModule)
- **Added**: PasswordHashingService component
- **Modified**: AuthService now depends on PasswordHashingService
- **Reason**: Security enhancement - separate hashing logic
- **Impact**: Medium - requires code refactoring
- **Related**: US-123, TECH-456

## v2.0 - 2025-02-27

### Container Diagram
- **Breaking Change**: Migrated from Monolith to Microservices
- **Added**: UserService, OrderService, PaymentService containers
- **Removed**: Legacy Monolith container
- **Reason**: Scalability and team autonomy
- **Impact**: High - requires full system redesign
- **Reviewer**: Marcus (SD-Architect), Senior Dev Team
```

### 變更追蹤欄位

每次架構圖變更應記錄:

| 欄位 | 說明 | 必填 |
|------|------|------|
| **Version** | 新版本號 | ✅ |
| **Date** | 變更日期 | ✅ |
| **Diagram Type** | 受影響的圖表類型 | ✅ |
| **Action** | Added/Modified/Removed | ✅ |
| **Description** | 變更內容描述 | ✅ |
| **Reason** | 變更原因 | ✅ |
| **Impact** | 影響範圍 (Low/Medium/High) | ✅ |
| **Reviewer** | 審查者 | ✅ |
| **Related** | 相關 User Story/Tech Debt ID | ❌ |

---

## 維護工作流程

### Workflow 1: 新增架構圖

```
1. 建立架構圖檔案
   ├─ 使用標準命名規範
   ├─ 初始版本設為 v1.0
   └─ 選擇合適的工具格式 (推薦 PlantUML)

2. 編寫架構圖內容
   ├─ 遵循 C4 Model 規範
   ├─ 添加清楚的標籤和註解
   └─ 使用一致的顏色和樣式

3. 匯出圖片 (PNG/SVG)
   └─ 存放至 exported/ 目錄

4. 更新 CHANGELOG.md
   └─ 記錄新增原因和影響範圍

5. Git Commit & Push
   └─ 使用規範的 commit 訊息

6. Code Review
   ├─ SD-Architect 審查
   └─ 團隊共識確認
```

### Workflow 2: 更新既有架構圖

```
1. 判斷版本號變更類型
   ├─ Major: 重大架構變更
   ├─ Minor: 新增容器/組件
   └─ Patch: 修正錯誤

2. 複製既有檔案為新版本
   └─ 範例: Container_v2.0.puml → Container_v2.1.puml

3. 修改架構圖內容
   ├─ 標記變更部分 (使用顏色或註解)
   └─ 更新版本號和日期

4. 匯出新版本圖片
   └─ 覆蓋 exported/ 目錄的舊圖片

5. 更新 CHANGELOG.md
   ├─ Added/Modified/Removed 清楚標示
   └─ 說明變更原因和影響

6. Git Commit & Push
   └─ 清楚說明變更內容

7. 通知團隊
   └─ 透過 Slack/Email 通知架構變更
```

### Workflow 3: 定期審查與清理

**頻率**: 每季度或每個 Major Release

```
1. 審查現有架構圖
   ├─ 檢查是否與實際系統一致
   ├─ 識別過時或不再使用的圖表
   └─ 確認所有圖表版本號正確

2. 清理舊版本
   ├─ 保留最近 3 個 Major 版本
   ├─ 歸檔超過 1 年的舊版本
   └─ 刪除重複或臨時檔案

3. 更新文檔
   ├─ 更新 README.md 架構圖索引
   └─ 確保 CHANGELOG.md 完整

4. 團隊培訓
   └─ 確保新成員了解架構圖維護流程
```

---

## 工具與格式選擇

### 推薦工具對照表

| 工具 | 優點 | 缺點 | 適用場景 | 版本控制友好度 |
|------|------|------|---------|--------------|
| **PlantUML** | - 純文本,易於 diff<br>- 自動化生成<br>- 支援 C4 擴充 | - 學習曲線<br>- 視覺調整困難 | 大型專案,自動化 CI/CD | ⭐⭐⭐⭐⭐ |
| **Mermaid** | - Markdown 內嵌<br>- GitHub 原生支援<br>- 語法簡單 | - 功能較少<br>- 樣式受限 | 中小型專案,GitHub | ⭐⭐⭐⭐ |
| **Draw.io** | - 視覺化拖拉<br>- 功能豐富<br>- 易上手 | - XML 格式,難 diff<br>- 手動維護 | 快速原型,簡報用 | ⭐⭐ |
| **Structurizr** | - C4 Model 專用<br>- DSL 語法<br>- 多視圖管理 | - 付費服務<br>- 學習成本高 | 企業級架構管理 | ⭐⭐⭐⭐ |
| **Lucidchart** | - 協作編輯<br>- 豐富模板 | - 付費<br>- 雲端依賴 | 團隊協作 | ⭐ |

### 格式轉換與匯出

**PlantUML 匯出範例**:
```bash
# 安裝 PlantUML (需要 Java)
brew install plantuml

# 匯出為 PNG
plantuml Container_v2.1.puml

# 匯出為 SVG (向量圖,推薦)
plantuml -tsvg Container_v2.1.puml

# 批量匯出
plantuml -tsvg docs/architecture/**/*.puml
```

**Mermaid 匯出範例**:
```bash
# 安裝 mermaid-cli
npm install -g @mermaid-js/mermaid-cli

# 匯出為 PNG
mmdc -i diagram.mmd -o diagram.png

# 匯出為 SVG
mmdc -i diagram.mmd -o diagram.svg
```

### 自動化匯出 (CI/CD 整合)

**GitHub Actions 範例**:
```yaml
name: Generate Architecture Diagrams

on:
  push:
    paths:
      - 'docs/architecture/**/*.puml'
      - 'docs/architecture/**/*.mmd'

jobs:
  generate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Generate PlantUML diagrams
        uses: cloudbees/plantuml-github-action@master
        with:
          args: '-v -tsvg docs/architecture/**/*.puml'

      - name: Commit generated diagrams
        run: |
          git config --local user.name "GitHub Actions"
          git add docs/architecture/exported/
          git commit -m "[AUTO] Update architecture diagrams" || echo "No changes"
          git push
```

---

## 常見問題與解決方案

### Q1: 架構圖與程式碼不一致怎麼辦?

**解決方案**:

1. **建立 Architecture Decision Record (ADR)**
   - 記錄為何架構圖與實作不同
   - 規劃何時同步

2. **定期架構審查會議**
   - 每 Sprint 結束檢查架構圖
   - SD-Architect 主導,Dev 團隊參與

3. **自動化檢測** (進階)
   - 使用工具如 ArchUnit (Java), NDepend (.NET)
   - 比對代碼與架構圖的差異

### Q2: 多人同時修改架構圖如何避免衝突?

**解決方案**:

1. **使用純文本格式** (PlantUML, Mermaid)
   - Git 可以 merge 純文本檔案

2. **分層管理**
   - Level 1/2: SD-Architect 獨自維護
   - Level 3/4: Dev 可提 Pull Request

3. **Lock 機制**
   - 在 Slack/Jira 宣告「正在更新 Container Diagram」
   - 避免同時編輯

### Q3: 如何處理實驗性架構設計?

**解決方案**:

1. **使用分支命名**
   - `arch/experiment-serverless`
   - `arch/spike-graphql`

2. **標記為 Draft 版本**
   - `Container_v3.0-draft_20250315.puml`

3. **不納入 main 分支**
   - 僅保留在實驗分支
   - 確定採用後才合併並更新版本號

### Q4: 大型專案架構圖過於複雜怎麼辦?

**解決方案**:

1. **分模組維護**
   ```
   architecture/
   ├── user-module/
   │   ├── Component_UserAuth_v1.0.puml
   │   └── Component_UserProfile_v1.0.puml
   ├── order-module/
   │   └── Component_Order_v1.0.puml
   └── payment-module/
       └── Component_Payment_v1.0.puml
   ```

2. **使用聚合視圖**
   - 高層次用 Context/Container
   - 細節用 Component Diagram 分開

3. **Dynamic Diagram**
   - 用序列圖展示特定流程
   - 避免將所有資訊塞在單一圖表

### Q5: 如何確保架構圖在 PR Review 中被檢查?

**解決方案**:

1. **Pull Request Template**
   ```markdown
   ## Checklist
   - [ ] 代碼變更
   - [ ] 單元測試
   - [ ] **架構圖更新** (如有架構變更)
   - [ ] CHANGELOG.md 更新
   ```

2. **CODEOWNERS 設定**
   ```
   # .github/CODEOWNERS
   docs/architecture/** @sd-architect @tech-lead
   ```

3. **CI 檢查**
   - 偵測 `src/` 有變更但 `docs/architecture/` 無變更
   - 提醒開發者更新架構圖

---

## 最佳實踐總結

### ✅ DO (應該做)

1. **使用語意版本號** - Major.Minor.Patch 清楚標示變更層級
2. **維護 CHANGELOG.md** - 記錄每次變更的原因和影響
3. **選擇純文本格式** - PlantUML/Mermaid 優於 Draw.io/Lucidchart
4. **定期審查** - 每季度或 Major Release 檢查一致性
5. **匯出圖片** - 方便非技術人員閱讀
6. **Code Review** - SD-Architect 必須審查架構圖變更
7. **團隊溝通** - 架構變更必須通知全團隊

### ❌ DON'T (不應該做)

1. **不要直接覆蓋舊版本** - 保留歷史版本以便追溯
2. **不要使用二進位格式** - .pptx/.vsdx 難以版本控制
3. **不要忽略變更記錄** - 沒有 CHANGELOG 等於沒有版本控制
4. **不要單一巨型圖表** - 分層分模組管理
5. **不要忘記匯出** - 只有 .puml 沒有 .png 不利於分享
6. **不要跳過審查** - 架構變更必須經過 SD-Architect
7. **不要與代碼脫節** - 定期同步架構圖與實作

---

## 相關資源

- **內部文檔**:
  - [C4_Model_Guidelines.md](C4_Model_Guidelines.md) - C4 Model 完整指南
  - [AISDLC_ID_Naming_Convention.md](AISDLC_ID_Naming_Convention.md) - ID 命名規範

- **外部資源**:
  - [C4 Model 官網](https://c4model.com/)
  - [PlantUML 官方文檔](https://plantuml.com/)
  - [Mermaid 官方文檔](https://mermaid-js.github.io/)
  - [Structurizr DSL](https://structurizr.com/dsl)

---

## 版本歷史

| 版本 | 日期 | 變更內容 | 作者 |
|------|------|---------|------|
| v0.01 | 2025-11-27 | 初始版本 - 架構圖版本控制指引 | AISDLC Team |

---

**文檔維護**: 本文檔應隨框架演進持續更新,確保架構圖維護流程清晰且可執行。
