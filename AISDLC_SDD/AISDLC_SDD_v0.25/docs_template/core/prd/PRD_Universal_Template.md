# PRD - [專案名稱]
# Product Requirements Document - Universal Template

**文檔類型**: PRD (Product Requirements Document)
**模板版本**: v0.01 Universal
**適用情境**: 所有專案類型 (透過情境標籤選擇)
**適用平台**: Web App / Mobile App / 全端應用 (v0.01 新增)

---

## 📋 文檔元數據

| 項目 | 內容 |
|-----|------|
| **專案名稱** | [Project Name] |
| **專案類型** | 🔽 **請選擇**: Greenfield / Brownfield / Sprint / Integration |
| **目標平台** | 🔽 **請選擇**: Web App / Mobile App (iOS/Android) / 全端應用 |
| **目標日期** | YYYY-MM-DD |
| **文檔狀態** | Draft / Under Review / Approved / In Execution / Completed |
| **Product Owner** | [姓名] |
| **Stakeholders** | [列出主要利害關係人] |
| **撰寫日期** | YYYY-MM-DD |
| **最後更新** | YYYY-MM-DD |
| **AISDLC 版本** | v0.01 |

### 目標平台專屬欄位（v0.01 新增）

<details>
<summary><b>[For Web App Only]</b> Web 平台資訊</summary>

| 項目 | 內容 |
|-----|------|
| **渲染模式** | SSR / SSG / ISR / SPA / MPA |
| **SEO 需求** | 必要 / 選擇性 / 不需要 |
| **目標瀏覽器** | Chrome, Firefox, Safari, Edge (最近 2 版本) |
| **響應式範圍** | Desktop / Tablet / Mobile |
| **效能目標 (Core Web Vitals)** | LCP < 2.5s, FID < 100ms, CLS < 0.1 |
| **無障礙等級** | WCAG 2.1 AA / AAA |

</details>

<details>
<summary><b>[For Mobile App Only]</b> Mobile 平台資訊</summary>

| 項目 | 內容 |
|-----|------|
| **支援平台** | iOS / Android / Cross-platform |
| **最低版本** | iOS 14+ / Android 9+ (API 28+) |
| **開發框架** | Native / React Native / Flutter |
| **離線功能** | 必要 / 選擇性 / 不需要 |
| **推播需求** | 本地 / 遠端 / 不需要 |

</details>

<details>
<summary><b>[For 全端應用 Only]</b> 全端平台資訊</summary>

| 項目 | 內容 |
|-----|------|
| **Web 平台** | [填寫 Web 平台資訊] |
| **Mobile 平台** | [填寫 Mobile 平台資訊] |
| **資料同步策略** | 即時同步 / 定期同步 / 離線優先 |
| **共用 API** | 是 / 否（分開開發）|

</details>

### 專案類型專屬欄位

<details>
<summary><b>[For Greenfield Only]</b> 全新專案資訊</summary>

| 項目 | 內容 |
|-----|------|
| **專案代號** | [Project Code] |
| **技術選型狀態** | 待決定 / 已確定 |
| **預計團隊規模** | [人數] |

</details>

<details>
<summary><b>[For Brownfield Only]</b> 既有系統資訊</summary>

| 項目 | 內容 |
|-----|------|
| **既有系統名稱** | [Existing System Name] |
| **現行版本** | vX.Y.Z |
| **目標版本** | vX.Y.Z |
| **系統文檔位置** | [連結或路徑] |
| **技術棧** | [列出現有技術] |

</details>

<details>
<summary><b>[For Sprint Only]</b> Sprint 資訊</summary>

| 項目 | 內容 |
|-----|------|
| **Sprint 編號** | Sprint XX |
| **時間範圍** | YYYY-MM-DD 至 YYYY-MM-DD |
| **上個 Sprint 回顧** | [連結] |
| **Sprint 目標** | [本 Sprint 的主要目標] |

</details>

<details>
<summary><b>[For Integration Only]</b> 整合專案資訊</summary>

| 項目 | 內容 |
|-----|------|
| **目標第三方系統** | [Third-Party System Name] |
| **整合方式** | API / Webhook / Database / File / Message Queue |
| **第三方文檔** | [連結] |
| **資料流向** | 雙向 / 單向(→我方) / 單向(我方→) |

