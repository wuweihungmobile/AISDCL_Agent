"""SD_Improving_06 W3-T3-28 — pgvector HNSW recall + latency（AC4-5）。

對應規格：
  - SD_Improving_06.md §6.5 AC4-5：recall@10 ≥ 0.95 + p95 < 50ms
  - SD_Improving_06.md §11 黃線：dual-read fallback（< 0.90 才阻塞）

驗證項目：
  T1 [PG 整合] recall@10 ≥ 0.95（須真實 PG + pgvector + HNSW index）
  T2 [PG 整合] p95 latency < 50ms（單機 1k 列基線）
  T3 [純單元] PgVectorSearchAdapter 在 fake SQL 下能正確序列化 VectorHit
  T4 [純單元] preferred_source='legacy' 時走 legacy 路徑
  T5 [純單元] new 路徑失敗時自動 fallback legacy（KB 表）
  T6 [純單元] new 路徑連續慢呼叫 → breaker open

PG 整合測試 (T1/T2) 需要：
  - AUTOCLAUDE_TEST_PG_DSN 環境變數（含 pgvector / halfvec extension）
  - alembic upgrade head（0007 + 0008 + 0009 ready）
  - 預先 seed 1,000 列 KB 含真實 BGE-M3 embedding
無上述條件 → skip（與 W3 階段 A 既有 PG-skip pattern 一致）。
"""
from __future__ import annotations

import os
import re
import time

import pytest

from autoclaude.core.ports.vector_search import VectorHit, VectorSearchError
from autoclaude.infra.adapters.circuit_breaker import CircuitBreaker
from autoclaude.infra.adapters.pg_vector_search import PgVectorSearchAdapter

_DSN_RAW = os.environ.get("AUTOCLAUDE_TEST_PG_DSN") or os.environ.get("AUTOCLAUDE_DB_DSN")
_DSN = re.sub(r"\+asyncpg", "", _DSN_RAW) if _DSN_RAW else None


# ── 純單元：fake SQL executor ─────────────────────────────────

class _FakeSql:
    def __init__(self, *, rows: list[dict] | None = None, raise_on_new: bool = False,
                 latency_ms: float = 5.0) -> None:
        self.rows = rows or []
        self.raise_on_new = raise_on_new
        self.latency_ms = latency_ms
        self.executed: list[str] = []

    def execute(self, sql: str, params: tuple) -> None:
        self.executed.append(sql[:40])

    def fetch_one(self, sql: str, params: tuple) -> dict:
        return {"ok": 1}

    def fetch_all(self, sql: str, params: tuple) -> list[dict]:
        time.sleep(self.latency_ms / 1000.0)
        if self.raise_on_new and "halfvec" in sql:
            raise RuntimeError("halfvec index unavailable")
        # legacy path 用 "embedding <=>" 識別
        if "embedding <=>" in sql:
            return [{**r, "model_id": "legacy-1536"} for r in self.rows]
        return self.rows


def test_pgvector_adapter_serializes_to_vector_hit():
    """T3 fake SQL 下能轉成 VectorHit + SearchStats（source=new）。"""
    sql = _FakeSql(rows=[
        {"id": "x1", "score": 0.99, "model_id": "bge-m3",
         "payload": {"content": "hello"}}
    ])
    adapter = PgVectorSearchAdapter(sql_executor=sql)
    hits, stats = adapter.search(
        namespace="knowledge_entries",
        query_vector=[0.0] * 1024,
        model_id="bge-m3",
        top_k=1,
    )
    assert isinstance(hits[0], VectorHit)
    assert hits[0].id == "x1"
    assert hits[0].source == "new"
    assert stats.used_fallback is False


def test_pgvector_adapter_preferred_source_legacy():
    """T4 preferred_source='legacy' 強制走 legacy（HNSW 重建期維運開關）。"""
    sql = _FakeSql(rows=[
        {"id": "y1", "score": 0.88, "model_id": "legacy-1536",
         "payload": {"content": "old"}}
    ])
    adapter = PgVectorSearchAdapter(sql_executor=sql, preferred_source="legacy")
    hits, stats = adapter.search(
        namespace="knowledge_entries",
        query_vector=[0.0] * 1536,
        model_id="*",
        top_k=1,
    )
    assert hits[0].source == "legacy"
    assert stats.used_fallback is True


def test_pgvector_adapter_falls_back_on_new_failure():
    """T5 new path 失敗時自動降級至 legacy（僅 KB 表有 legacy 路徑）。"""
    sql = _FakeSql(
        rows=[{"id": "z1", "score": 0.77, "model_id": "legacy-1536", "payload": {}}],
        raise_on_new=True,
    )
    adapter = PgVectorSearchAdapter(sql_executor=sql)
    hits, stats = adapter.search(
        namespace="knowledge_entries",
        query_vector=[0.0] * 1024,
        model_id="bge-m3",
        top_k=1,
    )
    assert stats.used_fallback is True
    assert hits[0].source == "legacy"


