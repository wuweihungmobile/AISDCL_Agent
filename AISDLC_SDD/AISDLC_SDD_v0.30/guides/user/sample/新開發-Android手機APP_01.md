# Android 記帳 APP 開發完整範例

> **SDD v0.01 使用者提示**：本指南基於 AISDLC-SDD v0.01。使用 AISDLC-SDD v0.01 時，請同時參考對應場景的 SDD Enhancement 文件（`scenarios/{scenario}/SDD_{SCENARIO}_ENHANCEMENT.md`），並確認所有 SCG 閘門步驟已整合到您的工作流程中。

---
# AISDLC Framework - Mobile App Development Guide

**版本**: v0.01
**建立日期**: 2025-12-13
**適用情境**: Greenfield Mobile App 開發
**範例專案**: MoneyTracker - Android 記帳軟體

---

## 🎯 專案概述

**專案名稱**: MoneyTracker
**專案類型**: Android 原生記帳 APP
**目標平台**: Android（Kotlin）
**開發工具**: Cursor AI + Claude Code
**AISDLC 版本**: v0.01

---

## 📂 步驟 1: Cursor AI 專案路徑設定

### 1.1 建立專案目錄

```bash
# 在你的工作目錄建立專案資料夾
mkdir MoneyTracker_Android
cd MoneyTracker_Android

# 建立基本目錄結構
mkdir -p {docs,src,tests}
```

### 1.2 開啟 Cursor AI

1. 啟動 Cursor AI
2. **File → Open Folder**
3. 選擇 `MoneyTracker_Android` 資料夾
4. 確認左側檔案樹顯示專案路徑

**預期結果**:
```
MoneyTracker_Android/
├── docs/
├── src/
└── tests/
```

---

## 🔧 步驟 2: 安裝設定 AISDLC Framework

### 2.1 複製 AISDLC Framework 到專案

```bash
# 方法 1: 直接複製（推薦）
cp -r ~/Cursor_Project/AISDLC_ALL/AISDLC_v0.09 ./AISDLC

# 方法 2: 建立符號連結（進階）
ln -s ~/Cursor_Project/AISDLC_ALL/AISDLC_v0.09 ./AISDLC
```

### 2.2 驗證安裝

```bash
# 檢查 AISDLC 目錄結構
ls -la AISDLC/
# 預期輸出: agent/ workflow/ docs_template/ scenarios/ guides/ prompts/
```

### 2.3 專案目錄結構（完整）

```
MoneyTracker_Android/
├── AISDLC/                    # AISDLC Framework
│   ├── AISDLC_INIT.md         # 必讀：框架初始化文檔
│   ├── agent/
│   ├── workflow/
│   ├── docs_template/
│   ├── scenarios/
│   └── guides/
├── docs/                      # 專案文檔（將產出 PRD/FRD/SRD）
├── src/                       # 原始碼
└── tests/                     # 測試
```

---

## 💬 步驟 3: Claude Code 開發流程（完整範例）

### 階段 0: 框架初始化（必須！）

**Cursor AI → Chat 面板 → 輸入指令**:

```
請載入 AISDLC Framework 初始化文檔：

請讀取並執行：AISDLC/AISDLC_INIT.md
```

**預期回應**:
```
✅ AISDLC Framework v0.01 已載入
✅ On-demand Loading 機制啟用
✅ 準備開始 Greenfield 開發流程
```

---

### 階段 1: 需求蒐集（2-3 小時）

#### 1.1 啟動 Greenfield SOP

**輸入指令**:
```
我要開發一個 Android 記帳 APP，請開始執行 Greenfield SOP。

專案名稱：MoneyTracker
平台：Android（原生 Kotlin）
目標使用者：個人使用者（記帳需求）
```

**預期回應**:
```
✅ SA-Analyst (Amanda) 已載入 - 準備進行需求分析
✅ BA-Business-Analyst (Beatrice) 已載入 - 準備驗證商業需求

【需求蒐集問卷】
請回答以下問題...
```

#### 1.2 回答需求問卷

**AI 提問範例**:
```
Q1. 核心功能需求？
Q2. 目標使用者是誰？
Q3. 是否需要雲端同步？
Q4. 預算與時程限制？
```

