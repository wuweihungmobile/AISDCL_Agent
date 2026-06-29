# Platform Agent Selection Guide
# 跨平台 Agent 選擇指南

> **文檔版本**: v1.0
> **適用框架**: AISDLC-SDD v0.01
> **建立日期**: 2025-11-12
> **最後更新**: 2025-11-12
> **維護者**: SA Agent (Amanda), PM/PO Agent (Victoria)

---

## 📋 目的 (Purpose)

本文檔提供 **跨平台專案的 Agent 選擇指南**，協助團隊：

1. **快速識別平台類型**：Web、iOS、Android、Desktop、跨平台混合
2. **選擇適當的專業 Agent**：根據平台特性選擇最適合的 Agent
3. **協調多平台開發**：當專案涉及多平台時，如何協調不同 Agent
4. **避免技術選型錯誤**：提供平台特性對照表，避免選錯技術棧

---

## 🎯 適用範圍 (Scope)

本指南適用於：

- ✅ **跨平台專案**：需同時支援 iOS + Android、或 Web + Mobile
- ✅ **平台選型階段**：AISDLC Greenfield SOP 階段 3 (技術選型)
- ✅ **Agent 協作規劃**：決定哪些 Specialized Agent 需參與
- ✅ **技術評估**：比較原生開發 vs 跨平台框架

**不適用**：
- ❌ 單一平台專案（僅 Web 或僅 iOS）- 直接使用對應 Agent 即可
- ❌ 後端架構設計 - 參考 C4_Model_Guidelines.md

---

## 📱 第一部分：平台類型識別 (Platform Identification)

### 1.1 平台分類表

| 平台類型 | 說明 | 技術棧範例 | 目標使用者 |
|---------|-----|-----------|----------|
| **Web** | 瀏覽器存取的網站或 Web App | React, Vue, Angular | 桌機、筆電使用者 |
| **iOS** | Apple 裝置專用 App | Swift, SwiftUI, Objective-C | iPhone、iPad 使用者 |
| **Android** | Android 裝置專用 App | Kotlin, Java, Jetpack Compose | Android 手機、平板使用者 |
| **跨平台 Mobile** | 單一程式碼同時支援 iOS + Android | React Native, Flutter, Xamarin | iOS + Android 使用者 |
| **Desktop** | 桌面應用程式 | Electron, Qt, .NET WinForms | Windows, macOS, Linux 使用者 |
| **跨平台 Desktop** | 單一程式碼支援多桌面系統 | Electron, Tauri | Windows + macOS + Linux 使用者 |
| **混合型 (Hybrid)** | Web + Mobile 或 Web + Desktop | React (Web) + React Native (Mobile) | 全平台使用者 |

---

### 1.2 平台識別決策樹

```
使用者主要在哪裡使用此產品？
├─ 📱 手機/平板
│  ├─ 僅 iOS 使用者 → 原生 iOS (Swift)
│  ├─ 僅 Android 使用者 → 原生 Android (Kotlin)
│  └─ iOS + Android 使用者 → 跨平台 Mobile (React Native / Flutter)
│
├─ 💻 桌機/筆電
│  ├─ 僅需瀏覽器存取 → Web App (React / Vue)
│  ├─ 需要離線功能/硬體存取 → Desktop App (Electron)
│  └─ 跨平台桌面 (Win/Mac/Linux) → Electron / Tauri
│
└─ 🌐 多平台 (手機 + 桌機 + Web)
   └─ 混合型架構 (Web + Mobile App)
```

---

### 1.3 平台識別檢查表

**使用方式**：在 AISDLC Greenfield SOP 階段 2 (需求釐清) 時填寫

| 問題 | 選項 | 你的答案 | 建議平台 |
|-----|------|---------|---------|
| **Q1. 使用者主要使用場景？** | ☐ 通勤路上<br>☐ 辦公室桌前<br>☐ 家中沙發<br>☐ 混合場景 | [填寫] | 通勤 → Mobile<br>辦公室 → Web/Desktop<br>混合 → 跨平台 |
| **Q2. 是否需要離線功能？** | ☐ 是<br>☐ 否 | [填寫] | 是 → Native App<br>否 → Web 也可 |
| **Q3. 是否需要使用硬體功能？** | ☐ 相機<br>☐ GPS<br>☐ 推送通知<br>☐ 生物辨識<br>☐ 都不需要 | [填寫] | 需要 → Native/跨平台 App<br>不需要 → Web 優先 |
| **Q4. 目標使用者裝置分佈？** | ☐ 80%+ iOS<br>☐ 80%+ Android<br>☐ iOS + Android 均衡<br>☐ 不確定 | [填寫] | 單一系統 → 原生<br>均衡 → 跨平台 |
| **Q5. 預算與時程限制？** | ☐ 預算充足、時間不急<br>☐ 預算有限、需快速上線<br>☐ 預算充足、需快速上線 | [填寫] | 充足+不急 → 原生<br>有限+快速 → 跨平台 |

**範例 (MoneyTracker)**：

| 問題 | 你的答案 | 建議平台 |
|-----|---------|---------|
| Q1. 使用場景 | 通勤路上、等待結帳時 | **Mobile** |
| Q2. 離線功能 | 是 (需離線記帳) | **Native App** |
| Q3. 硬體功能 | 相機 (拍攝收據)、推送通知 (預算提醒) | **Native/跨平台 App** |
| Q4. 裝置分佈 | iOS + Android 均衡 | **跨平台 Mobile** |
| Q5. 預算與時程 | 預算有限、需快速上線 | **跨平台 (React Native/Flutter)** |

