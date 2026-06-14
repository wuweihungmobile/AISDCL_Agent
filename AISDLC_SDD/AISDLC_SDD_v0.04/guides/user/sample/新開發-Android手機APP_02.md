# Android 記帳 APP 開發完整範例

> **SDD v0.01 使用者提示**：本指南基於 AISDLC-SDD v0.01。使用 AISDLC-SDD v0.01 時，請同時參考對應場景的 SDD Enhancement 文件（`scenarios/{scenario}/SDD_{SCENARIO}_ENHANCEMENT.md`），並確認所有 SCG 閘門步驟已整合到您的工作流程中。

---
# AISDLC Framework - Kotlin + Jetpack Compose + MVVM

**版本**: v0.01
**建立日期**: 2025-12-13
**適用情境**: Greenfield Mobile App 開發（Android Native）
**範例專案**: MoneyTracker Pro - 智能記帳 APP

---

## 🎯 專案概述

**專案名稱**: MoneyTracker Pro
**專案類型**: Android 原生記帳 APP
**技術棧**:
- **前端語言**: Kotlin 1.9+
- **UI 框架**: Jetpack Compose + Material Design 3
- **架構模式**: MVVM (ViewModel + StateFlow)
- **依賴注入**: Hilt (Dagger)
- **本地資料庫**: Room + SQLCipher
- **後端 API**: Python FastAPI (選用，雲端同步)

**開發工具**: Android Studio + Cursor AI + Claude Code
**AISDLC 版本**: v0.01

---

## 📂 步驟 1: Cursor AI 專案路徑設定

### 1.1 建立 Android 專案結構

```bash
# 建立主專案目錄
mkdir MoneyTracker_Pro
cd MoneyTracker_Pro

# 建立標準 Android 專案結構
mkdir -p app/src/{main,test,androidTest}/java/com/moneytracker/pro
mkdir -p app/src/main/{res,assets}
mkdir -p docs/{requirements,architecture,api,tests}

# 建立文檔目錄
mkdir -p docs/requirements docs/architecture docs/api docs/tests
```

### 1.2 初始化 Git（選用）

```bash
git init
echo "*.iml" > .gitignore
echo ".gradle/" >> .gitignore
echo ".idea/" >> .gitignore
echo "build/" >> .gitignore
echo "local.properties" >> .gitignore
```

### 1.3 開啟 Cursor AI

1. 啟動 Cursor AI
2. **File → Open Folder**
3. 選擇 `MoneyTracker_Pro` 資料夾
4. 確認左側檔案樹顯示完整結構

**預期結構**:
```
MoneyTracker_Pro/
├── app/                    # Android App 模組
│   ├── src/
│   │   ├── main/
│   │   │   ├── java/com/moneytracker/pro/
│   │   │   ├── res/
│   │   │   └── AndroidManifest.xml
│   │   ├── test/
│   │   └── androidTest/
│   └── build.gradle.kts
├── docs/                   # 文檔（PRD/FRD/SRD/API）
├── backend/                # Python FastAPI (選用)
└── AISDLC/                 # AISDLC Framework
```

---

## 🔧 步驟 2: 安裝設定 AISDLC Framework

### 2.1 複製 AISDLC 到專案

```bash
# 在專案根目錄執行
cp -r /Users/wuweihong/Cursor_Project/AISDLC_ALL/AISDLC_v0.09 ./AISDLC

# 驗證安裝
ls -la AISDLC/
# 預期輸出: AISDLC_INIT.md, agent/, workflow/, docs_template/, scenarios/, guides/
```

### 2.2 完整專案結構

