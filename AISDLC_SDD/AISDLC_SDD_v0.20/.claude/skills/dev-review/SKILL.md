---
name: dev-review
description: 開發者「提交前自審」（self-review before commit/PR）— 輕量、開發者視角的快速自檢，提交 PR 前先抓明顯的規格偏差與品質問題。【何時用哪個】提交前先跑本 skill 自審；PR 後正式 SCG-4 規格一致性主審用 /sdd-review；通用程式品質（可讀性/重複/效能/壞味道，不綁 SCG-4）用 /code-review。
user-invocable: true
disable-model-invocation: false
argument-hint: "[scope: pr|file|module] [focus: quality|security|performance|spec-compliance]"
allowed-tools:
  - Read
  - Grep
  - Glob
---

# Dev 提交前自審 Skill（SDD 原生）

本 Skill 是**開發者在提交 commit/PR 前的輕量自我審查**（self-review before commit/PR），以開發者視角快速自檢，把明顯的規格偏差與品質問題在送審前先解決。**它不是正式 SCG-4 閘門主審**——正式 SCG-4 規格一致性主審由 `/sdd-review` 負責；本 Skill 的自審結果僅作為提交前的事前準備，降低後續 SCG-4 被退回的機率。

---

## 觸發方式

```bash
/dev-review                        # 完整自審（提交 commit/PR 前）
/dev-review file                   # 自審特定檔案
/dev-review module                 # 自審特定模組
/dev-review security               # 安全聚焦自審
/dev-review performance            # 效能聚焦自審
```

---

## 前置條件（SDD Spec-First）

| 閘門/文件 | 說明 | 驗證方式 |
|---------|------|---------|
| 🔷 SCG-3 通過 | Contract 已凍結（審查依據） | `docs/02_architecture/api/CONTRACT-*.yaml` 存在 |
| SRD 存在 | 架構規格（審查依據） | `docs/02_architecture/SRD-{System}.md` 存在 |
| 代碼變更存在 | PR 或本地修改 | git diff 有內容 |

---

## 執行流程

### 階段 1：審查準備—讀取規格

審查前必須讀取對應規格文件：

```bash
# 讀取 API Contract（最重要）
docs/02_architecture/api/CONTRACT-{Module}-v{N}.yaml

# 讀取 SRD 模組設計
docs/02_architecture/SRD-{SystemName}.md

# 讀取 FRD（業務邏輯依據）
docs/01_requirements/FRD-{SystemName}.md

# 讀取 Business Invariants（Refactoring 情境）
docs/01_requirements/INVARIANT-SPEC-{SystemName}.md（若存在）
```

🔴 確認點：明確審查範圍（哪些 PR/文件/模組），確認對應的 Contract 版本。

---

### 階段 2：提交前規格自檢（事前準備，非 SCG-4 主審） 🔴

> 本清單供開發者提交前自查，提早發現明顯偏差；正式 SCG-4 規格一致性裁決由 `/sdd-review` 執行。

```markdown
## 提交前規格自檢清單

### API 實作 vs. Contract
- [ ] 所有端點 URL 與 Contract 一致（無多餘或缺少）
- [ ] HTTP Method 與 Contract 一致
- [ ] Request Body Schema 欄位名稱/型別與 Contract 一致
- [ ] Response Schema 欄位名稱/型別與 Contract 一致
- [ ] 錯誤碼回傳與 Contract 一致（400/401/403/404/500）
- [ ] 認證方式與 Contract security scheme 一致

### 業務邏輯 vs. FRD
- [ ] F-XXX 功能需求在代碼中有對應實作
- [ ] BR-XXX 業務規則在代碼中有強制執行（非可選）
- [ ] 例外情況處理與 FRD 描述一致

### 架構 vs. SRD
- [ ] 模組職責與 SRD 模組設計一致（無越界）
- [ ] 依賴關係與 SRD 容器架構一致
- [ ] 資料模型與 SRD 資料設計一致

### Business Invariants（Refactoring 情境）
- [ ] INV-XXX 不變量在重構後仍然保持
- [ ] Invariant Test Contract 測試未被破壞
```

---

### 階段 3：代碼品質審查

