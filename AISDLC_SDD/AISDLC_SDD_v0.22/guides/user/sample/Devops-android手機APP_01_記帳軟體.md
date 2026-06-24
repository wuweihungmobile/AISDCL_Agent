# AISDLC DevOps/CI/CD 實戰範例：Android 記帳 APP

**版本**: v0.01
**最後更新**: 2025-12-16
**情境**: DevOps/CI/CD
**平台**: Android + Python Backend
**技術棧**: Kotlin, Jetpack Compose, MVVM, Hilt, Python/FastAPI, GitHub Actions


> **SDD v0.01 使用者提示**：本指南基於 AISDLC-SDD v0.01。使用 AISDLC-SDD v0.01 時，請同時參考對應場景的 SDD Enhancement 文件（`scenarios/{scenario}/SDD_{SCENARIO}_ENHANCEMENT.md`），並確認所有 SCG 閘門步驟已整合到您的工作流程中。

---
---

## 📋 範例概述

本文檔展示如何使用 **AISDLC-SDD v0.01** 在 **Cursor AI** 環境中，透過 **Claude Code** 為 Android 記帳軟體建立完整的 DevOps/CI/CD 流程。

**技術棧**:
- **前端**: Kotlin + Jetpack Compose + MVVM + Hilt
- **後端**: Python + FastAPI + PostgreSQL
- **CI/CD**: GitHub Actions
- **部署**: Google Play Store (Android) + Google Cloud Run (Backend)
- **測試**: JUnit, Espresso, pytest
- **監控**: Firebase Crashlytics, Sentry

---

## 🎯 第一部分：環境設定

### 步驟 1.1: 設定 Cursor AI 專案路徑

**1.1.1 創建專案目錄**

```bash
# 創建 Monorepo 結構
mkdir -p ~/projects/MoneyTrackerDevOps
cd ~/projects/MoneyTrackerDevOps

# 創建前後端目錄
mkdir -p android backend
mkdir -p .github/workflows
mkdir -p scripts
mkdir -p docs/devops

# 創建 Android 專案
cd android
# 使用 Android Studio 創建專案後，移動檔案至此目錄
```

**1.1.2 在 Cursor 開啟專案**

```bash
cursor ~/projects/MoneyTrackerDevOps
```

---

### 步驟 1.2: 安裝設定 AISDLC-SDD v0.01

**1.2.1 建立符號連結**

```bash
cd ~/projects/MoneyTrackerDevOps
ln -s ~/projects/AISDLC_ALL/AISDLC_v0.09 ./AISDLC
```

**1.2.2 創建 CLAUDE.md**

```bash
cat > CLAUDE.md << 'EOF'
# MoneyTracker DevOps 專案指引

**專案名稱**: MoneyTracker (記帳軟體 CI/CD)
**AISDLC 版本**: v0.01
**開發情境**: DevOps/CI/CD

## 專案架構

- **Android**: Kotlin + Jetpack Compose + MVVM + Hilt
- **Backend**: Python + FastAPI + PostgreSQL
- **CI/CD**: GitHub Actions
- **部署**: Google Play + Google Cloud Run

## AISDLC 框架路徑

- **框架位置**: `./AISDLC/`
- **DevOps SOP**: `AISDLC/scenarios/devops/SOP.md`
- **文檔輸出**: `./docs/`

## DevOps 目標

1. 自動化測試 (單元測試、UI 測試、整合測試)
2. 自動化建置 (APK/AAB 簽章)
3. 自動化部署 (Internal Testing → Beta → Production)
4. 程式碼品質檢查 (Lint, Detekt, SonarQube)
5. 監控與告警 (Crashlytics, Sentry)

## 重要提醒

- 執行前先讀取 `AISDLC/AISDLC_INIT.md`
- 使用 DevOps Scenario: `AISDLC/scenarios/devops/SOP.md`
EOF
```

**1.2.3 創建基礎目錄結構**

```bash
mkdir -p docs/{devops,deployment,monitoring}
mkdir -p scripts/{build,deploy,test}
mkdir -p .github/workflows
```

---

## 🚀 第二部分：使用 Claude Code 開發 CI/CD

### 步驟 2.1: 啟動 Claude Code

```bash
claude code
```

---

### 步驟 2.2: 第一階段 - CI/CD 需求分析

**2.2.1 初始化並載入 DevOps Workflow**

