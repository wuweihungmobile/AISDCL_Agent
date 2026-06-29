# Greenfield Complete Development Flow
# 新專案完整開發流程

## Workflow 名稱
**greenfield-complete-flow** - Greenfield 專案端到端開發流程

## 描述
此工作流程涵蓋從零開始的全新專案開發完整生命週期，從需求收集、技術選型、架構設計，到 User Story 撰寫、Sprint 規劃和開發準備。適用於無既有系統限制、可自由選擇技術棧的全新專案。

**版本**: v0.01 | **最後更新**: 2026-04-17
**v0.01 更新**: 整合 SDD Spec-First Gate（SCG-0~SCG-6），所有規格文件必須在實作前通過對應閘門。繼承 v0.09 Mobile/多平台擴展支援。

## 適用場景
- **使用時機**：啟動全新專案、MVP 開發、新產品線
- **適用專案**：Web 應用、Mobile App（Android/iOS/macOS）、API 服務、SaaS 平台、多領域整合平台
- **執行頻率**：專案啟動時一次性執行（完整週期 3-5 天；含行動端需 4-7 天）

## 觸發條件
- 專案願景和業務目標已明確
- 已取得專案啟動授權和預算
- 核心團隊成員已到位
- 初步需求描述已準備（可以是文字、截圖、原型等）

---

# 角色與責任

## 主要負責人 (Primary Owner)
**Agent 角色**：SA (System Analyst) - Amanda
**責任**：
- 協調整個開發流程
- 確保需求分析品質
- 維護文檔追蹤鏈完整性
- 監督人機協作確認點執行

## 參與者 (Participants)
- **PM/PO (Victoria)**：業務價值評估、MVP 範圍定義、優先級決策
- **BA (Beatrice)**：利害關係人溝通、業務規則驗證、需求驗證
- **SD-Architect (Marcus/Sophia/Ethan)**：技術選型、架構設計、技術風險評估
- **Dev (Developer)**：實作可行性評估、工時估算、技術 Spike
- **QA (Quincy)**：測試策略規劃、Acceptance Criteria 定義、測試案例設計

## 審查者 (Reviewers)
- **PM/PO**：業務需求完整性、MVP 定義合理性
- **SD-Architect**：技術架構可行性、擴展性設計
- **QA-Lead**：測試覆蓋完整性、驗收標準明確性

---

# 輸入與前置條件

## 必要輸入文檔
- **專案願景文檔**：業務目標、目標使用者、核心價值主張
- **初步需求**：功能描述（文字/截圖/設計稿/原型）
- **預算和時限**：專案預算、交付時限、資源限制
- **團隊資訊**：團隊成員、技能矩陣、可用時間

## 前置條件
- 專案已獲得管理層批准
- 預算和資源已分配
- 核心團隊成員已確定並可投入
- 業務目標和成功標準已明確

## 所需資源
- **工具和系統**：
  - 協作平台（Notion/Confluence/Google Docs）
  - 專案管理工具（Jira/Linear/Trello）
  - 設計工具（Figma/Adobe XD）
  - 版本控制（GitHub/GitLab）
- **時間資源**：3-5 個工作日（全流程）
- **人力資源**：跨職能團隊（PM, SA, BA, SD, Dev, QA）

---


---

## SDD SCG 閘門整合（v0.01）

> 本 Workflow 整合 SDD Spec-First Gate，所有閘門**不可跳過**。

| 步驟 | 對應 SCG 閘門 | 強制產出 |
|------|-------------|---------|
| 步驟 1：需求提取與分析 | **SCG-0 準備** | FRD + User Stories + RTM 初版 |
| 步驟 2：技術選型與評估 | **SCG-1/2 準備** | ADR（技術棧選型） |
| 步驟 3：需求驗證與文件化 | **🔴 SCG-0 凍結** | FRD 凍結 + BA 驗證報告 |
| 步驟 4：系統架構設計 | **🔴 SCG-1/2 凍結** | SRD + C4 + ADR 全部 Accepted |
| 步驟 5：API 詳細規格生成 | **🔴 SCG-3 凍結** | OpenAPI 3.1 Contract Freeze |
| 步驟 6：User Story 撰寫 | SCG-0 補充 | AC-XXX-Y 完整 |
| 步驟 7：Sprint 規劃 | SCG-3 通過後 | Sprint Backlog |
| 步驟 8：開發準備 | SCG-3 通過後 | 開發規範 + Dev Checklist |
| 步驟 9：文檔一致性 | **SCG-4/5 準備** | RTM 100% 覆蓋 |