**最終決策**: **跨平台 Mobile App (React Native)**

---

## 🤖 第二部分：Agent 選擇對照表 (Agent Selection Matrix)

### 2.1 平台與 Specialized Agent 對應表

| 平台類型 | 推薦 Specialized Agent | Agent 檔案名稱 | 主要職責 |
|---------|----------------------|---------------|---------|
| **Web (前端)** | Web Architect<br>+ Senior Developer | `sd-web-architect.yaml`<br>`dev-senior.yaml` | 前端架構設計、元件設計、狀態管理 |
| **iOS (原生)** | Mobile Architect (iOS)<br>+ Senior Developer | `sd-mobile-architect.yaml`<br>`dev-senior.yaml` | iOS 架構設計、SwiftUI/UIKit 選型 |
| **Android (原生)** | Mobile Architect (Android)<br>+ Senior Developer | `sd-mobile-architect.yaml`<br>`dev-senior.yaml` | Android 架構設計、Jetpack Compose 選型 |
| **跨平台 Mobile** | Mobile Architect<br>+ Senior Developer | `sd-mobile-architect.yaml`<br>`dev-senior.yaml` | 跨平台框架選型 (React Native/Flutter) |
| **Desktop** | Web Architect (Electron)<br>或 Senior Developer | `sd-web-architect.yaml`<br>`dev-senior.yaml` | Desktop 架構設計 (Electron/Tauri) |
| **Backend API** | SD-Architect (Marcus)<br>+ DevOps Engineer | `05.sd-architect-zh.yaml`<br>`devops-engineer.yaml` | 後端架構、API 設計、基礎設施 |

---

### 2.2 核心 Agent (Core Agents) 在跨平台專案中的角色

| 核心 Agent | 角色 | 跨平台專案中的職責 |
|-----------|-----|------------------|
| **SA (Amanda)** | System Analyst | 分析需求、確認各平台功能差異、整合各平台需求 |
| **BA (Beatrice)** | Business Analyst | 驗證商業價值、確認各平台優先順序 |
| **PM/PO (Victoria)** | Product Manager | 決定平台發布順序 (如先 iOS 再 Android)、MVP 範圍 |
| **SD (Marcus)** | System Designer | 設計跨平台架構、API 規格、資料同步機制 |
| **Dev (David)** | Developer | 評估跨平台框架學習曲線、開發可行性 |
| **QA (Quincy)** | QA Engineer | 規劃各平台測試策略、整合測試 |

---

### 2.3 Specialized Agent 詳細說明

#### 🎨 SD-Web-Architect (Web 架構師)

**使用時機**：
- ✅ 專案包含 Web 前端 (React, Vue, Angular)
- ✅ 需要設計 Web 元件架構
- ✅ 需要評估前端狀態管理方案 (Redux, MobX, Zustand)

**檔案位置**: `agent/specialized/sd-web-architect.yaml`

**主要職責**：
- 設計 Web 前端架構 (Component Hierarchy, Routing, State Management)
- 評估 UI 框架選型 (React vs Vue vs Angular)
- 設計 API 整合策略 (RESTful, GraphQL)
- 效能優化建議 (Code Splitting, Lazy Loading)

**與核心 Agent 協作**：
- **SD (Marcus)**: Marcus 負責整體架構，Web-Architect 專注前端細節
- **Dev (David)**: Web-Architect 提供設計，David 評估實作可行性

---

#### 📱 SD-Mobile-Architect (Mobile 架構師)

**使用時機**：
- ✅ 專案包含 iOS、Android、或跨平台 Mobile App
- ✅ 需要選擇原生 vs 跨平台框架
- ✅ 需要設計 Mobile 特有功能 (離線儲存, 推送通知, 相機整合)

**檔案位置**: `agent/specialized/sd-mobile-architect.yaml`

**主要職責**：
- 評估跨平台框架選型 (React Native vs Flutter vs Native)
- 設計 Mobile 架構 (MVVM, MVI, Clean Architecture)
- 設計離線資料同步機制
- 規劃平台特有功能實作 (iOS: HealthKit, Android: WorkManager)

**與核心 Agent 協作**：
- **SD (Marcus)**: Marcus 負責後端 API，Mobile-Architect 負責 Mobile 端架構
- **QA (Quincy)**: 協作設計各平台測試策略

---

#### 💻 Dev-Senior (資深開發者)

**使用時機**：
- ✅ 需要評估複雜技術方案的可行性
- ✅ 需要快速原型驗證 (POC)
- ✅ 團隊中有資淺開發者，需要技術指導

**檔案位置**: `agent/specialized/dev-senior.yaml`

**主要職責**：
- 評估新技術的學習曲線與風險
- 建立程式碼規範與最佳實踐
- Code Review 與技術指導
- 快速實作技術 POC

---

#### 🔧 DevOps-Engineer (DevOps 工程師)

**使用時機**：
- ✅ 需要設計 CI/CD Pipeline
- ✅ 需要規劃多平台部署策略 (iOS App Store, Google Play, Web Hosting)
- ✅ 需要設計基礎設施 (雲端服務、資料庫、CDN)

**檔案位置**: `agent/specialized/devops-engineer.yaml`

**主要職責**：
- 設計 CI/CD Pipeline (GitHub Actions, Jenkins)
- 規劃多平台部署流程
- 基礎設施設計 (AWS, GCP, Azure)
- 監控與告警機制

---

## 🔀 第三部分：跨平台場景與 Agent 協作策略

### 3.1 場景 1: iOS + Android (跨平台 Mobile)

**專案範例**: MoneyTracker (個人記帳 App)

**技術選型**: React Native

#### Agent 組合

