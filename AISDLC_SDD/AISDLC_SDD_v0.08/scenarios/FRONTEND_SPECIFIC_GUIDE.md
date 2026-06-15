# 前端開發特化指引（SDD 版）
# Frontend Development Specific Guide — SDD Edition

**框架版本**: AISDLC-SDD v0.01
**基於**: AISDLC-SDD v0.01 FRONTEND_SPECIFIC_GUIDE
**最後更新**: 2026-04-15
**文檔目的**: 提供 AISDLC-SDD 框架在前端開發專案中的特化考量，特別是 SDD 前端規格要求

---

## 適用情境

本指南適用於以下 SDD 情境的前端開發面向：

| 情境 | 前端 SDD 重點 |
|------|-------------|
| **Greenfield** | 前端架構 ADR + UI Contract 規格 |
| **Brownfield** | 前端 As-Is 規格逆向 + Tech Debt 規格化 |
| **Refactoring** | UI Invariants + 組件 Contract |
| **Integration** | Frontend-Backend API Contract（Consumer Side）|
| **Performance** | Core Web Vitals SLO + PBS 規格 |
| **Testing** | 前端測試 RTM + E2E Contract |

---

## SDD 前端規格要求（新增）

### 前端必須的 SDD 文件

| 文件 | SDD 模板 | 適用情境 |
|------|---------|---------|
| UI Architecture ADR | `docs_template/sdd/adr/ADR-TEMPLATE.md` | Greenfield |
| Frontend Consumer Contract | `docs_template/sdd/api/CONSUMER-CONTRACT-TEMPLATE.yaml` | 所有情境 |
| Frontend As-Is SRD | `docs_template/sdd/architecture/AS-IS-SRD-TEMPLATE.md` | Brownfield |
| UI Invariants | `docs_template/sdd/requirements/INVARIANT-SPEC-TEMPLATE.md` | Refactoring |
| Frontend PBS | `docs_template/sdd/testing/PERFORMANCE-BASELINE-SPEC-TEMPLATE.md` | Performance |
| Frontend RTM | `docs_template/sdd/testing/RTM-TEMPLATE.md` | Testing |

### SCG 閘門的前端特化檢查

| SCG | 前端特化檢查項 |
|-----|-------------|
| SCG-1 | 前端架構 ADR 完整（框架選型、狀態管理、路由策略）|
| SCG-2 | C4 Model 包含 Frontend Component 層 |
| SCG-3 | OpenAPI Contract（前端視角 Consumer Contract 通過）|
| SCG-4 | 實作與 UI Contract 一致（API 呼叫、錯誤處理）|
| SCG-5 | 前端 RTM 覆蓋（F-XXX → 前端 TC-XXX）|

---

## 1. Greenfield — 前端新專案開發特化

### 1.1 前端需求分析重點（SDD 規格化）

在 **PRD/FRD** 階段，額外以 F-XXX 格式記錄前端功能需求：

**跨平台響應式需求（納入 FRD）**：
- F-FE-001: 支援裝置類型（Desktop/Tablet/Mobile）
- F-FE-002: 瀏覽器支援範圍（Chrome/Firefox/Safari/Edge）
- F-FE-003: 響應式斷點（Mobile < 768px / Tablet 768-1024px / Desktop > 1024px）

**UI/UX 設計需求（納入 FRD）**：
- F-FE-010: 設計系統選型（Material UI/Ant Design/自訂）
- F-FE-011: 無障礙設計（WCAG 2.1 Level AA）
- F-FE-012: 設計稿格式（Figma/Sketch 規格連結）

**效能需求（納入 PBS/SLO）**：
- NFR-FE-001: FCP < 1.8s
- NFR-FE-002: LCP < 2.5s
- NFR-FE-003: FID < 100ms
- NFR-FE-004: CLS < 0.1

### 1.2 前端架構 ADR 必要決策

以下技術決策**必須建立 ADR**（使用 `adr-generate`）：

```
ADR-FE-001: 前端框架選型（React/Vue/Angular）
ADR-FE-002: 狀態管理策略（Redux/Zustand/Pinia）
ADR-FE-003: 路由策略（SPA/MPA/SSR/SSG）
ADR-FE-004: CSS 解決方案（CSS Modules/Tailwind/CSS-in-JS）
ADR-FE-005: 打包工具選型（Vite/Webpack/Turbopack）
```

### 1.3 前端 Consumer Contract（SCG-3 前必須完成）

前端作為 API Consumer，需要在 SCG-3 前建立 Consumer Contract：

```yaml
# 使用 contract-generate 生成
Consumer: Frontend App
Provider: Backend API
Interactions:
  - 每個 API 端點的請求格式
  - 預期的回應格式（含錯誤格式）
  - 認證方式
```

---

## 2. Brownfield — 前端既有系統特化

### 2.1 前端逆向規格（As-Is）

執行前端 As-Is 規格逆向時，需額外記錄：

```yaml
前端 As-Is 清單:
  - 現有技術棧版本（框架/依賴版本）
  - 現有組件庫清單
  - 現有狀態管理機制
  - 現有 API 呼叫模式（是否符合 REST/GraphQL 規範）
  - 已知的前端技術債（TD-FE-XXX 格式）
```

### 2.2 前端 Tech Debt 規格化

常見前端技術債（納入 Tech Debt Spec）：

| Tech Debt ID | 類型 | 說明 |
|-------------|------|------|
| TD-FE-001 | 依賴過期 | 框架/套件版本嚴重落後 |
| TD-FE-002 | 缺乏 TypeScript | 無型別安全保護 |
| TD-FE-003 | 組件過度耦合 | 難以獨立測試 |
| TD-FE-004 | 無狀態管理規範 | 全局狀態散亂 |
| TD-FE-005 | 效能問題 | Bundle 過大、無程式碼分割 |

