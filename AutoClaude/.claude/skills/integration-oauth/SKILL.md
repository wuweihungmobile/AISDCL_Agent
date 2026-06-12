---
name: integration-oauth
description: 設計並實作 OAuth 2.0 認證整合，支援 Google/GitHub/Auth0 等提供者
user-invocable: true
disable-model-invocation: false
argument-hint: "<provider: OAuth 提供者 (google/github/auth0/custom)> [framework: 使用的框架 (nextjs/express/fastapi/spring)]"
allowed-tools:
  - Read
  - Write
  - Grep
  - Glob
  - Bash
---

# Integration OAuth Skill

基於 AISDLC Integration 情境的 OAuth 2.0 認證整合技能。

---

## 觸發方式

```bash
/integration-oauth google nextjs
/integration-oauth github express
/integration-oauth auth0 fastapi
/integration-oauth --provider=google --framework=nextjs
```

---

## 執行流程

### Step 1: API 研究 (10分鐘)

**任務清單**:
1. 確認 OAuth Provider 文檔
2. 識別所需 Scopes
3. 確認回調 URL 格式
4. 檢查 Rate Limiting

**Provider 文檔**:
| Provider | 文檔 URL | 推薦 Scopes |
|----------|---------|------------|
| Google | `developers.google.com/identity` | email, profile |
| GitHub | `docs.github.com/en/apps/oauth-apps` | user:email, read:user |
| Auth0 | `auth0.com/docs` | openid, profile, email |

🔴 **確認點**: 向使用者確認所需的權限範圍 (Scopes)

---

### Step 2: 認證設計 (15分鐘)

**OAuth 2.0 授權碼流程**:

```
┌──────────┐     ┌─────────────┐     ┌────────────┐
│  User    │     │  Your App   │     │  Provider  │
└────┬─────┘     └──────┬──────┘     └─────┬──────┘
     │   1. Click Login │                   │
     │──────────────────>                   │
     │                   │ 2. Redirect      │
     │                   │──────────────────>
     │                   │                   │
     │   3. Auth Screen  │                   │
     │<──────────────────────────────────────│
     │                   │                   │
     │   4. Approve      │                   │
     │──────────────────────────────────────>│
     │                   │                   │
     │                   │ 5. Code callback  │
     │                   │<──────────────────│
     │                   │                   │
     │                   │ 6. Exchange token │
     │                   │──────────────────>│
     │                   │                   │
     │                   │ 7. Access token   │
     │                   │<──────────────────│
     │                   │                   │
     │   8. Logged in    │                   │
     │<──────────────────│                   │
```

**Token 儲存策略**:
- 🔐 Access Token: HTTP-only Cookie 或 Memory
- 🔐 Refresh Token: HTTP-only Secure Cookie
- ❌ 絕不存於 localStorage

---

### Step 3: 框架整合

#### Next.js (App Router) + NextAuth.js

**安裝依賴**:
```bash
npm install next-auth
```

**配置檔案**: `app/api/auth/[...nextauth]/route.ts`
```typescript
import NextAuth from 'next-auth';
import GoogleProvider from 'next-auth/providers/google';
import GitHubProvider from 'next-auth/providers/github';

const handler = NextAuth({
  providers: [
    {{#if google}}
    GoogleProvider({
      clientId: process.env.GOOGLE_CLIENT_ID!,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
    }),
    {{/if}}
    {{#if github}}
    GitHubProvider({
      clientId: process.env.GITHUB_ID!,
      clientSecret: process.env.GITHUB_SECRET!,
    }),
    {{/if}}
  ],
  callbacks: {
    async jwt({ token, account }) {
      if (account) {
        token.accessToken = account.access_token;
      }
      return token;
    },
    async session({ session, token }) {
      session.accessToken = token.accessToken;
      return session;
    },
  },
});

export { handler as GET, handler as POST };
```

**環境變數**: `.env.local`
```
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=your-secret-key
```

#### Express.js + Passport.js

**安裝依賴**:
```bash
npm install passport passport-google-oauth20 express-session
```

**配置**: `src/auth/passport.ts`
```typescript
import passport from 'passport';
import { Strategy as GoogleStrategy } from 'passport-google-oauth20';

passport.use(new GoogleStrategy({
    clientID: process.env.GOOGLE_CLIENT_ID!,
    clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
    callbackURL: '/auth/google/callback',
  },
  (accessToken, refreshToken, profile, done) => {
    // 儲存或查詢使用者
    return done(null, profile);
  }
));

// 路由
app.get('/auth/google', passport.authenticate('google', { scope: ['profile', 'email'] }));

app.get('/auth/google/callback',
  passport.authenticate('google', { failureRedirect: '/login' }),
  (req, res) => {
    res.redirect('/');
  }
);
```

