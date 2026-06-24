# AISDLC 第三方整合實戰範例：Android 記帳 APP

**版本**: v0.01
**最後更新**: 2025-12-16
**情境**: 第三方整合 (Integration)
**平台**: Android
**語言/框架**: Kotlin, Jetpack Compose, MVVM, Python/RESTful API


> **SDD v0.01 使用者提示**：本指南基於 AISDLC-SDD v0.01。使用 AISDLC-SDD v0.01 時，請同時參考對應場景的 SDD Enhancement 文件（`scenarios/{scenario}/SDD_{SCENARIO}_ENHANCEMENT.md`），並確認所有 SCG 閘門步驟已整合到您的工作流程中。

---
---

## 📋 範例概述

本文檔展示如何使用 **AISDLC-SDD v0.01** 在 **Cursor AI** 環境中，透過 **Claude Code** 開發 Android 記帳軟體，涵蓋從專案設定到完整開發流程。

**技術棧**:
- **前端**: Kotlin + Jetpack Compose (UI)
- **架構**: MVVM + Hilt/Dagger (DI)
- **後端**: Python + RESTful API (可選)
- **AI 工具**: Claude Code (claude.ai/code)

---

## 🎯 第一部分：環境設定

### 步驟 1.1: 設定 Cursor AI 專案路徑

**1.1.1 創建專案目錄**

```bash
# 在您的工作目錄創建專案
mkdir -p ~/projects/MoneyTracker
cd ~/projects/MoneyTracker

# 創建 Android 專案結構
mkdir -p app/src/main/{java,res,kotlin}
mkdir -p app/src/main/java/com/example/moneytracker
```

**1.1.2 在 Cursor 開啟專案**

```bash
# 使用 Cursor 開啟專案目錄
cursor ~/projects/MoneyTracker
```

或：
1. 開啟 Cursor AI
2. File → Open Folder
3. 選擇 `~/projects/MoneyTracker`

---

### 步驟 1.2: 安裝設定 AISDLC-SDD v0.01

**1.2.1 下載 AISDLC 框架**

```bash
# 方法 A: 克隆完整框架 (如有 Git Repo)
cd ~/projects
git clone <AISDLC_REPO_URL> AISDLC_ALL
cd MoneyTracker

# 方法 B: 手動複製 (如已下載)
cp -r /path/to/AISDLC_ALL ~/projects/
```

**1.2.2 建立專案與框架的連結**

```bash
# 在專案根目錄創建 AISDLC 符號連結
cd ~/projects/MoneyTracker
ln -s ~/projects/AISDLC_ALL/AISDLC_v0.09 ./AISDLC

# 驗證連結
ls -la | grep AISDLC
# 應顯示: AISDLC -> ~/projects/AISDLC_ALL/AISDLC_v0.09
```

**1.2.3 創建專案文檔目錄**

```bash
# 創建 AISDLC 建議的文檔結構
mkdir -p docs/{requirements,design,api,tests}
mkdir -p docs/analysis
mkdir -p docs/planning
```

**1.2.4 創建 CLAUDE.md (專案指引)**

在專案根目錄創建 `CLAUDE.md`：

```bash
cat > CLAUDE.md << 'EOF'
# MoneyTracker 專案指引

**專案名稱**: MoneyTracker (記帳軟體)
**AISDLC 版本**: v0.01
**開發情境**: 第三方整合 (Integration)

## 專案架構

- **前端**: Kotlin + Jetpack Compose
- **架構**: MVVM + Hilt
- **後端**: Python + RESTful API (可選)

## AISDLC 框架路徑

- **框架位置**: `./AISDLC/` (符號連結至 AISDLC_v0.09)
- **文檔輸出**: `./docs/`

## 開發規範

1. 所有需求文檔遵循 AISDLC PRD/FRD 模板
2. API 設計遵循 AISDLC API 規格模板
3. 使用 AISDLC Integration 情境 SOP

## 重要提醒

- 執行任何 workflow 前，先讀取 `AISDLC/AISDLC_INIT.md`
- 使用 Integration Scenario: `AISDLC/scenarios/integration/SOP.md`
EOF
```

