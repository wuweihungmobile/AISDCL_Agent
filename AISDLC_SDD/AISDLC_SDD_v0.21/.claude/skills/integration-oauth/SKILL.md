---
name: integration-oauth
description: OAuth 2.0 認證整合，整合設計先行，ADR 記錄 Provider 選型，Consumer Contract 測試，RTM 追蹤
user-invocable: true
disable-model-invocation: false
argument-hint: "<provider: google|github|auth0|custom> [framework: nextjs|express|fastapi|spring]"
allowed-tools:
  - Read
  - Write
  - Grep
  - Glob
---

# Integration OAuth Skill（SDD 原生）

OAuth 整合在 SDD 中屬於「整合設計先行」範疇：Provider 選型需有 ADR，認證端點需在 Contract 中定義，整合行為需有 Consumer Contract 測試（Pact），整合測試結果需更新 RTM。

---

## 觸發方式

```bash
/integration-oauth google nextjs
/integration-oauth github express
/integration-oauth auth0 fastapi
```

---

## 前置條件（SDD Spec-First）

| 閘門 | 說明 | 驗證方式 |
|------|------|---------|
| 🔷 SCG-1 通過 | 認證架構已決定 | `docs/02_architecture/SRD-{System}.md` 認證章節 |
| FRD 認證需求 | 認證功能已定義為 F-XXX | `docs/01_requirements/FRD-{System}.md` 認證 Feature |
| NFR-SEC 已定義 | Token 安全 NFR 量化 | NFR-SEC-001 等存在 |

---

## 執行流程

### 階段 1：Provider 選型 ADR（設計先行）🔴

呼叫 `/adr-generate "OAuth Provider 選型"`：

```markdown
# ADR-{NNN}: OAuth Provider 選型

## Decision
選擇 {Google/GitHub/Auth0/自建} 作為 OAuth Provider

## Rationale
| Provider | 優點 | 缺點 | 適用情境 |
|---------|------|------|---------|
| Google | 用戶接受度高 | 依賴第三方 | B2C 消費者產品 |
| Auth0 | 企業功能完整 | 授權費用 | B2B/企業系統 |
| 自建 | 完全控制 | 維護成本高 | 特殊合規需求 |

## Security Considerations（對應 STRIDE）
- T-001 Spoofing：JWT RS256 簽章，TTL 對應 NFR-SEC-001
- T-003 Repudiation：所有認證事件記錄 Audit Log
- PKCE 流程（防 Authorization Code Interception）

## Consequences
- Token 儲存策略：HTTP-only Cookie（不用 localStorage）
- Refresh Token Rotation 週期：{NFR-SEC-001 定義值}
```

🔴 確認點：ADR 確定後才開始整合設計。

---

### 階段 2：整合規格設計（Integration Spec）

**文件路徑**：`docs/02_architecture/INTEGRATION-SPEC-OAuth-{System}.md`

```markdown
# OAuth Integration Spec — {System}

**Provider**: {Google/GitHub/Auth0}
**Flow**: Authorization Code + PKCE
**Token 儲存**: HTTP-only Secure Cookie

## 端點設計（補充至 CONTRACT）

| 端點 | 方法 | 說明 | FRD Feature |
|------|------|------|------------|
| /auth/{provider} | GET | 啟動 OAuth Flow | F-XXX 用戶登入 |
| /auth/{provider}/callback | GET | OAuth 回調 | F-XXX |
| /auth/logout | POST | 登出 | F-XXX |
| /auth/me | GET | 取得當前用戶 | F-XXX |

## Security 矩陣
| 機制 | 實作方式 | 對應 STRIDE | NFR-SEC |
|------|---------|-----------|---------|
| CSRF 防護 | state 參數 | T-001 Spoofing | NFR-SEC-001 |
| Code Injection 防護 | PKCE | T-002 Tampering | NFR-SEC-002 |
| Token 竊取防護 | HTTP-only Cookie | T-004 Info Disclosure | NFR-SEC-004 |
```

---

### 階段 3：Consumer Contract 測試設計

**文件路徑**：`docs/03_testing/contracts/CONSUMER-CONTRACT-OAuth-{Provider}.md`

```markdown
# Consumer Contract — OAuth {Provider}

**Consumer**: {SystemName}
**Provider**: {Google/GitHub/Auth0}
**Contract 工具**: Pact

## Consumer 期望的互動

### 互動 1: 用戶資訊端點
- Request: GET /userinfo
  - Header: Authorization: Bearer <valid_token>
- Response: 200
  - body.email: string（required）
  - body.name: string（required）
  - body.sub: string（Provider User ID，required）

### 互動 2: Token 交換
- Request: POST /token
  - body.code: string
  - body.grant_type: authorization_code
- Response: 200
  - body.access_token: string（required）
  - body.token_type: "Bearer"（required）

## Pact 測試路徑
`tests/contracts/oauth-{provider}.pact.spec.ts`
```

---

### 階段 4：框架實作（SCG-3 後）

依框架產出認證整合代碼（實作遵循 Integration Spec 的端點設計）：

**Next.js（NextAuth.js）核心配置**：
```typescript
// app/api/auth/[...nextauth]/route.ts
// 實作對應 ADR-NNN 決定的 Provider + Token 策略
import NextAuth from 'next-auth';
import GoogleProvider from 'next-auth/providers/google';

const handler = NextAuth({
  providers: [
    GoogleProvider({
      clientId: process.env.GOOGLE_CLIENT_ID!,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
    }),
  ],
  session: { strategy: 'jwt' },  // ADR-NNN: JWT 策略
  callbacks: {
    async jwt({ token, account }) {
      if (account) {
        token.accessToken = account.access_token;
      }
      return token;
    },
  },
});

export { handler as GET, handler as POST };
```

---

### 階段 5：RTM 更新 🔴

```bash
/rtm-generate update    # 更新認證相關 TC（TC-AUTH-XXX）
/spec-compliance-check docs/02_architecture/INTEGRATION-SPEC-OAuth-{System}.md
```

🔴 確認點：Consumer Contract 測試通過 + RTM 認證 TC 全部 ✅。

---

## 強制產出（SDD 文件）

| 產出物 | 路徑 | 對應 SCG |
|--------|------|---------|
| OAuth Provider ADR | `docs/02_architecture/adr/ADR-{NNN}-oauth-provider.md` | SCG-2 |
| Integration Spec | `docs/02_architecture/INTEGRATION-SPEC-OAuth-{System}.md` | SCG-1 後 |
| Consumer Contract | `docs/03_testing/contracts/CONSUMER-CONTRACT-OAuth-{Provider}.md` | SCG-3 後 |

---

## 後置動作

```
/rtm-generate update       # 更新認證 TC
/security-audit api        # 認證端點安全審查
/sdd-gate SCG-4            # 整合 PR Review
```

🔷 **本 Skill 對應 SCG**：SCG-2（認證架構凍結）、SCG-4（整合 PR Review）

---

## 相關 Skill

- `/adr-generate` — OAuth Provider 選型決策
- `/security-audit` — STRIDE 認證威脅分析（T-001 Spoofing）
- `/qa-testing` — Consumer Contract Testing
- `/integration-api-client` — API Client 整合（認證 Token 使用方）

---

**基於**: AISDLC-SDD v0.21
**對應情境**: Integration 場景