**🔷 整合閘門**：SCG-0 → SCG-1 → SCG-2 → SCG-3 → SCG-4 → SCG-5 → SCG-6
**📌 SDD 規則**：參考 `workflow/sdd-spec-first-gate/SDD_SPEC_FIRST_GATE.md`

# 執行步驟

## 步驟 1：需求提取與分析
**描述**：系統性收集和分析專案需求，識別功能清單、使用者角色、業務規則

**執行者**：SA (Amanda) + BA (Beatrice)

**具體作業**：
1. 執行 **requirements-extraction** workflow
2. 分析需求輸入（文字/截圖/設計稿）
3. 識別功能清單和使用者角色
4. 提取業務規則和約束條件
5. 分析非功能需求（效能、安全、可用性）

**人機協作確認點** 🔴：
- **確認點 1.1**：輸入理解確認（15 分鐘）
  - 系統呈現對需求的初步理解
  - 人類確認理解準確性並補充遺漏

- **確認點 1.2**：功能清單確認（20 分鐘）
  - 系統列出識別的所有功能
  - 人類確認完整性並補充遺漏功能
  - 確認功能優先級分類

- **確認點 1.3**：使用者角色確認（15 分鐘）
  - 系統列出識別的使用者角色和權限
  - 人類確認角色定義準確性

- **確認點 1.4**：業務規則確認（20 分鐘）
  - 系統列出關鍵業務規則和約束
  - 人類確認規則準確性並補充

**檢查點**：
- [ ] 所有需求輸入已分析完畢
- [ ] 功能清單完整且無遺漏
- [ ] 使用者角色定義清晰
- [ ] 業務規則明確且可驗證
- [ ] 所有確認點已完成並記錄

**品質標準**：
- 需求完整性：涵蓋功能性和非功能性需求
- 需求明確性：無模糊或歧義的描述
- 可追蹤性：每個需求有唯一 ID
- 零臆測：所有不確定點已與人類確認

**預估時間**：4-8 小時

**產出文件**：
- 需求提取報告 (Requirement Extraction Report)
- 功能清單 (Feature List)
- 使用者角色定義 (User Roles)
- 業務規則清單 (Business Rules)
- 人機協作記錄 (Collaboration Log)

---

## 步驟 2：技術選型與評估
**描述**：基於需求和團隊技能，選擇最適合的技術棧

**執行者**：SD-Architect (Marcus/Sophia/Ethan) + Dev

**具體作業**：
1. 執行 **tech-stack-selection** workflow
2. 分析需求對技術的要求（效能、擴展性、整合需求）
3. 評估團隊現有技能
4. 研究候選技術棧
5. 進行技術方案對比（優缺點、成本、學習曲線）
6. 評估技術風險

**人機協作確認點** 🔴：
- **確認點 2.1**：技術需求確認（15 分鐘）
  - 系統分析的技術需求是否完整
  - 補充特殊技術要求

- **確認點 2.2**：技術選型確認（30 分鐘）
  - 系統推薦的技術棧和理由
  - 審查替代方案對比
  - 確認最終技術選擇
  - 討論技術風險緩解措施

**檢查點**：
- [ ] 前端技術棧已選定
- [ ] 後端技術棧已選定
- [ ] 資料庫方案已確定
- [ ] 第三方服務已識別
- [ ] 技術風險已評估
- [ ] 團隊技能 gap 已識別

**品質標準**：
- 技術選型有充分理由和數據支撐
- 考慮團隊現有技能和學習曲線
- 評估長期維護成本
- 技術債風險可控

**預估時間**：2-4 小時

**產出文件**：
- 技術選型報告 (Tech Stack Selection Report)
- 技術方案對比表 (Technology Comparison)
- 技術風險評估 (Technical Risk Assessment)
- 學習計畫（如需要）

---

## 步驟 3：需求驗證與文件化
**描述**：多維度驗證需求，生成正式的 PRD 和 FRD

**執行者**：SA (Amanda) + BA (Beatrice) + PM/PO (Victoria)

**具體作業**：
1. 執行 **requirements-validation-and-documentation** workflow
2. 完整性驗證（SA）：檢查需求完整性和邏輯一致性
3. 業務價值驗證（PM/PO）：評估每個功能的業務價值
4. 技術可行性驗證（SD）：確認技術實現可行性
5. 生成 PRD（PM/PO 主導）
6. 生成 FRD（SA 主導）
7. 定義 MVP 範圍