💬 **您對 Claude 說**：
```
我要為 Android 記帳 APP (MoneyTracker) 建立完整的 CI/CD 流程。

技術棧:
- Android: Kotlin + Jetpack Compose + MVVM + Hilt
- Backend: Python + FastAPI
- 版本控制: GitHub
- 部署: Google Play Store + Google Cloud Run

請執行:
1. 讀取 AISDLC/AISDLC_INIT.md
2. 讀取 AISDLC/scenarios/devops/SOP.md
3. 分析 CI/CD 需求並建議流程
```

🤖 **Claude 回應**：
```
已讀取 AISDLC_INIT.md 和 DevOps SOP。

建議 CI/CD 流程:

【Android CI/CD Pipeline】
1. ✅ Code Quality Check (Lint, Detekt)
2. ✅ Unit Tests (JUnit)
3. ✅ Build Debug APK
4. ✅ UI Tests (Espresso)
5. ✅ Build Release AAB (簽章)
6. ✅ Upload to Google Play (Internal Testing)
7. ✅ Promote to Beta/Production

【Backend CI/CD Pipeline】
1. ✅ Code Quality (Black, Flake8, mypy)
2. ✅ Unit Tests (pytest)
3. ✅ Build Docker Image
4. ✅ Deploy to Cloud Run (Staging)
5. ✅ Integration Tests
6. ✅ Deploy to Production

請確認需求並提供補充資訊。
```

---

**2.2.2 提供 DevOps 需求**

💬 **您對 Claude 說**：
```
請使用 AISDLC DevOps workflow 分析以下需求:

## CI/CD 需求

### Android Pipeline
1. **觸發條件**
   - Push to main → 完整 CI 檢查
   - Pull Request → 程式碼品質 + 單元測試
   - Tag (v*.*.*) → 發布到 Google Play

2. **建置階段**
   - Kotlin 程式碼檢查 (Detekt)
   - 單元測試 (JUnit) + 覆蓋率報告 (JaCoCo)
   - UI 測試 (Espresso)
   - APK/AAB 簽章 (使用 GitHub Secrets)

3. **部署階段**
   - Internal Testing Track (自動)
   - Beta Track (手動批准)
   - Production Track (手動批准)

4. **通知**
   - 建置失敗 → Slack 通知
   - 部署成功 → Slack + Email

### Backend Pipeline
1. **觸發條件**
   - Push to main → 部署到 Staging
   - Tag (v*.*.*) → 部署到 Production

2. **建置階段**
   - Python 程式碼檢查 (Black, Flake8)
   - 單元測試 (pytest) + 覆蓋率
   - Docker Image 建置

3. **部署階段**
   - Cloud Run Staging (自動)
   - Cloud Run Production (手動批准)

### 監控需求
- Firebase Crashlytics (Android 崩潰追蹤)
- Sentry (Backend 錯誤追蹤)
- Google Analytics (使用者行為)

請載入 DevOps Agent 並生成完整的 CI/CD 配置。
```

🤖 **Claude 執行**：
```
步驟 1: 讀取 AISDLC/scenarios/devops/SOP.md
步驟 2: 載入 DevOps Agent
  - AISDLC/agent/specialized/devops-engineer.yaml

步驟 3: 🔴 DevOps 配置確認

【關鍵決策問題】
Q1: Google Play 簽章金鑰 - 使用 App Signing by Google Play？
Q2: Android 測試 - 需要在真實裝置上測試嗎？(Firebase Test Lab)
Q3: 版本號管理 - 自動遞增還是手動設定？
Q4: 回滾策略 - Production 發布後發現問題如何處理？
Q5: 環境變數 - API Keys 如何安全管理？(GitHub Secrets)
Q6: 建置快取 - 使用 Gradle Build Cache 嗎？

請回答以上問題。
```

---

**2.2.3 回答 DevOps 問題**

💬 **您對 Claude 說**：
```
A1: 是，使用 Google Play App Signing
A2: 初期使用 Emulator，重要版本使用 Firebase Test Lab
A3: 自動遞增 (基於 Git commit count)
A4: 使用 Google Play 的 Staged Rollout (5% → 20% → 50% → 100%)
A5: 全部使用 GitHub Secrets
A6: 是，啟用 Gradle Build Cache 加速建置
```