| 階段 | 核心 Agent | Specialized Agent | 協作重點 |
|-----|-----------|------------------|---------|
| **階段 2-3: 需求與選型** | SA (Amanda)<br>PM (Victoria) | Mobile-Architect | 確認是否需要平台特有功能、評估原生 vs 跨平台 |
| **階段 4-5: 設計** | SD (Marcus)<br>SA (Amanda) | Mobile-Architect<br>Dev-Senior | 設計跨平台架構、API 規格、離線同步機制 |
| **階段 6-7: 實作** | Dev (David) | Dev-Senior | 開發 React Native 元件、整合原生模組 |
| **階段 8: 測試** | QA (Quincy) | QA-Mobile-Tester | 分別測試 iOS 與 Android 平台 |
| **階段 9: 部署** | Dev (David) | DevOps-Engineer | 設定 iOS App Store + Google Play 部署流程 |

#### 協作流程圖

```
階段 3: 技術選型
├─ PM (Victoria) 主持會議
├─ SA (Amanda) 分析平台需求
├─ Mobile-Architect 評估框架選型
│  ├─ 選項 1: React Native (推薦)
│  ├─ 選項 2: Flutter
│  └─ 選項 3: 原生開發 (iOS + Android 分開)
└─ 決策: React Native

階段 5: 架構設計
├─ SD (Marcus) 設計後端 API
├─ Mobile-Architect 設計前端架構
│  ├─ 狀態管理: Redux Toolkit
│  ├─ 導航: React Navigation
│  ├─ 本地儲存: SQLite (react-native-sqlite-storage)
│  └─ 平台差異處理: Platform.OS 判斷
└─ Dev-Senior 驗證可行性

階段 8: 測試
├─ QA (Quincy) 規劃測試策略
├─ QA-Mobile-Tester (iOS) 測試 iPhone/iPad
├─ QA-Mobile-Tester (Android) 測試 Pixel/Samsung
└─ 整合測試報告
```

---

### 3.2 場景 2: Web + Mobile (混合平台)

**專案範例**: 電商平台 (Web 官網 + Mobile App)

**技術選型**:
- Web: React (Next.js)
- Mobile: React Native

#### Agent 組合

| 階段 | 核心 Agent | Specialized Agent | 協作重點 |
|-----|-----------|------------------|---------|
| **階段 2-3: 需求與選型** | SA (Amanda)<br>PM (Victoria) | Web-Architect<br>Mobile-Architect | 劃分 Web 與 Mobile 功能範圍、共用 API 設計 |
| **階段 4-5: 設計** | SD (Marcus) | Web-Architect<br>Mobile-Architect | 設計統一 API、Web 與 Mobile 共用元件策略 |
| **階段 6-7: 實作** | Dev (David) | Dev-Senior (Web)<br>Dev-Senior (Mobile) | 分工開發、共用程式碼 (Monorepo) |
| **階段 8: 測試** | QA (Quincy) | QA-Web-Tester<br>QA-Mobile-Tester | 跨平台整合測試 |
| **階段 9: 部署** | Dev (David) | DevOps-Engineer | Web (Vercel) + Mobile (App Store/Play) |

#### 程式碼共用策略

**方案 1: Monorepo (推薦)**

```
project/
├── packages/
│   ├── web/              # Next.js Web App
│   ├── mobile/           # React Native App
│   ├── shared/           # 共用邏輯
│   │   ├── api/          # API Client
│   │   ├── utils/        # 工具函式
│   │   └── types/        # TypeScript 類型定義
│   └── ui-components/    # 共用 UI 元件 (需適配平台)
```

**方案 2: 分離 Repository**

```
web-repo/        # Web 前端
mobile-repo/     # Mobile App
api-repo/        # 後端 API
shared-lib/      # 共用邏輯 (發布為 npm 套件)
```

---

### 3.3 場景 3: iOS Only (原生 iOS)

**專案範例**: Apple Watch 健康追蹤 App

**技術選型**: Swift + SwiftUI

#### Agent 組合

| 階段 | 核心 Agent | Specialized Agent | 協作重點 |
|-----|-----------|------------------|---------|
| **階段 2-3: 需求與選型** | SA (Amanda)<br>PM (Victoria) | Mobile-Architect (iOS 專家) | 確認 iOS 特有功能 (HealthKit, WatchKit) |
| **階段 4-5: 設計** | SD (Marcus) | Mobile-Architect | 設計 iOS 架構 (MVVM + Combine) |
| **階段 6-7: 實作** | Dev (David) | Dev-Senior (iOS) | 開發 SwiftUI 介面、整合 HealthKit |
| **階段 8: 測試** | QA (Quincy) | QA-Mobile-Tester (iOS) | 測試 iPhone + Apple Watch |
| **階段 9: 部署** | Dev (David) | DevOps-Engineer | App Store Connect 部署 |

---

### 3.4 場景 4: Desktop App (Electron)

**專案範例**: 設計工具、IDE

**技術選型**: Electron + React

#### Agent 組合

| 階段 | 核心 Agent | Specialized Agent | 協作重點 |
|-----|-----------|------------------|---------|
| **階段 2-3: 需求與選型** | SA (Amanda)<br>PM (Victoria) | Web-Architect | 確認是否需要硬體存取 (檔案系統、系統通知) |
| **階段 4-5: 設計** | SD (Marcus) | Web-Architect<br>Dev-Senior | 設計 Electron 架構 (Main Process vs Renderer Process) |
| **階段 6-7: 實作** | Dev (David) | Dev-Senior | 開發 Electron App、整合原生模組 |
| **階段 8: 測試** | QA (Quincy) | QA-Automation | 跨平台測試 (Windows/macOS/Linux) |
| **階段 9: 部署** | Dev (David) | DevOps-Engineer | 打包與簽章 (electron-builder) |