</details>

---

## 🔖 情境使用指引

**本模板支援四種情境，請根據專案類型閱讀對應章節**:

| 情境 | 必讀章節 | 必須附錄 | 可選章節 | 可跳過章節 |
|------|---------|---------|---------|-----------|
| **Greenfield** | 1-8 | 9(技術選型) | 10(風險) | 11(既有系統分析), 12(整合規格) |
| **Brownfield** | 1-8 | - | 11(既有系統分析), 10(風險) | 9(技術選型), 12(整合規格) |
| **Sprint** | 1-3, 5-7 | - | 8(里程碑簡化版) | 4(詳細市場分析), 9-12 |
| **Integration** | 1-3, 5-7, 12 | - | 10(風險), 11(既有系統) | 4(詳細市場分析), 9(技術選型) |

**📌 Greenfield 專案特別說明**:
- **必須附錄「9. 技術選型與架構」**: 在 Stage 3 完成技術選型後，必須將技術選型報告附加到 PRD 第 9 章，作為正式文檔的一部分。這確保了技術決策的可追溯性和團隊共識。

---

## 🎯 1. 專案願景與目標 (Vision & Objectives)

### 1.1 專案願景
*用 2-3 句話描述專案的長期願景和終極目標*

[描述專案要創造的長期價值和未來狀態]

### 1.2 業務目標
*描述為什麼要做這個專案*

**解決的問題**:
- **現況痛點**: [描述當前存在的問題]
- **目標用戶**: [誰會受益於這個系統]
- **市場機會**: [市場趨勢、競爭分析] *[For Greenfield - 詳細] / [For Others - 簡要]*

**預期成果**:
- **短期目標（3-6 個月）**: [上線後的立即目標]
- **中期目標（6-12 個月）**: [產品成熟期目標] *[Optional for Sprint]*
- **長期目標（1-2 年）**: [規模化目標] *[Optional for Sprint/Brownfield]*

### 1.3 成功指標 (Success Metrics)
*如何衡量專案成功*

| 指標類型 | 具體指標 | 目標值 | 衡量時間點 |
|---------|---------|--------|-----------|
| **業務指標** | [用戶數、營收、轉換率] | [具體數字] | 上線後 X 個月 |
| **用戶指標** | [活躍用戶、留存率、NPS] | [具體數字] | 上線後 X 個月 |
| **技術指標** | [可用性、回應時間、錯誤率] | [具體數字] | 持續監控 |
| **財務指標** | [ROI、成本節省] | [具體數字] | 上線後 X 個月 |

**🔴 人機協作確認點**:
- [ ] Stakeholders 確認願景與目標一致
- [ ] 成功指標可衡量且合理
- [ ] 短中長期目標有清晰路徑

---

## 👥 2. 目標用戶與使用場景 (Target Users & Use Cases)

### 2.1 用戶角色定義

| 用戶角色 | 描述 | 主要需求 | 使用頻率 | 技術熟練度 |
|---------|------|---------|---------|-----------|
| **[角色 1]** | [角色描述] | [核心需求] | 每日/每週/每月 | 高/中/低 |
| **[角色 2]** | [角色描述] | [核心需求] | 每日/每週/每月 | 高/中/低 |

### 2.2 核心使用場景

#### 場景 1: [場景名稱]
**觸發條件**: [什麼情況下會使用]
**用戶目標**: [用戶想達成什麼]
**關鍵步驟**:
1. [步驟 1]
2. [步驟 2]
3. [步驟 3]

**成功標準**: [場景完成的標誌]

**🔴 人機協作確認點**:
- [ ] 用戶角色定義準確
- [ ] 使用場景符合實際需求
- [ ] 使用流程合理可行

---

## 🏗️ 3. 功能範圍與 MVP 定義 (Scope & MVP Definition)

**📌 重要**: 對於 Greenfield 專案，本章節應在撰寫詳細功能需求（第 5 章）之前明確定義 MVP 範圍，避免需求蔓延。

