# Documentation Pipeline 配置範本

> **📝 P2 文檔 Pipeline**
>
> 此範本定義如何在 CI/CD Pipeline 中整合 **Documentation Pipeline**，
> 確保文檔品質、連結完整性，並自動化部署文檔站點。
>
> - **PR 階段**: Doc Lint + Link Check（< 3 分鐘）— 快速品質檢查
> - **Main 合併後**: Build + Deploy-Docs — 自動部署文檔站點
> - **目標**: 文檔品質從「人工審查」提升到「自動化守門」

---

**版本**: v1.0
**建立日期**: 2026-03-22
**文檔類型**: DevOps 配置範本 | Documentation Pipeline
**相關文檔**:
- [CICD_Pipeline_Template.md](./CICD_Pipeline_Template.md) - CI/CD Pipeline 完整範本
- [Layer0_Security_Baseline_Template.md](./Layer0_Security_Baseline_Template.md) - Layer 0 安全基線
- [Layer1_Build_Verify_Template.md](./Layer1_Build_Verify_Template.md) - Layer 1 建置驗證
- [Security_Scan_Integration_Template.md](./Security_Scan_Integration_Template.md) - P1 安全掃描整合
- [Migration_Pipeline_Template.md](./Migration_Pipeline_Template.md) - P1 Migration Pipeline
- [Performance_Benchmark_Gate_Template.md](./Performance_Benchmark_Gate_Template.md) - P2 效能基準門檻
- [Event_Driven_Agent_Notification_Template.md](./Event_Driven_Agent_Notification_Template.md) - P3 事件驅動 Agent 通知
- [Documentation SOP](../../../scenarios/documentation/SOP.md) - Documentation 情境完整 SOP

---

## 📋 目錄

