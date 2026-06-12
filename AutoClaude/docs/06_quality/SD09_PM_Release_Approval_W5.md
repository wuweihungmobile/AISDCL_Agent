# SD_09 W5 G5 PM 發布核准

| 項目 | 值 |
|------|---|
| 核准日 | YYYY-MM-DD |
| PM 姓名 | （待填入）|
| 核准切換 | yaml_only → both → db_only |
| canary 階梯 | 10% / 50% / 100%（24h / 48h / 7d）|
| W5 雙條件齊備 | ✅ / ❌ |
| PM 簽名 | （git commit --signoff 留痕）|

## 雙條件齊備驗證

- [ ] (1a) IObservabilityPort + trace_id 30 天 nightly 全綠（`tools/observability_ga_check.py` exit 0）
- [ ] (1b) KB metric 4 項 snapshot 連續 30 天綠（hit_rate / query_p95_ms / strategy_rotation / cache_eviction）
- [ ] (2) drift_log 30 天零事件（`severity != 'info'` 計數 = 0）

## 對應

- ADR-SD09-001 §3（W5 db_only 切換不可逆轉折點）
- ADR-SD08-005 §2.2 雙軌制（PG production GA 條件）
- ADR-SD09-005（PG canary 三階梯閾值）
- risk_log §15 R-SD09-A-4 / R-SD09-O-1 / R-SD09-A-5 / R-SD09-CI-3

## 狀態

⚠️ TEMPLATE（2026-05-19 P0-D4 建立）：待 SD_09 W5 G5 時由 PM 親自填入並 git commit --signoff 簽核。