---

## 📋 第四部分：Agent 選擇決策流程圖 (Decision Flowchart)

### 4.1 完整決策流程

```
專案啟動
    ↓
[步驟 1] 使用「平台識別檢查表」(見 1.3)
    ↓
[步驟 2] 確認平台類型
    ├─ Mobile (iOS + Android) → 跳至 4.2
    ├─ Web Only → 跳至 4.3
    ├─ Web + Mobile → 跳至 4.4
    └─ Desktop → 跳至 4.5
    ↓
[步驟 3] 查詢「Agent 選擇對照表」(見 2.1)
    ↓
[步驟 4] 確認 Agent 組合
    ├─ 核心 Agent (必選): SA, BA, PM, SD, Dev, QA
    └─ Specialized Agent (按需選擇)
    ↓
[步驟 5] 規劃 Agent 協作流程
    ↓
完成 Agent 選擇
```

---

### 4.2 Mobile (跨平台) 決策流程

```
專案需要 iOS + Android
    ↓
是否需要高效能/複雜動畫？
├─ 是 → 考慮 Flutter 或原生開發
└─ 否 → React Native 優先
    ↓
是否需要大量平台特有功能 (如 HealthKit, ARKit)？
├─ 是 → 原生開發 (Swift + Kotlin)
└─ 否 → 跨平台框架 (React Native / Flutter)
    ↓
團隊技能背景？
├─ 熟悉 JavaScript/React → React Native
├─ 熟悉 Dart → Flutter
└─ 熟悉 Swift/Kotlin → 原生開發
    ↓
選擇 Specialized Agent:
├─ Mobile-Architect (架構設計)
├─ Dev-Senior (技術指導)
└─ QA-Mobile-Tester (測試)
```

---

### 4.3 Web Only 決策流程（詳細版）

#### 4.3.1 Web 應用類型識別

```
專案僅需 Web
    ↓
[步驟 1] 確認 Web 應用類型
    ↓
使用者如何訪問此 Web 應用？
├─ 🌐 公開網站 (需 SEO、搜尋引擎曝光)
│  ├─ 內容為主 (部落格、新聞、文檔)
│  │  └─ 選擇: SSG (Static Site Generation)
│  │     - Next.js (Static Export)
│  │     - Gatsby
│  │     - VitePress
│  │
│  ├─ 動態內容 + SEO (電商、社群、預訂平台)
│  │  └─ 選擇: SSR (Server-Side Rendering)
│  │     - Next.js (App Router)
│  │     - Nuxt.js (Vue)
│  │     - SvelteKit
│  │
│  └─ 行銷頁面 (Landing Page、活動頁)
│     └─ 選擇: SSG 或 Jamstack
│        - Next.js Static
│        - Astro
│
├─ 🔒 企業內部系統 (不需 SEO、僅內部使用)
│  ├─ 管理後台 (CRM、ERP、Dashboard)
│  │  └─ 選擇: SPA (Single Page Application)
│  │     - React + Vite
│  │     - Vue 3 + Vite
│  │     - Angular
│  │
│  ├─ 數據視覺化 (BI Dashboard、監控面板)
│  │  └─ 選擇: SPA + 數據庫視化庫
│  │     - React + D3.js/Recharts
│  │     - Vue + ECharts
│  │
│  └─ 協作工具 (即時編輯、即時通訊)
│     └─ 選擇: SPA + WebSocket
│        - React + Socket.io
│        - Vue + Collab Framework
│
└─ 🏪 C2C/B2C 平台 (混合需求)
   ├─ 首頁 + 商品頁 (需 SEO)
   │  └─ SSR
   ├─ 會員中心 + 購物車 (不需 SEO)
   │  └─ SPA (Client-Side Rendering)
   └─ 選擇: 混合模式
      - Next.js (混合 SSR + CSR)
      - Nuxt.js (Universal Mode)
```

---

#### 4.3.2 Web 專案特性檢查清單

**使用時機**: AISDLC Greenfield SOP 階段 2-3 (需求釐清 → 技術選型)

| 檢查項目 | 問題 | 選項 | 技術建議 |
|---------|-----|------|---------|
| **SEO 需求** | 是否需要搜尋引擎索引？ | ☐ 是<br>☐ 否 | 是 → SSR/SSG<br>否 → SPA |
| **初始載入速度** | 首頁載入時間要求？ | ☐ <1秒 (極快)<br>☐ 1-3秒 (一般)<br>☐ >3秒 (可接受) | <1秒 → SSG<br>1-3秒 → SSR<br>>3秒 → SPA |
| **內容更新頻率** | 內容多久更新一次？ | ☐ 即時<br>☐ 每日<br>☐ 每週/月 | 即時 → SSR<br>每日 → SSR/SSG<br>每週+ → SSG |
| **互動複雜度** | 是否有複雜使用者互動？ | ☐ 高 (協作、即時)<br>☐ 中 (表單、篩選)<br>☐ 低 (閱讀為主) | 高 → SPA + WebSocket<br>中 → SSR/SPA<br>低 → SSG |
| **即時通訊** | 是否需要即時功能？ | ☐ 是 (聊天、通知)<br>☐ 否 | 是 → WebSocket/SSE<br>否 → RESTful API |
| **離線支援** | 是否需要離線功能？ | ☐ 是<br>☐ 否 | 是 → PWA + Service Worker<br>否 → 標準 Web |
| **使用者認證** | 認證方式？ | ☐ OAuth/OIDC<br>☐ JWT<br>☐ Session<br>☐ 無 | OAuth → Auth0/Clerk<br>JWT → 自建<br>Session → SSR |
| **資料量** | 單頁資料量？ | ☐ 大 (>1000筆)<br>☐ 中 (100-1000筆)<br>☐ 小 (<100筆) | 大 → 虛擬滾動<br>中 → 分頁<br>小 → 一次載入 |
| **目標瀏覽器** | 需支援的瀏覽器？ | ☐ 現代瀏覽器 (Chrome/Firefox/Safari 最新)<br>☐ IE11+ | 現代 → ESM<br>IE11 → Polyfill |

