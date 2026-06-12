---
name: mobile-development
description: 行動端應用開發規劃與實作，支援 Android/iOS/macOS 跨平台或原生開發
user-invocable: true
disable-model-invocation: false
argument-hint: "<platform: Android/iOS/macOS/cross-platform> <framework: React Native/Flutter/Kotlin/Swift>"
allowed-tools:
  - Read
  - Write
  - Grep
  - Glob
  - Bash
---

# Mobile Development 行動端開發

規劃並實作行動端應用，包含架構設計、API 對接、硬體整合（掃碼/NFC）、離線支援與跨平台策略。

---

## 觸發方式

```bash
/mobile-development Android Kotlin
/mobile-development iOS Swift
/mobile-development cross-platform "React Native"
/mobile-development cross-platform Flutter
```

---

## 執行流程

### 階段 1: 需求與平台分析 🔴

**必要資訊**:
- [ ] 目標平台（Android / iOS / macOS / 多平台）
- [ ] 技術框架選擇（原生 vs 跨平台）
- [ ] 既有後端 API 規格（REST / GraphQL）
- [ ] 硬體需求（相機掃碼、NFC、藍牙、GPS）
- [ ] 離線需求（完全離線 / 弱網路 / 僅線上）

**平台策略決策**:

```
需要支援多平台？
├─ 是 → 團隊技術偏好？
│       ├─ JavaScript/TypeScript → React Native
│       ├─ Dart → Flutter
│       └─ Kotlin → Kotlin Multiplatform (KMP)
└─ 否 → 單一平台
        ├─ Android → Kotlin + Jetpack Compose
        ├─ iOS → Swift + SwiftUI
        └─ macOS → Swift + SwiftUI / Catalyst
```

🔴 **確認點**: 平台策略、框架選擇、硬體需求是否確認

---

### 階段 2: 架構設計

**推薦架構模式**:

| 模式 | 適用情境 | 框架 |
|------|---------|------|
| **MVVM** | 大多數應用 | Android Jetpack / SwiftUI |
| **Clean Architecture** | 複雜業務邏輯 | 所有框架 |
| **MVI** | 單向資料流 | Kotlin + Compose |
| **Redux Pattern** | 狀態管理複雜 | React Native |

**分層架構**:
```
┌─────────────────────────────┐
│    Presentation Layer       │
│  (UI / ViewModel / State)   │
├─────────────────────────────┤
│    Domain Layer             │
│  (Use Cases / Entities)     │
├─────────────────────────────┤
│    Data Layer               │
│  (Repository / DataSource)  │
├──────────┬──────────────────┤
│ Local DB │  Remote API      │
│ (Room /  │  (Retrofit /     │
│  SQLite) │   URLSession)    │
└──────────┴──────────────────┘
```

**API 對接設計**:
```
行動端 ←→ API Gateway ←→ 後端服務
         │
         ├─ 認證: JWT / OAuth 2.0
         ├─ 通訊: REST + JSON
         ├─ 即時: WebSocket (通知/同步)
         └─ 檔案: Multipart Upload / S3 Presigned URL
```

---

### 階段 3: 硬體整合

**掃碼功能（Barcode/QR Code）**:

| 平台 | 推薦方案 | 備註 |
|------|---------|------|
| Android | ML Kit Barcode Scanning | Google 官方，免費 |
| iOS | AVFoundation / Vision | Apple 原生 API |
| Cross-platform | react-native-camera / mobile_scanner | 社群維護 |

**整合步驟**:
1. 權限宣告（相機、存儲）
2. 掃碼畫面 UI（對焦框、閃光燈控制）
3. 條碼解析（EAN-13 / Code 128 / QR Code）
4. 掃碼結果處理（查詢商品/觸發操作）
5. 批次掃碼模式（連續掃碼不中斷）

**Android 掃碼範例（ML Kit）**:
```kotlin
// build.gradle
implementation("com.google.mlkit:barcode-scanning:17.2.0")

// BarcodeAnalyzer.kt
class BarcodeAnalyzer(
    private val onBarcodeDetected: (String) -> Unit
) : ImageAnalysis.Analyzer {
    private val scanner = BarcodeScanning.getClient(
        BarcodeScannerOptions.Builder()
            .setBarcodeFormats(
                Barcode.FORMAT_EAN_13,
                Barcode.FORMAT_CODE_128,
                Barcode.FORMAT_QR_CODE
            )
            .build()
    )

    override fun analyze(imageProxy: ImageProxy) {
        val inputImage = InputImage.fromMediaImage(
            imageProxy.image!!, imageProxy.imageInfo.rotationDegrees
        )
        scanner.process(inputImage)
            .addOnSuccessListener { barcodes ->
                barcodes.firstOrNull()?.rawValue?.let { onBarcodeDetected(it) }
            }
            .addOnCompleteListener { imageProxy.close() }
    }
}
```