**人機協作確認點** 🔴：
- **確認點 3.1**：驗證結果確認（20 分鐘）
  - 審查三維度驗證結果
  - 確認發現的問題和風險
  - 決定解決方案

- **確認點 3.2**：MVP 範圍確認（30 分鐘）
  - 審查 MVP 功能清單
  - 確認優先級排序
  - 確認時程可行性

- **確認點 3.3**：文檔確認（20 分鐘）
  - 審查 PRD 草稿
  - 審查 FRD 草稿
  - 確認文檔準確性和完整性

**檢查點**：
- [ ] 需求完整性驗證通過
- [ ] 業務價值評估完成
- [ ] 技術可行性確認
- [ ] PRD 完成並審核通過
- [ ] FRD 完成並審核通過
- [ ] MVP 範圍明確定義
- [ ] 功能優先級排序完成

**品質標準**：
- PRD 符合產品需求文檔標準
- FRD 符合功能需求文檔標準
- MVP 範圍合理且可交付
- 所有需求有明確驗收標準

**預估時間**：3-5 小時

**產出文件**：
- PRD (Product Requirements Document)
- FRD (Functional Requirements Document)
- MVP Definition
- 需求驗證報告 (Validation Report)
- 需求追蹤矩陣 (Requirements Traceability Matrix)

---

## 步驟 4：系統架構設計
**描述**：設計系統整體架構、資料庫 Schema、API 規格

**執行者**：SD-Architect (Marcus/Sophia/Ethan)

> **🔀 多平台專案擴展（Web + Mobile + Desktop）**：
> 若專案涉及 Android (Kotlin) / iOS / macOS (SwiftUI) 行動端，本步驟需同時：
> - 載入 `sd-mobile-architect` 進行行動端架構設計
> - 行動端架構與後端 API 設計需同步進行（Mobile API 設計差異詳見確認點 4.4）
> - 參考 SOP.md 平台特化 Agent 選擇表，確認 Architect Agent 組合

**具體作業**：
1. 設計系統整體架構（C4 Model）
2. 設計模組劃分和職責
3. 設計資料流和整合點
4. 設計資料庫 Schema（ER 圖、資料表結構）
5. 設計 API 規格（RESTful/GraphQL）
6. 設計認證授權機制
7. 設計部署架構
8. 撰寫 Architecture Decision Records (ADR)
9. **（行動端適用）** 設計 Mobile-specific API 策略（Batch API、壓縮、離線快取）
10. **（行動端適用）** 設計 QR Code / 掃碼整合架構（Camera API / ZXing / AVFoundation）

**人機協作確認點** 🔴：
- **確認點 4.1**：架構設計確認（30 分鐘）
  - 審查系統架構圖
  - 確認模組劃分合理性
  - 確認可擴展性設計

- **確認點 4.2**：資料設計確認（20 分鐘）
  - 審查資料庫 Schema
  - 確認資料模型正確性
  - 確認索引策略

- **確認點 4.3**：API 設計確認（20 分鐘）
  - 審查 API 端點定義
  - 確認 API 命名和結構
  - 確認錯誤處理機制

- **確認點 4.4**：行動端架構確認（20 分鐘）⚠️ 僅當專案含 Mobile/Desktop App 時執行
  - 確認 Mobile API 與 Web API 共用策略（共用 REST API vs 行動端專用端點）
  - 確認認證機制：Mobile 建議 JWT（無狀態），Web 可用 Session
  - 確認批量請求策略（Mobile 端應支援 Batch API 減少網路請求）
  - 確認 QR Code 掃碼架構（Camera API 整合方式、離線掃碼支援）
  - 確認 App 與 Backend 版本相容性策略（API 版本管理、向下相容）

**檢查點**：
- [ ] 系統架構圖完成（Context/Container/Component）
- [ ] 模組職責清晰定義
- [ ] 資料庫 Schema 設計完成
- [ ] API 規格定義完成
- [ ] 安全性設計完成
- [ ] 部署架構設計完成
- [ ] ADR 記錄完整
- [ ] （行動端適用）Mobile API 策略已定義
- [ ] （行動端適用）QR Code 整合架構已設計
- [ ] （行動端適用）App 版本相容性策略已定義

**品質標準**：
- 架構符合需求和非功能需求
- 設計考慮可擴展性和可維護性
- 安全性設計充分
- 技術決策有明確記錄（ADR）
- （行動端）Mobile 架構符合 iOS HIG / Android Material Design 平台指南

**預估時間**：4-6 小時（含行動端架構設計需加 1-2 小時）

