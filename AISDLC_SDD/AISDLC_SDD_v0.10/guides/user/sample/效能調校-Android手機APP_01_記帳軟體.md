# 效能調校：Android 手機 APP（記帳軟體）

> **場景**: Performance Optimization - 針對現有 Android 記帳 APP 進行全面效能調校
> **技術棧**: Kotlin + Jetpack Compose + MVVM + Hilt + Room Database
> **AISDLC 版本**: v0.01
> **更新日期**: 2025-12-15


> **SDD v0.01 使用者提示**：本指南基於 AISDLC-SDD v0.01。使用 AISDLC-SDD v0.01 時，請同時參考對應場景的 SDD Enhancement 文件（`scenarios/{scenario}/SDD_{SCENARIO}_ENHANCEMENT.md`），並確認所有 SCG 閘門步驟已整合到您的工作流程中。

---
---

## 📋 目錄

1. [第一步：Cursor AI 專案路徑設定](#第一步cursor-ai-專案路徑設定)
2. [第二步：AISDLC 框架安裝](#第二步aisdlc-框架安裝)
3. [第三步：Claude Code 完整效能調校流程](#第三步claude-code-完整效能調校流程)
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
│   │   │   │   │   ├── transaction/
│   │   │   │   │   │   ├── TransactionListScreen.kt  # 🔴 效能問題
│   │   │   │   │   │   └── TransactionViewModel.kt
│   │   │   │   │   ├── chart/
│   │   │   │   │   │   └── ChartScreen.kt           # 🔴 效能問題
│   │   │   │   │   └── home/
│   │   │   │   ├── data/
│   │   │   │   │   ├── local/
│   │   │   │   │   │   ├── TransactionDao.kt        # 🔴 N+1 查詢
│   │   │   │   │   │   └── AppDatabase.kt
│   │   │   │   │   └── repository/
│   │   │   │   │       └── TransactionRepository.kt
│   │   │   │   ├── domain/
│   │   │   │   │   └── model/
│   │   │   │   │       └── Transaction.kt
│   │   │   │   └── di/
│   │   │   │       └── AppModule.kt
│   │   │   └── res/
│   │   └── androidTest/
│   ├── build.gradle.kts
│   └── proguard-rules.pro
├── gradle/
├── build.gradle.kts
└── settings.gradle.kts
```

**現有效能問題診斷**:
- ❌ 交易清單滑動卡頓（FPS < 30）
- ❌ 圖表繪製耗時過長（> 3 秒）
- ❌ 資料庫查詢慢（N+1 查詢問題）
- ❌ 記憶體洩漏（長時間使用後 APP 變慢）
- ❌ APK 體積過大（150 MB）
- ❌ 冷啟動時間長（> 5 秒）

### 1.2 建立效能調校專案結構

**在終端機執行**:
```bash
cd ~/Projects/ExpenseTrackerApp

# 建立效能分析目錄
mkdir -p performance-analysis
mkdir -p performance-analysis/profiling    # Android Profiler 結果
mkdir -p performance-analysis/reports      # 效能報告
mkdir -p performance-analysis/baseline     # 基準測試結果

# 建立文檔目錄
mkdir -p Docs
mkdir -p Docs/performance                  # 效能調校文檔
mkdir -p Docs/optimization                 # 優化方案
mkdir -p Docs/reports                      # 驗證報告

# 驗證
tree -L 2 -d
```

**完整專案結構**:
```
ExpenseTrackerApp/
├── app/                           # 🎯 Android Studio 專案
│   ├── src/
│   └── build.gradle.kts
├── performance-analysis/          # 📊 效能分析資料
│   ├── profiling/
│   ├── reports/
│   └── baseline/
├── Docs/                          # 📄 AISDLC 文檔
│   ├── performance/
│   ├── optimization/
│   └── reports/
└── AISDLC_SDD_v0.01/                 # 🔴 步驟 2 安裝
```

### 1.3 開啟 Android Studio 與 Cursor AI

**步驟**:
1. **Android Studio**: 打開現有專案 `~/Projects/ExpenseTrackerApp`
2. **Cursor AI**: `File` → `Open Folder...` → 選擇 `~/Projects/ExpenseTrackerApp`

**驗證**: Cursor 左側應顯示 `app/`, `performance-analysis/`, `Docs/`

---

## 第二步：AISDLC 框架安裝

### 2.1 方法一：符號連結（推薦）

```bash
cd ~/Projects/ExpenseTrackerApp

# 建立符號連結
ln -s /Users/你的用戶名/Cursor_Project/AISDLC_ALL/AISDLC_v0.09 AISDLC_v0.09

# 驗證
ls -lah | grep AISDLC
```

### 2.2 方法二：複製

```bash
cp -r /Users/你的用戶名/Cursor_Project/AISDLC_ALL/AISDLC_v0.09 ~/Projects/ExpenseTrackerApp/

# 驗證
ls AISDLC_SDD_v0.01/
```

### 2.3 驗證安裝

```bash
ls -la AISDLC_SDD_v0.01/AISDLC_INIT.md
cat AISDLC_SDD_v0.01/scenarios/performance/README.md | head -30
```

---

## 第三步：Claude Code 完整效能調校流程

### 階段 1：效能基準測試與問題診斷（2 週）

#### 3.1.1 啟動效能分析 Workflow

**在 Claude Code 輸入**:
```
請載入 AISDLC_INIT.md，我要進行「效能調校」場景。

目標：Android 記帳 APP 效能優化

技術棧：
- 前端：Kotlin + Jetpack Compose + MVVM
- 依賴注入：Hilt
- 資料庫：Room Database
- 後端：Python FastAPI（可選）

目前問題：
1. 交易清單滑動卡頓（FPS < 30）
2. 圖表繪製耗時 > 3 秒
3. 資料庫查詢慢
4. 記憶體洩漏
5. APK 體積 150 MB
6. 冷啟動時間 > 5 秒

請執行「performance-profiling-and-analysis」workflow，進行全面效能分析。
```

#### 3.1.2 Android Profiler 數據收集

**在 Claude Code 輸入**:
```
請指導我使用 Android Profiler 收集以下數據：

1. CPU Profiler（識別 CPU 熱點）
2. Memory Profiler（記憶體洩漏檢測）
3. Network Profiler（API 請求分析）
4. Energy Profiler（電池消耗）

測試場景：
- 滑動交易清單（500 筆資料）
- 切換圖表頁面
- 新增交易
- 長時間使用（30 分鐘）

請生成數據收集指南：`Docs/performance/profiler-guide.md`
```

**預期輸出** (`Docs/performance/profiler-guide.md`):
```markdown
# Android Profiler 數據收集指南

## 1. CPU Profiler

### 執行步驟
1. 打開 Android Studio
2. `View` → `Tool Windows` → `Profiler`
3. 選擇連接的設備或模擬器
4. 點擊 `CPU` → `Record`
5. 執行測試場景（滑動交易清單）
6. 點擊 `Stop` → 分析結果

### 關鍵指標
- **Top Down Tree**: 找出耗時最長的函式
- **Flame Chart**: 視覺化 CPU 使用情況
- **Call Chart**: 函式呼叫關係

### 預期發現
- `TransactionListScreen.kt` 的 `LazyColumn` 渲染耗時
- `ChartScreen.kt` 的圖表計算耗時
- 資料庫查詢阻塞 UI Thread

## 2. Memory Profiler

### 執行步驟
1. Profiler → `Memory` → `Record`
2. 執行測試場景（新增 100 筆交易）
3. 點擊 `Dump Java Heap`
4. 分析 Heap Dump

### 關鍵指標
- **Shallow Size**: 物件本身大小
- **Retained Size**: 物件及其引用總大小
- **Allocation Tracker**: 記憶體分配追蹤

### 預期發現
- `TransactionViewModel` 未釋放（記憶體洩漏）
- `Bitmap` 物件過多（圖片未優化）
- `Flow` 或 `LiveData` 訂閱未取消
```

#### 3.1.3 執行基準測試

**在 Claude Code 輸入**:
```
請協助建立 Jetpack Macrobenchmark 測試：

測試場景：
1. 冷啟動時間（從點擊圖示到首頁顯示）
2. 交易清單滑動流暢度（Jank 指標）
3. 圖表載入時間

測試檔案：`app/src/androidTest/java/com/example/expensetracker/benchmark/StartupBenchmark.kt`

請生成完整測試程式碼。
```

**Claude Code 生成**:

**1. `app/build.gradle.kts`** (新增依賴):
```kotlin
plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("androidx.benchmark")  // 新增
}

dependencies {
    // 現有依賴...

    // Benchmark
    androidTestImplementation("androidx.benchmark:benchmark-junit4:1.2.2")
    androidTestImplementation("androidx.test.ext:junit:1.1.5")
    androidTestImplementation("androidx.test.espresso:espresso-core:3.5.1")
    androidTestImplementation("androidx.test.uiautomator:uiautomator:2.3.0")
}

// Benchmark 配置
android {
    defaultConfig {
        testInstrumentationRunner = "androidx.benchmark.junit4.AndroidBenchmarkRunner"
    }

    testBuildType = "release"

    buildTypes {
        release {
            isMinifyEnabled = true
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
            signingConfig = signingConfigs.getByName("debug")
        }
    }
}
```

**2. `app/src/androidTest/java/com/example/expensetracker/benchmark/StartupBenchmark.kt`**:
```kotlin
package com.example.expensetracker.benchmark

import androidx.benchmark.macro.StartupMode
import androidx.benchmark.macro.StartupTimingMetric
import androidx.benchmark.macro.junit4.MacrobenchmarkRule
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.uiautomator.By
import androidx.test.uiautomator.Until
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

/**
 * 冷啟動效能測試
 * 目標: < 2 秒
 */
@RunWith(AndroidJUnit4::class)
class StartupBenchmark {

    @get:Rule
    val benchmarkRule = MacrobenchmarkRule()

    @Test
    fun startupCold() = benchmarkRule.measureRepeated(
        packageName = "com.example.expensetracker",
        metrics = listOf(StartupTimingMetric()),
        iterations = 5,
        startupMode = StartupMode.COLD
    ) {
        pressHome()
        startActivityAndWait()

        // 等待首頁載入完成
        device.wait(Until.hasObject(By.text("交易記錄")), 5_000)
    }

    @Test
    fun startupWarm() = benchmarkRule.measureRepeated(
        packageName = "com.example.expensetracker",
        metrics = listOf(StartupTimingMetric()),
        iterations = 5,
        startupMode = StartupMode.WARM
    ) {
        pressHome()
        startActivityAndWait()
        device.wait(Until.hasObject(By.text("交易記錄")), 3_000)
    }
}
```

**3. `ScrollBenchmark.kt`** (滑動流暢度測試):
```kotlin
package com.example.expensetracker.benchmark

import androidx.benchmark.macro.FrameTimingMetric
import androidx.benchmark.macro.StartupMode
import androidx.benchmark.macro.junit4.MacrobenchmarkRule
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.uiautomator.By
import androidx.test.uiautomator.Direction
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

/**
 * 滑動流暢度測試
 * 目標: Jank 次數 < 5
 */
@RunWith(AndroidJUnit4::class)
class ScrollBenchmark {

    @get:Rule
    val benchmarkRule = MacrobenchmarkRule()

    @Test
    fun scrollTransactionList() = benchmarkRule.measureRepeated(
        packageName = "com.example.expensetracker",
        metrics = listOf(FrameTimingMetric()),
        iterations = 5,
        startupMode = StartupMode.WARM,
        setupBlock = {
            pressHome()
            startActivityAndWait()
        }
    ) {
        val transactionList = device.findObject(By.res("transaction_list"))

        // 滑動 10 次
        repeat(10) {
            transactionList.setGestureMargin(device.displayWidth / 5)
            transactionList.fling(Direction.DOWN)
            device.waitForIdle()
        }
    }
}
```

**執行測試**:
```bash
# 在 Android Studio 終端機執行
./gradlew :app:connectedAndroidTest

# 查看結果
adb pull /sdcard/Android/data/com.example.expensetracker/files/benchmarks/
```

**預期結果** (`performance-analysis/baseline/startup-benchmark-results.txt`):
```
StartupBenchmark_startupCold
  timeToInitialDisplayMs   min 4,234,   median 4,567,   max 5,012
  timeToFullDisplayMs      min 5,123,   median 5,456,   max 5,890

ScrollBenchmark_scrollTransactionList
  frameDurationCpuMs       min 12,      median 45,      max 120
  frameOverrunMs           min 0,       median 28,      max 103
  Janky frames             23 (12.3%)  🔴 問題！目標 < 5%
```

#### 3.1.4 生成效能診斷報告

**在 Claude Code 輸入**:
```
請載入 QA Agent (Quincy)，分析以下效能數據：

1. Android Profiler 結果（我已上傳截圖）
2. Benchmark 測試結果（上方輸出）
3. 程式碼分析（識別效能瓶頸）

請生成診斷報告：`Docs/performance/performance-diagnosis-report.md`
```

**預期輸出摘要**:
```markdown
# 效能診斷報告

## 🔴 嚴重問題（Critical）

### 1. 交易清單滑動卡頓
- **位置**: `TransactionListScreen.kt` (第 45-120 行)
- **問題**:
  - `LazyColumn` 無使用 `key` 參數（導致不必要的重組）
  - 每個 `TransactionItem` 都重新計算日期格式化
  - 類別圖示使用 `painterResource` 每次重新載入
- **數據**:
  - FPS 平均 28（目標 60）
  - Jank 次數 23 次/10 秒（目標 < 5）
  - 單一 Frame 耗時 max 120ms（目標 < 16ms）
- **影響**: 使用者體驗差，滑動不流暢

### 2. 圖表繪製耗時過長
- **位置**: `ChartScreen.kt` (第 78-200 行)
- **問題**:
  - 在 `@Composable` 函式內執行大量計算（應移至 ViewModel）
  - 每次 Recomposition 都重新計算圖表資料
  - 未使用 `remember` 快取計算結果
- **數據**:
  - 首次載入耗時 3,450ms（目標 < 500ms）
  - CPU 使用率飆升至 85%
- **影響**: 頁面切換延遲，使用者等待時間長

### 3. 資料庫 N+1 查詢問題
- **位置**: `TransactionDao.kt` (第 23-35 行)
- **問題**:
  ```kotlin
  @Query("SELECT * FROM transactions")
  suspend fun getAllTransactions(): List<Transaction>

  // 在 Repository 中逐筆查詢 Category
  transactions.forEach { transaction ->
      transaction.category = categoryDao.getById(transaction.categoryId)  // ❌ N+1
  }
  ```
- **數據**:
  - 500 筆交易 → 501 次 SQL 查詢
  - 總查詢時間 1,200ms（目標 < 100ms）
- **影響**: 清單載入緩慢

### 4. 記憶體洩漏
- **位置**: `TransactionViewModel.kt`
- **問題**:
  - `Flow` 訂閱在 `ViewModel` 清除後未取消
  - `Bitmap` 物件未回收
- **數據**:
  - 使用 30 分鐘後記憶體從 120MB 增加至 450MB
  - Heap Dump 顯示 342 個 `TransactionViewModel` 實例未釋放
- **影響**: APP 變慢，最終 OOM Crash

## ⚠️  中等問題（Medium）

### 5. APK 體積過大（150 MB）
- **原因**:
  - 包含未使用的資源（多語言、多密度圖片）
  - 未啟用 R8 Code Shrinking
  - 未使用 WebP 壓縮圖片
- **建議**: 啟用 ProGuard/R8，移除未使用資源

### 6. 冷啟動時間長（5.4 秒）
- **原因**:
  - Hilt 依賴注入初始化耗時
  - Splash Screen 無優化
  - 資料庫預載入阻塞主執行緒
- **建議**: 延遲初始化，使用 WorkManager 背景預載入
```

---

### 階段 2：UI 效能優化（3 週）

#### 3.2.1 優化 LazyColumn 滑動效能

**在 Claude Code 輸入**:
```
請優化 TransactionListScreen.kt 的滑動效能：

問題：
1. LazyColumn 無 key 參數
2. 每個 Item 重新計算日期格式化
3. 類別圖示重複載入

目標：
- FPS > 55
- Jank 次數 < 5 次/10 秒

請提供優化後的完整程式碼。
```

**優化前** (`TransactionListScreen.kt`):
```kotlin
@Composable
fun TransactionListScreen(
    viewModel: TransactionViewModel = hiltViewModel()
) {
    val transactions by viewModel.transactions.collectAsState(initial = emptyList())

    LazyColumn {  // ❌ 無 key
        items(transactions) { transaction ->  // ❌ 無 key
            TransactionItem(transaction = transaction)
        }
    }
}

@Composable
fun TransactionItem(transaction: Transaction) {
    Row(modifier = Modifier.fillMaxWidth().padding(16.dp)) {
        // ❌ 每次 Recomposition 都重新載入圖示
        Image(
            painter = painterResource(id = getCategoryIcon(transaction.categoryId)),
            contentDescription = null,
            modifier = Modifier.size(40.dp)
        )

        Column(modifier = Modifier.weight(1f).padding(start = 12.dp)) {
            Text(text = transaction.title, style = MaterialTheme.typography.bodyLarge)

            // ❌ 每次重新格式化日期
            Text(
                text = SimpleDateFormat("yyyy-MM-dd HH:mm", Locale.getDefault())
                    .format(Date(transaction.timestamp)),
                style = MaterialTheme.typography.bodySmall,
                color = Color.Gray
            )
        }

        Text(
            text = "$${"%.2f".format(transaction.amount)}",
            style = MaterialTheme.typography.bodyLarge,
            color = if (transaction.type == TransactionType.INCOME) Color.Green else Color.Red
        )
    }
}
```

**優化後** (`TransactionListScreen.kt`):
```kotlin
@Composable
fun TransactionListScreen(
    viewModel: TransactionViewModel = hiltViewModel()
) {
    val transactions by viewModel.transactions.collectAsState(initial = emptyList())

    // ✅ 優化 1: 使用 derivedStateOf 避免不必要的重組
    val groupedTransactions by remember {
        derivedStateOf {
            transactions.groupBy { it.date.toLocalDate() }
        }
    }

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .testTag("transaction_list"),  // ✅ 用於 Benchmark 測試
        contentPadding = PaddingValues(vertical = 8.dp)
    ) {
        groupedTransactions.forEach { (date, dailyTransactions) ->
            // 日期標題
            item(key = "header_$date") {  // ✅ 優化 2: 使用 key
                DateHeader(date = date)
            }

            // 交易清單
            items(
                items = dailyTransactions,
                key = { transaction -> transaction.id }  // ✅ 優化 3: 使用 key
            ) { transaction ->
                TransactionItem(transaction = transaction)
            }
        }
    }
}

@Composable
fun TransactionItem(transaction: Transaction) {
    // ✅ 優化 4: 使用 remember 快取計算結果
    val formattedDate = remember(transaction.timestamp) {
        SimpleDateFormat("HH:mm", Locale.getDefault())
            .format(Date(transaction.timestamp))
    }

    val formattedAmount = remember(transaction.amount) {
        "$${"%.2f".format(transaction.amount)}"
    }

    // ✅ 優化 5: 使用 rememberAsyncImagePainter（Coil）快取圖片
    val categoryIcon = remember(transaction.categoryId) {
        getCategoryIcon(transaction.categoryId)
    }

    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clickable { /* 點擊事件 */ }
            .padding(horizontal = 16.dp, vertical = 12.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        // ✅ 優化 6: 圖示快取
        Image(
            painter = painterResource(id = categoryIcon),
            contentDescription = null,
            modifier = Modifier
                .size(40.dp)
                .clip(CircleShape)
                .background(MaterialTheme.colorScheme.primaryContainer)
                .padding(8.dp)
        )

        Column(
            modifier = Modifier
                .weight(1f)
                .padding(start = 12.dp)
        ) {
            Text(
                text = transaction.title,
                style = MaterialTheme.typography.bodyLarge,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis
            )

            Text(
                text = formattedDate,
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }

        Text(
            text = formattedAmount,
            style = MaterialTheme.typography.bodyLarge.copy(fontWeight = FontWeight.Bold),
            color = if (transaction.type == TransactionType.INCOME)
                MaterialTheme.colorScheme.primary
            else
                MaterialTheme.colorScheme.error
        )
    }
}

// ✅ 優化 7: 抽出獨立 Composable，減少重組範圍
@Composable
fun DateHeader(date: LocalDate) {
    val formattedDate = remember(date) {
        date.format(DateTimeFormatter.ofPattern("yyyy年MM月dd日", Locale.TRADITIONAL_CHINESE))
    }

    Text(
        text = formattedDate,
        style = MaterialTheme.typography.titleSmall,
        modifier = Modifier
            .fillMaxWidth()
            .background(MaterialTheme.colorScheme.surfaceVariant)
            .padding(horizontal = 16.dp, vertical = 8.dp)
    )
}
```

**額外優化：使用 Paging 3 分頁載入**:
```kotlin
// ViewModel
@HiltViewModel
class TransactionViewModel @Inject constructor(
    private val repository: TransactionRepository
) : ViewModel() {

    // ✅ 優化 8: 使用 Paging 3 分頁載入
    val transactionsPager: Flow<PagingData<Transaction>> = Pager(
        config = PagingConfig(
            pageSize = 20,
            prefetchDistance = 5,
            enablePlaceholders = false
        ),
        pagingSourceFactory = { repository.getTransactionsPagingSource() }
    ).flow.cachedIn(viewModelScope)
}

// Screen
@Composable
fun TransactionListScreen(
    viewModel: TransactionViewModel = hiltViewModel()
) {
    val lazyPagingItems = viewModel.transactionsPager.collectAsLazyPagingItems()

    LazyColumn {
        items(
            count = lazyPagingItems.itemCount,
            key = { index -> lazyPagingItems[index]?.id ?: index }
        ) { index ->
            val transaction = lazyPagingItems[index]
            if (transaction != null) {
                TransactionItem(transaction = transaction)
            }
        }
    }
}
```

#### 3.2.2 優化圖表繪製效能

**在 Claude Code 輸入**:
```
請優化 ChartScreen.kt 的圖表繪製效能：

問題：
1. 圖表計算在 Composable 內執行
2. 每次 Recomposition 都重新計算
3. 無快取機制

目標：
- 首次載入 < 500ms
- 切換月份 < 200ms

請提供優化方案。
```

**優化前** (`ChartScreen.kt`):
```kotlin
@Composable
fun ChartScreen(viewModel: TransactionViewModel = hiltViewModel()) {
    val transactions by viewModel.transactions.collectAsState(initial = emptyList())

    // ❌ 在 Composable 內執行大量計算
    val chartData = transactions
        .filter { it.timestamp >= getMonthStartTimestamp() }
        .groupBy { it.categoryId }
        .map { (categoryId, trans) ->
            ChartEntry(
                category = getCategoryName(categoryId),
                amount = trans.sumOf { it.amount },
                percentage = trans.sumOf { it.amount } / transactions.sumOf { it.amount } * 100
            )
        }
        .sortedByDescending { it.amount }

    PieChart(data = chartData)  // ❌ 每次重組都重繪
}
```

**優化後** (`ChartScreen.kt` + `ChartViewModel.kt`):

**1. ViewModel**:
```kotlin
@HiltViewModel
class ChartViewModel @Inject constructor(
    private val repository: TransactionRepository
) : ViewModel() {

    private val _selectedMonth = MutableStateFlow(YearMonth.now())
    val selectedMonth: StateFlow<YearMonth> = _selectedMonth.asStateFlow()

    // ✅ 優化 1: 計算移至 ViewModel
    val chartData: StateFlow<ChartUiState> = _selectedMonth
        .flatMapLatest { month ->
            repository.getTransactionsByMonth(month)
                .map { transactions ->
                    ChartUiState.Success(
                        data = calculateChartData(transactions),
                        totalIncome = transactions.filter { it.type == TransactionType.INCOME }.sumOf { it.amount },
                        totalExpense = transactions.filter { it.type == TransactionType.EXPENSE }.sumOf { it.amount }
                    )
                }
                .catch { emit(ChartUiState.Error(it.message ?: "Unknown error")) }
        }
        .stateIn(
            scope = viewModelScope,
            started = SharingStarted.WhileSubscribed(5000),
            initialValue = ChartUiState.Loading
        )

    // ✅ 優化 2: 使用快取（LruCache）
    private val chartDataCache = LruCache<YearMonth, List<ChartEntry>>(12)  // 快取 12 個月

    private fun calculateChartData(transactions: List<Transaction>): List<ChartEntry> {
        val month = _selectedMonth.value

        // 檢查快取
        chartDataCache.get(month)?.let { return it }

        // 計算圖表資料
        val totalExpense = transactions
            .filter { it.type == TransactionType.EXPENSE }
            .sumOf { it.amount }

        val data = transactions
            .filter { it.type == TransactionType.EXPENSE }
            .groupBy { it.categoryId }
            .map { (categoryId, trans) ->
                val amount = trans.sumOf { it.amount }
                ChartEntry(
                    category = getCategoryName(categoryId),
                    amount = amount,
                    percentage = (amount / totalExpense * 100).toFloat(),
                    color = getCategoryColor(categoryId)
                )
            }
            .sortedByDescending { it.amount }
            .take(8)  // 只顯示前 8 大類別

        // 存入快取
        chartDataCache.put(month, data)
        return data
    }

    fun selectMonth(month: YearMonth) {
        _selectedMonth.value = month
    }
}

sealed class ChartUiState {
    object Loading : ChartUiState()
    data class Success(
        val data: List<ChartEntry>,
        val totalIncome: Double,
        val totalExpense: Double
    ) : ChartUiState()
    data class Error(val message: String) : ChartUiState()
}

data class ChartEntry(
    val category: String,
    val amount: Double,
    val percentage: Float,
    val color: Color
)
```

**2. Screen**:
```kotlin
@Composable
fun ChartScreen(viewModel: ChartViewModel = hiltViewModel()) {
    val chartUiState by viewModel.chartData.collectAsState()
    val selectedMonth by viewModel.selectedMonth.collectAsState()

    Column(modifier = Modifier.fillMaxSize()) {
        // 月份選擇器
        MonthSelector(
            selectedMonth = selectedMonth,
            onMonthSelected = { viewModel.selectMonth(it) }
        )

        // 圖表內容
        when (val state = chartUiState) {
            is ChartUiState.Loading -> {
                CircularProgressIndicator(modifier = Modifier.align(Alignment.CenterHorizontally))
            }
            is ChartUiState.Success -> {
                // ✅ 優化 3: 使用 remember 避免重組時重繪
                ChartContent(
                    data = state.data,
                    totalIncome = state.totalIncome,
                    totalExpense = state.totalExpense
                )
            }
            is ChartUiState.Error -> {
                ErrorView(message = state.message)
            }
        }
    }
}

@Composable
fun ChartContent(
    data: List<ChartEntry>,
    totalIncome: Double,
    totalExpense: Double
) {
    Column(modifier = Modifier.fillMaxSize().padding(16.dp)) {
        // 總覽卡片
        SummaryCard(
            totalIncome = totalIncome,
            totalExpense = totalExpense
        )

        Spacer(modifier = Modifier.height(24.dp))

        // ✅ 優化 4: 圓餅圖（使用 Canvas 繪製，避免重組）
        PieChart(
            data = data,
            modifier = Modifier
                .size(280.dp)
                .align(Alignment.CenterHorizontally)
        )

        Spacer(modifier = Modifier.height(24.dp))

        // 圖例清單
        LazyColumn {
            items(
                items = data,
                key = { it.category }
            ) { entry ->
                ChartLegendItem(entry = entry)
            }
        }
    }
}

@Composable
fun PieChart(
    data: List<ChartEntry>,
    modifier: Modifier = Modifier
) {
    // ✅ 優化 5: 使用 remember 快取角度計算
    val angles = remember(data) {
        data.map { it.percentage * 3.6f }  // 轉換為角度
    }

    Canvas(modifier = modifier) {
        val canvasSize = size.minDimension
        val radius = canvasSize / 2f
        val center = Offset(size.width / 2f, size.height / 2f)

        var startAngle = -90f  // 從頂部開始

        data.forEachIndexed { index, entry ->
            val sweepAngle = angles[index]

            // 繪製扇形
            drawArc(
                color = entry.color,
                startAngle = startAngle,
                sweepAngle = sweepAngle,
                useCenter = true,
                topLeft = Offset(center.x - radius, center.y - radius),
                size = Size(radius * 2, radius * 2)
            )

            startAngle += sweepAngle
        }

        // 中心圓（Donut Chart 效果）
        drawCircle(
            color = Color.White,
            radius = radius * 0.5f,
            center = center
        )
    }
}
```

**效能對比**:
```
優化前：
- 首次載入: 3,450ms
- 切換月份: 2,100ms
- CPU 使用率: 85%

優化後：
- 首次載入: 380ms  ✅ 提升 90%
- 切換月份: 120ms  ✅ 提升 94%（快取命中）
- CPU 使用率: 35%  ✅ 降低 59%
```

---

### 階段 3：資料庫效能優化（2 週）

#### 3.3.1 修復 N+1 查詢問題

**在 Claude Code 輸入**:
```
請優化資料庫查詢效能：

問題：TransactionDao.kt 的 N+1 查詢問題

目標：
- 單次查詢取得所有關聯資料
- 查詢時間 < 100ms（500 筆資料）

請提供優化方案。
```

**優化前** (`TransactionDao.kt`):
```kotlin
@Dao
interface TransactionDao {
    @Query("SELECT * FROM transactions ORDER BY timestamp DESC")
    suspend fun getAllTransactions(): List<Transaction>  // ❌ N+1 問題
}

// Repository
class TransactionRepository @Inject constructor(
    private val transactionDao: TransactionDao,
    private val categoryDao: CategoryDao
) {
    suspend fun getAllTransactions(): List<Transaction> {
        val transactions = transactionDao.getAllTransactions()

        // ❌ 逐筆查詢 Category（N+1 問題）
        transactions.forEach { transaction ->
            transaction.category = categoryDao.getById(transaction.categoryId)
        }

        return transactions
    }
}
```

**優化後** (`TransactionDao.kt`):
```kotlin
// ✅ 優化 1: 使用 @Embedded 和 @Relation
@Dao
interface TransactionDao {

    // 原始查詢（僅 Transaction）
    @Query("SELECT * FROM transactions ORDER BY timestamp DESC")
    suspend fun getAllTransactions(): List<Transaction>

    // ✅ JOIN 查詢（包含 Category）
    @Transaction
    @Query("""
        SELECT t.*, c.name as category_name, c.icon as category_icon, c.color as category_color
        FROM transactions t
        LEFT JOIN categories c ON t.category_id = c.id
        ORDER BY t.timestamp DESC
    """)
    suspend fun getAllTransactionsWithCategory(): List<TransactionWithCategory>

    // ✅ 分頁查詢（Paging 3）
    @Transaction
    @Query("""
        SELECT t.*, c.name as category_name, c.icon as category_icon, c.color as category_color
        FROM transactions t
        LEFT JOIN categories c ON t.category_id = c.id
        ORDER BY t.timestamp DESC
    """)
    fun getTransactionsPaging(): PagingSource<Int, TransactionWithCategory>

    // ✅ 按月份查詢（用於圖表）
    @Transaction
    @Query("""
        SELECT t.*, c.name as category_name, c.icon as category_icon, c.color as category_color
        FROM transactions t
        LEFT JOIN categories c ON t.category_id = c.id
        WHERE t.timestamp >= :startTimestamp AND t.timestamp < :endTimestamp
        ORDER BY t.timestamp DESC
    """)
    fun getTransactionsByMonth(startTimestamp: Long, endTimestamp: Long): Flow<List<TransactionWithCategory>>
}

// ✅ 優化 2: 定義關聯實體
data class TransactionWithCategory(
    @Embedded val transaction: Transaction,
    @ColumnInfo(name = "category_name") val categoryName: String,
    @ColumnInfo(name = "category_icon") val categoryIcon: Int,
    @ColumnInfo(name = "category_color") val categoryColor: Int
)

// ✅ 優化 3: 建立索引
@Entity(
    tableName = "transactions",
    indices = [
        Index(value = ["category_id"]),       // 索引 1: Category JOIN
        Index(value = ["timestamp"]),         // 索引 2: 排序
        Index(value = ["type"]),              // 索引 3: 篩選
        Index(value = ["timestamp", "type"])  // 複合索引: 常見查詢
    ]
)
data class Transaction(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    @ColumnInfo(name = "category_id") val categoryId: Long,
    val title: String,
    val amount: Double,
    val type: TransactionType,
    val timestamp: Long,
    val note: String? = null
)
```

**Repository 優化**:
```kotlin
class TransactionRepository @Inject constructor(
    private val transactionDao: TransactionDao,
    private val ioDispatcher: CoroutineDispatcher = Dispatchers.IO
) {
    // ✅ 使用 Flow 自動更新
    fun getAllTransactions(): Flow<List<TransactionWithCategory>> = flow {
        emit(transactionDao.getAllTransactionsWithCategory())
    }.flowOn(ioDispatcher)

    // ✅ Paging 3 支援
    fun getTransactionsPagingSource(): PagingSource<Int, TransactionWithCategory> {
        return transactionDao.getTransactionsPaging()
    }

    // ✅ 按月份查詢（用於圖表）
    fun getTransactionsByMonth(month: YearMonth): Flow<List<TransactionWithCategory>> {
        val startTimestamp = month.atDay(1).atStartOfDay().toEpochSecond(ZoneOffset.UTC) * 1000
        val endTimestamp = month.plusMonths(1).atDay(1).atStartOfDay().toEpochSecond(ZoneOffset.UTC) * 1000

        return transactionDao.getTransactionsByMonth(startTimestamp, endTimestamp)
            .flowOn(ioDispatcher)
    }
}
```

**效能對比**:
```
優化前（N+1 查詢）:
- 500 筆交易: 1,200ms (501 次 SQL 查詢)
- 1000 筆交易: 2,400ms (1001 次 SQL 查詢)

優化後（JOIN 查詢 + 索引）:
- 500 筆交易: 45ms  ✅ 提升 96%
- 1000 筆交易: 78ms  ✅ 提升 97%
```

#### 3.3.2 資料庫遷移腳本

**在 Claude Code 輸入**:
```
請生成 Room Database 遷移腳本，新增索引：

從 Version 1 → Version 2
新增索引：category_id, timestamp, type

請提供完整遷移程式碼。
```

**Claude Code 生成**:
```kotlin
@Database(
    entities = [Transaction::class, Category::class],
    version = 2,  // ✅ 更新版本
    exportSchema = true
)
abstract class AppDatabase : RoomDatabase() {
    abstract fun transactionDao(): TransactionDao
    abstract fun categoryDao(): CategoryDao

    companion object {
        // ✅ 定義遷移
        val MIGRATION_1_2 = object : Migration(1, 2) {
            override fun migrate(database: SupportSQLiteDatabase) {
                // 新增索引
                database.execSQL("CREATE INDEX IF NOT EXISTS index_transactions_category_id ON transactions(category_id)")
                database.execSQL("CREATE INDEX IF NOT EXISTS index_transactions_timestamp ON transactions(timestamp)")
                database.execSQL("CREATE INDEX IF NOT EXISTS index_transactions_type ON transactions(type)")
                database.execSQL("CREATE INDEX IF NOT EXISTS index_transactions_timestamp_type ON transactions(timestamp, type)")
            }
        }

        @Volatile
        private var INSTANCE: AppDatabase? = null

        fun getDatabase(context: Context): AppDatabase {
            return INSTANCE ?: synchronized(this) {
                val instance = Room.databaseBuilder(
                    context.applicationContext,
                    AppDatabase::class.java,
                    "expense_tracker_db"
                )
                    .addMigrations(MIGRATION_1_2)  // ✅ 註冊遷移
                    .build()

                INSTANCE = instance
                instance
            }
        }
    }
}
```

---

### 階段 4：記憶體優化（1.5 週）

#### 3.4.1 修復記憶體洩漏

**在 Claude Code 輸入**:
```
請修復 TransactionViewModel 的記憶體洩漏問題：

問題：
1. Flow 訂閱未取消
2. ViewModel 實例未釋放

請提供修復方案。
```

**優化前**:
```kotlin
@HiltViewModel
class TransactionViewModel @Inject constructor(
    private val repository: TransactionRepository
) : ViewModel() {

    private val _transactions = MutableStateFlow<List<Transaction>>(emptyList())
    val transactions: StateFlow<List<Transaction>> = _transactions.asStateFlow()

    init {
        // ❌ 記憶體洩漏：訂閱未取消
        viewModelScope.launch {
            repository.getAllTransactions().collect { transactions ->
                _transactions.value = transactions
            }
        }
    }
}
```

**優化後**:
```kotlin
@HiltViewModel
class TransactionViewModel @Inject constructor(
    private val repository: TransactionRepository
) : ViewModel() {

    // ✅ 優化 1: 使用 stateIn 自動管理生命週期
    val transactions: StateFlow<List<TransactionWithCategory>> = repository
        .getAllTransactions()
        .stateIn(
            scope = viewModelScope,
            started = SharingStarted.WhileSubscribed(5000),  // ✅ 5 秒後停止訂閱
            initialValue = emptyList()
        )

    // ✅ 優化 2: 使用 shareIn 共享 Flow（避免多個訂閱）
    val transactionStats: SharedFlow<TransactionStats> = repository
        .getAllTransactions()
        .map { transactions ->
            TransactionStats(
                totalIncome = transactions.filter { it.transaction.type == TransactionType.INCOME }.sumOf { it.transaction.amount },
                totalExpense = transactions.filter { it.transaction.type == TransactionType.EXPENSE }.sumOf { it.transaction.amount },
                transactionCount = transactions.size
            )
        }
        .shareIn(
            scope = viewModelScope,
            started = SharingStarted.WhileSubscribed(5000),
            replay = 1
        )

    // ✅ 優化 3: 明確取消 Job
    private var searchJob: Job? = null

    fun searchTransactions(query: String) {
        searchJob?.cancel()  // 取消前一個搜尋
        searchJob = viewModelScope.launch {
            repository.searchTransactions(query).collect { results ->
                // 處理搜尋結果
            }
        }
    }

    // ✅ 優化 4: ViewModel 清除時取消所有訂閱
    override fun onCleared() {
        super.onCleared()
        searchJob?.cancel()
        // viewModelScope 會自動取消所有 launch
    }
}
```

**Composable 端優化**:
```kotlin
@Composable
fun TransactionListScreen(
    viewModel: TransactionViewModel = hiltViewModel()
) {
    // ✅ 優化 5: 使用 collectAsStateWithLifecycle（Lifecycle-aware）
    val transactions by viewModel.transactions.collectAsStateWithLifecycle()

    // ✅ 當 Composable 離開畫面時，自動停止訂閱
    LazyColumn {
        items(
            items = transactions,
            key = { it.transaction.id }
        ) { transaction ->
            TransactionItem(transaction = transaction)
        }
    }
}
```

**依賴新增** (`app/build.gradle.kts`):
```kotlin
dependencies {
    // Lifecycle-aware State collection
    implementation("androidx.lifecycle:lifecycle-runtime-compose:2.7.0")
}
```

---

### 階段 5：APK 體積優化（1 週）

#### 3.5.1 啟用 R8 Code Shrinking

**在 Claude Code 輸入**:
```
請優化 APK 體積：

目標：從 150 MB 減至 < 50 MB

優化項目：
1. 啟用 R8 Code Shrinking
2. 移除未使用資源
3. 壓縮圖片（使用 WebP）
4. 啟用 App Bundle

請提供完整配置。
```

**Claude Code 生成** (`app/build.gradle.kts`):
```kotlin
plugins {
    id("com.android.application")
    kotlin("android")
    kotlin("kapt")
    id("dagger.hilt.android.plugin")
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

        // ✅ 優化 1: 限制語言（僅繁體中文和英文）
        resourceConfigurations += listOf("zh-rTW", "en")

        // ✅ 優化 2: 限制 ABI（僅 arm64-v8a）
        ndk {
            abiFilters += listOf("arm64-v8a")
        }
    }

    buildTypes {
        release {
            // ✅ 優化 3: 啟用 Minify（R8 Code Shrinking）
            isMinifyEnabled = true

            // ✅ 優化 4: 移除未使用資源
            isShrinkResources = true

            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )

            signingConfig = signingConfigs.getByName("debug")
        }
    }

    // ✅ 優化 5: 啟用 App Bundle（動態交付）
    bundle {
        language {
            enableSplit = true
        }
        density {
            enableSplit = true
        }
        abi {
            enableSplit = true
        }
    }

    // ✅ 優化 6: Compose 編譯優化
    buildFeatures {
        compose = true
    }

    composeOptions {
        kotlinCompilerExtensionVersion = "1.5.3"
    }

    // ✅ 優化 7: 打包選項
    packagingOptions {
        resources {
            excludes += "/META-INF/{AL2.0,LGPL2.1}"
            excludes += "DebugProbesKt.bin"  // Kotlin Coroutines Debug
        }
    }
}

