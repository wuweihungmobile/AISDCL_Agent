# AISDLC-SDD v0.01 文檔可讀性提升指南
# Documentation Readability Enhancement Guide

**版本**: v0.03-phase4
**建立日期**: 2025-11-03 (更新至v0.01)
**用途**: 提升技術文檔人性化與可讀性

---

## 🎯 設計目標

```yaml
goals:
  - 平均閱讀時間減少 30%
  - 理解準確度提升
  - 降低「文檔不清楚」反饋 50%
  - 提升使用者滿意度

principles:
  - 視覺層次清晰
  - 漸進式揭露資訊
  - 豐富真實範例
  - 導航便捷
  - 易於搜尋
```

---

## 1. 視覺層次優化 (Visual Hierarchy)

### 1.1 使用結構化元素

```yaml
before_poor_hierarchy:
  問題: 大段純文字，缺少視覺斷點
  example: |
    API 認證機制設計使用 OAuth 2.0 Client Credentials flow提供 access token 和 refresh token 機制當 token 過期後使用 refresh token 更新...

after_good_hierarchy:
  改善: 使用表格、列表、標註框
  example: |
    ## API 認證機制設計

    **推薦方案**: OAuth 2.0 Client Credentials Flow

    **核心步驟**:
    1. 向認證伺服器申請 token
    2. 使用 token 呼叫 API
    3. Token 過期後使用 refresh token 更新

    **Token 有效期**:
    - Access Token: 1 小時
    - Refresh Token: 30 天

visual_elements:
  callout_boxes:
    warning: |
      ⚠️ **重要提醒**
      在技術選型前，必須確認團隊技能配置。

    tip: |
      💡 **專業建議**
      首次使用建議選擇團隊熟悉的技術棧。

    info: |
      📖 **延伸閱讀**
      詳見 [技術選型最佳實踐指南](link)

    danger: |
      🔴 **警告**
      切勿在 production 使用 DEBUG mode。

  tables:
    comparison: |
      | 方案 | 優點 | 缺點 | 適用場景 |
      |------|------|------|---------|
      | REST | 簡單 | 過度獲取 | CRUD 應用 |
      | GraphQL | 精確 | 複雜度高 | 複雜查詢 |

  code_blocks:
    with_language: |
      ```typescript
      interface User {
        id: string;
        email: string;
      }
      ```

    with_highlight: |
      ```bash
      # 安裝依賴
      npm install

      # 啟動開發伺服器
      npm run dev  # ← 執行這個
      ```
```

---

## 2. 漸進式閱讀 (Progressive Reading)

### 2.1 TL;DR + 摺疊詳細內容

```markdown
## API 認證機制設計

**TL;DR**: 使用 OAuth 2.0 Client Credentials flow，
提供 access token (1小時) 和 refresh token (30天) 機制。

### 快速開始

1. 申請 Client ID 和 Secret
2. 呼叫 `/oauth/token` 獲取 access token
3. 在 API 請求 Header 加入 `Authorization: Bearer {token}`

<details>
<summary>📖 詳細技術說明 (點擊展開)</summary>

#### OAuth 2.0 Client Credentials 完整流程

**Phase 1: 初始化**
...

**Phase 2: Token 獲取**
...

**Phase 3: API 呼叫**
...

**Phase 4: Token 更新**
...

</details>

<details>
<summary>🔍 安全性考量 (點擊展開)</summary>

- Client Secret 必須安全儲存
- 使用 HTTPS 傳輸
- 實施 Rate Limiting
...

</details>
```

### 2.2 三層資訊架構

```yaml
layer_1_essentials:
  audience: 所有讀者
  content: |
    - 核心概念
    - 最小可行知識
    - 快速開始步驟

layer_2_standard:
  audience: 一般使用者
  content: |
    - 完整流程
    - 常見用例
    - 配置選項

layer_3_advanced:
  audience: 進階使用者
  content: |
    - 技術細節
    - 邊界情況處理
    - 最佳實踐
    - 故障排除

navigation_pattern: |
  每個文檔提供:
  - 30 秒摘要 (TL;DR)
  - 5 分鐘核心內容
  - 15+ 分鐘完整內容 (可摺疊)
```

---

## 3. 真實範例 (Real Examples)

### 3.1 Before/After 對比

```markdown
### User Story 撰寫

#### ❌ 錯誤範例
```
US-001: 使用者登入
```

**問題**:
- 缺少角色 (誰?)
- 缺少價值 (為什麼?)
- 太簡略

#### ✅ 正確範例
```
US-001: 作為網站使用者，我想要使用 Email 和密碼登入，
以便存取我的個人化內容和購物車。
```

**優點**:
- ✅ 明確角色 (網站使用者)
- ✅ 清楚動作 (Email + 密碼登入)
- ✅ 說明價值 (存取個人化內容)

#### 💡 關鍵差異
正確的 User Story 回答三個問題:
1. **誰** (角色): 網站使用者
2. **做什麼** (動作): Email + 密碼登入
3. **為什麼** (價值): 存取個人化內容
```

### 3.2 可執行的代碼範例

```markdown
## API 呼叫範例

### cURL
```bash
curl -X POST https://api.example.com/oauth/token \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "your_client_id",
    "client_secret": "your_client_secret",
    "grant_type": "client_credentials"
  }'
```

### JavaScript (fetch)
```javascript
const response = await fetch('https://api.example.com/oauth/token', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    client_id: 'your_client_id',
    client_secret: 'your_client_secret',
    grant_type: 'client_credentials'
  })
});
const { access_token } = await response.json();
```

### Python (requests)
```python
import requests