**產出文件**：
- SRD (System Requirements Document)
- 系統架構圖 (Architecture Diagrams)
- 資料庫 Schema (Database Schema)
- API 規格文檔 (API Specification)
- Architecture Decision Records (ADR)
- 安全設計文檔 (Security Design)

---

## 步驟 5：API 詳細規格生成
**描述**：為每個 API 端點生成詳細規格文檔

**執行者**：SD-Architect (Marcus/Sophia/Ethan) + Dev

> **🔀 多平台 API 設計注意**：
> 若專案含行動端（Android/iOS/macOS），API 設計需區分以下差異：
>
> | 差異項目 | Web API | Mobile API |
> |---------|---------|-----------|
> | **認證機制** | Cookie Session 可用 | 強制使用 JWT（無狀態，支援 App 背景更新） |
> | **請求批量** | 單一請求為主 | 支援 Batch API，減少行動網路請求次數 |
> | **資料壓縮** | 選配 | 建議強制啟用 gzip/brotli（行動端流量敏感） |
> | **離線快取** | 不適用 | 提供快取友善的回應標頭（ETag / Cache-Control） |
> | **推播整合** | Web Push（選配） | FCM (Android) / APNs (iOS/macOS) Token 管理 API |
> | **QR Code** | 不適用 | 掃碼驗核 API（`POST /api/qr/verify`），支援離線預載格式 |
>
> **建議**: 使用「共用 REST API + 行動端特化端點」策略。核心 CRUD 端點共用，
> 行動端特定功能（掃碼、推播、批量同步）建立獨立端點，以 `/mobile/` 路徑前綴區分。

**具體作業**：
1. 執行 **api-specification-generation** workflow
2. 為每個 API 端點創建規格文件
3. 定義請求/回應格式
4. 定義認證要求
5. 定義錯誤處理
6. 提供使用範例
7. 建立 API Index
8. **（行動端適用）** 設計 Mobile-specific 端點（掃碼、推播、批量同步）
9. **（行動端適用）** 定義 QR Code API 規格（生成 + 驗核雙端點）

**人機協作確認點** 🔴：
- **確認點 5.1**：API 規格確認（20 分鐘）
  - 審查 API 端點完整性
  - 確認命名一致性
  - 確認錯誤碼定義

- **確認點 5.2**：行動端 API 差異確認（15 分鐘）⚠️ 僅當專案含 Mobile/Desktop App 時執行
  - 確認 JWT 認證策略（含 Refresh Token 機制）
  - 確認 Batch API 端點設計
  - 確認 QR Code API 規格（格式、離線支援、安全驗證）
  - 確認推播 Token 管理 API

**檢查點**：
- [ ] 所有 API 端點有詳細規格
- [ ] API Index 已建立
- [ ] 請求/回應格式明確
- [ ] 錯誤處理完整
- [ ] 使用範例清晰
- [ ] （行動端適用）Mobile 特化端點已定義
- [ ] （行動端適用）QR Code API 規格完整

**品質標準**：
- 每個 API 有獨立規格文件
- 遵循 API 設計最佳實踐
- 文檔清晰易懂
- （行動端）Mobile API 符合 RESTful 最佳實踐，並考慮行動網路特性

**預估時間**：2-3 小時（含行動端 API 設計需加 1 小時）

**產出文件**：
- API 規格文檔（每個端點）
- API Index
- API 使用範例
- （行動端適用）Mobile API 特化說明文件

---

## 步驟 6：User Story 撰寫與拆分
**描述**：將需求轉換為可執行的 User Stories 和 Acceptance Criteria

**執行者**：SA (Amanda) + QA (Quincy)

**具體作業**：
1. 執行 **user-story-and-design** workflow
2. 識別主要 Epics
3. 將 Epics 拆分為 User Stories
4. 撰寫 Acceptance Criteria（Given-When-Then）
5. 估算 Story Points
6. 識別 Story 依賴關係
7. 設計 Acceptance Tests

**人機協作確認點** 🔴：
- **確認點 6.1**：User Story 確認（30 分鐘）
  - 審查 User Story 清單
  - 確認 Story 大小合理（1-3 天）
  - 確認 Acceptance Criteria 明確

- **確認點 6.2**：Story Point 確認（15 分鐘）
  - 審查工時估算
  - 確認估算合理性
  - 調整過大或過小的 Story

