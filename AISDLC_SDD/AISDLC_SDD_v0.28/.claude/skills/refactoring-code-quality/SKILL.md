---
name: refactoring-code-quality
description: 代碼重構，As-Is SRD 前置建立基線，Invariants 保護重構安全性，RTM 驗證不破壞 Business Invariants
user-invocable: true
disable-model-invocation: false
argument-hint: "[scope: file|module|architecture] [target: 目標路徑]"
allowed-tools:
  - Read
  - Write
  - Grep
  - Glob
---

# Refactoring Code Quality Skill（SDD 原生）

重構在 SDD 中屬於「Refactoring 場景」，有嚴格的規格保護：重構前必須建立 As-Is SRD 基線，Business Invariants（INV-XXX）必須在重構過程中被保護，重構後 RTM 所有 TC 必須維持通過。

---

## 觸發方式

```bash
/refactoring-code-quality module src/orders
/refactoring-code-quality architecture
/refactoring-code-quality file src/utils/payment.ts
```

---

## 前置條件（SDD Spec-First）

| 閘門 | 說明 | 驗證方式 |
|------|------|---------|
| 🔷 As-Is SRD 存在 | 現有架構已文件化 | `docs/02_architecture/AS-IS-SRD-{System}.md` |
| Invariants 清單 | Business Invariants 已識別 | `docs/03_testing/contracts/INVARIANT-CONTRACT-{System}.md` |
| RTM 基線 | 重構前 TC 全部通過 | RTM 現況為 100% ✅ |

> 若 As-Is SRD 不存在，先執行 `/brownfield-analysis`

---

## 執行流程

### 階段 1：As-Is 基線確認 🔴

讀取 `docs/02_architecture/AS-IS-SRD-{System}.md`，確認：
- 目標重構模組的現有架構
- 技術債清單（TD-XXX）
- 依賴關係圖（避免重構引發連鎖反應）

🔴 確認點：Business Invariants 清單確認後才開始重構設計。

---

### 階段 2：Tech Debt Spec 識別

讀取技術債清單，針對目標模組：

```markdown
## 重構技術債清單

| TD ID | 問題描述 | 影響範圍 | 重構策略 | INV 影響 |
|-------|---------|---------|---------|---------|
| TD-001 | 過長函數（> 100 行）| OrderService.createOrder | Extract Method | INV-002（訂單狀態）|
| TD-002 | 重複的驗證邏輯 | 3 個 Controller | Extract Validator | 無 |
| TD-003 | 直接 DB 存取（缺 Repository）| Business Layer | Repository Pattern | INV-001 |
```

---

### 階段 3：Invariant 保護設計（重構核心）

```markdown
## Business Invariants 保護矩陣

| INV ID | 不變量描述 | 受影響的重構 | 保護方式 |
|--------|---------|------------|---------|
| INV-001 | 訂單金額 > 0 | Repository 重構 | DB CHECK 約束保留 |
| INV-002 | 狀態轉換：PENDING→CONFIRMED→COMPLETED | Service 重構 | 狀態機測試保留 |
| INV-003 | 用戶 email 唯一 | DB 結構不變 | UNIQUE INDEX 保留 |
```

**重構安全策略**：
- Strangler Fig：逐步替換，新舊並存
- Branch by Abstraction：先建 Interface，再切換實作
- 每次重構後立即執行 `/rtm-generate verify`

---

### 階段 4：重構執行（小步前進）

每次重構步驟：
1. 修改代碼
2. 執行 `{test command}` — 確認所有 Invariant TC 通過
3. 執行 `{compile command}` — 確認無編譯錯誤
4. 僅當通過才繼續下一步（不累積）

---

### 階段 5：RTM 驗證 🔴

```bash
/rtm-generate verify    # 確認重構後 RTM 100% ✅
/spec-compliance-check docs/02_architecture/AS-IS-SRD-{System}.md
```

🔴 確認點：重構後所有 INV-XXX TC 維持通過；無 TC 被刪除。

---

## 強制產出（SDD 文件）

| 產出物 | 路徑 | 對應 SCG |
|--------|------|---------|
| Tech Debt 更新 | `docs/06_quality/TECH-DEBT-{System}.md` | 重構後 |
| To-Be SRD 更新 | `docs/02_architecture/SRD-{System}.md` | 重構後 |

---

## 後置動作

```
/rtm-generate verify    # 確認 Invariants 未被破壞
/sdd-gate SCG-4         # 重構 PR Review
```

🔷 **本 Skill 對應 SCG**：SCG-4（重構 PR Review）

---

## 相關 Skill

- `/brownfield-analysis` — As-Is SRD 建立（重構前置）
- `/rtm-generate` — Invariant TC 驗證
- `/code-review` — 重構 PR 規格一致性審查

---

**基於**: AISDLC-SDD v0.28
**對應場景**: `scenarios/refactoring/SDD_REFACTORING_ENHANCEMENT.md`
