# SD09 AC4 啟用核准紀錄（labeled-PR 真 PG e2e）

**狀態**：✅ 已核准（2026-10-26）｜**核准事項**：啟用 `.github/workflows/autoclaude-pg-e2e-on-label.yml`——對 PR 貼 `needs-pg-e2e` 標籤才跑 pgvector recall／p95 真 PG e2e（SD_Improving_08 W2 T2-C5；ADR-SD09-008 v0.4 ACCEPTED 的 60ms 寬鬆升級門檻）。

## 1. 核准人與載體

- **核准人**：掌舵者（本專案 PM 角色；場景 A 個人開發，先例＝SD09_Execution_Guide T0-7「dev 自核」）。
- **載體**：Claude Code 互動選項（AskUserQuestion）於主控 session `0a41ada1-921d-48d4-bb4b-4cc4a18190e8`（2026-10-26），題目「要不要正式啟用『PR 貼 needs-pg-e2e 標籤才跑真 PG e2e』？」，所選＝**「啟用並記核准」**（其餘選項：啟用並消音 nightly 警示／暫不啟用）。主控依指示落本檔；觀察帳本列 OBS-SI-191 同日結案。

## 2. 依據（主控 2026-10-26 當回合真跑）

`python tools/ac4_progress_check.py --json`（於 `AutoClaude/` 下執行，rc=0）逐字關鍵欄：

| 欄位 | 值 |
|------|----|
| `status`／`ready_for_labeled_pr` | `ready`／`true` |
| `gate_basis`／`green_streak_required` | `green_streak`／14 |
| `green_streak`／`tolerant_streak`／`strict_streak` | 109／109／109（`tolerant_p95_ms`＝60.0） |
| `observation_streak`（`observation_p95_ms`＝50.0） | 0 |
| `consecutive_failures`／`clock_anomaly`／`staleness_days` | 0／false／0 |
| `caveats` | ① recall 在窗內 14 筆完全相同（0.999）⇒ σ=0.0 是「沒變」不是「驗過了」，`recall σ ≤ 0.02` 判準在本資料上無鑑別力；② 觀察軌（p95 < 50ms）連續綠 0/14 ⇒ 本次 ready **完全**由 60ms 升級門檻成立 |

nightly 觸發源：`AutoClaude/logs/nightly_latest.log:700`（2026-10-25 22:40:21）`[F2 ALERT] AC4 觀察期 #2 已達標 ready_for_labeled_pr=true (tolerant<60ms streak=109/14 observation<50ms streak=0/14; ADR-SD09-008 v0.4 ACCEPTED) — 需 PM 確認啟用 … 並紀錄至 docs/06_quality/SD09_AC4_Activation_Approval.md`。

## 3. 「啟用」的實際意義與影響

- workflow 自 W2 起即為 labeled trigger（`on: pull_request: types: [labeled]`＋`if: github.event.label.name == 'needs-pg-e2e'`），**沒有開關要翻、不改任何程式**；啟用＝PM 同意從即日起對需要真 PG 驗證的 PR 貼 `needs-pg-e2e` 標籤。
- 每次貼標多約 8～12 分鐘 CI（workflow 檔頭自述）；`continue-on-error: true`，不擋 merge。
- **風險**：ready 完全由 60ms 寬鬆門檻成立（嚴格 50ms 觀察指標 0/14）；recall σ 判準無鑑別力。此二者在 caveats 內明示，核准時已知。
- **回退**：停止貼標即停，零程式變更。

## 4. 刻意不做（掌舵者選項）

- nightly 每夜仍會印 `[F2 ALERT]`（`tools/run_local_nightly.ps1` 與 `tools/ac4_nightly_alert_parser.py` 不讀本檔）：掌舵者選「啟用並記核准」而非「啟用並消音」，消音屬另案（需改兩支程式與 `tests/tools/test_ac4_nightly_alert_parser.py`）。
- DBA／PM 兩份 TEMPLATE（`SD09_DBA_DryRun_Sign_W4.md`、`SD09_PM_Release_Approval_W5.md`）是 PG `db_only` 正式上線 G4／G5 的人簽，與 AC4 無關，維持 TEMPLATE（AutoClaude/CLAUDE.md〈Production 上線紅線〉）。

## 5. 關聯

OBS-SI-191（`docs/06_quality/SelfImproving_Observation_Ledger.md`）；`docs/05_development/SD09_Execution_Guide.md` C 議題群 T0-C1／T0-C2；ADR-SD09-008 v0.4。