- **確認點 6.3**：行動端 AC 差異確認（15 分鐘）⚠️ 僅當專案含 Mobile/Desktop App 時執行
  - 確認 Mobile User Stories 包含裝置權限 AC（相機/位置/通知）
  - 確認離線操作 Story 有明確的同步策略 AC
  - 確認 QR Code 掃碼 Story 標注需實機測試（模擬器無法完整驗證）
  - 確認推播通知 Story 包含 Deep Link AC
  - 確認 macOS (SwiftUI) 特殊 AC（Menu Bar、Keyboard Shortcuts、macOS 視窗管理）
  - 參考：SOP.md 階段 6 步驟 6.1 「Mobile 行動端 User Story 差異說明」

**檢查點**：
- [ ] 所有功能轉換為 User Stories
- [ ] 每個 Story 有明確 AC
- [ ] Story Points 估算完成
- [ ] 依賴關係已識別
- [ ] Acceptance Tests 設計完成
- [ ] （行動端適用）Mobile AC 包含裝置權限說明
- [ ] （行動端適用）需實機測試的 Story 已標注

**品質標準**：
- User Story 符合 INVEST 原則
- Acceptance Criteria 明確可測試
- Story 大小適中（1-3 天）
- 依賴關係清晰
- （行動端）Mobile AC 區分「Web 可測試」vs「需實機測試」

**預估時間**：3-4 小時（多模組系統可能需 5-6 小時）

**產出文件**：
- User Stories（完整清單）
- Acceptance Criteria
- Story Dependencies
- Story Point Estimation
- Acceptance Test Scenarios
- （行動端適用）Mobile 測試矩陣（裝置/OS 版本組合）

---

## 步驟 7：Sprint 規劃與路線圖
**描述**：規劃 Sprint 和發布路線圖

**執行者**：PM/PO (Victoria) + SA (Amanda)

**具體作業**：
1. 劃分 Sprint（通常 2 週一個 Sprint）
2. 規劃 Sprint 0（環境建置、架構搭建）
3. 分配 User Stories 到各 Sprint
4. 考慮依賴關係和風險
5. 定義里程碑
6. 制定發布計畫

**人機協作確認點** 🔴：
- **確認點 7.1**：Sprint 規劃確認（30 分鐘）
  - 審查 Sprint Roadmap
  - 確認每個 Sprint 的目標
  - 確認 Story 分配合理
  - 確認時程可行性

**檢查點**：
- [ ] Sprint 劃分完成
- [ ] Sprint 0 規劃完成
- [ ] User Stories 分配到 Sprint
- [ ] 里程碑定義完成
- [ ] 發布計畫完成
- [ ] 風險識別和緩解措施

**品質標準**：
- Sprint 目標明確
- Story 分配考慮依賴和風險
- 每個 Sprint 可交付價值
- 時程合理可行

**預估時間**：2-3 小時

**產出文件**：
- Sprint Roadmap
- Sprint 0 Plan
- Sprint Backlog（每個 Sprint）
- Release Plan
- Risk Register
- Milestone Definition

---

## 步驟 8：開發準備與規範制定
**描述**：制定開發規範、建置開發環境、準備開發工具

**執行者**：SD-Architect (Marcus) + DevOps + Dev

> **🔀 多語言 CI/CD 策略（Web + Mobile + Desktop）**：
> 若專案涉及多個技術棧（如 Java + JavaScript + Kotlin + Swift），CI/CD Pipeline 需統一規範：
>
> | 技術棧 | 語言 | 建議 CI 工具 | 測試框架 | 建置產物 |
> |--------|------|-------------|---------|---------|
> | Next.js 前端 | TypeScript | GitHub Actions | Jest + Playwright | Docker Image |
> | Spring Boot 後端 | Java | GitHub Actions | JUnit 5 + Testcontainers | Docker Image |
> | Android App | Kotlin | GitHub Actions | JUnit + Espresso | APK/AAB |
> | macOS App | Swift | GitHub Actions | XCTest | .app/.dmg |
>
> **多語言 Pipeline 建議策略**：
> - 使用 Monorepo 結構，各模組目錄下有獨立 CI 配置
> - 觸發條件：依據變更路徑（`on: paths`）只觸發受影響模組的 Pipeline
> - 統一 Secret 管理：所有語言共用 GitHub Secrets / Vault
> - 統一 Code Quality Gate：覆蓋率 ≥ 80%（各語言獨立計算）
>
> 參考：SOP.md Stage 8 「多語言 CI/CD 統一規範」