### 3.1 MVP / 本次範圍
*[Greenfield: **MVP 範圍定義**] / [Brownfield: 本次修改範圍] / [Sprint: Sprint 功能] / [Integration: 整合範圍]*

**🎯 [For Greenfield] MVP 定義原則**:
- **最小可行產品 (MVP)**: 能夠驗證核心價值主張的最小功能集合
- **必須包含**: 解決核心痛點的關鍵功能（P0 優先級）
- **時程目標**: 建議 8-12 週內可完成的範圍
- **驗證目標**: 能夠獲得早期用戶反饋並驗證市場需求

**MVP 功能清單**:

| 功能編號 | 功能名稱 | 優先級 | 預估複雜度 | FRD 連結 | 狀態 |
|---------|---------|--------|-----------|----------|------|
| F-001 | [核心功能 1] | P0 | 高/中/低 | [FRD](../../scenario_specific/xxx/FRD_Module.md) | Planning |
| F-002 | [核心功能 2] | P0 | 高/中/低 | [FRD](../../scenario_specific/xxx/FRD_Module.md) | Planning |

### 3.2 範圍外 (Out of Scope)
*明確列出本次不做的項目*

- ❌ [範圍外項目 1]
- ❌ [範圍外項目 2]

### 3.3 未來規劃 (Post-MVP / Future Enhancements)
*[Optional for Sprint]*

| 功能編號 | 功能名稱 | 規劃階段 | 預計時程 |
|---------|---------|---------|---------|
| F-101 | [進階功能 1] | Phase 2 | Q2 2025 |
| F-102 | [進階功能 2] | Phase 3 | Q3 2025 |

**🔴 人機協作確認點**:
- [ ] MVP/範圍定義清晰
- [ ] 優先級合理
- [ ] 範圍外項目已確認

---

## 📊 4. 商業需求分析 (Business Requirements)

### 4.1 投資報酬分析
*[For Greenfield - 詳細] / [For Sprint - 可省略]*

**成本估算**:
| 成本項目 | 預估金額 | 說明 |
|---------|---------|------|
| 開發成本 | $XXX,XXX | [人力、時間] |
| 基礎設施成本 | $XX,XXX | [雲端、授權] |
| 營運成本 (年) | $XX,XXX | [維護、支援] |
| **總計** | **$XXX,XXX** | |

**預期收益**:
- [收益項目 1]: $XXX,XXX
- [收益項目 2]: $XXX,XXX
- **ROI**: XX% (預計 XX 個月回本)

### 4.2 競爭分析
*[For Greenfield - 必填] / [For Others - Optional]*

| 競爭對手/替代方案 | 優勢 | 劣勢 | 我們的差異化 |
|-----------------|------|------|-------------|
| [競爭者 A] | [優勢] | [劣勢] | [我們如何勝出] |
| [現有流程] | [優勢] | [劣勢] | [自動化價值] |

---

## 💡 5. 功能性需求 (Functional Requirements)

### 5.1 核心功能詳述

> 📋 **ID 命名規範**: 使用 [AISDLC_ID_Naming_Convention.md](../../../guides/system/naming/AISDLC_ID_Naming_Convention.md)
> - **Feature ID**: F-XXX (功能需求)
> - **Non-Functional Req ID**: NFR-XXX (非功能需求)
> - 範例：F-001, F-002, NFR-001

#### F-001: [功能名稱]

**基本資訊**:
- **Feature ID**: F-001
- **優先級**: P0 (Must-have) / P1 (Should-have) / P2 (Nice-to-have)
- **Kano 分類**: 必備型 / 期望型 / 魅力型
- **RICE 分數**: [計算結果] (參考: [MVP_Definition_Template.md](../prd/MVP_Definition_Template.md))
- **MVP 階段**: Phase 1 (MVP) / Phase 2 / Phase 3 / Out of Scope

**功能描述**:
[詳細描述這個功能要做什麼，解決什麼問題，為使用者創造什麼價值]

**業務規則**:
> 注意：業務規則將在 FRD 中使用 BR-XXX ID 格式詳細定義
1. [規則 1 - 將對應 BR-001]
2. [規則 2 - 將對應 BR-002]