def test_pgvector_adapter_breaker_opens_on_slow_calls():
    """T6 連續慢呼叫 (> 200ms) 3 次 → breaker open（觸發降級門檻）。"""
    sql = _FakeSql(
        rows=[{"id": "s1", "score": 0.9, "model_id": "bge-m3", "payload": {}}],
        latency_ms=250.0,
    )
    breaker = CircuitBreaker(
        failure_threshold=99,
        latency_threshold_ms=200.0,
        slow_call_threshold=3,
    )
    adapter = PgVectorSearchAdapter(sql_executor=sql, breaker=breaker)
    for _ in range(3):
        adapter.search(
            namespace="knowledge_entries",
            query_vector=[0.0] * 1024,
            model_id="bge-m3",
            top_k=1,
        )
    assert breaker.state == "open"


def test_pgvector_adapter_namespaces_unknown_raises():
    """T7 未支援 namespace 必須 raise，避免悄悄走錯路徑。"""
    sql = _FakeSql(rows=[])
    adapter = PgVectorSearchAdapter(sql_executor=sql)
    with pytest.raises(VectorSearchError):
        adapter.search(
            namespace="unknown_table",  # type: ignore[arg-type]
            query_vector=[0.0] * 1024,
            model_id="bge-m3",
        )


# ── PG 整合（須真實 DB）─────────────────────────────────────

pg_required = pytest.mark.skipif(
    _DSN is None,
    reason="【未啟用，非缺件】設 AUTOCLAUDE_DB_DSN 或 AUTOCLAUDE_TEST_PG_DSN "
           "＋ `alembic upgrade head` ＋ seed 1k KB rows 即可啟用",
)

# ── 🔴 本輪訂正：reason 指向一個磁碟上不存在的通道 ────────────────────────────────
# 下面兩支的 skip reason 此前結尾都掛著一句「這個通道會跑它」的宣稱，而當回合實查
# `.github/workflows/**` 對 `hnsw`／本檔檔名**零命中**——也就是說 reason 告訴讀者
# 有人在跑，磁碟上沒有任何 job 在跑，而兩份說法從未對帳。
#
# 這比「沒寫」更糟：它讓複審者不再追查（同 `skip_static_scan._predicate_value_on_
# windows` docstring 記載的那次「宣稱有人承接、實際無人承接」）。純形式的可操作性
# 判準（`DEF-101-863` 原本的解鎖條件）放行這種假指路——它形式上指名了一個通道，
# 只是那個通道不存在。**指涉必須被解析**，這是本輪補上的第二半。
#
# 現況（寫現在為真的事）：本檔 T1/T2 需要一組本 repo 尚未建置的 staging 資料
# （1k 列真實 BGE-M3 向量 ＋ HNSW index），**任何自動通道都不跑它**。在該資料集
# 與對應 job 落地之前，這兩支是誠實的零覆蓋，不是「等 nightly」。
# 🔴 R82 包 A2 訂正：本段原本具名的機械物 `SkipReasonChannelClaimTest` **全 repo 不存在**
# （當回合以 Grep 全庫搜該符號，唯一命中就是這一行自己）——那是一筆幽靈機械物，比沒有
# 機械物更難看見：它讓下一個人以為「有人在守通道宣稱」而不再追查。實際存在的是
# `AutoClaude/tests/test_conftest_windows_native_skip_report.py::
# test_every_debt_handover_round_is_still_in_the_future`（R82 落地），它守的是**承接輪次
# 不得過期**，不是通道宣稱。⇒ 「通道宣稱必須可解析」這一面**目前仍無機械物**（誠實劃界）。
_NO_AUTOMATED_CHANNEL = (
    "本 repo 目前沒有任何自動通道會跑這兩支（當回合實查 .github/workflows 對本檔零命中）。"
    "要在本機跑：備妥 1k 列真實 BGE-M3 向量 ＋ HNSW index 的 staging DB，"
    "設 AUTOCLAUDE_TEST_PG_DSN 指向它，再把本行的 skip 拿掉。"
)