**1.2.5 驗證設定**

```bash
# 檢查 AISDLC 核心檔案是否可訪問
ls AISDLC/AISDLC_INIT.md
ls AISDLC/scenarios/integration/SOP.md
ls AISDLC/guides/user/onboarding/QUICK_START_GUIDE.md

# 檢查專案文檔目錄
tree docs -L 2
```

---

## 🚀 第二部分：使用 Claude Code 開發

### 步驟 2.1: 啟動 Claude Code

**2.1.1 在 Cursor 終端機啟動**

方法 A (如已安裝 Claude Code CLI):
```bash
# 在專案目錄啟動
claude code
```

方法 B (使用 Cursor 內建整合):
1. 按 `Cmd+Shift+P` (Mac) 或 `Ctrl+Shift+P` (Windows)
2. 輸入 "Claude"
3. 選擇 "Start Claude Code Session"

**2.1.2 驗證 Claude Code 可訪問 AISDLC**

在 Claude Code 對話框輸入：

```
請讀取 AISDLC/AISDLC_INIT.md 確認框架已正確載入
```

預期回應：Claude 應讀取檔案並確認框架版本為 v0.09。

---

### 步驟 2.2: 第一階段 - 需求分析 (Requirements Extraction)

**2.2.1 初始化 AISDLC 框架**

💬 **您對 Claude 說**：
```
我要開始一個新的 Android 記帳 APP 專案 (MoneyTracker)。

請執行以下步驟：
1. 讀取 AISDLC/AISDLC_INIT.md
2. 讀取 AISDLC/scenarios/integration/SOP.md
3. 告訴我應該從哪個 workflow 開始
```

🤖 **Claude 回應範例**：
```
已讀取 AISDLC_INIT.md 和 Integration SOP。

根據您的情況（全新 Android APP 開發），建議流程：
1. ✅ 先使用 unified-requirements-extraction workflow (需求萃取)
2. ✅ 再使用 user-story-and-design workflow (使用者故事與設計)
3. ✅ 再使用 api-specification-generation workflow (API 規格)

請提供您的需求描述或功能清單，我將協助執行需求萃取。
```

---

**2.2.2 執行需求萃取 Workflow**

💬 **您對 Claude 說**：
```
請使用 unified-requirements-extraction workflow 分析以下需求：

## 記帳 APP 功能需求

1. 使用者註冊與登入
2. 記錄收入/支出
3. 分類管理 (食、衣、住、行、娛樂等)
4. 每月帳單統計與圖表
5. 預算設定與提醒
6. 資料雲端同步 (Python 後端)

請載入對應的 Agent 並開始需求分析。
```

🤖 **Claude 執行步驟**：

```
步驟 1: 讀取 AISDLC/workflow/core/unified-requirements-extraction.md
步驟 2: 根據 AISDLC_INIT.md 載入對應 Agents:
  - SA (System Analyst): AISDLC/agent/core/04.sa-analyst-zh.yaml
  - BA (Business Analyst): AISDLC/agent/core/02.ba-business-analyst-zh.yaml

步驟 3: 🔴 人機協作檢查點 - 我需要向您確認：

【需求釐清問題】
Q1: 使用者註冊 - 需要支援第三方登入 (Google/Facebook) 嗎？
Q2: 資料同步 - 是否需要支援離線模式？
Q3: 預算提醒 - 通知方式為？(推播通知/App 內提示)
Q4: 圖表類型 - 偏好哪種圖表？(圓餅圖/長條圖/折線圖)

請回答以上問題，我將繼續完善需求分析。
```

---

**2.2.3 回答 Agent 問題**

💬 **您對 Claude 說**：
```
回答如下：
A1: 先支援 Email 註冊，第三方登入列為 v2.0 功能
A2: 需要離線模式，本地 SQLite + 雲端同步
A3: 推播通知 (Firebase Cloud Messaging)
A4: 圓餅圖(分類佔比) + 折線圖(每日趨勢)
```

