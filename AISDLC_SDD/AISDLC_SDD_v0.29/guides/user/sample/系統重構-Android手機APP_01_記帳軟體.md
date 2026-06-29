# AISDLC 詳細實戰：系統重構 Android 記帳 APP

**專案類型**: Refactoring (系統重構)
**開發環境**: Android Studio + Cursor AI + Claude Code
**技術棧**: Kotlin + Jetpack Compose (MVVM) + Hilt
**後端**: Python + FastAPI (可選)
**適用版本**: AISDLC-SDD v0.01+
**最後更新**: 2025-12-15


> **SDD v0.01 使用者提示**：本指南基於 AISDLC-SDD v0.01。使用 AISDLC-SDD v0.01 時，請同時參考對應場景的 SDD Enhancement 文件（`scenarios/{scenario}/SDD_{SCENARIO}_ENHANCEMENT.md`），並確認所有 SCG 閘門步驟已整合到您的工作流程中。

---
---

## 📋 目錄

1. [第一步：Cursor AI 專案路徑設定](#第一步cursor-ai-專案路徑設定)
2. [第二步：AISDLC 框架安裝](#第二步aisdlc-框架安裝)
3. [第三步：Claude Code 完整重構流程](#第三步claude-code-完整重構流程)
4. [附錄：命令速查表](#附錄命令速查表)

---

## 第一步：Cursor AI 專案路徑設定

### 1.1 既有專案結構

**位置**: `~/Projects/ExpenseTrackerAndroid/`

```
ExpenseTrackerAndroid/
├── app/
│   ├── src/main/java/com/expense/
│   │   ├── MainActivity.kt          # ⚠️ 單一 Activity (神類)
│   │   ├── TransactionAdapter.kt    # RecyclerView
│   │   ├── DatabaseHelper.kt        # ⚠️ 直接 SQLite
│   │   └── Utils.kt                 # ⚠️ 萬能工具類
│   ├── res/
│   │   └── layout/                  # ⚠️ XML Layout
│   └── build.gradle.kts
├── build.gradle.kts
└── settings.gradle.kts
```

**重構目標**:
- 單體架構 → Clean Architecture
- XML Layout → Jetpack Compose
- 直接 SQLite → Room + Repository
- 無測試 → 單元測試 (60%+)

### 1.2 建立輔助目錄

```bash
cd ~/Projects/ExpenseTrackerAndroid

mkdir -p Docs/analysis
mkdir -p Docs/planning
mkdir -p Docs/reports
mkdir -p Docs/legacy
mkdir -p Backend

ls -la
```

### 1.3 開啟 Cursor AI

1. 打開 Cursor
2. `File` → `Open Folder...`
3. 選擇 `~/Projects/ExpenseTrackerAndroid`

---

## 第二步：AISDLC 框架安裝

```bash
cd ~/Projects/ExpenseTrackerAndroid
ln -s ~/Cursor_Project/AISDLC_ALL/AISDLC_v0.09 ./AISDLC_v0.09
ls -la AISDLC_SDD_v0.01/scenarios/refactoring/SOP.md
```

---

## 第三步：Claude Code 完整重構流程

### 階段 0: 啟動

按 `Cmd + Shift + P` → `Claude Code`

---

### 階段 1: 重構評估

#### 命令 1.1

```
請載入 AISDLC_SDD_v0.01/AISDLC_INIT.md

系統重構 Android 記帳 APP，使用 Refactoring SOP。

背景：
- 舊架構：單體架構，所有邏輯在 MainActivity
- 技術債：無測試、緊耦合、直接 SQLite
- 重構目標：Clean Architecture + Compose + MVVM + Hilt + Room

啟動階段 1：程式碼品質評估。
```

#### Claude Code 回應

```
✅ 已載入 Refactoring SOP

🔴 人工確認點 1

Q1: 程式碼規模？
- 總行數
- MainActivity 行數
- 類別數量

Q2: 技術債務？
- 程式碼重複率
- 循環複雜度
- 測試覆蓋率

Q3: 重構範圍？
- 架構重構？
- UI 重構？
- 資料層重構？

Q4: 時程？
```

#### 命令 1.2

```
Q1: 規模
- 總行數：約 12,000 行 Kotlin
- MainActivity：1,800 行 (神類)
- 類別：8 個

Q2: 技術債
- 程式碼重複：約 40%
- 循環複雜度：高（MainActivity）
- 測試：0%

Q3: 範圍
- 全面重構：架構 + UI + 資料層

Q4: 時程
- 10 週
- 可分 5 個 Sprint

產出評估報告。
```

#### Claude Code 產出

```
✅ 程式碼品質評估完成

【程式碼健康度】🔴 差（40/100）

技術債務分析：
- 🔴 神類問題（MainActivity 1,800 行）
- 🔴 無測試（極高風險）
- 🔴 緊耦合（難以維護）
- 🟡 程式碼重複（40%）

【重構策略 (10 週)】

**Sprint 1-2 (週 1-4): 架構重構**
- Clean Architecture 建立
- Hilt 依賴注入
- Room Database 遷移
- Repository Pattern

**Sprint 3 (週 5-6): UI 重構**
- XML → Jetpack Compose
- Navigation Component

**Sprint 4 (週 7-8): 業務邏輯重構**
- ViewModel 實作
- Use Cases 建立
- 程式碼去重

**Sprint 5 (週 9-10): 測試 & 優化**
- 單元測試 (目標 60%)
- UI 測試
- 效能優化

📄 Docs/legacy/Code_Quality_Assessment.md
📄 Docs/planning/Refactoring_Strategy_10Week.md
```

---

### 階段 2: 舊程式碼分析

#### 命令 2.1

```
請使用 code-smell-detection workflow 分析：

1. app/src/main/java/com/expense/MainActivity.kt
2. app/src/main/java/com/expense/DatabaseHelper.kt
3. app/src/main/java/com/expense/Utils.kt

產出：
- Code Smell 清單
- 重構優先級
- 依賴關係圖
```

#### Claude Code 產出

```
✅ Code Smell 分析完成

【發現的 Code Smells】

1. **神類 (God Class)** - MainActivity
   - 1,800 行程式碼
   - 職責過多：UI + 業務邏輯 + 資料存取
   - 優先級：🔴 高

2. **長方法 (Long Method)**
   - `saveTransaction()`: 250 行
   - `calculateStatistics()`: 180 行
   - 優先級：🔴 高

3. **重複程式碼 (Duplicated Code)**
   - 日期格式化：5 處重複
   - 金額驗證：7 處重複
   - 優先級：🟡 中

4. **原始型別偏執 (Primitive Obsession)**
   - 使用 String 表示金額
   - 使用 Int 表示交易類型
   - 優先級：🟡 中

5. **不當親密 (Inappropriate Intimacy)**
   - MainActivity 直接操作 SQLite Cursor
   - 優先級：🔴 高

【重構優先級】

🔴 P1 (立即處理):
1. 拆分 MainActivity (神類)
2. 引入 Room Database
3. 建立 Repository Layer

🟡 P2 (次要):
4. 重構長方法
5. 消除程式碼重複

🟢 P3 (優化):
6. 改善命名
7. 增加註解

📄 Docs/legacy/Code_Smells_Report.md
📄 Docs/planning/Refactoring_Priority.md
```

---

### 階段 3: 重構設計

#### 命令 3.1

```
設計重構後的架構：

目標：Clean Architecture
- Presentation Layer (Compose + ViewModel)
- Domain Layer (Use Cases)
- Data Layer (Repository + Room)

產出：
1. 新目錄結構
2. 類別設計
3. 依賴注入設計
4. 遷移步驟
```

#### Claude Code 產出

```
✅ 重構架構設計完成

【Clean Architecture 結構】

```
app/src/main/java/com/expense/
├── ExpenseApplication.kt           # Hilt Application
│
├── di/                             # Dependency Injection
│   ├── AppModule.kt
│   ├── DatabaseModule.kt
│   └── RepositoryModule.kt
│
├── data/                           # Data Layer
│   ├── local/
│   │   ├── dao/
│   │   │   ├── TransactionDao.kt
│   │   │   └── CategoryDao.kt
│   │   ├── entity/
│   │   │   ├── TransactionEntity.kt
│   │   │   └── CategoryEntity.kt
│   │   └── AppDatabase.kt
│   └── repository/
│       ├── TransactionRepositoryImpl.kt
│       └── CategoryRepositoryImpl.kt
│
├── domain/                         # Domain Layer
│   ├── model/
│   │   ├── Transaction.kt
│   │   └── Category.kt
│   ├── repository/
│   │   ├── TransactionRepository.kt (Interface)
│   │   └── CategoryRepository.kt (Interface)
│   └── usecase/
│       ├── GetTransactionsUseCase.kt
│       ├── SaveTransactionUseCase.kt
│       ├── DeleteTransactionUseCase.kt
│       └── CalculateStatisticsUseCase.kt
│
└── presentation/                   # Presentation Layer
    ├── MainActivity.kt             # 簡化版 (僅導航)
    ├── ui/
    │   ├── theme/
    │   │   ├── Color.kt
    │   │   ├── Theme.kt
    │   │   └── Type.kt
    │   ├── screens/
    │   │   ├── home/
    │   │   │   ├── HomeScreen.kt
    │   │   │   └── HomeViewModel.kt
    │   │   ├── transaction/
    │   │   │   ├── TransactionListScreen.kt
    │   │   │   ├── AddTransactionScreen.kt
    │   │   │   └── TransactionViewModel.kt
    │   │   └── statistics/
    │   │       ├── StatisticsScreen.kt
    │   │       └── StatisticsViewModel.kt
    │   ├── components/
    │   │   ├── TransactionCard.kt
    │   │   └── CategoryChip.kt
    │   └── navigation/
    │       └── NavGraph.kt
    └── util/
        ├── DateFormatter.kt
        └── CurrencyFormatter.kt
```

【重構步驟（逐步遷移）】

**Phase 1: 建立新架構骨架**
```kotlin
// 1. 設定 Hilt
// build.gradle.kts
plugins {
    id("com.google.dagger.hilt.android")
    id("com.google.devtools.ksp")
}

dependencies {
    implementation("com.google.dagger:hilt-android:2.48")
    ksp("com.google.dagger:hilt-compiler:2.48")

    implementation("androidx.room:room-runtime:2.6.0")
    implementation("androidx.room:room-ktx:2.6.0")
    ksp("androidx.room:room-compiler:2.6.0")
}
```

**Phase 2: 建立 Room Database**
```kotlin
// data/local/entity/TransactionEntity.kt

@Entity(tableName = "transactions")
data class TransactionEntity(
    @PrimaryKey(autoGenerate = true)
    val id: Long = 0,

    @ColumnInfo(name = "amount")
    val amount: Double,

    @ColumnInfo(name = "type")
    val type: String,

    @ColumnInfo(name = "category_id")
    val categoryId: Long,

    @ColumnInfo(name = "date")
    val date: Long,

    @ColumnInfo(name = "note")
    val note: String?
)

// data/local/dao/TransactionDao.kt

@Dao
interface TransactionDao {
    @Query("SELECT * FROM transactions ORDER BY date DESC")
    fun getAllTransactions(): Flow<List<TransactionEntity>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insert(transaction: TransactionEntity)

    @Delete
    suspend fun delete(transaction: TransactionEntity)
}

// data/local/AppDatabase.kt

@Database(entities = [TransactionEntity::class], version = 1)
abstract class AppDatabase : RoomDatabase() {
    abstract fun transactionDao(): TransactionDao
}
```

**Phase 3: Repository Pattern**
```kotlin
// domain/repository/TransactionRepository.kt (Interface)

interface TransactionRepository {
    fun getAllTransactions(): Flow<List<Transaction>>
    suspend fun saveTransaction(transaction: Transaction)
    suspend fun deleteTransaction(transaction: Transaction)
}

// data/repository/TransactionRepositoryImpl.kt

class TransactionRepositoryImpl @Inject constructor(
    private val transactionDao: TransactionDao
) : TransactionRepository {

    override fun getAllTransactions(): Flow<List<Transaction>> {
        return transactionDao.getAllTransactions()
            .map { entities -> entities.map { it.toDomain() } }
    }

    override suspend fun saveTransaction(transaction: Transaction) {
        transactionDao.insert(transaction.toEntity())
    }

    override suspend fun deleteTransaction(transaction: Transaction) {
        transactionDao.delete(transaction.toEntity())
    }
}

// Mapper
private fun TransactionEntity.toDomain() = Transaction(
    id = id,
    amount = amount,
    type = TransactionType.valueOf(type),
    categoryId = categoryId,
    date = Date(date),
    note = note
)
```

**Phase 4: Use Case**
```kotlin
// domain/usecase/GetTransactionsUseCase.kt

class GetTransactionsUseCase @Inject constructor(
    private val repository: TransactionRepository
) {
    operator fun invoke(): Flow<List<Transaction>> {
        return repository.getAllTransactions()
    }
}
```

**Phase 5: ViewModel**
```kotlin
// presentation/ui/screens/transaction/TransactionViewModel.kt

@HiltViewModel
class TransactionViewModel @Inject constructor(
    private val getTransactionsUseCase: GetTransactionsUseCase,
    private val saveTransactionUseCase: SaveTransactionUseCase,
    private val deleteTransactionUseCase: DeleteTransactionUseCase
) : ViewModel() {

    private val _uiState = MutableStateFlow<TransactionUiState>(TransactionUiState.Loading)
    val uiState: StateFlow<TransactionUiState> = _uiState.asStateFlow()

    init {
        loadTransactions()
    }

    private fun loadTransactions() {
        viewModelScope.launch {
            getTransactionsUseCase()
                .catch { e ->
                    _uiState.value = TransactionUiState.Error(e.message ?: "Unknown error")
                }
                .collect { transactions ->
                    _uiState.value = TransactionUiState.Success(transactions)
                }
        }
    }

    fun deleteTransaction(transaction: Transaction) {
        viewModelScope.launch {
            deleteTransactionUseCase(transaction)
        }
    }
}

sealed class TransactionUiState {
    object Loading : TransactionUiState()
    data class Success(val transactions: List<Transaction>) : TransactionUiState()
    data class Error(val message: String) : TransactionUiState()
}
```

**Phase 6: Jetpack Compose UI**
```kotlin
// presentation/ui/screens/transaction/TransactionListScreen.kt

@Composable
fun TransactionListScreen(
    viewModel: TransactionViewModel = hiltViewModel()
) {
    val uiState by viewModel.uiState.collectAsState()

    Scaffold(
        topBar = {
            TopAppBar(title = { Text("交易記錄") })
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
                            onDelete = { viewModel.deleteTransaction(it) }
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

📄 Docs/planning/SRD_Refactored_Architecture.md
📄 Docs/planning/Migration_Steps_Guide.md
```

---

### 階段 4: 逐步重構實作

#### 命令 4.1

```
實作 Sprint 1：建立架構骨架

任務：
1. Hilt 設定
2. Room Database
3. Repository Pattern
4. 資料遷移（SQLite → Room）

提供完整程式碼。
```

#### 命令 4.2

```
實作 Sprint 2：拆分 MainActivity

任務：
1. 提取業務邏輯至 Use Cases
2. 建立 ViewModels
3. 簡化 MainActivity（僅保留導航）

提供重構前後對比。
```

---

### 階段 5: 測試 & 驗證

#### 命令 5.1

```
產生單元測試：
1. TransactionRepositoryTest
2. GetTransactionsUseCaseTest
3. TransactionViewModelTest

使用 JUnit + MockK + Turbine
```

#### 命令 5.2

```
執行 code-quality-check workflow：
驗證重構後的程式碼品質
```

---

## 附錄：命令速查表

### Refactoring Workflow

| Workflow | 命令 |
|----------|------|
| 程式碼品質評估 | `請使用 code-smell-detection workflow` |
| 重構設計 | `請使用 user-story-and-design workflow` |
| 品質驗證 | `請執行 code-quality-check workflow` |

### 10 週重構時程

- **Sprint 1-2 (週 1-4)**: 架構重構（Clean Architecture）
- **Sprint 3 (週 5-6)**: UI 重構（Compose）
- **Sprint 4 (週 7-8)**: 業務邏輯重構
- **Sprint 5 (週 9-10)**: 測試 & 優化

### 重構原則

1. **逐步遷移**：不要一次重寫所有程式碼
2. **保持功能穩定**：每次重構後立即測試
3. **測試先行**：重構前先補單元測試
4. **小步快跑**：頻繁提交，降低風險

---

**更新**: 2025-12-15 | **版本**: v0.01