dependencies {
    // 現有依賴...

    // ✅ 優化 8: 使用 Coil（替代 Glide，更輕量）
    implementation("io.coil-kt:coil-compose:2.5.0")

    // ✅ 優化 9: LeakCanary（僅 Debug 版）
    debugImplementation("com.squareup.leakcanary:leakcanary-android:2.12")
}
```

**ProGuard 規則** (`app/proguard-rules.pro`):
```proguard
# ✅ 保留 Hilt 相關類別
-keepclasseswithmembers class * {
    @dagger.* <methods>;
}
-keep class dagger.hilt.** { *; }

# ✅ 保留 Room Database
-keep class * extends androidx.room.RoomDatabase
-keep @androidx.room.Entity class *
-dontwarn androidx.room.paging.**

# ✅ 保留 Kotlin Coroutines
-keepnames class kotlinx.coroutines.internal.MainDispatcherFactory {}
-keepnames class kotlinx.coroutines.CoroutineExceptionHandler {}

# ✅ 保留 Compose
-keep class androidx.compose.** { *; }
-dontwarn androidx.compose.**

# ✅ 移除 Log（Release 版）
-assumenosideeffects class android.util.Log {
    public static *** d(...);
    public static *** v(...);
    public static *** i(...);
}
```

**圖片優化腳本** (`scripts/convert-to-webp.sh`):
```bash
#!/bin/bash

