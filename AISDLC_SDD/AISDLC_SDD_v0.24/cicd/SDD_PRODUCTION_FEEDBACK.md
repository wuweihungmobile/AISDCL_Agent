# SDD Production Feedback Layer — ACT-027 / M3
# SDD 生產回饋層 CI/CD 規格

**版本**: v1.0
**建立日期**: 2026-04-24
**對應 ACT**: Phase E / M3 / ACT-027
**文件類型**: 部署規格（Deployment Specification）
**所屬分類**: `AISDLC_SDD_v0.01/cicd/`
**Spec Gate**: 🔷 SCG-6 Release（Post-release monitoring layer）
**FSM 狀態**: `PRODUCTION_SIGNAL`（非阻塞監測）

---

## 🎯 目的

把「生產環境的 SLO 違反事件」閉環回饋到 SDD 規格鏈，讓 PBS / NFR 能依實測持續校正：

1. **採集**：File-based Pull 模式（**OPEN-10.6 使用者決策**），不開外部 HTTP Endpoint
2. **驗證**：HMAC-SHA256 簽章 + timestamp 合法性（防偽造、防重放）
3. **映射**：`metric → NFR-PERF-NNN`
4. **漂移偵測**：同一 NFR 24h 內 ≥ 3 次違反 → 觸發 PBS-DRIFT 報告
5. **人工決策**：sa-analyst 依報告更新 FRD NFR，透過 SCG-0 閘門重新凍結

> **Design Intent**（承 Automation_04 §拾柒）：PRODUCTION_SIGNAL 是「監測」而非「阻塞」狀態 —
> session 可繼續正常運作，只在 sa-analyst 採納漂移報告時才回歸 `SPEC_DRAFTING`。

---

## 🏗️ Pipeline 架構

```
外部監控 (Grafana / Datadog / 手寫腳本)
        │
        │ 依 SDD Schema 寫 YAML
        ▼
data/slo_events/SLO-EVENT-*.yaml  (inbox)
        │
        │ SessionStart Hook 或 CLI `scan`
        ▼
┌────────────────────────────────────┐
│ production_monitor.scan_inbox()    │
│  ├─ schema 驗證                    │
│  ├─ timestamp 合法性（72h / 5min） │
│  ├─ HMAC-SHA256 簽章               │
│  └─ metric → NFR 映射              │
└────────────────────────────────────┘
        │           │
     applied     rejected
        │           │
        ▼           ▼
  processed/    quarantine/
        │
        ▼
build/reports/fsm/PBS-DRIFT-{date}.yaml  (rolling log)
        │
        ▼ (同 NFR 24h ≥ 3 筆)
docs/06_quality/PBS-DRIFT-{NFR}-{date}.md (人工 review)
        │
        ▼
sa-analyst 採納 → SPEC_DRAFTING → SCG-0 重新閘門
```

---

## 📋 SLO Event Schema

| 欄位 | 必填 | 型別 | 說明 |
|------|------|------|------|
| `event_id` | ✅ | string | 全域唯一 ID（建議：`{metric}-{yyyymmdd}-{seq}`） |
| `timestamp` | ✅ | ISO-8601 | UTC 時戳，clock skew 容忍 5 分鐘 |
| `metric` | ✅ | string | 例：`p95_login_ms`、`error_rate_percent` |
| `observed` | ✅ | number | 觀測值 |
| `target` | ✅ | number | 當時 NFR 目標值（**事件產生當下**，不是現在值） |
| `unit` | ✅ | string | `ms` / `percent` / `rps` … |
| `duration_minutes` | ✅ | number | 違反持續分鐘數 |
| `environment` | ⬜ | string | `production` / `staging` / `canary` |
| `nfr_id` | ⬜ | string | 覆寫 metric→NFR 自動映射 |
| `signed_fields` | ✅ | list[string] | 必須 **等於** canonical tuple，順序不可調換 |
| `signature` | ✅ | hex string | HMAC-SHA256(secret, canonical_payload) |

### Canonical payload（簽章計算）

```
payload = "{event_id}|{timestamp}|{metric}|{observed}|{target}|{unit}|{duration_minutes}"
signature = HMAC-SHA256(SDD_SLO_EVENT_SECRET, payload).hexdigest()
```

---

## 🔒 安全機制

### HMAC-SHA256 簽章（強制）

- 由環境變數 `SDD_SLO_EVENT_SECRET` 提供 secret
- 開發 / 測試預設：`aisdlc-sdd-dev-secret`（**禁止**用於生產環境）
- 驗證用 `hmac.compare_digest`（常數時間，避免 timing attack）
- `signed_fields` 必須完全等於 canonical tuple，超集或子集皆視為篡改

### Timestamp 合法性