**範例填寫 (電商平台 Web 端)**:

| 檢查項目 | 答案 | 技術決策 |
|---------|-----|---------|
| SEO 需求 | 是 (商品頁需被 Google 索引) | **SSR** |
| 初始載入速度 | <1秒 (競爭激烈) | **SSG (首頁) + SSR (商品頁)** |
| 內容更新頻率 | 即時 (庫存、價格變動) | **SSR** |
| 互動複雜度 | 中 (篩選、購物車、結帳) | **SSR + Client Hydration** |
| 即時通訊 | 是 (客服聊天) | **WebSocket (Socket.io)** |
| 離線支援 | 否 (電商不需離線) | **標準 Web** |
| 使用者認證 | OAuth (Google/FB 登入) | **NextAuth.js** |
| 資料量 | 大 (商品列表 >1000 筆) | **分頁 + 無限滾動** |

**最終決策**: **Next.js 14 (App Router) + React Server Components + Socket.io**

---

#### 4.3.3 Web 技術棧選擇詳細流程

```
[步驟 1] 確認 Web 應用類型 (見 4.3.1)
    ↓
[步驟 2] 選擇前端框架

框架選擇決策樹：
├─ 團隊技能？
│  ├─ 熟悉 React → React 生態系
│  ├─ 熟悉 Vue → Vue 生態系
│  ├─ 熟悉 Angular → Angular
│  └─ 新專案/無偏好 → 推薦 React (生態系最完整)
│
├─ 需要 SSR？
│  ├─ React + SSR → Next.js (推薦)
│  ├─ Vue + SSR → Nuxt.js
│  ├─ Svelte + SSR → SvelteKit
│  └─ 不需要 SSR → Vite + React/Vue/Svelte
│
└─ 專案規模？
   ├─ 大型 (>50 頁面) → Next.js / Nuxt.js (內建路由、優化)
   ├─ 中型 (10-50 頁面) → Vite + React Router
   └─ 小型 (<10 頁面) → Vite + React (無需路由框架)

    ↓
[步驟 3] 選擇狀態管理

狀態管理決策：
├─ 複雜度高 (跨元件共享狀態多)？
│  ├─ React → Redux Toolkit / Zustand
│  ├─ Vue → Pinia (Vue 3) / Vuex (Vue 2)
│  └─ Angular → NgRx
│
├─ 複雜度中 (少量全域狀態)？
│  ├─ React → React Context + useReducer
│  ├─ Vue → Composition API (ref/reactive)
│  └─ Angular → Services
│
└─ 複雜度低 (幾乎無共享狀態)？
   └─ 無需狀態管理庫，使用內建功能即可

    ↓
[步驟 4] 選擇 UI 元件庫

UI 元件庫選擇：
├─ 需要客製化設計？
│  ├─ 高度客製 → Tailwind CSS + Headless UI
│  │  - shadcn/ui (React)
│  │  - Radix UI (React)
│  └─ 中度客製 → Material-UI / Ant Design (可主題化)
│
├─ 快速開發 (使用預設設計)？
│  ├─ React → Material-UI / Ant Design / Chakra UI
│  ├─ Vue → Vuetify / Element Plus / Naive UI
│  └─ Angular → Angular Material
│
└─ 企業後台 (專業、資料密集)？
   └─ Ant Design (React/Vue) / AG Grid (資料表格)

    ↓
[步驟 5] 選擇部署策略

部署平台選擇：
├─ SSG/SSR (Next.js/Nuxt.js)
│  ├─ Vercel (推薦，Next.js 原生支援)
│  ├─ Netlify (SSG 優化)
│  └─ AWS Amplify / Azure Static Web Apps
│
├─ SPA (React/Vue/Angular)
│  ├─ Netlify / Vercel (靜態檔案託管)
│  ├─ AWS S3 + CloudFront
│  └─ GitHub Pages (小型專案)
│
└─ 需要後端整合？
   ├─ Node.js 後端 → Vercel / Railway / Render
   ├─ Container 部署 → AWS ECS / Google Cloud Run
   └─ 傳統伺服器 → Nginx + PM2

    ↓
[步驟 6] 確認 Specialized Agent

選擇 Agent 組合：
├─ Web-Architect (sd-web-architect.yaml)
│  - 負責前端架構設計
│  - 選擇框架、狀態管理、元件設計
│
├─ Dev-Senior (dev-senior.yaml)
│  - Code Review
│  - 效能優化、安全性審查
│
├─ QA-Web-Tester (qa-web-tester.yaml)
│  - 跨瀏覽器測試
│  - E2E 測試 (Playwright/Cypress)
│
└─ DevOps-Engineer (devops-engineer.yaml)
   - CI/CD 設置
   - 部署自動化
```

---

#### 4.3.4 Web 專案完整案例：電商平台 (Web Only)

**專案名稱**: BnB Marketplace (住宿預訂平台 - 純 Web 版)