```
MoneyTracker_Pro/
├── AISDLC/                         # AISDLC Framework
│   ├── AISDLC_INIT.md              # 框架初始化
│   ├── scenarios/greenfield/       # Greenfield SOP
│   ├── agent/                      # Agent 配置
│   └── guides/                     # 參考指南
├── app/
│   ├── src/main/java/com/moneytracker/pro/
│   │   ├── data/                   # Data Layer
│   │   │   ├── local/              # Room Database
│   │   │   ├── remote/             # API (選用)
│   │   │   └── repository/         # Repository
│   │   ├── domain/                 # Domain Layer
│   │   │   ├── model/              # Domain Models
│   │   │   └── usecase/            # Use Cases
│   │   ├── presentation/           # Presentation Layer
│   │   │   ├── screens/            # Compose Screens
│   │   │   ├── viewmodel/          # ViewModels
│   │   │   └── components/         # Reusable Components
│   │   ├── di/                     # Hilt Modules
│   │   └── MoneyTrackerApp.kt      # Application Class
│   └── build.gradle.kts
├── docs/                           # 專案文檔
└── backend/                        # FastAPI (選用)
```

---

## 💬 步驟 3: Claude Code 開發流程（完整範例）

### 階段 0: 框架初始化

**Cursor AI → Chat 面板 → 輸入指令**:

```
請載入 AISDLC Framework 初始化文檔：

讀取並執行：AISDLC/AISDLC_INIT.md

專案類型：Greenfield Mobile App (Android Native)
技術棧：Kotlin + Jetpack Compose + MVVM + Hilt
```

**預期回應**:
```
✅ AISDLC Framework v0.01 已載入
✅ Mobile-Architect Agent 已準備
✅ 準備開始 Greenfield Android 開發流程
```

---

### 階段 1: 需求蒐集（2-3 小時）

#### 1.1 啟動需求分析

**輸入指令**:
```
我要開發 Android 記帳 APP，請開始執行 Greenfield SOP。

專案名稱：MoneyTracker Pro
平台：Android Native App
技術棧：
- 語言：Kotlin 1.9+
- UI：Jetpack Compose + Material Design 3
- 架構：MVVM (ViewModel + StateFlow)
- DI：Hilt
- 資料庫：Room + SQLCipher（加密）
- 後端：Python FastAPI（雲端同步，選用）

核心功能：
1. 記帳功能（收入/支出記錄）
2. 分類管理（自訂分類、圖示）
3. 報表統計（月報表、年報表、圖表）
4. 預算管理（設定月預算、超支提醒）
5. 雲端同步（選用，跨裝置同步）
```

**AI 回應**:
```
✅ SA-Analyst (Amanda) 已載入
✅ Mobile-Architect (Marcus) 已載入

【需求蒐集問卷】
請回答以下問題...
```

#### 1.2 回答需求問卷（範例）

```
Q1. 目標使用者？
A1.
   - 主要：25-45 歲上班族、自由工作者
   - 次要：學生、家庭主婦
   - 預估使用者：10,000 人（首年）

Q2. 核心場景？
A2.
   【場景 1】快速記帳
   - 使用者：上班族
   - 情境：買完午餐後立即記錄
   - 期望：< 10 秒完成記帳

   【場景 2】月底檢視報表
   - 使用者：自由工作者
   - 情境：檢視本月收支、分類占比
   - 期望：圖表清晰、可匯出 PDF

   【場景 3】預算管理
   - 使用者：家庭主婦
   - 情境：設定每月餐費預算 10,000 元
   - 期望：超支自動提醒

Q3. 資料儲存需求？
A3.
   - 本地優先：Room SQLite（加密）
   - 雲端同步：選用功能（Google Drive / 自建 API）
   - 離線模式：完整功能可用
   - 資料匯出：CSV / Excel / PDF

Q4. 安全需求？
A4.
   - 應用鎖：PIN / 指紋 / Face ID
   - 資料加密：SQLCipher（AES-256）
   - 隱私模式：隱藏金額顯示

Q5. 效能需求？
A5.
   - 啟動時間：< 2 秒（冷啟動）
   - 記帳操作：< 500ms（含動畫）
   - 支援資料量：> 10,000 筆交易記錄
```

#### 1.3 確認 PRD 文檔

