# 專案術語表模板
# Project Glossary Template

**文檔類型**: 支援文件 (Support Document)
**模板版本**: v1.0
**適用階段**: 全專案生命週期
**建立日期**: 2025-11-19
**AISDLC 版本**: v0.01+

---

## 📋 文檔目的

本文檔提供 **專案術語定義**的標準化模板，確保團隊對專業術語有一致的理解，避免溝通歧義。

### 使用時機

- **階段 2**: 需求收集時建立初版
- **階段 4-5**: PRD/SRD 撰寫時持續更新
- **全專案**: 新成員 onboarding 參考

### 使用者

- **所有 Agent**: 維護術語一致性
- **新成員**: 快速理解專案語彙

---

## 📖 術語表

### A

| 術語 | 英文 | 定義 | 使用範例 | 同義詞/相關詞 |
|------|------|------|---------|--------------|
| **AC** | Acceptance Criteria | 驗收標準，定義 User Story 完成的具體條件 | AC-001-1: 用戶可以使用 Email 登入 | 驗收條件 |
| **API** | Application Programming Interface | 應用程式介面 | POST /api/v1/users | 介面、端點 |

### B

| 術語 | 英文 | 定義 | 使用範例 | 同義詞/相關詞 |
|------|------|------|---------|--------------|
| **Backend** | - | 伺服器端程式 | Node.js backend | 後端、Server-side |

### C

| 術語 | 英文 | 定義 | 使用範例 | 同義詞/相關詞 |
|------|------|------|---------|--------------|
| **CRUD** | Create, Read, Update, Delete | 基本資料操作 | 交易 CRUD 功能 | - |
| **CSP** | Content Security Policy | 內容安全政策 | 設定 CSP 防止 XSS | - |

### D-F

| 術語 | 英文 | 定義 | 使用範例 | 同義詞/相關詞 |
|------|------|------|---------|--------------|
| **DTO** | Data Transfer Object | 資料傳輸物件 | UserDTO | - |
| **FRD** | Functional Requirements Document | 功能需求文件 | 參考 FRD 第 3 章 | - |

### G-I

| 術語 | 英文 | 定義 | 使用範例 | 同義詞/相關詞 |
|------|------|------|---------|--------------|
| **ISR** | Incremental Static Regeneration | 增量靜態生成 | 使用 ISR 每 60 秒更新 | - |

### J-L

| 術語 | 英文 | 定義 | 使用範例 | 同義詞/相關詞 |
|------|------|------|---------|--------------|
| **JWT** | JSON Web Token | JSON 網頁令牌 | JWT 驗證 | Token |
| **LCP** | Largest Contentful Paint | 最大內容繪製 | LCP < 2.5s | Core Web Vitals |

### M-O

| 術語 | 英文 | 定義 | 使用範例 | 同義詞/相關詞 |
|------|------|------|---------|--------------|
| **MVP** | Minimum Viable Product | 最小可行產品 | MVP 包含核心功能 | - |
| **ORM** | Object-Relational Mapping | 物件關係對映 | Prisma ORM | - |

### P-R

| 術語 | 英文 | 定義 | 使用範例 | 同義詞/相關詞 |
|------|------|------|---------|--------------|
| **PRD** | Product Requirements Document | 產品需求文件 | 參考 PRD 第 5 章 | - |
| **PWA** | Progressive Web App | 漸進式網頁應用 | 支援 PWA 離線功能 | - |

### S

| 術語 | 英文 | 定義 | 使用範例 | 同義詞/相關詞 |
|------|------|------|---------|--------------|
| **SRD** | System Requirements Document | 系統需求文件 | 參考 SRD 架構設計 | - |
| **SSG** | Static Site Generation | 靜態網站生成 | 使用 SSG 預先渲染 | - |
| **SSR** | Server-Side Rendering | 伺服器端渲染 | Next.js SSR | - |

### T-Z

| 術語 | 英文 | 定義 | 使用範例 | 同義詞/相關詞 |
|------|------|------|---------|--------------|
| **TC** | Test Case | 測試案例 | TC-001: 登入成功測試 | - |
| **US** | User Story | 使用者故事 | US-001: 用戶登入 | - |
| **WCAG** | Web Content Accessibility Guidelines | 網頁內容無障礙指南 | 符合 WCAG 2.1 AA | - |

---

## 🏢 業務領域術語

> 根據專案領域添加業務專屬術語

### [領域名稱] 術語

| 術語 | 定義 | 使用範例 |
|------|------|---------|
| **[術語 1]** | [定義] | [範例] |
| **[術語 2]** | [定義] | [範例] |

---

## 🔤 縮寫對照表

| 縮寫 | 全稱 | 中文 |
|------|------|------|
| API | Application Programming Interface | 應用程式介面 |
| CI/CD | Continuous Integration/Continuous Deployment | 持續整合/持續部署 |
| CRUD | Create, Read, Update, Delete | 新增、讀取、更新、刪除 |
| JWT | JSON Web Token | JSON 網頁令牌 |
| MVP | Minimum Viable Product | 最小可行產品 |
| PRD | Product Requirements Document | 產品需求文件 |
| SRD | System Requirements Document | 系統需求文件 |
| UI/UX | User Interface/User Experience | 使用者介面/使用者體驗 |

---

## 📝 術語維護指南

### 新增術語

1. 確認術語在現有表中不存在
2. 提供清楚的定義
3. 加入使用範例
4. 列出同義詞/相關詞
5. 按字母順序排列

### 術語命名規範

- 使用業界標準術語
- 避免自創縮寫
- 中英對照清晰
- 定義簡潔明確

---

## 🔗 相關文件

- [AISDLC_ID_Naming_Convention.md](../../guides/system/naming/AISDLC_ID_Naming_Convention.md)
- [PRD_Universal_Template.md](../prd/PRD_Universal_Template.md)

---

## 🔄 版本歷史

| 版本 | 日期 | 變更說明 |
|-----|------|---------|
| v1.0 | 2025-11-19 | 初版建立 - Phase 1 P0 問題修正 |

---

**文檔維護者**: AISDLC Framework Team
**最後更新**: 2025-11-19
**狀態**: ✅ Active

---

**End of Document**