🤖 **Claude 執行**：
```
收到！我將基於您的回答生成 FRD (功能需求文檔)。

執行步驟：
1. 讀取 AISDLC/docs_template/core/frd/FRD_Universal_Template.md
2. 讀取 AISDLC/guides/system/naming/AISDLC_ID_Naming_Convention.md
3. 生成需求 ID (US-001, US-002...)
4. 撰寫 FRD 到 docs/requirements/FRD_MoneyTracker_v1.0.md

【生成中...】

✅ 完成！已生成：
- docs/requirements/FRD_MoneyTracker_v1.0.md (功能需求文檔)
- 包含 8 個 User Stories (US-001 ~ US-008)
- 包含 32 個 Acceptance Criteria (AC-001-1 ~ AC-008-4)

請檢閱文檔，確認無誤後我們進入下一階段。
```

---

### 步驟 2.3: 第二階段 - 系統設計 (System Design)

**2.3.1 執行使用者故事與設計 Workflow**

💬 **您對 Claude 說**：
```
FRD 已確認。請執行 user-story-and-design workflow，
生成 SRD (系統需求文檔)，包含：
1. MVVM 架構設計
2. Jetpack Compose UI 元件規劃
3. 本地資料庫 Schema (Room)
4. API 端點定義
```

🤖 **Claude 執行**：
```
步驟 1: 讀取 AISDLC/workflow/core/user-story-and-design.md
步驟 2: 載入 SD (System Designer) Agent
  - AISDLC/agent/core/05.sd-architect-zh.yaml

步驟 3: 讀取架構設計指南
  - AISDLC/guides/system/architecture/C4_Model_Guidelines.md
  - AISDLC/guides/system/architecture/Web_Architecture_Decision_Tree.md

步驟 4: 生成 SRD
  - 使用模板: AISDLC/docs_template/core/srd/SRD_Template.md

【設計中...】

✅ 完成！已生成：
1. docs/design/SRD_MoneyTracker_v1.0.md
   - 包含 C4 Model (Context, Container, Component 層級圖)
   - MVVM 架構說明
   - Room Database Schema
   - Jetpack Compose 元件樹狀圖

2. docs/design/Architecture_Decision_Records.md
   - ADR-001: 選擇 MVVM 架構 (理由: 可測試性、生命週期管理)
   - ADR-002: 選擇 Room 而非 SQLite (理由: 編譯時驗證、RxJava 整合)
   - ADR-003: 選擇 Hilt 而非 Dagger (理由: 減少樣板代碼)

請檢閱設計文檔。
```

---

**2.3.2 生成 API 規格**

💬 **您對 Claude 說**：
```
設計文檔已確認。請執行 api-specification-generation workflow，
為雲端同步功能生成詳細的 API 規格。
```

🤖 **Claude 執行**：
```
步驟 1: 讀取 AISDLC/workflow/core/api-specification-generation.md
步驟 2: 讀取 API 模板
  - AISDLC/docs_template/core/api/API_Specification_Template.md

步驟 3: 讀取 API 設計指南
  - AISDLC/guides/system/api/API_Versioning_Guide.md

步驟 4: 生成 API 規格

【生成中...】

✅ 完成！已生成 7 個 API 規格文檔：

docs/api/
├── API_Index.md
├── API_Auth_Register.md       # POST /api/v1/auth/register
├── API_Auth_Login.md          # POST /api/v1/auth/login
├── API_Transactions_Create.md # POST /api/v1/transactions
├── API_Transactions_List.md   # GET /api/v1/transactions
├── API_Categories_List.md     # GET /api/v1/categories
└── API_Sync_Upload.md         # POST /api/v1/sync/upload

每個 API 規格包含：
- 完整的 Request/Response 範例
- 狀態碼定義
- 錯誤處理
- 安全性考量 (JWT Token)
- Rate Limiting 規範

請檢閱 API 規格。
```