**AI 輸出**:
```
✅ 需求分析完成！

【產出文檔】
- docs/requirements/PRD_MoneyTracker_Pro_v1.0.md
- docs/requirements/User_Journey_Map.md
- docs/requirements/Wireframe_Sketches.md

【識別的 Epic】
- EPIC-001: 記帳核心功能
- EPIC-002: 分類管理系統
- EPIC-003: 報表與統計
- EPIC-004: 預算管理
- EPIC-005: 雲端同步（選用）
- EPIC-006: 安全與隱私

【下一步】
請確認 PRD，確認後進入 Stage 2（需求驗證與 STRIDE 分析）
```

---

### 階段 2: 需求驗證與威脅建模（2-3 小時）

#### 2.1 STRIDE 威脅建模

**輸入指令**:
```
PRD 確認無誤，請進入 Stage 2 需求驗證與威脅建模。
```

**AI 執行**:
```
✅ 正在執行 STRIDE 威脅分析（Mobile App 特化版）...

【威脅建模結果】
識別 12 個潛在威脅：
- Spoofing (S): 2 個（未授權存取、Root 破解）
- Tampering (T): 2 個（資料庫篡改、APK 重打包）
- Repudiation (R): 1 個（否認操作記錄）
- Information Disclosure (I): 3 個（記憶體洩露、螢幕截圖、備份洩露）
- Denial of Service (D): 2 個（惡意大量資料、記憶體耗盡）
- Elevation of Privilege (E): 2 個（Root 權限提升、Debug 模式）

【產出安全需求】
- NFR-SEC-001: 應用鎖認證（PIN / 生物辨識）
- NFR-SEC-002: 資料庫加密（SQLCipher AES-256）
- NFR-SEC-003: Root 偵測與防護
- NFR-SEC-004: 螢幕截圖防護（敏感頁面）
- NFR-SEC-005: 操作日誌記錄
- NFR-SEC-006: APK 簽章驗證

【產出文檔】
- docs/requirements/FRD_MoneyTracker_Pro_v1.0.md
- docs/requirements/STRIDE_Threat_Analysis_Mobile.md
- docs/requirements/Security_Requirements_Spec.md
```

#### 2.2 確認 User Story（範例）

**AI 輸出**:
```
【EPIC-001: 記帳核心功能】
- US-001: 使用者可以快速記錄支出
  - AC-001-1: 點擊「新增」按鈕開啟記帳頁面
  - AC-001-2: 輸入金額、選擇分類、新增備註（選填）
  - AC-001-3: 點擊「儲存」後記錄顯示在清單
  - AT-001-1-1: 輸入金額 500、分類「午餐」，驗證儲存成功

- US-002: 使用者可以記錄收入
  - AC-002-1: 切換至「收入」標籤
  - AC-002-2: 輸入金額、選擇收入來源
  - AT-002-1-1: 記錄薪資收入 40,000，驗證顯示正確

【EPIC-003: 報表與統計】
- US-010: 使用者可以查看月報表
  - AC-010-1: 顯示當月總收入、總支出、結餘
  - AC-010-2: 顯示分類占比圓餅圖
  - AC-010-3: 支援切換月份
  - AT-010-1-1: 驗證 12 月報表計算正確

... (共 35 個 User Story)
```

---

### 階段 3: 技術選型與架構設計（2-3 小時）

#### 3.1 技術棧確認

**輸入指令**:
```
FRD 確認完成，請進入 Stage 3 技術選型與架構設計。

技術棧確認：
- 語言：Kotlin 1.9+
- UI：Jetpack Compose + Material Design 3
- 架構：Clean Architecture (MVVM)
- DI：Hilt
- 資料庫：Room + SQLCipher
- 圖表：Vico Chart Library
- 非同步：Kotlin Coroutines + Flow

請設計完整架構。
```

