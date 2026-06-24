# AISDLC 詳細實戰：舊專案維護 iOS 記帳 APP

**專案類型**: Brownfield (既有系統改造)
**開發環境**: Xcode + Cursor AI + Claude Code
**前端技術**: Swift + SwiftUI (MVVM)
**後端技術**: Python + FastAPI (可選)
**資料庫**: Core Data (本地) + PostgreSQL (後端)
**適用版本**: AISDLC-SDD v0.01+
**最後更新**: 2025-12-15


> **SDD v0.01 使用者提示**：本指南基於 AISDLC-SDD v0.01。使用 AISDLC-SDD v0.01 時，請同時參考對應場景的 SDD Enhancement 文件（`scenarios/{scenario}/SDD_{SCENARIO}_ENHANCEMENT.md`），並確認所有 SCG 閘門步驟已整合到您的工作流程中。

---
---

## 📋 目錄

1. [第一步：Xcode 專案路徑設定](#第一步xcode-專案路徑設定)
2. [第二步：AISDLC 框架安裝](#第二步aisdlc-框架安裝)
3. [第三步：Claude Code 完整維護流程](#第三步claude-code-完整維護流程)
4. [附錄：命令速查表](#附錄命令速查表)

---

## 第一步：Xcode 專案路徑設定

### 1.1 既有 Xcode 專案結構

**專案位置**: `~/Projects/ExpenseTrackerApp/`

```
ExpenseTrackerApp/
├── iOS/
│   └── ExpenseTracker/
│       ├── ExpenseTracker.xcodeproj
│       ├── ExpenseTracker/
│       │   ├── App/
│       │   │   └── ExpenseTrackerApp.swift
│       │   ├── Views/              # 舊 UI (部分 UIKit)
│       │   │   ├── MainViewController.swift  # ⚠️ UIKit
│       │   │   └── AddTransactionVC.swift    # ⚠️ UIKit
│       │   ├── Models/
│       │   │   └── Transaction.swift
│       │   ├── Data/
│       │   │   └── CoreDataStack.swift
│       │   └── Resources/
│       └── ExpenseTrackerTests/
└── Backend/                        # Python API (可選)
```

### 1.2 建立輔助目錄

```bash
cd ~/Projects/ExpenseTrackerApp

mkdir -p Docs/analysis
mkdir -p Docs/planning
mkdir -p Docs/planning/api
mkdir -p Docs/reports
mkdir -p Docs/legacy

ls -la
```

**完整結構**:
```
ExpenseTrackerApp/
├── iOS/ExpenseTracker/    # Xcode 專案 (既有)
├── Backend/              # Python API (可選)
├── Docs/                 # AISDLC 文檔
│   ├── analysis/
│   ├── planning/
│   ├── reports/
│   └── legacy/
└── AISDLC_SDD_v0.01/        # 步驟 2 安裝
```

### 1.3 開啟 Cursor AI

1. 打開 Cursor
2. `File` → `Open Folder...`
3. 選擇：`~/Projects/ExpenseTrackerApp`
4. 點擊「Open」

---

## 第二步：AISDLC 框架安裝

### 2.1 符號連結

```bash
cd ~/Projects/ExpenseTrackerApp
ln -s ~/Cursor_Project/AISDLC_ALL/AISDLC_v0.09 ./AISDLC_v0.09
ls -la AISDLC_SDD_v0.01/scenarios/brownfield/SOP.md
```

---

## 第三步：Claude Code 完整維護流程

### 階段 0: 啟動

按 `Cmd + Shift + P` → `Claude Code`

---

### 階段 1: 專案評估

#### 命令 1.1

```
請載入 AISDLC_SDD_v0.01/AISDLC_INIT.md

維護既有 iOS 記帳 APP，使用 Brownfield SOP。

背景：
- 舊架構：UIKit + MVC (部分)
- 需求：遷移至 SwiftUI + MVVM
- 技術債：無測試、部分硬編碼
- 新功能：預算管理、圖表統計、iCloud 同步

啟動階段 1：專案評估。
```

#### Claude Code 回應

```
✅ 已載入 Brownfield SOP

🔴 人工確認點 1

Q1: 專案規模？
- Swift 程式碼行數
- UIKit vs SwiftUI 比例
- Core Data 表格數

Q2: 技術債務？
- 單元測試覆蓋率
- 已知 Bug 數量

Q3: 維護時程？
```

#### 命令 1.2

```
Q1: 規模
- 程式碼：約 8,000 行 Swift
- UIKit: 70%, SwiftUI: 30%
- Core Data: 3 張表

Q2: 技術債
- 測試：0%
- Bug: 5 個

Q3: 時程
- 預計 8 週
- 可分階段

產出評估報告。
```

#### Claude Code 產出

```
✅ 專案評估完成

【健康度】⚠️ 中等（60/100）

【重構策略 (8 週)】

週 1-2: 架構重構
- MVVM 架構建立
- SwiftUI 遷移準備

週 3-4: UI 遷移
- UIKit → SwiftUI
- 核心功能遷移

週 5-6: 新功能
- 預算管理
- 統計圖表

週 7-8: 測試 & 優化
- 單元測試 (目標 60%)
- iCloud 同步

📄 Docs/legacy/Project_Assessment_Report.md
📄 Docs/planning/Refactoring_Strategy.md
```

---

### 階段 2: 舊系統分析

#### 命令 2.1

```
請使用 brownfield-system-analysis workflow 分析：

1. iOS/ExpenseTracker/Views/
2. iOS/ExpenseTracker/Models/
3. iOS/ExpenseTracker/Data/

產出：
- 既有功能清單
- 資料模型文檔
- UI 流程圖
```

#### Claude Code 產出

```
✅ 系統分析完成

【既有功能 (6 個)】

F-LEGACY-001: 新增收支 (UIKit)
F-LEGACY-002: 收支列表 (UIKit)
F-LEGACY-003: 編輯收支 (UIKit)
F-LEGACY-004: 刪除收支
F-LEGACY-005: 分類管理 (SwiftUI ✅)
F-LEGACY-006: 簡單統計 (文字)

【Core Data Schema】

```swift
// 舊實作
@objc(Transaction)
class Transaction: NSManagedObject {
    @NSManaged var id: UUID
    @NSManaged var amount: Double
    @NSManaged var type: String
    @NSManaged var date: Date
    @NSManaged var note: String?
}

// ⚠️ 問題
1. 缺少 Category 關聯
2. 無 createdAt/updatedAt
3. 無 iCloud 同步標記
```

📄 Docs/legacy/Existing_System_Analysis.md
📄 Docs/legacy/Data_Model_Documentation.md
```

#### 命令 2.2

```
整合新需求並產出 PRD/FRD：

新需求：
1. 預算管理
   - 月度總預算
   - 分類預算
   - 超支警告

2. 統計圖表
   - 折線圖（月度趨勢）
   - 圓餅圖（分類占比）
   - 使用 Swift Charts

3. iCloud 同步
   - CloudKit 整合
   - 衝突處理

保留所有既有功能。
```

#### Claude Code 產出

```
✅ 需求分析完成

【功能對照表】

| 功能 | 狀態 | 技術升級 |
|------|------|---------|
| F-001 新增收支 | 🔄 重構 | UIKit → SwiftUI |
| F-002 收支列表 | 🔄 重構 | UIKit → SwiftUI |
| F-003 編輯收支 | 🔄 重構 | UIKit → SwiftUI |
| F-004 刪除收支 | ✅ 保留 | 邏輯遷移 |
| F-005 分類管理 | ✅ 保留 | 已是 SwiftUI |
| F-006 簡單統計 | 🔄 升級 | 圖表化 |
| F-007 **預算管理** | 🆕 新功能 | 全新開發 |
| F-008 **統計圖表** | 🆕 新功能 | Swift Charts |
| F-009 **iCloud 同步** | 🆕 新功能 | CloudKit |

📄 Docs/analysis/PRD_ExpenseTracker_v2.0.md
📄 Docs/analysis/FRD_ExpenseTracker_v2.0.md
```

---

### 階段 3: 架構設計

#### 命令 3.1

```
設計 v2.0 新架構：

目標：
- 100% SwiftUI
- MVVM 架構
- Combine (響應式)
- Core Data + CloudKit

產出：
1. 新目錄結構
2. MVVM 設計
3. Core Data Schema 更新
4. 遷移計畫
```

#### Claude Code 產出

```
✅ 架構設計完成

【新目錄結構】

```
ExpenseTracker/
├── App/
│   └── ExpenseTrackerApp.swift
│
├── Core/
│   ├── Data/
│   │   ├── Models/
│   │   │   ├── Transaction.swift       # 更新
│   │   │   ├── Category.swift
│   │   │   └── Budget.swift            # 🆕
│   │   ├── CoreData/
│   │   │   ├── ExpenseTracker.xcdatamodeld
│   │   │   ├── CoreDataManager.swift
│   │   │   └── CloudKitManager.swift   # 🆕
│   │   └── Repositories/               # 🆕
│   │       ├── TransactionRepository.swift
│   │       └── BudgetRepository.swift
│   │
│   ├── Domain/                         # 🆕
│   │   └── UseCases/
│   │       ├── GetTransactionsUseCase.swift
│   │       └── SaveTransactionUseCase.swift
│   │
│   └── Presentation/
│       ├── ViewModels/                 # 🆕 MVVM
│       │   ├── TransactionListViewModel.swift
│       │   ├── AddTransactionViewModel.swift
│       │   ├── BudgetViewModel.swift   # 🆕
│       │   └── StatisticsViewModel.swift # 🆕
│       │
│       └── Views/                      # SwiftUI
│           ├── Transaction/
│           │   ├── TransactionListView.swift
│           │   └── AddTransactionView.swift
│           ├── Budget/                 # 🆕
│           │   └── BudgetView.swift
│           ├── Statistics/             # 🆕
│           │   ├── StatisticsView.swift
│           │   ├── LineChartView.swift
│           │   └── PieChartView.swift
│           └── Components/
│               ├── TransactionRow.swift
│               └── BudgetCard.swift
│
└── Utils/
    ├── Extensions/
    └── Constants.swift
```

【Core Data Schema 更新】

```swift
// 更新後的 Transaction Entity

@objc(Transaction)
class Transaction: NSManagedObject {
    @NSManaged var id: UUID
    @NSManaged var amount: Decimal        // Double → Decimal
    @NSManaged var type: String
    @NSManaged var date: Date
    @NSManaged var note: String?
    @NSManaged var category: Category     // 🆕 關聯
    @NSManaged var createdAt: Date        // 🆕
    @NSManaged var updatedAt: Date        // 🆕
    @NSManaged var isSynced: Bool         // 🆕 CloudKit
}

// 新增 Budget Entity

@objc(Budget)
class Budget: NSManagedObject {
    @NSManaged var id: UUID
    @NSManaged var month: String          // "YYYY-MM"
    @NSManaged var totalAmount: Decimal
    @NSManaged var category: Category?    // Optional
    @NSManaged var createdAt: Date
}
```

【遷移計畫 (8 週)】

週 1-2: MVVM 基礎
- Repository Pattern
- ViewModel 建立
- Combine 整合

週 3-4: UI 遷移
- TransactionListView (SwiftUI)
- AddTransactionView (SwiftUI)

週 5-6: 新功能
- BudgetView
- StatisticsView (Swift Charts)

週 7-8: CloudKit & 測試
- iCloud 同步
- 單元測試

📄 Docs/planning/SRD_ExpenseTracker_v2.0.md
📄 Docs/planning/Migration_Plan.md
```

---

### 階段 4: 實作（週 1-2）

#### 命令 4.1

```
實作週 1-2：MVVM 基礎架構

任務：
1. TransactionRepository
2. TransactionListViewModel
3. Core Data 更新

提供完整 Swift 程式碼。
```

#### Claude Code 產出

```
✅ MVVM 基礎架構

【TransactionRepository.swift】

```swift
// Core/Data/Repositories/TransactionRepository.swift

import Foundation
import CoreData
import Combine

protocol TransactionRepositoryProtocol {
    func fetchAll() -> AnyPublisher<[Transaction], Error>
    func save(_ transaction: Transaction) -> AnyPublisher<Void, Error>
    func delete(_ transaction: Transaction) -> AnyPublisher<Void, Error>
}

class TransactionRepository: TransactionRepositoryProtocol {
    private let coreDataManager: CoreDataManager

    init(coreDataManager: CoreDataManager = .shared) {
        self.coreDataManager = coreDataManager
    }

    func fetchAll() -> AnyPublisher<[Transaction], Error> {
        return Future { promise in
            let context = self.coreDataManager.viewContext
            let request: NSFetchRequest<Transaction> = Transaction.fetchRequest()
            request.sortDescriptors = [NSSortDescriptor(key: "date", ascending: false)]

            do {
                let transactions = try context.fetch(request)
                promise(.success(transactions))
            } catch {
                promise(.failure(error))
            }
        }
        .eraseToAnyPublisher()
    }

    func save(_ transaction: Transaction) -> AnyPublisher<Void, Error> {
        return Future { promise in
            let context = self.coreDataManager.viewContext
            transaction.updatedAt = Date()

            do {
                try context.save()
                promise(.success(()))
            } catch {
                promise(.failure(error))
            }
        }
        .eraseToAnyPublisher()
    }

    func delete(_ transaction: Transaction) -> AnyPublisher<Void, Error> {
        return Future { promise in
            let context = self.coreDataManager.viewContext
            context.delete(transaction)

            do {
                try context.save()
                promise(.success(()))
            } catch {
                promise(.failure(error))
            }
        }
        .eraseToAnyPublisher()
    }
}
```

【TransactionListViewModel.swift】

```swift
// Core/Presentation/ViewModels/TransactionListViewModel.swift

import Foundation
import Combine

class TransactionListViewModel: ObservableObject {
    @Published var transactions: [Transaction] = []
    @Published var isLoading: Bool = false
    @Published var errorMessage: String?

    private let repository: TransactionRepositoryProtocol
    private var cancellables = Set<AnyCancellable>()

    init(repository: TransactionRepositoryProtocol = TransactionRepository()) {
        self.repository = repository
        loadTransactions()
    }

    func loadTransactions() {
        isLoading = true

        repository.fetchAll()
            .receive(on: DispatchQueue.main)
            .sink { [weak self] completion in
                self?.isLoading = false

                if case .failure(let error) = completion {
                    self?.errorMessage = error.localizedDescription
                }
            } receiveValue: { [weak self] transactions in
                self?.transactions = transactions
            }
            .store(in: &cancellables)
    }

    func deleteTransaction(_ transaction: Transaction) {
        repository.delete(transaction)
            .receive(on: DispatchQueue.main)
            .sink { completion in
                if case .failure(let error) = completion {
                    print("Delete error: \(error)")
                }
            } receiveValue: { [weak self] _ in
                self?.loadTransactions()
            }
            .store(in: &cancellables)
    }
}
```

【TransactionListView.swift】

```swift
// Core/Presentation/Views/Transaction/TransactionListView.swift

import SwiftUI

struct TransactionListView: View {
    @StateObject private var viewModel = TransactionListViewModel()
    @State private var showAddSheet = false

    var body: some View {
        NavigationStack {
            ZStack {
                if viewModel.isLoading {
                    ProgressView()
                } else {
                    List {
                        ForEach(viewModel.transactions, id: \.id) { transaction in
                            TransactionRow(transaction: transaction)
                        }
                        .onDelete { indexSet in
                            indexSet.forEach { index in
                                let transaction = viewModel.transactions[index]
                                viewModel.deleteTransaction(transaction)
                            }
                        }
                    }
                }
            }
            .navigationTitle("交易記錄")
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button {
                        showAddSheet = true
                    } label: {
                        Image(systemName: "plus")
                    }
                }
            }
            .sheet(isPresented: $showAddSheet) {
                AddTransactionView()
            }
            .alert("錯誤", isPresented: .constant(viewModel.errorMessage != nil)) {
                Button("確定") {
                    viewModel.errorMessage = nil
                }
            } message: {
                if let error = viewModel.errorMessage {
                    Text(error)
                }
            }
        }
    }
}
```

✅ 週 1-2 完成

測試：
- [ ] Repository 可正常讀寫
- [ ] ViewModel 狀態更新正確
- [ ] SwiftUI View 正常顯示

繼續週 3-4：UI 遷移？
```

---

### 階段 5: 測試

#### 命令 5.1

```
產生 TransactionViewModel 單元測試：
使用 XCTest + Combine
```

#### 命令 5.2

```
執行 document-consistency-check workflow：
驗證新架構符合 SRD
```

---

## 附錄：命令速查表

### Brownfield Workflow

| Workflow | 命令 |
|----------|------|
| 專案評估 | `請使用 brownfield-system-analysis workflow` |
| 架構設計 | `請使用 user-story-and-design workflow` |
| 一致性檢查 | `請執行 document-consistency-check workflow` |

### 8 週時程

- **週 1-2**: MVVM 基礎 (Repository + ViewModel)
- **週 3-4**: UI 遷移 (UIKit → SwiftUI)
- **週 5-6**: 新功能 (預算 + 圖表)
- **週 7-8**: CloudKit + 測試

---

**更新**: 2025-12-15 | **版本**: v0.01
