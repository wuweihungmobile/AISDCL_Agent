---
name: code-review
description: 標準化的代碼審查流程，確保代碼品質和知識傳承
user-invocable: true
disable-model-invocation: false
argument-hint: "[pr_url: Pull Request URL] [type: 審查類型 (standard/security/architecture)]"
allowed-tools:
  - Read
  - Write
  - Grep
  - Glob
---

# Code Review Workflow Skill

標準化的代碼審查流程。

---

## 觸發方式

```bash
/code-review                           # 開始審查流程
/code-review https://github.com/...    # 審查特定 PR
/code-review security                  # 安全審查
/code-review architecture              # 架構審查
```

---

## 審查角色

| 角色 | 職責 | 審查重點 |
|------|------|----------|
| **Reviewer** | 主要審查者 | 代碼品質、邏輯正確性 |
| **SD** | 架構審查 | 設計模式、架構符合度 |
| **Security** | 安全審查 | 安全漏洞、最佳實踐 |
| **Author** | 代碼作者 | 回應問題、修改代碼 |

---

## 執行流程

### 階段 1: 審查準備 🔴

**PR 檢查清單**:
- [ ] PR 描述完整
- [ ] 關聯的 Issue/User Story
- [ ] 自我審查完成
- [ ] 測試通過
- [ ] 無衝突

**PR 描述模板**:
```markdown
## 變更描述
[描述這個 PR 做了什麼]

## 關聯 Issue
Closes #[issue-number]

## 變更類型
- [ ] Bug 修復
- [ ] 新功能
- [ ] 重構
- [ ] 文檔更新

## 測試
- [ ] 單元測試
- [ ] 整合測試
- [ ] 手動測試

## 截圖 (如適用)
[截圖]

## Checklist
- [ ] 代碼符合編碼規範
- [ ] 已添加必要的測試
- [ ] 文檔已更新
```

🔴 **確認點**: 確認 PR 準備就緒

---

### 階段 2: 代碼審查

**審查維度**:

```markdown
## 代碼審查清單

### 1. 正確性
- [ ] 邏輯正確
- [ ] 邊界條件處理
- [ ] 錯誤處理完整
- [ ] 資源正確釋放

### 2. 可讀性
- [ ] 命名清晰
- [ ] 程式結構合理
- [ ] 註解適當
- [ ] 複雜度可接受

### 3. 可維護性
- [ ] 單一職責
- [ ] DRY 原則
- [ ] 適當抽象
- [ ] 測試覆蓋

### 4. 效能
- [ ] 無 N+1 查詢
- [ ] 適當使用快取
- [ ] 無記憶體洩漏
- [ ] 非同步處理適當

### 5. 安全性
- [ ] 輸入驗證
- [ ] 無敏感資訊洩漏
- [ ] 權限檢查
- [ ] SQL 注入防護
```

---

### 階段 3: 審查回饋

**回饋類型**:

| 標籤 | 含義 | 必須處理 |
|------|------|----------|
| 🔴 **Blocker** | 必須修改 | ✅ |
| 🟡 **Suggestion** | 建議修改 | ⚪ |
| 🟢 **Nitpick** | 小問題 | ⚪ |
| 💬 **Question** | 需要解釋 | ⚪ |
| 👍 **Praise** | 值得讚揚 | ⚪ |

**回饋格式**:
```markdown
🔴 **Blocker**: SQL 注入風險

這裡的查詢沒有使用參數化，可能導致 SQL 注入：

```typescript
// 問題代碼
const query = `SELECT * FROM users WHERE id = ${userId}`;

// 建議修改
const query = `SELECT * FROM users WHERE id = $1`;
const result = await db.query(query, [userId]);
```

參考: [OWASP SQL Injection](https://owasp.org/...)
```

---

### 階段 4: 作者回應

**回應方式**:

```markdown
## 回應清單

### Comment 1 (Blocker)
**問題**: SQL 注入風險
**處理**: ✅ 已修改，使用參數化查詢
**Commit**: abc1234

### Comment 2 (Suggestion)
**問題**: 可以使用更好的命名
**處理**: ✅ 已修改
**Commit**: def5678

### Comment 3 (Nitpick)
**問題**: 格式問題
**處理**: ⏭️ 下次改進
**原因**: 不影響功能，已記錄
```

---

### 階段 5: 審查決議 🔴

**審查結果**:

| 結果 | 條件 |
|------|------|
| ✅ **Approved** | 無 Blocker，可合併 |
| 🔄 **Request Changes** | 有 Blocker，需修改 |
| 💬 **Comment** | 僅提供意見 |

**合併條件**:
- [ ] 至少 1 個 Approved
- [ ] 所有 Blocker 已解決
- [ ] CI/CD 通過
- [ ] 無衝突

🔴 **確認點**: 確認審查結果

---

### 階段 6: 知識記錄

**審查學習**:

```markdown
## Code Review Learnings

### 日期: [YYYY-MM-DD]
### PR: #[number]

### 發現的問題模式
1. [問題模式描述]
   - 影響: [影響描述]
   - 解決: [解決方案]

### 最佳實踐
1. [最佳實踐描述]

### 團隊討論要點
1. [討論要點]
```

---

## 審查時間指南

| PR 大小 | 行數 | 建議時間 |
|---------|------|----------|
| XS | < 50 | 15 分鐘 |
| S | 50-200 | 30 分鐘 |
| M | 200-500 | 1 小時 |
| L | 500-1000 | 2 小時 |
| XL | > 1000 | 建議拆分 |

---

## 產出物

| 產出物 | 路徑 |
|--------|------|
| 審查報告 | `docs/06_quality/CODE_REVIEW_[PR].md` |
| 學習記錄 | `docs/06_quality/CODE_REVIEW_LEARNINGS.md` |

---

## 相關 Skill

- `/dev-review` - Dev 代碼審查
- `/security` - 安全審計
- `/refactor` - 代碼重構

---


## 相關檔案

- Workflow 定義: `workflow/core/`

**基於**: AISDLC v0.09 Workflow
