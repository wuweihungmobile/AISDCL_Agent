---
name: mobile-development
description: 行動端應用開發規劃與實作，嵌入 SDD SCG 閘門，確保 Mobile API Contract 凍結後才開始實作，App Store 發布對應 SCG-6
user-invocable: true
disable-model-invocation: false
argument-hint: "<platform: Android|iOS|macOS|cross-platform> <framework: ReactNative|Flutter|Kotlin|Swift>"
allowed-tools:
  - Read
  - Write
  - Grep
  - Glob
---

# Mobile Development Skill（SDD 原生）

行動端開發在 SDD 框架中有特殊考量：Mobile API Contract 的凍結時機、離線功能的 NFR 量化、App Store 發布作為 SCG-6 的一環。本 Skill 確保 Mobile 開發不繞過 SDD 閘門。

---

## 觸發方式

```bash
/mobile-development Android Kotlin
/mobile-development iOS Swift
/mobile-development cross-platform "React Native"
/mobile-development cross-platform Flutter
```

---

## 前置條件（SDD Spec-First）

| 閘門 | 說明 | 驗證方式 |
|------|------|---------|
| 🔷 SCG-1 通過 | SRD 包含 Mobile 架構說明 | SRD 有 Mobile 平台策略章節 |
| 🔷 SCG-3 通過 | Mobile API Contract 已凍結 | `docs/02_architecture/api/CONTRACT-{Module}-v{N}.yaml` |

> Mobile 特有：API Contract 必須包含 Mobile 端所需的所有端點（含離線同步 API）。

---

## 執行流程

### 階段 1：平台策略決策與 ADR

**決策框架**：

```
需要支援多平台？
├─ 是 → 團隊技術偏好？
│       ├─ JavaScript/TypeScript → React Native
│       ├─ Dart → Flutter
│       └─ Kotlin → Kotlin Multiplatform (KMP)
└─ 否 → 原生開發（Android: Kotlin / iOS: Swift）
```

**必須記錄 ADR**（呼叫 `/adr-generate`）：
- ADR：Mobile 平台策略選型（原生 vs 跨平台）
- ADR：離線策略（Local DB / Cache / 無離線）
- ADR：認證機制（Biometric / OAuth / API Key）

🔴 確認點：平台選型決策必須在 SCG-2 前確認，並產出 ADR。

---

### 階段 2：Mobile NFR 量化（SCG-0 必填）

Mobile 特有的非功能性需求，必須在 FRD 中量化（NFR-XXX 格式）：

```markdown
## Mobile 特有 NFR

### NFR-M001: 離線能力
- 離線功能範圍: {完全離線/弱網/僅線上}
- 本地快取策略: {SQLite/Realm/SharedPreferences}
- 資料同步策略: {最終一致性/即時同步}

### NFR-M002: 效能
- 冷啟動時間: < {N} 秒
- 畫面切換延遲: < {N} ms
- API 呼叫超時: {N} ms

### NFR-M003: 安全
- 認證方式: {Biometric/PIN/OAuth2}
- 敏感資料儲存: {Keychain/Keystore（非 SharedPreferences）}
- Root/Jailbreak 偵測: 是/否

### NFR-M004: App Store 發布
- 目標 Android API Level: {N}+
- 目標 iOS 版本: {N}+
- App Size 限制: < {N} MB（OTA 更新限制）
```

---

### 階段 3：架構設計（Mobile 專屬 C4）

補充 C4 Container 圖的 Mobile 部分：

```markdown
## Mobile C4 Container

### Mobile App Container
- **框架**: {React Native/Flutter/Kotlin/Swift}
- **本地儲存**: {SQLite/Realm/CoreData}
- **狀態管理**: {Redux/Riverpod/ViewModel}
- **API 通訊**: {Retrofit/Axios/Dio}

### 離線同步架構（若需要）
- 本地 DB Schema（對應 SRD 資料模型）
- 衝突解決策略（ADR-XXX）
- 同步觸發條件
```

---

### 階段 4：Mobile API Contract 確認（SCG-3）

確認後端 Contract 包含 Mobile 需要的所有端點：

- 分頁 API（支援 cursor-based pagination，避免 Mobile 大量載入）
- 離線同步 API（差異同步端點，若有離線需求）
- Push Notification 訂閱端點
- 版本兼容端點（Mobile 版本強制升級機制）

執行 `/spec-compliance-check docs/02_architecture/api/CONTRACT-*.yaml` 確認 Mobile 端點完整。

---

### 階段 5：實作階段

**必須在 SCG-3 通過後才開始實作**。

實作結構範例：

```
src/
├── api/          # Contract 對應的 API Client（自動從 OpenAPI 生成）
├── features/     # 功能模組（對應 FRD F-XXX）
├── core/         # 共用服務
└── offline/      # 離線同步邏輯（NFR-M001）
```

---

### 階段 6：App Store 發布（SCG-6 一環）🔴

App Store 發布在 SDD 中屬於 SCG-6 Release Gate 的一部分：

```markdown
## App Store Release Checklist（SCG-6 附加）

### App Store 準備
- [ ] App 版本號更新（對應 Release Notes）
- [ ] 隱私政策更新（若有新資料收集）
- [ ] App Store 截圖/說明更新

### 技術驗證
- [ ] 目標 API Level/iOS 版本符合要求
- [ ] App Size 在限制內（NFR-M004）
- [ ] 無 Critical 安全問題（/security-audit 通過）
- [ ] Contract Testing 通過（Mobile 端點全部通過）

### RTM 更新
- [ ] Mobile 功能的 AC 全部對應 TC（RTM 100%）
```

1. 執行 `/rtm-generate verify`
2. 執行 `/sdd-gate SCG-6`
3. 🔴 確認點：App Store 提交前等待 SCG-6 授權

---

## 強制產出（SDD 文件）

| 產出物 | 路徑 | 對應 SCG |
|--------|------|---------|
| Mobile 平台策略 ADR | `docs/02_architecture/adr/ADR-{NNN}-mobile-platform.md` | SCG-2 |
| Mobile NFR（補充在 FRD） | `docs/01_requirements/FRD-{System}.md` 的 NFR 章節 | SCG-0 |
| Mobile C4 Container（補充在 SRD） | `docs/02_architecture/SRD-{System}.md` | SCG-2 |

---

## 後置動作

```
/adr-generate "Mobile 平台策略"     # 記錄平台選型決策
/contract-generate openapi          # 確認 Mobile API Contract
/sdd-gate SCG-3                     # Contract 凍結後才開始 Mobile 實作
/release-management {version}       # App Store 發布（含 SCG-6）
```

🔷 **本 Skill 協助通過**：SCG-2（Mobile 架構凍結）、SCG-3（Mobile API Contract 凍結）、SCG-6（App Store 發布）

---

## 相關 Skill

- `/sd-architect` — 系統架構設計（Mobile C4 的上下文）
- `/contract-generate` — API Contract（Mobile 端點凍結）
- `/integration-api-client` — Mobile API Client 設計
- `/release-management` — App Store 發布流程

---

**基於**: AISDLC-SDD v0.21
**對應場景**: `scenarios/greenfield/SDD_GREENFIELD_ENHANCEMENT.md`