---

### 步驟 2.4: 第三階段 - 驗證一致性

**2.4.1 執行文檔一致性檢查**

💬 **您對 Claude 說**：
```
請執行 document-consistency-check workflow，
驗證 FRD、SRD、API 規格的一致性。
```

🤖 **Claude 執行**：
```
步驟 1: 讀取 AISDLC/workflow/core/document-consistency-check.md
步驟 2: 載入 QA Agent
  - AISDLC/agent/core/07.qa-tester-zh.yaml

步驟 3: 執行交叉驗證
  - FRD US-001 (使用者註冊) ↔ SRD (UserViewModel) ↔ API_Auth_Register.md
  - FRD US-002 (記錄交易) ↔ SRD (TransactionRepository) ↔ API_Transactions_Create.md
  - ... (全部 8 個 User Stories)

【驗證中...】

⚠️ 發現 2 個不一致問題：

1. 🔴 問題 1: FRD US-005 (預算提醒) 在 API 規格中缺少對應端點
   - 建議: 新增 API_Budget_GetStatus.md

2. 🔴 問題 2: SRD 提到「圓餅圖使用 MPAndroidChart」，但未在 FRD 技術選型中說明
   - 建議: 在 SRD 增加第三方函式庫章節

是否要我修正這些問題？(是/否)
```

💬 **您對 Claude 說**：
```
是，請修正。
```

🤖 **Claude 執行**：
```
✅ 已修正！

1. 新增 docs/api/API_Budget_GetStatus.md
2. 更新 docs/design/SRD_MoneyTracker_v1.0.md
   - 新增「第三方函式庫」章節
   - 列出 MPAndroidChart, Retrofit, Room, Hilt 版本

✅ 一致性驗證通過！
生成驗證報告: docs/reports/Document_Consistency_Report_2025-12-16.md
```

---

### 步驟 2.5: 第四階段 - 程式碼實作引導

**2.5.1 請求程式碼架構生成**

💬 **您對 Claude 說**：
```
文檔已完成。請根據 SRD 生成 Kotlin 程式碼架構：

1. 生成 MVVM 層級的檔案結構
2. 生成 ViewModel、Repository、DAO 介面定義
3. 生成 Jetpack Compose UI 基礎元件

請使用 AISDLC scenarios/integration/SOP.md 的程式碼生成步驟。
```

🤖 **Claude 執行**：
```
步驟 1: 讀取 AISDLC/scenarios/integration/SOP.md
步驟 2: 讀取 AISDLC/guides/system/architecture/C4_Model_Guidelines.md
步驟 3: 讀取 SRD_MoneyTracker_v1.0.md 架構設計

【生成程式碼架構...】

✅ 完成！已生成檔案結構：

app/src/main/kotlin/com/example/moneytracker/
├── data/
│   ├── local/
│   │   ├── dao/
│   │   │   ├── TransactionDao.kt
│   │   │   ├── CategoryDao.kt
│   │   │   └── UserDao.kt
│   │   ├── entity/
│   │   │   ├── TransactionEntity.kt
│   │   │   ├── CategoryEntity.kt
│   │   │   └── UserEntity.kt
│   │   └── AppDatabase.kt
│   ├── remote/
│   │   ├── api/
│   │   │   ├── AuthApi.kt
│   │   │   ├── TransactionApi.kt
│   │   │   └── SyncApi.kt
│   │   └── dto/
│   │       ├── LoginRequest.kt
│   │       └── TransactionDto.kt
│   └── repository/
│       ├── TransactionRepository.kt
│       ├── AuthRepository.kt
│       └── CategoryRepository.kt
├── domain/
│   ├── model/
│   │   ├── Transaction.kt
│   │   ├── Category.kt
│   │   └── User.kt
│   └── usecase/
│       ├── GetTransactionsUseCase.kt
│       ├── AddTransactionUseCase.kt
│       └── LoginUseCase.kt
├── presentation/
│   ├── viewmodel/
│   │   ├── TransactionViewModel.kt
│   │   ├── LoginViewModel.kt
│   │   └── StatisticsViewModel.kt
│   └── ui/
│       ├── screen/
│       │   ├── LoginScreen.kt
│       │   ├── HomeScreen.kt
│       │   ├── AddTransactionScreen.kt
│       │   └── StatisticsScreen.kt
│       ├── component/
│       │   ├── TransactionCard.kt
│       │   ├── CategorySelector.kt
│       │   └── ChartView.kt
│       └── theme/
│           ├── Color.kt
│           ├── Theme.kt
│           └── Type.kt
└── di/
    ├── AppModule.kt
    ├── DatabaseModule.kt
    └── NetworkModule.kt

已生成所有檔案的介面定義和基礎結構。
下一步：實作業務邏輯？(是/否)
```