**成功指標**:
- [如何衡量此功能是否成功？]
- [預期的使用率/轉換率/滿意度]

**相關文檔**:
- **對應 FRD**: [連結到 FRD_Module.md](../../scenario_specific/xxx/FRD_Module.md) (詳細業務規則 BR-XXX)
- **對應 Epic**: [將產生 EPIC-XXX]
- **對應 User Story**: [將產生 US-XXX]
- **對應 API**: [將產生 API-XXX]

**追蹤鏈範例**:
```
F-001 → BR-001~003 (FRD) → EPIC-001 → US-001~005 → AC-XXX-Y → API-101~103
```

---

## 🔧 6. 非功能性需求 (Non-Functional Requirements)

> 📋 **ID 命名規範**: 使用 NFR-XXX 格式
> - NFR-001: 效能需求
> - NFR-002: 安全需求
> - NFR-003: 擴展性需求
> - NFR-004: 維護性需求

### NFR-001: 效能需求

| 指標 | 目標值 | 說明 | 優先級 |
|------|--------|------|--------|
| **回應時間** | < 200ms (p95) | API 回應時間 | P0 |
| **吞吐量** | > 1000 req/s | 尖峰流量處理 | P1 |
| **可用性** | 99.9% | 每月停機時間 < 43 分鐘 | P0 |
| **頁面載入** | < 2 秒 (First Contentful Paint) | 使用者體驗 | P0 |

### NFR-002: 安全需求

- **NFR-002-1 認證**: [OAuth 2.0 / JWT / Session-based]
- **NFR-002-2 授權**: [RBAC / ABAC]
- **NFR-002-3 資料加密**: [傳輸 TLS 1.3 / 儲存 AES-256]
- **NFR-002-4 合規要求**: [GDPR / HIPAA / 無]
- **NFR-002-5 資料備份**: [每日備份 / 備份保留期限]

### NFR-003: 擴展性需求

- **NFR-003-1 用戶規模**: [預期用戶數，如 10K DAU → 100K DAU]
- **NFR-003-2 資料規模**: [預期資料量，如 1M records → 100M records]
- **NFR-003-3 水平擴展**: [支援/不支援，如 Auto-scaling]
- **NFR-003-4 資料庫擴展**: [Read Replica / Sharding / 無]

### NFR-004: 維護性需求

- **NFR-004-1 可監控性**: [日誌 (ELK/CloudWatch)、指標 (Prometheus)、追蹤 (Jaeger)]
- **NFR-004-2 可測試性**: [自動化測試覆蓋率 > 80%]
- **NFR-004-3 可部署性**: [CI/CD 自動化部署，Zero-downtime deployment]
- **NFR-004-4 文檔完整性**: [API 文檔、架構文檔、操作手冊]

**追蹤鏈**:
```
NFR-001 (效能需求) → TC-NFR-001-1 (效能測試案例)
NFR-002 (安全需求) → TC-NFR-002-1 (安全測試案例)
```

**🔴 人機協作確認點**:
- [ ] 所有 NFR 已定義 ID (NFR-XXX)
- [ ] NFR 符合業務需求與技術可行性
- [ ] 效能目標可達成且可測量
- [ ] 安全要求符合規範與法規

---

## 🎨 7. 使用者體驗需求 (UX Requirements)

### 7.1 設計原則

- **易用性**: [描述目標用戶的易用性要求]
- **一致性**: [UI/UX 一致性標準]
- **回饋機制**: [操作回饋、錯誤提示]

### 7.2 介面規範
*[For Greenfield - 詳細] / [For Brownfield - 需配合既有風格]*

- **設計系統**: [Material Design / Custom / 既有系統延續]
- **響應式設計**: [Desktop / Tablet / Mobile]
- **無障礙需求**: [WCAG 2.1 Level AA / 無]

### 7.3 原型/線框圖
*附上或連結到設計稿*

- [Figma/Sketch 連結]
- [關鍵畫面截圖]

---

## 📅 8. 時程與里程碑 (Timeline & Milestones)

### 8.1 專案里程碑

