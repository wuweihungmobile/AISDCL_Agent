---
name: sdd-review
description: SDD 規格視角 SCG-4 主審 — 正式裁決實作與規格一致性（Code vs Contract vs FRD vs Invariant），SCG-4（Implementation Review Gate）正式閘門主責。【何時用哪個】PR 後正式 SCG-4 規格一致性裁決用本 skill；提交 commit/PR 前的開發者輕量自審用 /dev-review；通用程式品質（可讀性/重複/效能/壞味道，不綁 SCG-4）用 /code-review。
user-invocable: true
disable-model-invocation: false
argument-hint: "[review_type: full|spec|contract|invariant] [pr_path: <PR描述或diff路徑>]"
allowed-tools:
  - Read
  - Write
  - Grep
  - Glob
---

# SDD 規格一致性審查 Skill（SCG-4 主審）

本 Skill 是 **SCG-4（Implementation Review Gate）的正式主審**，在 PR Review 時執行，從 SDD 規格視角**正式裁決實作是否符合規格**。核心任務：確認代碼變更與凍結的 FRD、OpenAPI Contract、Business Invariants 一致，是 SCG-4 閘門通過與否的權威依據。**與另兩支 review skill 分工互斥**：提交前的開發者輕量自審見 `/dev-review`（事前準備、不裁決）；通用程式品質（可讀性/重複/效能/壞味道，不綁 SCG-4）見 `/code-review`。

---

## 觸發方式

```bash
/sdd-review                        # 完整 SCG-4 審查
/sdd-review spec                   # 僅驗證 FRD/SRD 規格一致性
/sdd-review contract               # 僅驗證 OpenAPI Contract 一致性
/sdd-review invariant              # 僅驗證 Business Invariants（Refactoring 情境）
```

---

## 前置條件（SCG-4）

| 必要文件 | 說明 |
|---------|------|
| `docs/01_requirements/FRD-{System}.md` | 功能需求規格（AC-XXX-Y 清單） |
| `docs/02_architecture/api/CONTRACT-{Module}-v{N}.yaml` | 已凍結的 OpenAPI 3.1 Contract（SCG-3） |
| `docs/03_testing/RTM-{System}.md` | 需求追蹤矩陣 |
| Refactoring 情境：`docs/01_requirements/INVARIANT-SPEC-{System}.md` | Business Invariants |

---

## 執行流程

### 階段 1：讀取規格基線

```
讀取 docs/01_requirements/FRD-{System}.md
讀取 docs/02_architecture/api/CONTRACT-*.yaml（若存在）
讀取 docs/01_requirements/INVARIANT-SPEC-*.md（Refactoring 情境）
```

### 階段 2：實作規格對照

產出結構化比對報告：

```markdown
## SCG-4 PR Review 報告 — {PR 標題}

**審查日期**: {YYYY-MM-DD}
**審查範圍**: {功能/模組名稱}
**基準規格**: FRD-{System} + CONTRACT-{Module}-v{N}

### A. FRD 功能規格一致性

| AC-ID | 驗收標準 | 實作狀態 | 結論 |
|-------|---------|---------|------|
| AC-001-1 | {Given-When-Then} | {已實作/未實作/偏差} | Pass/Fail |
| AC-001-2 | {Given-When-Then} | {已實作/未實作/偏差} | Pass/Fail |

### B. OpenAPI Contract 一致性（SCG-3 凍結版本）

| API-ID | Contract 定義 | 實作 | 結論 |
|--------|-------------|------|------|
| API-001 | POST /{resource} → 200/400/401 | {實作行為} | Pass/Fail |

### C. Business Invariants 保護（Refactoring 情境）

| INV-ID | 不變量描述 | 測試保護 | 結論 |
|--------|-----------|---------|------|
| INV-001 | {業務約束} | {測試覆蓋方式} | Pass/Fail |

### D. RTM 覆蓋率確認

- 本 PR 涉及 AC：{清單}
- 已有 TC 覆蓋：{已覆蓋 AC}
- 缺少 TC 覆蓋：{未覆蓋 AC}（需補充）

### 審查結論

| 項目 | 狀態 |
|------|------|
| FRD 功能規格 | Pass / Fail（{N} 項不符） |
| Contract 一致性 | Pass / Fail（{N} 項偏差） |
| Invariants 保護 | Pass / N/A |
| RTM 覆蓋率 | {N}%（要求 100%） |

**SCG-4 建議**: [通過] / [需修正後再審查]

### 必修項目（Fail 項）
| 編號 | 問題 | 需修正內容 | 對應規格 |
|------|------|---------|---------|
| 1 | {問題描述} | {修正方向} | AC-{XXX-Y} |
```

