# PBS-DRIFT Report — {NFR_ID}
# Performance Baseline Spec Drift Report

> 本模板由 `tools/fsm_runtime/production_monitor.generate_drift_report()` 自動生成；
> 人工 review 後由 **sa-analyst** 決定是否更新 FRD NFR 與 PBS。
>
> 對應 ACT：Phase E / M3 / ACT-027（Production Feedback Layer）

---

## 摘要

- **專案**: {PROJECT_NAME}
- **NFR ID**: {NFR_ID}（例：`NFR-PERF-001`）
- **Metric**: `{METRIC_KEY}`（例：`p95_login_ms`）
- **Drift 視窗**: 最近 {WINDOW_HOURS}h（預設 24h）
- **違反次數**: {EVENT_COUNT}（持續違反閾值：{PERSISTENT_THRESHOLD}）
- **報告產生時間**: {ISO8601}
- **事件來源**: ACT-027 Production Feedback Layer（HMAC-verified）

---

## 1. 觀察到的違反事件

| # | event_id | timestamp | observed | target | unit | duration_min |
|---|----------|-----------|----------|--------|------|--------------|
| 1 | {event_id} | {timestamp} | {observed} | {target} | {unit} | {duration_minutes} |
| 2 | ... | ... | ... | ... | ... | ... |

---

## 2. 建議 NFR 更新 Diff

```diff
- {NFR_ID}.target_{unit}: {OLD_TARGET}
+ {NFR_ID}.target_{unit}: {NEW_TARGET}  # +{DELTA} ({METRIC_KEY})
```

> 建議值採「觀測期間最大值」為保守 bump，由 sa-analyst 依業務與能力判斷是否採納。
> 若要維持原 target，請於 FRD 中新增容量 / 基礎架構強化計畫（例：P-ACT-XXX）。

---

## 3. Next Actions（sa-analyst 流程）

1. **閱讀本報告**：確認違反事件是否由已知事件（deploy / 外部 incident）造成
2. **更新 FRD**：
   - 編輯 `docs/01_requirements/FRD-{SystemName}.md` 的 NFR 條目
   - 若接受 bump：採用建議 target 值
   - 若拒絕 bump：新增 performance action 計畫（另開 `docs/04_planning/performance/` 文件）
3. **SLV 重跑**：
   - `/spec-logical-validator` 重跑 `SLV-001`（物理可行性）、`SLV-002`（AC 可量化）
4. **SCG-0 閘門**：
   - 新 NFR 通過 SCG-0 重新凍結，可回到 `SPEC_FROZEN`
5. **RTM 同步**：
   - 更新 RTM，確保 NFR 變更追溯到對應 User Story 與測試案例
6. **閉環通知**：
   - Commit 時附上本報告連結
   - FSM 透過 `rt.exit_production_signal("SPEC_DRAFTING")` 重新進入規格迴圈

---

## 4. 規格與實作追溯

| 來源 | 連結 |
|------|------|
| Drift 事件原始紀錄 | `build/reports/fsm/PBS-DRIFT-{DATE}.yaml` |
| 對應 FRD 段落 | `docs/01_requirements/FRD-{SystemName}.md#{NFR_ANCHOR}` |
| 對應 PBS | `docs/04_planning/performance/PBS-{SystemName}-*.md` |
| 觸發的 FSM 決策 | 查詢 `FSM-STATE-{project}.yaml#decision_trace`（trigger=`production_signal_enter`） |

---

## 5. 治理附註

- 本報告不是自動 apply — **禁止** 直接覆寫 FRD 檔案
- 若 24h 內產生多份同 NFR 報告，最新版覆寫舊版（歷史保留在 `PBS-DRIFT-{date}.yaml`）
- 事件簽章失敗者不會出現在此報告（已 quarantine 於 `data/slo_events/quarantine/`）

---

**範本版本**: v1.0
**建立日期**: 2026-04-24
**對應 ACT**: ACT-027 / Phase E M3
