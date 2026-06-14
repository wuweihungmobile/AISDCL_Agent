# 重構計畫（即規格）
# Refactoring Plan as Specification

**專案**: {PROJECT_NAME}
**系統**: {SYSTEM_NAME}
**版本**: v1.0
**建立日期**: YYYY-MM-DD
**建立者**: sd-architect + dev-senior
**適用情境**: Refactoring（Stage 3 強制文件）

---

## SDD 原則聲明

> **重構計畫本身即是規格文件。**
> 每個 STEP 必須是「原子操作」——單一職責，可獨立驗證，有 Rollback Plan。
> 違反不變量測試 → 立即 Rollback，禁止繼續。

---

## 重構概覽

| 項目 | 說明 |
|------|------|
| 重構目標 | {為什麼要重構，解決什麼問題} |
| 重構策略 | Strangler Fig / Branch by Abstraction / Parallel Run / Big Bang |
| 選擇理由 | {為什麼選擇此策略} |
| Before Architecture | `docs/02_architecture/BEFORE-ARCH-{system}.md` |
| After Architecture | `docs/02_architecture/AFTER-ARCH-{system}.md` |
| Business Invariants | `docs/01_requirements/INVARIANT-SPEC-{system}.md` |
| 預估總 SP | {N} SP |
| 預估工期 | {N} Sprint |

---

## 里程碑規劃

| 里程碑 | 包含 STEP | 完成標準 |
|-------|---------|---------|
| Milestone 1：{名稱} | STEP-001 ~ STEP-005 | 所有 INV 測試通過 + Human 確認 |
| Milestone 2：{名稱} | STEP-006 ~ STEP-010 | 所有 INV 測試通過 + Human 確認 |
| Final：驗收 | 整體驗收 | After Baseline 達標 + 全回歸通過 |

---

## 詳細重構步驟

### STEP-001：{步驟名稱}

**描述**: {此步驟做什麼，一件事}  
**原子性確認**: ✅（單一職責）  
**預估 SP**: {N}

**Before State**:
```
{執行前的系統狀態描述}
```

**After State**:
```
{執行後的系統狀態描述}
```

**實作指引**:
1. {具體操作步驟 1}
2. {具體操作步驟 2}

**後置驗證**:
```bash
# 執行不變量測試（必須 100% 通過才能繼續）
npm run test:invariants

# 執行單元測試
npm test

# 驗證 Build 通過
npm run build
```

**不變量測試清單**（此步驟後必須通過）:
- INV-001: {不變量名稱}
- INV-002: {不變量名稱}

**Rollback Plan**:
```bash
# 若此步驟失敗，執行以下回滾操作
git revert HEAD
# 或
git checkout {branch-before-step}
```

**Rollback 觸發條件**:
- 任何 INV 測試失敗
- Build 失敗
- {其他失敗條件}

---

### STEP-002：{步驟名稱}

（同上格式）

---

### STEP-003：{步驟名稱}

（同上格式）

---

## 每個步驟完成記錄

| STEP | 完成日期 | INV 測試 | Commit Hash | 備註 |
|------|---------|---------|-------------|------|
| STEP-001 | YYYY-MM-DD | 100% ✅ | `{hash}` | |
| STEP-002 | YYYY-MM-DD | 100% ✅ | `{hash}` | |
| STEP-003 | (未開始) | - | - | |

---

## 風險管理

| 風險 | 可能性 | 影響 | 緩解措施 |
|------|-------|------|---------|
| INV 測試漏網之魚 | 中 | 高 | Mutation Test 在里程碑時補強 |
| Strangler Fig 並行期過長 | 中 | 中 | 設定最長並行期限（{N} Sprint）|
| 依賴模組不配合替換 | 低 | 高 | 提前識別，Branch by Abstraction |

---

## 🔴 Human 確認

**確認日期**: YYYY-MM-DD  
**確認者**: {Product Owner / Tech Lead}

- [ ] 重構目標明確，符合業務需求
- [ ] 重構策略選擇合理
- [ ] 每個 STEP 都是原子操作
- [ ] Rollback Plan 已確認
- [ ] 里程碑時間點可接受

---

**相關文件**:
- [Before Architecture](../../docs/02_architecture/BEFORE-ARCH-{system}.md)
- [After Architecture](../../docs/02_architecture/AFTER-ARCH-{system}.md)
- [業務不變量規格](../../docs/01_requirements/INVARIANT-SPEC-{system}.md)
- [Invariant Test Contract](../../docs/03_testing/contracts/INVARIANT-TEST-CONTRACT.md)
