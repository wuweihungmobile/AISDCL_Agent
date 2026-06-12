# SD_Improving_08 W5 — Perf Baseline Report v1.0

| 項目 | 內容 |
|------|------|
| 文件版本 | **v1.0（W5 T5-G10 落地）** |
| 建立日期 | 2026-05-18 |
| 對應 ADR | [ADR-SD08-003](../04_planning/ADR/ADR-SD08-003-perf-regression-policy.md) Perf Regression Policy |
| 對應 Sprint Wave | SD_Improving_08 W5 |
| 採集環境 | 本地（Win11 Pro / Python 3.11.9 / git e65bcee）— 首次鎖定 |
| 適用範圍 | **CPU-bound 場景**（pgvector 延 perf machine） |

---

## 1. 量測場景與 SLA（ADR-SD08-003 §2.2）

| # | 場景 | 量測檔 | 採集環境 | SLA |
|---|------|--------|---------|------|
| 1 | dry_run 全步驟 e2e | [test_dry_run_e2e.py](../../tests/perf/test_dry_run_e2e.py) | CI nightly | p95 < baseline × 1.15 |
| 2 | TokenHalt 往返 | [test_token_halt_roundtrip.py](../../tests/perf/test_token_halt_roundtrip.py) | CI nightly | p95 < baseline × 1.15 |
| 3 | decide_correction 單次 | [test_decide_correction.py](../../tests/perf/test_decide_correction.py) | CI nightly | p95 < baseline × 1.15 |
| 4 | pgvector recall@10 + p95 | [test_pgvector_recall_perf.py](../../tests/perf/test_pgvector_recall_perf.py) | **perf machine 季度** | recall ≥ 0.95 + p95 < 50ms |

> ⚠️ 場景 4 在 CI runner 預設 SKIP（R-SD08-G-1：pgvector p95 在 GitHub Actions ubuntu-latest 變異 ±50%，必須延 perf machine 季度校準）。

---

## 2. 首次鎖定 baseline 數字（SD_08 W5）

採集：連跑 7 次取 p50 / p95 / p99（ADR-SD08-003 §2.3）。

| 場景 | p50 (ms) | p95 (ms) | p99 (ms) | samples | git_sha |
|------|----------|----------|----------|---------|---------|
| dry_run_e2e | 0.243 | 0.258 | 0.258 | 7 | e65bcee |
| token_halt_roundtrip | 0.001 | 0.006 | 0.006 | 7 | e65bcee |
| decide_correction | 0.002 | 1.705 | 1.705 | 7 | e65bcee |

> **本機數字僅供 W5 框架驗證**；正式 baseline 由 `perf-baseline-nightly` job 在 ubuntu-latest runner 連跑 7 個 nightly 後覆寫（ADR-SD08-003 §2.6 更新規則）。
>
> 鎖定檔：[.perf_baseline.toml](../../.perf_baseline.toml)

---

## 3. 告警閾值（ADR-SD08-003 §2.4）

| 增量範圍 | 等級 | CI 行為 |
|---------|------|---------|
| p95 增量 < 10% | 🟢 通過 | 無動作 |
| 10% ≤ 增量 < 15% | 🟡 警告 | `::warning::` annotation（非阻塞） |
| 增量 ≥ 15% | 🔴 阻塞 | `::error::` annotation + PR comment + exit=1 |

實作：[`tools/perf_regression_check.py`](../../tools/perf_regression_check.py)。
雙通道（annotation + `perf_regression_comment.md`）。

---

## 4. CI Job 設計（ADR-SD08-003 §3）

```yaml
perf-baseline-nightly:
  name: Perf Baseline (CPU-bound scenarios) - nightly
  runs-on: ubuntu-latest
  timeout-minutes: 30
  if: schedule || workflow_dispatch
  continue-on-error: true       # nightly 警示，不阻塞 main
```

完整定義：[.github/workflows/ci.yml](../../.github/workflows/ci.yml) §perf-baseline-nightly。

---

## 5. 退化風險緩解（連動 R-SD08-G-1）

| 風險 | 緩解 |
|------|------|
| pgvector p95 在 CI runner 變異 ±50% | 場景 4 強制延 perf machine 季度（R-SD08-G-1 / 紅線 ❌20 部分） |
| 連續多次小幅退化堆積（< 15% 但累計） | 季度 perf machine 校準時與 3 個月前對比 > 25% 觸發 P1 |
| Perf machine SD_09 才採購，SD_08 無絕對基準 | SD_08 僅做相對閾值；絕對基準等 SD_09（ADR-SD08-003 §5） |

---

## 6. 後續行動（SD_09 接續）

- **採購 perf machine 評估**：建議規格 / 預算 / 季度排程
- **絕對基準鎖定**：場景 4 pgvector p95 < 50ms 在 perf machine 跑 7 次連續達標
- **趨勢分析**：每季度 ubuntu-latest 連跑 90 天 history 對比

---

## 7. 文件版本歷史

| 版本 | 日期 | 內容 |
|------|------|------|
| v1.0 | 2026-05-18 | SD_08 W5 T5-G10 首次鎖定；場景 1-3 CI nightly baseline；場景 4 延 perf machine |
