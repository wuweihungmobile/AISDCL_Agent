"""SD_09 W0 議題 C 觀察期 #2 — pgvector real recall fixture 播種工具。

對應 SD_07 PM #2 真實 PG e2e「結構保留」缺口修復：
    - tests/integration/test_pgvector_real_recall.py 3 case 移除硬編碼 pytest.skip
    - 100 query embedding fixture + ground truth 播種
    - ac4_progress_check._is_green() 三態 sentinel（status=skip 視為中性）對齊

模式：
    --mock              僅寫 fixture 檔（不寫 PG，384-dim）
    --mock-pg-seed      X1 路徑：寫 fixture 且寫 PG（1024-dim；需 --pg-dsn）
    --pg-dsn DSN        真實模式（需 BGE-M3；本工具尚未啟用，graceful exit 0）

對應（SD_09 W2 / W3 更新）：
    - SD09_W0_AC4_Implementation_TaskBreakdown.md X1 補實作路徑
    - risk_log §15 R-SD09-CI-2
    - SD09_Pre_W0_Audit_Findings.md
    - SD_09 W2 audit P2-AUDIT-27 註解過時修正（2026-05-21）：
      原指 ac4_progress_check.py:84（status 判定），現已重構為 _is_green() 三態 sentinel
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
from pathlib import Path
from typing import Iterable

_REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_EMBEDDING_DIM = 384  # BGE-M3 dense head 為 1024，但純 mock 採 384 以節省 fixture 體積
DEFAULT_MOCK_PG_DIM = 1024  # X1 路徑：與 halfvec(1024) 對齊
DEFAULT_COUNT = 100
DEFAULT_TOP_K = 10
DEFAULT_SEED = 20260520


def _normalize(vec: list[float]) -> list[float]:
    norm = math.sqrt(sum(v * v for v in vec))
    if norm == 0.0:
        # 避免除以 0，回傳 unit vector at axis 0
        out = [0.0] * len(vec)
        out[0] = 1.0
        return out
    return [v / norm for v in vec]


def _random_normalized(rng: random.Random, dim: int) -> list[float]:
    raw = [rng.gauss(0.0, 1.0) for _ in range(dim)]
    return _normalize(raw)


def _cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def _top_k_ids(query: list[float], doc_ids: list[str], doc_vecs: list[list[float]], k: int) -> list[str]:
    sims = [(doc_ids[i], _cosine(query, doc_vecs[i])) for i in range(len(doc_ids))]
    sims.sort(key=lambda x: x[1], reverse=True)
    return [doc_id for doc_id, _ in sims[:k]]


def generate_mock_fixtures(
    count: int = DEFAULT_COUNT,
    dim: int = DEFAULT_EMBEDDING_DIM,
    top_k: int = DEFAULT_TOP_K,
    seed: int = DEFAULT_SEED,
) -> tuple[list[dict], dict[str, list[str]]]:
    """產生 mock queries fixture + ground truth。

    Returns:
        (queries, ground_truth)
        queries:       [{"id": "q0", "embedding": [...]}, ...]
        ground_truth:  {"q0": ["doc_3", "doc_17", ...], ...}
    """
    rng = random.Random(seed)

    # 為了讓 self-similarity 可計算，建立 doc corpus（同樣 count 筆）
    # 並把每個 query 與其對應的 doc 設成「同 query 但加少量擾動」，確保 top-1 有 ground truth
    doc_ids = [f"doc_{i}" for i in range(count)]
    doc_vecs = [_random_normalized(rng, dim) for _ in range(count)]

    queries: list[dict] = []
    ground_truth: dict[str, list[str]] = {}
    for i in range(count):
        # query_i 由 doc_i 加擾動構成（保證可 recall）
        noise = [rng.gauss(0.0, 0.05) for _ in range(dim)]
        q_vec = _normalize([d + n for d, n in zip(doc_vecs[i], noise)])
        q_id = f"q{i}"
        queries.append({"id": q_id, "embedding": q_vec})
        ground_truth[q_id] = _top_k_ids(q_vec, doc_ids, doc_vecs, top_k)

    return queries, ground_truth


def _validate_queries(queries: Iterable[dict], dim: int) -> None:
    seen_ids: set[str] = set()
    for idx, q in enumerate(queries):
        if not isinstance(q, dict):
            raise ValueError(f"query[{idx}] not a dict")
        if "id" not in q or "embedding" not in q:
            raise ValueError(f"query[{idx}] missing 'id' or 'embedding'")
        if q["id"] in seen_ids:
            raise ValueError(f"duplicate query id: {q['id']}")
        seen_ids.add(q["id"])
        emb = q["embedding"]
        if not isinstance(emb, list) or len(emb) != dim:
            raise ValueError(
                f"query[{idx}] embedding dim mismatch: got {len(emb) if isinstance(emb, list) else type(emb)}"
            )
        norm = math.sqrt(sum(v * v for v in emb))
        if abs(norm - 1.0) > 1e-3:
            raise ValueError(f"query[{idx}] not normalized (||v||={norm:.4f})")


def _validate_ground_truth(gt: dict[str, list[str]], queries: list[dict], top_k: int) -> None:
    q_ids = {q["id"] for q in queries}
    for q_id, doc_list in gt.items():
        if q_id not in q_ids:
            raise ValueError(f"ground_truth has unknown query id: {q_id}")
        if not isinstance(doc_list, list) or len(doc_list) != top_k:
            raise ValueError(
                f"ground_truth[{q_id}] length mismatch: got {len(doc_list) if isinstance(doc_list, list) else type(doc_list)}, want {top_k}"
            )


def _write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def seed_pg_mock(
    dsn: str,
    count: int = DEFAULT_COUNT,
    dim: int = DEFAULT_MOCK_PG_DIM,
    top_k: int = DEFAULT_TOP_K,
    seed: int = DEFAULT_SEED,
) -> tuple[list[dict], dict[str, list[str]]]:
    """X1 路徑：寫入 mock knowledge_entries 至 PG，並回傳 fixture 資料。

    - 生成 count 筆 dim 維向量，INSERT 至 knowledge_entries（embedding_v halfvec）
    - 若已有 ≥ count 筆 embedding_v IS NOT NULL 的資料，跳過 INSERT（idempotent）
    - ground truth 使用實際 DB entry_id（UUID）確保測試可還原
    """
    import re as _re
    import psycopg2
    import psycopg2.extras

    # strip asyncpg 確保 psycopg2 可用
    sync_dsn = _re.sub(r"\+asyncpg", "", dsn)
    conn = psycopg2.connect(sync_dsn)
    conn.autocommit = True

    rng = random.Random(seed)
    doc_vecs = [_random_normalized(rng, dim) for _ in range(count)]

    # 檢查是否已 seed（idempotent）
    with conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM knowledge_entries "
            "WHERE embedding_v IS NOT NULL AND error_class LIKE 'mock_class_%'"
        )
        existing = cur.fetchone()[0]

    if existing >= count:
        print(f"[SKIP] PG 已有 {existing} 筆 mock 資料（≥ {count}），跳過 seed。", file=sys.stderr)
        # 讀回既有的 UUIDs + 向量重建 ground truth
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT entry_id::text, embedding_v::text "
                "FROM knowledge_entries "
                "WHERE embedding_v IS NOT NULL AND error_class LIKE 'mock_class_%' "
                # 必須按數字順序（mock_class_0,1,...,99）確保 doc_uuids[i] 對應 doc_vecs[i]
                # ORDER BY error_signature 為字母序（10 < 2），導致 uuid↔vector 錯位 → recall≈0.17
                "ORDER BY CAST(SPLIT_PART(error_class, '_', 3) AS INTEGER) "
                f"LIMIT {count}"
            )
            rows = cur.fetchall()
        doc_uuids = [r["entry_id"] for r in rows]
        # 重建 query + ground truth（相同 seed → 相同向量）
        queries: list[dict] = []
        ground_truth: dict[str, list[str]] = {}
        for i in range(count):
            noise = [rng.gauss(0.0, 0.05) for _ in range(dim)]
            q_vec = _normalize([d + n for d, n in zip(doc_vecs[i], noise)])
            q_id = f"q{i}"
            queries.append({"id": q_id, "embedding": q_vec})
            ground_truth[q_id] = _top_k_ids(q_vec, doc_uuids, doc_vecs, top_k)
        conn.close()
        return queries, ground_truth

    # 插入 mock entries
    doc_uuids: list[str] = []
    vec_str_list: list[str] = []
    for vec in doc_vecs:
        vec_str_list.append("[" + ",".join(f"{v:.6f}" for v in vec) + "]")

    with conn.cursor() as cur:
        for i, (vec_str, vec) in enumerate(zip(vec_str_list, doc_vecs)):
            cur.execute(
                "INSERT INTO knowledge_entries "
                "  (error_class, error_signature, step_id, outcome, "
                "   embedding_v, embedding_model_id, embedding_status) "
                "VALUES (%s, %s, %s, %s, %s::halfvec, %s, %s) "
                "RETURNING entry_id::text",
                (
                    f"mock_class_{i}",
                    f"mock_sig_{i}_{seed}",
                    f"mock_step_{i}",
                    "success",
                    vec_str,
                    "mock-1024",
                    "ok",
                ),
            )
            row = cur.fetchone()
            doc_uuids.append(row[0])

    print(f"[OK] Inserted {len(doc_uuids)} mock entries into knowledge_entries.", file=sys.stderr)

    # 生成 query + ground truth（使用實際 UUID）
    queries = []
    ground_truth = {}
    rng2 = random.Random(seed)
    doc_vecs2 = [_random_normalized(rng2, dim) for _ in range(count)]
    for i in range(count):
        noise = [rng2.gauss(0.0, 0.05) for _ in range(dim)]
        q_vec = _normalize([d + n for d, n in zip(doc_vecs2[i], noise)])
        q_id = f"q{i}"
        queries.append({"id": q_id, "embedding": q_vec})
        ground_truth[q_id] = _top_k_ids(q_vec, doc_uuids, doc_vecs2, top_k)

    conn.close()
    return queries, ground_truth


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="SD_09 W0 議題 C 觀察期 #2 — pgvector real recall fixture 播種"
    )
    parser.add_argument("--mock", action="store_true", help="僅寫 fixture 檔（不寫 PG，384-dim）")
    parser.add_argument(
        "--mock-pg-seed", action="store_true",
        help="X1 路徑：寫 fixture 且寫 PG mock 資料（1024-dim；需 --pg-dsn）",
    )
    parser.add_argument(
        "--pg-dsn", type=str, default=None,
        help="PostgreSQL DSN（--mock-pg-seed / 真實模式）",
    )
    parser.add_argument(
        "--corpus-dir", type=Path, default=None,
        help="真實模式語料目錄（每檔一段文字）",
    )
    parser.add_argument(
        "--count", type=int, default=DEFAULT_COUNT,
        help=f"產生 query 筆數（預設 {DEFAULT_COUNT}）",
    )
    parser.add_argument(
        "--dim", type=int, default=None,
        help="embedding 維度（預設：--mock=384 / --mock-pg-seed=1024）",
    )
    parser.add_argument(
        "--top-k", type=int, default=DEFAULT_TOP_K,
        help=f"ground truth 取前 K（預設 {DEFAULT_TOP_K}）",
    )
    parser.add_argument(
        "--seed", type=int, default=DEFAULT_SEED,
        help="隨機種子（決定 mock 輸出 deterministic）",
    )
    parser.add_argument(
        "--output-queries", type=Path,
        default=_REPO_ROOT / "tests" / "fixtures" / "pgvector_real_queries.json",
        help="輸出 query embedding fixture 路徑",
    )
    parser.add_argument(
        "--output-ground-truth", type=Path,
        default=_REPO_ROOT / "tests" / "fixtures" / "pgvector_real_ground_truth.json",
        help="輸出 ground truth fixture 路徑",
    )
    args = parser.parse_args(argv)

    # X1 路徑：mock-pg-seed — 同時寫 PG + fixture（1024-dim）
    if args.mock_pg_seed:
        if not args.pg_dsn:
            print("[ERROR] --mock-pg-seed 需要 --pg-dsn 參數。", file=sys.stderr)
            return 1
        dim = args.dim or DEFAULT_MOCK_PG_DIM
        queries, gt = seed_pg_mock(
            dsn=args.pg_dsn, count=args.count, dim=dim,
            top_k=args.top_k, seed=args.seed,
        )
        _validate_queries(queries, dim)
        _validate_ground_truth(gt, queries, args.top_k)
        _write_json(args.output_queries, queries)
        _write_json(args.output_ground_truth, gt)
        print(
            f"[OK] mock-pg-seed: queries={args.output_queries} "
            f"({len(queries)} entries, dim={dim}); "
            f"ground_truth={args.output_ground_truth} ({len(gt)} entries)"
        )
        return 0

    if args.mock:
        dim = args.dim or DEFAULT_EMBEDDING_DIM
        queries, gt = generate_mock_fixtures(
            count=args.count, dim=dim, top_k=args.top_k, seed=args.seed,
        )
        _validate_queries(queries, dim)
        _validate_ground_truth(gt, queries, args.top_k)
        _write_json(args.output_queries, queries)
        _write_json(args.output_ground_truth, gt)
        print(
            f"[OK] mock fixtures generated: "
            f"queries={args.output_queries} ({len(queries)} entries, dim={dim}); "
            f"ground_truth={args.output_ground_truth} ({len(gt)} entries, top_k={args.top_k})"
        )
        return 0

    # 真實模式：需 --pg-dsn + --corpus-dir，且需 BGE-M3 / pgvector
    if not args.pg_dsn or not args.corpus_dir:
        print(
            "[SKIP] 未指定 --mock / --mock-pg-seed 且缺少 --pg-dsn / --corpus-dir；"
            "真實模式需 BGE-M3 + pgvector 環境（SD_09 W0 尚未啟用）。graceful exit 0。",
            file=sys.stderr,
        )
        return 0

    # 真實模式 placeholder
    print(
        "[NOT-ENABLED] 真實 PG 模式尚未啟用 BGE-M3 + pgvector 整合；"
        "待 SD_09 議題 C 完整落地。graceful exit 0 不阻塞 nightly。",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
