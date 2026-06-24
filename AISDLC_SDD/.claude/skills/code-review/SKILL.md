---
name: code-review
description: 通用程式品質審查 — 可讀性、重複（DRY）、效能、壞味道、錯誤處理等工程品質面向，不綁 SCG-4 規格一致性。【何時用哪個】純品質/壞味道審查用本 skill；PR 後正式 SCG-4 規格一致性主審（Code vs Contract vs FRD）用 /sdd-review；提交 commit/PR 前的開發者輕量自審用 /dev-review。
user-invocable: true
disable-model-invocation: false
argument-hint: "[pr_url: PR URL] [type: standard|security|performance|readability]"
allowed-tools:
  - Read
  - Write
  - Grep
  - Glob
---

# Code Review Skill（通用程式品質）

本 Skill 專注**通用程式品質審查**：可讀性、命名、重複（DRY）、巢狀深度、效能熱點、錯誤處理、壞味道（code smell）等工程品質面向。**它不負責 SCG-4 規格一致性裁決**——Code vs Contract vs FRD 的規格一致性主審由 `/sdd-review` 負責；提交 commit/PR 前的開發者輕量自審由 `/dev-review` 負責。三者分工互斥、報告路徑互異。

---

## 觸發方式

```bash
/code-review standard      # 通用品質全面審查
/code-review readability   # 可讀性/命名/結構聚焦
/code-review performance   # 效能熱點聚焦
/code-review security      # 安全壞味道聚焦
```

---

## 前置條件

| 條件 | 說明 | 驗證方式 |
|------|------|---------|
| 代碼變更存在 | PR 或本地修改 | git diff 有內容 |

> 本 Skill 為通用品質審查，**不以規格凍結為前置**；規格一致性（Contract/FRD/SRD 對照）不在本 skill 範圍，請改用 `/sdd-review`。

---

## 執行流程

### 階段 1：審查範圍準備

讀取待審代碼變更（PR diff 或指定檔案／模組），確認審查焦點（standard / readability / performance / security）。

---

### 階段 2：通用程式品質審查（核心）🔴

**審查清單 A：結構與可讀性**

| 審查項目 | ✅/❌ |
|---------|-------|
| 命名規範清晰有意義（函數/變數/類別）| |
| 單一職責（函數聚焦、無多重職責）| |
| 巢狀深度 ≤ 3 層 | |
| DRY 原則（無重複邏輯）| |
| 無明顯壞味道（god function / magic number / dead code）| |

**審查清單 B：錯誤處理**

| 審查項目 | ✅/❌ |
|---------|-------|
| 外部呼叫/IO 有錯誤處理 | |
| 使用者輸入有驗證 | |
| 錯誤訊息不洩漏系統內部資訊 | |

**審查清單 C：效能**

| 審查項目 | ✅/❌ |
|---------|-------|
| 無 N+1 查詢 | |
| 大量查詢有分頁 | |
| 無不必要的重複計算/迴圈內 IO | |
| 適當使用快取 | |

**審查清單 D：測試與安全壞味道**

| 審查項目 | ✅/❌ |
|---------|-------|
| 變更有對應測試、覆蓋率未下降 | |
| 無硬編碼的密鑰 | |
| 無明顯注入面（拼接 SQL / 未編碼輸出）| |

---

### 階段 3：品質審查報告產出

**文件路徑**：`docs/06_quality/CODE-QUALITY-REVIEW-{Module}-{date}.md`

```markdown
# Code Quality Review Report — {模組/PR}

**審查範圍**: {PR ID 或檔案清單}
**審查者**: {name}
**審查日期**: {YYYY-MM-DD}

## 品質審查結論

| 審查類型 | 結果 | 問題數 |
|---------|------|--------|
| A: 結構與可讀性 | ✅ Pass / ❌ Fail | {N} |
| B: 錯誤處理 | ✅ Pass / ❌ Fail | {N} |
| C: 效能 | ✅ Pass / ❌ Fail | {N} |
| D: 測試與安全壞味道 | ✅ Pass / ❌ Fail | {N} |

## 阻擋問題（必修復）
- [ ] {問題描述} — {file:line}

## 建議改善（非阻擋）
- {建議}

## 品質審查結論
→ **Approved / Request Changes**
```

🔴 確認點：阻擋問題全部修復後，品質審查報告更新為 Approved。

---

## 強制產出

| 產出物 | 路徑 | 用途 |
|--------|------|------|
| Code Quality Review Report | `docs/06_quality/CODE-QUALITY-REVIEW-{Module}-{date}.md` | 通用程式品質審查（不綁 SCG-4） |

---

## 後置動作

```
/refactoring-code-quality   # 依品質審查結果重構（解決壞味道/重複）
```

> 規格一致性（SCG-4）不在本 skill 範圍；若需 SCG-4 規格一致性主審，請執行 `/sdd-review`。

---

## 相關 Skill（何時用哪個）

- `/sdd-review` — **PR 後正式 SCG-4 規格一致性主審**（Code vs Contract vs FRD 裁決）
- `/dev-review` — **提交 commit/PR 前的開發者輕量自審**
- `/refactoring-code-quality` — 依品質審查結果重構

---

**基於**: AISDLC-SDD v0.22
**定位**: 通用程式品質審查（不綁 SCG-4；SCG-4 規格一致性主審見 `/sdd-review`）