# ✅ 將所有 PNG/JPG 轉換為 WebP（減少 30-50% 體積）
find app/src/main/res -name "*.png" -o -name "*.jpg" | while read img; do
    cwebp -q 80 "$img" -o "${img%.*}.webp"
    rm "$img"  # 刪除原始圖片
done

echo "✅ 圖片轉換完成"
```

**執行優化**:
```bash
# 1. 轉換圖片為 WebP
chmod +x scripts/convert-to-webp.sh
./scripts/convert-to-webp.sh

# 2. 打包 Release APK
./gradlew assembleRelease

# 3. 打包 App Bundle（推薦）
./gradlew bundleRelease

# 4. 分析 APK 體積
./gradlew :app:analyzeReleaseBundle
```

**體積對比**:
```
優化前：
- APK 體積: 150 MB
- 包含: 所有語言、所有 ABI、未壓縮圖片

優化後：
- APK 體積: 42 MB  ✅ 減少 72%
- App Bundle: 35 MB（動態交付後實際下載僅 12 MB）
```

---

### 階段 6：啟動時間優化（1 週）

#### 3.6.1 優化冷啟動時間

**在 Claude Code 輸入**:
```
請優化 APP 冷啟動時間：

目標：從 5.4 秒減至 < 2 秒

優化項目：
1. Splash Screen 優化
2. Hilt 延遲初始化
3. 資料庫預載入優化

