# Living Test Report — Template
# 測試報告格式規格（Living Document）
# Phase 05 — Testing 情境 SDD 強化

**文件類型**: Living Test Report (LTR)
**SDD 特性**: Living Document — 每次 CI 執行後自動更新
**存放位置**: `docs/03_testing/LIVING-TEST-REPORT-{project}.md`
**自動更新**: CI Pipeline → RTM Coverage Report Generator

---

## 文件資訊

| 欄位 | 說明 |
|------|------|
| **專案名稱** | {ProjectName} |
| **報告版本** | 自動遞增（CI Build #） |
| **最後更新** | {自動填入：CI 執行時間} |
| **CI Build** | #{build_number} |
| **Git Commit** | {commit_sha} |
| **測試環境** | {env} |

---

## 1. 品質儀表板（Quality Dashboard）

### 1.1 覆蓋率摘要

| 指標 | 目標 | 實際值 | 狀態 |
|-----|------|--------|------|
| Line Coverage | ≥ 80% | {X}% | ✅/❌ |
| Branch Coverage | ≥ 75% | {X}% | ✅/❌ |
| AC → AT 映射覆蓋 | 100% | {X}% | ✅/❌ |
| E2E 關鍵旅程覆蓋 | 100% | {X}% | ✅/❌ |
| Contract 覆蓋 | 100% | {X}% | ✅/❌ |

### 1.2 測試執行摘要

| 測試層 | 總數 | 通過 | 失敗 | 跳過 | 通過率 |
|-------|------|------|------|------|-------|
| Unit | {N} | {N} | {N} | {N} | {X}% |
| Integration | {N} | {N} | {N} | {N} | {X}% |
| Contract | {N} | {N} | {N} | {N} | {X}% |
| E2E | {N} | {N} | {N} | {N} | {X}% |
| Security (SAST) | {N} | {N} | {N} | — | {X}% |
| **Total** | **{N}** | **{N}** | **{N}** | **{N}** | **{X}%** |

### 1.3 Quality Gate 結果

| Gate | 檢查項目 | 結果 |
|------|---------|------|
| Coverage Gate | Line ≥ 80% | ✅ PASS / ❌ FAIL |
| Contract Gate | Zero Violations | ✅ PASS / ❌ FAIL |
| Security Gate | No High/Critical | ✅ PASS / ❌ FAIL |
| RTM Gate | AC→AT 100% | ✅ PASS / ❌ FAIL |
| **Overall Gate** | **All PASS** | **✅ / ❌** |

---

## 2. RTM 覆蓋率報告（自動生成）

| EPIC | Feature | US | AC 數 | AT 數 | 通過 | 失敗 | 覆蓋率 |
|------|---------|-----|-------|-------|------|------|-------|
| EPIC-001 | F-001 | US-001 | 3 | 6 | 6 | 0 | 100% |
| EPIC-001 | F-002 | US-002 | 2 | 4 | 3 | 1 | 75% |
| **合計** | | | {N} | {N} | {N} | {N} | **{X}%** |

### 2.1 未覆蓋 AC 清單（需立即補充 AT）

| AC ID | AC 描述 | Feature | 負責 QA | 截止日期 |
|-------|---------|---------|---------|---------|
| AC-{NNN} | {description} | F-{NNN} | {name} | {date} |

---

## 3. 失敗測試詳情

### 3.1 當前失敗測試

| 測試 ID | 測試名稱 | 層次 | 失敗原因摘要 | 缺陷 ID | 狀態 |
|--------|---------|------|------------|---------|------|
| AT-{NNN} | {test name} | Unit | {reason} | BUG-{NNN} | 修復中 |

### 3.2 Contract 違反記錄

| Consumer | Provider | Interaction | 違反類型 | 發現日期 | 狀態 |
|---------|---------|------------|---------|---------|------|
| {service} | {service} | {interaction} | Schema / Status | {date} | 🔴 未修復 |

---

## 4. 效能基準（對照 PBS）

| 指標 | PBS 目標 | 實際值 | 狀態 |
|-----|---------|--------|------|
| Latency P50 | < {N}ms | {N}ms | ✅/❌ |
| Latency P95 | < {N}ms | {N}ms | ✅/❌ |
| Latency P99 | < {N}ms | {N}ms | ✅/❌ |
| Throughput | > {N} RPS | {N} RPS | ✅/❌ |
| Error Rate | < 0.1% | {X}% | ✅/❌ |

---

## 5. 安全掃描摘要

| 工具 | 掃描類型 | Critical | High | Medium | Low | 狀態 |
|-----|---------|---------|------|--------|-----|------|
| SonarQube | SAST | 0 | 0 | {N} | {N} | ✅/❌ |
| OWASP ZAP | DAST | 0 | {N} | {N} | {N} | ✅/❌ |
| Snyk | SCA | 0 | {N} | {N} | {N} | ✅/❌ |
| Trivy | Container | 0 | {N} | {N} | {N} | ✅/❌ |

---

## 6. 缺陷趨勢（最近 {N} 次 Sprint）

| Sprint | 新增缺陷 | 修復缺陷 | 未解決 | P0/P1 比例 | 逃逸率 |
|--------|---------|---------|--------|-----------|-------|
| Sprint-{N} | {N} | {N} | {N} | {X}% | {X}% |

---

## 7. 改進建議（本次 CI 發現）

| 問題 | 影響 | 建議行動 | 優先級 |
|------|------|---------|-------|
| {issue} | {impact} | {action} | P0/P1/P2 |

---

## 8. 歷史趨勢

```
覆蓋率趨勢（最近 10 次 Build）:
Build: [#1][#2][#3][#4][#5][#6][#7][#8][#9][#10]
Line:  [72%][74%][76%][78%][79%][80%][82%][83%][84%][{X}%]
```

---

> **自動化說明**: 本報告由 CI Pipeline 自動生成，每次 Build 後更新。
> 手動編輯將在下次 CI 執行後被覆蓋。
> 如需永久記錄，請建立快照版本（Archive）。