**AI 輸出**:
```
✅ Mobile-Architect (Marcus) 已載入

【技術選型評估】

#### 1. UI 框架：Jetpack Compose vs XML
| 評估維度 | Compose | XML Views |
|---------|---------|-----------|
| 功能性 | 5 | 4 |
| 開發效率 | 5 | 3 |
| 學習曲線 | 4 | 5 |
| 社群支援 | 5 | 5 |
| **總分** | **4.8** | **4.2** |

**決策**: Jetpack Compose（現代化、聲明式 UI）

---

#### 2. 架構模式：MVVM vs MVI
| 評估維度 | MVVM | MVI |
|---------|------|-----|
| 功能性 | 5 | 5 |
| 複雜度 | 4 | 3 |
| 狀態管理 | 4 | 5 |
| 測試性 | 4 | 5 |
| **總分** | **4.3** | **4.5** |

**決策**: MVVM（團隊熟悉度高，適合中型專案）
**替代**: 可在複雜頁面局部使用 MVI 模式

---

【最終技術棧】
- **Language**: Kotlin 1.9+ (Coroutines + Flow)
- **UI**: Jetpack Compose + Material Design 3
- **Architecture**: Clean Architecture (3-Layer MVVM)
  - Presentation Layer (UI + ViewModel)
  - Domain Layer (UseCase + Model)
  - Data Layer (Repository + DataSource)
- **DI**: Hilt (Dagger)
- **Database**: Room 2.6+ + SQLCipher 4.5+
- **Charts**: Vico Chart Library
- **Testing**: JUnit 5 + Mockk + Turbine (Flow Testing)
```

#### 3.2 架構設計圖

**AI 輸出**:
```
┌──────────────────────────────────────────────────────────┐
│       MoneyTracker Pro - Clean Architecture (MVVM)       │
└──────────────────────────────────────────────────────────┘

📱 Presentation Layer (UI + ViewModel)
   │
   ├─ Compose Screens
   │  ├─ HomeScreen.kt              (首頁 - 交易清單)
   │  ├─ AddTransactionScreen.kt    (新增交易)
   │  ├─ ReportScreen.kt            (報表統計)
   │  └─ SettingsScreen.kt          (設定)
   │
   ├─ ViewModels (StateFlow)
   │  ├─ HomeViewModel.kt
   │  ├─ AddTransactionViewModel.kt
   │  └─ ReportViewModel.kt
   │
   └─ UI State
      ├─ HomeUiState.kt
      └─ ReportUiState.kt

   ↓ (UseCase Invocation)

🧠 Domain Layer (Business Logic)
   │
   ├─ Models (Domain Entities)
   │  ├─ Transaction.kt             (交易實體)
   │  ├─ Category.kt                (分類實體)
   │  └─ Budget.kt                  (預算實體)
   │
   └─ UseCases
      ├─ AddTransactionUseCase.kt
      ├─ GetMonthlyReportUseCase.kt
      ├─ GetCategoryStatsUseCase.kt
      └─ CheckBudgetUseCase.kt

   ↓ (Repository Interface)

💾 Data Layer (Data Sources)
   │
   ├─ Repository (Implementations)
   │  ├─ TransactionRepositoryImpl.kt
   │  ├─ CategoryRepositoryImpl.kt
   │  └─ BudgetRepositoryImpl.kt
   │
   ├─ Local Data Source (Room + SQLCipher)
   │  ├─ AppDatabase.kt
   │  ├─ TransactionDao.kt
   │  ├─ CategoryDao.kt
   │  └─ Entities
   │     ├─ TransactionEntity.kt
   │     └─ CategoryEntity.kt
   │
   └─ Remote Data Source (選用)
      └─ ApiService.kt              (FastAPI 同步)

🔧 DI (Hilt Modules)
   ├─ DatabaseModule.kt              (提供 Room Database)
   ├─ RepositoryModule.kt            (提供 Repositories)
   └─ UseCaseModule.kt               (提供 UseCases)
```

#### 3.3 資料庫 Schema 設計