| 條件 | 動作 |
|------|------|
| 不是 ISO-8601 | 拒絕（`bad_timestamp`） |
| 超出未來 > 5 分鐘 | 拒絕（`future_timestamp`） |
| 早於現在 > 72 小時 | 拒絕（`stale_timestamp`，防重放） |

### Quarantine 策略

- 任何 reject 原因（schema 缺欄、簽章錯、時戳違規、無 NFR 映射）→ 移至 `quarantine/`
- Scan 報告記錄 reason 與檔案路徑
- **事件不會自動套用** — 人工檢查後可修正再放回 inbox

---

## 🔄 session_start.py 掃描整合

`session_start.py` 每次 Session 啟動執行：

```python
from tools.fsm_runtime.production_monitor import scan_inbox
report = scan_inbox()   # 使用預設 inbox / quarantine / processed 路徑
# additionalContext 注入："[SDD-PROD] scanned=N applied=M quarantined=K drift_reports=…"
```

**同時更新 FSM-STATE**（lazy 寫入 `production_signal_tracking`）：

```yaml
production_signal_tracking:
  last_scan_at: "{ISO8601}"
  events_ingested_count: {cumulative}
  events_quarantined_count: {cumulative}
  drift_reports_written: [...]
```

---

## 📈 漂移偵測規則

```python
if len(recent_entries_for_nfr(nfr_id, window=24h)) >= 3:
    generate_drift_report(nfr_id, metric, recent_entries)
```

- Window：滾動 24 小時（跨今天 + 昨天兩份 `PBS-DRIFT-{date}.yaml`）
- Threshold：預設 **3 次** — 覆寫於 `FSM-STATE.production_signal_tracking.persistent_threshold`
- 同一 session 內重複達標只覆寫同一份 Markdown 報告（不會產生多份）

---

## 🚦 FSM 整合

| 動作 | 條件 | FSM 行為 |
|------|------|---------|
| 進入 PRODUCTION_SIGNAL | `rt.enter_production_signal()` 明確呼叫 | 當前 state 必須 ∈ `{RELEASE, RELEASE_READY, PRODUCTION_SIGNAL}`；否則 `TransitionError` |
| 離開 PRODUCTION_SIGNAL | `rt.exit_production_signal(target)` | target ∈ `{SPEC_DRAFTING, RELEASE}`；SPEC_DRAFTING 代表 sa-analyst 採納漂移報告 |
| Tool calls | 任何時間 | **不阻塞**（對比 ESCALATION / TERMINATED）— 監測狀態可繼續正常操作 |
| Auto-compact 觸發 | PRODUCTION_SIGNAL 期間 cumulative_tokens 達 90% | 允許（`AUTO_COMPACT_SOURCES` 已納入 PRODUCTION_SIGNAL），compact 完成後回到 PRODUCTION_SIGNAL |

---

## 🧪 驗收腳本（ACT-027 完工憑證）

```bash
# 1. 準備 5 筆簽章事件（3 筆同 NFR + 2 筆不同）
pytest tools/fsm_runtime/tests/test_production_monitor.py -v

# 2. 人工 dry-run：注入 mock 事件並掃描
python tools/fsm_runtime/tests/fixtures/make_mock_slo_events.py   # 若 fixture 腳本存在
python -m tools.fsm_runtime.production_monitor scan

# 3. 確認：
#  - data/slo_events/processed/ 有 5 份
#  - build/reports/fsm/PBS-DRIFT-{date}.yaml 有 5 筆 entries
#  - docs/06_quality/PBS-DRIFT-NFR-PERF-001-{date}.md 已生成
```

> **Windows 宿主注意**：`session_start.py` 及驗收腳本輸出含中文（繁體），
> 若以 Python `subprocess` capture，必須顯式指定 `encoding="utf-8"` 或
> `text=False` 後手動 `decode("utf-8", errors="replace")`，否則會在
> `cp950` 終端觸發 `UnicodeDecodeError`。`.claude/settings.json` 已全域設
> `PYTHONIOENCODING=utf-8`，但外部 QA harness 應自行對齊此約定。

---

## 🔗 相關文件

- [Automation_04 §ACT-027](../build/planning/active/SDD_improving_Automation_04.md#act-027production-feedback-layerlevel-5-入口)
- [FSM Engine](../workflow/sdd-fsm-engine/SDD_FSM_ENGINE.md)（Phase E M3 章節）
- [PBS-DRIFT Template](../docs_template/sdd/quality/PBS-DRIFT-REPORT-TEMPLATE.md)
- [CLAUDE.md Rule 9.10](../../CLAUDE.md)

---

**建立者**: AISDLC-SDD Phase E M3 執行（Claude Opus 4.7）
**驗收日期**: 2026-04-24
