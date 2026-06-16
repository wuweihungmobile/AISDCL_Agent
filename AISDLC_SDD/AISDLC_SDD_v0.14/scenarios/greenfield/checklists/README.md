# Greenfield Checklists 目錄說明
# Greenfield Checklists Directory README

**目錄版本**: v1.0
**建立日期**: 2025-11-12
**適用情境**: Greenfield - 新專案開發
**AISDLC 版本: v0.01

---

## 📋 目錄用途

本目錄包含 **Greenfield 情境專用的檢查清單與範本**，幫助團隊在開發過程中系統性地確認所有必要項目。

### 為什麼需要 Checklists？

1. **避免遺漏**: 系統性確認，減少遺漏重要需求
2. **標準化**: 建立團隊共同的檢查標準
3. **提升效率**: 快速識別缺失項目，減少返工
4. **品質保證**: 確保產出文件的完整性和品質

---

## 📂 目錄結構

```
checklists/
├── README.md                              # 本文檔
├── Standard_Confirmation_Questions.md     # 標準確認問題清單
├── Cost_Estimation_Template.md           # 成本試算表範本
└── Completeness_Checklist.md             # 需求完整性檢查清單
```

---

## 📄 檢查清單總覽

### 1. Standard_Confirmation_Questions.md
**標準確認問題清單**

| 屬性 | 內容 |
|-----|------|
| **檔案名稱** | [Standard_Confirmation_Questions.md](Standard_Confirmation_Questions.md) |
| **文檔類型** | 問題清單 |
| **使用階段** | SOP 階段 2 - 需求提取階段 |
| **使用時機** | 人機協作點 1（輸入理解確認與非功能需求引導） |
| **主要使用者** | PM/PO Agent, SA Agent, BA Agent |
| **問題數量** | 72 個（52 個必問 + 20 個情境專屬） |
| **用途簡述** | 在需求提取階段系統性確認所有必要問題，確保需求理解全面 |

**包含類別**:
- 目標使用者與使用情境（6 個問題）
- 核心功能與優先級（5 個問題）
- 資料與同步需求（7 個問題）
- 平台與技術約束（6 個問題）
- 非功能性需求（11 個問題）
- 平台特性與整合（8 個問題）
- 第三方整合（5 個問題）
- 使用者體驗（8 個問題）
- 維護與更新（4 個問題）

**情境專屬問題**:
- 情境 A: 記帳 / 財務管理 App（5 個問題）
- 情境 B: 社交 / 社群 App（4 個問題）
- 情境 C: 電商 / 購物 App（5 個問題）
- 情境 D: 內容閱讀 / 學習 App（4 個問題）
- 情境 E: 工具 / 生產力 App（4 個問題）