1. [Pipeline 架構](#pipeline-架構)
2. [Doc Lint（文檔格式檢查）](#doc-lint文檔格式檢查)
3. [Link Check（連結完整性檢查）](#link-check連結完整性檢查)
4. [Doc Build（文檔建置）](#doc-build文檔建置)
5. [Deploy-Docs（文檔部署）](#deploy-docs文檔部署)
6. [觸發條件與策略](#觸發條件與策略)
7. [工具選型](#工具選型)
8. [情境適用性](#情境適用性)
9. [Pipeline 整合位置](#pipeline-整合位置)
10. [維護與更新](#維護與更新)

---

## Pipeline 架構

### 執行流程

```
PR 階段（每次 PR 觸發）              Main 合併後
┌─────────────────────┐            ┌─────────────────────────┐
│ Doc Lint             │            │ Doc Build               │
│ ├── Markdown Lint    │            │ ├── 靜態站點生成         │
│ ├── 拼字檢查         │            │ ├── 搜尋索引建立         │
│ └── 格式一致性       │            │ └── 版本標記             │
│                     │            │                         │
│ Link Check          │            │ Deploy-Docs             │
│ ├── 內部連結驗證     │            │ ├── GitHub Pages         │
│ ├── 外部連結驗證     │            │ ├── 或 S3/CloudFront    │
│ └── 錨點驗證        │            │ └── 或 自建伺服器        │
│                     │            │                         │
│ ⏱️ < 3 分鐘         │            │ ⏱️ 5-10 分鐘            │
│ 🔴 失敗阻塞 PR      │            │ 🔴 失敗通知維護者        │
└─────────────────────┘            └─────────────────────────┘
```

### 為什麼需要 Documentation Pipeline？

| 問題 | 影響 | Pipeline 解決方案 |
|------|------|-----------------|
| 斷裂連結 | 使用者找不到文檔 | Link Check 自動偵測 |
| 格式不一致 | 閱讀體驗差 | Doc Lint 強制格式 |
| 拼字錯誤 | 降低專業度 | Spell Check 自動修正 |
| 手動部署 | 文檔版本落後 | 自動 Deploy-Docs |

---

## Doc Lint（文檔格式檢查）

### 檢查項目

| 檢查類型 | 工具 | 阻塞策略 | 說明 |
|---------|------|---------|------|
| **Markdown Lint** | markdownlint-cli2 | 🔴 阻塞 | 標題層級、列表格式、空行規則 |
| **拼字檢查** | cspell / typos | ⚠️ 警告 | 英文拼字、技術術語白名單 |
| **格式一致性** | prettier (markdown) | 🔴 阻塞 | 統一縮排、換行、引號風格 |
| **中文排版** | pangu.js (選配) | ⚠️ 警告 | 中英文間距、標點符號 |

### markdownlint 配置

```yaml
# .markdownlint.yml（專案根目錄）
default: true
MD013:                        # 行長度
  line_length: 200            # 文檔允許較長行
  tables: false               # 表格不限長度
MD033:                        # 允許 HTML
  allowed_elements:
    - details
    - summary
    - br
    - sup
MD041: false                  # 允許非 H1 開頭（README 例外）
MD024:
  siblings_only: true         # 僅檢查同層級標題重複
```

### cspell 配置

```json
// .cspell.json（專案根目錄）
{
  "version": "0.2",
  "language": "en",
  "words": [
    "AISDLC", "greenfield", "brownfield", "canary",
    "rollback", "devops", "middleware", "webhook"
  ],
  "ignorePaths": [
    "node_modules", ".git", "*.lock", "*.min.js"
  ],
  "enableFiletypes": ["markdown"]
}
```

---

## Link Check（連結完整性檢查）

### 檢查範圍

| 類型 | 檢查內容 | 阻塞策略 |
|------|---------|---------|
| **內部連結** | 相對路徑 `.md` 連結是否存在 | 🔴 阻塞 |
| **錨點連結** | `#section-name` 是否對應標題 | 🔴 阻塞 |
| **外部連結** | HTTP/HTTPS URL 是否可達 | ⚠️ 警告（避免外部服務暫時不可用阻塞） |
| **圖片連結** | 圖片檔案是否存在 | 🔴 阻塞 |

### 配置

```yaml
# .lychee.toml（lychee 配置）或等效工具配置
exclude_paths = ["node_modules", ".git"]
max_concurrency = 10
timeout = 30                    # 外部連結 30 秒超時
accept = [200, 204, 301, 302]  # 接受的 HTTP 狀態碼
exclude_loopback = true         # 排除 localhost

# 排除已知不穩定的外部連結
exclude = [
  "https://example\\.com",
  "https://localhost"
]
```

---

## Doc Build（文檔建置）

### 支援的文檔建置工具

| 工具 | 適用場景 | 輸出 |
|------|---------|------|
| **MkDocs** (Material) | 技術文檔站點（推薦） | 靜態 HTML |
| **Docusaurus** | React 生態系文檔 | 靜態 HTML |
| **VitePress** | Vue 生態系文檔 | 靜態 HTML |
| **mdBook** | Rust 生態系 / 輕量 | 靜態 HTML |
| **Jekyll** | GitHub Pages 原生 | 靜態 HTML |

### MkDocs 配置範例

```yaml
# mkdocs.yml
site_name: "專案文檔"
theme:
  name: material
  language: zh-TW
  features:
    - navigation.instant
    - navigation.tabs
    - search.highlight
plugins:
  - search:
      lang: zh
  - minify:
      minify_html: true
```

---

## Deploy-Docs（文檔部署）

### 部署策略

| 平台 | 適用場景 | 成本 |
|------|---------|------|
| **GitHub Pages** | 開源專案（推薦首選） | 免費 |
| **GitLab Pages** | GitLab 託管專案 | 免費 |
| **Netlify** | 自訂域名 + 預覽部署 | 免費/付費 |
| **Vercel** | 前端文檔 | 免費/付費 |
| **S3 + CloudFront** | 企業內部 | 付費 |

### 部署觸發條件

```yaml
deploy_triggers:
  auto_deploy:
    - push_to_main              # main 分支推送自動部署
    - tag_release               # 版本標記時部署
  manual_deploy:
    - workflow_dispatch          # 手動觸發
  preview_deploy:
    - pull_request               # PR 預覽部署（Netlify/Vercel）
```

---

## 觸發條件與策略

### 觸發條件配置

```yaml
documentation_pipeline:
  # PR 階段（Doc Lint + Link Check）
  pr_checks:
    trigger:
      - pull_request:
          paths:
            - '**/*.md'
            - 'docs/**'
            - 'mkdocs.yml'
            - '.markdownlint.yml'
    timeout: 180s                # 3 分鐘硬上限
    blocking: true               # 失敗阻塞 PR

  # Main 合併後（Build + Deploy）
  deploy:
    trigger:
      - push:
          branches: [main]
          paths:
            - '**/*.md'
            - 'docs/**'
            - 'mkdocs.yml'
    timeout: 600s                # 10 分鐘
    blocking: false              # 失敗通知但不阻塞

  # Nightly（完整外部連結檢查）
  nightly_link_check:
    trigger:
      - schedule: "0 3 * * *"   # 每日 03:00 UTC
    include_external: true       # 包含外部連結
    timeout: 1800s               # 30 分鐘（外部連結較慢）
```

### 阻塞策略

| 階段 | 檢查項 | 阻塞策略 |
|------|--------|---------|
| PR | Markdown Lint | 🔴 阻塞 |
| PR | 內部 Link Check | 🔴 阻塞 |
| PR | 外部 Link Check | ⚠️ 警告 |
| PR | 拼字檢查 | ⚠️ 警告 |
| Main | Doc Build | 🔴 失敗通知 |
| Main | Deploy | 🔴 失敗通知 |
| Nightly | 完整 Link Check | ⚠️ 報告審查 |

---

## 工具選型

### 推薦工具組合

| 類型 | 推薦工具（免費） | 商業替代 | 適用場景 |
|------|----------------|---------|---------|
| **Markdown Lint** | markdownlint-cli2 | - | 格式檢查 |
| **Link Check** | **lychee** (推薦) / markdown-link-check | - | 連結驗證 |
| **拼字檢查** | cspell / typos | Grammarly | 拼字與語法 |
| **Doc Build** | MkDocs Material (推薦) | Confluence | 文檔站點 |
| **Deploy** | GitHub Pages (推薦) | Netlify, Vercel | 靜態部署 |

---

## 情境適用性

### Documentation Pipeline 適用矩陣

| 情境 | Doc Lint | Link Check | Doc Build + Deploy | 說明 |
|------|:---:|:---:|:---:|------|
| `documentation` | 🔴 強制 | 🔴 強制 | 🔴 強制 | 核心情境，完整文檔 Pipeline |
| `greenfield` | ⚠️ 選配 | ⚠️ 選配 | ❌ | 新專案 README/API 文檔品質 |
| `brownfield` | ⚠️ 選配 | ⚠️ 選配 | ❌ | 既有文檔更新品質 |
| `refactoring` | ❌ | ❌ | ❌ | 重構不產出新文檔 |
| `migration` | ⚠️ 選配 | ⚠️ 選配 | ❌ | 遷移文檔品質 |
| `integration` | ⚠️ 選配 | ⚠️ 選配 | ❌ | API 文檔品質 |
| `performance` | ❌ | ❌ | ❌ | 效能不需文檔 Pipeline |
| `devops` | ❌ | ❌ | ❌ | IaC 文檔由其他工具管理 |
| `testing` | ❌ | ❌ | ❌ | 測試報告由測試工具生成 |
| `security` | ❌ | ❌ | ❌ | 安全文檔由安全工具生成 |

---

## Pipeline 整合位置

### 執行順序

```
Layer 0: Security Baseline ✅
Layer 1: Build & Verify ✅（documentation 情境可跳過 Build/Test）
    ↓
┌─────────────────────────────────────────────┐
│  Layer 2: Documentation Pipeline (本範本)    │
│  ├── Doc Lint (PR 階段, < 1min)            │
│  ├── Link Check (PR 階段, < 2min)          │
│  ├── Doc Build (Main 合併後, < 5min)       │
│  └── Deploy-Docs (Main 合併後, < 5min)     │
└─────────────────────────────────────────────┘
    ↓
Layer 3: Deploy & Validate（文檔站點驗證）
```

### 超時設定

| 階段 | PR 階段 | Main/Nightly | 超時後處理 |
|------|---------|---------|-----------|
| **Doc Lint** | 1 分鐘 | 1 分鐘 | ⚠️ 降級為警告 |
| **Link Check (內部)** | 2 分鐘 | 2 分鐘 | ⚠️ 降級為警告 |
| **Link Check (外部)** | N/A | 30 分鐘 | ⚠️ 降級為警告 |
| **Doc Build** | N/A | 5 分鐘 | 🔴 失敗通知 |
| **Deploy-Docs** | N/A | 5 分鐘 | 🔴 失敗通知 |

---

## 維護與更新

### 定期更新週期

| 項目 | 更新頻率 | 負責角色 |
|------|---------|---------|
| markdownlint 規則 | 每季審查 | Technical-Writer + DevOps |
| 拼字白名單 | 功能變更時 | Dev + Technical-Writer |
| 文檔建置工具版本 | 每月 | DevOps-Engineer |
| 外部連結排除清單 | 每季 | Technical-Writer |

### 變更記錄

| 日期 | 版本 | 變更內容 |
|------|------|---------|
| 2026-03-22 | v1.0 | 初始版本，建立 Doc Lint + Link Check + Build + Deploy 完整 Pipeline |