請提供完整方案。
```

**優化方案**:

**1. Splash Screen（使用 Android 12+ SplashScreen API）**:

`themes.xml`:
```xml
<resources>
    <!-- ✅ Splash Screen Theme -->
    <style name="Theme.ExpenseTracker.Splash" parent="Theme.SplashScreen">
        <item name="windowSplashScreenBackground">@color/primary</item>
        <item name="windowSplashScreenAnimatedIcon">@drawable/ic_app_logo</item>
        <item name="windowSplashScreenAnimationDuration">500</item>
        <item name="postSplashScreenTheme">@style/Theme.ExpenseTracker</item>
    </style>
</resources>
```

`AndroidManifest.xml`:
```xml
<activity
    android:name=".MainActivity"
    android:theme="@style/Theme.ExpenseTracker.Splash"  <!-- ✅ 使用 Splash Theme -->
    android:exported="true">
    <intent-filter>
        <action android:name="android.intent.action.MAIN" />
        <category android:name="android.intent.category.LAUNCHER" />
    </intent-filter>
</activity>
```

**2. Hilt 延遲初始化**:

`Application.kt`:
```kotlin
@HiltAndroidApp
class ExpenseTrackerApp : Application(), Configuration.Provider {

    @Inject
    lateinit var workManagerFactory: HiltWorkerFactory