**AI 輸出**:
```kotlin
// TransactionEntity.kt
@Entity(tableName = "transactions")
data class TransactionEntity(
    @PrimaryKey(autoGenerate = true)
    val id: Long = 0,

    @ColumnInfo(name = "type")
    val type: TransactionType,  // INCOME, EXPENSE

    @ColumnInfo(name = "amount")
    val amount: Double,

    @ColumnInfo(name = "category_id")
    val categoryId: Long,

    @ColumnInfo(name = "note")
    val note: String?,

    @ColumnInfo(name = "date")
    val date: Long,  // Unix timestamp

    @ColumnInfo(name = "created_at")
    val createdAt: Long = System.currentTimeMillis()
)

// CategoryEntity.kt
@Entity(tableName = "categories")
data class CategoryEntity(
    @PrimaryKey(autoGenerate = true)
    val id: Long = 0,

    @ColumnInfo(name = "name")
    val name: String,

    @ColumnInfo(name = "icon")
    val icon: String,  // Material Icon name

    @ColumnInfo(name = "color")
    val color: String,  // Hex color code

    @ColumnInfo(name = "type")
    val type: TransactionType
)

// BudgetEntity.kt
@Entity(tableName = "budgets")
data class BudgetEntity(
    @PrimaryKey(autoGenerate = true)
    val id: Long = 0,

    @ColumnInfo(name = "category_id")
    val categoryId: Long,

    @ColumnInfo(name = "amount")
    val amount: Double,

    @ColumnInfo(name = "month")
    val month: String,  // "2025-12"

    @ColumnInfo(name = "created_at")
    val createdAt: Long = System.currentTimeMillis()
)

// Indexes for performance
@Database(
    entities = [TransactionEntity::class, CategoryEntity::class, BudgetEntity::class],
    version = 1,
    exportSchema = true
)
abstract class AppDatabase : RoomDatabase() {
    // DAOs
    abstract fun transactionDao(): TransactionDao
    abstract fun categoryDao(): CategoryDao
    abstract fun budgetDao(): BudgetDao
}
```

---

### 階段 4-5: 實作開發（6-8 週）

#### 4.1 初始化專案

**輸入指令**:
```
請協助建立完整的 Android 專案結構，包含：

1. build.gradle.kts（Compose + Hilt + Room + SQLCipher）
2. Hilt Application Class
3. Room Database 設定（含 SQLCipher 加密）
4. Navigation Graph（Compose Navigation）
```

**AI 產出 - build.gradle.kts (app 模組)**:
```kotlin
plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("com.google.devtools.ksp")
    id("com.google.dagger.hilt.android")
}

android {
    namespace = "com.moneytracker.pro"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.moneytracker.pro"
        minSdk = 26
        targetSdk = 34
        versionCode = 1
        versionName = "1.0.0"

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }

    buildFeatures {
        compose = true
    }

    composeOptions {
        kotlinCompilerExtensionVersion = "1.5.3"
    }

    kotlinOptions {
        jvmTarget = "17"
    }
}

dependencies {
    // Jetpack Compose
    implementation(platform("androidx.compose:compose-bom:2024.01.00"))
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.ui:ui-tooling-preview")
    implementation("androidx.activity:activity-compose:1.8.2")
    implementation("androidx.navigation:navigation-compose:2.7.6")

    // Lifecycle + ViewModel
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.7.0")
    implementation("androidx.lifecycle:lifecycle-runtime-compose:2.7.0")

    // Hilt
    implementation("com.google.dagger:hilt-android:2.50")
    ksp("com.google.dagger:hilt-compiler:2.50")
    implementation("androidx.hilt:hilt-navigation-compose:1.1.0")

    // Room + SQLCipher
    implementation("androidx.room:room-runtime:2.6.1")
    implementation("androidx.room:room-ktx:2.6.1")
    ksp("androidx.room:room-compiler:2.6.1")
    implementation("net.zetetic:android-database-sqlcipher:4.5.4")

    // Coroutines
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.7.3")

    // Charts
    implementation("com.patrykandpatrick.vico:compose:1.13.1")

    // Testing
    testImplementation("junit:junit:4.13.2")
    testImplementation("io.mockk:mockk:1.13.8")
    testImplementation("app.cash.turbine:turbine:1.0.0")
    androidTestImplementation("androidx.test.ext:junit:1.1.5")
}
```