| 階段 | 里程碑 | 交付物 | 目標日期 | 負責人 |
|------|--------|--------|---------|--------|
| **Phase 1** | 需求確認 | PRD/FRD 完成 | YYYY-MM-DD | [姓名] |
| **Phase 2** | 設計完成 | SRD/API 規格完成 | YYYY-MM-DD | [姓名] |
| **Phase 3** | 開發完成 | 功能實作完成 | YYYY-MM-DD | [姓名] |
| **Phase 4** | 測試完成 | 測試報告 | YYYY-MM-DD | [姓名] |
| **Phase 5** | 上線 | 生產環境部署 | YYYY-MM-DD | [姓名] |

### 8.2 Sprint 規劃
*[For Sprint Only]*

**本 Sprint 時間表**:
- **Sprint Planning**: YYYY-MM-DD
- **Daily Standup**: 每日 10:00
- **Sprint Review**: YYYY-MM-DD
- **Sprint Retrospective**: YYYY-MM-DD

**🔴 人機協作確認點**:
- [ ] 時程合理可行
- [ ] 里程碑定義清晰
- [ ] 負責人已確認

---

## 🔧 9. 技術選型與架構 (Technical Stack & Architecture)
*[For Greenfield Only] / [Optional for Others]*

<details>
<summary><b>展開技術選型詳情</b> (非 Greenfield 可跳過)</summary>

### 9.1 技術棧建議

**前端**:
- 框架: [React / Vue / Angular / 其他]
- 狀態管理: [Redux / Vuex / 其他]
- UI 庫: [Material-UI / Ant Design / Custom]

**後端**:
- 語言: [Node.js / Python / Java / Go / 其他]
- 框架: [Express / FastAPI / Spring Boot / Gin / 其他]
- 資料庫: [PostgreSQL / MySQL / MongoDB / 其他]
- 快取: [Redis / Memcached / 無]

**基礎設施**:
- 雲端平台: [AWS / GCP / Azure / On-Premise]
- 容器化: [Docker / Kubernetes / 無]
- CI/CD: [GitHub Actions / GitLab CI / Jenkins / 其他]

**🔴 人機協作確認點**:
- [ ] 技術選型與團隊技能匹配
- [ ] 符合公司技術標準
- [ ] 成本在預算範圍內

</details>

---

## ⚠️ 10. 風險與依賴 (Risks & Dependencies)

### 10.1 風險評估

| 風險 | 機率 | 影響 | 緩解措施 | 負責人 |
|------|------|------|---------|--------|
| [風險 1] | 高/中/低 | 高/中/低 | [緩解方案] | [姓名] |
| [風險 2] | 高/中/低 | 高/中/低 | [緩解方案] | [姓名] |

### 10.2 依賴項目

**技術依賴**:
- [依賴的第三方服務/API]
- [依賴的內部系統]

**團隊依賴**:
- [需要其他團隊支援的項目]

**🔴 人機協作確認點**:
- [ ] 所有風險已識別
- [ ] 緩解措施可行
- [ ] 依賴項目已確認

---

## 🔍 11. 既有系統分析 (Existing System Analysis)
*[For Brownfield Only] / [Optional for Integration]*

<details>
<summary><b>展開既有系統分析</b> (僅 Brownfield/Integration 需填)</summary>

### 11.1 現況分析

**系統概況**:
- **架構**: [現有架構描述]
- **技術債**: [已知的技術債務]
- **痛點**: [現有系統的問題]

### 11.2 影響分析

**影響範圍**:
| 模組/功能 | 影響程度 | 需要修改 | 風險 |
|----------|---------|---------|------|
| [模組 A] | 高/中/低 | 是/否 | [風險描述] |
| [模組 B] | 高/中/低 | 是/否 | [風險描述] |

**向後相容性**:
- [ ] 需要保持向後相容
- [ ] 允許 Breaking Changes (需溝通)

**🔴 人機協作確認點**:
- [ ] 影響範圍已完整評估
- [ ] 相容性策略已確認

</details>

---

## 🔗 12. 整合規格 (Integration Specifications)
*[For Integration Only]*

<details>
<summary><b>展開整合規格詳情</b> (僅 Integration 專案需填)</summary>

### 12.1 第三方系統資訊

