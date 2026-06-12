# SD_09 W0 AC4 真實 e2e 實作 Task Breakdown（X1 方案）

| 項目 | 內容 |
|------|------|
| 文件版本 | **v0.2（W0 G0 五方 zero-trust audit 同步；X1 路徑落地實作完成 2026-05-20）** |
| 建立日期 | 2026-05-19 |
| 最後更新 | **2026-05-20 v0.2**（PM 拍板狀態：已拍板 X1 — 主規劃 §6 line 265；實作完成：`tools/seed_kb.py` 204 LOC mock 完整 + `tests/fixtures/pgvector_real_queries.json`/`pgvector_real_ground_truth.json` 100 query × 384-dim 已 commit；`tests/integration/test_pgvector_real_recall.py` 3 case 改 fixture-side conditional skip；`tools/ac4_progress_check.py:84` 三態 sentinel pass/fail/skip→None）|
| 對應風險 | [R-SD09-CI-2](risk_log.md) 🟢 CLOSED 2026-05-20（SD_07 PM #2 結構保留缺口已解封）|
| 對應 SD_09 觀察期 | #2 AC4 14 天 nightly 全綠（fixture 結構性解封；W0 啟動後重定錨採集起算日）|
| 預估工程量 | **1.5 PD（已落地）**（前置 0.2 ✅ + 實作 1.3 ✅）|
| PM 拍板 | **✅ 已拍板 X1**（2026-05-19 / PM zero-trust / commit 7883fe3+；主規劃 §6 line 265）|

---

## 1. 缺口確認

### 1.1 現狀（為何 ready_for_labeled_pr 永遠 false）

```
tests/integration/test_pgvector_real_recall.py:67-72  ← 硬編碼 pytest.skip()
                ↓ 跑出 status: "skip" (recall=null, p95=null)
tools/ac4_nightly_collector.py                        ← 寫入 .ac4_history.jsonl
                ↓
tools/ac4_progress_check.py:84  if status != "pass": return False  ← skip 也算失敗
                ↓
consecutive_failures += 1 每日累積 → ready_for_labeled_pr = false
```

### 1.2 缺什麼