#### 4.2 實作核心功能（範例：新增交易）

**輸入指令**:
```
請實作 US-001: 使用者可以快速記錄支出

需要實作：
1. AddTransactionScreen (Compose UI)
2. AddTransactionViewModel (StateFlow)
3. AddTransactionUseCase
4. TransactionRepository
5. TransactionDao + Entity

使用 Clean Architecture + MVVM 模式。
```

**AI 產出**:

**1. Domain Model (Transaction.kt)**:
```kotlin
// domain/model/Transaction.kt
data class Transaction(
    val id: Long = 0,
    val type: TransactionType,
    val amount: Double,
    val categoryId: Long,
    val note: String?,
    val date: LocalDateTime,
    val createdAt: LocalDateTime = LocalDateTime.now()
)

enum class TransactionType {
    INCOME, EXPENSE
}
```

**2. UseCase (AddTransactionUseCase.kt)**:
```kotlin
// domain/usecase/AddTransactionUseCase.kt
class AddTransactionUseCase @Inject constructor(
    private val repository: TransactionRepository
) {
    suspend operator fun invoke(transaction: Transaction): Result<Long> {
        return try {
            // 業務邏輯驗證
            require(transaction.amount > 0) { "金額必須大於 0" }
            require(transaction.note?.length ?: 0 <= 100) { "備註最多 100 字" }

            val id = repository.insertTransaction(transaction)
            Result.success(id)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
}
```

**3. Repository Interface (TransactionRepository.kt)**:
```kotlin
// domain/repository/TransactionRepository.kt
interface TransactionRepository {
    suspend fun insertTransaction(transaction: Transaction): Long
    suspend fun getTransactionById(id: Long): Transaction?
    fun getTransactionsByMonth(yearMonth: String): Flow<List<Transaction>>
    suspend fun deleteTransaction(id: Long)
}
```

**4. Repository Implementation**:
```kotlin
// data/repository/TransactionRepositoryImpl.kt
class TransactionRepositoryImpl @Inject constructor(
    private val transactionDao: TransactionDao
) : TransactionRepository {

    override suspend fun insertTransaction(transaction: Transaction): Long {
        val entity = transaction.toEntity()
        return transactionDao.insert(entity)
    }

    override fun getTransactionsByMonth(yearMonth: String): Flow<List<Transaction>> {
        return transactionDao.getTransactionsByMonth(yearMonth)
            .map { entities -> entities.map { it.toDomain() } }
    }

    // ... other methods
}

// Mappers
private fun Transaction.toEntity() = TransactionEntity(
    id = id,
    type = type,
    amount = amount,
    categoryId = categoryId,
    note = note,
    date = date.toEpochSecond(ZoneOffset.UTC),
    createdAt = createdAt.toEpochSecond(ZoneOffset.UTC)
)

private fun TransactionEntity.toDomain() = Transaction(
    id = id,
    type = type,
    amount = amount,
    categoryId = categoryId,
    note = note,
    date = LocalDateTime.ofEpochSecond(date, 0, ZoneOffset.UTC),
    createdAt = LocalDateTime.ofEpochSecond(createdAt, 0, ZoneOffset.UTC)
)
```