**系統名稱**: [Third-Party System]
**API 文檔**: [連結]
**認證方式**: [OAuth / API Key / Basic Auth / 其他]
**API 版本**: [v1.0 / v2.0]

### 12.2 資料同步策略

**同步方式**:
- [ ] 即時同步 (Webhook)
- [ ] 批次同步 (排程)
- [ ] 事件驅動 (Message Queue)

**同步頻率**: [每 X 分鐘 / 每小時 / 每日]

### 12.3 錯誤處理

**重試機制**: [指數退避 / 固定間隔 / 無]
**失敗通知**: [Email / Slack / 日誌]
**資料補償**: [手動補償 / 自動補償]

**🔴 人機協作確認點**:
- [ ] 第三方 API 存取已確認
- [ ] 同步策略符合需求
- [ ] 錯誤處理機制完善

</details>

---

## 📎 13. 附錄 (Appendix)

### 13.1 詞彙表 (Glossary)

| 術語 | 定義 |
|------|------|
| [術語 1] | [定義] |
| [術語 2] | [定義] |

### 13.2 參考資料

- [市場研究報告]
- [競品分析文件]
- [技術調研文件]

### 13.3 變更記錄

| 日期 | 版本 | 變更內容 | 變更人 |
|------|------|---------|--------|
| YYYY-MM-DD | v1.0 | 初版建立 | [姓名] |
| YYYY-MM-DD | v1.1 | [變更描述] | [姓名] |

---

## 🔗 14. 文檔追蹤鏈 (Traceability)

### 上游文檔
- **需求來源**: [商業需求文件 / 用戶反饋 / 市場分析]

### 下游文檔
- **FRD 文檔**: [連結到各功能模組的 FRD]
- **SRD 文檔**: [連結到系統設計文檔]
- **API 規格**: [連結到 API 規格文檔]
- **測試計畫**: [連結到測試計畫]

---

## ✅ 文檔完成檢查清單

### PRD 品質檢查
- [ ] 所有必填欄位已完成
- [ ] 根據專案類型填寫對應的情境專屬章節
- [ ] 成功指標明確可衡量
- [ ] 範圍定義清晰 (In-Scope / Out-of-Scope)
- [ ] 所有 🔴 確認點已通過
- [ ] 時程與資源合理
- [ ] 風險已識別並有緩解措施
- [ ] 與 Stakeholders 完成評審

### AISDLC 流程檢查
- [ ] 已由 PM/PO Agent (Victoria) 主導撰寫
- [ ] 已由 BA Agent (Beatrice) 協助驗證
- [ ] 所有人機協作確認點已完成
- [ ] 文檔追蹤鏈完整
- [ ] 版本控制正確

---

**文檔所有者**: [Product Owner 姓名]
**最後審查日期**: YYYY-MM-DD
**下一次審查日期**: YYYY-MM-DD

---

## 📖 模板使用說明

### 如何使用本統一模板

1. **選擇專案類型**: 在文檔元數據中選擇 Greenfield / Brownfield / Sprint / Integration
2. **展開對應欄位**: 展開專案類型專屬的 `<details>` 區塊
3. **參考情境指引表**: 根據專案類型，閱讀必讀/可選/可跳過章節
4. **填寫內容**: 依照指引填寫對應章節
5. **完成檢查**: 使用文檔完成檢查清單驗證

### 各情境重點差異

**Greenfield (全新專案)**:
- 重點: 技術選型(第9章)、商業分析(第4章)、完整時程規劃(第8章)
- 需完整填寫所有章節

**Brownfield (既有系統修改)**:
- 重點: 既有系統分析(第11章)、影響範圍評估、向後相容性
- 可跳過技術選型，簡化商業分析

**Sprint (敏捷衝刺)**:
- 重點: Sprint 範圍(第3章)、Sprint 時程(第8.2)
- 簡化商業分析、跳過技術選型和長期規劃

**Integration (第三方整合)**:
- 重點: 整合規格(第12章)、資料流設計、錯誤處理
- 跳過技術選型、簡化商業分析

---

**模板版本: v0.01 Universal
**建立日期**: 2025-10-23
**維護者**: AISDLC Framework Team
