---
name: compliance-audit
description: 合規審查，合規需求對應 FRD NFR-COMP，驗收清單對應 RTM TC，SCG-5 閘門依據
user-invocable: true
disable-model-invocation: false
argument-hint: "<standard: gdpr|hipaa|pci-dss|soc2|iso27001|all> [scope: full|data|access|privacy]"
allowed-tools:
  - Read
  - Grep
  - Glob
---

# Compliance Audit Skill（SDD 原生）

合規在 SDD 中是規格驅動的：合規需求必須在 FRD 中以 NFR-COMP-XXX 格式量化，每個合規要求必須有對應的 TC（測試案例）在 RTM 中追蹤，合規缺口報告是 SCG-5 閘門的必要依據之一。

---

## 觸發方式

```bash
/compliance-audit gdpr
/compliance-audit pci-dss
/compliance-audit all
```

---

## 前置條件（SDD Spec-First）

| 閘門 | 說明 | 驗證方式 |
|------|------|---------|
| 🔷 FRD NFR-COMP 存在 | 合規需求已量化 | `docs/01_requirements/FRD-{System}.md` 中 NFR-COMP-XXX 節 |
| RTM 建立 | 合規 TC 已建立 | `docs/03_testing/RTM-{System}.md` 中含 TC-COMP-XXX |
| STRIDE 完成 | 安全威脅已分析 | `docs/06_quality/security/STRIDE-{System}.md` 存在 |

---

## 執行流程

### 階段 1：讀取合規需求（FRD NFR-COMP）

讀取 `docs/01_requirements/FRD-{System}.md` 的合規需求章節：

```markdown
## 合規需求提取（NFR-COMP）

| NFR-COMP ID | 合規標準 | 條款 | 需求描述 | TC 覆蓋 |
|------------|---------|------|---------|---------|
| NFR-COMP-001 | GDPR | Art.17 | 用戶刪除權：30 天內完成 | TC-COMP-001 |
| NFR-COMP-002 | GDPR | Art.15 | 資料匯出：JSON 格式，24h 內 | TC-COMP-002 |
| NFR-COMP-003 | PCI-DSS | Req.3 | PAN 禁止明文儲存 | TC-COMP-003 |
```

---

### 階段 2：Compliance Matrix 產出

**文件路徑**：`docs/06_quality/security/COMPLIANCE-MATRIX-{SystemName}.md`

```markdown
# Compliance Matrix — {SystemName}

**適用標準**: {GDPR / PCI-DSS / HIPAA / SOC2 / ISO 27001}
**版本**: {N}.{N}
**狀態**: Draft → Validated（SCG-5 前）

## 合規矩陣

| 要求 ID | 條款 | GDPR | PCI-DSS | ISO 27001 | NFR-COMP ID | 實作狀態 | TC ID | 證據 |
|--------|------|------|---------|-----------|------------|---------|-------|------|
| CMP-001 | 資料刪除 | Art.17 | — | A.8.3 | NFR-COMP-001 | 已實作 | TC-COMP-001 | API /user DELETE |
| CMP-002 | 資料加密 | Art.32 | Req.3 | A.10.1 | NFR-COMP-003 | 已實作 | TC-COMP-003 | AES-256 配置 |
| CMP-003 | 存取日誌 | Art.30 | Req.10 | A.9.4 | NFR-COMP-004 | 進行中 | TC-COMP-004 | Audit Log 設計 |
```

---

### 階段 3：合規缺口分析

依各標準執行缺口分析，對照 FRD NFR-COMP 清單：

**GDPR 關鍵確認點**：
- [ ] Art.15 資料主體存取權（對應 NFR-COMP-XXX）
- [ ] Art.17 刪除權（對應 NFR-COMP-XXX）
- [ ] Art.20 資料可攜權（對應 NFR-COMP-XXX）
- [ ] Art.32 安全措施（對應 STRIDE SAD）
- [ ] 同意管理記錄（對應 FRD 同意功能需求）

**PCI-DSS 關鍵確認點**：
- [ ] Req.3 PAN 不明文儲存（對應 NFR-COMP-XXX）
- [ ] Req.6 漏洞管理（對應 security-audit 結果）
- [ ] Req.10 存取日誌（對應 NFR-COMP-XXX）
- [ ] Req.12 資訊安全政策文件

---

### 階段 4：合規審查報告產出

**文件路徑**：`docs/06_quality/security/COMPLIANCE-AUDIT-REPORT-{SystemName}-{date}.md`

```markdown
# 合規審查報告 — {SystemName}

**審查日期**: {YYYY-MM-DD}
**審查標準**: {標準清單}
**FRD 合規需求**: {NFR-COMP 總數} 項
**整體合規率**: {X}%（對應 RTM TC 通過率）

## 缺口摘要

### P0 - 關鍵缺口（阻擋 SCG-5）
| CMP ID | NFR-COMP | 條款 | 現狀 | 缺口 | RTM TC | 修復負責人 |
|--------|---------|------|------|------|--------|----------|

### P1 - 高優先（SCG-5 前修復）
| CMP ID | NFR-COMP | 條款 | 現狀 | 缺口 | RTM TC | 目標日期 |
|--------|---------|------|------|------|--------|---------|

## RTM 覆蓋率（合規 TC）
- NFR-COMP 總數: {N}
- 有 TC 覆蓋: {N}（應達 100%）
- TC 通過: {N}

## SCG-5 合規閘門結論
- [ ] 所有 P0 缺口已修復
- [ ] RTM 合規 TC 100% 覆蓋
- [ ] Compliance Matrix 已完成
- → SCG-5 合規部分: **Pass / Fail**
```

---

### 階段 5：RTM 更新與 SCG-5 準備 🔴

```bash
/rtm-generate update    # 更新合規 TC 狀態（TC-COMP-XXX）
/spec-compliance-check docs/06_quality/security/COMPLIANCE-MATRIX-{System}.md
/sdd-gate SCG-5         # 提交合規驗證證據
```

🔴 確認點：P0 缺口修復後，Compliance Matrix 100% 覆蓋，才可執行 SCG-5。

---

## 強制產出（SDD 文件）

| 產出物 | 路徑 | 對應 SCG |
|--------|------|---------|
| Compliance Matrix | `docs/06_quality/security/COMPLIANCE-MATRIX-{System}.md` | SCG-5 前 |
| 合規審查報告 | `docs/06_quality/security/COMPLIANCE-AUDIT-REPORT-{System}.md` | SCG-5 |

---

## 後置動作

```
/rtm-generate verify    # 確認合規 TC 全部通過
/sdd-gate SCG-5         # 合規通過後提交閘門
```

🔷 **本 Skill 協助通過**：SCG-5（合規驗收）

---

## 相關 Skill

- `/security-audit` — STRIDE 威脅模型（合規的安全基礎）
- `/sa-analyst` — FRD NFR-COMP 定義（合規需求的規格依據）
- `/rtm-generate` — 合規 TC 追蹤
- `/sdd-gate SCG-5` — 交付閘門（合規為必要條件）

---

**基於**: AISDLC-SDD v0.25
**對應 CI/CD 規格**: `cicd/SDD_SECURITY_CICD.md`
**SDD Enhancement**: `scenarios/security/SDD_SECURITY_ENHANCEMENT.md`