**5. ViewModel (AddTransactionViewModel.kt)**:
```kotlin
// presentation/viewmodel/AddTransactionViewModel.kt
@HiltViewModel
class AddTransactionViewModel @Inject constructor(
    private val addTransactionUseCase: AddTransactionUseCase,
    private val getCategoriesUseCase: GetCategoriesUseCase
) : ViewModel() {

    private val _uiState = MutableStateFlow(AddTransactionUiState())
    val uiState: StateFlow<AddTransactionUiState> = _uiState.asStateFlow()

    init {
        loadCategories()
    }

    private fun loadCategories() {
        viewModelScope.launch {
            getCategoriesUseCase(TransactionType.EXPENSE).collect { categories ->
                _uiState.update { it.copy(categories = categories) }
            }
        }
    }

    fun onAmountChange(amount: String) {
        _uiState.update { it.copy(amount = amount) }
    }

    fun onCategorySelect(categoryId: Long) {
        _uiState.update { it.copy(selectedCategoryId = categoryId) }
    }

    fun onNoteChange(note: String) {
        _uiState.update { it.copy(note = note) }
    }

    fun saveTransaction() {
        viewModelScope.launch {
            _uiState.update { it.copy(isLoading = true) }

            val transaction = Transaction(
                type = TransactionType.EXPENSE,
                amount = _uiState.value.amount.toDoubleOrNull() ?: 0.0,
                categoryId = _uiState.value.selectedCategoryId ?: 0,
                note = _uiState.value.note,
                date = LocalDateTime.now()
            )

            addTransactionUseCase(transaction)
                .onSuccess {
                    _uiState.update { it.copy(isLoading = false, isSaved = true) }
                }
                .onFailure { error ->
                    _uiState.update { it.copy(isLoading = false, error = error.message) }
                }
        }
    }
}

data class AddTransactionUiState(
    val amount: String = "",
    val selectedCategoryId: Long? = null,
    val note: String = "",
    val categories: List<Category> = emptyList(),
    val isLoading: Boolean = false,
    val isSaved: Boolean = false,
    val error: String? = null
)
```

**6. Compose Screen (AddTransactionScreen.kt)**:
```kotlin
// presentation/screens/AddTransactionScreen.kt
@Composable
fun AddTransactionScreen(
    viewModel: AddTransactionViewModel = hiltViewModel(),
    onNavigateBack: () -> Unit
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()

    LaunchedEffect(uiState.isSaved) {
        if (uiState.isSaved) {
            onNavigateBack()
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("新增支出") },
                navigationIcon = {
                    IconButton(onClick = onNavigateBack) {
                        Icon(Icons.Default.ArrowBack, "返回")
                    }
                }
            )
        }
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            // 金額輸入
            OutlinedTextField(
                value = uiState.amount,
                onValueChange = viewModel::onAmountChange,
                label = { Text("金額") },
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
                modifier = Modifier.fillMaxWidth()
            )

            // 分類選擇
            Text("選擇分類", style = MaterialTheme.typography.titleMedium)
            LazyRow(
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                items(uiState.categories) { category ->
                    CategoryChip(
                        category = category,
                        isSelected = category.id == uiState.selectedCategoryId,
                        onClick = { viewModel.onCategorySelect(category.id) }
                    )
                }
            }

            // 備註輸入
            OutlinedTextField(
                value = uiState.note,
                onValueChange = viewModel::onNoteChange,
                label = { Text("備註（選填）") },
                maxLines = 3,
                modifier = Modifier.fillMaxWidth()
            )

            Spacer(modifier = Modifier.weight(1f))

            // 儲存按鈕
            Button(
                onClick = viewModel::saveTransaction,
                enabled = !uiState.isLoading && uiState.amount.isNotEmpty() && uiState.selectedCategoryId != null,
                modifier = Modifier.fillMaxWidth()
            ) {
                if (uiState.isLoading) {
                    CircularProgressIndicator(modifier = Modifier.size(24.dp))
                } else {
                    Text("儲存")
                }
            }

            // 錯誤訊息
            uiState.error?.let { error ->
                Text(
                    text = error,
                    color = MaterialTheme.colorScheme.error,
                    style = MaterialTheme.typography.bodySmall
                )
            }
        }
    }
}

@Composable
fun CategoryChip(
    category: Category,
    isSelected: Boolean,
    onClick: () -> Unit
) {
    FilterChip(
        selected = isSelected,
        onClick = onClick,
        label = { Text(category.name) },
        leadingIcon = {
            Icon(
                imageVector = rememberVectorPainter(category.icon),
                contentDescription = null,
                tint = Color(android.graphics.Color.parseColor(category.color))
            )
        }
    )
}
```