**你的回答範例**:
```
A1. 核心功能：
    - 記帳（收入/支出/轉帳）
    - 類別管理（自訂類別）
    - 統計報表（月報、年報）
    - 預算管理（設定月預算）

A2. 目標使用者：
    - 20-40 歲個人使用者
    - 需要簡單易用的記帳工具
    - 通勤路上快速記帳

A3. 雲端同步：
    - Phase 1 不需要（僅本地儲存）
    - Phase 2 考慮 Google Drive 同步

A4. 預算時程：
    - 預算：個人專案（無預算限制）
    - 時程：3 個月內完成 MVP
```

#### 1.3 確認需求文檔

**AI 輸出**:
```
✅ 需求分析完成！

【產出文檔】
- docs/PRD_MoneyTracker_v1.0.md
- docs/Requirement_Analysis_Report.md

【下一步】
請確認需求文檔，確認後我們進入 Stage 2（需求驗證）
```

**你的指令**:
```
請幫我打開 PRD 文檔預覽，確認無誤後繼續。
```

---

### 階段 2: 需求驗證與威脅建模（3-4 小時）

#### 2.1 需求驗證

**輸入指令**:
```
需求確認無誤，請進入 Stage 2 需求驗證與威脅建模。
```

**AI 執行**:
```
✅ 正在執行需求一致性檢查...
✅ 正在執行 STRIDE 威脅建模...

【威脅建模結果】
- 識別 12 個潛在威脅
- 產出 5 個安全需求（NFR-SEC-001 ~ 005）

【產出文檔】
- docs/FRD_MoneyTracker_v1.0.md
- docs/STRIDE_Threat_Analysis.md
```

#### 2.2 確認 FRD 文檔

**你的指令**:
```
請展示 FRD 中的 User Story 列表和安全需求。
```

**AI 回應**:
```
【User Story 列表】
- US-001: 使用者可以新增一筆支出記錄
- US-002: 使用者可以查看本月支出統計
- US-003: 使用者可以設定月預算
... (共 15 個 User Story)

【安全需求】
- NFR-SEC-001: 本地資料庫加密（SQLCipher）
- NFR-SEC-002: 密碼保護（選用 4-6 位數 PIN）
- NFR-SEC-003: 敏感資料遮罩（在多工畫面）
```

---

### 階段 3: 技術選型（2-4 小時）

#### 3.1 平台識別

**輸入指令**:
```
請進入 Stage 3 技術選型階段。
```

**AI 執行**:
```
✅ SD-Architect (Marcus) 已載入 - 準備進行技術選型

【平台識別】
- 使用場景：通勤路上、等待結帳時 → Mobile
- 離線功能：需要 → Native App
- 硬體功能：相機（拍攝收據）→ Native
- 平台：Android → 原生 Kotlin

【建議 Specialized Agent】
- Mobile-Architect (專注 Android 架構)
```

#### 3.2 技術棧評估

**AI 提問**:
```
【技術選型問題】
Q1. 團隊技能：Kotlin / Java / React Native / Flutter？
Q2. 最低支援 Android 版本？
Q3. 是否需要 Material Design 3？
```

**你的回答**:
```
A1. Kotlin（現代化、官方推薦）
A2. Android 8.0 (API 26) 以上
A3. 是，使用 Material Design 3
```

**AI 輸出**:
```
✅ 技術選型完成！

【推薦技術棧】
- 語言: Kotlin 1.9+
- 架構: MVVM (ViewModel + LiveData)
- UI: Jetpack Compose + Material Design 3
- 資料庫: Room (SQLite) + SQLCipher
- DI: Hilt
- 非同步: Kotlin Coroutines + Flow

【技術選型評估矩陣】
| 維度 | Kotlin+Compose | React Native | Flutter |
|------|---------------|--------------|---------|
| 功能性 | 5 | 4 | 4 |
| 成本 | 5 | 4 | 4 |
| 學習曲線 | 4 | 5 | 3 |
| 社群支援 | 5 | 5 | 4 |
| 風險評估 | 5 | 3 | 4 |
| **加權總分** | **4.8** | **4.2** | **3.8** |

【決策理由】
1. 功能性：原生 API 完整支援
2. 效能：Compose 效能優於跨平台方案
3. 長期維護：Google 官方支援，生態系成熟

【產出文檔】
- docs/Tech_Stack_Selection_Report.md
- docs/Architecture_Decision_Record.md
```