**具體作業**：
1. 制定 Coding Standards（各語言獨立規範）
2. 制定 Git Workflow（Branch Strategy）
3. 制定 Code Review Guidelines
4. 制定 Testing Standards（各技術棧測試框架）
5. 建立專案架構骨架
6. 設定 CI/CD Pipeline（含多語言建置策略）
7. 建立測試環境
8. 整合專案管理工具（Jira/Linear）

**人機協作確認點** 🔴：
- **確認點 8.1**：開發規範確認（20 分鐘）
  - 審查開發規範文檔
  - 確認團隊理解並同意
  - 補充團隊特定要求

**檢查點**：
- [ ] 開發規範文檔完成
- [ ] Git Workflow 定義完成
- [ ] 專案骨架建立完成
- [ ] CI/CD Pipeline 設定完成
- [ ] 測試環境建立完成
- [ ] 專案管理工具整合完成
- [ ] 開發環境 Setup 指南完成

**品質標準**：
- 開發規範清晰易懂
- CI/CD Pipeline 可自動執行
- 環境建置流程文檔化
- 工具整合順暢

**預估時間**：1-2 天

**產出文件**：
- Coding Standards
- Git Workflow Guide
- Code Review Guidelines
- Testing Standards
- Developer Setup Guide
- CI/CD Configuration
- Team Collaboration Guidelines

---

## 步驟 9：文檔一致性檢查
**描述**：確保所有文檔一致且追蹤鏈完整

**執行者**：SA (Amanda) + Technical-Writer

**具體作業**：
1. 執行 **document-consistency-check** workflow
2. 驗證追蹤鏈：PRD → FRD → SRD → API → User Stories
3. 檢查文檔間引用正確性
4. 檢查 ID 編號一致性
5. 檢查術語使用一致性
6. 驗證所有連結有效

**檢查點**：
- [ ] 追蹤鏈完整無斷點
- [ ] 文檔間引用正確
- [ ] ID 編號格式一致
- [ ] 術語定義一致
- [ ] 所有內部連結有效

**品質標準**：
- 100% 追蹤覆蓋率
- 無孤立需求
- 術語表完整

**預估時間**：1-2 小時

**產出文件**：
- 一致性檢查報告
- 問題清單（如有）

---

## 步驟 10：團隊 Kickoff 與交接
**描述**：召開專案啟動會議，移交開發團隊

**執行者**：PM/PO (Victoria) + SA (Amanda) + SD (Marcus)

**具體作業**：
1. 準備 Kickoff 簡報
2. 召開全員 Kickoff Meeting
3. 說明專案願景和目標
4. 介紹技術架構和決策
5. 說明 Sprint 計畫
6. 說明開發流程和規範
7. Q&A 環節
8. 分配第一個 Sprint 任務

**人機協作確認點** 🔴：
- **確認點 10.1**：交接確認（會議後）
  - 團隊理解專案目標
  - 團隊理解技術架構
  - 團隊理解開發流程
  - 第一個 Sprint 任務已分配

**檢查點**：
- [ ] Kickoff 會議完成
- [ ] 所有文檔已分享
- [ ] 團隊成員理解專案
- [ ] 開發環境已就緒
- [ ] 第一個 Sprint 已啟動

**品質標準**：
- 團隊對專案有共同理解
- 所有疑問已解答
- 開發可立即開始

**預估時間**：1 小時（會議）+ 準備時間

**產出文件**：
- Kickoff 簡報
- Meeting Minutes
- Q&A 記錄

---

## 步驟 11：實施與測試（Sprint 執行）
**描述**：執行 Sprint 內的程式碼開發、編譯測試、整合測試與 Code Review

**執行者**：Dev (David) + QA (Quincy)

**觸發 Workflow**：`sprint-execution`（[sprint-execution.md](../core/sprint-execution.md)）

**建議 Skill**：`/dev-review`、`/qa-testing`、`/testing-strategy`、`/code-review`

**具體作業**：
1. Sprint 啟動確認（User Stories + AC + 技術方案）
2. 開發-編譯-測試循環（🔴 強制：每支程式開發完成後立即編譯→測試）
3. 整合測試（API + 前後端 + 跨平台）
4. Code Review 與 PR 合併
5. Sprint 驗收（逐項執行 AC）

**人機協作確認點** 🔴：
- **確認點 11.1**：Sprint 目標與開發順序確認
- **確認點 11.2**：Code Review 通過後合併
- **確認點 11.3**：Sprint 驗收結果確認

