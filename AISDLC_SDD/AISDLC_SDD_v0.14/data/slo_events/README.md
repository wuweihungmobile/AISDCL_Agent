# SLO Event Inbox (ACT-027)

> 本目錄為 **File-based Pull** 模式的 SLO 事件落地位置（`SDD_improving_Automation_04.md §OPEN-10.6` 使用者決策）。
> 架構上刻意不採 HTTP Webhook：降低資安面、零外部依賴，適合地端與受限網路。

## 目錄結構

```
data/slo_events/
├── README.md                    ← 本文件
├── metric_nfr_map.yaml          ← 選配：metric → NFR 對應覆蓋
├── SLO-EVENT-YYYYMMDD-*.yaml    ← 原始事件檔（待 ingest）
├── quarantine/                  ← 簽章失敗 / schema 不合 → 隔離
└── processed/                   ← 成功 ingest → 保留歸檔
```

## 事件 Schema（SLO Event Payload）

```yaml
event_id: "p95-login-20260424-001"
timestamp: "2026-04-24T10:00:00+00:00"
metric: "p95_login_ms"
observed: 450
target: 200
unit: "ms"
duration_minutes: 15
environment: "production"         # 選配
signed_fields:                    # 必要；僅接受下列 canonical tuple
  - event_id
  - timestamp
  - metric
  - observed
  - target
  - unit
  - duration_minutes
signature: "<hex HMAC-SHA256>"    # 必要；見下節
nfr_id: "NFR-PERF-001"            # 選配；省略時由 production_monitor 自動映射
```

### 時間合法性

- `timestamp` 必須為 ISO-8601（含時區，或隱含 UTC）
- 未來時間：容忍 5 分鐘 clock skew，超過即 quarantine
- 過期事件：超過 72h 即 quarantine（避免重放）

## HMAC 簽章

```
payload    = "|".join(str(event[f]) for f in signed_fields)
signature  = HMAC-SHA256(SDD_SLO_EVENT_SECRET, payload).hexdigest()
```

- Secret 來源：環境變數 `SDD_SLO_EVENT_SECRET`
- 開發 / 測試預設：`aisdlc-sdd-dev-secret`（**禁止**用於生產）
- `signed_fields` 必須 **完全等於** 預設 canonical tuple；任何 subset / superset 即視為可疑
- 驗證使用 `hmac.compare_digest`（常數時間，避免 timing oracle）

## 簽章 CLI

```bash
# 對一個事件檔簽章
python -m tools.fsm_runtime.production_monitor sign --event data/slo_events/my-event.yaml

# 驗證簽章
python -m tools.fsm_runtime.production_monitor verify --event data/slo_events/my-event.yaml
```

## 掃描與 ingest

```bash
# 一次掃描整個 inbox
python -m tools.fsm_runtime.production_monitor scan
```

- `session_start.py` 在每個 Session 啟動時自動觸發（與 reconcile CI events 並行）
- 未簽章 / 過期 / schema 不合 → 移至 `quarantine/`，記錄到掃描報告
- 成功 ingest → 移至 `processed/`、寫入 `build/reports/fsm/PBS-DRIFT-{date}.yaml`
- 同一 NFR 24h 內 ≥ 3 次違反 → 自動產出 `docs/06_quality/PBS-DRIFT-{NFR}-{date}.md`

## Metric → NFR 映射

預設使用 `_BUILTIN_MAP`（`production_monitor.py`）。若需覆蓋，建立 `metric_nfr_map.yaml`：

```yaml
metric_to_nfr:
  p95_login_ms: "NFR-PERF-001"
  p95_api_ms: "NFR-PERF-002"
  error_rate_percent: "NFR-PERF-010"
```

未對應且符合 `p<digits>_<name>_ms` pattern 的 metric，會回傳 `NFR-PERF-9NN` 的 deterministic slot（以 SHA-1 取模）。

## Mock 事件產生（測試 / Canary）

Test fixture 位於：
```
tools/fsm_runtime/tests/test_production_monitor.py::make_signed_event()
```

使用此 helper 可生成合法簽章事件，直接丟入本目錄即可被 `scan_inbox()` 攝取。