---

**2.5.2 實作核心功能**

💬 **您對 Claude 說**：
```
是。請先實作「新增交易」功能 (US-002)，包含：
1. TransactionViewModel
2. AddTransactionScreen (Compose UI)
3. AddTransactionUseCase
4. TransactionRepository
```

🤖 **Claude 執行**：
```
步驟 1: 讀取 docs/requirements/FRD_MoneyTracker_v1.0.md (US-002)
步驟 2: 讀取 docs/design/SRD_MoneyTracker_v1.0.md (架構設計)
步驟 3: 實作程式碼

【實作中...】

✅ 完成！已實作：

1. ✅ presentation/viewmodel/TransactionViewModel.kt
   - 狀態管理 (MutableStateFlow)
   - 新增交易邏輯
   - 驗證規則 (金額 > 0, 分類必選)

2. ✅ presentation/ui/screen/AddTransactionScreen.kt
   - Jetpack Compose UI
   - 金額輸入框、分類選擇器、日期選擇器
   - 表單驗證與錯誤提示

3. ✅ domain/usecase/AddTransactionUseCase.kt
   - 業務邏輯: 驗證、轉換、儲存

4. ✅ data/repository/TransactionRepositoryImpl.kt
   - 本地儲存 (Room)
   - 遠端同步 (Retrofit) - 標記為 TODO (後端未完成)

5. ✅ 單元測試
   - TransactionViewModelTest.kt
   - AddTransactionUseCaseTest.kt

程式碼已遵循：
- AISDLC ID 追蹤 (註解標示 US-002, AC-002-1)
- MVVM 架構分層
- Kotlin Coding Conventions

下一步：執行測試？(是/否)
```

---

### 步驟 2.6: 第五階段 - 測試驗證

**2.6.1 執行單元測試**

💬 **您對 Claude 說**：
```
是，請執行單元測試並回報結果。
```

🤖 **Claude 執行**：
```
步驟 1: 讀取 AISDLC/guides/system/testing/AT_vs_TC_Guide.md
步驟 2: 執行測試命令

$ ./gradlew test

【測試執行中...】

✅ 測試結果：

TransactionViewModelTest
  ✅ testAddTransaction_Success (0.012s)
  ✅ testAddTransaction_InvalidAmount (0.008s)
  ✅ testAddTransaction_MissingCategory (0.007s)

AddTransactionUseCaseTest
  ✅ testExecute_Success (0.015s)
  ✅ testExecute_ValidationFail (0.009s)

總計: 5 個測試通過，0 個失敗

測試覆蓋率: 87% (ViewModel 92%, UseCase 84%)

生成測試報告: docs/tests/Unit_Test_Report_AddTransaction_2025-12-16.md
```

---

**2.6.2 執行驗收測試 (Acceptance Test)**

💬 **您對 Claude 說**：
```
單元測試通過。請根據 FRD 的 Acceptance Criteria 生成驗收測試。
```

