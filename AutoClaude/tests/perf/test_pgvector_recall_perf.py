"""pgvector recall@10 + p95 性能 baseline（SD_08 W5 / ADR-SD08-003 §2.2 場景 #4）。

採集環境：**perf machine 季度**（NOT CI nightly — R-SD08-G-1 紅線）
SLA 目標：recall ≥ 0.95 + p95 < 50ms

CI 上預設 SKIP；僅在帶 `pg_real` marker 的 perf machine 上跑（SD_09 採購評估）。

SD_09 W0 Pre-W0 audit B-07 修復（2026-05-20）：
  - 移除 placeholder `pass` workload
  - 改為 100 query × adapter.search(top_k=10) 真實負載
  - 維持 PG_REAL_ENABLED=0 時 skip（pg_real marker）

🔴 R79（D-skipped #4）——**這支從 2026-06-12 落地起一次都沒被執行過，而它壞了**：
  · 通道面：全 repo 沒有任何地方設 `PG_REAL_ENABLED`（當回合 Grep 實測：11 支 workflow
    零命中、`run_local_nightly.{ps1,sh}` 零命中、`tools/*.ps1` 零命中），也就是說它代言的
    ADR-SD08-003「p95 < 50ms」SLA 從來沒有被這支量過。
  · 實作面：首次真跑（本輪自己開的通道）立刻 `TypeError:
    PgVectorSearchAdapter.__init__() got an unexpected keyword argument 'dsn'` ——建構子
    要的是 `sql_executor`（DSN 走 `from_dsn()` 工廠），而 `search()` 的參數是
    `namespace=／query_vector=／model_id=／top_k=`，不是 `query_embedding=`。兩處簽章都對
    不上，且原碼還帶著 `# noqa: F841 — adapter signature may differ` 這句自白。
  · R76 把它歸進「誠實劃界、補不了」那一格（理由是「跑不到」）——那句話對，但它讓後續三輪
    都以為問題只是通道。實況是兩層：跑不到，而且跑得到也是壞的。**凡是被歸進「不可覆蓋」
    的格子，都可能藏著同型的第二層。**

本輪修的三件事：①簽章對齊真實 adapter（`from_dsn` ＋ 具名參數）；②前置條件由 docstring
升格為 code（語料必須真的在這顆 DB 裡，否則量到的 p95 是「查空表」的 p95——與姊妹檔
`tests/integration/test_pgvector_real_recall.py` 的 `_require_seeded_corpus` 同一個教訓）；
③skip 理由全部帶分群標籤，讓 `tools/lib/skip_tag_policy.py` 的分群天花板數得到它。

通道（R79 落地）：`pg-e2e-nightly` job 已備妥本檔所需的**全部**條件（pgvector service
container ＋ postgres extras ＋ DSN ＋ `alembic upgrade head` ＋ `seed_kb.py` seed），
缺的只是 `PG_REAL_ENABLED` 這一個環境變數與一行 pytest 呼叫——兩者本輪都補進該 job。
本機跑法（🔴 R83 補齊 bash/zsh 那一半——原文只有 `$env:…` 這種 PowerShell 專屬形態，
mac/Linux 讀者照抄無效）＋ DSN ＋ 先跑一次 `tools/seed_kb.py --mock-pg-seed`：

  PowerShell：  $env:PG_REAL_ENABLED = '1'
  bash / zsh：  export PG_REAL_ENABLED='1'
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

import pytest

from autoclaude.utils.perf_baseline import measure

pytestmark = [pytest.mark.perf, pytest.mark.pg_real]


_PG_REAL_ENABLED = os.environ.get("PG_REAL_ENABLED", "0") == "1"

#: 與姊妹檔 `tests/integration/test_pgvector_real_recall.py` 同一個常數語意：語料與
#: ground truth 只在「同一次 seed 之內」成立，故這裡只驗「這顆 DB 有沒有夠多帶向量的列」。
_MIN_CORPUS_ROWS = 100
_SEED_HINT = (
    "先跑 `python tools/seed_kb.py --mock-pg-seed --pg-dsn <同一個 DSN>`"
    "（它會同時寫 PG 與 tests/fixtures/ 兩份檔，兩者必須同一次產出）"
)


def _sync_dsn() -> str | None:
    """psycopg2 用的同步 DSN（`+asyncpg` 必須剝掉——`from_dsn()` 走 psycopg2）。"""
    raw = os.environ.get("AUTOCLAUDE_TEST_PG_DSN") or os.environ.get("AUTOCLAUDE_DB_DSN")
    return re.sub(r"\+asyncpg", "", raw) if raw else None


@pytest.mark.skipif(
    not _PG_REAL_ENABLED,
    # 🔴 R82 包 A2（ENV-01）：訂正**措辭**，保留 opt-in。原字串前半逐字寫「僅在 perf
    # machine 跑」，讀起來像「你得先弄一台專用機器」——那句話讓分流者把它歸進「做不到」。
    # 實測：本機不是 perf machine，設一個環境變數就跑得完（`1 passed in 5.12s`）。
    # 但同一支在機器忙的時候實測 `p95=51.703ms ≥ 50.0ms` ⇒ 它量的是**延遲 SLA**、對負載
    # 敏感。所以正確的說法不是「需要 perf machine」也不是「其實隨時可以跑」，而是
    # **「隨時跑得起來，但只有在機器閒著時量出來的數字才算數」**——這也是它必須維持
    # opt-in 的理由（本輪一度把它接進 conftest 自動打開，被上面那次 51.7ms 打回來）。
    reason="[ENV-DISABLED] pgvector recall 延遲 SLA 未啟用——**未啟用，非缺件**（本機實測"
           "設一個環境變數即跑完，5.12s）。維持 opt-in 的理由是它量的是延遲、對機器負載"
           "敏感：R82 在忙碌時量到 p95=51.703ms ≥ 50ms，預設打開會變成 flaky 閘門。"
           # 🔴 R83：配方原本只有 PowerShell 形態，mac/Linux 讀者照抄無效——一則 reason 的
           # 全部價值就是「照著做就能讓它跑起來」，只在一個平台成立等於對另一半讀者失效。
           "配方（機器閒置時跑）——PowerShell：`$env:PG_REAL_ENABLED = '1'; python -m pytest "
           "tests/perf/test_pgvector_recall_perf.py`；bash / zsh："
           "`export PG_REAL_ENABLED='1'; python -m pytest "
           "tests/perf/test_pgvector_recall_perf.py`（DSN 由 conftest 的 PG autodetect "
           "自動注入）。R-SD08-G-1",
)
def test_pgvector_recall_baseline_perf_machine_only():
    """真實 pgvector recall 量測（有 PG 就跑；`-m perf` 才是「只在 perf machine 跑」的載具）。

    SD_09 B-07：100 query × adapter.search(top_k=10) 真實負載。
    fixture 缺失時 skip（X1 路徑 tests/fixtures/pgvector_real_queries.json）。
    """
    queries_path = Path("tests/fixtures/pgvector_real_queries.json")
    if not queries_path.exists():
        pytest.skip(
            f"[TOOL-ABSENCE] fixture 缺失：{queries_path}；{_SEED_HINT}（X1 路徑）"
        )

    queries = json.loads(queries_path.read_text(encoding="utf-8"))
    if len(queries) < 100:
        pytest.skip(f"[TOOL-ABSENCE] query 數量不足：{len(queries)} < 100；{_SEED_HINT}")

    # 真實 PG 連線需 SD07_REAL_PG_E2E_ENABLED；perf machine 既然開了 PG_REAL_ENABLED 即假設 PG 就緒
    dsn = _sync_dsn()
    if not dsn:
        pytest.skip(
            "[ENV-DISABLED] AUTOCLAUDE_TEST_PG_DSN 未設定 — perf machine 預期應提供 DSN"
        )

    # 延遲 import：避免 CI runner skip path 觸發 psycopg / asyncpg 載入
    import psycopg2

    from autoclaude.infra.adapters.pg_vector_search import PgVectorSearchAdapter

    # 🔴 前置條件升格為 code：語料不在這顆 DB 裡時，下面量到的是「查空表」的 p95
    # （HNSW 掃 0 列必然遠快於 50ms）⇒ SLA 會以一個**看起來很好**的假數字通過。
    # 這正是本檔要防的形態，所以是 skip 而不是讓它綠。
    with psycopg2.connect(dsn) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT count(*) FROM knowledge_entries WHERE embedding_v IS NOT NULL")
        corpus_rows = cur.fetchone()[0]
    if corpus_rows < _MIN_CORPUS_ROWS:
        pytest.skip(
            f"[TOOL-ABSENCE] 本 DB 只有 {corpus_rows} 列帶 embedding 的 knowledge_entries"
            f"（需 ≥ {_MIN_CORPUS_ROWS}）⇒ 缺件，不是實作問題。{_SEED_HINT}"
        )

    adapter = PgVectorSearchAdapter.from_dsn(dsn)
    selected_queries = queries[:100]
    cursor = iter(selected_queries)

    def _workload() -> None:
        """**一次** adapter.search(top_k=10) 真實 pgvector HNSW 查詢＝一個樣本。"""
        q = next(cursor)
        adapter.search(
            namespace="knowledge_entries",
            query_vector=q["embedding"],
            model_id="*",
            top_k=10,
        )

    # 🔴 R79：`runs` 由 7 改為 100、每個樣本由「100 次查詢」改為「1 次查詢」。
    # 這**不是**調參數，是修單位錯誤：`measure()` 把每一次 `_workload()` 呼叫記成一個
    # 樣本，而舊碼的 `_workload` 一次跑 100 個 query ⇒ 量到的 p95 是「一整批 100 次查詢」
    # 的耗時，卻拿去和**每次查詢** 50ms 的 SLA 比，差 100 倍。本輪首次真跑實測
    # p95=4403.8ms（＝每次查詢約 44ms），舊寫法會把一台其實達標的機器判成違反 SLA 88 倍。
    # 順帶滿足 ADR-SD08-003 v1.1 的 `MIN_RUNS=20`（7 個樣本會印 statistical-noise 警告，
    # 且 `_percentile` 在 n<20 時直接退化成取最大值＝根本不是 p95）。
    baseline = measure("pgvector_recall_perf", _workload, runs=len(selected_queries))

    # 絕對 SLA（perf machine 限定）。門檻沿用姊妹檔 `tests/integration/
    # test_pgvector_real_recall.py` 既有的同一個 env 覆寫（預設 50.0 不變——CI/Linux 走
    # 預設值；Windows + Docker Desktop 才由跑的人顯式放寬，這是 repo 既有機制，
    # 不是本輪為了讓數字好看而調高門檻）。
    threshold_ms = float(os.environ.get("AUTOCLAUDE_TEST_P95_THRESHOLD_MS", "50.0"))
    assert baseline.p95_ms < threshold_ms, (
        f"pgvector recall p95={baseline.p95_ms}ms ≥ {threshold_ms}ms"
        f"（perf machine SLA 違反；樣本數 {baseline.samples}，每個樣本＝1 次 search）"
    )

    _record_baseline(baseline)


def _record_baseline(baseline) -> None:
    """SD_09 B-08：注入 module-level registry，供 conftest 收集。"""
    import sys

    mod = sys.modules.get("tests.perf.conftest")
    if mod is not None and hasattr(mod, "_PERF_RESULTS"):
        mod._PERF_RESULTS.append(baseline)
