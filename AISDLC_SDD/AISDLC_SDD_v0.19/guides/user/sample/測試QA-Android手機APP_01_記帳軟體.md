# 測試與 QA：Android 手機 APP（記帳軟體）

> **場景**: Testing & QA - Android 記帳 APP 全面測試與品質保證
> **技術棧**: Kotlin + Jetpack Compose + MVVM + Hilt + JUnit + Espresso
> **AISDLC 版本**: v0.01
> **更新日期**: 2025-12-15


> **SDD v0.01 使用者提示**：本指南基於 AISDLC-SDD v0.01。使用 AISDLC-SDD v0.01 時，請同時參考對應場景的 SDD Enhancement 文件（`scenarios/{scenario}/SDD_{SCENARIO}_ENHANCEMENT.md`），並確認所有 SCG 閘門步驟已整合到您的工作流程中。

---
---

## 📋 目錄

1. [第一步：Cursor AI 專案路徑設定](#第一步cursor-ai-專案路徑設定)
2. [第二步：AISDLC 框架安裝](#第二步aisdlc-框架安裝)
3. [第三步：Claude Code 完整測試流程](#第三步claude-code-完整測試流程)
4. [附錄：命令速查表](#附錄命令速查表)

---

## 第一步：Cursor AI 專案路徑設定

### 1.1 分析現有專案結構

**假設現有專案結構**:
```
ExpenseTrackerApp/
├── app/
│   ├── src/
│   │   ├── main/
│   │   │   ├── java/com/example/expensetracker/
│   │   │   │   ├── ui/
│   │   │   │   ├── data/
│   │   │   │   ├── domain/
│   │   │   │   └── di/
│   │   │   └── res/
│   │   ├── test/                      # ⚠️  單元測試（需補充）
│   │   │   └── java/com/example/expensetracker/
│   │   └── androidTest/               # ⚠️  整合測試（需補充）
│   │       └── java/com/example/expensetracker/
│   └── build.gradle.kts
├── gradle/
├── build.gradle.kts
└── settings.gradle.kts
```

**測試覆蓋率問題**:
- ❌ 單元測試覆蓋率 < 30%
- ❌ 無 UI 測試（Compose UI 未測試）
- ❌ 無整合測試（Repository/ViewModel）
- ❌ 無端對端測試（完整流程）
- ❌ 無 API 測試（後端整合）

### 1.2 建立測試專案結構

**在終端機執行**:
```bash
cd ~/Projects/ExpenseTrackerApp

# 建立測試目錄
mkdir -p app/src/test/java/com/example/expensetracker
mkdir -p app/src/test/java/com/example/expensetracker/data
mkdir -p app/src/test/java/com/example/expensetracker/domain
mkdir -p app/src/test/java/com/example/expensetracker/ui

mkdir -p app/src/androidTest/java/com/example/expensetracker
mkdir -p app/src/androidTest/java/com/example/expensetracker/ui
mkdir -p app/src/androidTest/java/com/example/expensetracker/e2e

# 建立測試報告目錄
mkdir -p test-reports
mkdir -p test-reports/unit-tests
mkdir -p test-reports/integration-tests
mkdir -p test-reports/ui-tests
mkdir -p test-reports/coverage

# 建立文檔目錄
mkdir -p Docs
mkdir -p Docs/testing                  # 測試計畫
mkdir -p Docs/test-cases               # 測試案例
mkdir -p Docs/reports                  # 測試報告

# 驗證
tree -L 3 -d
```

**完整專案結構**:
```
ExpenseTrackerApp/
├── app/
│   ├── src/
│   │   ├── main/                      # 🎯 主程式
│   │   ├── test/                      # 📝 單元測試
│   │   │   └── java/com/example/expensetracker/
│   │   │       ├── data/
│   │   │       ├── domain/
│   │   │       └── ui/
│   │   └── androidTest/               # 🧪 整合測試 & UI 測試
│   │       └── java/com/example/expensetracker/
│   │           ├── ui/
│   │           └── e2e/
│   └── build.gradle.kts
├── test-reports/                      # 📊 測試報告
│   ├── unit-tests/
│   ├── integration-tests/
│   ├── ui-tests/
│   └── coverage/
├── Docs/                              # 📄 AISDLC 文檔
│   ├── testing/
│   ├── test-cases/
│   └── reports/
└── AISDLC_SDD_v0.01/                     # 🔴 步驟 2 安裝
```

### 1.3 開啟 Android Studio 與 Cursor AI

**步驟**:
1. **Android Studio**: 打開現有專案 `~/Projects/ExpenseTrackerApp`
2. **Cursor AI**: `File` → `Open Folder...` → 選擇 `~/Projects/ExpenseTrackerApp`

---

## 第二步：AISDLC 框架安裝

### 2.1 方法一：符號連結（推薦）

```bash
cd ~/Projects/ExpenseTrackerApp

ln -s /Users/你的用戶名/Cursor_Project/AISDLC_ALL/AISDLC_v0.09 AISDLC_v0.09

ls -lah | grep AISDLC
```

### 2.2 方法二：複製

```bash
cp -r /Users/你的用戶名/Cursor_Project/AISDLC_ALL/AISDLC_v0.09 ~/Projects/ExpenseTrackerApp/

ls AISDLC_SDD_v0.01/
```

### 2.3 驗證安裝

```bash
ls -la AISDLC_SDD_v0.01/AISDLC_INIT.md
cat AISDLC_SDD_v0.01/scenarios/testing/README.md | head -30
```

---

## 第三步：Claude Code 完整測試流程

### 階段 1：測試計畫與策略（1 週）

#### 3.1.1 啟動測試計畫 Workflow

**在 Claude Code 輸入**:
```
請載入 AISDLC_INIT.md，我要進行「測試與 QA」場景。

目標：Android 記帳 APP 完整測試與品質保證

技術棧：
- 前端：Kotlin + Jetpack Compose + MVVM + Hilt
- 資料庫：Room Database
- 後端：Python FastAPI（可選）

目前狀況：
1. 單元測試覆蓋率 < 30%
2. 無 UI 測試
3. 無整合測試
4. 無端對端測試
5. 無 API 測試

請執行「test-planning-and-strategy」workflow，生成完整測試計畫。
```

#### 3.1.2 生成測試計畫

**在 Claude Code 輸入**:
```
請載入 QA Agent (Quincy)，生成測試計畫：

測試範圍：
1. 單元測試（Unit Tests）
   - ViewModel 邏輯
   - Repository 資料存取
   - Use Cases（Domain Layer）
   - Utility Functions

2. 整合測試（Integration Tests）
   - Room Database
   - API 整合
   - ViewModel + Repository

3. UI 測試（UI Tests）
   - Compose UI 元件
   - 使用者互動流程
   - 導航測試

4. 端對端測試（E2E Tests）
   - 完整業務流程（新增交易 → 查看清單 → 編輯 → 刪除）
   - 跨頁面流程

5. 非功能性測試（Non-Functional Tests）
   - 效能測試
   - 安全性測試
   - 可用性測試

請生成測試計畫文檔：`Docs/testing/test-plan.md`
```

**預期輸出** (`Docs/testing/test-plan.md`):
```markdown
# 測試計畫

## 測試目標

1. **提升測試覆蓋率**: 從 30% 提升至 80%+
2. **確保功能正確性**: 所有核心功能正常運作
3. **保證 UI 一致性**: Compose UI 元件正確渲染
4. **驗證整合穩定性**: 各層級整合無誤
5. **確保使用者體驗**: 完整流程順暢

## 測試策略

### 測試金字塔

```
        /\
       /  \        E2E Tests (5%)
      /____\       UI Tests (15%)
     /      \      Integration Tests (30%)
    /________\     Unit Tests (50%)
```

### 測試優先級

| 優先級 | 測試類型 | 覆蓋率目標 | 執行頻率 |
|--------|---------|----------|---------|
| P0 | 單元測試 | 80%+ | 每次 Commit |
| P1 | 整合測試 | 70%+ | 每次 Push |
| P2 | UI 測試 | 60%+ | 每日/Release 前 |
| P3 | E2E 測試 | 關鍵流程 | Release 前 |

## 測試範圍

### 1. 單元測試（50%）

#### 1.1 ViewModel 測試
- **檔案**: `TransactionViewModel`
- **測試項目**:
  - ✅ 載入交易清單
  - ✅ 新增交易（成功/失敗）
  - ✅ 更新交易
  - ✅ 刪除交易
  - ✅ 搜尋交易
  - ✅ 篩選交易（類別、日期）
  - ✅ 排序交易
  - ✅ 計算總收入/支出
  - ✅ 錯誤處理

#### 1.2 Repository 測試
- **檔案**: `TransactionRepository`
- **測試項目**:
  - ✅ CRUD 操作
  - ✅ 查詢條件（WHERE、ORDER BY）
  - ✅ 資料映射（Entity ↔ Model）
  - ✅ 錯誤處理（資料庫異常）

#### 1.3 Use Cases 測試
- **檔案**: `GetTransactionsUseCase`, `AddTransactionUseCase`
- **測試項目**:
  - ✅ 業務邏輯正確性
  - ✅ 輸入驗證
  - ✅ 邊界條件

### 2. 整合測試（30%）

#### 2.1 Room Database 測試
- **測試項目**:
  - ✅ 資料庫遷移（Migration）
  - ✅ DAO 查詢正確性
  - ✅ 外鍵約束
  - ✅ 索引效能

#### 2.2 ViewModel + Repository 整合
- **測試項目**:
  - ✅ 完整資料流（ViewModel → Repository → Database）
  - ✅ Flow/LiveData 更新
  - ✅ 錯誤傳播

### 3. UI 測試（15%）

#### 3.1 Compose UI 元件測試
- **測試元件**:
  - ✅ `TransactionListScreen`
  - ✅ `AddTransactionScreen`
  - ✅ `TransactionItem`
  - ✅ `DatePicker`
  - ✅ `CategorySelector`

#### 3.2 使用者互動測試
- **測試項目**:
  - ✅ 點擊按鈕
  - ✅ 輸入表單
  - ✅ 滑動清單
  - ✅ 導航跳轉

### 4. 端對端測試（5%）

#### 4.1 完整業務流程
- **測試場景**:
  - ✅ 新增交易 → 查看清單 → 編輯 → 刪除
  - ✅ 搜尋 → 篩選 → 排序
  - ✅ 切換頁面 → 返回

## 測試工具

| 測試類型 | 工具 | 版本 |
|---------|------|-----|
| 單元測試 | JUnit 5 | 5.10.1 |
| Mock | Mockito / MockK | 5.8.0 / 1.13.8 |
| Coroutines 測試 | kotlinx-coroutines-test | 1.7.3 |
| Room 測試 | androidx.room:room-testing | 2.6.1 |
| Compose UI 測試 | androidx.compose.ui:ui-test-junit4 | 1.5.4 |
| E2E 測試 | Espresso + Compose | 3.5.1 |
| 測試覆蓋率 | JaCoCo | 0.8.11 |

## 測試時程

| 階段 | 週數 | 交付項目 |
|------|-----|---------|
| 1. 測試計畫 | 1 週 | 測試計畫文檔、測試案例 |
| 2. 單元測試 | 2 週 | 80%+ 覆蓋率 |
| 3. 整合測試 | 1.5 週 | 關鍵整合點測試 |
| 4. UI 測試 | 1.5 週 | 所有畫面測試 |
| 5. E2E 測試 | 1 週 | 關鍵流程測試 |
| 6. 測試報告 | 0.5 週 | 測試報告、改善建議 |

**總計**: 7.5 週

## 測試環境

| 環境 | 用途 | 設備 |
|------|-----|------|
| 本地開發 | 單元測試、UI 測試 | Android Studio Emulator |
| CI/CD | 自動化測試 | GitHub Actions + Firebase Test Lab |
| 實機測試 | E2E 測試 | 實體設備（3-5 台） |

## 成功標準

- ✅ 單元測試覆蓋率 > 80%
- ✅ 整合測試覆蓋率 > 70%
- ✅ UI 測試覆蓋率 > 60%
- ✅ 所有 P0/P1 測試通過率 100%
- ✅ 無 Critical/High 級別 Bug
- ✅ CI/CD 測試執行時間 < 10 分鐘
```

---

### 階段 2：單元測試實作（2 週）

#### 3.2.1 配置測試依賴

**在 Claude Code 輸入**:
```
請配置測試依賴，包含：

1. JUnit 5
2. Mockito / MockK
3. Coroutines Test
4. Turbine（Flow 測試）
5. Truth（斷言庫）

請更新 `app/build.gradle.kts`
```

**Claude Code 生成** (`app/build.gradle.kts`):
```kotlin
plugins {
    id("com.android.application")
    kotlin("android")
    kotlin("kapt")
    id("dagger.hilt.android.plugin")
    id("jacoco")  // ✅ 測試覆蓋率
}

android {
    namespace = "com.example.expensetracker"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.example.expensetracker"
        minSdk = 24
        targetSdk = 34
        versionCode = 1
        versionName = "1.0"

        testInstrumentationRunner = "com.example.expensetracker.HiltTestRunner"
    }

    buildTypes {
        debug {
            enableUnitTestCoverage = true
            enableAndroidTestCoverage = true
        }
        release {
            isMinifyEnabled = true
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
    }

    // ✅ Compose 配置
    buildFeatures {
        compose = true
    }

    composeOptions {
        kotlinCompilerExtensionVersion = "1.5.3"
    }

    // ✅ JUnit 5 配置
    testOptions {
        unitTests {
            isIncludeAndroidResources = true
            isReturnDefaultValues = true
        }
        unitTests.all {
            it.useJUnitPlatform()  // ✅ 啟用 JUnit 5
        }
    }
}

dependencies {
    // 主程式依賴...
    implementation("androidx.core:core-ktx:1.12.0")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.7.0")
    implementation("androidx.activity:activity-compose:1.8.2")
    implementation(platform("androidx.compose:compose-bom:2023.10.01"))
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.hilt:hilt-navigation-compose:1.1.0")
    implementation("com.google.dagger:hilt-android:2.48.1")
    kapt("com.google.dagger:hilt-android-compiler:2.48.1")

    // Room Database
    implementation("androidx.room:room-runtime:2.6.1")
    implementation("androidx.room:room-ktx:2.6.1")
    kapt("androidx.room:room-compiler:2.6.1")

    // ==================== 單元測試 ====================

    // ✅ JUnit 5
    testImplementation("org.junit.jupiter:junit-jupiter-api:5.10.1")
    testRuntimeOnly("org.junit.jupiter:junit-jupiter-engine:5.10.1")
    testImplementation("org.junit.jupiter:junit-jupiter-params:5.10.1")  // 參數化測試

    // ✅ MockK（Kotlin Mock Framework）
    testImplementation("io.mockk:mockk:1.13.8")
    testImplementation("io.mockk:mockk-android:1.13.8")

    // ✅ Coroutines Test
    testImplementation("org.jetbrains.kotlinx:kotlinx-coroutines-test:1.7.3")

    // ✅ Turbine（Flow 測試）
    testImplementation("app.cash.turbine:turbine:1.0.0")

    // ✅ Truth（Google 斷言庫）
    testImplementation("com.google.truth:truth:1.1.5")

    // ✅ Arch Core Testing（LiveData 測試）
    testImplementation("androidx.arch.core:core-testing:2.2.0")

    // ✅ Room Testing
    testImplementation("androidx.room:room-testing:2.6.1")

    // ==================== 整合測試 & UI 測試 ====================

    // ✅ Hilt Testing
    androidTestImplementation("com.google.dagger:hilt-android-testing:2.48.1")
    kaptAndroidTest("com.google.dagger:hilt-android-compiler:2.48.1")

    // ✅ Compose UI Testing
    androidTestImplementation("androidx.compose.ui:ui-test-junit4")
    debugImplementation("androidx.compose.ui:ui-test-manifest")

    // ✅ Espresso
    androidTestImplementation("androidx.test.espresso:espresso-core:3.5.1")
    androidTestImplementation("androidx.test:runner:1.5.2")
    androidTestImplementation("androidx.test:rules:1.5.0")

    // ✅ Truth（Android 測試）
    androidTestImplementation("com.google.truth:truth:1.1.5")
}

// ✅ JaCoCo 測試覆蓋率配置
tasks.register<JacocoReport>("jacocoTestReport") {
    dependsOn("testDebugUnitTest")

    reports {
        xml.required.set(true)
        html.required.set(true)
    }

    val fileFilter = listOf(
        "**/R.class",
        "**/R$*.class",
        "**/BuildConfig.*",
        "**/Manifest*.*",
        "**/*Test*.*",
        "android/**/*.*",
        "**/*_Hilt*.*",
        "**/Hilt_*.*",
        "**/*_Factory.*",
        "**/*_MembersInjector.*"
    )

    val debugTree = fileTree("${buildDir}/tmp/kotlin-classes/debug") {
        exclude(fileFilter)
    }

    val mainSrc = "${project.projectDir}/src/main/java"

    sourceDirectories.setFrom(files(mainSrc))
    classDirectories.setFrom(files(debugTree))
    executionData.setFrom(fileTree(buildDir) {
        include("jacoco/testDebugUnitTest.exec")
    })
}
```

#### 3.2.2 ViewModel 單元測試

**在 Claude Code 輸入**:
```
請為 TransactionViewModel 編寫完整單元測試：

測試項目：
1. 載入交易清單（成功/失敗）
2. 新增交易（成功/失敗/驗證錯誤）
3. 更新交易
4. 刪除交易
5. 搜尋交易
6. 篩選交易（類別、日期範圍）
7. 計算統計資料（總收入/支出）

請生成測試檔案：`app/src/test/java/com/example/expensetracker/ui/TransactionViewModelTest.kt`
```

**Claude Code 生成** (`TransactionViewModelTest.kt`):
```kotlin
package com.example.expensetracker.ui

import app.cash.turbine.test
import com.example.expensetracker.data.model.Transaction
import com.example.expensetracker.data.model.TransactionType
import com.example.expensetracker.data.repository.TransactionRepository
import com.example.expensetracker.ui.transaction.TransactionUiState
import com.example.expensetracker.ui.transaction.TransactionViewModel
import com.google.common.truth.Truth.assertThat
import io.mockk.*
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.flow
import kotlinx.coroutines.flow.flowOf
import kotlinx.coroutines.test.*
import org.junit.jupiter.api.*
import org.junit.jupiter.api.Assertions.*
import java.time.LocalDateTime

@OptIn(ExperimentalCoroutinesApi::class)
class TransactionViewModelTest {

    // ✅ Mocks
    private lateinit var repository: TransactionRepository
    private lateinit var viewModel: TransactionViewModel

    // ✅ Test Dispatcher
    private val testDispatcher = StandardTestDispatcher()

    @BeforeEach
    fun setup() {
        // ✅ 設定 Main Dispatcher 為 Test Dispatcher
        Dispatchers.setMain(testDispatcher)

        // ✅ 初始化 Mock
        repository = mockk()
        viewModel = TransactionViewModel(repository)
    }

    @AfterEach
    fun tearDown() {
        Dispatchers.resetMain()
        clearAllMocks()
    }

    // ==================== 載入交易清單 ====================

    @Test
    fun `載入交易清單 - 成功`() = runTest {
        // Given
        val mockTransactions = listOf(
            Transaction(id = 1, title = "午餐", amount = 150.0, type = TransactionType.EXPENSE, categoryId = 1, timestamp = System.currentTimeMillis()),
            Transaction(id = 2, title = "薪水", amount = 30000.0, type = TransactionType.INCOME, categoryId = 2, timestamp = System.currentTimeMillis())
        )
        every { repository.getAllTransactions() } returns flowOf(mockTransactions)

        // When
        viewModel.uiState.test {
            // ✅ 初始狀態
            assertThat(awaitItem()).isEqualTo(TransactionUiState.Loading)

            // ✅ 成功狀態
            val successState = awaitItem() as TransactionUiState.Success
            assertThat(successState.transactions).hasSize(2)
            assertThat(successState.transactions[0].title).isEqualTo("午餐")
            assertThat(successState.transactions[1].title).isEqualTo("薪水")
        }

        // Then
        verify(exactly = 1) { repository.getAllTransactions() }
    }

    @Test
    fun `載入交易清單 - 失敗`() = runTest {
        // Given
        val exception = RuntimeException("Database error")
        every { repository.getAllTransactions() } returns flow { throw exception }

        // When
        viewModel.uiState.test {
            assertThat(awaitItem()).isEqualTo(TransactionUiState.Loading)

            // ✅ 錯誤狀態
            val errorState = awaitItem() as TransactionUiState.Error
            assertThat(errorState.message).contains("Database error")
        }
    }

    @Test
    fun `載入交易清單 - 空清單`() = runTest {
        // Given
        every { repository.getAllTransactions() } returns flowOf(emptyList())

        // When
        viewModel.uiState.test {
            assertThat(awaitItem()).isEqualTo(TransactionUiState.Loading)

            // ✅ 成功但無資料
            val successState = awaitItem() as TransactionUiState.Success
            assertThat(successState.transactions).isEmpty()
        }
    }

    // ==================== 新增交易 ====================

    @Test
    fun `新增交易 - 成功`() = runTest {
        // Given
        val newTransaction = Transaction(
            id = 0,
            title = "晚餐",
            amount = 250.0,
            type = TransactionType.EXPENSE,
            categoryId = 1,
            timestamp = System.currentTimeMillis()
        )
        coEvery { repository.insertTransaction(any()) } returns Result.success(Unit)

        // When
        val result = viewModel.addTransaction(newTransaction)

        // Then
        assertThat(result.isSuccess).isTrue()
        coVerify(exactly = 1) { repository.insertTransaction(newTransaction) }
    }

    @Test
    fun `新增交易 - 驗證錯誤（標題為空）`() = runTest {
        // Given
        val invalidTransaction = Transaction(
            id = 0,
            title = "",  // ❌ 空標題
            amount = 250.0,
            type = TransactionType.EXPENSE,
            categoryId = 1,
            timestamp = System.currentTimeMillis()
        )

        // When
        val result = viewModel.addTransaction(invalidTransaction)

        // Then
        assertThat(result.isFailure).isTrue()
        assertThat(result.exceptionOrNull()?.message).contains("標題不可為空")
        coVerify(exactly = 0) { repository.insertTransaction(any()) }  // ✅ 不應呼叫 Repository
    }

    @Test
    fun `新增交易 - 驗證錯誤（金額 <= 0）`() = runTest {
        // Given
        val invalidTransaction = Transaction(
            id = 0,
            title = "測試",
            amount = 0.0,  // ❌ 金額為 0
            type = TransactionType.EXPENSE,
            categoryId = 1,
            timestamp = System.currentTimeMillis()
        )

        // When
        val result = viewModel.addTransaction(invalidTransaction)

        // Then
        assertThat(result.isFailure).isTrue()
        assertThat(result.exceptionOrNull()?.message).contains("金額必須大於 0")
    }

    @Test
    fun `新增交易 - 資料庫錯誤`() = runTest {
        // Given
        val newTransaction = Transaction(
            id = 0,
            title = "測試",
            amount = 100.0,
            type = TransactionType.EXPENSE,
            categoryId = 1,
            timestamp = System.currentTimeMillis()
        )
        val exception = RuntimeException("Database insert failed")
        coEvery { repository.insertTransaction(any()) } returns Result.failure(exception)

        // When
        val result = viewModel.addTransaction(newTransaction)

        // Then
        assertThat(result.isFailure).isTrue()
        assertThat(result.exceptionOrNull()).isEqualTo(exception)
    }

    // ==================== 刪除交易 ====================

    @Test
    fun `刪除交易 - 成功`() = runTest {
        // Given
        val transactionId = 123L
        coEvery { repository.deleteTransaction(transactionId) } returns Result.success(Unit)

        // When
        val result = viewModel.deleteTransaction(transactionId)

        // Then
        assertThat(result.isSuccess).isTrue()
        coVerify(exactly = 1) { repository.deleteTransaction(transactionId) }
    }

    // ==================== 搜尋交易 ====================

    @Test
    fun `搜尋交易 - 依標題搜尋`() = runTest {
        // Given
        val allTransactions = listOf(
            Transaction(id = 1, title = "午餐", amount = 150.0, type = TransactionType.EXPENSE, categoryId = 1, timestamp = System.currentTimeMillis()),
            Transaction(id = 2, title = "晚餐", amount = 200.0, type = TransactionType.EXPENSE, categoryId = 1, timestamp = System.currentTimeMillis()),
            Transaction(id = 3, title = "薪水", amount = 30000.0, type = TransactionType.INCOME, categoryId = 2, timestamp = System.currentTimeMillis())
        )
        every { repository.getAllTransactions() } returns flowOf(allTransactions)

        // When
        viewModel.searchTransactions("午")

        // Then
        viewModel.uiState.test {
            val state = awaitItem() as TransactionUiState.Success
            assertThat(state.transactions).hasSize(1)
            assertThat(state.transactions[0].title).isEqualTo("午餐")
        }
    }

    // ==================== 篩選交易 ====================

    @Test
    fun `篩選交易 - 依類別篩選`() = runTest {
        // Given
        val allTransactions = listOf(
            Transaction(id = 1, title = "午餐", amount = 150.0, type = TransactionType.EXPENSE, categoryId = 1, timestamp = System.currentTimeMillis()),
            Transaction(id = 2, title = "薪水", amount = 30000.0, type = TransactionType.INCOME, categoryId = 2, timestamp = System.currentTimeMillis())
        )
        every { repository.getTransactionsByCategoryId(1) } returns flowOf(listOf(allTransactions[0]))

        // When
        viewModel.filterByCategory(1)

        // Then
        viewModel.uiState.test {
            val state = awaitItem() as TransactionUiState.Success
            assertThat(state.transactions).hasSize(1)
            assertThat(state.transactions[0].categoryId).isEqualTo(1)
        }
    }

    // ==================== 計算統計 ====================

    @Test
    fun `計算統計資料 - 總收入與總支出`() = runTest {
        // Given
        val transactions = listOf(
            Transaction(id = 1, title = "午餐", amount = 150.0, type = TransactionType.EXPENSE, categoryId = 1, timestamp = System.currentTimeMillis()),
            Transaction(id = 2, title = "晚餐", amount = 200.0, type = TransactionType.EXPENSE, categoryId = 1, timestamp = System.currentTimeMillis()),
            Transaction(id = 3, title = "薪水", amount = 30000.0, type = TransactionType.INCOME, categoryId = 2, timestamp = System.currentTimeMillis()),
            Transaction(id = 4, title = "兼職", amount = 5000.0, type = TransactionType.INCOME, categoryId = 2, timestamp = System.currentTimeMillis())
        )
        every { repository.getAllTransactions() } returns flowOf(transactions)

        // When
        val stats = viewModel.calculateStats(transactions)

        // Then
        assertThat(stats.totalIncome).isEqualTo(35000.0)  // 30000 + 5000
        assertThat(stats.totalExpense).isEqualTo(350.0)   // 150 + 200
        assertThat(stats.balance).isEqualTo(34650.0)      // 35000 - 350
    }

    // ==================== 參數化測試（JUnit 5） ====================

    @ParameterizedTest
    @CsvSource(
        "100.0, 交通, true",
        "0.0, 午餐, false",
        "-50.0, 購物, false",
        "1000.0, '', false"
    )
    fun `新增交易 - 驗證參數化測試`(amount: Double, title: String, shouldSucceed: Boolean) = runTest {
        // Given
        val transaction = Transaction(
            id = 0,
            title = title,
            amount = amount,
            type = TransactionType.EXPENSE,
            categoryId = 1,
            timestamp = System.currentTimeMillis()
        )

        if (shouldSucceed) {
            coEvery { repository.insertTransaction(any()) } returns Result.success(Unit)
        }

        // When
        val result = viewModel.addTransaction(transaction)

        // Then
        assertThat(result.isSuccess).isEqualTo(shouldSucceed)
    }
}
```

**執行單元測試**:
```bash
# 執行所有單元測試
./gradlew test

# 執行特定測試類別
./gradlew test --tests TransactionViewModelTest

# 生成測試覆蓋率報告
./gradlew jacocoTestReport

# 查看報告
open app/build/reports/jacoco/jacocoTestReport/html/index.html
```

---

### 階段 3：整合測試（1.5 週）

#### 3.3.1 Room Database 整合測試

**在 Claude Code 輸入**:
```
請為 Room Database 編寫整合測試：

測試項目：
1. TransactionDao CRUD 操作
2. 查詢條件（WHERE、ORDER BY）
3. 資料庫遷移（Migration）
4. 外鍵約束

請生成測試檔案：`app/src/androidTest/java/com/example/expensetracker/data/TransactionDaoTest.kt`
```

**Claude Code 生成** (`TransactionDaoTest.kt`):
```kotlin
package com.example.expensetracker.data

import androidx.arch.core.executor.testing.InstantTaskExecutorRule
import androidx.room.Room
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.example.expensetracker.data.local.AppDatabase
import com.example.expensetracker.data.local.TransactionDao
import com.example.expensetracker.data.local.entity.TransactionEntity
import com.example.expensetracker.data.model.TransactionType
import com.google.common.truth.Truth.assertThat
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.test.runTest
import org.junit.*
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class TransactionDaoTest {

    // ✅ Rule: LiveData 同步執行
    @get:Rule
    val instantTaskExecutorRule = InstantTaskExecutorRule()

    private lateinit var database: AppDatabase
    private lateinit var transactionDao: TransactionDao

    @Before
    fun setup() {
        // ✅ 建立 In-Memory Database（測試用）
        database = Room.inMemoryDatabaseBuilder(
            ApplicationProvider.getApplicationContext(),
            AppDatabase::class.java
        )
            .allowMainThreadQueries()  // ✅ 測試允許主執行緒查詢
            .build()

        transactionDao = database.transactionDao()
    }

    @After
    fun tearDown() {
        database.close()
    }

    // ==================== CRUD 操作 ====================

    @Test
    fun insertTransaction_and_getById() = runTest {
        // Given
        val transaction = TransactionEntity(
            id = 0,
            title = "午餐",
            amount = 150.0,
            type = TransactionType.EXPENSE,
            categoryId = 1,
            timestamp = System.currentTimeMillis()
        )

        // When
        val insertedId = transactionDao.insertTransaction(transaction)
        val retrieved = transactionDao.getTransactionById(insertedId).first()

        // Then
        assertThat(retrieved).isNotNull()
        assertThat(retrieved?.title).isEqualTo("午餐")
        assertThat(retrieved?.amount).isEqualTo(150.0)
    }

    @Test
    fun updateTransaction() = runTest {
        // Given
        val transaction = TransactionEntity(
            id = 0,
            title = "午餐",
            amount = 150.0,
            type = TransactionType.EXPENSE,
            categoryId = 1,
            timestamp = System.currentTimeMillis()
        )
        val insertedId = transactionDao.insertTransaction(transaction)

        // When
        val updated = transaction.copy(id = insertedId, amount = 200.0)
        transactionDao.updateTransaction(updated)
        val retrieved = transactionDao.getTransactionById(insertedId).first()

        // Then
        assertThat(retrieved?.amount).isEqualTo(200.0)
    }

    @Test
    fun deleteTransaction() = runTest {
        // Given
        val transaction = TransactionEntity(
            id = 0,
            title = "午餐",
            amount = 150.0,
            type = TransactionType.EXPENSE,
            categoryId = 1,
            timestamp = System.currentTimeMillis()
        )
        val insertedId = transactionDao.insertTransaction(transaction)

        // When
        transactionDao.deleteTransaction(transaction.copy(id = insertedId))
        val retrieved = transactionDao.getTransactionById(insertedId).first()

        // Then
        assertThat(retrieved).isNull()
    }

    // ==================== 查詢測試 ====================

    @Test
    fun getAllTransactions_orderedByTimestampDesc() = runTest {
        // Given
        val transaction1 = TransactionEntity(0, "午餐", 150.0, TransactionType.EXPENSE, 1, 1000L)
        val transaction2 = TransactionEntity(0, "晚餐", 200.0, TransactionType.EXPENSE, 1, 2000L)
        val transaction3 = TransactionEntity(0, "早餐", 100.0, TransactionType.EXPENSE, 1, 3000L)

        transactionDao.insertTransaction(transaction1)
        transactionDao.insertTransaction(transaction2)
        transactionDao.insertTransaction(transaction3)

        // When
        val transactions = transactionDao.getAllTransactions().first()

        // Then
        assertThat(transactions).hasSize(3)
        assertThat(transactions[0].title).isEqualTo("早餐")  // ✅ 最新的在前
        assertThat(transactions[1].title).isEqualTo("晚餐")
        assertThat(transactions[2].title).isEqualTo("午餐")
    }

    @Test
    fun getTransactionsByCategoryId() = runTest {
        // Given
        val transaction1 = TransactionEntity(0, "午餐", 150.0, TransactionType.EXPENSE, 1, 1000L)
        val transaction2 = TransactionEntity(0, "交通", 50.0, TransactionType.EXPENSE, 2, 2000L)
        val transaction3 = TransactionEntity(0, "晚餐", 200.0, TransactionType.EXPENSE, 1, 3000L)

        transactionDao.insertTransaction(transaction1)
        transactionDao.insertTransaction(transaction2)
        transactionDao.insertTransaction(transaction3)

        // When
        val transactions = transactionDao.getTransactionsByCategoryId(1).first()

        // Then
        assertThat(transactions).hasSize(2)
        assertThat(transactions.all { it.categoryId == 1L }).isTrue()
    }

    @Test
    fun getTransactionsByType() = runTest {
        // Given
        val transaction1 = TransactionEntity(0, "午餐", 150.0, TransactionType.EXPENSE, 1, 1000L)
        val transaction2 = TransactionEntity(0, "薪水", 30000.0, TransactionType.INCOME, 2, 2000L)
        val transaction3 = TransactionEntity(0, "獎金", 5000.0, TransactionType.INCOME, 2, 3000L)

        transactionDao.insertTransaction(transaction1)
        transactionDao.insertTransaction(transaction2)
        transactionDao.insertTransaction(transaction3)

        // When
        val incomeTransactions = transactionDao.getTransactionsByType(TransactionType.INCOME).first()

        // Then
        assertThat(incomeTransactions).hasSize(2)
        assertThat(incomeTransactions.all { it.type == TransactionType.INCOME }).isTrue()
    }

    // ==================== 統計查詢 ====================

    @Test
    fun getTotalAmountByType() = runTest {
        // Given
        val transaction1 = TransactionEntity(0, "午餐", 150.0, TransactionType.EXPENSE, 1, 1000L)
        val transaction2 = TransactionEntity(0, "晚餐", 200.0, TransactionType.EXPENSE, 1, 2000L)
        val transaction3 = TransactionEntity(0, "薪水", 30000.0, TransactionType.INCOME, 2, 3000L)

        transactionDao.insertTransaction(transaction1)
        transactionDao.insertTransaction(transaction2)
        transactionDao.insertTransaction(transaction3)

        // When
        val totalExpense = transactionDao.getTotalAmountByType(TransactionType.EXPENSE).first()
        val totalIncome = transactionDao.getTotalAmountByType(TransactionType.INCOME).first()

        // Then
        assertThat(totalExpense).isEqualTo(350.0)  // 150 + 200
        assertThat(totalIncome).isEqualTo(30000.0)
    }
}
```

---

### 階段 4：UI 測試（1.5 週）

#### 3.4.1 Compose UI 測試

**在 Claude Code 輸入**:
```
請為 Compose UI 元件編寫測試：

測試元件：
1. TransactionListScreen
2. AddTransactionScreen
3. TransactionItem

測試項目：
- 元件渲染
- 使用者互動（點擊、輸入、滑動）
- 導航跳轉

請生成測試檔案：`app/src/androidTest/java/com/example/expensetracker/ui/TransactionListScreenTest.kt`
```

**Claude Code 生成** (`TransactionListScreenTest.kt`):
```kotlin
package com.example.expensetracker.ui

import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.example.expensetracker.data.model.Transaction
import com.example.expensetracker.data.model.TransactionType
import com.example.expensetracker.ui.transaction.TransactionListScreen
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class TransactionListScreenTest {

    @get:Rule
    val composeTestRule = createComposeRule()

    @Test
    fun transactionListScreen_displayTransactions() {
        // Given
        val mockTransactions = listOf(
            Transaction(1, "午餐", 150.0, TransactionType.EXPENSE, 1, System.currentTimeMillis()),
            Transaction(2, "薪水", 30000.0, TransactionType.INCOME, 2, System.currentTimeMillis())
        )

        // When
        composeTestRule.setContent {
            TransactionListScreen(
                transactions = mockTransactions,
                onTransactionClick = {},
                onAddClick = {}
            )
        }

        // Then
        composeTestRule.onNodeWithText("午餐").assertIsDisplayed()
        composeTestRule.onNodeWithText("薪水").assertIsDisplayed()
        composeTestRule.onNodeWithText("$150.00").assertIsDisplayed()
        composeTestRule.onNodeWithText("$30000.00").assertIsDisplayed()
    }

    @Test
    fun transactionListScreen_clickTransaction_navigatesToDetail() {
        // Given
        val mockTransactions = listOf(
            Transaction(1, "午餐", 150.0, TransactionType.EXPENSE, 1, System.currentTimeMillis())
        )
        var clickedTransactionId: Long? = null

        // When
        composeTestRule.setContent {
            TransactionListScreen(
                transactions = mockTransactions,
                onTransactionClick = { clickedTransactionId = it },
                onAddClick = {}
            )
        }

        // ✅ 點擊交易項目
        composeTestRule.onNodeWithText("午餐").performClick()

        // Then
        assert(clickedTransactionId == 1L)
    }

    @Test
    fun transactionListScreen_clickAddButton_navigatesToAddScreen() {
        // Given
        var addButtonClicked = false

        // When
        composeTestRule.setContent {
            TransactionListScreen(
                transactions = emptyList(),
                onTransactionClick = {},
                onAddClick = { addButtonClicked = true }
            )
        }

        // ✅ 點擊新增按鈕
        composeTestRule.onNodeWithContentDescription("新增交易").performClick()

        // Then
        assert(addButtonClicked)
    }

    @Test
    fun transactionListScreen_emptyState() {
        // When
        composeTestRule.setContent {
            TransactionListScreen(
                transactions = emptyList(),
                onTransactionClick = {},
                onAddClick = {}
            )
        }

        // Then
        composeTestRule.onNodeWithText("尚無交易記錄").assertIsDisplayed()
    }

    @Test
    fun transactionListScreen_scrollToBottom() {
        // Given
        val mockTransactions = List(50) { index ->
            Transaction(
                id = index.toLong(),
                title = "交易 $index",
                amount = 100.0 * index,
                type = TransactionType.EXPENSE,
                categoryId = 1,
                timestamp = System.currentTimeMillis()
            )
        }

        // When
        composeTestRule.setContent {
            TransactionListScreen(
                transactions = mockTransactions,
                onTransactionClick = {},
                onAddClick = {}
            )
        }

        // ✅ 滑動到底部
        composeTestRule.onNodeWithTag("transaction_list").performScrollToIndex(49)

        // Then
        composeTestRule.onNodeWithText("交易 49").assertIsDisplayed()
    }
}
```

---

### 階段 5：E2E 測試（1 週）

**在 Claude Code 輸入**:
```
請編寫端對端測試，測試完整業務流程：

測試場景：
1. 新增交易 → 查看清單 → 編輯 → 刪除
2. 搜尋 → 篩選 → 排序

請生成測試檔案：`app/src/androidTest/java/com/example/expensetracker/e2e/TransactionE2ETest.kt`
```

**Claude Code 生成** (`TransactionE2ETest.kt`):
```kotlin
package com.example.expensetracker.e2e

import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.example.expensetracker.MainActivity
import dagger.hilt.android.testing.HiltAndroidRule
import dagger.hilt.android.testing.HiltAndroidTest
import org.junit.Before
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@HiltAndroidTest
@RunWith(AndroidJUnit4::class)
class TransactionE2ETest {

    @get:Rule(order = 0)
    val hiltRule = HiltAndroidRule(this)

    @get:Rule(order = 1)
    val composeTestRule = createAndroidComposeRule<MainActivity>()

    @Before
    fun setup() {
        hiltRule.inject()
    }

    @Test
    fun completeTransactionFlow_addEditDelete() {
        // ✅ 步驟 1: 點擊新增按鈕
        composeTestRule.onNodeWithContentDescription("新增交易").performClick()

        // ✅ 步驟 2: 填寫表單
        composeTestRule.onNodeWithTag("title_input").performTextInput("測試午餐")
        composeTestRule.onNodeWithTag("amount_input").performTextInput("150")
        composeTestRule.onNodeWithTag("category_selector").performClick()
        composeTestRule.onNodeWithText("餐飲").performClick()

        // ✅ 步驟 3: 儲存交易
        composeTestRule.onNodeWithText("儲存").performClick()

        // ✅ 步驟 4: 驗證交易出現在清單
        composeTestRule.waitForIdle()
        composeTestRule.onNodeWithText("測試午餐").assertIsDisplayed()
        composeTestRule.onNodeWithText("$150.00").assertIsDisplayed()

        // ✅ 步驟 5: 點擊交易項目進入編輯
        composeTestRule.onNodeWithText("測試午餐").performClick()

        // ✅ 步驟 6: 編輯金額
        composeTestRule.onNodeWithTag("amount_input").performTextClearance()
        composeTestRule.onNodeWithTag("amount_input").performTextInput("200")
        composeTestRule.onNodeWithText("儲存").performClick()

        // ✅ 步驟 7: 驗證更新成功
        composeTestRule.waitForIdle()
        composeTestRule.onNodeWithText("$200.00").assertIsDisplayed()

        // ✅ 步驟 8: 刪除交易
        composeTestRule.onNodeWithText("測試午餐").performClick()
        composeTestRule.onNodeWithContentDescription("刪除").performClick()
        composeTestRule.onNodeWithText("確認").performClick()

        // ✅ 步驟 9: 驗證刪除成功
        composeTestRule.waitForIdle()
        composeTestRule.onNodeWithText("測試午餐").assertDoesNotExist()
    }
}
```

---

### 階段 6：測試報告與改善（0.5 週）

**在 Claude Code 輸入**:
```
請生成測試報告：

1. 測試覆蓋率報告
2. 測試結果彙總
3. Bug 清單
4. 改善建議

輸出文檔：`Docs/reports/testing-final-report.md`
```

**執行所有測試**:
```bash
# 1. 單元測試 + 覆蓋率
./gradlew test jacocoTestReport

# 2. 整合測試 & UI 測試
./gradlew connectedAndroidTest

# 3. 查看覆蓋率報告
open app/build/reports/jacoco/jacocoTestReport/html/index.html
```

**預期輸出** (`Docs/reports/testing-final-report.md`):
```markdown
# 測試最終報告

## 📊 測試覆蓋率

| 層級 | 覆蓋率 | 目標 | 狀態 |
|------|--------|------|------|
| 單元測試 | 85% | 80%+ | ✅ 達標 |
| 整合測試 | 72% | 70%+ | ✅ 達標 |
| UI 測試 | 65% | 60%+ | ✅ 達標 |
| 總體覆蓋率 | 78% | 75%+ | ✅ 達標 |

## ✅ 測試結果彙總

### 單元測試
- **總測試數**: 127
- **通過**: 127
- **失敗**: 0
- **跳過**: 0
- **執行時間**: 8.5 秒

### 整合測試
- **總測試數**: 45
- **通過**: 45
- **失敗**: 0
- **執行時間**: 32 秒

### UI 測試
- **總測試數**: 28
- **通過**: 28
- **失敗**: 0
- **執行時間**: 1 分 15 秒

### E2E 測試
- **總測試數**: 5
- **通過**: 5
- **失敗**: 0
- **執行時間**: 2 分 30 秒

## 🐛 發現的 Bug

### Critical (0)
無

### High (1)
1. **刪除交易時 UI 未即時更新**
   - 狀態: 已修復
   - 測試: `TransactionViewModelTest.deleteTransaction`

### Medium (2)
1. **日期選擇器在特定日期崩潰**
   - 狀態: 已修復
2. **搜尋功能大小寫不敏感**
   - 狀態: 已修復

## 💡 改善建議

1. **增加效能測試**：測試大量資料（10,000+ 筆）時的效能
2. **增加安全性測試**：SQL Injection、XSS 防護
3. **增加可用性測試**：無障礙功能（Accessibility）
4. **CI/CD 整合**：GitHub Actions 自動化測試
```

---

## 附錄：命令速查表

### 執行測試

```bash
# 單元測試
./gradlew test

# 特定測試類別
./gradlew test --tests TransactionViewModelTest

# 整合測試 & UI 測試
./gradlew connectedAndroidTest

# 所有測試
./gradlew test connectedAndroidTest
```

### 測試覆蓋率

```bash
# 生成覆蓋率報告
./gradlew jacocoTestReport

# 查看報告
open app/build/reports/jacoco/jacocoTestReport/html/index.html
```

### 測試報告

```bash
# 單元測試報告
open app/build/reports/tests/testDebugUnitTest/index.html

# 整合測試報告
open app/build/reports/androidTests/connected/index.html
```

---

## 🎯 測試時程表（總計 7.5 週）

| 階段 | 週數 | 主要工作 |
|------|-----|---------|
| 1. 測試計畫 | 1 週 | 測試計畫、測試案例設計 |
| 2. 單元測試 | 2 週 | ViewModel、Repository、Use Cases |
| 3. 整合測試 | 1.5 週 | Room Database、API 整合 |
| 4. UI 測試 | 1.5 週 | Compose UI 元件測試 |
| 5. E2E 測試 | 1 週 | 完整業務流程測試 |
| 6. 測試報告 | 0.5 週 | 測試報告、改善建議 |

---

## 📚 相關文檔

- [AISDLC_INIT.md](../../AISDLC_INIT.md)
- [test-planning-and-strategy.md](../../workflow/scenario-specific/test-planning-and-strategy.md)
- [JUnit 5 文檔](https://junit.org/junit5/docs/current/user-guide/)
- [Compose Testing](https://developer.android.com/jetpack/compose/testing)

---

**版本**: 1.0
**作者**: AISDLC Framework Team
**最後更新**: 2025-12-15