---

## 3. Refactoring — 前端重構特化

### 3.1 前端 UI Invariants（重構前必須提取）

使用 `INVARIANT-SPEC-TEMPLATE.md` 記錄：

```
INV-FE-001: [結帳流程] 購物車狀態在頁面刷新後必須保持
INV-FE-002: [認證狀態] 登出後必須清除所有 Token 和本地快取
INV-FE-003: [表單提交] 雙重提交防護（避免重複訂單）
INV-FE-004: [錯誤邊界] 子組件錯誤不能使整個應用當機
```

### 3.2 組件重構策略

依 SDD 原則，組件重構必須先定義 Before/After Contract：

```
Before Contract: 現有組件的輸入/輸出 Props 規格
After Contract: 重構後的組件 Props 規格
變更原因: ADR（記錄為何需要重構）
測試策略: 組件 Contract Tests（確保 Invariants 不破壞）
```

---

## 4. Integration — 前端與後端整合特化

### 4.1 Frontend Consumer Contract 建立流程

```
1. integration-specialist 提供 Provider API Spec（OpenAPI）
2. 前端開發者建立 Consumer Contract（請求/回應的最小規格）
3. 使用 contract-generate 生成 Contract 文件
4. SCG-3 閘門：Consumer Contract 凍結 🔴
5. 實作 API Client（符合 Contract）
6. 執行 Consumer Contract Tests
7. SCG-4 PR Review：確認實作符合 Contract 🔴
```

### 4.2 前端 API 整合常見 SDD 缺失

| 缺失 | SDD 要求 |
|------|---------|
| 未定義錯誤處理規格 | Contract 中明確定義各 HTTP 錯誤碼的前端行為 |
| 未定義 Loading State | FRD 中明確定義 Loading/Empty/Error UI 狀態 |
| 未定義離線行為 | NFR 中明確定義離線 Fallback 策略 |
| 未定義認證流程 | ADR 記錄 Token 管理策略（存放位置、刷新機制）|

---

## 5. Performance — 前端效能特化

### 5.1 前端 PBS（Performance Baseline Spec）

在 PBS Gate 前，必須定義以下 SLO（使用 `PERFORMANCE-BASELINE-SPEC-TEMPLATE.md`）：

```yaml
Core Web Vitals SLO:
  FCP: < 1.8s（75th percentile）
  LCP: < 2.5s（75th percentile）
  FID: < 100ms（75th percentile）
  CLS: < 0.1（75th percentile）

Bundle Size SLO:
  Initial Bundle: < 250KB（gzipped）
  Lazy Chunks: < 100KB（per chunk）

Lighthouse Score SLO:
  Performance: >= 90
  Accessibility: >= 95
  SEO: >= 85
```

### 5.2 前端效能優化策略（依 SDD 優先級）

| 優先級 | 優化策略 | SDD 記錄 |
|-------|---------|---------|
| P1 | Code Splitting（路由/組件懶加載）| ADR 記錄策略 |
| P1 | 圖片優化（WebP/AVIF/Lazy Loading）| NFR 定義格式要求 |
| P2 | CSS 優化（Critical CSS/PurgeCSS）| ADR 記錄選型 |
| P2 | Service Worker 快取策略 | ADR 記錄快取策略 |
| P3 | Tree Shaking 優化 | 無需 ADR（構建工具默認）|

---

## 6. Testing — 前端測試特化

### 6.1 前端測試 RTM 結構

```
F-FE-001（響應式需求）→ US-XXX → TC-FE-001（視覺回歸測試）
F-FE-010（UI 組件需求）→ US-XXX → TC-FE-002（組件單元測試）
API Contract → Consumer Contract → TC-FE-003（Contract Tests）
INV-FE-001（UI Invariants）→ TC-FE-004（E2E 不變量測試）
```

### 6.2 前端測試策略（SDD 對齊）

| 測試類型 | SDD 必要文件 | 工具建議 |
|---------|-----------|---------|
| 組件單元測試 | 組件 Contract 規格 | Jest + Testing Library |
| Consumer Contract Tests | Consumer Contract YAML | Pact |
| E2E 測試 | RTM 中的 E2E TC-XXX | Playwright/Cypress |
| 視覺回歸測試 | UI Invariants 截圖基準 | Chromatic/Percy |
| 效能測試 | PBS 中的 Lighthouse SLO | Lighthouse CI |

---

## 前端 SCG 閘門快速清單

```
SCG-0 ✓: FRD 包含前端功能需求（F-FE-XXX）和 NFR（NFR-FE-XXX）
SCG-1 ✓: 前端架構 ADR（ADR-FE-001~005）完成
SCG-2 ✓: C4 Component 層包含前端組件結構
SCG-3 ✓: Consumer Contract 凍結（前端視角）
SCG-4 ✓: 實作符合 Consumer Contract + UI Invariants 通過
SCG-5 ✓: 前端 RTM 100% 覆蓋（含 E2E TC）
SCG-6 ✓: Lighthouse Score 達 PBS SLO
```

---

## 相關文檔

- `docs_template/sdd/api/CONSUMER-CONTRACT-TEMPLATE.yaml` — Consumer Contract 模板
- `docs_template/sdd/testing/PERFORMANCE-BASELINE-SPEC-TEMPLATE.md` — PBS 模板
- `docs_template/sdd/adr/ADR-TEMPLATE.md` — 前端 ADR 模板
- `docs_template/sdd/requirements/INVARIANT-SPEC-TEMPLATE.md` — UI Invariants 模板
- `docs_template/sdd/testing/RTM-TEMPLATE.md` — 前端 RTM 模板

---

**維護者**: AISDLC-SDD Framework Team
**SDD 版本**: v0.01
**最後更新**: 2026-04-15