    override fun onCreate() {
        super.onCreate()

        // ✅ 優化 1: 延遲初始化 WorkManager
        // 不在 onCreate 中初始化，改用 Configuration.Provider

        // ✅ 優化 2: StrictMode（僅 Debug）
        if (BuildConfig.DEBUG) {
            StrictMode.setThreadPolicy(
                StrictMode.ThreadPolicy.Builder()
                    .detectAll()
                    .penaltyLog()
                    .build()
            )
        }
    }

    // ✅ 延遲初始化 WorkManager
    override fun getWorkManagerConfiguration(): Configuration {
        return Configuration.Builder()
            .setWorkerFactory(workManagerFactory)
            .setMinimumLoggingLevel(if (BuildConfig.DEBUG) Log.DEBUG else Log.ERROR)
            .build()
    }
}
```

**3. 資料庫預載入優化**:

```kotlin
@Module
@InstallIn(SingletonComponent::class)
object DatabaseModule {

    @Provides
    @Singleton
    fun provideAppDatabase(
        @ApplicationContext context: Context
    ): AppDatabase {
        return Room.databaseBuilder(
            context,
            AppDatabase::class.java,
            "expense_tracker_db"
        )
            .addMigrations(AppDatabase.MIGRATION_1_2)
            // ✅ 優化 3: 延遲資料庫建立（首次查詢時才建立）
            .setJournalMode(RoomDatabase.JournalMode.WRITE_AHEAD_LOGGING)  // WAL 模式
            .build()
    }
}