#### Spring Boot + Spring Security OAuth2

**安裝依賴** (`build.gradle.kts`):
```kotlin
dependencies {
    implementation("org.springframework.boot:spring-boot-starter-oauth2-client")
    implementation("org.springframework.boot:spring-boot-starter-security")
}
```

**配置**: `application.yml`
```yaml
spring:
  security:
    oauth2:
      client:
        registration:
          google:
            client-id: ${GOOGLE_CLIENT_ID}
            client-secret: ${GOOGLE_CLIENT_SECRET}
            scope: email, profile
          github:
            client-id: ${GITHUB_CLIENT_ID}
            client-secret: ${GITHUB_CLIENT_SECRET}
            scope: user:email, read:user
```

**Security 配置**:
```java
@Configuration
@EnableWebSecurity
public class SecurityConfig {

    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        http
            .authorizeHttpRequests(auth -> auth
                .requestMatchers("/", "/login", "/public/**").permitAll()
                .anyRequest().authenticated()
            )
            .oauth2Login(oauth2 -> oauth2
                .loginPage("/login")
                .defaultSuccessUrl("/dashboard")
                .userInfoEndpoint(userInfo -> userInfo
                    .userService(customOAuth2UserService())
                )
            );
        return http.build();
    }

    @Bean
    public OAuth2UserService<OAuth2UserRequest, OAuth2User> customOAuth2UserService() {
        DefaultOAuth2UserService delegate = new DefaultOAuth2UserService();
        return request -> {
            OAuth2User user = delegate.loadUser(request);
            // 儲存或查詢使用者
            return user;
        };
    }
}
```

#### FastAPI + Authlib

**安裝依賴**:
```bash
pip install authlib httpx
```

**配置**: `src/auth/oauth.py`
```python
from authlib.integrations.starlette_client import OAuth
from starlette.config import Config

config = Config(".env")
oauth = OAuth(config)

oauth.register(
    name="google",
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)

# FastAPI 路由
@router.get("/login/google")
async def login_google(request: Request):
    redirect_uri = request.url_for("auth_callback")
    return await oauth.google.authorize_redirect(request, redirect_uri)

@router.get("/auth/callback")
async def auth_callback(request: Request):
    token = await oauth.google.authorize_access_token(request)
    user_info = token.get("userinfo")
    # 儲存或查詢使用者
    return RedirectResponse(url="/dashboard")
```

---

### Step 4: 錯誤處理

**錯誤分類**:
| 錯誤類型 | HTTP Code | 處理方式 |
|---------|-----------|---------|
| invalid_grant | 400 | 引導重新授權 |
| access_denied | 403 | 顯示友善訊息 |
| server_error | 500 | 重試 + 告警 |
| rate_limit | 429 | 指數退避重試 |

**錯誤處理範例**:
```typescript
async function handleOAuthError(error: OAuthError) {
  switch (error.code) {
    case 'invalid_grant':
      // Token 過期，引導重新登入
      await clearSession();
      return redirect('/login?reason=session_expired');

    case 'access_denied':
      // 使用者拒絕授權
      return redirect('/login?reason=access_denied');

    default:
      // 記錄錯誤並顯示通用訊息
      logger.error('OAuth error', error);
      return redirect('/error?code=auth_failed');
  }
}
```

---

### Step 5: 安全檢查清單

🔴 **必須確認**:

- [ ] State 參數已實作（防 CSRF）
- [ ] PKCE 已啟用（公開客戶端）
- [ ] Token 不存於 localStorage
- [ ] Redirect URI 已白名單
- [ ] HTTPS 在生產環境強制啟用
- [ ] Token 過期自動更新機制已實作

---

## 產出物清單

| 產出物 | 路徑 | 說明 |
|--------|------|------|
| Auth 配置 | `app/api/auth/` 或 `src/auth/` | 認證核心邏輯 |
| 環境變數範本 | `.env.example` | 需要的環境變數 |
| 安全設定指南 | `docs/AUTH_SETUP.md` | Provider 設定步驟 |

---

## Provider 設定快速指南

### Google OAuth 設定
1. 前往 [Google Cloud Console](https://console.cloud.google.com)
2. 建立專案 → API 和服務 → 憑證
3. 建立 OAuth 2.0 用戶端 ID
4. 新增授權的重新導向 URI

### GitHub OAuth 設定
1. 前往 GitHub Settings → Developer settings
2. OAuth Apps → New OAuth App
3. 設定 Homepage URL 和 Callback URL

---

## 相關 Skill

- `/integration-stripe` - 支付整合
- `/security` - 安全審查
- `/testing` - 認證測試

---


## 相關檔案

- SOP 參考: `scenarios/integration/SOP_QuickRef.md`

**基於**: AISDLC v0.09 Integration 情境
**維護者**: AISDLC Framework Team