**對應 SOP 章節**: [Greenfield SOP.md - 階段 2, 步驟 2.2](../SOP.md#階段-2-需求提取與分析)

---

### 2. Cost_Estimation_Template.md
**成本試算表範本**

| 屬性 | 內容 |
|-----|------|
| **檔案名稱** | [Cost_Estimation_Template.md](Cost_Estimation_Template.md) |
| **文檔類型** | 範本（模板） |
| **使用階段** | SOP 階段 3 - 技術選型階段 |
| **使用時機** | 步驟 3.2 技術選型與架構草案 |
| **主要使用者** | PM/PO Agent, SD-Architect Agent, Dev Agent |
| **成本類別** | 5 大類別（開發、服務、帳號、基礎設施、維護） |
| **用途簡述** | 全面評估 Mobile App 專案的開發成本與營運成本 |

**包含成本類別**:
1. **開發成本（一次性）**
   - 人力成本（開發者、設計師、PM、QA）
   - 設計成本（UI/UX、Icon、Splash Screen）
   - 測試成本（測試裝置、測試平台）

2. **第三方服務成本（持續性）**
   - 雲端服務（Firebase, AWS, Heroku）
   - 推播服務（FCM, OneSignal）
   - 分析服務（Firebase Analytics, Mixpanel）
   - 錯誤監控（Sentry, Crashlytics）
   - 其他 API 服務（地圖、金融、簡訊）

3. **開發者帳號與證書（年度）**
   - Apple Developer Program（$99/年）
   - Google Play Console（$25 一次性）
   - SSL 證書與網域

4. **CI/CD 與基礎設施（月度）**
   - CI/CD 工具（GitHub Actions, CircleCI）
   - 程式碼倉庫（GitHub, GitLab）
   - 測試服務（Firebase Test Lab, BrowserStack）

5. **維護與營運成本（年度）**
   - 維護人力
   - 伺服器與雲端成本
   - 第三方服務續約

**特色功能**:
- MoneyTracker 實際範例（首年成本 $124,590）
- 技術棧成本對比（React Native vs Flutter vs Native）
- 成本增長預估（依使用者規模）
- 成本優化建議

**對應 SOP 章節**: [Greenfield SOP.md - 階段 3, 步驟 3.2](../SOP.md#階段-3-技術選型)

---

### 3. Completeness_Checklist.md
**需求完整性檢查清單**

| 屬性 | 內容 |
|-----|------|
| **檔案名稱** | [Completeness_Checklist.md](Completeness_Checklist.md) |
| **文檔類型** | 檢查清單 |
| **使用階段** | SOP 階段 4 - PRD 撰寫前 |
| **使用時機** | 步驟 4.1 需求完整性檢查 |
| **主要使用者** | SA Agent, BA Agent, QA Agent |
| **檢查項目** | 120 個（9 大類別） |
| **用途簡述** | 撰寫 PRD 前驗證需求完整性，確保無遺漏 |

**包含類別**:
1. **核心功能完整性**（15 項）
   - 功能清單、功能流程、資料處理、商業規則

2. **Mobile 特定需求**（30 項）
   - 離線模式與資料同步
   - Onboarding 與首次使用教學
   - 搜尋功能
   - 匯入/匯出功能
   - 備份與還原
   - 推播通知

3. **使用者體驗**（12 項）
   - 多語系支援、無障礙設計、設定頁面、主題與外觀

4. **效能與安全**（15 項）
   - 效能需求、安全需求、隱私保護

5. **整合與相容性**（10 項）
   - 第三方整合、裝置相容性、跨平台一致性

6. **合規與政策**（8 項）
   - App Store 政策、法規遵循、內容政策

7. **App 生命週期**（10 項）
   - 版本更新策略、錯誤回報與監控、分析與追蹤

8. **技術需求**（12 項）
   - 技術架構、開發環境、測試策略

9. **可測試性**（8 項）
   - Acceptance Criteria、測試資料、測試環境

**特色功能**:
- 完整性評分機制（90-100% 優秀，70-89% 良好）
- MoneyTracker 範例檢查結果（93% 完整性）
- 遺漏項目識別與追蹤

**對應 SOP 章節**: [Greenfield SOP.md - 階段 4, 步驟 4.1](../SOP.md#階段-4-需求驗證與-prd)

---

## 🔄 使用流程

### Greenfield 開發流程中的檢查清單使用時機

```
階段 1: 專案初始化
    ↓
階段 2: 需求提取與分析
    ├─ 步驟 2.2: 人機協作點 1
    └─ 📋 使用：Standard_Confirmation_Questions.md
        ↓
階段 3: 技術選型
    ├─ 步驟 3.2: 技術選型與架構草案
    └─ 📋 使用：Cost_Estimation_Template.md
        ↓
階段 4: 需求驗證與 PRD
    ├─ 步驟 4.1: 需求完整性檢查
    └─ 📋 使用：Completeness_Checklist.md
        ↓
階段 5-9: 系統設計 → 實作 → 測試 → 移交
```

---

## 📊 檢查清單快速對照表

| 檔案 | 階段 | 步驟 | 問題/項目數 | 預計時間 | 產出 |
|-----|------|------|------------|---------|------|
| Standard_Confirmation_Questions | 階段 2 | 2.2 | 72 | 20 分鐘 | 記錄在 Requirement_Extraction_Report |
| Cost_Estimation_Template | 階段 3 | 3.2 | N/A | 1-2 小時 | 整合到 Tech_Stack_Selection_Report |
| Completeness_Checklist | 階段 4 | 4.1 | 120 | 30-45 分鐘 | 完整性評分 + 遺漏項目清單 |

---

## 🎯 最佳實踐

### 使用檢查清單的建議

1. **不要跳過**
   - 每個檢查清單都有其重要性，建議完整執行
   - 跳過檢查可能導致後續返工成本更高

2. **記錄檢查結果**
   - 使用對應的產出文件模板記錄檢查結果
   - 標記已確認項目（打勾 ✅）

3. **識別 N/A 項目**
   - 某些項目可能不適用於特定專案
   - 標記為 N/A 並說明原因

4. **團隊協作**
   - 檢查清單不是單一 Agent 的工作
   - PM/PO, SA, BA, QA 共同參與

5. **持續更新**
   - 在專案過程中發現新的檢查項目，更新檢查清單
   - 為未來專案建立更完善的檢查標準

---

## 💡 常見問題 (FAQ)

### Q1: 所有檢查清單都必須使用嗎？

**A**: 是的，建議完整使用。每個檢查清單針對特定階段，幫助確保該階段的產出完整性。跳過檢查可能導致遺漏重要需求。

---

### Q2: 檢查清單中的問題/項目可以調整嗎？

**A**: 可以。檢查清單提供標準化基準，但團隊可依專案特性調整：
- **新增**: 專案特定的檢查項目
- **移除**: 確定不適用的項目（標記 N/A）
- **修改**: 調整問題描述以更符合專案情境

---

### Q3: 如果檢查清單有很多未確認項目怎麼辦？

**A**:
- **< 70% 完整性**: 建議返回前階段補充需求
- **70-89% 完整性**: 補充遺漏項目後繼續
- **≥ 90% 完整性**: 可進入下一階段

---

### Q4: Cost_Estimation_Template 的成本數字不準確怎麼辦？

**A**: 成本試算表提供的是參考範例（以美國市場為準）。團隊應：
- 依據本地市場調整時薪/費用
- 使用實際報價替代範例數字
- 保留試算表結構，更新數字內容

---

### Q5: 檢查清單需要每次都從頭檢查嗎？

**A**:
- **首次使用**: 完整檢查所有項目
- **後續專案**: 可依專案類型略過明確不適用的項目
- **團隊經驗累積**: 建立專案類型專屬的簡化版檢查清單

---

## 🔗 相關文件

### 上游文件
- [Greenfield SOP.md](../SOP.md) - 完整開發流程
- [AISDLC_INIT.md](../../../AISDLC_INIT.md) - Agent 載入規則

### 產出文件模板
- [Requirement_Extraction_Report_Template.md](../../../docs_template/support/Requirement_Extraction_Report_Template.md)
- [Tech_Stack_Selection_Report_Template.md](../../../docs_template/support/Tech_Stack_Selection_Report_Template.md)
- [PRD_Universal_Template.md](../../../docs_template/core/prd/PRD_Universal_Template.md)

### 其他指引文件
- [Estimation_Standards.md](../../../guides/system/planning/Estimation_Standards.md) - 估算標準
- [AISDLC_ID_Naming_Convention.md](../../../guides/system/naming/AISDLC_ID_Naming_Convention.md) - ID 命名規範

---

## 📈 使用統計（建議追蹤）

團隊可選擇性追蹤以下指標，用於持續改進：

| 指標 | 說明 | 目標 |
|-----|------|------|
| **檢查清單使用率** | 專案使用檢查清單的比例 | 100% |
| **平均完整性分數** | Completeness_Checklist 平均分數 | ≥ 90% |
| **遺漏需求數** | 後續階段發現的遺漏需求數量 | < 5 個 |
| **返工次數** | 因需求遺漏導致的返工次數 | 0 次 |

---

## 🔄 版本歷史

| 版本 | 日期 | 變更說明 |
|-----|------|---------|
| v1.0 | 2025-11-12 | 初版建立 - Phase 2 P1 問題修正 |

---

## 📧 回饋與改進

如果您在使用檢查清單時發現：
- 缺少重要檢查項目
- 某些項目不適用或過時
- 使用流程需要優化

請透過以下方式回饋：
- 更新本文檔並提交 Pull Request
- 在專案 Issue Tracker 中提出建議

---

**目錄維護者**: AISDLC Framework Team
**最後更新**: 2025-11-12
**狀態**: ✅ Active

---

**End of Document**
