# AISDLC 詳細實戰：開發 iPhone 記帳 APP

**專案類型**: Greenfield (全新專案)
**開發環境**: Xcode + Cursor AI + Claude Code
**前端技術**: Swift + SwiftUI (MVVM 模式)
**後端技術**: Python + FastAPI (可選)
**資料庫**: Core Data (本地) + PostgreSQL (後端)
**適用版本**: AISDLC-SDD v0.01+
**最後更新**: 2025-12-15


> **SDD v0.01 使用者提示**：本指南基於 AISDLC-SDD v0.01。使用 AISDLC-SDD v0.01 時，請同時參考對應場景的 SDD Enhancement 文件（`scenarios/{scenario}/SDD_{SCENARIO}_ENHANCEMENT.md`），並確認所有 SCG 閘門步驟已整合到您的工作流程中。

---
---

## 📋 完整目錄

1. [第一步：Cursor AI 專案路徑設定](#第一步cursor-ai-專案路徑設定)
2. [第二步：AISDLC 框架安裝](#第二步aisdlc-框架安裝)
3. [第三步：Claude Code 完整開發流程](#第三步claude-code-完整開發流程)
4. [附錄：命令速查表](#附錄命令速查表)

---

## 第一步：Xcode 專案路徑設定

### 1.1 建立 Xcode 專案

**步驟**:
1. 打開 Xcode
2. `File` → `New` → `Project`
3. 選擇 `iOS` → `App`
4. 設定專案資訊：
   - **Product Name**: ExpenseTracker
   - **Team**: (選擇您的開發團隊)
   - **Organization Identifier**: com.yourcompany
   - **Interface**: SwiftUI ✅
   - **Language**: Swift ✅
   - **Storage**: Core Data ✅ (勾選)
   - **Include Tests**: ✅ (勾選)

5. **儲存位置**: `~/Projects/ExpenseTrackerApp/iOS/`
   - 建議路徑: `/Users/你的用戶名/Projects/ExpenseTrackerApp/iOS/`
   - 點擊「Create」

### 1.2 驗證 Xcode 專案結構

**預期結構**:
```
~/Projects/ExpenseTrackerApp/
└── iOS/
    └── ExpenseTracker/
        ├── ExpenseTracker.xcodeproj       # 專案檔
        ├── ExpenseTracker/
        │   ├── ExpenseTrackerApp.swift    # App Entry Point
        │   ├── ContentView.swift          # 主 View
        │   ├── ExpenseTracker.xcdatamodeld  # Core Data Model
        │   ├── Assets.xcassets            # 圖片資源
        │   └── Preview Content/
        └── ExpenseTrackerTests/           # 測試目錄
```

### 1.3 建立專案完整結構

```bash
# 在終端機執行
cd ~/Projects/ExpenseTrackerApp
mkdir -p Backend          # Python API 專案 (可選)
mkdir -p Docs             # AISDLC 文檔輸出
mkdir -p Docs/analysis    # PRD/FRD
mkdir -p Docs/planning    # SRD/User Stories
mkdir -p Docs/planning/api  # API 規格
mkdir -p Docs/reports     # 驗證報告

# 驗證
ls -la
```

**完整專案結構**:
```
ExpenseTrackerApp/
├── iOS/                    # 🎯 Xcode 專案（已建立）
│   └── ExpenseTracker/
├── Backend/               # 🔧 Python FastAPI (可選)
├── Docs/                  # 📄 AISDLC 文檔輸出
│   ├── analysis/
│   ├── planning/
│   └── reports/
└── AISDLC_SDD_v0.01/         # 🔴 步驟 2 安裝
```

### 1.4 開啟 Cursor AI

**步驟**:
1. 打開 Cursor 應用程式
2. `File` → `Open Folder...`
3. 選擇：`~/Projects/ExpenseTrackerApp` （**專案根目錄**）
4. 點擊「Open」

**驗證**: Cursor 左側應顯示 `iOS/ExpenseTracker/`, `Docs/`, `Backend/`

---

## 第二步：AISDLC 框架安裝

### 2.1 方法一：符號連結（推薦）

**優點**: 節省磁碟空間，AISDLC 更新時自動同步

```bash
# 在 Cursor 內建終端執行（Terminal → New Terminal）
cd ~/Projects/ExpenseTrackerApp

# 創建符號連結
ln -s ~/Cursor_Project/AISDLC_ALL/AISDLC_v0.09 ./AISDLC_v0.09

# 驗證安裝
ls -la AISDLC_SDD_v0.01/
ls -la AISDLC_SDD_v0.01/AISDLC_INIT.md
```

**預期輸出**:
```
AISDLC_v0.09 -> /Users/你的用戶名/Cursor_Project/AISDLC_ALL/AISDLC_v0.09
-rw-r--r--  1 user  staff  XXXXX  AISDLC_INIT.md
```

### 2.2 方法二：完整拷貝

**優點**: 獨立版本，可針對專案客製化

```bash
cd ~/Projects/ExpenseTrackerApp

# 拷貝完整框架
cp -r ~/Cursor_Project/AISDLC_ALL/AISDLC_v0.09 .

# 驗證
du -sh AISDLC_v0.09  # 顯示大小
```

### 2.3 驗證安裝成功

```bash
# 檢查核心檔案
test -f AISDLC_SDD_v0.01/AISDLC_INIT.md && echo "✅ 安裝成功" || echo "❌ 安裝失敗"

# 檢查關鍵目錄
ls AISDLC_SDD_v0.01/agent/core/
ls AISDLC_SDD_v0.01/workflow/core/
ls AISDLC_SDD_v0.01/scenarios/greenfield/
```

---

## 第三步：Claude Code 完整開發流程

### 階段 0: 啟動 Claude Code

**在 Cursor 中**:
1. 按 `Cmd + Shift + P` 開啟命令面板
2. 輸入 `Claude Code`
3. 選擇 `Claude Code: Open`

或直接點擊右下角的 Claude 圖示

---

### 階段 1: 初始化 AISDLC 框架

#### 命令 1.1: 載入框架

在 Claude Code 對話框輸入：

```
請載入 AISDLC_SDD_v0.01/AISDLC_INIT.md

我要開發一個 iPhone 記帳 APP，請確認框架已正確初始化。
```

#### Claude Code 預期回應：

```
✅ 已成功載入 AISDLC-SDD v0.01 框架

框架資訊：
- 版本: v0.01
- 情境: Greenfield (全新專案開發)
- 可用 Agent: 7 個核心 Agent
- 可用 Workflow: 17 個 Workflow

請問您希望從哪個階段開始？
1. 需求分析（推薦）
2. 直接進入設計階段
```

---

### 階段 2: 需求分析（產出 PRD/FRD）

#### 命令 2.1: 啟動需求提取 Workflow

```
請使用 Greenfield SOP 引導我完成開發。

現在開始階段 1：需求分析

專案名稱：ExpenseTracker
專案類型：iPhone 記帳 APP

核心需求：
1. 收支記錄功能
   - 使用者可記錄每日收入/支出
   - 必填：金額、日期、分類
   - 選填：備註、照片（發票）

2. 分類管理
   - 預設分類：飲食、交通、娛樂、薪資、投資
   - 使用者可新增/編輯/刪除自訂分類
   - 每個分類有圖示和顏色

3. 統計圖表
   - 月度收支統計（折線圖）
   - 分類支出占比（圓餅圖）
   - 趨勢分析（柱狀圖）

4. 安全功能
   - Touch ID / Face ID 登入
   - 資料本地加密

5. 資料同步（未來功能）
   - 第一版使用 iCloud 同步
   - 未來版本考慮自建後端

技術棧：
- 前端：Swift + SwiftUI (MVVM 模式)
- 本地資料：Core Data
- 後端（v2.0）：Python FastAPI + PostgreSQL

請啟動 unified-requirements-extraction workflow，開始需求分析。
```

#### Claude Code 預期回應：

```
✅ 已載入 SA Agent (04.sa-analyst-zh.yaml)
✅ 已啟動 unified-requirements-extraction workflow

我會先進行需求確認，有幾個問題需要釐清：

🔴 人工確認點 1: 多幣別支援
Q1: 是否需要支援多幣別（USD, EUR, JPY 等）？
建議：如果有跨國旅行記帳需求，建議支援

Q2: 預算功能是否必要？
- 每月預算設定
- 超支警告

Q3: 報表匯出功能？
- PDF 報表
- Excel 匯出
- 分享至其他 APP

Q4: OCR 發票掃描？
- 掃描發票自動辨識金額
- 需整合第三方 OCR API

請逐一回答，我將根據您的回覆產出 PRD/FRD。
```

#### 命令 2.2: 回答確認問題

```
回答如下：

Q1: 多幣別支援 → 第一版不需要，僅支援 TWD
Q2: 預算功能 → 需要，每月預算 + 超支警告
Q3: 報表匯出 → 需要 PDF 和分享功能
Q4: OCR 掃描 → v2.0 再考慮，第一版手動輸入

請繼續產出 PRD 和 FRD。
```

#### Claude Code 產出文檔：

```
✅ 需求確認完成

正在產出文檔...

📄 已創建: Docs/analysis/PRD_ExpenseTracker_v1.0.md
   - 產品概述
   - 目標使用者
   - 功能清單（20 個功能點）
   - 非功能需求（效能、安全、可用性）

📄 已創建: Docs/analysis/FRD_ExpenseTracker_v1.0.md
   - 功能詳細描述（F-001 ~ F-020）
   - 使用者互動流程
   - 資料模型定義
   - 業務規則

請檢閱文檔，確認無誤後我們進入下一階段。
```

---

### 階段 3: User Story & 架構設計（產出 SRD）

#### 命令 3.1: 啟動設計 Workflow

```
PRD/FRD 已確認，請進入階段 2：系統設計

請執行以下任務：
1. 基於 FRD 產出 User Stories（Epic → Feature → User Story → AC）
2. 設計 MVVM 架構
3. 繪製 C4 架構圖（Level 2-3）
4. 定義資料模型（Core Data Schema）

請載入 SD Architect Agent 並啟動 user-story-and-design workflow。
```

#### Claude Code 預期回應：

```
✅ 已載入 SD Architect (05.sd-architect-zh.yaml)
✅ 已啟動 user-story-and-design workflow

開始分析 FRD...

【第一步：Epic 拆解】

EPIC-001: 收支記錄管理
  ├─ Feature-001: 新增收支記錄
  ├─ Feature-002: 編輯收支記錄
  └─ Feature-003: 刪除收支記錄

EPIC-002: 分類管理
  ├─ Feature-004: 預設分類
  └─ Feature-005: 自訂分類

EPIC-003: 統計圖表
  ├─ Feature-006: 月度統計
  ├─ Feature-007: 分類占比
  └─ Feature-008: 趨勢分析

EPIC-004: 預算管理
  ├─ Feature-009: 設定月度預算
  └─ Feature-010: 超支警告

【第二步：User Story 拆解】

US-001: 記錄支出項目
  作為一個使用者
  我希望能快速記錄支出
  以便追蹤我的消費習慣

  Acceptance Criteria:
  AC-001-1: 使用者可選擇「支出」類型
  AC-001-2: 必須輸入金額（正數，最多兩位小數）
  AC-001-3: 必須選擇日期（預設今天）
  AC-001-4: 必須選擇分類（從預設或自訂分類選擇）
  AC-001-5: 可選輸入備註（最多 200 字）
  AC-001-6: 點擊「儲存」後立即更新首頁統計
  AC-001-7: 儲存失敗時顯示錯誤訊息

US-002: 記錄收入項目
  作為一個使用者
  我希望能記錄收入
  以便了解我的財務狀況

  Acceptance Criteria:
  AC-002-1: 使用者可選擇「收入」類型
  AC-002-2: 收入分類：薪資、獎金、投資、其他
  AC-002-3: 其他欄位與 US-001 相同

... (US-003 ~ US-020 省略)

正在產出 SRD...
```

#### 命令 3.2: 確認架構設計

```
User Stories 已確認，請繼續產出：
1. MVVM 架構設計
2. Core Data Schema
3. SwiftUI 頁面結構
```

#### Claude Code 產出：

```
【MVVM 架構設計】

📱 Views (SwiftUI)
├── ContentView.swift              # 主頁（Tab 容器）
├── TransactionListView.swift      # 收支清單
├── AddTransactionView.swift       # 新增/編輯收支
├── StatisticsView.swift           # 統計圖表
├── CategoryManagementView.swift   # 分類管理
└── SettingsView.swift             # 設定

🧠 ViewModels
├── TransactionViewModel.swift     # 收支業務邏輯
├── StatisticsViewModel.swift      # 統計計算邏輯
├── CategoryViewModel.swift        # 分類管理邏輯
└── SettingsViewModel.swift        # 設定邏輯

📦 Models (Core Data)
├── Transaction.swift              # 收支記錄實體
├── Category.swift                 # 分類實體
└── Budget.swift                   # 預算實體

🔧 Services
├── CoreDataManager.swift          # Core Data 管理
├── BiometricAuthService.swift     # Face/Touch ID
└── ExportService.swift            # PDF 匯出

【Core Data Schema】

Entity: Transaction
  - id: UUID (Primary Key)
  - amount: Decimal
  - type: String (enum: "income" | "expense")
  - category: Relationship → Category
  - date: Date
  - note: String (optional)
  - createdAt: Date
  - updatedAt: Date

Entity: Category
  - id: UUID (Primary Key)
  - name: String
  - icon: String (SF Symbol name)
  - color: String (hex color)
  - type: String (enum: "income" | "expense")
  - isSystem: Bool (預設分類不可刪除)
  - transactions: Relationship → [Transaction]

Entity: Budget
  - id: UUID (Primary Key)
  - month: String (YYYY-MM)
  - amount: Decimal
  - category: Relationship → Category (optional)

📄 已創建: Docs/planning/SRD_ExpenseTracker_v1.0.md
📄 已創建: Docs/planning/UserStories_Sprint1.md
📄 已創建: Docs/planning/Architecture_Design.md

請檢閱，確認後進入 API 設計階段。
```

---

### 階段 4: API 規格設計（v2.0 後端準備）

#### 命令 4.1: 設計 RESTful API

```
SRD 已確認。

雖然 v1.0 使用 Core Data 本地儲存，但請預先設計 v2.0 的後端 API 規格，以便未來擴展。

請使用 api-specification-generation workflow 設計：

1. 使用者認證 API
   - 註冊、登入、登出
   - JWT Token 機制

2. 收支記錄 API
   - CRUD 操作
   - 分頁查詢
   - 依日期範圍篩選

3. 分類管理 API
   - 取得系統預設分類
   - CRUD 自訂分類

4. 統計查詢 API
   - 月度統計
   - 分類統計
   - 趨勢分析

5. 預算管理 API
   - CRUD 預算
   - 超支警告查詢

請依照 API_Specification_Template.md 格式產出。
```

#### Claude Code 產出：

```
✅ 已啟動 api-specification-generation workflow

正在設計 RESTful API...

【API 規格概覽】

Base URL: https://api.expensetracker.com/v1

認證方式: Bearer Token (JWT)

Endpoints:
1. POST   /auth/register          # 註冊
2. POST   /auth/login             # 登入
3. POST   /auth/logout            # 登出
4. GET    /transactions           # 查詢收支（分頁）
5. POST   /transactions           # 新增收支
6. GET    /transactions/{id}      # 取得單筆收支
7. PUT    /transactions/{id}      # 更新收支
8. DELETE /transactions/{id}      # 刪除收支
9. GET    /categories             # 取得分類清單
10. POST   /categories            # 新增自訂分類
11. PUT    /categories/{id}       # 更新分類
12. DELETE /categories/{id}       # 刪除分類
13. GET    /statistics/monthly    # 月度統計
14. GET    /statistics/category   # 分類統計
15. GET    /budgets               # 取得預算清單
16. POST   /budgets               # 新增預算
17. PUT    /budgets/{id}          # 更新預算
18. DELETE /budgets/{id}          # 刪除預算

【範例：POST /transactions】

Request:
POST /api/v1/transactions
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

Body:
{
  "type": "expense",
  "amount": 350.00,
  "category_id": "cat-food-001",
  "date": "2025-12-15",
  "note": "午餐便當"
}

Response (201 Created):
{
  "transaction_id": "txn-uuid-12345",
  "type": "expense",
  "amount": 350.00,
  "category": {
    "id": "cat-food-001",
    "name": "飲食",
    "icon": "fork.knife",
    "color": "#FF6B6B"
  },
  "date": "2025-12-15",
  "note": "午餐便當",
  "created_at": "2025-12-15T12:30:00Z"
}

Error Response (400 Bad Request):
{
  "error": "INVALID_AMOUNT",
  "message": "金額必須為正數",
  "details": {
    "field": "amount",
    "value": -100
  }
}

📄 已創建: Docs/planning/api/API_Auth_Login.md
📄 已創建: Docs/planning/api/API_Transactions_CRUD.md
📄 已創建: Docs/planning/api/API_Categories_Management.md
📄 已創建: Docs/planning/api/API_Statistics_Query.md
📄 已創建: Docs/planning/api/API_Budgets_Management.md
📄 已創建: Docs/planning/api/API_Index.md

API 設計完成，請檢閱。
```

---

### 階段 5: Xcode 專案實作

#### 命令 5.1: 建立 Xcode 專案結構

```
設計階段已完成，現在進入實作階段。

請協助我建立 Xcode 專案結構：

專案名稱：ExpenseTracker
Bundle ID: com.yourcompany.expensetracker
最低版本：iOS 16.0
架構：MVVM

目錄結構：
ExpenseTracker/
├── App/
│   ├── ExpenseTrackerApp.swift      # App Entry Point
│   └── ContentView.swift            # Main Tab View
├── Models/
│   ├── CoreData/
│   │   ├── ExpenseTracker.xcdatamodeld
│   │   ├── Transaction+CoreData.swift
│   │   ├── Category+CoreData.swift
│   │   └── Budget+CoreData.swift
│   └── Enums/
│       ├── TransactionType.swift
│       └── CategoryIcon.swift
├── ViewModels/
│   ├── TransactionViewModel.swift
│   ├── StatisticsViewModel.swift
│   ├── CategoryViewModel.swift
│   └── SettingsViewModel.swift
├── Views/
│   ├── Transactions/
│   │   ├── TransactionListView.swift
│   │   ├── AddTransactionView.swift
│   │   └── TransactionRowView.swift
│   ├── Statistics/
│   │   ├── StatisticsView.swift
│   │   ├── MonthlyChartView.swift
│   │   └── CategoryPieChartView.swift
│   ├── Categories/
│   │   └── CategoryManagementView.swift
│   └── Settings/
│       └── SettingsView.swift
├── Services/
│   ├── CoreDataManager.swift
│   ├── BiometricAuthService.swift
│   └── ExportService.swift
└── Utils/
    ├── Extensions/
    │   ├── Date+Extensions.swift
    │   └── Decimal+Extensions.swift
    └── Constants.swift

請先產出檔案結構說明，我會在 Xcode 手動建立專案，然後您再提供程式碼。
```

#### Claude Code 回應：

```
✅ 已理解專案結構

【建立 Xcode 專案步驟】

1. 打開 Xcode
2. File → New → Project
3. 選擇「iOS」→「App」
4. 設定：
   - Product Name: ExpenseTracker
   - Team: (選擇您的開發團隊)
   - Organization Identifier: com.yourcompany
   - Interface: SwiftUI
   - Language: Swift
   - Storage: Core Data ✅ (勾選)
5. 儲存至：~/Projects/ExpenseTrackerApp/iOS/

【建立目錄結構】

在 Xcode Navigator 中：
1. 右鍵點擊「ExpenseTracker」群組
2. New Group → 命名為「Models」
3. 重複步驟創建所有群組

建立完成後請告訴我，我將提供程式碼。
```

#### 命令 5.2: 實作 Core Data Model

```
Xcode 專案已建立，目錄結構已完成。

請提供 Core Data Model 的實作：
1. Entity 定義（Transaction, Category, Budget）
2. Relationship 設定
3. CoreDataManager.swift 程式碼
```

#### Claude Code 產出：

```
✅ 開始產出 Core Data 實作

【步驟 1: 設定 Core Data Model】

打開 ExpenseTracker.xcdatamodeld，新增以下 Entities:

Entity: Transaction
屬性：
- id: UUID (Primary Key)
- amount: Decimal
- type: String
- date: Date
- note: String (Optional)
- createdAt: Date
- updatedAt: Date

關聯：
- category: Category (To One, Delete Rule: Nullify)

Entity: Category
屬性：
- id: UUID
- name: String
- icon: String
- color: String
- type: String
- isSystem: Boolean

關聯：
- transactions: Transaction (To Many, Delete Rule: Cascade)

Entity: Budget
屬性：
- id: UUID
- month: String
- amount: Decimal

關聯：
- category: Category (To One, Optional, Delete Rule: Nullify)

【步驟 2: CoreDataManager.swift】

```swift
// Models/CoreData/CoreDataManager.swift

import CoreData
import Foundation

class CoreDataManager {
    static let shared = CoreDataManager()

    private init() {}

    // MARK: - Core Data Stack

    lazy var persistentContainer: NSPersistentContainer = {
        let container = NSPersistentContainer(name: "ExpenseTracker")
        container.loadPersistentStores { description, error in
            if let error = error {
                fatalError("❌ Core Data 載入失敗: \(error)")
            }
        }
        return container
    }()

    var context: NSManagedObjectContext {
        return persistentContainer.viewContext
    }

    // MARK: - CRUD Operations

    func save() {
        if context.hasChanges {
            do {
                try context.save()
            } catch {
                print("❌ 儲存失敗: \(error.localizedDescription)")
            }
        }
    }

    // MARK: - Transaction Operations

    func createTransaction(
        amount: Decimal,
        type: TransactionType,
        category: Category,
        date: Date,
        note: String?
    ) -> Transaction {
        let transaction = Transaction(context: context)
        transaction.id = UUID()
        transaction.amount = NSDecimalNumber(decimal: amount)
        transaction.type = type.rawValue
        transaction.category = category
        transaction.date = date
        transaction.note = note
        transaction.createdAt = Date()
        transaction.updatedAt = Date()

        save()
        return transaction
    }

    func fetchTransactions(
        from startDate: Date? = nil,
        to endDate: Date? = nil
    ) -> [Transaction] {
        let request: NSFetchRequest<Transaction> = Transaction.fetchRequest()

        var predicates: [NSPredicate] = []

        if let start = startDate {
            predicates.append(NSPredicate(format: "date >= %@", start as NSDate))
        }

        if let end = endDate {
            predicates.append(NSPredicate(format: "date <= %@", end as NSDate))
        }

        if !predicates.isEmpty {
            request.predicate = NSCompoundPredicate(andPredicateWithSubpredicates: predicates)
        }

        request.sortDescriptors = [NSSortDescriptor(key: "date", ascending: false)]

        do {
            return try context.fetch(request)
        } catch {
            print("❌ 查詢失敗: \(error)")
            return []
        }
    }

    func deleteTransaction(_ transaction: Transaction) {
        context.delete(transaction)
        save()
    }

    // MARK: - Category Operations

    func fetchCategories(type: TransactionType? = nil) -> [Category] {
        let request: NSFetchRequest<Category> = Category.fetchRequest()

        if let type = type {
            request.predicate = NSPredicate(format: "type == %@", type.rawValue)
        }

        request.sortDescriptors = [NSSortDescriptor(key: "name", ascending: true)]

        do {
            return try context.fetch(request)
        } catch {
            print("❌ 查詢分類失敗: \(error)")
            return []
        }
    }

    func createDefaultCategories() {
        // 預設支出分類
        let expenseCategories = [
            ("飲食", "fork.knife", "#FF6B6B"),
            ("交通", "car.fill", "#4ECDC4"),
            ("娛樂", "gamecontroller.fill", "#95E1D3"),
            ("購物", "cart.fill", "#F38181"),
            ("醫療", "cross.case.fill", "#AA96DA"),
            ("教育", "book.fill", "#FCBAD3"),
        ]

        for (name, icon, color) in expenseCategories {
            let category = Category(context: context)
            category.id = UUID()
            category.name = name
            category.icon = icon
            category.color = color
            category.type = TransactionType.expense.rawValue
            category.isSystem = true
        }

        // 預設收入分類
        let incomeCategories = [
            ("薪資", "banknote.fill", "#6BCF7F"),
            ("獎金", "gift.fill", "#FFD93D"),
            ("投資", "chart.line.uptrend.xyaxis", "#6BCFCF"),
        ]

        for (name, icon, color) in incomeCategories {
            let category = Category(context: context)
            category.id = UUID()
            category.name = name
            category.icon = icon
            category.color = color
            category.type = TransactionType.income.rawValue
            category.isSystem = true
        }

        save()
    }
}

// MARK: - Enums

enum TransactionType: String, CaseIterable {
    case income = "income"
    case expense = "expense"

    var displayName: String {
        switch self {
        case .income: return "收入"
        case .expense: return "支出"
        }
    }
}
```

已儲存程式碼，請複製至 Xcode。

接下來請告訴我要實作哪個 View 或 ViewModel？
```

#### 命令 5.3: 實作第一個 User Story (US-001)

```
請實作 US-001: 記錄支出項目

根據 AC-001-1 ~ AC-001-7，請提供：
1. TransactionViewModel.swift
2. AddTransactionView.swift
3. 表單驗證邏輯
```

#### Claude Code 產出：

```
✅ 開始實作 US-001

【TransactionViewModel.swift】

```swift
// ViewModels/TransactionViewModel.swift

import Foundation
import Combine

class TransactionViewModel: ObservableObject {
    @Published var transactions: [Transaction] = []
    @Published var amount: String = ""
    @Published var selectedType: TransactionType = .expense
    @Published var selectedCategory: Category?
    @Published var selectedDate: Date = Date()
    @Published var note: String = ""
    @Published var showError: Bool = false
    @Published var errorMessage: String = ""

    private let coreDataManager = CoreDataManager.shared

    init() {
        fetchTransactions()
    }

    // MARK: - Fetch

    func fetchTransactions(from startDate: Date? = nil, to endDate: Date? = nil) {
        transactions = coreDataManager.fetchTransactions(from: startDate, to: endDate)
    }

    // MARK: - Create (AC-001-1 ~ AC-001-7)

    func saveTransaction() -> Bool {
        // AC-001-2: 驗證金額
        guard let amountDecimal = Decimal(string: amount),
              amountDecimal > 0 else {
            showErrorAlert("金額必須為正數")
            return false
        }

        // AC-001-4: 驗證分類
        guard let category = selectedCategory else {
            showErrorAlert("請選擇分類")
            return false
        }

        // AC-001-6: 儲存
        let transaction = coreDataManager.createTransaction(
            amount: amountDecimal,
            type: selectedType,
            category: category,
            date: selectedDate,
            note: note.isEmpty ? nil : note
        )

        // AC-001-6: 立即更新統計
        fetchTransactions()

        // 重置表單
        resetForm()

        return true
    }

    // MARK: - Delete

    func deleteTransaction(_ transaction: Transaction) {
        coreDataManager.deleteTransaction(transaction)
        fetchTransactions()
    }

    // MARK: - Validation (AC-001-2, AC-001-5)

    func validateAmount(_ input: String) -> Bool {
        // 只允許數字和小數點
        let regex = "^[0-9]*\\.?[0-9]{0,2}$"
        return NSPredicate(format: "SELF MATCHES %@", regex).evaluate(with: input)
    }

    func validateNote(_ input: String) -> Bool {
        // AC-001-5: 最多 200 字
        return input.count <= 200
    }

    // MARK: - Helpers

    private func showErrorAlert(_ message: String) {
        // AC-001-7: 顯示錯誤訊息
        errorMessage = message
        showError = true
    }

    private func resetForm() {
        amount = ""
        selectedDate = Date()
        note = ""
    }
}
```

【AddTransactionView.swift】

```swift
// Views/Transactions/AddTransactionView.swift

import SwiftUI

struct AddTransactionView: View {
    @Environment(\.dismiss) var dismiss
    @StateObject private var viewModel = TransactionViewModel()
    @FetchRequest(
        sortDescriptors: [NSSortDescriptor(keyPath: \Category.name, ascending: true)],
        animation: .default
    ) private var categories: FetchedResults<Category>

    var body: some View {
        NavigationView {
            Form {
                // AC-001-1: 選擇類型
                Section("類型") {
                    Picker("交易類型", selection: $viewModel.selectedType) {
                        ForEach(TransactionType.allCases, id: \.self) { type in
                            Text(type.displayName).tag(type)
                        }
                    }
                    .pickerStyle(.segmented)
                }

                // AC-001-2: 輸入金額
                Section("金額") {
                    HStack {
                        Text("NT$")
                            .foregroundColor(.secondary)
                        TextField("0", text: $viewModel.amount)
                            .keyboardType(.decimalPad)
                            .onChange(of: viewModel.amount) { newValue in
                                // 即時驗證
                                if !viewModel.validateAmount(newValue) {
                                    viewModel.amount = String(newValue.dropLast())
                                }
                            }
                    }
                }

                // AC-001-3: 選擇日期
                Section("日期") {
                    DatePicker(
                        "日期",
                        selection: $viewModel.selectedDate,
                        displayedComponents: .date
                    )
                }

                // AC-001-4: 選擇分類
                Section("分類") {
                    Picker("選擇分類", selection: $viewModel.selectedCategory) {
                        Text("請選擇").tag(nil as Category?)
                        ForEach(filteredCategories, id: \.self) { category in
                            HStack {
                                Image(systemName: category.icon ?? "")
                                    .foregroundColor(Color(hex: category.color ?? "#000000"))
                                Text(category.name ?? "")
                            }
                            .tag(category as Category?)
                        }
                    }
                }

                // AC-001-5: 輸入備註
                Section("備註（選填）") {
                    TextEditor(text: $viewModel.note)
                        .frame(height: 100)
                        .onChange(of: viewModel.note) { newValue in
                            if !viewModel.validateNote(newValue) {
                                viewModel.note = String(newValue.prefix(200))
                            }
                        }

                    Text("\(viewModel.note.count) / 200")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
            }
            .navigationTitle("新增記錄")
            .toolbar {
                ToolbarItem(placement: .navigationBarLeading) {
                    Button("取消") {
                        dismiss()
                    }
                }

                ToolbarItem(placement: .navigationBarTrailing) {
                    Button("儲存") {
                        if viewModel.saveTransaction() {
                            dismiss()
                        }
                    }
                    .disabled(!isFormValid)
                }
            }
            // AC-001-7: 錯誤提示
            .alert("錯誤", isPresented: $viewModel.showError) {
                Button("確定", role: .cancel) {}
            } message: {
                Text(viewModel.errorMessage)
            }
        }
    }

    // MARK: - Computed Properties

    private var filteredCategories: [Category] {
        categories.filter { $0.type == viewModel.selectedType.rawValue }
    }

    private var isFormValid: Bool {
        !viewModel.amount.isEmpty &&
        viewModel.selectedCategory != nil &&
        Decimal(string: viewModel.amount) != nil
    }
}

// MARK: - Preview

struct AddTransactionView_Previews: PreviewProvider {
    static var previews: some View {
        AddTransactionView()
            .environment(\.managedObjectContext, CoreDataManager.shared.context)
    }
}

// MARK: - Color Extension

extension Color {
    init(hex: String) {
        let hex = hex.trimmingCharacters(in: CharacterSet.alphanumerics.inverted)
        var int: UInt64 = 0
        Scanner(string: hex).scanHexInt64(&int)
        let a, r, g, b: UInt64
        switch hex.count {
        case 6: // RGB
            (a, r, g, b) = (255, int >> 16, int >> 8 & 0xFF, int & 0xFF)
        default:
            (a, r, g, b) = (255, 0, 0, 0)
        }
        self.init(
            .sRGB,
            red: Double(r) / 255,
            green: Double(g) / 255,
            blue:  Double(b) / 255,
            opacity: Double(a) / 255
        )
    }
}
```

✅ US-001 實作完成

【測試檢查清單】
- [ ] AC-001-1: 可選擇「支出」類型
- [ ] AC-001-2: 金額驗證（正數、兩位小數）
- [ ] AC-001-3: 日期選擇（預設今天）
- [ ] AC-001-4: 分類選擇（必填）
- [ ] AC-001-5: 備註輸入（選填、200字限制）
- [ ] AC-001-6: 儲存後更新統計
- [ ] AC-001-7: 錯誤訊息顯示

請在 Xcode 編譯並測試，確認所有 AC 已滿足。

接下來要實作哪個 User Story？
```

---

### 階段 6: 測試與驗證

#### 命令 6.1: 產生測試用例

```
US-001 實作已完成，請產生對應的測試用例：

1. Unit Test (TransactionViewModelTests.swift)
   - 測試金額驗證邏輯
   - 測試備註字數限制
   - 測試儲存功能

2. UI Test (AddTransactionUITests.swift)
   - 測試表單填寫流程
   - 測試錯誤提示

請使用 XCTest 框架。
```

#### Claude Code 產出：

```
✅ 產生測試用例

【TransactionViewModelTests.swift】

```swift
// ExpenseTrackerTests/TransactionViewModelTests.swift

import XCTest
@testable import ExpenseTracker

final class TransactionViewModelTests: XCTestCase {

    var viewModel: TransactionViewModel!

    override func setUp() {
        super.setUp()
        viewModel = TransactionViewModel()
    }

    override func tearDown() {
        viewModel = nil
        super.tearDown()
    }

    // MARK: - AC-001-2: 金額驗證測試

    func testValidateAmount_ValidDecimal() {
        XCTAssertTrue(viewModel.validateAmount("100.50"))
        XCTAssertTrue(viewModel.validateAmount("0.99"))
        XCTAssertTrue(viewModel.validateAmount("1234567.89"))
    }

    func testValidateAmount_InvalidDecimal() {
        XCTAssertFalse(viewModel.validateAmount("100.999")) // 超過兩位小數
        XCTAssertFalse(viewModel.validateAmount("abc"))      // 非數字
        XCTAssertFalse(viewModel.validateAmount("-50"))      // 負數
    }

    // AC-001-5: 備註驗證測試

    func testValidateNote_WithinLimit() {
        let note = String(repeating: "a", count: 200)
        XCTAssertTrue(viewModel.validateNote(note))
    }

    func testValidateNote_ExceedLimit() {
        let note = String(repeating: "a", count: 201)
        XCTAssertFalse(viewModel.validateNote(note))
    }

    // AC-001-6: 儲存功能測試

    func testSaveTransaction_Success() {
        viewModel.amount = "100.00"
        viewModel.selectedType = .expense
        // 需要設定 selectedCategory (mock)

        let result = viewModel.saveTransaction()
        XCTAssertTrue(result)
        XCTAssertEqual(viewModel.amount, "") // 表單應重置
    }

    func testSaveTransaction_FailInvalidAmount() {
        viewModel.amount = ""

        let result = viewModel.saveTransaction()
        XCTAssertFalse(result)
        XCTAssertTrue(viewModel.showError)
        XCTAssertEqual(viewModel.errorMessage, "金額必須為正數")
    }

    func testSaveTransaction_FailNoCategory() {
        viewModel.amount = "100.00"
        viewModel.selectedCategory = nil

        let result = viewModel.saveTransaction()
        XCTAssertFalse(result)
        XCTAssertTrue(viewModel.showError)
        XCTAssertEqual(viewModel.errorMessage, "請選擇分類")
    }
}
```

【執行測試】

在 Xcode:
1. Cmd + U (執行所有測試)
2. 或點擊測試方法旁的菱形圖示

預期結果: ✅ All Tests Passed
```

#### 命令 6.2: 執行一致性檢查

```
US-001 ~ US-003 已實作完成，請執行 document-consistency-check workflow：

檢查項目：
1. 實作是否符合 SRD 規格
2. 所有 AC 是否已滿足
3. Core Data Schema 是否與設計一致
4. UI 流程是否符合 FRD
```

#### Claude Code 產出：

```
✅ 已啟動 document-consistency-check workflow

正在驗證...

【一致性檢查報告】

檢查時間: 2025-12-15 14:30:00

1. ✅ SRD 規格符合度: 100%
   - MVVM 架構完整
   - 目錄結構符合設計
   - Core Data Schema 一致

2. ✅ Acceptance Criteria 滿足度: 100% (7/7)
   - AC-001-1: ✅ 可選擇「支出」類型
   - AC-001-2: ✅ 金額驗證（正數、兩位小數）
   - AC-001-3: ✅ 日期選擇（預設今天）
   - AC-001-4: ✅ 分類選擇（必填）
   - AC-001-5: ✅ 備註輸入（200字限制）
   - AC-001-6: ✅ 儲存後更新統計
   - AC-001-7: ✅ 錯誤訊息顯示

3. ✅ Core Data 一致性: 100%
   - Transaction Entity: ✅
   - Category Entity: ✅
   - Budget Entity: ✅
   - Relationships: ✅

4. ✅ UI 流程符合度: 100%
   - FRD F-001 功能完整實作
   - 使用者體驗符合設計

【潛在問題】
無

【建議】
1. 可考慮新增 loading 狀態指示
2. 建議新增單元測試覆蓋率（目標 >80%）

📄 已創建: Docs/reports/Consistency_Check_Report_Sprint1.md

驗證完成！可進入下一個 Sprint。
```

---

## 附錄：命令速查表

### Workflow 觸發命令

| Workflow | 命令 |
|----------|------|
| 初始化 | `請載入 AISDLC_SDD_v0.01/AISDLC_INIT.md` |
| 需求提取 | `請使用 unified-requirements-extraction workflow` |
| PRD/FRD 產出 | `請使用 requirements-validation-and-documentation workflow` |
| User Story 設計 | `請使用 user-story-and-design workflow` |
| API 規格設計 | `請使用 api-specification-generation workflow` |
| 一致性檢查 | `請執行 document-consistency-check workflow` |
| 需求變更管理 | `請使用 requirements-change-management workflow` |

### Agent 載入命令

| Agent | 檔案 | 命令 |
|-------|------|------|
| SA 系統分析師 | 04.sa-analyst-zh.yaml | `請載入 SA Agent` |
| BA 業務分析師 | 02.ba-business-analyst-zh.yaml | `請載入 BA Agent` |
| PM/PO | 03.pm-po-agent-zh.yaml | `請載入 PM Agent` |
| SD 架構師 | 05.sd-architect-zh.yaml | `請載入 SD Architect` |
| Developer | 06.dev-developer-zh.yaml | `請載入 Developer Agent` |
| QA 測試 | 07.qa-tester-zh.yaml | `請載入 QA Agent` |

### Scenario SOP

```
請使用 Greenfield SOP 引導完整開發流程
```

**Greenfield SOP 階段**:
1. 需求分析
2. 系統設計
3. API 設計
4. 實作規劃
5. 開發實作
6. 測試驗證
7. 部署準備
8. 文檔產出
9. 品質門檻驗證

---

## 完整開發時程建議

### Sprint 1 (2 週) - MVP
- US-001 ~ US-005: 核心記帳功能
- 產出: PRD, FRD, SRD, Core Data 實作

### Sprint 2 (2 週) - 統計功能
- US-006 ~ US-010: 統計圖表
- 產出: SwiftUI Charts 整合

### Sprint 3 (1 週) - 安全與優化
- US-011 ~ US-015: Face ID, 資料加密
- 產出: 安全功能實作

### Sprint 4 (1 週) - 測試與發布
- 完整測試
- App Store 準備
- 產出: TestFlight 版本

---

**文檔版本**: v1.0
**最後更新**: 2025-12-15
**作者**: AISDLC Framework Team