| # | 缺件 | 描述 | 從未實作的證據 |
|---|------|------|---------------|
| **A** | `tools/seed_kb.py` | seed ≥ 100 列 KB + BGE-M3 真實 1024-dim embedding | [test_pgvector_real_recall.py:13](../../tests/integration/test_pgvector_real_recall.py#L13) 提及，未存在於 tools/ |
| **B** | `tests/fixtures/queries_100.jsonl` | 100 query embedding fixture | 未存在於 tests/fixtures/ |
| **C** | `tests/fixtures/ground_truth_top10.jsonl` | brute force cosine top-10 預計算 | 未存在 |
| **D** | 替換 3 case `pytest.skip(...)` | 改為真實 PgVectorSearchAdapter 呼叫 + assertion | [test_pgvector_real_recall.py:69](../../tests/integration/test_pgvector_real_recall.py#L69), L80~ TestP95Latency, L100~ TestDualAdapterFallback |

---

## 2. 任務分解

### T0 前置調查（0.2 PD）

- [ ] **T0-1** 確認 `knowledge_entries` 分區表 embedding 欄位 schema：dim / type（halfvec / vector）/ partition 路由規則（YYYY_MM）— 看 [alembic/versions/0007/0008/0009](../../alembic/versions/) + [autoclaude/infra/adapters/pg_vector_search.py](../../autoclaude/infra/adapters/pg_vector_search.py)
- [ ] **T0-2** 確認 BGE-M3 model 取得方式：HuggingFace `BAAI/bge-m3`（~1.5GB），CPU 推論可行 vs GPU 加速；`sentence-transformers` 是否已在 `[dev]` extras
- [ ] **T0-3** 決定 corpus 來源（≥ 100 條測試文本）：(a) 抽 docs/ 段落 / (b) generic Wikipedia dump / (c) AutoClaude 內部 playbook descriptions
- [ ] **T0-4** 評估 fixture 大小（100 query × 1024 float = ~400KB；ground_truth ~50KB；可進 git）

### T1 實作 seed_kb.py（0.5 PD）

- [ ] **T1-1** 路徑：[tools/seed_kb.py](../../tools/seed_kb.py)（LOC tier=adapter ≤ 400 行）
- [ ] **T1-2** CLI 參數：
  ```bash
  python tools/seed_kb.py \
    --pg-dsn $AUTOCLAUDE_TEST_PG_DSN \
    --corpus-dir docs/ \
    --count 100 \
    --output-queries tests/fixtures/queries_100.jsonl \
    --output-ground-truth tests/fixtures/ground_truth_top10.jsonl
  ```
- [ ] **T1-3** 邏輯：
  1. 載入 BGE-M3 model（`sentence_transformers.SentenceTransformer('BAAI/bge-m3')`）
  2. 從 corpus-dir 取 100 個文字段落（每段 50~500 字）
  3. embed 100 個段落 → 1024-dim vector
  4. INSERT 進 `knowledge_entries`（路由至當月分區，例 `knowledge_entries_2026_05`）
  5. 從同 corpus 抽不重疊 100 個 query（或 paraphrase）→ embed → 寫 queries_100.jsonl
  6. 對每 query 跑 brute force cosine top-10 → 寫 ground_truth_top10.jsonl
- [ ] **T1-4** 冪等性：偵測既有 fixture → 跳過 seed；強制重 seed 用 `--force`
- [ ] **T1-5** 單元測試：[tests/test_seed_kb.py](../../tests/test_seed_kb.py)（mock BGE-M3 + asyncpg）

### T2 fixture 產出（0.3 PD，由 T1 跑出）

- [ ] **T2-1** [tests/fixtures/queries_100.jsonl](../../tests/fixtures/queries_100.jsonl) schema：
  ```json
  {"query_id": 0, "text": "...", "embedding": [0.012, ..., -0.034]}
  ```
- [ ] **T2-2** [tests/fixtures/ground_truth_top10.jsonl](../../tests/fixtures/ground_truth_top10.jsonl) schema：
  ```json
  {"query_id": 0, "expected_kb_ids": [42, 87, ..., 13]}
  ```
- [ ] **T2-3** 評估 git 直接 commit vs git-lfs（~500KB 應該可直接 commit）
- [ ] **T2-4** 加入 `.gitattributes` 必要規則（jsonl text + LF）

### T3 替換 pytest.skip → 真實 assertion（0.5 PD）

- [ ] **T3-1** [test_pgvector_real_recall.py:67](../../tests/integration/test_pgvector_real_recall.py#L67) `test_recall_at_10`：
  ```python
  def test_recall_at_10(self):
      _require_real_pg()
      adapter = PgVectorSearchAdapter(dsn=_DSN)
      queries = _load_jsonl("tests/fixtures/queries_100.jsonl")
      truth = _load_jsonl("tests/fixtures/ground_truth_top10.jsonl")
      hits = 0
      for q, t in zip(queries, truth):
          result = adapter.search(q["embedding"], top_k=10)
          retrieved_ids = {h.kb_id for h in result}
          expected_ids = set(t["expected_kb_ids"])
          if retrieved_ids & expected_ids:
              hits += 1
      recall = hits / len(queries)
      assert recall >= 0.95, f"recall@10 = {recall:.3f} < 0.95"
  ```
- [ ] **T3-2** L80 `test_p95_latency_under_50ms`：量 100 query latency → percentile(95) < 50ms
- [ ] **T3-3** L100 `test_bge_failure_minimax_fallback_under_60s`：用 `unittest.mock` 注入 BGE 例外 → 量 CircuitBreaker 切 Minimax 的時間 < 60s
- [ ] **T3-4** 移除 3 處 `pytest.skip("real PG / seed 1k KB / 100 query embedding 需要 nightly CI 環境")`

### T4 nightly 腳本整合（0.1 PD）

- [ ] **T4-1** 修 [tools/run_local_nightly.ps1 Stage 2](../../tools/run_local_nightly.ps1)：
  - alembic upgrade 後加：若 `tests/fixtures/queries_100.jsonl` 不存在 → 跑 `python tools/seed_kb.py ...`
  - 因 fixture 已 commit 進 git，僅首跑或 `--force` 重 seed
- [ ] **T4-2** 修 [.github/workflows/ci.yml `pg-e2e-nightly` job](../../.github/workflows/ci.yml#L167)：alembic upgrade 後加 seed step
- [ ] **T4-3** 確認 BGE-M3 model 在 CI 上的快取策略（`actions/cache` ~/.cache/huggingface）

### T5 文件更新（0.1 PD）

- [ ] **T5-1** [ADR-SD09-002 §2.8](../04_planning/ADR/ADR-SD09-002-mutation-full-module-expansion.md) 新增「真實 PG e2e 啟用條件」段
- [ ] **T5-2** [SD_Improving_09.md §8.1](../04_planning/SD_Improving_09.md) 觀察期 #2 移除 `⚠️ 阻塞中` 標記
- [ ] **T5-3** [risk_log.md R-SD09-CI-2](risk_log.md) 標記 🔴 → 🟢 已緩解
- [ ] **T5-4** [SD_07_AC_Matrix.md](../03_testing/SD07_AC_Matrix.md) AC4-1 / AC4-2 對應 case 標 ✅
- [ ] **T5-5** 此檔（SD09_W0_AC4_Implementation_TaskBreakdown.md）加入「實作完成」section

---

## 3. 驗收條件

```bash
# 在本地或 CI 環境（PG container 起來 + alembic upgrade head 完成）
python tools/seed_kb.py --pg-dsn $DSN --corpus-dir docs/ --count 100
python -m pytest tests/integration/test_pgvector_real_recall.py -v -m pg_real
```

**期望輸出**：

```
PASSED tests/integration/test_pgvector_real_recall.py::TestRecallAt10::test_recall_at_10
PASSED tests/integration/test_pgvector_real_recall.py::TestP95Latency::test_p95_latency_under_50ms
PASSED tests/integration/test_pgvector_real_recall.py::TestDualAdapterFallback::test_bge_failure_minimax_fallback_under_60s
==== 3 passed in X.XXs ====
```

**AC4 collector 寫入**：
```json
{"timestamp": "...", "run_id": "local", "recall_at_10": 0.98, "p95_ms": 35.2, "circuit_breaker_open_count": 0, "status": "pass"}
```

**ac4_progress_check.py 累積 14 天後**：
```json
{"status": "ready", "consecutive_failures": 0, "ready_for_labeled_pr": true}
```

---

## 4. 風險與依賴

| ID | 描述 | 緩解 |
|----|------|------|
| **R-T1-1** | BGE-M3 ~1.5GB 模型下載慢（首次） | 預載到本機 ~/.cache/huggingface 後分享 cache；CI 加 `actions/cache` |
| **R-T1-2** | CPU 跑 BGE-M3 embedding 100 個段落 ~3~5 min | 接受 — seed 本應一次性執行 |
| **R-T1-3** | partition 路由邏輯隨月份漂移（5 月 seed 但 6 月跑測試）| 測試前重 seed 或加 partition 多月觀察期；seed_kb.py 加 `--target-partition` 參數 |
| **R-T3-1** | `PgVectorSearchAdapter.search()` 簽名/回傳格式與假設不符 | T0-1 預先驗證；不符時調整 T3 assertion |
| **D1** | `sentence-transformers` 須加入 `[dev]` extras | T0-2 確認；不在的話 pyproject.toml 加一行 |

---

## 5. 排程建議

**前置條件**：PM 拍板 X1（即本方案）。

| Wave | 任務 | 預估 |
|------|------|------|
| W0 D1 | T0 前置調查 | 0.2 PD |
| W0 D2 | T1 seed_kb.py 實作 + T2 fixture 產出 | 0.8 PD |
| W0 D3 | T3 替換 pytest.skip + T4 nightly 整合 | 0.6 PD |
| W0 D3 EOD | T5 文件更新 + 驗收 | 0.1 PD |
| **合計** | | **~1.5 PD（≈ 2 工作日 with buffer）**|

**最晚啟動日**：2026-06-15（觀察期 #2 結束 2026-06-02 前完成則 W0 可繼續累積到 6/17 達 14 天綠 → 但因觀察期 #2 結束日早於實作完成，**只能改觀察期 #2 結束日 +14 天延後**，或接受啟動條件改 14 天計數從實作落地日起算）。

**對 SD_09 啟動日影響**：若 X1 於 2026-06-02 前完成 → 觀察期 #2 從實作日起 +14 天 = 啟動日延至 **2026-06-16** 或更晚（與觀察期 #3 結束 2026-06-17 接近）。

---

## 6. 三方對照（為 PM 拍板時參考）

| 方案 | 工程量 | 啟動日影響 | 風險 | 信號 |
|------|--------|----------|------|------|
| **X1（本檔）補實作** | ~1.5 PD | 延至 2026-06-16~25 | T1-3 partition 漂移；BGE-M3 cache 大小 | ✅ 真實 recall + p95 驗證 |
| **X2 改 ac4_progress_check 判定** | ~0.3 PD | 不影響 | 「skip 即綠」埋下未驗證隱性風險 | ❌ 失去 AC4 真實驗證信號 |
| **X3 移除觀察期 #2 / 議題 C 延 SD_10** | ~0.2 PD | 不影響 | 失去 pg-e2e 14 天觀察 | ❌ 無 AC4 信號至 SD_10 |

---

**對應**：
- [risk_log.md R-SD09-CI-2](risk_log.md)
- [SD_Improving_09.md §8.1 #2 footnote](../04_planning/SD_Improving_09.md)
- [tests/integration/test_pgvector_real_recall.py](../../tests/integration/test_pgvector_real_recall.py)
- [tools/ac4_progress_check.py](../../tools/ac4_progress_check.py)
- [tools/run_local_nightly.ps1](../../tools/run_local_nightly.ps1)