---

### 階段 4-5: 系統架構設計（4-6 小時）

#### 4.1 架構設計

**輸入指令**:
```
技術選型確認，請進入系統架構設計階段（Stage 4-5）。
```

**AI 執行**:
```
✅ 正在設計 C4 Model Level 1-3...
✅ 正在設計資料庫 Schema...
✅ 正在設計 MVVM 架構...

【產出文檔】
- docs/SRD_MoneyTracker_System_Architecture.md
- docs/SRD_Database_Schema.md
- docs/SRD_UI_Component_Design.md

【架構總覽】
```
┌─────────────────────────────────────────┐
│         MoneyTracker - C4 Level 2       │
└─────────────────────────────────────────┘

📱 UI Layer (Jetpack Compose)
   ├─ TransactionScreen
   ├─ StatisticsScreen
   └─ SettingsScreen
          ↓
🧠 ViewModel Layer (MVVM)
   ├─ TransactionViewModel
   ├─ StatisticsViewModel
   └─ SettingsViewModel
          ↓
📦 Repository Layer
   ├─ TransactionRepository
   ├─ CategoryRepository
   └─ BudgetRepository
          ↓
🗄️ Database Layer (Room + SQLCipher)
   ├─ TransactionDao
   ├─ CategoryDao
   └─ BudgetDao
```
```

#### 4.2 確認 SRD 文檔

**你的指令**:
```
請展示資料庫 Schema 設計。
```

**AI 回應**:
```sql
-- Transaction Table
CREATE TABLE transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL,          -- 'INCOME', 'EXPENSE', 'TRANSFER'
    amount REAL NOT NULL,
    category_id INTEGER,
    date TEXT NOT NULL,          -- ISO 8601
    note TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES categories(id)
);

-- Category Table
CREATE TABLE categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    type TEXT NOT NULL,          -- 'INCOME', 'EXPENSE'
    icon TEXT,
    color TEXT
);

-- Budget Table
CREATE TABLE budgets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    month TEXT NOT NULL,         -- 'YYYY-MM'
    category_id INTEGER,
    limit_amount REAL NOT NULL,
    FOREIGN KEY (category_id) REFERENCES categories(id)
);
```

---

### 階段 6-8: 實作開發（4-8 週）

#### 6.1 初始化 Android 專案

**輸入指令**:
```
請協助我建立 Android 專案基礎架構。

需求：
1. Kotlin + Jetpack Compose
2. MVVM 架構
3. Hilt DI
4. Room Database
```

**AI 執行**:
```
✅ 正在建立專案結構...
✅ 正在配置 build.gradle...
✅ 正在建立 MVVM 基礎類別...

【建立檔案清單】
- app/build.gradle.kts (Hilt, Room, Compose 配置)
- src/main/AndroidManifest.xml
- src/main/java/com/example/moneytracker/
  ├── di/AppModule.kt
  ├── data/
  │   ├── database/AppDatabase.kt
  │   ├── dao/TransactionDao.kt
  │   ├── entity/Transaction.kt
  │   └── repository/TransactionRepository.kt
  ├── ui/
  │   ├── screen/TransactionScreen.kt
  │   └── viewmodel/TransactionViewModel.kt
  └── MainActivity.kt
```

#### 6.2 開發核心功能

**你的指令（範例）**:
```
請實作 US-001：使用者可以新增一筆支出記錄

需求：
- TransactionScreen UI（Compose）
- TransactionViewModel
- TransactionRepository
- 儲存至 Room Database
```