// ✅ 優化 4: 使用 WorkManager 背景預載入資料
@HiltWorker
class DatabasePreloadWorker @AssistedInject constructor(
    @Assisted context: Context,
    @Assisted params: WorkerParameters,
    private val database: AppDatabase
) : CoroutineWorker(context, params) {

    override suspend fun doWork(): Result {
        return withContext(Dispatchers.IO) {
            try {
                // 預載入常用資料（類別清單）
                database.categoryDao().getAllCategories()
                Result.success()
            } catch (e: Exception) {
                Result.failure()
            }
        }
    }
}

// MainActivity.kt
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        // ✅ 優化 5: 安裝 Splash Screen
        installSplashScreen()

        super.onCreate(savedInstanceState)

        // ✅ 優化 6: 背景預載入資料庫
        enqueuePreloadWork()

        setContent {
            ExpenseTrackerTheme {
                NavGraph()
            }
        }
    }

    private fun enqueuePreloadWork() {
        val preloadRequest = OneTimeWorkRequestBuilder<DatabasePreloadWorker>()
            .build()

        WorkManager.getInstance(this).enqueue(preloadRequest)
    }
}
```

**4. Baseline Profiles（Jetpack Compose 優化）**:

`app/build.gradle.kts`:
```kotlin
android {
    // ✅ 啟用 Baseline Profiles
    defaultConfig {
        profileable = true
    }
}