**需求摘要**:
- 公開網站，需要 SEO (Google 搜尋曝光)
- 房源列表、詳細頁需被搜尋引擎索引
- 會員中心、預訂流程不需 SEO
- 即時聊天功能 (房東-房客溝通)

##### 平台識別

| 檢查項目 | 答案 | 決策 |
|---------|-----|------|
| Web 應用類型 | C2C 平台 (混合需求) | **混合模式** |
| SEO 需求 | 是 (房源頁需 SEO) | **SSR (房源) + CSR (會員中心)** |
| 初始載入速度 | <1秒 (首頁) | **SSG (首頁)** |
| 內容更新頻率 | 即時 (房源可用性) | **SSR** |
| 互動複雜度 | 高 (日曆選擇、篩選、地圖) | **SPA (會員中心)** |
| 即時通訊 | 是 (聊天) | **WebSocket** |
| 離線支援 | 否 | 標準 Web |
| 使用者認證 | OAuth (Google/Facebook) + Email | **NextAuth.js** |
| 資料量 | 大 (房源 >10000 筆) | **分頁 + 無限滾動** |

**最終技術棧決策**:
- 前端框架: **Next.js 14 (App Router)**
- 狀態管理: **Zustand** (輕量、易用)
- UI 元件庫: **Tailwind CSS + shadcn/ui** (客製化設計)
- 地圖整合: **Mapbox GL JS**
- 即時通訊: **Socket.io**
- 部署平台: **Vercel**

##### Agent 組合

| 階段 | 核心 Agent | Specialized Agent | 協作重點 |
|-----|-----------|------------------|---------|
| **階段 2: 需求釐清** | SA (Amanda)<br>BA (Beatrice)<br>PM (Victoria) | - | 確認 Web Only 可行性、SEO 需求、功能優先級 |
| **階段 3: 技術選型** | SA (Amanda)<br>SD (Marcus) | **Web-Architect** | 評估 Next.js vs Nuxt.js、SSR 策略、地圖方案 |
| **階段 4-5: 設計** | SD (Marcus)<br>SA (Amanda) | **Web-Architect**<br>Dev-Senior | 前端架構設計、API 規格、WebSocket 協議 |
| **階段 6-7: 實作** | Dev (David) | **Dev-Senior** | 開發 Next.js 頁面、整合 Socket.io、地圖功能 |
| **階段 8: 測試** | QA (Quincy) | **QA-Web-Tester** | E2E 測試 (Playwright)、跨瀏覽器測試、效能測試 |
| **階段 9: 部署** | Dev (David) | **DevOps-Engineer** | Vercel 部署、環境變數設置、監控告警 |

##### 協作時間軸

```
Week 1-2: 需求分析
├─ SA (Amanda) 需求萃取 (72 問確認)
├─ BA (Beatrice) 商業價值驗證
│  └─ Kano 模型分析：聊天功能 (Delighter)
└─ PM (Victoria) MVP 定義
   └─ Phase 1: 房源瀏覽 + 預訂
   └─ Phase 2: 聊天功能

Week 3: 技術選型
├─ SA (Amanda) + SD (Marcus) 主持技術評估會議
├─ Web-Architect 提供方案評估
│  ├─ 方案 1: Next.js 14 (推薦) ✅
│  ├─ 方案 2: Nuxt.js 3
│  └─ 方案 3: SPA (Vite + React)
├─ Dev (David) 評估團隊技能
└─ 決策: Next.js 14 (App Router) + Vercel

Week 4-5: 架構設計
├─ SD (Marcus) 設計後端 API
│  └─ RESTful API + WebSocket 端點
├─ Web-Architect 設計前端架構
│  ├─ 路由設計
│  │  ├─ / (首頁) → SSG
│  │  ├─ /listings → SSR (房源列表)
│  │  ├─ /listings/[id] → SSR (房源詳細頁)
│  │  ├─ /dashboard → CSR (會員中心)
│  │  └─ /messages → CSR + WebSocket (聊天)
│  ├─ 狀態管理: Zustand
│  │  ├─ userStore (使用者資訊)
│  │  ├─ searchStore (搜尋條件)
│  │  └─ chatStore (聊天訊息)
│  └─ 元件設計
│     ├─ ListingCard (房源卡片)
│     ├─ DateRangePicker (日期選擇器)
│     ├─ MapView (地圖檢視)
│     └─ ChatWidget (聊天元件)
├─ Dev-Senior 審查可行性
└─ 產出: SRD, API Spec, 元件規格

Week 6-10: 開發
├─ Dev (David) 實作功能
│  ├─ Week 6: 首頁 + 房源列表 (SSR)
│  ├─ Week 7: 房源詳細頁 + 預訂流程
│  ├─ Week 8: 會員中心 + 身份驗證 (NextAuth.js)
│  ├─ Week 9: 地圖整合 (Mapbox)
│  └─ Week 10: 聊天功能 (Socket.io)
├─ Dev-Senior 每週 Code Review
│  └─ 重點: 效能優化、SEO 設置、安全性
└─ SA (Amanda) 驗證需求符合度

Week 11-12: 測試與部署
├─ QA (Quincy) 整合測試
├─ QA-Web-Tester 執行測試
│  ├─ E2E 測試 (Playwright)
│  │  └─ 測試腳本: 搜尋 → 檢視房源 → 預訂 → 付款
│  ├─ 跨瀏覽器測試
│  │  └─ Chrome, Firefox, Safari, Edge
│  ├─ 效能測試 (Lighthouse)
│  │  └─ 目標: 首頁 Performance Score >90
│  └─ SEO 測試
│     └─ Google Search Console 驗證
├─ DevOps-Engineer 設置部署
│  ├─ Vercel 專案設定
│  ├─ 環境變數配置
│  │  └─ NEXTAUTH_SECRET, MAPBOX_TOKEN, DATABASE_URL
│  ├─ CI/CD Pipeline (GitHub Actions)
│  └─ 監控設置 (Vercel Analytics + Sentry)
└─ 上線: https://bnb-marketplace.vercel.app
```