🤖 **Claude 執行**：
```
步驟 1: 讀取 docs/requirements/FRD_MoneyTracker_v1.0.md (AC-002-1 ~ AC-002-4)
步驟 2: 讀取 AISDLC/docs_template/core/tests/Acceptance_Test_Template.md
步驟 3: 生成驗收測試

✅ 完成！已生成：

docs/tests/AT_US-002_AddTransaction.md

驗收測試案例：
AT-002-1: 使用者可成功新增支出
  - 前置條件: 使用者已登入
  - 測試步驟: 1) 點擊「新增」 2) 輸入金額 500 3) 選擇「食」 4) 儲存
  - 預期結果: 交易成功儲存，顯示於首頁列表
  - 實際結果: ✅ 通過 (手動測試)

AT-002-2: 金額驗證 - 拒絕零或負數
  - 測試步驟: 輸入金額 0
  - 預期結果: 顯示錯誤提示「金額必須大於 0」
  - 實際結果: ✅ 通過

AT-002-3: 分類驗證 - 必須選擇分類
  - 測試步驟: 未選擇分類，點擊儲存
  - 預期結果: 顯示錯誤提示「請選擇分類」
  - 實際結果: ✅ 通過

AT-002-4: 離線模式 - 本地儲存
  - 前置條件: 關閉網路
  - 測試步驟: 新增交易
  - 預期結果: 交易儲存至本地，標記為「待同步」
  - 實際結果: ✅ 通過

驗收測試狀態: 4/4 通過 (100%)
```

---

### 步驟 2.7: 後續功能開發

**2.7.1 使用迭代開發模式**

💬 **您對 Claude 說**：
```
US-002 已完成。請繼續實作 US-003 (查看交易列表)，
使用相同的開發流程。
```

🤖 **Claude 執行**：
```
收到！我將重複以下流程：

1. ✅ 讀取 FRD US-003 需求
2. ✅ 實作 TransactionListViewModel
3. ✅ 實作 HomeScreen (Compose LazyColumn)
4. ✅ 實作 GetTransactionsUseCase
5. ✅ 撰寫單元測試
6. ✅ 撰寫驗收測試
7. ✅ 執行測試驗證

【開發中...】

(此處省略詳細步驟，與 US-002 類似)

✅ US-003 完成！
```

---

## 📊 第三部分：完整開發流程總結

### 3.1 命令範例清單 (依階段)

#### 階段 1: 需求分析

```
命令範例 1:
「請讀取 AISDLC/AISDLC_INIT.md，並告訴我 Integration 情境應該使用哪些 workflows。」

命令範例 2:
「使用 unified-requirements-extraction workflow 分析以下需求：[貼上需求清單]」

命令範例 3:
「載入 SA 和 BA Agents，針對需求提出釐清問題。」
```

#### 階段 2: 系統設計

```
命令範例 4:
「使用 user-story-and-design workflow，根據 FRD 生成 SRD，包含 MVVM 架構設計。」

命令範例 5:
「讀取 C4_Model_Guidelines.md，為 MoneyTracker 繪製 Container Diagram。」

命令範例 6:
「使用 api-specification-generation workflow，為所有 API 端點生成詳細規格。」
```

#### 階段 3: 一致性驗證

```
命令範例 7:
「執行 document-consistency-check workflow，驗證 FRD、SRD、API 規格的一致性。」

命令範例 8:
「檢查所有 User Stories 是否都有對應的 API 端點和 ViewModel。」
```

#### 階段 4: 程式碼實作

```
命令範例 9:
「根據 SRD 生成完整的 Kotlin 檔案結構 (MVVM + Hilt)。」

命令範例 10:
「實作 US-002 (新增交易) 的所有層級：ViewModel、UseCase、Repository、UI。」

命令範例 11:
「為 TransactionViewModel 撰寫單元測試，覆蓋所有邊界情況。」
```

#### 階段 5: 測試驗證

```
命令範例 12:
「執行 ./gradlew test 並回報測試結果。」

命令範例 13:
「根據 FRD 的 Acceptance Criteria 生成驗收測試文檔。」

命令範例 14:
「執行所有驗收測試並更新測試狀態。」
```

---

### 3.2 完整開發時間軸 (範例)

