# Multimodal Test Fixtures

ACT-031 (Phase F M4 D-31.16) — 多模態驗證的最小可重現樣本，覆蓋 A-31.1~A-31.9。

```
fixtures/multimodal/
├── frd-positive.md            # A-31.1: UI/API/DB 三類 anchor 全對齊
├── frd-ui-missing-button.md   # A-31.2: UI 反例（mockup 缺登入按鈕）
├── frd-api-missing-field.md   # A-31.4: OpenAPI requestBody 缺 password
├── frd-db-missing-column.md   # A-31.5: DB schema 缺 email 欄位
├── srd-orphan-component.md    # A-31.6: C4 元件未對應到 SRD
├── frd-missing-anchor.md      # A-31.7: anchor 指向不存在的 mockup 檔
├── srd-c4-aligned.md          # A-31.6 正例
├── docs/                      # mock project_root 用
│   ├── 99_media/ui/login-screen.html
│   ├── 99_media/ui/login-screen-no-button.html
│   ├── 02_architecture/api/auth.yaml
│   ├── 02_architecture/api/auth-no-password.yaml
│   ├── 02_architecture/C4-OrderSystem.md
│   ├── 07_design/db/schema.sql
│   └── 07_design/db/schema-no-email.sql
```

每個 fixture 都包含一段 AC 與一個 anchor，讓單元測試能精確驗證一條規則。