---

#### 4.3.5 選擇 Specialized Agent

**Web Only 專案建議 Agent 組合**:

| Agent | 檔案名稱 | 何時使用 | 職責重點 |
|-------|---------|---------|---------|
| **Web-Architect** | `sd-web-architect.yaml` | **必選** (所有 Web 專案) | 前端架構設計、框架選型、元件設計、狀態管理、路由設計 |
| **Dev-Senior** | `dev-senior.yaml` | 推薦 (中大型專案) | Code Review、效能優化、安全性審查、最佳實踐指導 |
| **QA-Web-Tester** | `qa-web-tester.yaml` | **必選** (所有 Web 專案) | E2E 測試、跨瀏覽器測試、效能測試、SEO 測試 |
| **DevOps-Engineer** | `devops-engineer.yaml` | 推薦 (需 CI/CD) | 部署自動化、環境管理、監控告警、基礎設施 |
| **Security-Engineer** | `security-engineer.yaml` | 可選 (涉及金流/敏感資料) | 安全性審計、OWASP Top 10 檢查、認證授權審查 |
| **Performance-Engineer** | `performance-engineer.yaml` | 可選 (高流量/效能要求高) | 效能優化、快取策略、CDN 配置、負載測試 |

**決策流程**:

```
Web 專案已確認
    ↓
是否為中大型專案 (>20 頁面)？
├─ 是 → 必選: Web-Architect + Dev-Senior + QA-Web-Tester + DevOps-Engineer
└─ 否 → 必選: Web-Architect + QA-Web-Tester
    ↓
是否涉及金流/敏感資料？
├─ 是 → 加入: Security-Engineer
└─ 否 → 不需要
    ↓
是否有高流量/效能要求？
├─ 是 → 加入: Performance-Engineer
└─ 否 → 不需要
```

---

### 4.4 Web + Mobile 混合決策流程

```
專案需要 Web + Mobile
    ↓
是否需要共用大量程式碼？
├─ 是 → Monorepo + React/React Native
└─ 否 → 分離 Repository
    ↓
是否需要統一 API？
├─ 是 → 設計 Universal API (支援 Web + Mobile)
└─ 否 → 分別設計 API
    ↓
選擇 Specialized Agent:
├─ Web-Architect (Web 前端)
├─ Mobile-Architect (Mobile 前端)
├─ SD-Architect (統一 API 設計)
└─ DevOps-Engineer (多平台部署)
```

---

### 4.5 Desktop 決策流程

```
專案需要 Desktop App
    ↓
是否需要跨平台 (Win/Mac/Linux)？
├─ 是 → Electron / Tauri
└─ 否 → 平台原生 (.NET WinForms, Cocoa)
    ↓
是否需要存取系統資源 (檔案、通知)？
├─ 是 → Electron (完整 Node.js 支援)
└─ 否 → Web App 包裝成 PWA
    ↓
選擇 Specialized Agent:
├─ Web-Architect (Electron 前端)
├─ Dev-Senior (Electron Main Process)
└─ DevOps-Engineer (打包與部署)
```

---

## 🔧 第五部分：實際案例分析 (Case Studies)

### 案例 1: MoneyTracker (個人記帳 App)

**需求**：iOS + Android 記帳 App，需離線儲存、推送通知

#### 平台識別

| 檢查項目 | 答案 | 結論 |
|---------|-----|------|
| 使用場景 | 通勤路上、等待結帳時 | Mobile |
| 離線功能 | 需要 (離線記帳) | 必須原生或跨平台 App |
| 硬體功能 | 相機 (拍攝收據)、推送通知 | 必須 App |
| 裝置分佈 | iOS + Android 均衡 | 跨平台 |
| 預算時程 | 預算有限、快速上線 | 跨平台框架 |

**平台決策**: **跨平台 Mobile (React Native)**

#### Agent 組合

| 角色 | Agent | 檔案名稱 |
|-----|-------|---------|
| **需求分析** | SA (Amanda) | `04.sa-analyst-zh.yaml` |
| **業務驗證** | BA (Beatrice) | `02.ba-business-analyst-zh.yaml` |
| **產品決策** | PM (Victoria) | `03.pm-po-agent-zh.yaml` |
| **架構設計** | SD (Marcus) | `05.sd-architect-zh.yaml` |
| **Mobile 架構** | Mobile-Architect | `sd-mobile-architect.yaml` |
| **實作評估** | Dev (David) | `06.dev-developer-zh.yaml` |
| **測試** | QA (Quincy) | `07.qa-tester-zh.yaml` |
| **Mobile 測試** | QA-Mobile-Tester | `qa-mobile-tester.yaml` |

#### 協作時間軸

```
Week 1-2: 需求分析
├─ SA (Amanda) 主導需求萃取
├─ BA (Beatrice) 驗證商業價值
└─ PM (Victoria) 決定 MVP 範圍

Week 3: 技術選型
├─ Mobile-Architect 評估框架
│  ├─ React Native (推薦)
│  ├─ Flutter
│  └─ 原生開發
├─ Dev (David) 評估團隊技能
└─ 決策: React Native

Week 4-5: 架構設計
├─ SD (Marcus) 設計後端 API
├─ Mobile-Architect 設計前端架構
│  ├─ 狀態管理: Redux Toolkit
│  ├─ 導航: React Navigation
│  └─ 本地儲存: SQLite
└─ 產出: SRD, API Spec

Week 6-10: 開發
├─ Dev (David) 實作功能
├─ Dev-Senior 提供技術指導
└─ Code Review

Week 11-12: 測試與部署
├─ QA (Quincy) 整合測試
├─ QA-Mobile-Tester iOS 測試
├─ QA-Mobile-Tester Android 測試
└─ 上架 App Store + Google Play
```