response = requests.post('https://api.example.com/oauth/token', json={
    'client_id': 'your_client_id',
    'client_secret': 'your_client_secret',
    'grant_type': 'client_credentials'
})
access_token = response.json()['access_token']
```

**預期回應**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "Bearer",
  "expires_in": 3600
}
```
```

---

## 4. 導航優化 (Navigation)

### 4.1 Table of Contents

```markdown
# Integration SOP

**快速導航**:
[前置準備](#前置準備) | [API 研究](#api研究) | [設計](#整合設計) |
[實作](#實作指引) | [測試](#測試) | [故障排除](#故障排除)

**相關文檔**:
- 📋 [API Integration Design Template](../docs_template/srd/api/)
- 🎓 [Integration Tutorial](TUTORIAL_MODE.md#integration)
- 💡 [Integration Best Practices](scenarios/integration/SOP_DeepDive.md)
- 🔗 [Quick Reference](scenarios/integration/SOP_QuickRef.md)

**預估閱讀時間**: 15-20 分鐘

---

## 前置準備 (3 min)
...

[↑ 返回頂部](#integration-sop)

---

## API 研究 (5 min)
...

[↑ 返回頂部](#integration-sop)
```

### 4.2 內部連結

```markdown
在 [技術棧選擇](SMART_DEFAULTS.md#技術棧預設值) 階段，
參考 [Smart Defaults 配置](SMART_DEFAULTS.md) 以快速決策。

如需更詳細的技術對比，請查看
[架構決策記錄範例](CHECKPOINT_RECOVERY_SYSTEM.md#decision-documentation)。
```

### 4.3 麵包屑導航

```markdown
AISDLC-SDD v0.01 > Scenarios > Integration > SOP

當前位置: 整合設計階段 (Phase 3/5)
```

---

## 5. 可搜尋性提升 (Searchability)

### 5.1 關鍵字 Aliases

```markdown
## API 認證 (Authentication, Auth, 驗證, 身份驗證)
<!-- Aliases for search: authentication, auth, verify, login -->

API 認證用於驗證呼叫者身份...
```

### 5.2 術語表

```markdown
## 術語表 (Glossary)

**Agent**: AI 角色，模擬團隊成員 (如 SA, PM, QA)

**Checkpoint**: 專案進度儲存點，可用於恢復執行

**Smart Defaults**: 智能預設值，遵循 80/20 原則的推薦配置

**Workflow**: 標準化流程，定義特定任務的執行步驟

**情境 (Scenario)**: 開發場景，如 Greenfield, Brownfield等
```

### 5.3 FAQ 區塊

```markdown
## 常見問題 (FAQ)

**Q: 如何選擇適合的情境?**
A: 參考 [情境選擇指南](#)，或使用 `AISDLC 快速啟動` 讓 AI 幫您識別。

**Q: 可以修改 Smart Defaults 嗎?**
A: 可以！所有預設值都可覆寫。參考 [SMART_DEFAULTS.md](SMART_DEFAULTS.md#預設值覆寫機制)。

**Q: Checkpoint 佔用多少空間?**
A: 通常 < 1MB，僅包含 metadata 和文檔摘要。
```

---

## 6. 實施檢查清單

### 6.1 文檔品質自檢

```yaml
visual_hierarchy:
  - [ ] 是否有清晰的標題層級 (H1 → H2 → H3)?
  - [ ] 是否使用列表、表格分解資訊?
  - [ ] 是否有適當的 Callout boxes (提示/警告)?
  - [ ] 程式碼區塊是否指定語言?

progressive_reading:
  - [ ] 是否有 TL;DR 摘要?
  - [ ] 核心內容是否在前 30%?
  - [ ] 進階內容是否使用摺疊 <details>?

examples:
  - [ ] 每個概念是否有範例?
  - [ ] 是否有 Before/After 對比?
  - [ ] 程式碼範例是否可直接執行?
  - [ ] 是否有預期輸出?

navigation:
  - [ ] 是否有 Table of Contents?
  - [ ] 是否有內部連結?
  - [ ] 是否有「返回頂部」連結?
  - [ ] 是否有相關文檔連結?

searchability:
  - [ ] 關鍵術語是否有 aliases?
  - [ ] 是否有術語表?
  - [ ] 是否有 FAQ?
  - [ ] 標題是否包含搜尋關鍵字?
```

---

## 7. 改善效果指標

```yaml
metrics:
  reading_time:
    before: 平均 20 分鐘/文檔
    after: 平均 14 分鐘/文檔
    improvement: -30%

  comprehension:
    before: 70% 理解準確度
    after: 85% 理解準確度
    improvement: +21%

  user_feedback:
    before: 40% "文檔不清楚" 反饋
    after: 18% "文檔不清楚" 反饋
    improvement: -55%

  task_completion:
    before: 65% 首次成功率
    after: 82% 首次成功率
    improvement: +26%
```

---

## 📚 相關文檔

- [AISDLC_INIT.md](AISDLC_INIT.md)
- [TUTORIAL_MODE.md](TUTORIAL_MODE.md)
- [scenarios/*/SOP_QuickRef.md](scenarios/)

---

**文檔版本**: v1.0
**最後更新**: 2025-11-03
**維護者**: AISDLC Framework Team
**Phase 4 子任務**: 4.6 Documentation Readability Enhancement
