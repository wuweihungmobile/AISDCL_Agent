# Documentation - 快速參考指南
# Quick Reference Guide

**版本**: v0.01
**閱讀時間**: 5 分鐘
**適用情境**: 技術文檔撰寫、API 文檔、使用者手冊

---

## 🎯 一頁總覽

### 適用場景
✅ 撰寫技術文檔
✅ API 文檔生成
✅ 使用者手冊編寫
✅ 知識庫建立

### 不適用場景
❌ 程式碼註解（Inline Comments）
❌ Commit Messages
❌ 專案管理文檔

---

## 📋 6 階段快速流程 (v0.01 更新)

```
總時間: 3.5-5 小時 (無安全) / 5-7 小時 (含安全)

┌─────────────────────────────────────────────┐
│ 階段 1: 文檔現況盤點與規劃 (40-60 分鐘) 🔴  │
│ └─ 文檔架構設計 → 文檔架構實施              │
├─────────────────────────────────────────────┤
│ 階段 2: 核心文檔撰寫 (1.5-2 小時) 🔴        │
│ └─ README → API 文檔 → 架構文檔             │
├─────────────────────────────────────────────┤
│ 階段 3: 開發者指南與範例 (1-2 小時) 🟡        │
│ └─ Getting Started → 程式碼範例             │
│    → 資料庫文件(ERD/Schema) → 行動端架構    │
├─────────────────────────────────────────────┤
│ 階段 4: 故障排除與 FAQ (30-40 分鐘) 🟡       │
│ └─ 常見問題 FAQ → 故障排除指南              │
├─────────────────────────────────────────────┤
│ 階段 5: 文檔維護與版本管理 (20-30 分鐘) ✅  │
│ └─ 更新流程 → CHANGELOG → Docs as Code      │
├─────────────────────────────────────────────┤
│ 階段 6: 安全與合規文檔 (選用, 1-2 小時) ⭐   │
│ └─ 安全架構 → 威脅模型 → 合規對照 → 行動端  │
│ ⚠️ 觸發: 敏感資料/合規要求/多平台部署        │
│ 📋 載入: Security-Engineer + Compliance-Officer│
└─────────────────────────────────────────────┘
```

---

## 🚀 快速啟動

```
提示詞:
「請載入 AISDLC-SDD v0.01，我需要撰寫技術文檔」

或具體描述:
「需要為 RESTful API 撰寫文檔」
「撰寫使用者手冊給非技術人員」
「建立內部知識庫文章」
「維護經銷存系統的安全合規文檔」⭐ v0.01 新增
```

---

## 📚 文檔類型快速參考

| 文檔類型 | 讀者 | 深度 | 範例數量 | 更新頻率 |
|---------|------|------|---------|---------|
| **API 文檔** | 開發者 | 🔴 高 | 多 | 每次發布 |
| **使用者手冊** | 終端使用者 | 🟡 中 | 多 | 每個版本 |
| **開發者指南** | 開發者 | 🔴 高 | 中 | 季度 |
| **架構文檔** | 架構師/開發 | 🔴 高 | 少 | 半年 |
| **Runbook** | 運維/SRE | 🟡 中 | 多 | 按需 |
| **Release Notes** | 所有人 | 🟢 低 | 無 | 每次發布 |
| **FAQ** | 所有人 | 🟢 低 | 無 | 按需 |

---

## ⚡ API 文檔快速模板

### RESTful API 文檔結構

```markdown
# API Name

## Overview
簡要描述 API 用途

## Base URL
```
https://api.example.com/v1
```

## Authentication
說明認證方式（API Key, OAuth 2.0, JWT）

## Endpoints

### GET /users
獲取使用者列表

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| page | integer | No | Page number (default: 1) |
| limit | integer | No | Items per page (default: 20) |

**Response:**
```json
{
  "data": [
    {
      "id": 1,
      "name": "John Doe",
      "email": "john@example.com"
    }
  ],
  "meta": {
    "page": 1,
    "total": 100
  }
}
```

**Status Codes:**
- 200: Success
- 400: Bad Request
- 401: Unauthorized
- 500: Internal Server Error

**Example:**
```bash
curl -X GET "https://api.example.com/v1/users?page=1&limit=10" \
  -H "Authorization: Bearer YOUR_TOKEN"