---

### 案例 2: 電商平台 (Web + Mobile)

**需求**：Web 官網 + Mobile App，共用後端 API

#### 平台識別

| 檢查項目 | 答案 | 結論 |
|---------|-----|------|
| 使用場景 | 桌機瀏覽 (首次訪問) + 手機 App (回購) | Web + Mobile |
| 離線功能 | Mobile 需要 (購物車離線編輯) | Mobile: App, Web: PWA |
| 硬體功能 | 推送通知 (促銷提醒)、相機 (掃描條碼) | Mobile 需要 App |
| 裝置分佈 | Web 60%, Mobile 40% | 兩者並重 |
| 優先順序 | Web 先上線 (SEO 重要) | Phase 1: Web, Phase 2: Mobile |

**平台決策**:
- **Phase 1**: Web (Next.js)
- **Phase 2**: Mobile (React Native)

#### Agent 組合

| 階段 | 核心 Agent | Specialized Agent |
|-----|-----------|------------------|
| **Phase 1: Web** | SA, BA, PM, SD, Dev, QA | Web-Architect, Dev-Senior (Web), QA-Web-Tester |
| **Phase 2: Mobile** | SA, PM, SD, Dev, QA | Mobile-Architect, Dev-Senior (Mobile), QA-Mobile-Tester |
| **Phase 3: 整合** | SD, Dev, QA | Integration-Specialist |

---

### 案例 3: 企業內部工具 (Desktop App)

**需求**：設計工具，需存取本地檔案系統

#### 平台識別

| 檢查項目 | 答案 | 結論 |
|---------|-----|------|
| 使用場景 | 辦公室桌機 (Windows/macOS) | Desktop |
| 離線功能 | 需要 (不依賴網路) | Desktop App |
| 硬體功能 | 檔案系統存取、系統通知 | 必須 Desktop App |
| 裝置分佈 | Windows 70%, macOS 30% | 跨平台 Desktop |
| 預算時程 | 預算充足、快速上線 | Electron |

**平台決策**: **Electron + React**

#### Agent 組合

| 角色 | Agent | 重點職責 |
|-----|-------|---------|
| 架構設計 | SD (Marcus) + Web-Architect | Electron Main/Renderer Process 設計 |
| 實作 | Dev (David) + Dev-Senior | Electron 整合、原生模組 |
| 測試 | QA (Quincy) + QA-Automation | 跨平台自動化測試 |
| 部署 | DevOps-Engineer | electron-builder 打包、簽章 |

---

## 📚 第六部分：參考資料 (References)

### 6.1 相關 AISDLC 文檔

- **Greenfield SOP**: `scenarios/greenfield/SOP.md`
- **Specialized Agents 目錄**: `agent/specialized/`
- **C4 Model Guidelines**: `guides/C4_Model_Guidelines.md`
- **Estimation Standards**: `guides/Estimation_Standards.md`

---

### 6.2 跨平台框架比較表

| 框架 | 語言 | 優點 | 缺點 | 適用場景 |
|-----|------|------|------|---------|
| **React Native** | JavaScript/TypeScript | 生態系豐富、熱更新、社群活躍 | 效能略遜原生、升級成本高 | 快速開發、業務邏輯為主 |
| **Flutter** | Dart | 高效能、美觀 UI、跨平台一致性高 | 生態系較小、包體積較大 | 注重 UI/動畫的 App |
| **Xamarin** | C# | 與 .NET 生態整合、微軟支援 | 社群較小、效能中等 | .NET 團隊、企業 App |
| **原生開發** | Swift/Kotlin | 最佳效能、完整平台支援 | 需維護兩套程式碼、成本高 | 高效能需求、平台特有功能多 |

---

### 6.3 延伸閱讀

1. **React Native 官方文檔**: https://reactnative.dev/
2. **Flutter 官方文檔**: https://flutter.dev/
3. **Electron 官方文檔**: https://www.electronjs.org/
4. **Mobile App 架構指南**: Martin Fowler - Mobile App Architecture

---

## ✅ Agent 選擇檢查清單 (Selection Checklist)

完成平台與 Agent 選擇後，使用此清單驗證：

- [ ] **平台類型已明確**: Web / iOS / Android / Desktop / 混合
- [ ] **技術棧已決策**: 原生 vs 跨平台框架
- [ ] **核心 Agent 已確認**: SA, BA, PM, SD, Dev, QA 全數就位
- [ ] **Specialized Agent 已選擇**: 根據平台選擇對應專家
- [ ] **協作流程已規劃**: 明確各 Agent 在各階段的職責
- [ ] **文檔已準備**: 各 Agent 的 YAML 設定檔已載入
- [ ] **測試策略已確認**: 各平台測試方法已規劃
- [ ] **部署策略已確認**: 各平台部署流程已規劃

---

## 📝 變更記錄 (Change Log)

| 版本 | 日期 | 修改人 | 修改內容 |
|-----|------|--------|---------|
| v1.0 | 2025-11-12 | Amanda (SA) | 初版建立，定義跨平台 Agent 選擇標準 |

---

**文檔結束 (End of Document)**
