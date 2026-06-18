# Canary Release Spec — Canary 部署規格模板
# 使用說明：複製至 docs/08_deployment/CANARY-SPEC-{system}.md 後填寫

**系統名稱**: {SystemName}
**版本**: v1.0
**建立日期**: {date}
**前置文件**: `MIGRATION-CONTRACT-MAP-{system}.md`（Routing Contract 章節）

---

## 1. Canary 策略概覽

| 項目 | 值 |
|------|-----|
| 部署類型 | Canary Release |
| 流量切換工具 | {Istio / Nginx / AWS ALB / Kubernetes Ingress} |
| 監控工具 | {Prometheus + Grafana / Datadog} |
| 自動化程度 | {全自動 / 人工確認每階段} |

---

## 2. Canary 流量分配計畫

| 階段 | 新系統流量 | 觀察時間 | 進入條件 | 退出條件（回滾） |
|------|----------|---------|---------|----------------|
| Phase 0 | 0% | — | 前置條件全部通過 | — |
| Phase 1 | 5% | {N}h | P0 通過、手動確認 | 錯誤率 > {%} |
| Phase 2 | 25% | {N}h | P1 穩定 {N}h | 錯誤率 > {%} |
| Phase 3 | 50% | {N}h | P2 穩定 {N}h | 錯誤率 > {%} |
| Phase 4 | 75% | {N}h | P3 穩定 {N}h | 錯誤率 > {%} |
| Phase 5 | 100% | {N}h 觀察 | P4 穩定 {N}h | 任何 P0 事件 |

---

## 3. 流量切換規格

### 3.1 Phase 1 → Phase 5 切換命令

```yaml
# Kubernetes Ingress 範例（按實際工具調整）
phase_1:
  canary_weight: 5
  command: |
    kubectl annotate ingress {ingress-name} \
      nginx.ingress.kubernetes.io/canary-weight="5"
  validation: curl {health-endpoint}
  
phase_2:
  canary_weight: 25
  command: |
    kubectl annotate ingress {ingress-name} \
      nginx.ingress.kubernetes.io/canary-weight="25" --overwrite
  validation: curl {health-endpoint}

# 其他 Phase 依此類推...
```

### 3.2 目標用戶群組（若使用 Header/Cookie 路由）

| 群組 | 描述 | 路由條件 |
|------|------|---------|
| Internal | 內部測試人員 | Header: `X-Canary: true` |
| Beta Users | 自願參與的 Beta 用戶 | Cookie: `canary=1` |
| Random {%} | 隨機流量 | Canary Weight |

---

## 4. 每階段監控指標（SLO-Based）

| 指標 | 基準值 | Phase 1-2 告警閾值 | Phase 3-5 告警閾值 |
|------|--------|-----------------|-----------------|
| 錯誤率（5xx） | < {%} | > {%} | > {%} |
| P50 延遲 | < {N}ms | > {N}ms | > {N}ms |
| P95 延遲 | < {N}ms | > {N}ms | > {N}ms |
| P99 延遲 | < {N}ms | > {N}ms | > {N}ms |
| 吞吐量（RPS） | {N} RPS | < {N} RPS | < {N} RPS |

---

## 5. 自動化 Canary 分析

```yaml
# 自動化 Canary 分析規格（如使用 Argo Rollouts / Flagger）
canary_analysis:
  interval: {N}m
  threshold: {N}（連續幾次失敗才回滾）
  metrics:
    - name: success-rate
      threshold: {%}
      query: |
        sum(rate(http_requests_total{status!~"5.."}[5m]))
        / sum(rate(http_requests_total[5m]))
    - name: latency-p95
      threshold: {N}ms
      query: |
        histogram_quantile(0.95, 
          sum(rate(http_request_duration_seconds_bucket[5m])) by (le))
```

---

## 6. 每階段 Human 確認點

| 確認點 | 時機 | 確認者 | 確認標準 |
|--------|------|--------|---------|
| Phase 1 進入確認 | Phase 0 完成後 | {決策者} | 前置條件 100% ✅ |
| Phase 2 進入確認 | Phase 1 觀察期結束 | {決策者} | 指標全綠 ✅ |
| Phase 3 進入確認 | Phase 2 觀察期結束 | {決策者} | 指標全綠 ✅ |
| Phase 5（全量）確認 | Phase 4 觀察期結束 | {最終決策者} | 🔴 Human 最終授權 |

---

## 7. Canary 完成後

- [ ] 舊版本流量清零確認
- [ ] 舊版本容器/服務下線（廢棄期後）
- [ ] 監控告警規則更新（移除 Canary 相關）
- [ ] 🔴 Human 確認：全量切換完成

**最後更新**: {date}