🤖 **Claude 執行**：
```
收到！生成 CI/CD 配置...

【生成中...】

✅ 完成！已生成:

1. .github/workflows/android-ci.yml          # Android CI Pipeline
2. .github/workflows/android-release.yml     # Android Release Pipeline
3. .github/workflows/backend-ci.yml          # Backend CI Pipeline
4. .github/workflows/backend-deploy.yml      # Backend Deploy Pipeline
5. scripts/build/build-android.sh            # Android 建置腳本
6. scripts/deploy/deploy-playstore.sh        # Google Play 部署腳本
7. scripts/deploy/deploy-cloudrun.sh         # Cloud Run 部署腳本
8. docs/devops/CICD_Architecture.md          # CI/CD 架構文檔
9. docs/devops/Deployment_Guide.md           # 部署指南
10. docs/devops/Secrets_Management.md        # 密鑰管理指南

請檢閱生成的配置檔案。
```

---

### 步驟 2.3: 第二階段 - GitHub Actions 配置

**2.3.1 生成 Android CI Pipeline**

💬 **您對 Claude 說**：
```
請詳細展示 .github/workflows/android-ci.yml 的完整內容，
包含所有階段的配置。
```

🤖 **Claude 回應**：
```
✅ android-ci.yml 完整配置:

name: Android CI

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  lint:
    name: Code Quality Check
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up JDK 17
        uses: actions/setup-java@v4
        with:
          distribution: 'temurin'
          java-version: '17'

      - name: Setup Gradle
        uses: gradle/gradle-build-action@v2
        with:
          cache-read-only: ${{ github.ref != 'refs/heads/main' }}

      - name: Run Detekt
        run: ./gradlew detekt

      - name: Run Android Lint
        run: ./gradlew lint

      - name: Upload Lint Reports
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: lint-reports
          path: android/app/build/reports/

  unit-test:
    name: Unit Tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up JDK 17
        uses: actions/setup-java@v4
        with:
          distribution: 'temurin'
          java-version: '17'

      - name: Setup Gradle
        uses: gradle/gradle-build-action@v2

      - name: Run Unit Tests
        run: ./gradlew test

      - name: Generate Coverage Report
        run: ./gradlew jacocoTestReport

      - name: Upload Coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          files: android/app/build/reports/jacoco/test/jacocoTestReport.xml

      - name: Upload Test Reports
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: test-reports
          path: android/app/build/reports/tests/

  ui-test:
    name: UI Tests
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up JDK 17
        uses: actions/setup-java@v4
        with:
          distribution: 'temurin'
          java-version: '17'

      - name: Setup Gradle
        uses: gradle/gradle-build-action@v2

      - name: Run Instrumented Tests
        uses: reactivecircus/android-emulator-runner@v2
        with:
          api-level: 34
          arch: x86_64
          target: google_apis
          script: ./gradlew connectedAndroidTest

      - name: Upload UI Test Reports
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: ui-test-reports
          path: android/app/build/reports/androidTests/

  build:
    name: Build Debug APK
    runs-on: ubuntu-latest
    needs: [lint, unit-test]
    steps:
      - uses: actions/checkout@v4

      - name: Set up JDK 17
        uses: actions/setup-java@v4
        with:
          distribution: 'temurin'
          java-version: '17'

      - name: Setup Gradle
        uses: gradle/gradle-build-action@v2

      - name: Build Debug APK
        run: ./gradlew assembleDebug

      - name: Upload APK
        uses: actions/upload-artifact@v4
        with:
          name: debug-apk
          path: android/app/build/outputs/apk/debug/*.apk

已生成！此配置包含:
- ✅ 程式碼品質檢查 (Detekt, Lint)
- ✅ 單元測試 + 覆蓋率報告 (JaCoCo)
- ✅ UI 測試 (Espresso on Emulator)
- ✅ Debug APK 建置
- ✅ Gradle Build Cache
- ✅ 測試報告上傳

請檢閱配置。
```

---

**2.3.2 生成 Android Release Pipeline**

💬 **您對 Claude 說**：
```
請生成 android-release.yml，包含:
1. AAB 簽章
2. 上傳到 Google Play (Internal Testing)
3. 版本號自動遞增
```

