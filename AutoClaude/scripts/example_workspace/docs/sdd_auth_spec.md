# SDD 規格：FastAPI JWT 驗證模組（example_playbook 的 fixture 規格）

> 🔴 這份檔案是 `scripts/example_playbook.yaml` 的**輸入 fixture**，不是產物。
> R82（ACB-02）立案理由：該 playbook 的 T01 原本要求讀 `docs/sdd_auth_spec.md`，
> 而全庫 Glob `**/sdd_auth_spec.md` 逐字回「No files found」——第一步就沒有規格可讀，
> 於是整支範例 playbook 在「規格先行」這件事上是空轉的。
> 產物（`auth.py` / `tests/test_auth.py` / `docs/api_auth.md`）一律落在本目錄的兄弟位置，
> 並由 `.gitignore` 排除；只有本檔入庫。

## 1. 範圍

單一 FastAPI router，提供帳密登入換發 JWT、以及以 JWT 取得自身資料兩個端點。
不含註冊、不含密碼重設、不含 refresh token（刻意窄，讓範例能在數個步驟內收斂）。

## 2. 契約（Contract-First）

### 2.1 `POST /auth/login`

| 項目 | 內容 |
|------|------|
| Request | `{"username": str, "password": str}` |
| 200 | `{"access_token": str, "token_type": "bearer"}` |
| 401 | `{"detail": "Invalid credentials"}` |

### 2.2 `GET /auth/me`

| 項目 | 內容 |
|------|------|
| Header | `Authorization: Bearer <access_token>` |
| 200 | `{"username": str}` |
| 401 | `{"detail": "Invalid token"}`（token 缺失／過期／簽章錯誤皆同此回應） |

## 3. 不變量（Invariants）

- INV-1：JWT 以 HS256 簽章，密鑰自環境變數 `AUTH_SECRET` 取得；缺該變數時**啟動即失敗**，不得回落到硬編預設值。
- INV-2：`exp` 必填，預設有效期 30 分鐘。
- INV-3：任何情況下都不得在回應主體或 log 中出現密碼明文。
- INV-4：帳密比對失敗與帳號不存在必須回**相同**的 401 回應（不可由回應差異反推帳號是否存在）。

## 4. 驗收條件（AC）

| ID | 條件 |
|----|------|
| AC-1 | 正確憑證 `POST /auth/login` → 200 且回應含非空 `access_token` |
| AC-2 | 錯誤密碼 `POST /auth/login` → 401 |
| AC-3 | 有效 token `GET /auth/me` → 200 且 `username` 等於登入者 |
| AC-4 | 無效／竄改 token `GET /auth/me` → 401 |

## 5. 固定測試帳號（範例專用）

`demo` / `demo-password`（僅供本範例，正式實作應接資料庫）。