```markdown
## 代碼品質清單

### 結構與可讀性
- [ ] 命名規範清晰有意義（函數/變數/類別）
- [ ] 單一職責原則（函數 ≤ 50 行，無多重職責）
- [ ] 巢狀深度 ≤ 3 層
- [ ] DRY 原則（無重複邏輯）

### 錯誤處理
- [ ] 所有外部 API 呼叫有錯誤處理
- [ ] 使用者輸入有驗證
- [ ] 資料庫操作有異常處理
- [ ] 錯誤訊息不洩漏系統內部資訊

### 測試
- [ ] 新功能有對應單元測試
- [ ] Contract Testing 未被破壞（測試通過）
- [ ] 覆蓋率未下降（相對 PR 前）
```

---

### 階段 4：安全性審查

```markdown
## 安全審查清單

### 輸入驗證
- [ ] 所有使用者輸入有驗證（型別/長度/格式）
- [ ] SQL 注入防護（參數化查詢）
- [ ] XSS 防護（輸出編碼）
- [ ] 路徑遍歷防護

### 認證授權
- [ ] 敏感操作有 RBAC 權限檢查
- [ ] Token/Session 安全處理（不存 localStorage）
- [ ] 日誌不含敏感資訊（密碼/Token/PII）

### 依賴安全
- [ ] 無已知 CVE 高風險依賴（新增套件前確認）
```

---

### 階段 5：效能審查

```markdown
## 效能審查清單

### 資料庫
- [ ] 無 N+1 查詢問題
- [ ] 大量查詢有分頁（limit/offset 或 cursor）
- [ ] 查詢欄位有索引支援

### 非同步
- [ ] 耗時操作使用非同步處理（非阻塞主執行緒）
- [ ] 適當使用快取（對照 NFR-XXX 要求）
```

---

### 階段 6：審查報告產出 🔴

```markdown
# 提交前自審報告 — {模組/檔案名稱}

**自審範圍**: {檔案清單或模組}
**自審日期**: {YYYY-MM-DD}
**自審者**: Dev（提交者本人）
**對應規格**: SRD-{System} / CONTRACT-{Module}-v{N}

## 提交前規格自檢結果（事前準備，非 SCG-4 裁決）
🟢 自檢通過 / 🔴 自檢發現問題（提交前先修）

### 規格不一致項目（若有）
| 項目 | Contract 定義 | 代碼實作 | 修改建議 |
|------|-------------|---------|---------|
| POST /{resource} 回應 | 201 Created | 200 OK | 修改為 201 |

## 代碼品質問題

### Critical（必須修復後才能合併）
1. {問題描述} — {file.ts:line}
   - 建議: {修復方案}

### Major（建議修復）
1. {問題描述}

### Minor（可選改善）
1. {問題描述}

## 結論
- [ ] ✅ 自審通過（可提交 PR，後續交 /sdd-review 進行 SCG-4 主審）
- [ ] 🔄 提交前需先修（Critical 問題未修復）
- [ ] ❌ 重大架構問題（需重新設計）

**提交建議**: 🟢 可提交 PR / 🔴 提交前先修
```

🔴 確認點：提交者需確認自審結果，明顯問題修復後再提 PR。

---

## 強制產出（SDD 文件）

| 產出物 | 路徑 | 對應 SCG |
|--------|------|---------|
| 提交前自審報告 | `docs/06_quality/DEV-SELF-REVIEW-{Module}-{date}.md` | SCG-4 事前準備 |
| 自檢發現清單（若有） | 包含在自審報告中 | 提交前修正依據 |

---

## 後置動作

若自審通過：
```
/sdd-review             # 提交 PR 後執行正式 SCG-4 規格一致性主審
```

若自審未通過：
```
# 提交前先修，再重新執行 /dev-review 自審
```

🔷 **本 Skill 定位**：SCG-4 的**提交前事前準備**（正式 SCG-4 主審見 `/sdd-review`）

---

## 相關 Skill（何時用哪個）

- `/sdd-review` — **提交 PR 後的正式 SCG-4 規格一致性主審**（Code vs Contract vs FRD 裁決）
- `/code-review` — **通用程式品質審查**（可讀性/重複/效能/壞味道，不綁 SCG-4）
- `/qa-testing` — QA 測試（Contract Testing 結果作為自審參考）
- `/security-audit` — 深度安全審查（若發現重大安全問題）

---

**基於**: AISDLC-SDD v0.20
**對應 Agent**: `06.dev-developer-zh.yaml`
**對應 SDD Enhancement**: `scenarios/greenfield/SDD_GREENFIELD_ENHANCEMENT.md`
