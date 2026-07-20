# ADR-SD08-003：Perf Regression Policy — p95 增量 < 15% + 雙軌採集 + annotation/PR comment 雙通道

| 項目 | 內容 |
|------|------|
| 狀態 | **APPROVED（PM 形式核准 / 場景 A 個人開發 dev 自核 2026-05-18；SD_09 W1 修訂 §2.3 / §2.6 升 samples ≥ 20 — 2026-05-21）** |
| 建立日期 | 2026-05-18 |
| 對應 PM 拍板 | SD_08 PM #6（雙軌：CI nightly + perf machine 季度校準）|
| 提案人 | SD（實作可行性主導）|
| 核准日期 | 2026-05-18（SD_08 W0 T0-ADR3）|
| 修訂歷史 | v1.0（2026-05-18，初版）；v1.1（2026-05-21，SD_09 W0 二次/三次 audit S-2 結構性問題 → samples=7 統計噪音必然，升 baseline samples ≥ 20）|

---

## 1. 背景

- AutoClaude 既無 e2e 執行時間 baseline；無回歸告警機制
- **SD 量測警示**：GitHub Actions Ubuntu runner CPU 共享，IO 密集場景（pgvector recall）p95 變異可達 ±50% → 誤報率壓垮開發流程

## 2. 決議

### 2.1 採集環境（雙軌）

| 軌道 | 環境 | 頻率 | 量測場景 | 用途 |
|------|------|------|----------|------|
| **(b) CI nightly** | GitHub Actions ubuntu-latest | 每週一 02:00 UTC（與 pg-e2e-nightly 同步；**R14 修訂**：CI-2 額度裁決 2026-07-20 由每日降週頻，每日訊號改由 Windows 本地 nightly perf-baseline stage 承擔）| **CPU-bound only**：dry_run 全步驟 / TokenHalt 往返 / decide_correction 單次 | 趨勢監控 + 相對閾值 |
| **(c) perf machine** | 專用機（SD_09 採購評估）| 季度（每 3 個月）| **IO/IO-bound**：pgvector recall@10 + p95 / multi-run resume | 絕對基準 + production SLA |

**禁止**：(a) 本地 dev（無法重現 + 無歷史趨勢）

### 2.2 量測場景（4 個核心）

| # | 場景 | 量測檔 | 採集環境 | SLA 目標 |
|---|------|--------|---------|---------|
| 1 | **dry_run 全步驟 e2e**（5 step playbook）| `tests/perf/test_dry_run_e2e.py` | CI nightly | p95 < baseline × 1.15 |
| 2 | **TokenHalt 往返**（halt → /compact → resume）| `tests/perf/test_token_halt_roundtrip.py` | CI nightly | p95 < baseline × 1.15 |
| 3 | **decide_correction 單次**（Minimax → ON_EVENT phase）| `tests/perf/test_decide_correction.py` | CI nightly | p95 < baseline × 1.15 |
| 4 | **pgvector recall@10 + p95**（100 query × 1000 vector）| `tests/perf/test_pgvector_recall_perf.py` | perf machine 季度 | recall ≥ 0.95 + p95 < 50ms |

### 2.3 採集策略（連跑 ≥ 20 次取分位數）

> **v1.1 修訂（2026-05-21 / SD_09 W0 audit S-2）**：
> samples=7 在 Windows + Docker Desktop 環境下 p95 抖動可達 ±80%（c964328 同 commit 不同 run 觀測），
> 統計噪音必然。**升至 samples ≥ 20** 才能寫 baseline / 才能升級判定。
> 採集寬鬆 + 升級嚴格雙軌（W0 P1-G 已落地）：
>   - 採集時 `runs=20`（pytest-benchmark `--benchmark-min-rounds=20`）
>   - `tools/perf_regression_check.py::MIN_BASELINE_SAMPLES=20` 對 < 20 印 warning（不阻塞）
>   - 升級至 baseline lock 必須 `samples ≥ 20` 才可寫入 `.perf_baseline.toml`

```python
# autoclaude/utils/perf_baseline.py
MIN_RUNS = 20  # ADR-SD08-003 v1.1 升級門檻（原 7 → 20）

def measure(scenario: str, runs: int = MIN_RUNS) -> PerfBaseline:
    """連跑 N≥20 次取 p50 / p95 / p99，避免單次抖動。"""
    if runs < MIN_RUNS:
        sys.stderr.write(
            f"::warning::samples={runs} < {MIN_RUNS}; statistical noise high. "
            f"baseline lock 將被拒絕。\n"
        )
    samples = []
    for i in range(runs):
        start = time.perf_counter()
        run_scenario(scenario)
        samples.append((time.perf_counter() - start) * 1000)  # ms
    return PerfBaseline(
        scenario=scenario,
        p50_ms=median(samples),
        p95_ms=percentile(samples, 95),
        p99_ms=percentile(samples, 99),
        samples=runs,
        git_sha=current_sha(),
        captured_at=datetime.now(UTC),
    )
```

### 2.4 告警閾值（p95 增量 < 15%）

| 增量範圍 | 告警等級 | CI 行為 |
|---------|---------|---------|
| **p95 增量 < 10%** | 🟢 通過 | 無動作 |
| **10% ≤ p95 增量 < 15%** | 🟡 警告 | `::warning::` annotation（不阻塞）|
| **p95 增量 ≥ 15%** | 🔴 阻塞 | `::error::` annotation + PR comment + block merge |

> 比題目 (a) 20% 收緊 5% — 為雜訊預留 buffer

### 2.5 雙通道告警設計

`tools/perf_regression_check.py`（W5 新建）：