| 時間 | 階段 | Claude 命令 | 產出文檔 |
|------|------|------------|---------|
| Day 1 上午 | 需求分析 | 命令 1-3 | FRD_MoneyTracker_v1.0.md |
| Day 1 下午 | 系統設計 | 命令 4-6 | SRD_MoneyTracker_v1.0.md<br>API_Index.md + 7 個 API 規格 |
| Day 2 上午 | 一致性驗證 | 命令 7-8 | Document_Consistency_Report.md |
| Day 2 下午 | 程式碼架構 | 命令 9 | 完整 Kotlin 檔案結構 |
| Day 3-5 | 功能實作 | 命令 10-11 (重複 8 次) | 8 個 User Stories 的程式碼 |
| Day 6 | 測試驗證 | 命令 12-14 | 測試報告、驗收測試文檔 |

---

### 3.3 關鍵成功要素

#### ✅ DO (建議做的)

1. **每次開發前讀取 AISDLC_INIT.md**
   - 確保載入正確的 Agents 和 Workflows

2. **明確指定要使用的 Workflow**
   - 例：「使用 api-specification-generation workflow」

3. **提供完整的上下文**
   - 貼上需求清單、技術棧、限制條件

4. **利用 🔴 人機協作檢查點**
   - 當 Claude 提出問題時，詳細回答

5. **要求生成 AISDLC 規範的文檔**
   - 明確要求「使用 FRD_Universal_Template.md」

6. **迭代式開發**
   - 一次完成一個 User Story，再進行下一個

#### ❌ DON'T (避免做的)

1. **不要跳過 Workflow**
   - 錯誤：「直接幫我寫程式碼」
   - 正確：「先執行需求分析 workflow，再執行設計 workflow」

2. **不要忽略 Agent 的問題**
   - 錯誤：「隨便，你決定」
   - 正確：提供明確的決策依據

3. **不要省略文檔驗證**
   - 錯誤：「FRD 看起來 OK，直接寫程式碼吧」
   - 正確：「先執行 document-consistency-check」

4. **不要混用多個版本的 AISDLC**
   - 確保所有路徑都指向 `AISDLC_v0.09`

---

## 🎓 第四部分：進階技巧

### 4.1 整合第三方服務 (Firebase)

💬 **命令範例**：
```
我要整合 Firebase Cloud Messaging 實現推播通知 (US-005)。

請執行以下步驟：
1. 讀取 AISDLC/scenarios/integration/SOP.md 的第三方整合章節
2. 分析 Firebase SDK 整合點
3. 更新 SRD 加入 Firebase 架構圖
4. 生成整合程式碼 (FirebaseMessagingService)
```

---

### 4.2 使用專業化 Agent

💬 **命令範例**：
```
我需要審查程式碼品質。

請載入 AISDLC/agent/specialized/code-analyzer.yaml，
分析 presentation/viewmodel/ 目錄下的所有 ViewModel，
檢查：
1. MVVM 架構遵循度
2. Kotlin Conventions
3. 記憶體洩漏風險
4. 測試覆蓋率
```

---

### 4.3 生成技術文檔

💬 **命令範例**：
```
請使用 AISDLC/scenarios/documentation/SOP.md，
為 MoneyTracker 生成 API 使用手冊 (Markdown 格式)，
包含：
1. 認證流程說明
2. 每個 API 的 cURL 範例
3. 錯誤碼對照表
4. 測試帳號資訊
```

---

## 📁 第五部分：最終專案結構

