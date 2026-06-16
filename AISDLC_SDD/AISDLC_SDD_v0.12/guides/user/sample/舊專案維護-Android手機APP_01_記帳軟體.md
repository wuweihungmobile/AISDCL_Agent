# AISDLC 詳細實戰：舊專案維護 Android 記帳 APP

**專案類型**: Brownfield (既有系統改造)
**開發環境**: Android Studio + Cursor AI + Claude Code
**前端技術**: Kotlin + Jetpack Compose (MVVM)
**依賴注入**: Hilt/Dagger
**後端技術**: Python + FastAPI (可選)
**資料庫**: Room (本地) + PostgreSQL (後端)
**適用版本**: AISDLC-SDD v0.01+
**最後更新**: 2025-12-15

> **SDD v0.01 使用者提示**：本指南基於 AISDLC-SDD v0.01。使用 AISDLC-SDD v0.01 時，請同時參考對應場景的 SDD Enhancement 文件（`scenarios/{scenario}/SDD_{SCENARIO}_ENHANCEMENT.md`），並確認所有 SCG 閘門步驟已整合到您的工作流程中。

---

---

## 📋 完整目錄

1. [第一步：Cursor AI 專案路徑設定](#第一步cursor-ai-專案路徑設定)
2. [第二步：AISDLC 框架安裝](#第二步aisdlc-框架安裝)
3. [第三步：Claude Code 完整維護流程](#第三步claude-code-完整維護流程)
4. [附錄：命令速查表](#附錄命令速查表)

---

## 第一步：Cursor AI 專案路徑設定

### 1.1 假設既有專案結構

**既有專案位置**: `~/Projects/ExpenseTrackerAndroid/`

```
ExpenseTrackerAndroid/
├── app/                           # Android 主模組
│   ├── src/
│   │   ├── main/
│   │   │   ├── java/com/yourcompany/expensetracker/
│   │   │   │   ├── MainActivity.kt
│   │   │   │   ├── data/           # 舊資料層（需重構）
│   │   │   │   ├── ui/             # 舊 UI（可能是 XML）
│   │   │   │   └── utils/
│   │   │   ├── res/
│   │   │   └── AndroidManifest.xml
│   │   └── test/
│   ├── build.gradle.kts
│   └── proguard-rules.pro
├── gradle/
├── build.gradle.kts
├── settings.gradle.kts
└── README.md
```

### 1.2 建立輔助目錄

```bash
# 在專案根目錄執行
cd ~/Projects/ExpenseTrackerAndroid

# 建立 AISDLC 文檔目錄
mkdir -p Docs/analysis           # 需求分析
mkdir -p Docs/planning           # 重構規劃
mkdir -p Docs/planning/api       # API 規格
mkdir -p Docs/reports            # 驗證報告
mkdir -p Docs/legacy             # 舊系統文檔
mkdir -p Backend                 # Python API (可選)

# 驗證
ls -la
```

**完整結構**:
```
ExpenseTrackerAndroid/
├── app/                    # 🎯 Android 專案（既有）
├── Backend/               # 🔧 Python FastAPI (可選)
├── Docs/                  # 📄 AISDLC 文檔
│   ├── analysis/
│   ├── planning/
│   ├── reports/
│   └── legacy/            # 舊系統文檔
├── AISDLC_SDD_v0.01/         # 🔴 步驟 2 安裝
└── [既有檔案]
```

### 1.3 開啟 Cursor AI

**步驟**:
1. 打開 Cursor 應用程式
2. `File` → `Open Folder...`
3. 選擇：`~/Projects/ExpenseTrackerAndroid` （**專案根目錄**）
4. 點擊「Open」

**驗證**: Cursor 左側應顯示 `app/`, `Docs/`, `gradle/`

---

## 第二步：AISDLC 框架安裝

### 2.1 方法一：符號連結（推薦）

```bash
cd ~/Projects/ExpenseTrackerAndroid

# 創建符號連結
ln -s ~/Cursor_Project/AISDLC_ALL/AISDLC_v0.09 ./AISDLC_v0.09

# 驗證
ls -la AISDLC_SDD_v0.01/AISDLC_INIT.md
```

### 2.2 方法二：完整拷貝

```bash
cd ~/Projects/ExpenseTrackerAndroid
cp -r ~/Cursor_Project/AISDLC_ALL/AISDLC_v0.09 .
```

### 2.3 驗證安裝

```bash
test -f AISDLC_SDD_v0.01/AISDLC_INIT.md && echo "✅ 安裝成功"
ls AISDLC_SDD_v0.01/scenarios/brownfield/
```

---

## 第三步：Claude Code 完整維護流程

### 階段 0: 啟動 Claude Code

在 Cursor 按 `Cmd + Shift + P` → 輸入 `Claude Code` → 開啟

---

### 階段 1: 初始化 & 專案評估

#### 命令 1.1: 載入 Brownfield SOP

```
請載入 AISDLC_SDD_v0.01/AISDLC_INIT.md

我要維護一個既有的 Android 記帳 APP，請使用 Brownfield SOP 引導我。

專案背景：
- 既有 Android APP (Kotlin)
- 舊架構：部分使用 XML View，部分使用 Compose
- 需求：全面遷移至 Jetpack Compose + MVVM + Hilt
- 舊資料層需要重構（目前直接操作 SQLite）
- 需要新增：預算功能、圖表統計、雲端同步

請啟動 Brownfield 階段 1：專案評估。
```

#### Claude Code 預期回應：

```
✅ 已載入 AISDLC-SDD v0.01 框架
✅ 已載入 Brownfield SOP (scenarios/brownfield/SOP.md)

【Brownfield 階段 1: 專案評估】

我將協助您評估既有專案，請提供以下資訊：

🔴 人工確認點 1: 專案基本資訊

Q1: 專案規模？
- 總程式碼行數
- 模組數量
- 主要功能數量

Q2: 技術債務評估？
- 是否有單元測試？覆蓋率多少？
- 是否有技術文檔？
- 最近一次重大更新時間？

Q3: 維護目標？
- 效能優化
- 架構重構
- 新功能開發
- Bug 修復

Q4: 時程限制？
- 預計完成時間
- 是否可分階段進行

請逐一回答，我將產出「專案評估報告」。
```

#### 命令 1.2: 回答評估問題

```
回答如下：

Q1: 專案規模
- 程式碼：約 15,000 行 Kotlin
- 模組：1 個主模組
- 主要功能：8 個（記帳、分類、統計、設定等）

Q2: 技術債務
- 單元測試：無
- 技術文檔：僅有簡單 README
- 最後更新：6 個月前

Q3: 維護目標
- 優先：架構重構（XML → Compose + MVVM + Hilt）
- 次要：新增預算功能、統計圖表
- 最後：效能優化

Q4: 時程
- 預計 8 週
- 可分 4 個 Sprint

請產出評估報告並建議重構策略。
```

#### Claude Code 產出：

```
✅ 專案評估完成

【專案評估報告】

專案健康度: ⚠️ 中等（需要重構）

技術債務分析:
- 🔴 無單元測試（高風險）
- 🟡 文檔不足（中風險）
- 🟢 程式碼規模適中（可控）

【重構策略建議】

階段 1 (Sprint 1-2): 架構重構
- 引入 Hilt 依賴注入
- 建立 MVVM 架構層
- 遷移 Room Database
- 優先重構核心功能（記帳、分類）

階段 2 (Sprint 3): UI 現代化
- XML View → Jetpack Compose
- Material Design 3
- 響應式設計

階段 3 (Sprint 4): 新功能開發
- 預算管理
- 統計圖表（Vico Charts）
- 雲端同步準備

階段 4 (後續): 優化與測試
- 單元測試補充（目標覆蓋率 >60%）
- 效能優化
- 安全性強化

📄 已創建: Docs/legacy/Project_Assessment_Report.md
📄 已創建: Docs/planning/Refactoring_Strategy.md

請確認策略，我們將進入需求分析階段。
```

---

### 階段 2: 需求分析與文檔補充

#### 命令 2.1: 舊系統文檔化

```
請使用 brownfield-system-analysis workflow 分析既有系統：

請分析以下檔案並產出文檔：
1. app/src/main/java/com/yourcompany/expensetracker/MainActivity.kt
2. app/src/main/java/com/yourcompany/expensetracker/data/ （整個目錄）
3. app/src/main/java/com/yourcompany/expensetracker/ui/ （整個目錄）

產出：
- 既有功能清單
- 資料模型文檔
- UI 流程圖
- 依賴關係圖
```

#### Claude Code 預期回應：

```
✅ 已啟動 brownfield-system-analysis workflow

正在分析既有程式碼...

【分析結果】

既有功能清單 (8 個主要功能):
1. F-LEGACY-001: 新增收支記錄
2. F-LEGACY-002: 編輯收支記錄
3. F-LEGACY-003: 刪除收支記錄
4. F-LEGACY-004: 分類管理
5. F-LEGACY-005: 月度統計（簡單文字）
6. F-LEGACY-006: 設定頁面
7. F-LEGACY-007: 匯出 CSV
8. F-LEGACY-008: 備份/還原

資料模型 (3 個 Entity):
```kotlin
// 舊實作 (直接操作 SQLite)
data class Transaction(
    val id: Long,
    val amount: Double,
    val type: String,        // "income" or "expense"
    val categoryId: Long,
    val date: String,        // ⚠️ String 格式，應改為 Long timestamp
    val note: String?
)

data class Category(
    val id: Long,
    val name: String,
    val icon: String,
    val color: String,
    val type: String
)

// ⚠️ 缺少 Budget Entity（新功能需要）
```

技術問題發現:
1. 🔴 直接使用 SQLite Cursor（應改為 Room）
2. 🔴 UI 邏輯混在 Activity（應分離到 ViewModel）
3. 🔴 日期使用 String 格式（應使用 Timestamp）
4. 🟡 無依賴注入（手動 new Instance）
5. 🟡 無 Repository 層（資料來源耦合）

📄 已創建: Docs/legacy/Existing_System_Analysis.md
📄 已創建: Docs/legacy/Data_Model_Documentation.md
📄 已創建: Docs/legacy/UI_Flow_Diagram.md

接下來請確認新需求，我將產出 PRD/FRD。
```

#### 命令 2.2: 新需求分析

```
基於既有功能，請加入新需求並產出 PRD/FRD：

新需求：
1. 預算管理
   - 每月總預算設定
   - 分類預算設定
   - 超支警告（推播通知）
   - 預算進度顯示

2. 統計圖表升級
   - 月度收支折線圖（目前僅文字）
   - 分類支出圓餅圖（新功能）
   - 年度趨勢柱狀圖（新功能）
   - 使用 Vico Charts 套件

3. 雲端同步準備
   - 設計 RESTful API 規格
   - 本地資料結構調整
   - 同步衝突處理機制

保留既有功能：
- 所有現有功能必須保留並優化

請產出 PRD、FRD，並標示哪些是既有功能、哪些是新功能。
```

#### Claude Code 產出：

```
✅ 需求分析完成

【功能對照表】

| 功能 ID | 功能名稱 | 狀態 | 重構程度 |
|---------|---------|------|---------|
| F-001 | 新增收支記錄 | 🔄 保留+重構 | 架構重構 |
| F-002 | 編輯收支記錄 | 🔄 保留+重構 | 架構重構 |
| F-003 | 刪除收支記錄 | 🔄 保留+重構 | 架構重構 |
| F-004 | 分類管理 | 🔄 保留+重構 | 架構重構 |
| F-005 | 月度統計 | 🔄 保留+升級 | UI 升級（圖表化） |
| F-006 | 設定頁面 | ✅ 保留 | 僅 UI 遷移 |
| F-007 | 匯出 CSV | ✅ 保留 | 僅遷移 |
| F-008 | 備份/還原 | ✅ 保留 | 僅遷移 |
| F-009 | **預算管理** | 🆕 新功能 | 全新開發 |
| F-010 | **統計圖表** | 🆕 新功能 | 全新開發 |
| F-011 | **雲端同步** | 🆕 新功能 | 全新開發 |

📄 已創建: Docs/analysis/PRD_ExpenseTracker_v2.0.md
📄 已創建: Docs/analysis/FRD_ExpenseTracker_v2.0.md
📄 已創建: Docs/planning/Feature_Comparison_Matrix.md

請檢閱，確認後進入架構設計。
```

---

### 階段 3: 架構設計（重構 + 新功能）

#### 命令 3.1: 設計新架構

```
請設計 v2.0 的新架構：

目標架構：
- Jetpack Compose (100% Composable)
- MVVM (ViewModel + StateFlow)
- Hilt 依賴注入
- Room Database
- Repository Pattern
- Clean Architecture

請產出：
1. 新架構設計文檔（SRD）
2. 目錄結構規劃
3. 遷移計畫（舊 → 新）
4. Room Entity 定義
5. ViewModel 設計
```

#### Claude Code 產出：

```
✅ 新架構設計完成

【新目錄結構】

```
app/src/main/java/com/yourcompany/expensetracker/
├── ExpenseTrackerApp.kt              # Hilt Application
│
├── di/                                # 🆕 依賴注入
│   ├── AppModule.kt
│   ├── DatabaseModule.kt
│   └── RepositoryModule.kt
│
├── data/                              # 🔄 重構資料層
│   ├── local/
│   │   ├── dao/
│   │   │   ├── TransactionDao.kt
│   │   │   ├── CategoryDao.kt
│   │   │   └── BudgetDao.kt        # 🆕
│   │   ├── entity/
│   │   │   ├── TransactionEntity.kt
│   │   │   ├── CategoryEntity.kt
│   │   │   └── BudgetEntity.kt     # 🆕
│   │   └── AppDatabase.kt
│   ├── remote/                        # 🆕 API (未來)
│   │   └── ExpenseTrackerApi.kt
│   └── repository/                    # 🆕 Repository
│       ├── TransactionRepository.kt
│       ├── CategoryRepository.kt
│       └── BudgetRepository.kt      # 🆕
│
├── domain/                            # 🆕 Domain Layer
│   ├── model/
│   │   ├── Transaction.kt
│   │   ├── Category.kt
│   │   └── Budget.kt                # 🆕
│   └── usecase/
│       ├── GetTransactionsUseCase.kt
│       ├── SaveTransactionUseCase.kt
│       └── GetBudgetStatusUseCase.kt  # 🆕
│
├── ui/                                # 🔄 全面遷移 Compose
│   ├── theme/
│   │   ├── Color.kt
│   │   ├── Theme.kt
│   │   └── Type.kt
│   ├── components/                    # 🆕 共用組件
│   │   ├── TransactionCard.kt
│   │   ├── CategoryChip.kt
│   │   └── BudgetProgressBar.kt   # 🆕
│   ├── screens/
│   │   ├── home/
│   │   │   ├── HomeScreen.kt
│   │   │   └── HomeViewModel.kt
│   │   ├── transaction/
│   │   │   ├── TransactionListScreen.kt
│   │   │   ├── AddTransactionScreen.kt
│   │   │   └── TransactionViewModel.kt
│   │   ├── budget/                  # 🆕
│   │   │   ├── BudgetScreen.kt
│   │   │   └── BudgetViewModel.kt
│   │   ├── statistics/              # 🆕 升級
│   │   │   ├── StatisticsScreen.kt
│   │   │   └── StatisticsViewModel.kt
│   │   └── settings/
│   │       ├── SettingsScreen.kt
│   │       └── SettingsViewModel.kt
│   └── navigation/
│       └── NavGraph.kt
│
└── utils/
    ├── DateUtils.kt
    └── CurrencyUtils.kt
```

【Room Entity 定義】

```kotlin
// data/local/entity/TransactionEntity.kt

@Entity(tableName = "transactions")
data class TransactionEntity(
    @PrimaryKey(autoGenerate = true)
    val id: Long = 0,

    @ColumnInfo(name = "amount")
    val amount: Double,

    @ColumnInfo(name = "type")
    val type: String,  // "income" or "expense"

    @ColumnInfo(name = "category_id")
    val categoryId: Long,

    @ColumnInfo(name = "date")
    val date: Long,    // ✅ 改為 Timestamp

    @ColumnInfo(name = "note")
    val note: String?,

    @ColumnInfo(name = "created_at")
    val createdAt: Long = System.currentTimeMillis(),

    @ColumnInfo(name = "updated_at")
    val updatedAt: Long = System.currentTimeMillis(),

    @ColumnInfo(name = "synced")  // 🆕 雲端同步標記
    val synced: Boolean = false
)

// data/local/entity/BudgetEntity.kt (新功能)

@Entity(tableName = "budgets")
data class BudgetEntity(
    @PrimaryKey(autoGenerate = true)
    val id: Long = 0,

    @ColumnInfo(name = "month")
    val month: String,  // "YYYY-MM"

    @ColumnInfo(name = "total_budget")
    val totalBudget: Double,

    @ColumnInfo(name = "category_id")
    val categoryId: Long?,  // null = 總預算

    @ColumnInfo(name = "created_at")
    val createdAt: Long = System.currentTimeMillis()
)
```

【遷移計畫】

Sprint 1: 基礎架構
- ✅ 引入 Hilt
- ✅ 建立 Room Database
- ✅ 遷移 Transaction, Category Entity
- ✅ 建立 Repository Pattern
- ✅ 資料遷移腳本（SQLite → Room）

Sprint 2: UI 遷移 (核心功能)
- ✅ TransactionListScreen (Compose)
- ✅ AddTransactionScreen (Compose)
- ✅ CategoryManagementScreen (Compose)
- ✅ ViewModel 實作

Sprint 3: 新功能開發
- 🆕 BudgetScreen
- 🆕 StatisticsScreen (圖表)
- 🆕 推播通知

Sprint 4: 雲端同步 & 測試
- 🆕 API 整合
- ✅ 單元測試
- ✅ UI 測試

📄 已創建: Docs/planning/SRD_ExpenseTracker_v2.0.md
📄 已創建: Docs/planning/Migration_Plan.md
📄 已創建: Docs/planning/Directory_Structure.md

請確認架構設計，開始實作。
```

---

### 階段 4: 實作（分階段遷移）

#### 命令 4.1: Sprint 1 - 建立基礎架構

```
請協助建立 Sprint 1 基礎架構：

任務：
1. 設定 Hilt 依賴
2. 建立 Room Database
3. 建立 Repository Pattern
4. 資料遷移腳本

請提供完整程式碼。
```

#### Claude Code 產出：

```
✅ Sprint 1 開始

【步驟 1: build.gradle.kts 設定】

```kotlin
// app/build.gradle.kts

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("com.google.dagger.hilt.android")  // 🆕 Hilt
    id("com.google.devtools.ksp")         // 🆕 Room KSP
}

dependencies {
    // 🆕 Hilt
    implementation("com.google.dagger:hilt-android:2.48")
    ksp("com.google.dagger:hilt-compiler:2.48")
    implementation("androidx.hilt:hilt-navigation-compose:1.1.0")

    // 🆕 Room
    implementation("androidx.room:room-runtime:2.6.0")
    implementation("androidx.room:room-ktx:2.6.0")
    ksp("androidx.room:room-compiler:2.6.0")

    // 🆕 Jetpack Compose
    implementation(platform("androidx.compose:compose-bom:2023.10.01"))
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.ui:ui-tooling-preview")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.6.2")
    implementation("androidx.navigation:navigation-compose:2.7.5")

    // 🆕 Vico Charts (統計圖表)
    implementation("com.patrykandpatrick.vico:compose:1.13.1")
}
```

【步驟 2: Hilt Application】

```kotlin
// ExpenseTrackerApp.kt

package com.yourcompany.expensetracker

import android.app.Application
import dagger.hilt.android.HiltAndroidApp

@HiltAndroidApp
class ExpenseTrackerApp : Application()
```

【步驟 3: Room Database】

```kotlin
// data/local/AppDatabase.kt

package com.yourcompany.expensetracker.data.local

import androidx.room.Database
import androidx.room.RoomDatabase
import com.yourcompany.expensetracker.data.local.dao.*
import com.yourcompany.expensetracker.data.local.entity.*

@Database(
    entities = [
        TransactionEntity::class,
        CategoryEntity::class,
        BudgetEntity::class
    ],
    version = 2,  // ⚠️ 從舊版本升級
    exportSchema = true
)
abstract class AppDatabase : RoomDatabase() {
    abstract fun transactionDao(): TransactionDao
    abstract fun categoryDao(): CategoryDao
    abstract fun budgetDao(): BudgetDao
}
```

【步驟 4: Hilt Module】

```kotlin
// di/DatabaseModule.kt

package com.yourcompany.expensetracker.di

import android.content.Context
import androidx.room.Room
import androidx.room.migration.Migration
import androidx.sqlite.db.SupportSQLiteDatabase
import com.yourcompany.expensetracker.data.local.AppDatabase
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object DatabaseModule {

    @Provides
    @Singleton
    fun provideDatabase(
        @ApplicationContext context: Context
    ): AppDatabase {
        return Room.databaseBuilder(
            context,
            AppDatabase::class.java,
            "expense_tracker.db"
        )
            .addMigrations(MIGRATION_1_2)  // 🔴 資料遷移
            .build()
    }

    @Provides
    fun provideTransactionDao(database: AppDatabase) = database.transactionDao()

    @Provides
    fun provideCategoryDao(database: AppDatabase) = database.categoryDao()

    @Provides
    fun provideBudgetDao(database: AppDatabase) = database.budgetDao()

    // 🔴 資料遷移：舊 SQLite → Room v2
    private val MIGRATION_1_2 = object : Migration(1, 2) {
        override fun migrate(database: SupportSQLiteDatabase) {
            // 1. 修改 date 欄位格式 (String → Long)
            database.execSQL(
                """
                ALTER TABLE transactions
                ADD COLUMN date_timestamp INTEGER NOT NULL DEFAULT 0
                """.trimIndent()
            )

            // 2. 將舊 String 日期轉為 Timestamp
            // (需要寫資料轉換邏輯)

            // 3. 新增 Budget 表格
            database.execSQL(
                """
                CREATE TABLE IF NOT EXISTS budgets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                    month TEXT NOT NULL,
                    total_budget REAL NOT NULL,
                    category_id INTEGER,
                    created_at INTEGER NOT NULL
                )
                """.trimIndent()
            )

            // 4. 新增同步標記欄位
            database.execSQL(
                """
                ALTER TABLE transactions
                ADD COLUMN synced INTEGER NOT NULL DEFAULT 0
                """.trimIndent()
            )
        }
    }
}
```

【步驟 5: Repository】

```kotlin
// data/repository/TransactionRepository.kt

package com.yourcompany.expensetracker.data.repository

import com.yourcompany.expensetracker.data.local.dao.TransactionDao
import com.yourcompany.expensetracker.data.local.entity.TransactionEntity
import com.yourcompany.expensetracker.domain.model.Transaction
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import javax.inject.Inject

class TransactionRepository @Inject constructor(
    private val transactionDao: TransactionDao
) {
    fun getAllTransactions(): Flow<List<Transaction>> {
        return transactionDao.getAllTransactions()
            .map { entities -> entities.map { it.toDomainModel() } }
    }

    fun getTransactionsByDateRange(
        startDate: Long,
        endDate: Long
    ): Flow<List<Transaction>> {
        return transactionDao.getTransactionsByDateRange(startDate, endDate)
            .map { entities -> entities.map { it.toDomainModel() } }
    }

    suspend fun insertTransaction(transaction: Transaction) {
        transactionDao.insert(transaction.toEntity())
    }

    suspend fun deleteTransaction(id: Long) {
        transactionDao.deleteById(id)
    }
}

// Mapper Extensions
private fun TransactionEntity.toDomainModel() = Transaction(
    id = id,
    amount = amount,
    type = type,
    categoryId = categoryId,
    date = date,
    note = note
)

private fun Transaction.toEntity() = TransactionEntity(
    id = id,
    amount = amount,
    type = type,
    categoryId = categoryId,
    date = date,
    note = note,
    synced = false
)
```

✅ Sprint 1 基礎架構完成

請在 Android Studio 編譯並測試，確認：
- [ ] Hilt 依賴注入正常
- [ ] Room Database 創建成功
- [ ] 資料遷移無誤
- [ ] Repository 可正常讀寫

接下來要實作 Sprint 2: UI 遷移嗎？
```

#### 命令 4.2: Sprint 2 - UI 遷移（TransactionListScreen）

```
Sprint 1 已完成，請實作 Sprint 2：

請提供 TransactionListScreen 的 Compose 實作：
1. TransactionViewModel (StateFlow)
2. TransactionListScreen (Composable)
3. TransactionCard (Composable Component)
```

#### Claude Code 產出（部分）：

```
✅ Sprint 2 UI 遷移

【TransactionViewModel.kt】

```kotlin
// ui/screens/transaction/TransactionViewModel.kt

package com.yourcompany.expensetracker.ui.screens.transaction

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.yourcompany.expensetracker.data.repository.TransactionRepository
import com.yourcompany.expensetracker.domain.model.Transaction
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class TransactionViewModel @Inject constructor(
    private val repository: TransactionRepository
) : ViewModel() {

    private val _uiState = MutableStateFlow<TransactionUiState>(TransactionUiState.Loading)
    val uiState: StateFlow<TransactionUiState> = _uiState.asStateFlow()

    init {
        loadTransactions()
    }

    private fun loadTransactions() {
        viewModelScope.launch {
            repository.getAllTransactions()
                .catch { e ->
                    _uiState.value = TransactionUiState.Error(e.message ?: "Unknown error")
                }
                .collect { transactions ->
                    _uiState.value = TransactionUiState.Success(transactions)
                }
        }
    }

    fun deleteTransaction(id: Long) {
        viewModelScope.launch {
            repository.deleteTransaction(id)
        }
    }
}

sealed class TransactionUiState {
    object Loading : TransactionUiState()
    data class Success(val transactions: List<Transaction>) : TransactionUiState()
    data class Error(val message: String) : TransactionUiState()
}
```

【TransactionListScreen.kt】

```kotlin
// ui/screens/transaction/TransactionListScreen.kt

@Composable
fun TransactionListScreen(
    viewModel: TransactionViewModel = hiltViewModel(),
    onTransactionClick: (Long) -> Unit,
    onAddClick: () -> Unit
) {
    val uiState by viewModel.uiState.collectAsState()

    Scaffold(
        topBar = {
            TopAppBar(title = { Text("交易記錄") })
        },
        floatingActionButton = {
            FloatingActionButton(onClick = onAddClick) {
                Icon(Icons.Default.Add, contentDescription = "新增")
            }
        }
    ) { padding ->
        when (val state = uiState) {
            is TransactionUiState.Loading -> {
                CircularProgressIndicator(modifier = Modifier.padding(padding))
            }
            is TransactionUiState.Success -> {
                LazyColumn(modifier = Modifier.padding(padding)) {
                    items(state.transactions) { transaction ->
                        TransactionCard(
                            transaction = transaction,
                            onClick = { onTransactionClick(transaction.id) }
                        )
                    }
                }
            }
            is TransactionUiState.Error -> {
                Text("錯誤: ${state.message}")
            }
        }
    }
}
```

(後續省略...)

請複製至 Android Studio 編譯測試。
```

---

### 階段 5: 測試與驗證

#### 命令 5.1: 產生測試用例

```
請產生 TransactionViewModel 的單元測試：
使用 JUnit + MockK + Turbine (Flow 測試)
```

#### 命令 5.2: 執行一致性檢查

```
請執行 document-consistency-check workflow，驗證：
1. 新架構符合 SRD
2. 既有功能無遺失
3. 資料遷移正確性
```

---

## 附錄：命令速查表

### Brownfield Workflow

| Workflow | 命令 |
|----------|------|
| 專案評估 | `請使用 brownfield-system-analysis workflow` |
| 需求分析 | `請使用 requirements-validation-and-documentation workflow` |
| 架構設計 | `請使用 user-story-and-design workflow` |
| 遷移規劃 | `請使用 brownfield SOP 階段 3: 遷移規劃` |
| 一致性檢查 | `請執行 document-consistency-check workflow` |

### Sprint 時程建議

- **Sprint 1 (2週)**: 基礎架構（Hilt + Room + Repository）
- **Sprint 2 (2週)**: UI 遷移（核心功能）
- **Sprint 3 (2週)**: 新功能開發（預算 + 圖表）
- **Sprint 4 (2週)**: 雲端同步 + 測試

---

**更新**: 2025-12-15 | **版本**: v0.01