dependencies {
    // ✅ Baseline Profile Installer
    implementation("androidx.profileinstaller:profileinstaller:1.3.1")

    // Baseline Profile Generator（用於生成）
    baselineProfile(project(":benchmark"))
}
```

**執行生成 Baseline Profile**:
```bash
# 1. 生成 Baseline Profile
./gradlew :app:generateBaselineProfile

# 2. Profile 會自動打包至 APK
./gradlew assembleRelease
```

**啟動時間對比**:
```
優化前：
- 冷啟動: 5,456ms
- timeToInitialDisplay: 4,234ms
- timeToFullDisplay: 5,456ms

優化後：
- 冷啟動: 1,678ms  ✅ 提升 69%
- timeToInitialDisplay: 980ms   ✅ 提升 77%
- timeToFullDisplay: 1,678ms    ✅ 提升 69%
```

---

### 階段 7：最終驗證與報告（1 週）

#### 3.7.1 執行完整效能測試

**在 Claude Code 輸入**:
```
請執行完整效能驗證：

1. 重新執行 Benchmark 測試
2. Android Profiler 驗證
3. 記憶體洩漏檢測（LeakCanary）
4. 使用者測試（Beta 版）

生成最終效能報告：`Docs/reports/performance-optimization-report.md`
```

**執行測試**:
```bash
# 1. Benchmark 測試
./gradlew :app:connectedAndroidTest

# 2. APK 體積分析
./gradlew :app:analyzeReleaseBundle

# 3. 記憶體洩漏檢測（安裝 Debug APK，使用 30 分鐘）
./gradlew installDebug
# 使用 APP 30 分鐘後，LeakCanary 會自動檢測並報告
```

**預期輸出** (`Docs/reports/performance-optimization-report.md`):
```markdown
# 效能優化最終報告

## 📊 效能指標對比

### 1. 啟動時間
| 指標 | 優化前 | 優化後 | 改善 |
|------|--------|--------|------|
| 冷啟動 | 5,456ms | 1,678ms | ✅ **69%** |
| 熱啟動 | 2,100ms | 450ms | ✅ **79%** |
| timeToInitialDisplay | 4,234ms | 980ms | ✅ **77%** |

### 2. UI 流暢度
| 指標 | 優化前 | 優化後 | 改善 |
|------|--------|--------|------|
| 平均 FPS | 28 | 58 | ✅ **107%** |
| Jank 次數/10秒 | 23 | 2 | ✅ **91%** |
| Frame 耗時 (P95) | 120ms | 14ms | ✅ **88%** |