```
```

---

## 🛠️ 文檔工具快速選擇

### API 文檔工具

| 工具 | 特點 | 適用場景 | 推薦指數 |
|------|------|---------|---------|
| **Swagger/OpenAPI** | 標準化、可互動 | RESTful API | ⭐⭐⭐⭐⭐ |
| **Postman** | 測試+文檔 | API 開發 | ⭐⭐⭐⭐⭐ |
| **ReadMe** | 美觀、互動性強 | 公開 API | ⭐⭐⭐⭐ |
| **Stoplight** | 設計優先 | API 設計 | ⭐⭐⭐⭐ |
| **Redoc** | OpenAPI 渲染器 | 簡潔展示 | ⭐⭐⭐⭐ |

### 一般文檔工具

| 工具 | 特點 | 適用場景 | 推薦指數 |
|------|------|---------|---------|
| **MkDocs** | 簡單、Markdown | 技術文檔 | ⭐⭐⭐⭐⭐ |
| **Docusaurus** | React、可擴展 | 大型專案 | ⭐⭐⭐⭐⭐ |
| **GitBook** | 美觀、協作 | 產品文檔 | ⭐⭐⭐⭐ |
| **Notion** | 靈活、協作 | 內部知識庫 | ⭐⭐⭐⭐⭐ |
| **Confluence** | 企業級 | 大型團隊 | ⭐⭐⭐⭐ |

---

## 📝 撰寫最佳實踐

### 文檔撰寫黃金法則

**1. Know Your Audience**
```yaml
✅ 開發者文檔:
- 技術細節
- 程式碼範例
- 假設基礎知識

✅ 終端使用者文檔:
- 簡單語言
- 步驟式指引
- 大量截圖
```

**2. Show, Don't Just Tell**
```markdown
❌ 不好:
"Use the API to get user data."

✅ 好:
"To retrieve user information, make a GET request to /users/:id:
```bash
curl https://api.example.com/users/123
```
This returns the user object with all profile details."
```

**3. Keep It Up-to-Date**
```yaml
策略:
□ 文檔與程式碼同步更新
□ 自動化文檔生成（如 JSDoc, Swagger）
□ 定期審查（季度/半年）
□ 標註版本號和更新日期
```

**4. Make It Discoverable**
```yaml
SEO 友善:
□ 清晰的標題層級
□ 關鍵字優化
□ 內部連結

導航友善:
□ 目錄 (TOC)
□ 麵包屑
□ 搜尋功能
□ 相關文章推薦
```

---

## 🎨 文檔風格指南

### Markdown 最佳實踐

```markdown
# 一級標題 (每個文件只有一個)

## 二級標題 (主要區塊)

### 三級標題 (子區塊)

#### 四級標題 (細節，盡量避免更深層級)

**粗體** 用於強調
*斜體* 用於術語
`代碼` 用於內聯程式碼

連結: [文字](URL)
圖片: ![替代文字](URL)

列表:
- 項目 1
- 項目 2
  - 子項目

數字列表:
1. 步驟 1
2. 步驟 2

程式碼區塊:
```language
code here
```

表格:
| Header 1 | Header 2 |
|----------|----------|
| Cell 1   | Cell 2   |

引用:
> 這是引用文字

分隔線:
---
```

### 寫作風格

```yaml
✅ 推薦:
- 使用主動語態 ("Click the button" 而非 "The button should be clicked")
- 簡潔明瞭 (避免冗長句子)
- 使用現在式
- 一致的術語 (不要混用同義詞)
- 專業但友善的語氣

❌ 避免:
- 被動語態
- 過度技術術語 (或提供解釋)
- 模糊表達 ("可能", "通常")
- 過時資訊
```

---

## ✅ 文檔檢查清單

### Pre-Publish Checklist