```
MoneyTracker/
├── AISDLC/                           # 符號連結至 AISDLC_v0.09
├── CLAUDE.md                         # Claude Code 專案指引
├── app/
│   ├── src/
│   │   ├── main/
│   │   │   ├── kotlin/com/example/moneytracker/
│   │   │   │   ├── data/            # Repository, DAO, API
│   │   │   │   ├── domain/          # UseCase, Model
│   │   │   │   ├── presentation/    # ViewModel, UI
│   │   │   │   └── di/              # Hilt Modules
│   │   │   ├── res/                 # Android Resources
│   │   │   └── AndroidManifest.xml
│   │   └── test/                    # 單元測試
│   └── build.gradle.kts
├── docs/
│   ├── requirements/
│   │   └── FRD_MoneyTracker_v1.0.md
│   ├── design/
│   │   ├── SRD_MoneyTracker_v1.0.md
│   │   └── Architecture_Decision_Records.md
│   ├── api/
│   │   ├── API_Index.md
│   │   ├── API_Auth_Register.md
│   │   └── (其他 6 個 API 規格)
│   ├── tests/
│   │   ├── AT_US-002_AddTransaction.md
│   │   └── Unit_Test_Report_AddTransaction_2025-12-16.md
│   └── reports/
│       └── Document_Consistency_Report_2025-12-16.md
├── backend/                          # Python 後端 (可選)
│   ├── app/
│   │   ├── api/
│   │   ├── models/
│   │   └── services/
│   └── requirements.txt
└── README.md
```

---

## 🔍 常見問題 (FAQ)

### Q1: Claude 找不到 AISDLC 檔案？

**A**: 檢查符號連結是否正確：
```bash
ls -la AISDLC
# 應顯示: AISDLC -> /path/to/AISDLC_v0.09

# 如果連結錯誤，重新創建
rm AISDLC
ln -s ~/projects/AISDLC_ALL/AISDLC_v0.09 ./AISDLC
```

---

### Q2: Claude 沒有按照 Workflow 執行？

**A**: 明確指定 Workflow 名稱並要求讀取：
```
請執行以下步驟：
1. 讀取 AISDLC/workflow/core/unified-requirements-extraction.md
2. 根據 Workflow 定義的步驟逐一執行
```

---

### Q3: 如何讓 Claude 遵循 AISDLC 模板？

**A**: 明確要求使用模板：
```
請使用 AISDLC/docs_template/core/frd/FRD_Universal_Template.md
生成功能需求文檔，不要省略任何章節。
```

---

### Q4: 如何處理中英文混雜問題？

**A**: 在 CLAUDE.md 加入語言規範：
```markdown
## 語言規範
- 所有文檔使用繁體中文撰寫
- 專有名詞保持英文 (ViewModel, Repository 等)
- 程式碼註解使用繁體中文
```

---

## 📚 相關資源

### AISDLC 核心文檔
- [AISDLC_INIT.md](../../AISDLC_INIT.md) - 框架入口
- [Integration SOP](../../scenarios/integration/SOP.md) - 第三方整合標準流程
- [API 設計指南](../../guides/system/api/API_Versioning_Guide.md)

### 快速開始指南
- [QUICK_START_GUIDE.md](../onboarding/QUICK_START_GUIDE.md) - 5 分鐘快速上手
- [SCENARIO_SELECTOR.md](../onboarding/SCENARIO_SELECTOR.md) - 情境選擇器

### 範例專案
- [Greenfield 範例](./第三方整合-android手機APP_02_進階功能.md) (待補充)

---

## ✅ 結論

透過本範例，您已學會：

1. ✅ 在 Cursor AI 設定 AISDLC-SDD v0.01 專案
2. ✅ 使用 Claude Code 執行 AISDLC Workflows
3. ✅ 從需求分析到程式碼實作的完整流程
4. ✅ 如何與 AI Agents 協作進行開發
5. ✅ 如何驗證文檔一致性與測試

**核心理念**: AISDLC 不是取代開發者，而是**引導 AI 系統化地協助開發**，確保每個階段都有明確的輸入、輸出和驗證機制。

**下一步建議**:
1. 實際執行本範例中的命令
2. 閱讀 [Integration SOP](../../scenarios/integration/SOP.md) 深入了解整合流程
3. 探索其他情境 (Greenfield, Refactoring 等)

---

**文檔版本**: v1.0
**適用 AISDLC 版本**: v0.01
**最後更新**: 2025-12-16
**作者**: AISDLC 框架維護團隊
