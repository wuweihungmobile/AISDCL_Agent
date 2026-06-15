---
name: dev-review
description: 以 Developer 角色進行代碼審查，驗證實作與規格（SRD/OpenAPI Contract）一致性，產出 SCG-4 通過依據
user-invocable: true
disable-model-invocation: false
argument-hint: "[scope: pr|file|module] [focus: quality|security|performance|spec-compliance]"
allowed-tools:
  - Read
  - Grep
  - Glob
---

# Dev 代碼審查 Skill（SDD 原生）

代碼審查的 SDD 核心目標：**驗證實作與規格一致性**。審查清單直接對照 SRD 和 OpenAPI Contract，確保代碼是規格的忠實實現。本 Skill 產出 SCG-4 的通過依據。

---

## 觸發方式

```bash
/dev-review                        # 完整審查（PR 提交後）
/dev-review pr                     # 審查特定 Pull Request
/dev-review spec-compliance        # 僅驗證規格一致性（SCG-4 核心）
/dev-review security               # 安全聚焦審查
/dev-review performance            # 效能聚焦審查
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

### 階段 2：規格一致性審查（SCG-4 核心） 🔴

```markdown
## 規格一致性審查清單（SCG-4）

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
# 代碼審查報告 — {PR/模組名稱}

**審查範圍**: {PR ID 或文件清單}
**審查日期**: {YYYY-MM-DD}
**審查者**: Dev Agent (David)
**對應規格**: SRD-{System} / CONTRACT-{Module}-v{N}

## 規格一致性結果（SCG-4 依據）
🟢 通過 / 🔴 未通過

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
- [ ] ✅ 通過審查（SCG-4 依據已建立）
- [ ] 🔄 需要修改後重審（Critical 問題未修復）
- [ ] ❌ 重大架構問題（需重新設計）

**SCG-4 建議**: 🟢 可通過 / 🔴 需修正
```

執行 `/spec-compliance-check`（非必填，可選）後，🔴 確認點：PR 作者需確認審查結果。

---

## 強制產出（SDD 文件）

| 產出物 | 路徑 | 對應 SCG |
|--------|------|---------|
| 代碼審查報告 | `docs/06_quality/CODE-REVIEW-{PR/Module}-{date}.md` | SCG-4 |
| 規格不一致清單（若有） | 包含在審查報告中 | SCG-4 修正依據 |

---

## 後置動作

若審查通過：
```
/rtm-generate update    # 更新 RTM 中 TC 狀態為 ✅
/sdd-gate SCG-4         # 執行 Implementation Review 閘門
```

若審查未通過：
```
# 退回修改，重新提 PR，重新執行 /dev-review
```

🔷 **本 Skill 協助通過**：SCG-4（Implementation Review Gate）

---

## 相關 Skill

- `/qa-test` — QA 測試（Contract Testing 結果作為審查參考）
- `/security-audit` — 深度安全審查（若發現重大安全問題）
- `/refactoring-code-quality` — 代碼重構（解決 Major 問題）
- `/sdd-gate SCG-4` — 實作審查閘門

---

**基於**: AISDLC-SDD v0.01
**對應 Agent**: `06.dev-developer-zh.yaml`
**對應 SDD Enhancement**: `scenarios/greenfield/SDD_GREENFIELD_ENHANCEMENT.md`
