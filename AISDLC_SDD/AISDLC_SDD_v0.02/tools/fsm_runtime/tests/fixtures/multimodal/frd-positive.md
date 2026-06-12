# FRD — Auth (A-31.1 / A-31.3 / A-31.5 positive)

## F-010 登入流程

**AC-010-1**: 用戶輸入 Email 與 password，按下「登入」按鈕後導向首頁。
資料表 `email` 與 `password` 欄位於 `users` 中持久化。

<!-- anchor:ui:LoginScreen -->
<!-- anchor:api:POST /auth/login -->
<!-- anchor:db:users -->
