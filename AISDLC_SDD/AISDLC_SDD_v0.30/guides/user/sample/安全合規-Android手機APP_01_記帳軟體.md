# 安全與合規：Android 記帳 APP

> **場景**: Security & Compliance - Android 記帳 APP 安全評估與合規檢查
> **技術棧**: Kotlin + Jetpack Compose + MVVM + Hilt + Python API
> **AISDLC 版本**: v0.01
> **更新日期**: 2025-12-16


> **SDD v0.01 使用者提示**：本指南基於 AISDLC-SDD v0.01。使用 AISDLC-SDD v0.01 時，請同時參考對應場景的 SDD Enhancement 文件（`scenarios/{scenario}/SDD_{SCENARIO}_ENHANCEMENT.md`），並確認所有 SCG 閘門步驟已整合到您的工作流程中。

---
---

## 📋 目錄

1. [第一步：Cursor AI 專案路徑設定](#第一步cursor-ai-專案路徑設定)
2. [第二步：AISDLC 框架安裝](#第二步aisdlc-框架安裝)
3. [第三步：Claude Code 完整安全流程](#第三步claude-code-完整安全流程)
4. [附錄：安全工具與命令](#附錄安全工具與命令)

---

## 第一步：Cursor AI 專案路徑設定

### 1.1 分析現有專案結構

**假設現有專案結構**:
```
ExpenseTrackerApp/
├── app/
│   ├── src/main/java/com/example/expensetracker/
│   │   ├── ui/                         # UI 層
│   │   ├── data/                       # 資料層
│   │   │   ├── local/                  # ⚠️ 本地資料庫（敏感資料）
│   │   │   └── remote/                 # ⚠️ API 呼叫（傳輸安全）
│   │   ├── domain/                     # 業務邏輯
│   │   └── di/                         # 依賴注入
│   └── build.gradle.kts
├── backend/                            # Python API（若有）
│   ├── app.py
│   └── requirements.txt
└── gradle/
```

**安全隱憂**:
- ❌ 敏感資料未加密（交易記錄、密碼）
- ❌ API 通訊未加密（HTTP 非 HTTPS）
- ❌ 無身份驗證機制（PIN/生物辨識）
- ❌ 資料庫未加密（SQLCipher）
- ❌ 無程式碼混淆（ProGuard/R8）

### 1.2 建立安全評估結構

**在終端機執行**:
```bash
cd ~/Projects/ExpenseTrackerApp

# 建立安全文檔目錄
mkdir -p Docs/security
mkdir -p Docs/security/assessment        # 安全評估報告
mkdir -p Docs/security/vulnerabilities   # 漏洞清單
mkdir -p Docs/security/compliance        # 合規文檔

# 建立安全測試目錄
mkdir -p security-tests
mkdir -p security-tests/static-analysis  # 靜態分析報告
mkdir -p security-tests/dynamic-analysis # 動態分析報告
mkdir -p security-tests/penetration      # 滲透測試報告

# 驗證
tree -L 2 Docs/security security-tests
```

**完整專案結構**:
```
ExpenseTrackerApp/
├── app/
├── Docs/
│   └── security/                       # 📄 安全文檔
│       ├── assessment/
│       ├── vulnerabilities/
│       └── compliance/
├── security-tests/                     # 🔒 安全測試
│   ├── static-analysis/
│   ├── dynamic-analysis/
│   └── penetration/
└── AISDLC_SDD_v0.01/                      # 🔴 步驟 2 安裝
```

### 1.3 開啟 Cursor AI

1. **Cursor AI**: `File` → `Open Folder...`
2. 選擇 `~/Projects/ExpenseTrackerApp`

---

## 第二步：AISDLC 框架安裝

### 2.1 符號連結安裝

```bash
cd ~/Projects/ExpenseTrackerApp
ln -s ~/Cursor_Project/AISDLC_ALL/AISDLC_v0.09 AISDLC_v0.09
ls -lah | grep AISDLC
```

### 2.2 驗證安裝

```bash
ls -la AISDLC_SDD_v0.01/AISDLC_INIT.md
cat AISDLC_SDD_v0.01/scenarios/security/SOP_QuickRef.md | head -50
```

---

## 第三步：Claude Code 完整安全流程

### 階段 1：安全需求分析（2-3 小時）

#### 3.1.1 啟動安全評估 Workflow

**在 Claude Code 輸入**:
```
請載入 AISDLC_INIT.md，我要進行「安全與合規」場景。

目標：Android 記帳 APP 安全評估與合規檢查

技術棧：
- 前端：Kotlin + Jetpack Compose + MVVM + Hilt
- 資料庫：Room Database
- 後端：Python FastAPI（可選）

安全隱憂：
1. 敏感資料未加密（交易記錄、密碼）
2. API 通訊未加密（HTTP）
3. 無身份驗證機制
4. 資料庫未加密
5. 無程式碼混淆

請執行「security-assessment」workflow，生成安全評估計畫。
```

#### 3.1.2 生成威脅模型

**在 Claude Code 輸入**:
```
請載入 Security Agent，生成威脅模型（STRIDE）：

資產識別：
1. 敏感資料
   - 交易記錄（金額、類別、備註）
   - 使用者帳戶（Email、密碼）
   - 銀行帳戶資訊（可選）

2. 系統元件
   - Android APP（前端）
   - Room Database（本地儲存）
   - Python API（後端，若有）
   - SQLite 資料庫檔案

威脅建模（STRIDE）：
- Spoofing（偽造）：無身份驗證
- Tampering（篡改）：資料庫未加密
- Repudiation（否認）：無稽核日誌
- Information Disclosure（資訊洩漏）：HTTP 傳輸
- Denial of Service（阻斷服務）：無 Rate Limiting
- Elevation of Privilege（權限提升）：無權限檢查

請生成威脅模型文檔：`Docs/security/assessment/threat-model.md`
```

**預期輸出** (`threat-model.md`):
```markdown
# 記帳 APP 威脅模型

## 資產清單

### 高價值資產
1. **交易記錄**
   - 風險：金融隱私洩漏
   - 影響：使用者財務狀況曝光

2. **使用者憑證**
   - 風險：帳號被盜用
   - 影響：未授權存取

3. **資料庫檔案**
   - 風險：完整資料外洩
   - 影響：Root 設備可直接讀取

## STRIDE 威脅分析

### S - Spoofing（偽造身份）
- **威脅**: 攻擊者偽裝成合法使用者
- **現狀**: 無 PIN/生物辨識
- **風險**: 🔴 Critical
- **建議**: 實施多因素驗證（MFA）

### T - Tampering（資料篡改）
- **威脅**: 資料庫被惡意修改
- **現狀**: SQLite 未加密
- **風險**: 🔴 Critical
- **建議**: 使用 SQLCipher 加密

### R - Repudiation（否認操作）
- **威脅**: 無法追蹤操作記錄
- **現狀**: 無稽核日誌
- **風險**: 🟡 Medium
- **建議**: 實施操作日誌

### I - Information Disclosure（資訊洩漏）
- **威脅**: 敏感資料外洩
- **現狀**: HTTP 傳輸、未加密儲存
- **風險**: 🔴 Critical
- **建議**: HTTPS + 資料加密

### D - Denial of Service（阻斷服務）
- **威脅**: API 被惡意大量呼叫
- **現狀**: 無 Rate Limiting
- **風險**: 🟡 Medium
- **建議**: 實施速率限制

### E - Elevation of Privilege（權限提升）
- **威脅**: 攻擊者取得管理員權限
- **現狀**: 無權限檢查
- **風險**: 🟢 Low
- **建議**: 最小權限原則

## 優先修復清單

| 威脅 | 風險 | 優先級 | 預計工時 |
|------|------|--------|---------|
| 資料庫未加密 | 🔴 Critical | P0 | 8 小時 |
| HTTP 傳輸 | 🔴 Critical | P0 | 4 小時 |
| 無身份驗證 | 🔴 Critical | P0 | 16 小時 |
| 無程式碼混淆 | 🟡 High | P1 | 2 小時 |
| 無稽核日誌 | 🟡 Medium | P2 | 8 小時 |
```

---

### 階段 2：漏洞掃描（3-4 小時）

#### 3.2.1 靜態分析掃描

**在 Claude Code 輸入**:
```
請配置靜態分析工具，掃描 Android APP 安全漏洞：

工具選擇：
1. Android Lint（內建）
2. Detekt（Kotlin 程式碼品質）
3. SpotBugs（安全漏洞）
4. OWASP Dependency-Check（依賴掃描）

請更新 `app/build.gradle.kts` 並執行掃描。
```

**Claude Code 生成** (`app/build.gradle.kts`):
```kotlin
plugins {
    id("com.android.application")
    kotlin("android")
    kotlin("kapt")
    id("dagger.hilt.android.plugin")
    id("io.gitlab.arturbosch.detekt") version "1.23.4"  // ✅ Detekt
}

android {
    namespace = "com.example.expensetracker"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.example.expensetracker"
        minSdk = 24
        targetSdk = 34
    }

    // ✅ Lint 配置
    lint {
        checkDependencies = true
        abortOnError = true
        warningsAsErrors = true
        baseline = file("lint-baseline.xml")
    }

    // ✅ ProGuard/R8 混淆
    buildTypes {
        release {
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
    }
}

// ✅ Detekt 配置
detekt {
    buildUponDefaultConfig = true
    config = files("$projectDir/detekt.yml")
    baseline = file("$projectDir/detekt-baseline.xml")
}

dependencies {
    // 主程式依賴...

    // ✅ 安全相關依賴
    implementation("androidx.security:security-crypto:1.1.0-alpha06")  // EncryptedSharedPreferences
    implementation("net.zetetic:android-database-sqlcipher:4.5.4")     // SQLCipher
    implementation("androidx.biometric:biometric:1.1.0")                // 生物辨識

    // ✅ 靜態分析工具
    detektPlugins("io.gitlab.arturbosch.detekt:detekt-formatting:1.23.4")
}
```

**執行靜態分析**:
```bash
# Lint 掃描
./gradlew lint

# Detekt 掃描
./gradlew detekt

# 查看報告
open app/build/reports/lint-results.html
open app/build/reports/detekt/detekt.html
```

#### 3.2.2 依賴漏洞掃描

**在 Claude Code 輸入**:
```
請使用 OWASP Dependency-Check 掃描第三方套件漏洞：

掃描範圍：
- Gradle 依賴
- Kotlin 標準庫
- AndroidX 函式庫
- 第三方套件

請生成漏洞報告：`security-tests/static-analysis/dependency-vulnerabilities.md`
```

**執行依賴掃描**:
```bash
# 安裝 OWASP Dependency-Check
brew install dependency-check

# 掃描專案
dependency-check --project ExpenseTrackerApp --scan . --format HTML --out security-tests/static-analysis/

# 查看報告
open security-tests/static-analysis/dependency-check-report.html
```

---

### 階段 3：安全修復實施（2-3 天）

#### 3.3.1 資料庫加密（SQLCipher）

**在 Claude Code 輸入**:
```
請實施資料庫加密，使用 SQLCipher：

需求：
1. 整合 SQLCipher 到 Room Database
2. 使用 Android Keystore 儲存加密金鑰
3. 設定資料庫密碼

請修改 `app/src/main/java/com/example/expensetracker/data/local/AppDatabase.kt`
```

**Claude Code 生成** (`AppDatabase.kt`):
```kotlin
package com.example.expensetracker.data.local

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase
import net.sqlcipher.database.SQLiteDatabase
import net.sqlcipher.database.SupportFactory
import javax.inject.Inject

@Database(
    entities = [TransactionEntity::class, CategoryEntity::class],
    version = 1,
    exportSchema = false
)
abstract class AppDatabase : RoomDatabase() {
    abstract fun transactionDao(): TransactionDao
    abstract fun categoryDao(): CategoryDao

    companion object {
        private const val DATABASE_NAME = "expense_tracker.db"

        @Volatile
        private var INSTANCE: AppDatabase? = null

        fun getInstance(context: Context): AppDatabase {
            return INSTANCE ?: synchronized(this) {
                val instance = buildDatabase(context)
                INSTANCE = instance
                instance
            }
        }

        private fun buildDatabase(context: Context): AppDatabase {
            // ✅ 從 Android Keystore 取得加密金鑰
            val passphrase = getOrCreateDatabaseKey(context)

            // ✅ 建立 SQLCipher 加密工廠
            val factory = SupportFactory(SQLiteDatabase.getBytes(passphrase))

            return Room.databaseBuilder(
                context.applicationContext,
                AppDatabase::class.java,
                DATABASE_NAME
            )
                .openHelperFactory(factory)  // ✅ 啟用加密
                .fallbackToDestructiveMigration()
                .build()
        }

        private fun getOrCreateDatabaseKey(context: Context): CharArray {
            // ✅ 使用 EncryptedSharedPreferences 儲存金鑰
            val masterKey = MasterKey.Builder(context)
                .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
                .build()

            val encryptedPrefs = EncryptedSharedPreferences.create(
                context,
                "secure_prefs",
                masterKey,
                EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
                EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
            )

            // 檢查是否已有金鑰
            var key = encryptedPrefs.getString("db_key", null)
            if (key == null) {
                // 生成新金鑰
                key = generateSecureRandomKey()
                encryptedPrefs.edit().putString("db_key", key).apply()
            }

            return key.toCharArray()
        }

        private fun generateSecureRandomKey(): String {
            val random = SecureRandom()
            val bytes = ByteArray(32)  // 256-bit key
            random.nextBytes(bytes)
            return Base64.encodeToString(bytes, Base64.NO_WRAP)
        }
    }
}
```

#### 3.3.2 身份驗證（生物辨識 + PIN）

**在 Claude Code 輸入**:
```
請實施身份驗證機制：

功能：
1. 生物辨識（指紋/Face ID）
2. PIN 碼備用驗證
3. 自動鎖定（30 秒無操作）

請生成檔案：`app/src/main/java/com/example/expensetracker/auth/BiometricAuthManager.kt`
```

**Claude Code 生成** (`BiometricAuthManager.kt`):
```kotlin
package com.example.expensetracker.auth

import android.content.Context
import androidx.biometric.BiometricManager
import androidx.biometric.BiometricPrompt
import androidx.core.content.ContextCompat
import androidx.fragment.app.FragmentActivity
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class BiometricAuthManager @Inject constructor(
    private val context: Context
) {
    // ✅ 檢查生物辨識可用性
    fun isBiometricAvailable(): Boolean {
        val biometricManager = BiometricManager.from(context)
        return when (biometricManager.canAuthenticate(
            BiometricManager.Authenticators.BIOMETRIC_STRONG
        )) {
            BiometricManager.BIOMETRIC_SUCCESS -> true
            else -> false
        }
    }

    // ✅ 顯示生物辨識提示
    fun authenticate(
        activity: FragmentActivity,
        onSuccess: () -> Unit,
        onError: (String) -> Unit,
        onFailed: () -> Unit
    ) {
        val executor = ContextCompat.getMainExecutor(context)

        val biometricPrompt = BiometricPrompt(
            activity,
            executor,
            object : BiometricPrompt.AuthenticationCallback() {
                override fun onAuthenticationSucceeded(result: BiometricPrompt.AuthenticationResult) {
                    super.onAuthenticationSucceeded(result)
                    onSuccess()
                }

                override fun onAuthenticationError(errorCode: Int, errString: CharSequence) {
                    super.onAuthenticationError(errorCode, errString)
                    onError(errString.toString())
                }

                override fun onAuthenticationFailed() {
                    super.onAuthenticationFailed()
                    onFailed()
                }
            }
        )

        // ✅ 設定提示資訊
        val promptInfo = BiometricPrompt.PromptInfo.Builder()
            .setTitle("身份驗證")
            .setSubtitle("使用指紋或 Face ID 解鎖")
            .setNegativeButtonText("使用 PIN 碼")
            .setAllowedAuthenticators(
                BiometricManager.Authenticators.BIOMETRIC_STRONG
            )
            .build()

        biometricPrompt.authenticate(promptInfo)
    }
}
```

#### 3.3.3 HTTPS 通訊（Retrofit + SSL Pinning）

**在 Claude Code 輸入**:
```
請實施 HTTPS 安全通訊：

功能：
1. 強制使用 HTTPS
2. SSL Certificate Pinning
3. 禁止使用 HTTP

請修改：`app/src/main/java/com/example/expensetracker/data/remote/ApiClient.kt`
```

**Claude Code 生成** (`ApiClient.kt`):
```kotlin
package com.example.expensetracker.data.remote

import okhttp3.CertificatePinner
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit

object ApiClient {
    private const val BASE_URL = "https://api.example.com/"  // ✅ 強制 HTTPS

    // ✅ SSL Certificate Pinning
    private val certificatePinner = CertificatePinner.Builder()
        .add("api.example.com", "sha256/AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=")
        .build()

    private val okHttpClient = OkHttpClient.Builder()
        .certificatePinner(certificatePinner)  // ✅ 啟用 Certificate Pinning
        .addInterceptor(HttpLoggingInterceptor().apply {
            level = if (BuildConfig.DEBUG) {
                HttpLoggingInterceptor.Level.BODY
            } else {
                HttpLoggingInterceptor.Level.NONE
            }
        })
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .build()

    val retrofit: Retrofit = Retrofit.Builder()
        .baseUrl(BASE_URL)
        .client(okHttpClient)
        .addConverterFactory(GsonConverterFactory.create())
        .build()
}
```

#### 3.3.4 程式碼混淆（ProGuard/R8）

**在 Claude Code 輸入**:
```
請配置 ProGuard 規則，保護程式碼：

混淆範圍：
- 業務邏輯
- 加密邏輯
- API 呼叫

保留項目：
- Room Database Entities
- Retrofit Interfaces
- Gson Models

請生成：`app/proguard-rules.pro`
```

**Claude Code 生成** (`proguard-rules.pro`):
```proguard
# ==================== 基本混淆規則 ====================

# ✅ 啟用混淆
-dontskipnonpubliclibraryclasses
-optimizations !code/simplification/arithmetic,!code/simplification/cast,!field/*,!class/merging/*
-optimizationpasses 5
-allowaccessmodification

# ==================== 保留 Room Database ====================

-keep class * extends androidx.room.RoomDatabase
-keep @androidx.room.Entity class *
-dontwarn androidx.room.paging.**

# ==================== 保留 Retrofit ====================

-keepattributes Signature, InnerClasses, EnclosingMethod
-keepattributes RuntimeVisibleAnnotations, RuntimeVisibleParameterAnnotations
-keepclassmembers,allowshrinking,allowobfuscation interface * {
    @retrofit2.http.* <methods>;
}

# ==================== 保留 Gson Models ====================

-keep class com.example.expensetracker.data.model.** { *; }
-keepclassmembers class com.example.expensetracker.data.model.** { *; }

# ==================== 保留 Hilt ====================

-keep class dagger.hilt.** { *; }
-keep class javax.inject.** { *; }
-keepclasseswithmembernames class * {
    @dagger.* <methods>;
}

# ==================== 移除 Log ====================

-assumenosideeffects class android.util.Log {
    public static *** d(...);
    public static *** v(...);
    public static *** i(...);
}
```

---

### 階段 4：合規性檢查（0.5-1 天）

#### 3.4.1 GDPR 合規檢查

**在 Claude Code 輸入**:
```
請檢查 GDPR 合規性：

檢查項目：
1. 使用者同意機制
2. 資料存取權限（Right to Access）
3. 資料刪除權限（Right to be Forgotten）
4. 隱私政策

請生成合規報告：`Docs/security/compliance/gdpr-compliance.md`
```

**預期輸出** (`gdpr-compliance.md`):
```markdown
# GDPR 合規性檢查報告

## 合規狀態總覽

| 要求 | 狀態 | 實施方式 |
|------|------|---------|
| 使用者同意 | ✅ 已實施 | 初次啟動時顯示同意對話框 |
| 資料存取 | ✅ 已實施 | 設定頁面「匯出我的資料」 |
| 資料刪除 | ✅ 已實施 | 設定頁面「刪除我的帳號」 |
| 資料可攜性 | ✅ 已實施 | 匯出為 JSON 格式 |
| 隱私政策 | ✅ 已實施 | 內嵌於 APP 和網站 |
| 資料加密 | ✅ 已實施 | SQLCipher + HTTPS |

## 實施細節

### 1. 使用者同意機制
- **實施**: 首次啟動時顯示同意對話框
- **儲存**: EncryptedSharedPreferences
- **撤回**: 設定頁面可撤回同意

### 2. 資料存取權限
- **功能**: 「匯出我的資料」
- **格式**: JSON
- **內容**: 所有交易記錄、類別、設定

### 3. 資料刪除權限
- **功能**: 「刪除我的帳號」
- **範圍**: 所有本地資料 + 後端資料
- **確認**: 二次確認對話框

## 建議改善

1. ✅ 已完成：實施資料加密
2. ✅ 已完成：HTTPS 通訊
3. 🟡 待完成：資料洩漏通知機制（72 小時內）
4. 🟡 待完成：定期資料保留政策檢查
```

---

### 階段 5：安全測試驗證（1 天）

#### 3.5.1 滲透測試

**在 Claude Code 輸入**:
```
請執行基本滲透測試：

測試項目：
1. SQL Injection（Room Database）
2. 本地資料外洩（Root 設備）
3. 網路攔截（Man-in-the-Middle）
4. 逆向工程（APK 反編譯）

請生成測試報告：`security-tests/penetration/penetration-test-report.md`
```

**手動測試步驟**:
```bash
# 1. APK 反編譯測試
apktool d app-release.apk -o decompiled/
jadx app-release.apk -d jadx-output/

# 檢查：程式碼是否已混淆？API Key 是否外洩？

# 2. 資料庫提取測試（需 Root 設備）
adb root
adb shell
cd /data/data/com.example.expensetracker/databases/
ls -la

# 檢查：資料庫檔案是否加密？

# 3. 網路攔截測試（使用 Charles Proxy）
# - 啟動 Charles Proxy
# - 配置 Android 裝置代理伺服器
# - 執行 APP，觀察網路流量

# 檢查：是否使用 HTTPS？Certificate Pinning 是否生效？
```

---

### 階段 6：最終安全報告（0.5 天）

**在 Claude Code 輸入**:
```
請生成最終安全評估報告：

內容：
1. 威脅模型總結
2. 漏洞清單與修復狀態
3. 合規性檢查結果
4. 測試結果彙總
5. 改善建議

輸出文檔：`Docs/security/assessment/final-security-report.md`
```

---

## 附錄：安全工具與命令

### 靜態分析工具

```bash
# Android Lint
./gradlew lint

# Detekt
./gradlew detekt

# OWASP Dependency-Check
dependency-check --project ExpenseTrackerApp --scan . --format HTML
```

### APK 安全檢查

```bash
# 反編譯 APK
apktool d app-release.apk

# 反編譯為 Java 程式碼
jadx app-release.apk -d output/

# 檢查混淆
grep -r "com.example.expensetracker" output/
```

### 資料庫安全檢查

```bash
# 提取資料庫（需 Root）
adb root
adb pull /data/data/com.example.expensetracker/databases/expense_tracker.db

# 嘗試開啟（應失敗，因已加密）
sqlite3 expense_tracker.db
```

---

## 🎯 安全時程表（總計 5-7 天）

| 階段 | 天數 | 主要工作 |
|------|-----|---------|
| 1. 安全需求分析 | 0.5 天 | 威脅模型、風險評估 |
| 2. 漏洞掃描 | 0.5 天 | 靜態分析、依賴掃描 |
| 3. 安全修復 | 2-3 天 | 加密、驗證、HTTPS、混淆 |
| 4. 合規性檢查 | 0.5-1 天 | GDPR、隱私政策 |
| 5. 安全測試 | 1 天 | 滲透測試、驗證 |
| 6. 最終報告 | 0.5 天 | 安全評估報告 |

---

## 📚 相關文檔

- [AISDLC_INIT.md](../../AISDLC_INIT.md)
- [Security SOP](../../scenarios/security/SOP.md)
- [OWASP Mobile Top 10](https://owasp.org/www-project-mobile-top-10/)
- [Android Security Best Practices](https://developer.android.com/topic/security/best-practices)

---

**版本**: 1.0
**作者**: AISDLC Framework Team
**最後更新**: 2025-12-16