**AI 回應**:
```kotlin
// TransactionScreen.kt
@Composable
fun TransactionScreen(viewModel: TransactionViewModel = hiltViewModel()) {
    var amount by remember { mutableStateOf("") }
    var note by remember { mutableStateOf("") }

    Column(modifier = Modifier.padding(16.dp)) {
        OutlinedTextField(
            value = amount,
            onValueChange = { amount = it },
            label = { Text("金額") },
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number)
        )

        OutlinedTextField(
            value = note,
            onValueChange = { note = it },
            label = { Text("備註") }
        )

        Button(onClick = {
            viewModel.addTransaction(
                type = TransactionType.EXPENSE,
                amount = amount.toDouble(),
                note = note
            )
        }) {
            Text("新增支出")
        }
    }
}

// TransactionViewModel.kt
@HiltViewModel
class TransactionViewModel @Inject constructor(
    private val repository: TransactionRepository
) : ViewModel() {

    fun addTransaction(type: TransactionType, amount: Double, note: String) {
        viewModelScope.launch {
            repository.insert(
                Transaction(
                    type = type,
                    amount = amount,
                    note = note,
                    date = LocalDateTime.now()
                )
            )
        }
    }
}
```

---

### 階段 9: 測試與驗證（1-2 週）

#### 9.1 執行測試

**輸入指令**:
```
請協助建立 Unit Test 和 UI Test。

測試範圍：
- TransactionViewModel Unit Test
- TransactionScreen UI Test（Compose Test）
```

**AI 產出**:
```kotlin
// TransactionViewModelTest.kt
@Test
fun `addTransaction should insert transaction to repository`() = runTest {
    // Given
    val repository = mockk<TransactionRepository>(relaxed = true)
    val viewModel = TransactionViewModel(repository)

    // When
    viewModel.addTransaction(
        type = TransactionType.EXPENSE,
        amount = 100.0,
        note = "午餐"
    )

    // Then
    coVerify { repository.insert(any()) }
}

// TransactionScreenTest.kt
@Test
fun `should display amount and note input fields`() {
    composeTestRule.setContent {
        TransactionScreen()
    }

    composeTestRule.onNodeWithText("金額").assertExists()
    composeTestRule.onNodeWithText("備註").assertExists()
}
```

---

## 📊 完整開發時程參考

| 階段 | 時間 | 產出文檔 |
|------|------|---------|
| Stage 1-2: 需求分析 | 1 週 | PRD, FRD |
| Stage 3: 技術選型 | 3 天 | Tech Stack Report, ADR |
| Stage 4-5: 架構設計 | 1 週 | SRD, Database Schema |
| Stage 6-8: 開發實作 | 6 週 | 原始碼, Unit Tests |
| Stage 9: 測試驗證 | 1 週 | Test Report |
| **總計** | **10 週** | **完整文檔 + 可交付 APP** |

---

## ✅ 關鍵成功因素

### 1. 嚴格遵循 SOP
- ✅ 每個階段都必須產出對應文檔
- ✅ 不跳過確認點（🔴 標記）
- ✅ 文檔先行，程式碼後行

### 2. 充分利用 Agent
- ✅ SA-Analyst: 需求澄清與驗證
- ✅ SD-Architect: 技術選型與架構設計
- ✅ Mobile-Architect: Android 專業建議
- ✅ QA-Tester: 測試案例與驗收標準

### 3. 文檔追蹤性
- ✅ PRD → FRD → SRD → Code 完整追蹤
- ✅ 每個功能都有對應 User Story ID
- ✅ 測試案例對應驗收標準

---

## 🚀 快速開始指令（Copy & Paste）

```bash
# Step 1: 建立專案
mkdir MoneyTracker_Android && cd MoneyTracker_Android
mkdir -p {docs,src,tests}

# Step 2: 複製 AISDLC Framework
cp -r ~/Cursor_Project/AISDLC_ALL/AISDLC_v0.09 ./AISDLC

# Step 3: 開啟 Cursor AI
# File → Open Folder → 選擇 MoneyTracker_Android
```

**Cursor AI Chat 第一個指令**:
```
請載入 AISDLC Framework 並開始 Greenfield Mobile App 開發流程：

讀取：AISDLC/AISDLC_INIT.md

專案名稱：MoneyTracker
平台：Android (Kotlin + Jetpack Compose)
```

---

## 📚 參考文檔

- [Greenfield SOP](../../scenarios/greenfield/SOP.md)
- [Mobile Architecture Guide](../../scenarios/greenfield/README.md)
- [Tech Stack Selection Matrix](../system/planning/Tech_Stack_Selection_Matrix.md)
- [AISDLC_INIT.md](../../../AISDLC_INIT.md)

---

**維護記錄**:
- v0.01 (2025-12-13): 初版建立（Android 記帳 APP 完整範例）
