# Path Cost Estimator 規格（Phase G M6 / ACT-043/044）

**對應規則**: CLAUDE.md §9.19
**對應 tag**: `phase-g-final`
**OPEN 對齊**: OPEN-G.6（冷啟動 default = 8000 tokens）

---

## 1. 估算模型

### 1.1 樣本來源

- 歷史 dispatch 紀錄：`build/reports/test-analysis/DISPATCH-LOG-{date}.yaml`
- 實測 token 紀錄：`build/state/conversation-ledger.yaml`
- key tuple：`(subagent, classification)`，例如 `(sa-analyst, requirement_drafting)`

### 1.2 公式

```
samples_30 = last 30 ledger entries for (subagent, classification)
avg = mean(samples_30)
stddev = stdev(samples_30)
estimated = avg + 1.5 * stddev   # safety margin
gate_pass = token_remaining > estimated * 1.2
```

### 1.3 冷啟動

```
if len(samples_30) < 10:
    estimated = 8000   # OPEN-G.6 / Rule 9.19.1 conservative default
    source = "cold_start"
```

### 1.4 持久化

- rolling window state：`build/state/path-cost-rolling.yaml`
- schema：`{(subagent, classification): {samples: [...], updated_at: ...}}`
- 由 `file_lock.py` 保護並行寫入

---

## 2. 整合點

### 2.1 Orchestrator dispatch budget gate

- `agent/specialized/sdd-orchestrator-zh.yaml` 新增 `step_3_5_estimate_cost`
- 派遣 subagent 前呼叫 `PathCostEstimator.estimate(subagent, classification)`
- gate 失敗 → 拒絕 + `record_dispatch_rejection()` 寫入 `build/reports/orchestrator/REJECTED-{date}.yaml`

### 2.2 REJECTED 日誌結構（與 DISPATCH-LOG 對齊）

```yaml
schema_version: 1
rejected:
- subagent: dev-senior
  classification: implementation_pr
  estimated: 12000
  remaining: 9500
  reason: "budget_exhausted: 12000 * 1.2 > 9500"
  proposed_alternative: "stage-compaction first"
  rejected_at: "2026-04-27T10:15:00+00:00"
```

### 2.3 連續 3 拒 → ESCALATION

- `state.dispatch_rejection_count` 計數
- 連續 3 次（不 reset by other dispatches）→ `transition("ESCALATION", reason="budget_exhausted")`
- DiagnosticAgent 對 reason `budget_exhausted` 分類為 `retry_exhausted` (structural)，不可 auto-recover（per Rule 9.14.3）

---

## 3. 邊界（Rule 9.19）

| 子規則 | 內容 |
|-------|------|
| 9.19.1 | 樣本不足（< 10）使用保守 default `estimated = 8000`；不可降低 |
| 9.19.2 | dispatch 拒絕一律寫入 REJECTED log，含 reason / proposed_alternative |
| 9.19.3 | 連續 3 次拒絕 → 自動 ESCALATION（reason: `budget_exhausted`） |
| 9.19.4 | 預估誤差 > 50% 連續 5 次 → 警告人工調校（寫入 `build/reports/orchestrator/CALIBRATION-WARN-{date}.yaml`） |
| 9.19.5 | NA-3 milestone hook：每個 (subagent, classification) 樣本首次達 30（rolling-30 飽和）時，由 `record_sample()` 一次性寫 `build/reports/orchestrator/CALIBRATION-MILESTONE-{subagent}-{classification}-{date}.yaml`；之後 sample 不重發；milestone fired 旗標持久化於 `build/state/path-cost-rolling.yaml` 的 `milestone_fired: true` |

---

## 4. 驗收

- [ ] PathCostEstimator 預估誤差 rolling-30 平均 < 30%
- [ ] Budget gate 拒絕命中率 100%（token_remaining < estimated × 1.2 時）
- [ ] REJECTED log schema 與 DISPATCH-LOG 對齊
- [ ] 連續 3 拒 → ESCALATION 整合測試通過
- [ ] DiagnosticAgent 對 `budget_exhausted` 分類為 structural（無誤觸發 auto-recovery）