🤖 **Claude 執行**：
```
✅ android-release.yml 完整配置:

name: Android Release

on:
  push:
    tags:
      - 'v*.*.*'

jobs:
  release:
    name: Build and Release
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0  # 需要完整歷史以計算版本號

      - name: Set up JDK 17
        uses: actions/setup-java@v4
        with:
          distribution: 'temurin'
          java-version: '17'

      - name: Calculate Version Code
        id: version
        run: |
          VERSION_CODE=$(git rev-list --count HEAD)
          VERSION_NAME=${GITHUB_REF#refs/tags/v}
          echo "code=$VERSION_CODE" >> $GITHUB_OUTPUT
          echo "name=$VERSION_NAME" >> $GITHUB_OUTPUT

      - name: Decode Keystore
        run: |
          echo "${{ secrets.KEYSTORE_BASE64 }}" | base64 -d > android/keystore.jks

      - name: Build Release AAB
        run: ./gradlew bundleRelease
        env:
          KEYSTORE_PASSWORD: ${{ secrets.KEYSTORE_PASSWORD }}
          KEY_ALIAS: ${{ secrets.KEY_ALIAS }}
          KEY_PASSWORD: ${{ secrets.KEY_PASSWORD }}
          VERSION_CODE: ${{ steps.version.outputs.code }}
          VERSION_NAME: ${{ steps.version.outputs.name }}

      - name: Sign AAB
        run: |
          jarsigner -verbose -sigalg SHA256withRSA -digestalg SHA-256 \
            -keystore android/keystore.jks \
            -storepass "${{ secrets.KEYSTORE_PASSWORD }}" \
            -keypass "${{ secrets.KEY_PASSWORD }}" \
            android/app/build/outputs/bundle/release/app-release.aab \
            ${{ secrets.KEY_ALIAS }}

      - name: Upload to Google Play (Internal Testing)
        uses: r0adkll/upload-google-play@v1
        with:
          serviceAccountJsonPlainText: ${{ secrets.GOOGLE_PLAY_SERVICE_ACCOUNT }}
          packageName: com.example.moneytracker
          releaseFiles: android/app/build/outputs/bundle/release/app-release.aab
          track: internal
          status: completed
          whatsNewDirectory: android/whatsnew/

      - name: Create GitHub Release
        uses: softprops/action-gh-release@v1
        with:
          files: android/app/build/outputs/bundle/release/app-release.aab
          body: |
            ## 版本 ${{ steps.version.outputs.name }}

            版本號: ${{ steps.version.outputs.code }}

            已自動上傳至 Google Play Internal Testing Track

      - name: Notify Slack
        if: success()
        uses: 8398a7/action-slack@v3
        with:
          status: success
          text: '✅ Android Release ${{ steps.version.outputs.name }} 已成功發布至 Internal Testing'
          webhook_url: ${{ secrets.SLACK_WEBHOOK }}

      - name: Notify on Failure
        if: failure()
        uses: 8398a7/action-slack@v3
        with:
          status: failure
          text: '❌ Android Release 建置失敗'
          webhook_url: ${{ secrets.SLACK_WEBHOOK }}

已生成！包含:
- ✅ 版本號自動計算 (基於 Git commits)
- ✅ Keystore 解碼 (從 GitHub Secrets)
- ✅ AAB 簽章
- ✅ 自動上傳 Google Play Internal Testing
- ✅ GitHub Release 創建
- ✅ Slack 通知

請檢閱配置。
```

---

**2.3.3 生成 Backend CI/CD Pipeline**

💬 **您對 Claude 說**：
```
請生成 backend-ci.yml 和 backend-deploy.yml。
```

🤖 **Claude 執行**：
```
✅ 已生成兩個檔案:

【backend-ci.yml】- 程式碼品質與測試
【backend-deploy.yml】- Docker + Cloud Run 部署

包含:
- ✅ Python 程式碼格式化 (Black)
- ✅ Linting (Flake8, mypy)
- ✅ 單元測試 (pytest) + 覆蓋率
- ✅ Docker Image 建置
- ✅ Cloud Run 部署 (Staging/Production)
- ✅ 整合測試 (部署後)

詳細配置已生成至對應檔案。
```

---

### 步驟 2.4: 第三階段 - 監控與告警設定

**2.4.1 配置 Firebase Crashlytics**

💬 **您對 Claude 說**：
```
請協助整合 Firebase Crashlytics:

1. 修改 Android build.gradle 加入 Crashlytics
2. 生成初始化程式碼
3. 生成崩潰報告檢視指南
```