**檢查點**：
- [ ] 所有 User Stories 的 AC 通過
- [ ] 單元測試覆蓋率 ≥ 80%
- [ ] Code Review 通過
- [ ] 無 Critical/High 的 Bug
- [ ] Sprint 回顧完成

**產出文件**：
- Sprint 測試報告 → `docs/03_testing/`
- Code Review 紀錄 → `docs/06_quality/`
- Sprint 進度日誌 → `docs/05_development/`

---

## 步驟 12：部署準備與上線
**描述**：環境建置、安全驗證、正式部署與發布

**執行者**：DevOps (devops-engineer) + QA (Quincy) + PM/PO (Victoria)

**建議 Skill**：`/devops-github-actions`、`/devops-docker`、`/security-audit`、`/release-management`

**具體作業**：
1. 部署環境建置（Docker + CI/CD Pipeline）
2. 上線前驗證（安全掃描 + 效能測試 + 回滾方案）
3. 正式部署（資料庫遷移 + 應用部署 + 煙霧測試）
4. 發布與文檔（Release Notes + 通知利害關係人）

**人機協作確認點** 🔴：
- **確認點 12.1**：上線前最終確認
- **確認點 12.2**：發布成功確認

**檢查點**：
- [ ] Docker 容器化完成
- [ ] CI/CD Pipeline 正常運作
- [ ] 安全掃描通過
- [ ] Staging 環境驗證通過
- [ ] Production 部署成功
- [ ] 監控告警設定完成
- [ ] Release Notes 發布

**產出文件**：
- 部署配置 → `docs/08_deployment/`
- Release Notes → `docs/08_deployment/`
- 監控設定 → `docs/08_deployment/`

---

# 輸出與交付

## 主要交付物

### 需求文檔
- **PRD** (Product Requirements Document)
- **FRD** (Functional Requirements Document)
- **需求追蹤矩陣** (Requirements Traceability Matrix)

### 架構文檔
- **SRD** (System Requirements Document)
- **系統架構圖** (Architecture Diagrams - C4 Model)
- **資料庫 Schema** (Database Schema)
- **API 規格文檔** (API Specifications)
- **Architecture Decision Records** (ADR)

### 開發文檔
- **User Stories** (完整清單)
- **Acceptance Criteria**
- **Sprint Roadmap**
- **Sprint Backlog**
- **Coding Standards**
- **Developer Setup Guide**

### 測試文檔
- **Acceptance Test Scenarios**
- **Testing Strategy**

## 交付標準

**完整性**：
- 所有必要文檔齊全
- 追蹤鏈完整（PRD→FRD→SRD→API→Stories→ATs）
- 無孤立需求或未定義功能

**準確性**：
- 文檔內容與利害關係人期望一致
- 技術設計符合需求
- User Stories 正確反映功能需求

**可追蹤性**：
- 每個需求有唯一 ID
- 文檔間引用清晰
- 變更歷史可追蹤

**可執行性**：
- User Stories 明確可執行
- Acceptance Criteria 明確可測試
- Sprint 計畫可行

**人機協作品質**：
- 所有確認點已完成
- 所有決策有人類確認
- 無自主臆測
- 協作記錄完整

## 驗收條件
- [ ] 所有主要交付物已完成
- [ ] 所有文檔通過品質檢查
- [ ] 追蹤鏈一致性檢查通過
- [ ] 所有人機協作確認點已完成
- [ ] 團隊已理解並準備好開始開發
- [ ] 開發環境和工具已就緒
- [ ] 第一個 Sprint 已啟動

## 後續流程交接
- **交接給**：開發團隊（Dev + QA + DevOps）
- **交接內容**：
  - 完整的需求和設計文檔
  - Sprint Backlog
  - 開發規範和指南
  - 開發環境存取權限
- **交接標準**：
  - 開發團隊確認理解所有文檔
  - 開發環境可正常運作
  - 第一個 Story 可立即開始開發

---

# 協作與整合

## 前置 Workflows
無（此為專案啟動 workflow）

## 後續 Workflows
- **Sprint Execution**：執行 Sprint 開發
- **requirements-change-management**：處理需求變更（如有）
- **document-consistency-check**：定期檢查文檔一致性

## 相關 Workflows
- **requirements-extraction**：需求提取子流程
- **requirements-validation-and-documentation**：需求驗證子流程
- **tech-stack-selection**：技術選型子流程
- **user-story-and-design**：User Story 撰寫子流程
- **api-specification-generation**：API 規格生成子流程

---

# 品質控制

