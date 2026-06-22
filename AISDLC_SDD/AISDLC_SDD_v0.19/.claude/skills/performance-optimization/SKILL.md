---
name: performance-optimization
description: 效能優化，PBS Gate 前置定義基準規格，NFR 量化目標，優化結果更新 RTM
user-invocable: true
disable-model-invocation: false
argument-hint: "[focus: frontend|backend|database|full]"
allowed-tools:
  - Read
  - Grep
  - Glob
---

# Performance Optimization Skill（SDD 原生）

效能優化在 SDD 中必須「先定義基準，後優化」：PBS（Performance Baseline Specification）必須在效能測試前建立，優化目標直接引用 NFR 量化值，不可「憑感覺」優化，優化結果需更新 RTM 的效能 TC。

---

## 觸發方式

```bash
/performance-optimization backend
/performance-optimization database
/performance-optimization full
```

---

## 前置條件（SDD Spec-First）

| 閘門 | 說明 | 驗證方式 |
|------|------|---------|
| 🔷 NFR 量化 | 效能 SLO 已定義 | `docs/01_requirements/FRD-{System}.md` NFR-P-XXX 節 |
| PBS 建立 | 效能基準已量化 | `docs/06_quality/PBS-{System}.md` 存在 |

---

## 執行流程

### 階段 1：PBS（Performance Baseline Specification）建立 🔴

**文件路徑**：`docs/06_quality/PBS-{SystemName}.md`

```markdown
# Performance Baseline Specification — {SystemName}

**測試環境**: {staging / prod-like 環境}
**測試工具**: {k6 / JMeter / Locust / Artillery}
**基線建立日期**: {YYYY-MM-DD}

## SLO 目標（來自 FRD NFR）

| 指標 | NFR ID | SLO 目標 | 當前基線 | 差距 |
|------|--------|---------|---------|------|
| P50 API 延遲 | NFR-P001 | < 100ms | {測量值} | {差距} |
| P99 API 延遲 | NFR-P001 | < 500ms | {測量值} | {差距} |
| 錯誤率 | NFR-P002 | < 0.1% | {測量值} | {差距} |
| 並發用戶 | NFR-P003 | 1000 rps | {測量值} | {差距} |
| DB 查詢 P99 | NFR-P005 | < 50ms | {測量值} | {差距} |

## 測試腳本

```javascript
// k6/load-test.js
import http from 'k6/http';
import { check } from 'k6';

export const options = {
  // 對應 NFR-P003 目標
  scenarios: {
    slo_validation: {
      executor: 'ramping-vus',
      stages: [
        { duration: '30s', target: 100 },
        { duration: '1m', target: 1000 },   // NFR-P003 目標
        { duration: '30s', target: 0 },
      ],
      thresholds: {
        http_req_duration: ['p(99)<500'],     // NFR-P001 P99
        http_req_failed: ['rate<0.001'],      // NFR-P002 錯誤率
      },
    },
  },
};
```
```

🔴 確認點：PBS 基線測量完成，差距已識別。

---

### 階段 2：瓶頸分析（針對 NFR 未達標項目）

依測量結果，識別具體瓶頸：

**後端優化方向**（按 NFR 差距優先）：
- P99 延遲過高 → 檢查慢查詢 / N+1 問題 / 未加索引
- 錯誤率過高 → 檢查連接池設定 / 超時配置
- 並發能力不足 → 檢查資源鎖 / 非同步處理

**資料庫優化**（對應 NFR-P005）：
- EXPLAIN ANALYZE 慢查詢
- 索引策略（對應 DB Schema Contract）
- 連接池設定（對應 NFR-R 資源需求）

---

### 階段 3：優化實作

每次優化遵循 SDD 循環：
1. 識別問題（有 NFR 數據支撐）
2. 提出假設
3. 實作優化
4. 重新測試（對照 PBS 基線）
5. 更新 PBS 結果

**禁止行為**：
- 未測量就聲稱「已優化」
- 優化到超過 NFR 目標就停止（避免過度優化）

---

### 階段 4：RTM 更新 🔴

```bash
/rtm-generate update    # 更新效能 TC（TC-PERF-XXX）
/spec-compliance-check docs/06_quality/PBS-{System}.md
```

🔴 確認點：所有 NFR-P-XXX 的 SLO 已達標；PBS 基線更新為優化後結果。

---

## 強制產出（SDD 文件）

| 產出物 | 路徑 | 對應 SCG |
|--------|------|---------|
| PBS 效能基準 | `docs/06_quality/PBS-{System}.md` | SCG-5 前 |
| 效能優化 ADR（若有架構變更）| `docs/02_architecture/adr/ADR-{NNN}-performance.md` | SCG-5 前 |

---

## 後置動作

```
/devops-monitoring         # 設定 PBS 告警（NFR 閾值）
/sdd-gate SCG-5            # 效能達標後提交交付閘門
```

🔷 **本 Skill 協助通過**：SCG-5（效能 NFR 驗收）

---

## 相關 Skill

- `/devops-monitoring` — NFR 告警設定（PBS 監控）
- `/integration-database` — DB 索引優化
- `/integration-redis` — 快取策略（效能提升）

---

**基於**: AISDLC-SDD v0.01
**對應 CI/CD 規格**: `cicd/SDD_PERFORMANCE_CICD.md`