🤖 **Claude 執行**：
```
✅ 完成！已生成:

1. android/app/build.gradle.kts (已加入 Crashlytics)
2. android/app/src/main/java/com/example/moneytracker/MoneyTrackerApplication.kt
   - Crashlytics 初始化
   - 自訂錯誤報告
3. docs/monitoring/Crashlytics_Integration_Guide.md
   - 設定步驟
   - 自訂 Key-Value 追蹤
   - 崩潰報告查看流程

關鍵程式碼:

// MoneyTrackerApplication.kt
class MoneyTrackerApplication : Application() {
    override fun onCreate() {
        super.onCreate()

        // Firebase Crashlytics
        FirebaseCrashlytics.getInstance().apply {
            setCrashlyticsCollectionEnabled(!BuildConfig.DEBUG)
            setCustomKey("user_id", getCurrentUserId())
            setCustomKey("app_version", BuildConfig.VERSION_NAME)
        }
    }
}

// 記錄非致命錯誤
fun logError(error: Throwable) {
    FirebaseCrashlytics.getInstance().recordException(error)
}

請檢閱整合指南。
```

---

**2.4.2 配置 Sentry (Backend)**

💬 **您對 Claude 說**：
```
請整合 Sentry 至 Python Backend:

1. 修改 backend/main.py
2. 生成錯誤追蹤配置
3. 生成告警規則建議
```

🤖 **Claude 執行**：
```
✅ 完成！已生成:

1. backend/requirements.txt (已加入 sentry-sdk)
2. backend/main.py (Sentry 初始化)
3. docs/monitoring/Sentry_Integration_Guide.md

關鍵程式碼:

# main.py
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    environment=os.getenv("ENV", "development"),
    traces_sample_rate=1.0 if os.getenv("ENV") == "development" else 0.1,
    integrations=[FastApiIntegration()],
)

# 自訂錯誤追蹤
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    sentry_sdk.capture_exception(exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

告警規則建議:
- Error Rate > 1% → Slack 通知
- Response Time > 2s → Email 通知
- 5xx Errors > 10/min → PagerDuty 告警

請檢閱整合指南。
```

---

### 步驟 2.5: 第四階段 - 部署自動化

**2.5.1 生成部署腳本**

💬 **您對 Claude 說**：
```
請生成完整的部署腳本:

1. scripts/deploy/deploy-playstore.sh (Google Play)
2. scripts/deploy/deploy-cloudrun.sh (Backend)
3. 包含環境變數檢查、回滾機制
```

🤖 **Claude 執行**：
```
✅ 完成！已生成 3 個腳本:

【deploy-playstore.sh】
- 支援多 Track 部署 (internal/beta/production)
- 自動產生 Release Notes
- 階段式發布 (Staged Rollout)
- 回滾機制

【deploy-cloudrun.sh】
- 支援多環境 (staging/production)
- 零停機部署 (Traffic Splitting)
- Health Check 驗證
- 自動回滾

【rollback-playstore.sh】
- 回滾到前一版本
- 保留使用者資料

腳本包含完整錯誤處理與日誌記錄。

範例使用:
# 部署至 Google Play Beta
./scripts/deploy/deploy-playstore.sh beta v1.2.0

# 部署 Backend 至 Production
./scripts/deploy/deploy-cloudrun.sh production

# 回滾 Google Play
./scripts/deploy/rollback-playstore.sh production

請檢閱腳本。
```

---

### 步驟 2.6: 第五階段 - 文檔生成

**2.6.1 生成完整 DevOps 文檔**

💬 **您對 Claude 說**：
```
請生成完整的 DevOps 文檔:

1. CI/CD 架構圖
2. 部署流程圖
3. 環境變數清單
4. 故障排除指南
5. Runbook (標準操作程序)
```

🤖 **Claude 執行**：
```
✅ 完成！已生成:

1. docs/devops/CICD_Architecture.md
   - CI/CD Pipeline 架構圖 (Mermaid)
   - Android Pipeline 流程
   - Backend Pipeline 流程
   - 觸發條件說明

2. docs/devops/Deployment_Guide.md
   - 部署前檢查清單
   - 各環境部署步驟
   - 版本管理策略
   - 回滾程序

3. docs/devops/Secrets_Management.md
   - GitHub Secrets 清單 (19 個)
   - Google Cloud Secret Manager 整合
   - Keystore 管理
   - API Keys 輪替策略

4. docs/devops/Troubleshooting_Guide.md
   - 常見建置失敗問題
   - 部署失敗排查
   - 測試失敗處理
   - 監控告警處理

5. docs/devops/Runbook.md
   - 發布新版本 SOP
   - 緊急修復 (Hotfix) SOP
   - 生產環境事故處理
   - 效能問題排查

所有文檔已包含詳細步驟與範例。

請檢閱文檔。
```

