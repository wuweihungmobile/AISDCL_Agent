---
name: sdd-gate
description: 執行 SDD Spec-First Gate（SCG）閘門驗證，確認規格文件完整後才允許進入下一階段
user-invocable: true
disable-model-invocation: false
argument-hint: "<gate: SCG-0|SCG-1|SCG-2|SCG-3|SCG-4|SCG-5|SCG-6>"
allowed-tools:
  - Read
  - Grep
  - Glob
---

# SDD Gate Skill（SDD 原生）

SDD 三大支柱之 **Spec-First Gate**：每個關鍵里程碑前的強制閘門驗證。本 Skill 是所有 Agent Skill 的入口守衛，確保「規格先於實作」原則不被繞過。

---

## 觸發方式

```bash
/sdd-gate SCG-0    # 需求凍結前驗證
/sdd-gate SCG-1    # 設計凍結前驗證
/sdd-gate SCG-2    # 架構凍結前驗證
/sdd-gate SCG-3    # API Contract 凍結前驗證
/sdd-gate SCG-4    # PR Review（實作與規格一致性）
/sdd-gate SCG-5    # 交付前（RTM 100%）
/sdd-gate SCG-6    # 發布前（全閘門通過）
```

---

## 前置條件（SDD Spec-First）

> 本 Skill 本身是所有其他 Skill 的前置條件，無需 SCG 前置。

---

## 閘門定義與 Skill 引用鏈

| Gate | 名稱 | 進入條件 | 必要文件 | **需要以下 Skill 產出** | 主責 Agent |
|------|------|---------|---------|----------------------|-----------|
| 🔷 SCG-0 | Requirement Spec Gate | 需求凍結前 | PRD + FRD ≥ 95% | `/sa-analyze` + `/ba-validate` | sa-analyst |
| 🔷 SCG-1 | Architecture Spec Gate | 設計凍結前 | SRD + API Spec 草稿 | `/sd-design` | sd-architect |
| 🔷 SCG-2 | Architecture Freeze Gate | 架構凍結前 | C4 圖 + ADR | `/sd-design` + `/adr-generate` | sd-architect |
| 🔷 SCG-3 | API Contract Freeze | 開發啟動前 | OpenAPI 3.1 + Consumer Contract | `/contract-generate` | sd-architect |
| 🔷 SCG-4 | Implementation Review | PR Review | 實作與規格一致性 + 測試通過 | `/dev-review` + `/qa-testing` | qa-tester |
| 🔷 SCG-5 | Delivery Gate | 交付前 | RTM 100% 覆蓋 + 所有測試通過 | `/rtm-generate verify` + `/qa-testing` | qa-tester |
| 🔷 SCG-6 | Release Gate | 發布前 | SCG-0~5 全通過 | `/release-management` | 首席架構師 |

---

## 執行流程

### 階段 1：收集驗證素材

依指定 Gate 讀取對應文件：

```
SCG-0 → docs/01_requirements/PRD-*.md + FRD-*.md
SCG-1 → docs/02_architecture/SRD-*.md
SCG-2 → docs/02_architecture/C4-*.md + adr/ADR-*.md
SCG-3 → docs/02_architecture/api/CONTRACT-*.yaml
SCG-4 → 程式碼變更（git diff）+ docs/02_architecture/api/
SCG-5 → docs/03_testing/RTM-*.md
SCG-6 → 所有 SCG-0~5 驗證報告
```

---

### 階段 2：逐項驗證

#### 🔷 SCG-0：需求凍結
```
- [ ] PRD 版本已鎖定（Status: Approved）
- [ ] FRD 覆蓋所有 PRD 功能項目（F-XXX 追溯）
- [ ] NFR 已量化定義（效能 P99、安全等級、可用性 SLA）
- [ ] User Story 已完成 INVEST 原則檢查
- [ ] 利害關係人已確認簽核
- [ ] RTM 初版已建立（/rtm-generate 已執行）
```

#### 🔷 SCG-1：設計凍結
```
- [ ] SRD 完成並通過 Review（Status: Approved）
- [ ] API Spec 草稿完成（所有端點清單）
- [ ] 資料模型設計完成
- [ ] NFR 設計對應完成（架構選型對應 NFR 指標）
- [ ] 整合架構說明完整（第三方服務已識別）
```