---

### 階段 3：確認點 🔴

審查報告產出後，必須由人工確認：
- [ ] 所有 Fail 項已明確標注
- [ ] 修正項目有對應規格引用
- [ ] 若有 Contract 偏差：需確認是否需要 SCG-3 重新凍結

🔴 **確認點**：SCG-4 Pass 需全部 AC 一致性確認 + RTM 無空缺。

---

## 強制產出

| 產出物 | 路徑 | 對應 SCG |
|--------|------|---------|
| SCG-4 PR Review 報告 | `docs/03_testing/SCG4-REVIEW-{Feature}-{YYYYMMDD}.md` | SCG-4 |

---

## 🔄 FSM 整合：Retry Budget 追蹤

本 Skill 的每次執行與 `/sdd-gate SCG-4` 的 **PR_REVIEW retry_count** 直接連動。

```
[sdd-review 執行結果] → [影響 sdd-gate SCG-4 retry_count]

失敗時（有任何 Fail 項）：
  → retry_count++（由 sdd-gate 追蹤）
  → 修正後重新執行 /sdd-review

連續相同失敗 × 3 次：
  → sdd-gate 偵測到 failure_pattern_hash 相符
  → 自動進入 SPEC_AUDIT 狀態
  → 停止 PR Review 迴圈，深查 AC vs Test Contract 矛盾

retry_count ≥ 5 次：
  → sdd-gate 宣告 ESCALATION
  → 停止所有開發，等待人工介入
```

**重要**：不得在 retry_count 耗盡前繞過 /sdd-gate 強行合併 PR。

相關文件：[SDD_FSM_ENGINE.md](../../../workflow/sdd-fsm-engine/SDD_FSM_ENGINE.md) | [SDD_ESCALATION_PROTOCOL.md](../../../workflow/sdd-escalation/SDD_ESCALATION_PROTOCOL.md)

---

## 後置動作

```bash
# 若全部 Pass：
/sdd-gate SCG-4    # 執行 SCG-4 閘門確認（通過後 retry_count 重置）

# 若有 Fail：
# 退回開發修正後，重新執行 /sdd-review
# ⚠️ 每次 Fail 累積至 /sdd-gate SCG-4 的 retry_count（上限 5 次）
# ⚠️ 相同失敗模式出現 3 次 → 系統自動觸發 SPEC_AUDIT（見 SDD_FSM_ENGINE.md）
```

---

## 相關 Skill（何時用哪個）

- `/dev-review` — **提交 commit/PR 前的開發者輕量自審**（事前準備，不做 SCG-4 裁決）
- `/code-review` — **通用程式品質審查**（可讀性/重複/效能/壞味道，不綁 SCG-4）
- `/sdd-gate SCG-4` — Implementation Review Gate
- `/rtm-generate verify` — RTM 覆蓋率確認
- `/spec-compliance-check` — 規格合規性檢查
- `/contract-generate` — 若需重新凍結 Contract

---

**基於**: AISDLC-SDD v0.27
**對應 Agent**: `07.qa-tester-zh.yaml`（主審）、`dev-senior-zh.yaml`（協同）
**對應 SCG 閘門**: SCG-4（Implementation Review Gate）