```python
# 採 GitHub Actions annotation + PR comment 雙通道
# (1) annotation：CI failure 強制 review（::error::）
# (2) PR comment：詳細 diff 表格 + 歷史趨勢圖連結（gh pr comment）
```

PR comment 範本：

```markdown
## ⚠️ Perf Regression Alert（ADR-SD08-003）

| 場景 | Baseline p95 | Current p95 | 增量 | 狀態 |
|------|--------------|-------------|------|------|
| dry_run_e2e | 1,234 ms | 1,420 ms | +15.1% | 🔴 阻塞 |
| token_halt_roundtrip | 567 ms | 590 ms | +4.1% | 🟢 通過 |
| decide_correction | 123 ms | 145 ms | +17.9% | 🔴 阻塞 |

**Action required**：請檢查 commit `abc1234` 是否引入效能退化；查看 [Trend Chart](link)
```

### 2.6 Baseline 鎖定與更新

> **v1.1 修訂（2026-05-21 / SD_09 W0 S-2）**：每筆 baseline 寫入時必須附 `samples ≥ 20`；
> < 20 由 `tools/perf_baseline_lock.py` 拒絕寫入並印 warning（不阻塞 nightly 流程）。

```toml
# .perf_baseline.toml（W5 末鎖定）
[dry_run_e2e]
p50_ms = 1100.0
p95_ms = 1234.5
p99_ms = 1500.0
samples = 20            # v1.1：必須 ≥ 20
captured_at = "2026-06-15T02:00:00Z"
locked_by = "SD_08 W5 G5"

# 更新規則：
# 1. samples ≥ 20 才可寫入 baseline（W3/W5 採集腳本驗證；< 20 印 ::warning::）
# 2. PR merge 後 main branch nightly 連續 7 次達標即更新
# 3. 重大重構（如 SD_09）後由 W6 收尾任務手動 unlock + recapture
```

## 3. CI Job 草稿（W5 落地）

`.github/workflows/autoclaude-ci.yml` 新增 `perf-baseline-nightly` job：

```yaml
perf-baseline-nightly:
  name: Perf Baseline (CPU-bound scenarios) - nightly
  runs-on: ubuntu-latest
  timeout-minutes: 30
  if: github.event_name == 'schedule' || github.event_name == 'workflow_dispatch'
  continue-on-error: true  # nightly 警示，不阻塞 main

  steps:
    - name: Checkout
      uses: actions/checkout@v4
      with:
        fetch-depth: 1

    - name: Set up Python 3.11
      uses: actions/setup-python@v5

    - name: Install dependencies
      run: pip install -e ".[dev]"

    - name: Run perf baseline (4 scenarios × 20 runs) — v1.1
      run: |
        python -m pytest tests/perf/ -v --tb=short \
          --benchmark-only \
          --benchmark-min-rounds=20 \
          --benchmark-json=perf_results.json

    - name: Check regression vs baseline
      run: python tools/perf_regression_check.py perf_results.json .perf_baseline.toml

    - name: Upload perf reports
      if: always()
      uses: actions/upload-artifact@v4
      with:
        name: perf-baseline-${{ github.run_id }}
        path: |
          perf_results.json
          perf_*.log
        retention-days: 90  # 季度趨勢分析
```

## 4. 落地 Checklist（W5 task breakdown）

```
[  ] T5-G1 新建 autoclaude/utils/perf_baseline.py（PerfBaseline dataclass + measure() helper）
[  ] T5-G2 新建 tests/perf/test_dry_run_e2e.py（≥ 1 case + pytest-benchmark）
[  ] T5-G3 新建 tests/perf/test_token_halt_roundtrip.py（≥ 1 case）
[  ] T5-G4 新建 tests/perf/test_decide_correction.py（≥ 1 case）
[  ] T5-G5 新建 tests/perf/test_pgvector_recall_perf.py（≥ 1 case，pg_real marker，僅 perf machine 跑）
[  ] T5-G6 新建 tools/perf_regression_check.py（雙通道告警）
[  ] T5-G7 .github/workflows/autoclaude-ci.yml 新增 perf-baseline-nightly job
[  ] T5-G8 首次跑 7 次連續，鎖定 .perf_baseline.toml
[  ] T5-G9 補 tests/contract/test_perf_regression_check.py（≥ 4 case：通過 / 警告 / 阻塞 / 缺 baseline）
[  ] T5-G10 產 docs/06_quality/SD08_Perf_Baseline_Report.md（W5 末，含 4 場景 baseline 數字）
```

## 5. 退化風險緩解（連動 R-SD08-G-1）

| 風險 | 緩解 |
|------|------|
| pgvector p95 在 CI runner 變異 ±50% | pgvector 場景**強制**跑 perf machine（季度校準），CI 僅跑 CPU-bound（dry_run / TokenHalt / decide_correction）|
| 連續多次小幅退化堆積（< 15% 但累計）| 季度 perf machine 校準時與 3 個月前對比，若累計 > 25% 觸發 P1 |
| Perf machine SD_09 才採購，SD_08 無絕對基準 | SD_08 僅做相對閾值；絕對基準等 SD_09 |

## 6. 簽核

| 角色 | 狀態 | 日期 |
|------|------|------|
| SD | ✅ 實作可行性主導 | 2026-05-18 |
| Architect | ✅ 共識（雙軌策略一致）| 2026-05-18 |
| PM | ✅ 形式核准（場景 A 個人開發 dev 自核）| 2026-05-18 |
| QA | ✅ v1.1 修訂（samples ≥ 20）核准 | 2026-05-21 |
| PM | ✅ v1.1 修訂（採集寬鬆 + 升級嚴格雙軌）核准 | 2026-05-21 |

---

**相關文件**：
- [SD_Improving_08.md](../SD_Improving_08.md) v1.0 §6 PM 拍板 #6
