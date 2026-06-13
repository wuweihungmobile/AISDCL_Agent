# SDD Agentic 中止報告模板
# SDD Abort Report Template

**模板版本**: v1.0
**建立日期**: 2026-04-18
**使用說明**: 當 FSM 進入 ESCALATION 或 TERMINATED 狀態時，從此模板複製並填寫
**產出路徑**: `build/reports/abort/ABORT-{date}-{reason-slug}.md`

---

# SDD Abort Report

**報告編號**: ABORT-{YYYY-MM-DD}-{reason-slug}
**建立時間**: {YYYY-MM-DD HH:MM}
**專案**: {System Name}
**情境**: {greenfield / brownfield / refactoring / ...}
**觸發來源**: {觸發 ESCALATION 的 FSM 狀態}

---

## 🚨 中止原因

**觸發條件**: {選擇一項}
- [ ] SCG 驗證失敗超過重試上限（retry_count ≥ N）
- [ ] PR Review 失敗超過重試上限（retry_count ≥ 5）
- [ ] SPEC_AUDIT 確認邏輯矛盾
- [ ] HUMAN_PENDING 逾時（> 168h）
- [ ] Token Budget 耗盡（> 95%）
- [ ] 其他：{描述}

**根本原因分析**:
```
{詳細描述根本原因，例如：
 "AC-003-1 定義了物理不可能的效能目標（0ms），通過了 SCG 格式驗證，
  但在 PR Review 時導致測試永遠無法通過。"}
```

**嚴重程度**: 🔴 HIGH / 🟡 MEDIUM / ⚪ LOW

---

## 📍 當前 FSM 狀態

| 項目 | 值 |
|------|---|
| FSM 狀態 | {ESCALATION / TERMINATED} |
| 觸發前狀態 | {PR_REVIEW / SCG_VALIDATION / ...} |
| Stage | Stage {N} — {Stage Name} |
| SCG 進度 | {SCG-N 通過，SCG-M 未開始} |
| retry_count | SCG: {N}次，PR: {N}次 |
| 異常模式 | {描述重複失敗的模式，如有} |

---

## 🔍 已嘗試的解決方案

| 嘗試次數 | 解決方案 | 結果 | 失敗原因 |
|---------|---------|------|---------|
| #1 | {描述} | ❌ 失敗 | {原因} |
| #2 | {描述} | ❌ 失敗 | {原因} |
| #3 | {描述} | ❌ 失敗 | {原因} |

---

## 📂 已完成文件（可恢復資產）

| 文件 | 路徑 | 狀態 |
|------|------|------|
| PRD | docs/01_requirements/PRD-{system}.md | ✅ FROZEN |
| FRD | docs/01_requirements/FRD-{system}.md | {狀態} |
| SRD | docs/02_architecture/SRD-{system}.md | {狀態} |
| RTM | docs/03_testing/RTM-{system}.md | {狀態} |
| ADR Index | docs/02_architecture/adr/ADR-INDEX.md | {狀態} |
| {其他} | {路徑} | {狀態} |

---

## 🔙 可恢復點

| 恢復點 | 描述 | 所需修復 |
|--------|------|---------|
| **建議恢復點** | {Stage N SPEC_FROZEN} | {描述需要修復的內容} |
| 替代恢復點 | {Stage M SPEC_FROZEN} | {更大範圍的修復} |

---

## 👤 建議人工行動

**主要行動**:
```
1. {具體行動 1，例如：sa-analyst 重新審查 FRD AC-003-1，修正效能目標數值}
2. {具體行動 2}
3. {具體行動 3}
```

**通知對象**:
- {角色}: {通知原因}

**預估修復時間**: {如可評估}

---

## 🔄 恢復指引

修復完成後，在新 conversation 中執行：

```
1. 讀取 AISDLC_SDD_INIT.md
2. 讀取此 Abort Report
3. 讀取恢復點的 Stage Summary（build/reports/compaction/COMPACT-Stage{N}-{date}.md）
4. 從 {RESUME_STATE} 狀態繼續
5. 執行 /spec-logical-validator 確認問題已修復
6. 繼續 {下一步操作}
```

---

## 📊 資源消耗摘要

| 項目 | 數量 |
|------|------|
| 估計 Token 消耗 | ~{N}K tokens |
| 迭代次數 | {N} 次 SCG/PR 嘗試 |
| 耗費時間 | {N} 小時（估算） |
| 已完成文件 | {N} 個 |

---

**報告建立者**: SDD Agentic System（自動生成）
**需要人工確認**: ✅ 是（ESCALATION 不可自動退出）
