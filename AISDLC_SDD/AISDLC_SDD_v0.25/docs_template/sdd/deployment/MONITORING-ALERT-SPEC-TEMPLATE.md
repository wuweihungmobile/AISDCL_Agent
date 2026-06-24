# Monitoring Alert Spec — 監控告警規格模板
# 使用說明：複製至 docs/08_deployment/MONITORING-ALERT-SPEC-{system}.md 後填寫

**系統名稱**: {SystemName}
**版本**: v1.0
**建立日期**: {date}
**前置文件**: `INFRA-REQUIREMENTS-SPEC-{system}.md`（SLO 章節）

---

## 1. 監控架構

| 元件 | 工具 | 用途 |
|------|------|------|
| 指標收集 | {Prometheus / Datadog} | APM 指標 |
| 視覺化 | {Grafana / Datadog Dashboard} | 儀表板 |
| 日誌聚合 | {ELK / CloudWatch} | 集中日誌 |
| 分散式追蹤 | {Jaeger / Zipkin / Datadog APM} | 請求追蹤 |
| 告警路由 | {PagerDuty / OpsGenie / Slack} | 告警通知 |

---

## 2. SLO-Based 告警規格

> 所有告警閾值必須基於 INFRA-REQUIREMENTS-SPEC 中定義的 SLO

### 2.1 可用性告警

| 告警 ID | 名稱 | 條件 | 持續時間 | 嚴重度 | 通知對象 |
|---------|------|------|---------|--------|---------|
| ALERT-AVAIL-001 | 服務可用性下降 | 可用性 < {99.7}% | 5min | P1 | #oncall |
| ALERT-AVAIL-002 | 服務不可用 | 可用性 < {99.0}% | 1min | P0 | #oncall + PagerDuty |

```yaml
# Prometheus 告警規則範例
- alert: ServiceAvailabilityP1
  expr: |
    (sum(rate(http_requests_total{status!~"5.."}[5m]))
    / sum(rate(http_requests_total[5m]))) < 0.997
  for: 5m
  labels:
    severity: P1
  annotations:
    summary: "服務可用性低於 99.7%"
    runbook: "https://wiki/{runbook_url}"
```

### 2.2 延遲告警

| 告警 ID | 名稱 | 條件 | 持續時間 | 嚴重度 |
|---------|------|------|---------|--------|
| ALERT-LAT-001 | P95 延遲警告 | P95 > {N}ms | 5min | P2 |
| ALERT-LAT-002 | P95 延遲嚴重 | P95 > {N}ms | 2min | P1 |
| ALERT-LAT-003 | P99 延遲嚴重 | P99 > {N}ms | 2min | P1 |

### 2.3 錯誤率告警

| 告警 ID | 名稱 | 條件 | 持續時間 | 嚴重度 |
|---------|------|------|---------|--------|
| ALERT-ERR-001 | 錯誤率上升 | 5xx Rate > {%} | 5min | P2 |
| ALERT-ERR-002 | 錯誤率飆升 | 5xx Rate > {%} | 2min | P1 |
| ALERT-ERR-003 | 完全失敗 | 5xx Rate > {%} | 1min | P0 |

### 2.4 資源告警

| 告警 ID | 名稱 | 條件 | 嚴重度 |
|---------|------|------|--------|
| ALERT-RES-001 | CPU 高使用率 | CPU > {%} 持續 10min | P2 |
| ALERT-RES-002 | Memory 高使用率 | Memory > {%} 持續 10min | P2 |
| ALERT-RES-003 | DB 連線池耗盡 | Pool Usage > {%} | P1 |
| ALERT-RES-004 | 磁碟空間不足 | Disk > {%} | P1 |

---

## 3. 業務指標告警

| 告警 ID | 名稱 | 指標 | 閾值 | 嚴重度 |
|---------|------|------|------|--------|
| ALERT-BIZ-001 | {業務指標 1} 異常 | {metric} | {閾值} | P1 |
| ALERT-BIZ-NNN | {業務指標 N} | {metric} | {閾值} | {嚴重度} |

---

## 4. 告警嚴重度定義

| 嚴重度 | 定義 | 回應時間 | 通知方式 |
|--------|------|---------|---------|
| **P0** | 生產服務完全不可用，所有用戶受影響 | 立即（< 5min） | PagerDuty + Slack + 電話 |
| **P1** | 生產服務嚴重降級，部分用戶受影響 | < 30min | PagerDuty + Slack |
| **P2** | 非緊急問題，可在工作時間內處理 | < 4h | Slack |
| **P3** | 資訊性告警，趨勢警示 | 下一工作日 | Email |

---

## 5. Runbook 連結

| 告警 | Runbook URL |
|------|-------------|
| 服務不可用 | {URL} |
| 高錯誤率 | {URL} |
| 資料庫問題 | {URL} |
| 容量不足 | {URL} |

---

## 6. 儀表板規格

### 主要 Grafana 儀表板

| 儀表板 | 用途 | 受眾 | 刷新頻率 |
|--------|------|------|---------|
| Service Overview | 整體服務健康 | 所有團隊 | 30s |
| API Performance | API 延遲/錯誤率 | Dev + DevOps | 1m |
| Infrastructure | CPU/Memory/Disk | DevOps | 1m |
| Business KPI | 業務指標 | PM + 業務 | 5m |
| Canary Deployment | 遷移/Canary 監控 | DevOps + Dev Lead | 30s |

---

## 7. SLO 錯誤預算追蹤

```yaml
slo_error_budget:
  availability_slo: {99.9}%
  measurement_window: 30_days
  error_budget_minutes: 43.8  # 30d * 24h * 60min * (1-0.999)
  current_burn_rate_alert:
    - fast_burn: 14.4x  # 消耗 1h 的 budget，觸發 P1
    - slow_burn: 1x     # 過去 6h 消耗超過 budget，觸發 P2
```

**最後更新**: {date}