### 3. 資料庫效能
| 指標 | 優化前 | 優化後 | 改善 |
|------|--------|--------|------|
| 查詢時間（500 筆） | 1,200ms | 45ms | ✅ **96%** |
| SQL 查詢次數 | 501 | 1 | ✅ **99.8%** |

### 4. 記憶體使用
| 指標 | 優化前 | 優化後 | 改善 |
|------|--------|--------|------|
| 初始記憶體 | 120 MB | 85 MB | ✅ **29%** |
| 使用 30 分鐘後 | 450 MB | 105 MB | ✅ **77%** |
| 記憶體洩漏 | 342 個實例 | 0 | ✅ **100%** |

### 5. APK 體積
| 指標 | 優化前 | 優化後 | 改善 |
|------|--------|--------|------|
| APK 體積 | 150 MB | 42 MB | ✅ **72%** |
| App Bundle | - | 35 MB | - |
| 實際下載（arm64） | 150 MB | 12 MB | ✅ **92%** |

### 6. 圖表載入
| 指標 | 優化前 | 優化後 | 改善 |
|------|--------|--------|------|
| 首次載入 | 3,450ms | 380ms | ✅ **89%** |
| 切換月份 | 2,100ms | 120ms | ✅ **94%** |
| CPU 使用率 | 85% | 35% | ✅ **59%** |

## ✅ 已完成優化項目

### UI 效能
- [x] LazyColumn 使用 key 參數
- [x] 使用 remember/derivedStateOf 減少重組
- [x] 圖示快取
- [x] 日期格式化快取
- [x] 使用 Paging 3 分頁載入

### 資料庫效能
- [x] 修復 N+1 查詢問題（使用 JOIN）
- [x] 新增索引（category_id, timestamp, type）
- [x] 使用 Flow 自動更新
- [x] Room Database WAL 模式

### 記憶體優化
- [x] 修復 Flow 訂閱洩漏（使用 stateIn/shareIn）
- [x] 使用 collectAsStateWithLifecycle
- [x] ViewModel onCleared 清理
- [x] LeakCanary 檢測（無洩漏）

### APK 體積
- [x] 啟用 R8 Code Shrinking
- [x] 移除未使用資源
- [x] 圖片轉換為 WebP
- [x] 限制語言和 ABI
- [x] App Bundle 動態交付

### 啟動時間
- [x] Splash Screen API
- [x] Hilt 延遲初始化
- [x] 資料庫背景預載入
- [x] Baseline Profiles

## 🎯 使用者體驗改善

| 場景 | 優化前 | 優化後 |
|------|--------|--------|
| 開啟 APP | 等待 5 秒 | 1.7 秒進入 ✅ |
| 滑動清單 | 明顯卡頓 | 流暢 60 FPS ✅ |
| 查看圖表 | 等待 3 秒 | 0.4 秒顯示 ✅ |
| 切換月份 | 等待 2 秒 | 0.12 秒切換 ✅ |
| 長時間使用 | APP 變慢 | 持續流暢 ✅ |

## 📱 測試設備

- **設備 1**: Samsung Galaxy S22 (Android 14)
- **設備 2**: Google Pixel 6 (Android 14)
- **設備 3**: Xiaomi 11 (Android 13)

## 🔍 未來優化建議

1. **圖表動畫**: 使用 Canvas 動畫（目前使用 Compose Animation）
2. **資料預測快取**: 預載入下個月資料
3. **離線支援**: Service Worker（PWA）
4. **暗色模式優化**: 減少白色背景功耗
```

---

## 附錄：命令速查表

### AISDLC Workflow 命令

| 階段 | Workflow | Claude Code 命令 |
|------|----------|-----------------|
| 效能分析 | performance-profiling-and-analysis | `請載入 AISDLC_INIT.md，執行「performance-profiling-and-analysis」workflow` |
| 效能驗證 | performance-testing-and-validation | `請執行「performance-testing-and-validation」workflow` |

### Android Studio Profiler

```bash
# 啟動 Profiler
View → Tool Windows → Profiler

# CPU Profiler
1. 選擇 CPU → Record
2. 執行測試場景
3. Stop → 分析 Top Down Tree

# Memory Profiler
1. 選擇 Memory → Record
2. 執行測試場景
3. Dump Java Heap → 分析 Shallow/Retained Size
```

### Benchmark 測試

```bash
# 執行 Macrobenchmark
./gradlew :app:connectedAndroidTest

# 僅執行啟動測試
./gradlew :app:connectedAndroidTest -Pandroid.testInstrumentationRunnerArguments.class=com.example.expensetracker.benchmark.StartupBenchmark

# 查看結果
adb pull /sdcard/Android/data/com.example.expensetracker/files/benchmarks/
```

### APK 優化命令

```bash
# 打包 Release APK
./gradlew assembleRelease

# 打包 App Bundle
./gradlew bundleRelease

# 分析 APK 體積
./gradlew :app:analyzeReleaseBundle

# APK Analyzer（Android Studio）
Build → Analyze APK...
```

### 記憶體洩漏檢測

```bash
# 安裝 Debug APK（包含 LeakCanary）
./gradlew installDebug

# 使用 APP 30 分鐘
# LeakCanary 會自動檢測並在通知欄顯示結果

# 查看 LeakCanary 報告
adb shell am start -n com.example.expensetracker/leakcanary.internal.activity.LeakActivity
```

### 圖片優化

```bash
# 轉換為 WebP
cwebp -q 80 input.png -o output.webp

# 批次轉換
find app/src/main/res -name "*.png" | while read img; do
    cwebp -q 80 "$img" -o "${img%.*}.webp"
    rm "$img"
done
```

---

## 🎯 效能優化時程表（總計 11.5 週）

| 階段 | 週數 | 主要工作 |
|------|-----|---------|
| 1. 效能基準測試與診斷 | 2 週 | Profiler 收集、Benchmark 測試、診斷報告 |
| 2. UI 效能優化 | 3 週 | LazyColumn、圖表、Paging 3 |
| 3. 資料庫效能優化 | 2 週 | 修復 N+1、新增索引、遷移腳本 |
| 4. 記憶體優化 | 1.5 週 | 修復洩漏、Flow 管理、LeakCanary |
| 5. APK 體積優化 | 1 週 | R8、資源移除、WebP、App Bundle |
| 6. 啟動時間優化 | 1 週 | Splash Screen、延遲初始化、Baseline Profile |
| 7. 最終驗證與報告 | 1 週 | 重新測試、生成報告、Beta 測試 |

**總計**: 11.5 週（約 3 個月）

---

## 📚 相關文檔

- [AISDLC_INIT.md](../../AISDLC_INIT.md) - 框架初始化
- [performance-profiling-and-analysis.md](../../workflow/scenario-specific/performance-profiling-and-analysis.md)
- [performance-testing-and-validation.md](../../workflow/scenario-specific/performance-testing-and-validation.md)
- [Android Profiler 官方文檔](https://developer.android.com/studio/profile)
- [Jetpack Macrobenchmark 指南](https://developer.android.com/topic/performance/benchmarking/macrobenchmark-overview)

---

**版本**: 1.0
**作者**: AISDLC Framework Team
**最後更新**: 2025-12-15
