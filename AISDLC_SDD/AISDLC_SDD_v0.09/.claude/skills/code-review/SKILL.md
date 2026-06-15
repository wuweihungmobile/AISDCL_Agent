---
name: code-review
description: 代碼審查，規格一致性清單為核心（Code vs Contract vs FRD），SCG-4 閘門依據
user-invocable: true
disable-model-invocation: false
argument-hint: "[pr_url: PR URL] [type: standard|security|architecture|spec-compliance]"
allowed-tools:
  - Read
  - Write
  - Grep
  - Glob
---

# Code Review Skill（SDD 原生）

SDD 的 Code Review 不只是「代碼風格審查」，而是「規格一致性審查」：實作必須符合凍結的 API Contract（SCG-3），業務邏輯必須對應 FRD AC，架構必須符合 SRD C4 設計。Code Review 是 SCG-4 閘門的必要依據。

---

## 觸發方式

```bash
/code-review standard
/code-review spec-compliance
/code-review security
```

---

## 前置條件（SDD Spec-First）

| 閘門 | 說明 | 驗證方式 |
|------|------|---------|
| 🔷 SCG-3 通過 | Contract 已凍結（審查依據）| `CONTRACT-*.yaml` 存在 |
| FRD 可讀 | 業務邏輯審查依據 | `docs/01_requirements/FRD-{System}.md` |

---

## 執行流程

### 階段 1：規格文件準備

讀取：
- `docs/02_architecture/api/CONTRACT-{Module}-v{N}.yaml`（API 一致性依據）
- `docs/01_requirements/FRD-{System}.md`（業務邏輯依據）
- `docs/02_architecture/SRD-{System}.md`（架構依據）

---

### 階段 2：SDD 規格一致性審查（核心）🔴

**審查清單 A：API Contract vs 實作**

| 審查項目 | 方法 | ✅/❌ |
|---------|------|-------|
| 所有 Contract 端點都已實作 | 比對 operationId vs handler | |
| 請求 Schema 驗證完整 | 比對 requestBody properties vs DTO | |
| 回應格式與 Contract 一致 | 比對 responses schema vs 實際回傳 | |
| 所有 Contract 錯誤碼都已處理 | 比對 400/401/403/404/500 | |
| 未定義的端點沒有被實作 | 無幽靈端點 | |

**審查清單 B：FRD Business Logic vs 實作**

| 審查項目 | 方法 | ✅/❌ |
|---------|------|-------|
| AC 驗收標準有對應的代碼邏輯 | AC-XXX-Y → 函數/條件 | |
| Business Invariants（INV-XXX）有強制執行 | INV vs Guard Clause / DB Constraint | |
| NFR 有對應的非功能實作 | NFR-P001（速率限制）/ NFR-SEC（加密）| |

**審查清單 C：架構符合 SRD**

| 審查項目 | ✅/❌ |
|---------|-------|
| 新模組符合 C4 Container 邊界 | |
| 模組間依賴符合 SRD 依賴方向 | |
| 外部整合使用 Integration Spec 設計 | |
| 無未記錄的技術決策（需 ADR）| |

**審查清單 D：代碼品質**

| 審查項目 | ✅/❌ |
|---------|-------|
| 單元測試覆蓋率 ≥ 80%（NFR 要求）| |
| Contract Testing 通過 | |
| 無硬編碼的密鑰（安全）| |
| Error Handling 對應 Error Contract | |

---

### 階段 3：SCG-4 審查報告產出

**文件路徑**：`docs/03_testing/SCG-4-REPORT-{System}-PR{N}.md`

```markdown
# SCG-4 Code Review Report — PR #{N}

**PR 標題**: {PR 標題}
**對應 US-ID**: {US-XXX}
**審查者**: {name}
**審查日期**: {YYYY-MM-DD}

## 規格一致性結論

| 審查類型 | 結果 | 問題數 |
|---------|------|--------|
| A: Contract vs 實作 | ✅ Pass / ❌ Fail | {N} |
| B: FRD AC vs 實作 | ✅ Pass / ❌ Fail | {N} |
| C: 架構符合 SRD | ✅ Pass / ❌ Fail | {N} |
| D: 代碼品質 | ✅ Pass / ❌ Fail | {N} |

## 阻擋問題（必修復）
- [ ] {問題描述}（對應 AC-XXX-Y / Contract 端點 XXX）

## 建議改善（非阻擋）
- {建議}

## SCG-4 閘門結論
→ **Approved / Request Changes**
```

---

### 階段 4：RTM 狀態更新 🔴

```bash
/rtm-generate update    # 更新審查後的 TC 狀態
/spec-compliance-check  # 確認所有文件規格合規
```

🔴 確認點：阻擋問題全部修復後，SCG-4 Report 更新為 Approved。

---

## 強制產出（SDD 文件）

| 產出物 | 路徑 | 對應 SCG |
|--------|------|---------|
| SCG-4 Review Report | `docs/03_testing/SCG-4-REPORT-{System}-PR{N}.md` | SCG-4 |

---

## 後置動作

```
/sdd-gate SCG-4    # 審查通過後正式執行 SCG-4 閘門
```

🔷 **本 Skill 協助通過**：SCG-4（PR Review 閘門）

---

## 相關 Skill

- `/dev-review` — 開發自我審查（提交前）
- `/spec-compliance-check` — 自動規格驗證
- `/sdd-gate SCG-4` — 正式閘門確認

---

**基於**: AISDLC-SDD v0.01
**閘門文件**: `workflow/sdd-spec-first-gate/SDD_SPEC_FIRST_GATE.md`
