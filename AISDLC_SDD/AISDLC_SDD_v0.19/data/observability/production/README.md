# data/observability/production/ — 生產遙測 inbox（Phase I M3 / ACT-067）

生產遙測落地（file-based pull，沿用 OPEN-10.6「禁 HTTP endpoint」資安決策）。

- `logs.ndjson` — `{ts, level, msg, ac_id, ...}`
- `metrics.ndjson` — `{ts, name, value, labels:{}}`
- `behavioral.ndjson` — `{ts, ac_id, observed_fields[], observed_order[], invariants_violated[], branches_hit[]}`

由 `observability_query.logql_lite/promql_lite`（指向本目錄）唯讀查詢，
`behavioral_drift_scorer` 量化功能性偏差，`production_to_fpl` 在窗口內 ≥3 次
偏差時自動產 FPL 草案（trust_level=proposed，advisory-only）。

> 與 `data/slo_events/`（數值 SLO，production_monitor）區隔：本目錄承載
> **功能性 behavioral** 現實，補 PI-5「現實只用數字說話」的盲區。