---

## 📊 第三部分：完整 DevOps 流程總結

### 3.1 GitHub Secrets 清單

需在 GitHub Repository Settings → Secrets 設定:

**Android Secrets**
```
KEYSTORE_BASE64            # Keystore Base64 編碼
KEYSTORE_PASSWORD          # Keystore 密碼
KEY_ALIAS                  # 簽章別名
KEY_PASSWORD               # 簽章密碼
GOOGLE_PLAY_SERVICE_ACCOUNT # Google Play API JSON
```

**Backend Secrets**
```
GCP_PROJECT_ID             # Google Cloud 專案 ID
GCP_SERVICE_ACCOUNT_KEY    # GCP Service Account JSON
DATABASE_URL               # PostgreSQL 連線字串
JWT_SECRET_KEY             # JWT 密鑰
SENTRY_DSN                 # Sentry DSN
```

**通知 Secrets**
```
SLACK_WEBHOOK              # Slack Webhook URL
```

---

### 3.2 CI/CD 流程圖

```
【Android Release Flow】
Tag v1.0.0 → GitHub Actions
  ↓
[1] Code Quality (Detekt, Lint)
  ↓
[2] Unit Tests (JUnit + JaCoCo)
  ↓
[3] Build AAB + Sign
  ↓
[4] Upload to Google Play (Internal)
  ↓
[5] Manual Approval → Beta
  ↓
[6] Manual Approval → Production (Staged Rollout)
  ↓
[7] Monitor Crashlytics

【Backend Deploy Flow】
Push to main → GitHub Actions
  ↓
[1] Code Quality (Black, Flake8)
  ↓
[2] Unit Tests (pytest)
  ↓
[3] Build Docker Image
  ↓
[4] Push to Google Container Registry
  ↓
[5] Deploy to Cloud Run (Staging)
  ↓
[6] Integration Tests
  ↓
[7] Manual Approval → Production
  ↓
[8] Monitor Sentry
```

---

### 3.3 關鍵命令範例

**本地測試 CI Pipeline**
```bash
# 執行 Lint
./gradlew detekt lint

# 執行單元測試 + 覆蓋率
./gradlew test jacocoTestReport

# 建置 Debug APK
./gradlew assembleDebug

# 執行 UI 測試 (需 Emulator)
./gradlew connectedAndroidTest
```

**手動部署**
```bash
# 建置 Release AAB
./gradlew bundleRelease \
  -Pandroid.injected.signing.store.file=keystore.jks \
  -Pandroid.injected.signing.store.password=$KEYSTORE_PASSWORD \
  -Pandroid.injected.signing.key.alias=$KEY_ALIAS \
  -Pandroid.injected.signing.key.password=$KEY_PASSWORD

# 部署 Backend 至 Cloud Run
gcloud run deploy moneytracker-backend \
  --image gcr.io/PROJECT_ID/moneytracker-backend:latest \
  --platform managed \
  --region asia-east1 \
  --allow-unauthenticated
```

---

## 🎓 第四部分：進階 DevOps 技巧

### 4.1 Firebase Test Lab 整合

💬 **命令範例**：
```
請整合 Firebase Test Lab 至 CI Pipeline:

1. 在真實裝置上執行 UI 測試
2. 測試矩陣: Android 9-14, 5 種裝置
3. 生成測試報告並上傳至 GitHub Artifacts
```

---

### 4.2 SonarQube 程式碼品質分析

💬 **命令範例**：
```
請整合 SonarQube:

1. 修改 GitHub Actions 加入 SonarQube 掃描
2. 設定品質門檻 (Coverage > 80%, Bugs = 0)
3. Pull Request 自動註解程式碼問題
```

---

### 4.3 A/B Testing 部署策略

💬 **命令範例**：
```
請設計 A/B Testing 部署策略:

1. 使用 Firebase Remote Config
2. 功能開關 (Feature Flags)
3. 段階式發布 (5% → 25% → 50% → 100%)
```

---

### 4.4 自動化效能測試