@pg_required
def test_pgvector_recall_at_10_ge_095():
    """T1 真實 pgvector HNSW recall@10 ≥ 0.95（AC4-5 上線基線）。"""
    # 🔴 R82 包 A2（DEBT-01）：承接輪次往後推了一輪——修前它逐字寫著**本輪**，而本輪
    # 到來時沒有任何東西會說話，輪號因此可以永遠停在原地。實際輪號只寫在下面那句
    # reason 裡（本註解刻意不複述數字：程式碼註解不得自稱超前帳本的輪號，
    # `test_check_defect_log_crossref.py::TestR71CodeRoundLabelsNeverExceedLedgerCurrentRound`
    # 會當場紅）。全樹逐筆比對見 `test_conftest_windows_native_skip_report.py::
    # test_every_debt_handover_round_is_still_in_the_future`。
    # 🔴 本輪（承接輪次到期的那一輪）：走出口②再推一輪，理由與**可執行的解除條件**
    # 逐字寫在下面那句 reason 裡（不是「下輪處理」）。同輪 AC3-4／AC5-4／AC6-3 三筆走的
    # 是出口①（target 檔已建），本筆之所以不同：它缺的不是斷言，是受測對象本身。
    pytest.skip(
        # 🔴 R85 推遲的理由（第 3 次順延，本輪**不是**「下輪處理」那種空話，理由是可查證的
        # 持有面事實）：本輪 R85 是六包並行波，本包（P3）的持有面只有 `AutoClaude/**`；
        # 而本列的兩個解除條件**各自落在別人的持有面**——
        #   ① 「建自動通道」＝改 `.github/workflows/*.yml` 或 `tools/run_local_nightly.*`
        #      （monorepo 根層，本包唯讀）；
        #   ② 「保留或顯式廢止」＝ SD_06 W3 G3 的 PM 層級門檻決定，本 reason 自己第 4 段
        #      就寫著「修復者不得自行拍板」。
        # ⇒ 這正是根 CLAUDE.md〈鐵律七〉點名的形態：一道鎖的常數／史料／消費端被切給不同
        #   的包，於是它在**任何**單包手上都結不掉，該包唯一能回報的只有 not_done。
        # 🔴 讓這次順延**付出代價**（否則它與前兩次沒有差別）：R85 起本列不接受「再推一輪」
        #   這個出口——承接者只有兩個選擇：把 PM 決定拿到手（保留＋同輪建自動通道／顯式廢止），
        #   或把這兩支測試連同 reason 一起刪除並在帳本留下廢止紀錄。掌舵者未拍板前不得再改
        #   輪號，因為那會第 4 次把「有人負責」的假象續期。
        f"[DEBT] 需 W3 G3 staging 資料集：1k seed + BGE-M3 真實向量。承接輪次 R86"
        f"（該輪必須先決定保留或顯式廢止：保留就得同時建自動通道，"
        f"否則寫好也不會被跑）。"
        f"🔴 本輪再推一輪的理由（非「下輪處理」）：本輪是 macOS 本機輪，缺件是**受測對象**"
        f"而非斷言——BGE-M3 權重與 1k 列 staging 資料集在本機都不存在，"
        f"而在沒有自動通道的前提下把斷言先寫出來，只會把同一筆欠債換成"
        f"「寫好了但永遠不會跑」的另一種假象（那正是本 case 已經付過的學費）。"
        f"🔴 承接輪到期的那一輪（R84）逐項實查後仍推一輪，理由是**解除條件三項全未滿足**、"
        f"且該輪是收斂輪（把跨包干擾造成的紅收掉，不開新戰場）："
        f"①本機無 BGE-M3（1024 維）權重與 ≥1k 列 staging 語料，PG 容器是 CI 對等的空庫；"
        f"②`.github/workflows` 對本檔仍零命中（自動通道未建）；"
        f"③「保留或廢止」是 SD_06 W3 G3 的 PM 層級門檻決定，收斂輪不得代為拍板。"
        f"⇒ 走出口②：顯式推到下一輪，而不是把斷言寫成量不到東西的假綠。"
        f"🔴 解除條件（三項全滿足才做得到，缺一即不得動工）："
        f"①備妥 PG17+pgvector staging，內含 ≥1k 列真實 BGE-M3（1024 維）向量與"
        f"per-table HNSW index（AC3-5 的三個 index）；"
        f"②該環境上 SD07_REAL_PG_E2E_ENABLED=true 且 AUTOCLAUDE_TEST_PG_DSN 指向它；"
        f"③同一個變更內落地會跑本檔的自動通道（CI job 或 nightly stage），"
        f"並在 PR 貼出該通道真的跑過本檔的 log 行。"
        f"🔴 「保留或廢止」是 SD_06 W3 G3 的門檻決定，屬 PM 層級，修復者不得自行拍板。"
        f"{_NO_AUTOMATED_CHANNEL}")


@pg_required
def test_pgvector_p95_latency_under_50ms():
    """T2 真實 pgvector HNSW p95 latency < 50ms。"""
    pytest.skip(
        # 🔴 R85：與 T1 同一筆決定、同一份順延理由（見上方 T1 那段：持有面被切開＋PM 拍板
        # 未到手），故同步推到 R85，並同樣適用「R85 起不接受再推一輪」的到期條款。
        f"[DEBT] 需 W3 G3 staging 資料集（同 T1）。承接輪次 R86"
        f"（保留或顯式廢止的決定與 T1 同一筆）。"
        f"🔴 本輪再推一輪的理由與解除條件與 T1 逐字同一份（見 "
        f"test_pgvector_recall_at_10_ge_095 的 reason）：兩者共用同一個 staging 資料集與"
        f"同一個自動通道，任一項缺件都同時擋住兩支，故刻意不分開推。"
        f"{_NO_AUTOMATED_CHANNEL}")
