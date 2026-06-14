# Observability Inbox — 本地唯讀查詢資料源

> **Phase H M4 / ACT-053**：對應 SDD_improving_Automation_08.md §4.3 / §G5。
> 保留 OPEN-10.6「禁 HTTP endpoint」資安決策，但恢復 AI「主動查詢根因」能力
> （查詢 ≠ 開 server）。由 `sandbox_runner` 在 EXECUTION_EVALUATION 中落地。

## 檔案

| 檔案 | 格式 | 內容 |
|------|------|------|
| `logs.ndjson` | 每行一 JSON | `{ts, level, msg, ...}` 沙箱執行日誌 |
| `metrics.ndjson` | 每行一 JSON | `{ts, name, value, labels:{}}` 時序指標 |

## 查詢（純 stdlib，無網路）

```python
from tools.fsm_runtime import observability_query as oq
oq.logql_lite('{level="error"} |= "deadlock"')          # LogQL 子集
oq.promql_lite("http_p95_ms", agg="max", labels={"route": "/login"})  # PromQL 子集
```

> 查詢結果進跨實例 Hub 前須經 anonymizer 雙掃（沿用 Phase F M2 PII 防護）。