## 人機協作原則
- **零臆測原則**：AI 不得自行假設，所有不確定點必須與人類確認
- **確認點強制執行**：所有 🔴 確認點不可跳過
- **30 分鐘超時**：確認點如 30 分鐘無回應，自動暫停並記錄
- **協作記錄**：所有確認和決策必須記錄在 Collaboration Log

## 品質門檻
- **需求階段**：需求完整性 ≥ 95%，需求明確性 100%
- **設計階段**：架構文檔完整性 100%，ADR 完整記錄
- **規劃階段**：User Story 符合 INVEST，AC 100% 可測試

## 風險管理
- **技術風險**：每個技術選擇有風險評估和緩解措施
- **時程風險**：Sprint 規劃留有緩衝（20%）
- **需求風險**：需求變更管理流程已建立

---

# 監控與度量

## 進度追蹤
- 每個步驟完成時間
- 人機協作確認點完成率
- 文檔產出及時性

## 品質度量
- 需求明確度分數
- 文檔一致性分數
- User Story 品質分數（INVEST 符合度）

## 效率度量
- 總執行時間 vs 預估時間
- 重工次數（需求變更導致）
- 確認點平均回應時間

---

# 常見問題與處理

## 場景 1：需求不明確或頻繁變更
**處理方式**：
- 暫停流程，回到需求提取階段
- 執行更深入的利害關係人訪談
- 使用原型驗證需求
- 記錄需求變更並更新所有相關文檔

## 場景 2：技術選型爭議
**處理方式**：
- 召開技術評審會議
- 進行技術 Spike 驗證可行性
- 記錄 ADR 說明決策理由
- 必要時進行 POC（Proof of Concept）

## 場景 3：時程壓力導致想跳過步驟
**處理方式**：
- 不可跳過，但可精簡
- 識別最小必要交付物
- 調整 MVP 範圍而非跳過流程
- 記錄技術債和後續改進計畫

## 場景 4：團隊技能與技術選擇不匹配
**處理方式**：
- 評估學習曲線和時間成本
- 考慮調整技術選型或引入外部資源
- 制定培訓計畫
- 增加 Sprint 0 的時間進行技術學習

---

# 最佳實踐

## Do's ✅
- **充分溝通**：每個確認點充分討論，不要急於通過
- **文檔優先**：先完善文檔，再開始開發
- **MVP 思維**：首版追求可用，非完美
- **持續驗證**：每個階段完成後回顧和驗證
- **知識分享**：定期同步進度，確保團隊理解一致

## Don'ts ❌
- **不跳過確認點**：即使時間緊迫也不可跳過
- **不自行假設**：所有不確定點必須確認
- **不過度設計**：避免 over-engineering
- **不忽視非功能需求**：效能、安全同樣重要
- **不拖延文檔**：文檔與開發同步進行

---

# 附錄

## 參考文檔
- [Greenfield SOP](../../scenarios/greenfield/SOP.md)
- [Requirements Extraction Workflow](../core/requirements-extraction.md)
- [Requirements Validation Workflow](../core/validation-documentation.md)
- [User Story and Design Workflow](../core/user-story-design.md)
- [API Specification Workflow](../core/api-specification.md)
- [Consistency Check Workflow](../core/consistency-check.md)
- [Interaction Analysis Workflow](../core/interaction-analysis.md)
- [Sprint Execution Workflow](../core/sprint-execution.md)

## 相關 Agents

### Core Agents
- [SA - System Analyst](../../agent/core/04.sa-analyst-zh.yaml)
- [BA - Business Analyst](../../agent/core/02.ba-business-analyst-zh.yaml)
- [PM/PO - Product Manager](../../agent/core/03.pm-po-agent-zh.yaml)
- [SD - System Designer](../../agent/core/05.sd-architect-zh.yaml)
- [QA - QA Engineer](../../agent/core/07.qa-tester-zh.yaml)
- [Dev - Developer](../../agent/core/06.dev-developer-zh.yaml)

### Specialized Agents（按需載入）
- [DevOps Engineer](../../agent/specialized/devops-engineer-zh.yaml) - 階段 8 CI/CD 與部署準備

## 模板與範例
- [PRD Template](../../docs_template/core/prd/PRD_Universal_Template.md)
- [FRD Template](../../docs_template/core/frd/FRD_Universal_Template.md)
- [SRD Template](../../docs_template/core/srd/SRD_Module_Template.md)
- [API Specification Template](../../docs_template/core/api/API_Specification_Template.md)

---

**版本**：v0.01
**最後更新**：2026-04-17
**維護者**：AISDLC-SDD Framework Team
