---
name: integration-firebase
description: Firebase 整合，ADR 記錄 BaaS 選型，Security Rules Spec 設計先行，RTM 追蹤
user-invocable: true
disable-model-invocation: false
argument-hint: "<services: auth|firestore|storage|functions|all> [framework: nextjs|react|flutter]"
allowed-tools:
  - Read
  - Write
  - Grep
  - Glob
---

# Integration Firebase Skill（SDD 原生）

Firebase 整合在 SDD 中必須設計先行：BaaS 選型需有 ADR，Security Rules 必須在實作前以規格形式凍結（SDD 規則：規則先於資料結構），Firestore 資料結構對應 FRD 資料模型。

---

## 觸發方式

```bash
/integration-firebase auth nextjs
/integration-firebase firestore storage
/integration-firebase all flutter
```

---

## 前置條件（SDD Spec-First）

| 閘門 | 說明 | 驗證方式 |
|------|------|---------|
| 🔷 SCG-2 通過 | BaaS 架構確定 | `docs/02_architecture/SRD-{System}.md` 含 Firebase 架構 |
| FRD 資料模型 | 資料結構已定義 | FRD 資料模型章節（對應 Firestore Collection）|

---

## 執行流程

### 階段 1：Firebase BaaS 選型 ADR

呼叫 `/adr-generate "Firebase BaaS 選型"`：

```markdown
# ADR-{NNN}: Firebase 使用決策

## Decision
使用 Firebase {Auth / Firestore / Storage / Functions}

## Rationale（對應需求）
| 服務 | 用途 | 對應 NFR |
|------|------|---------|
| Firebase Auth | 第三方認證 | NFR-SEC-001（認證）|
| Firestore | 即時資料同步 | NFR-P004（即時更新需求）|

## Consequences
- Vendor Lock-in：重度依賴 Firebase SDK
- Security Rules 是最後一道防線（必須嚴格設計）
- Client 端直接存取 Firestore：需 Security Rules 保護
```

---

### 階段 2：Security Rules Spec（安全規則設計）🔴

**文件路徑**：`docs/02_architecture/INTEGRATION-SPEC-Firebase-SecurityRules-{System}.md`

```markdown
# Firebase Security Rules Spec — {System}

**設計原則**: Deny All → 明確允許（白名單）
**對應 STRIDE**: T-006 Elevation, T-004 Info Disclosure

## Firestore Rules 設計

| Collection | 讀取 | 寫入 | 條件 | FRD Feature |
|-----------|------|------|------|------------|
| users/{uid} | 僅本人 | 僅本人 | auth.uid == uid | F-USR-001 |
| posts/{postId} | 所有登入用戶 | 僅作者 | resource.data.authorId == auth.uid | F-POST-001 |
| admin/{doc} | 無 | 無（僅 Functions）| false | 管理員資料保護 |

## Security Rules 實作

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // 預設拒絕所有（SDD: Deny All 原則）
    match /{document=**} {
      allow read, write: if false;
    }

    // users Collection（對應 F-USR-001）
    match /users/{uid} {
      allow read, write: if request.auth != null
                        && request.auth.uid == uid;
    }
  }
}
```

🔴 Security Rules 必須在 Firestore 資料結構實作前凍結。
```

---

### 階段 3：Firestore 資料結構（對應 FRD 資料模型）

```markdown
# Firestore Data Model Spec

## Collection: users（對應 FRD F-USR-XXX）

Document ID: {uid}（Firebase Auth UID）
| 欄位 | 型別 | 必要 | 說明 |
|------|------|------|------|
| email | string | ✅ | 用戶 email |
| displayName | string | ✅ | 顯示名稱 |
| createdAt | timestamp | ✅ | 建立時間 |
| role | string | ✅ | 'user' / 'admin' |
```

---

### 階段 4：RTM 更新 🔴

```bash
/rtm-generate update
/spec-compliance-check docs/02_architecture/INTEGRATION-SPEC-Firebase-SecurityRules-{System}.md
```

🔴 確認點：Security Rules 測試（Firebase Emulator）通過；所有 Collection 有 Rules 覆蓋。

---

## 強制產出（SDD 文件）

| 產出物 | 路徑 | 對應 SCG |
|--------|------|---------|
| Firebase BaaS ADR | `docs/02_architecture/adr/ADR-{NNN}-firebase-baas.md` | SCG-2 |
| Security Rules Spec | `docs/02_architecture/INTEGRATION-SPEC-Firebase-SecurityRules-{System}.md` | SCG-2 |

---

**基於**: AISDLC-SDD v0.29
**對應情境**: Integration 場景