```yaml
內容完整性:
□ 涵蓋所有關鍵功能
□ 範例程式碼可執行
□ 連結都有效
□ 圖片清晰可見

技術準確性:
□ 技術細節正確
□ 程式碼範例測試過
□ API 端點驗證
□ 版本號正確

架構文件完整性（含多模組系統）⭐ v0.01 新增:
□ C4 Level 1 (System Context) 存在
□ C4 Level 2 (Container Diagram) 存在
□ ADR 索引存在，主要技術決策均有記錄
□ CONTRIBUTING.md 存在且步驟完整

API 文件完整性（多模組系統）⭐ v0.01 新增:
□ 每個業務模組有獨立 OpenAPI 規格（非全部合併一個檔案）
□ 統一錯誤碼文件（error_codes.md）存在
□ Webhook 事件規格存在（若系統有 Webhook）
□ API 版本管理策略已說明

可讀性:
□ 結構清晰
□ 語法正確
□ 無錯別字
□ 格式一致

導航:
□ 目錄完整
□ 內部連結正確
□ 搜尋功能正常
□ 相關文章連結

SEO:
□ 標題描述性強
□ Meta 描述
□ 關鍵字適當
□ URL 友善

維護性:
□ 版本號標註
□ 更新日期
□ 作者/維護者
□ 變更記錄

資料庫文件（含 PostgreSQL 系統）⭐ v0.01 新增:
□ ERD 文件存在（至少模組級別，建議 Mermaid / dbdiagram.io）
□ Schema 說明涵蓋枚舉值與狀態機轉換規則
□ Migration 策略與 Rollback 方案已文件化
□ 索引設計說明已記錄
□ 測試資料 Seed 文件存在（各角色帳號）

行動端文件（Android / macOS 適用時）⭐ v0.01 新增:
□ App 架構文件存在（MVVM / SwiftUI 技術選型記錄）
□ QR Code 掃描模組規格已定義（格式/有效期/離線策略）
□ Mobile-specific API 規格（與 Web API 差異說明）
□ 推播通知設定文件（FCM / APNs）
```

---

## 📊 文檔指標

### 衡量文檔品質

```yaml
使用度指標:
- 頁面瀏覽量
- 平均停留時間
- 跳出率
- 搜尋關鍵字

互動指標:
- 反饋評分 (有用/無用)
- 評論/問題數量
- 文檔相關 Support Ticket 減少率

完整性指標:
- API 覆蓋率
- 範例程式碼數量
- 更新頻率
- 過時內容比例

目標:
□ 80%+ API 有文檔
□ 每個 API 至少 1 個範例
□ 季度更新一次
□ < 10% 過時內容
```

---

## 🔗 延伸閱讀

- 📘 [Documentation SOP 完整版](./SOP.md)
- 📖 [Documentation DeepDive 深度指南](./SOP_DeepDive.md)
- 🔧 [Documentation Workflow](../../workflow/scenario-specific/documentation-flow.md)
- 🔧 [Documentation Reconstruction Workflow](../../workflow/scenario-specific/documentation-reconstruction-flow.md)
- 🚀 [Documentation 快速啟動指令集](../../prompts/scenario-prompts/documentation-prompts.md)
- 📄 [AISDLC_INIT.md](../../AISDLC_INIT.md)

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
- `/devops-github-actions` - Docs as Code CI/CD
- `/security-audit` - 安全架構文檔（選用）
- `/compliance-audit` - 合規對照文檔（選用）
- `/mobile-development` - 行動端文檔（選用）

---

**提示**:
- 📖 文檔是產品的一部分
- 🔄 保持文檔與程式碼同步
- 👥 考慮讀者的技術背景
- ⭐ 範例勝過千言萬語

---

**文檔版本: v0.01
**最後更新**: 2026-03-28

---

## AutoClaude 自動化執行（Phase Z / v0.02 新增）

規格凍結（SPEC_FROZEN）→ `python -m autoclaude.tools.sdd_compile` 編譯 playbook → 人工 review YAML → `python -m autoclaude playbooks/sdd_bridge.yaml` 執行（🔴 人工閘門不可跳過）。
全文見：`workflow/sdd-autoclaude-bridge/SDD_AUTOCLAUDE_BRIDGE.md`。
