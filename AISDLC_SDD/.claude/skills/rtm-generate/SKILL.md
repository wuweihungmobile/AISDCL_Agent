---
name: rtm-generate
description: 生成或更新需求追溯矩陣（RTM），建立從業務需求到測試案例的完整追溯鏈，確保 SCG-5 100% 覆蓋
user-invocable: true
disable-model-invocation: false
argument-hint: "[scope: full|update|verify] [feature: 功能範圍或 FRD 路徑]"
allowed-tools:
  - Read
  - Write
  - Grep
  - Glob
---

# RTM 生成 Skill（SDD 原生）

SDD 三大支柱之 **Spec-First Gate**：建立從業務需求到測試案例的完整追溯鏈。本 Skill 在 SDD 工作流中被多個 Agent Skill 呼叫，確保每個階段的產出都被追溯。

---

## 觸發方式

```bash
/rtm-generate                    # 生成完整 RTM（首次）
/rtm-generate update             # 更新現有 RTM（新增需求或 API 後）
/rtm-generate verify             # 驗證 RTM 完整性（SCG-5 前執行）
/rtm-generate "訂單功能"         # 針對特定功能生成 RTM 片段
```

---

## 前置條件（SDD Spec-First）

> RTM 在不同階段有不同前置條件：

| 執行時機 | 前置條件 | 說明 |
|---------|---------|------|
| 初版建立（full） | FRD 已完成 | `/sa-analyst` 產出後 |
| 加入 API 追溯（update） | SCG-3 通過（Contract 凍結） | `/contract-generate` 產出後 |
| 加入 TC 追溯（update） | 測試計畫完成 | `/qa-testing` 產出後 |
| 覆蓋率驗證（verify） | 所有上述追溯已完成 | SCG-5 前執行 |

---

## 執行流程

### 階段 1：收集來源文件

依執行範圍讀取：

```
full/update → 讀取以下所有存在的文件:
  docs/01_requirements/FRD-{System}.md       ← F-XXX, NFR-XXX, US-XXX, AC-XXX-Y
  docs/01_requirements/PRD-{System}.md       ← EPIC（業務目標）
  docs/02_architecture/SRD-{System}.md       ← API-XXX 對應
  docs/02_architecture/api/CONTRACT-*.yaml   ← API 端點清單
  docs/03_testing/TEST-PLAN-{System}.md      ← TC-XXX-Y-Z

verify → 讀取 docs/03_testing/RTM-{System}.md 進行覆蓋率計算
```

---

### 階段 2：建立/更新追溯條目

對每個功能建立完整追溯鏈：

```
EPIC-XXX（業務目標）
  └── F-XXX（功能需求，來自 FRD）
        └── US-XXX（使用者故事）
              └── AC-XXX-Y（驗收標準，Given-When-Then）
                    └── TC-XXX-Y-Z（測試案例）
                          ├── API-XXX（對應 API 端點，SCG-3 後填入）
                          └── NFR-XXX（關聯的非功能需求）
```

**ID 分配規則**：
- EPIC：`EPIC-001`、`EPIC-002`（業務史詩）
- Feature：`F-001`、`F-002`（功能需求，來自 FRD）
- User Story：`US-001`、`US-002`（一個 Feature 可有多個 US）
- Acceptance Criteria：`AC-001-1`、`AC-001-2`（第一個數字為 US 序號）
- Test Case：`TC-001-1-1`（格式：TC-{US}-{AC}-{序號}）
- API：`API-001`（對應 Contract 中的端點）
- NFR：`NFR-001`（非功能需求）

---

### 階段 3：RTM 格式產出

```markdown
# RTM - {SystemName}

**版本**: {N}.{N}
**日期**: {YYYY-MM-DD}
**狀態**: Draft → In Review → Approved
**覆蓋率**: {N}/{Total} AC（{百分比}%）

## 追溯矩陣

| EPIC | Feature | User Story | AC | Test Case | API | NFR | 狀態 |
|------|---------|-----------|-----|-----------|-----|-----|------|
| EPIC-001 | F-001 | US-001 | AC-001-1 | TC-001-1-1 | API-001 | NFR-001 | ✅ |
| EPIC-001 | F-001 | US-001 | AC-001-2 | TC-001-2-1 | API-001 | - | ✅ |
| EPIC-001 | F-002 | US-002 | AC-002-1 | 🔄 待測試 | API-002 | NFR-002 | 🔄 |

## 覆蓋率統計

| 指標 | 數值 |
|------|------|
| 總 Feature 數 | {N} |
| 總 AC 數 | {N} |
| 有 TC 的 AC 數 | {N} |
| **覆蓋率** | **{N}%** |
| SCG-5 目標 | 100% |
```

---

### 階段 4：覆蓋率驗證（verify 模式）

計算 RTM 覆蓋率：
```
覆蓋率 = 有 TC-XXX-Y-Z 對應的 AC 數 / 總 AC 數 × 100%
目標：100%（SCG-5 強制通過條件）
```

若覆蓋率 < 100%，輸出缺口清單：
```markdown
### 未覆蓋 AC 清單（需補測試案例）
- AC-003-2: US-003「使用者登出」→ 缺少對應 TC
- AC-005-1: US-005「密碼重設」→ 缺少對應 TC
```

---

### 階段 5：存檔 🔴

1. 存放路徑：`docs/03_testing/RTM-{SystemName}.md`
2. 執行 `/spec-compliance-check docs/03_testing/RTM-{SystemName}.md`
3. 🔴 確認點：核對追溯矩陣與 FRD/Test Plan 的一致性

---

## 強制產出（SDD 文件）

| 產出物 | 路徑 | 對應 SCG |
|--------|------|---------|
| RTM 文件（初版） | `docs/03_testing/RTM-{SystemName}.md` | SCG-0 後建立 |
| RTM 文件（含 API） | 同上（更新） | SCG-3 後更新 |
| RTM 文件（含 TC） | 同上（更新） | SCG-4 後更新 |
| RTM 驗證報告 | `docs/03_testing/RTM-VERIFY-{SystemName}.md` | SCG-5 前 |

---

## 後置動作

```
/spec-compliance-check docs/03_testing/RTM-{SystemName}.md
```

**各階段後置動作**：
- `full` 完成後 → 通知 `/sa-analyst` RTM 初版已建立
- `update`（API）後 → 通知 `/qa-testing` 可開始補 TC
- `verify` 通過（100%）→ `/sdd-gate SCG-5`

🔷 **本 Skill 協助通過**：SCG-5（Delivery Gate）

---

## 被以下 Skill 呼叫

| Skill | 呼叫時機 | 說明 |
|-------|---------|------|
| `/sa-analyst` | FRD 完成後 | 建立 RTM 初版 |
| `/sd-architect` | SRD 完成後 | 更新 API 追溯 |
| `/contract-generate` | Contract 凍結後 | 確認 API-XXX 對應 |
| `/qa-testing` | 測試計畫完成後 | 填入 TC-XXX-Y-Z |
| `/dev-review` | PR 通過後 | 更新 Status 為 ✅ |

---

## 相關 Skill

- `/sa-analyst` — 需求分析（RTM 來源文件）
- `/qa-testing` — 測試案例（RTM 目標文件）
- `/spec-compliance-check` — 驗證 RTM 格式與覆蓋率
- `/sdd-gate SCG-5` — 使用 RTM 100% 作為交付閘門條件

---

**基於**: AISDLC-SDD v0.01（SDD 專屬 Skill）
**對應 SDD 原則**: Spec-First Gate（SCG-5 100% RTM 覆蓋）
**對應範本**: `docs_template/sdd/testing/RTM-TEMPLATE.md`