**其他硬體**:
- **NFC**: 讀取 RFID 標籤（Android NfcAdapter / iOS Core NFC）
- **藍牙**: 連接藍牙印表機/秤（BLE API）
- **GPS**: 配送路線追蹤（Fused Location / Core Location）

---

### 階段 4: 離線支援

**離線策略選擇**:

| 策略 | 說明 | 適用情境 |
|------|------|---------|
| **Cache-First** | 優先使用本地快取 | 商品目錄、參數檔 |
| **Network-First** | 優先請求網路 | 庫存即時查詢 |
| **Offline-First** | 本地操作→排隊同步 | 倉庫掃碼入出庫 |
| **Write-Through** | 同時寫本地與遠端 | 訂單建立（網路穩定時） |

**離線同步架構**:
```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  操作佇列    │ ──→ │  同步引擎     │ ──→ │  遠端 API   │
│ (Room Queue) │     │ (WorkManager) │     │ (REST API)  │
└─────────────┘     └──────────────┘     └─────────────┘
       ↑                    │
       │                    ↓
┌─────────────┐     ┌──────────────┐
│  UI 操作     │     │  衝突解決     │
│ (掃碼/下單)  │     │ (Last-Write   │
└─────────────┘     │   -Wins /     │
                    │  Server-Wins) │
                    └──────────────┘
```

**衝突解決策略**:
- **Server-Wins**: 伺服器資料優先（適合庫存數量）
- **Last-Write-Wins**: 最後寫入優先（適合備註欄位）
- **Manual Merge**: 人工介入（適合訂單修改）

---

### 階段 5: 測試與部署

**測試策略**:
- [ ] 單元測試（ViewModel / UseCase / Repository）
- [ ] UI 測試（Espresso / XCTest）
- [ ] 整合測試（API Mock + 本地 DB）
- [ ] 掃碼功能測試（實機 + 多條碼格式）
- [ ] 離線同步測試（斷網→操作→恢復→同步）
- [ ] 效能測試（啟動時間 < 2s、掃碼延遲 < 500ms）
- [ ] 裝置相容性（不同螢幕尺寸、OS 版本）

**部署管道**:
```
Git Push → CI Build → Unit Test → UI Test
    → Sign APK/IPA → Upload to Store
    → Internal Testing → Staged Rollout → Full Release
```

**推薦 CI/CD 工具**:
- **Android**: GitHub Actions + Gradle + Firebase App Distribution
- **iOS**: Xcode Cloud / Fastlane + TestFlight
- **Cross-platform**: Codemagic / Bitrise / EAS Build

---

## 常見陷阱

| 問題 | 解決方案 |
|------|---------|
| 掃碼在低光環境失敗 | 啟用閃光燈控制 + 調整對比度 |
| 離線操作後同步衝突 | 預設 Server-Wins + 衝突佇列通知用戶 |
| Android 碎片化 | 設定 minSdk 26+ + 多裝置測試矩陣 |
| iOS 審核被拒 | 遵守 HIG + 提前準備審核說明 |
| API 回應過慢 | 分頁載入 + 本地快取 + 骨架屏 |
| 記憶體溢位（圖片） | 使用 Coil/Glide (Android) / SDWebImage (iOS) |
| 電量消耗過高 | 批次同步 + WorkManager 約束條件 |

---

## 產出物

| 產出物 | 路徑 |
|--------|------|
| 行動端架構設計 | `docs/02_architecture/Mobile_Architecture.md` |
| API 對接規格 | `docs/02_architecture/Mobile_API_Contract.md` |
| 硬體整合規格 | `docs/02_architecture/Hardware_Integration.md` |
| 離線同步設計 | `docs/02_architecture/Offline_Sync_Design.md` |
| 裝置相容性矩陣 | `docs/03_testing/Device_Compatibility_Matrix.md` |
| 行動端測試報告 | `docs/03_testing/Mobile_Test_Report.md` |

---

## 相關 Skill

- `/sd-architect` - 系統架構設計（含行動端分層）
- `/integration-api-client` - API 客戶端建立
- `/testing-strategy` - 測試策略（含行動端測試）
- `/devops-github-actions` - CI/CD Pipeline 設定
- `/database-migration` - 資料庫遷移（離線 DB 相關）

---

## 相關檔案

- SOP 參考: `scenarios/migration/SOP.md`（階段 6: 新平台開發）
- QuickRef: `scenarios/migration/SOP_QuickRef.md`

**基於**: AISDLC v0.09 Migration 情境