---

### 階段 6: 測試與驗證

#### 6.1 Unit Test（ViewModel）

**AI 產出**:
```kotlin
// AddTransactionViewModelTest.kt
@ExperimentalCoroutinesApi
class AddTransactionViewModelTest {

    @get:Rule
    val mainDispatcherRule = MainDispatcherRule()

    private lateinit var viewModel: AddTransactionViewModel
    private val addTransactionUseCase: AddTransactionUseCase = mockk()
    private val getCategoriesUseCase: GetCategoriesUseCase = mockk()

    @Before
    fun setup() {
        every { getCategoriesUseCase(any()) } returns flowOf(emptyList())
        viewModel = AddTransactionViewModel(addTransactionUseCase, getCategoriesUseCase)
    }

    @Test
    fun `onAmountChange updates state`() = runTest {
        viewModel.onAmountChange("500")
        assertEquals("500", viewModel.uiState.value.amount)
    }

    @Test
    fun `saveTransaction success`() = runTest {
        coEvery { addTransactionUseCase(any()) } returns Result.success(1L)

        viewModel.onAmountChange("500")
        viewModel.onCategorySelect(1L)
        viewModel.saveTransaction()

        viewModel.uiState.test {
            val state = awaitItem()
            assertTrue(state.isSaved)
            assertFalse(state.isLoading)
            assertNull(state.error)
        }
    }
}
```

---

## 📊 完整開發時程參考

| 階段 | 時間 | 產出文檔/交付物 |
|------|------|----------------|
| Stage 1-2: 需求分析 | 1.5 週 | PRD, FRD, STRIDE 分析 |
| Stage 3: 架構設計 | 1 週 | SRD, Architecture Diagram, DB Schema |
| Stage 4-5: UI 實作 | 3 週 | Compose Screens, ViewModels |
| Stage 6-7: 功能實作 | 3 週 | UseCase, Repository, Database |
| Stage 8: 整合測試 | 1 週 | Unit Tests, UI Tests |
| Stage 9: 效能優化 | 0.5 週 | 效能測試報告 |
| **總計** | **10 週 (2.5 個月)** | **完整 Android APP + 測試** |

---

## 🚀 快速開始指令

```bash
# Step 1: 建立專案
mkdir MoneyTracker_Pro && cd MoneyTracker_Pro
mkdir -p app/src/main/java/com/moneytracker/pro docs

# Step 2: 複製 AISDLC
cp -r /Users/wuweihong/Cursor_Project/AISDLC_ALL/AISDLC_v0.09 ./AISDLC

# Step 3: 開啟 Cursor AI
# File → Open Folder → 選擇 MoneyTracker_Pro
```

**Cursor AI Chat 第一個指令**:
```
請載入 AISDLC Framework 並開始 Greenfield Android App 開發流程：

讀取：AISDLC/AISDLC_INIT.md

專案名稱：MoneyTracker Pro
平台：Android Native App
技術棧：Kotlin + Jetpack Compose + MVVM + Hilt + Room + SQLCipher
目標：智能記帳 APP（記帳、報表、預算管理、雲端同步）
```

---

## 📚 參考文檔

- [Greenfield SOP](../../scenarios/greenfield/SOP.md)
- [Mobile Architecture Guidelines](../system/architecture/Mobile_Architecture_Guidelines.md)
- [Security Architecture Checklist](../system/architecture/Security_Architecture_Checklist.md)
- [Performance Test Plan Template](../system/testing/Performance_Test_Plan_Template.md)

---

**維護記錄**:
- v0.01 (2025-12-13): 初版建立（Android Kotlin + Compose + MVVM 完整範例）
  - 技術棧：Kotlin 1.9+ + Jetpack Compose + Hilt + Room + SQLCipher
  - 架構：Clean Architecture (3-Layer MVVM)
  - 包含完整程式碼範例（ViewModel, UseCase, Repository, Compose UI）
  - 包含 Unit Test 範例