💬 **命令範例**：
```
請整合自動化效能測試:

1. Android Profiler (啟動時間、記憶體)
2. Backend 負載測試 (Locust)
3. 效能退化檢測 (與上一版本比較)
```

---

## 📁 第五部分：最終專案結構

```
MoneyTrackerDevOps/
├── AISDLC/                           # 符號連結
├── CLAUDE.md
│
├── .github/
│   └── workflows/
│       ├── android-ci.yml            # Android CI
│       ├── android-release.yml       # Android Release
│       ├── backend-ci.yml            # Backend CI
│       └── backend-deploy.yml        # Backend Deploy
│
├── android/                          # Android 專案
│   ├── app/
│   │   ├── build.gradle.kts
│   │   └── src/
│   ├── keystore.jks.example
│   └── whatsnew/                     # Release Notes
│
├── backend/                          # Python Backend
│   ├── app/
│   ├── tests/
│   ├── Dockerfile
│   └── requirements.txt
│
├── scripts/
│   ├── build/
│   │   └── build-android.sh
│   ├── deploy/
│   │   ├── deploy-playstore.sh
│   │   ├── deploy-cloudrun.sh
│   │   └── rollback-playstore.sh
│   └── test/
│       └── run-integration-tests.sh
│
└── docs/
    ├── devops/
    │   ├── CICD_Architecture.md
    │   ├── Deployment_Guide.md
    │   ├── Secrets_Management.md
    │   ├── Troubleshooting_Guide.md
    │   └── Runbook.md
    └── monitoring/
        ├── Crashlytics_Integration_Guide.md
        └── Sentry_Integration_Guide.md
```

---

## 🔍 常見問題 (FAQ)

### Q1: GitHub Actions 建置時間過長？

**A**: 優化策略
```yaml
# 啟用 Gradle Build Cache
- uses: gradle/gradle-build-action@v2
  with:
    cache-read-only: false

# 平行執行測試
./gradlew test --parallel --max-workers=4

# 只在必要時執行 UI 測試
if: github.event_name == 'push' && github.ref == 'refs/heads/main'
```

---

### Q2: Google Play 簽章金鑰如何安全保存？

**A**:
1. 將 keystore.jks 轉為 Base64
```bash
base64 -i keystore.jks | pbcopy
```
2. 儲存至 GitHub Secrets (KEYSTORE_BASE64)
3. CI 時解碼
```bash
echo "${{ secrets.KEYSTORE_BASE64 }}" | base64 -d > keystore.jks
```

---

### Q3: 如何實現自動版本號遞增？

**A**: 使用 Git commit count
```bash
VERSION_CODE=$(git rev-list --count HEAD)
VERSION_NAME=${GITHUB_REF#refs/tags/v}
```

在 build.gradle.kts:
```kotlin
versionCode = System.getenv("VERSION_CODE")?.toInt() ?: 1
versionName = System.getenv("VERSION_NAME") ?: "1.0.0"
```

---

### Q4: 如何處理多環境配置？

**A**: 使用 Build Variants
```kotlin
// build.gradle.kts
android {
    buildTypes {
        debug {
            buildConfigField("String", "API_URL", "\"https://staging-api.com\"")
        }
        release {
            buildConfigField("String", "API_URL", "\"https://api.com\"")
        }
    }
}
```

---

## ✅ 結論

透過本範例，您已學會:

1. ✅ 設定完整的 Android CI/CD Pipeline (GitHub Actions)
2. ✅ 自動化測試 (Unit, UI, Integration)
3. ✅ 自動化部署 (Google Play + Cloud Run)
4. ✅ 監控與告警 (Crashlytics + Sentry)
5. ✅ 程式碼品質管理 (Lint, Detekt, Coverage)
6. ✅ 安全的密鑰管理 (GitHub Secrets)

**核心價值**: AISDLC DevOps SOP 確保每個 CI/CD 階段都有明確定義、可重複執行、並包含完整的監控與回滾機制。

**下一步建議**:
1. 實際執行本範例配置
2. 閱讀 [DevOps SOP](../../scenarios/devops/SOP.md)
3. 探索進階主題 (Firebase Test Lab, SonarQube, A/B Testing)

---

**文檔版本**: v1.0
**適用 AISDLC 版本**: v0.01
**最後更新**: 2025-12-16
**作者**: AISDLC 框架維護團隊