#### 🔷 SCG-2：架構凍結
```
- [ ] C4 Context 圖完成（系統邊界清晰）
- [ ] C4 Container 圖完成（主要組件識別）
- [ ] 所有架構決策有對應 ADR（Status: Accepted）
- [ ] Trust Boundary Map 完成（Security 情境）
- [ ] Before/After 架構對比（Brownfield/Refactoring 情境）
```

#### 🔷 SCG-3：Contract Freeze
```
- [ ] OpenAPI 3.1 規格完整（所有端點含完整 Schema）
- [ ] Request/Response Schema 定義完整
- [ ] 錯誤碼定義（400/401/403/404/500）
- [ ] Consumer Contract 完成（整合情境）
- [ ] API ID 與 RTM 已對應
- [ ] Contract 已 Review 通過
```

#### 🔷 SCG-4：實作 Review
```
- [ ] 程式碼實作符合 SRD 規格
- [ ] API 實作符合 Contract（端點/格式一致）
- [ ] 單元測試覆蓋率 ≥ 80%
- [ ] 無 Critical/High Security 漏洞
- [ ] Business Invariants 未被破壞（Refactoring 情境）
```

#### 🔷 SCG-5：交付閘門
```
- [ ] RTM 追溯覆蓋率 = 100%（/rtm-generate verify 通過）
- [ ] 所有 AC 對應測試案例並通過
- [ ] 整合測試通過
- [ ] 效能基準（PBS）驗證通過（Performance 情境）
- [ ] /spec-compliance-check 全部通過
```

#### 🔷 SCG-6：發布閘門
```
- [ ] SCG-0 ~ SCG-5 全部通過（附驗證報告）
- [ ] Release Notes 撰寫完成
- [ ] 運維文件（Runbook）完成
- [ ] 回滾計畫就緒
- [ ] STRIDE 威脅模型已執行（/security-audit）
```

---

### 階段 3：產出驗證報告 🔴

```markdown
## 🔷 SCG-{N} 驗證報告

**閘門**: SCG-{N}（{名稱}）
**日期**: {YYYY-MM-DD}
**系統**: {SystemName}
**執行者**: {Agent/人工}

### 通過項目 ✅
- [x] 項目 1

### 未通過項目 ❌
- [ ] 缺少 ADR-003（技術棧選型未記錄）
- [ ] OpenAPI 端點 POST /orders 缺少 401 錯誤碼

### 結論
🔴 未通過 / 🟢 通過

### 下一步
{修正項目清單 or 可進入下一階段}
```

🔴 **人工確認點**：閘門通過需等待負責人明確確認，不可自動通過。

---

## 強制產出（SDD 文件）

| 產出物 | 路徑 | 說明 |
|--------|------|------|
| SCG 驗證報告 | `docs/03_testing/SCG-{N}-REPORT-{System}.md` | 每次執行必產出 |

---

## 後置動作

| Gate | 通過後執行 |
|------|-----------|
| SCG-0 通過 | `/sd-design` 開始架構設計 |
| SCG-1 通過 | `/adr-generate` + `/contract-generate` |
| SCG-2 通過 | `/contract-generate openapi` → SCG-3 |
| SCG-3 通過 | 開發啟動（`/devops-github-actions` 或 `/integration-*`） |
| SCG-4 通過 | `/rtm-generate verify` → SCG-5 |
| SCG-5 通過 | `/release-management` → SCG-6 |
| SCG-6 通過 | 發布 |

🔷 **本 Skill 是所有後續 Skill 的守門員**

---

## 相關 Skill

- `/spec-compliance-check` — 文件符合性驗證（SCG 的自動驗證子任務）
- `/adr-generate` — 補建缺少的 ADR（SCG-2 常見修正）
- `/contract-generate` — 建立缺少的 Contract（SCG-3 前置）
- `/rtm-generate` — 建立/更新 RTM（SCG-0/SCG-5 必要）

---

**基於**: AISDLC-SDD v0.01（SDD 專屬 Skill）
**對應 SDD 原則**: Spec-First Gate（所有 SCG 閘門）
**對應工作流**: `workflow/sdd-spec-first-gate/SDD_SPEC_FIRST_GATE.md`
