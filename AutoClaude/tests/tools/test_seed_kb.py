"""tools/seed_kb.py 單元測試 — DEF-200-305（驗證鏡子；CLAUDE.md 紀律 #4）。

驗證兩件事：
    1. `_write_json` 產物一律 LF、不含 `\\r`（Windows text-mode 預設會轉譯；
       比照 test_perf_baseline_lock.py::test_write_baseline_produces_no_cr_def_200_300
       對 `.toml` 的既有樣式，這裡驗證 `.json`）。
    2. `--mock-pg-seed` 預設不再覆寫 `tests/fixtures/pgvector_real_*.json`——
       DEF-200-305 訂正（複審 SA-1）：`pgvector_real_ground_truth.json` 全 repo
       零消費者（連 test_pgvector_real_recall.py 自己都就地 seed／讀值，不讀這份
       檔），PG 端 entry_id（UUID）每次 truncate/reinsert 全換，寫檔只會製造每晚
       無意義的 diff commit；`pgvector_real_queries.json` 則由
       tests/perf/test_pgvector_recall_perf.py 唯讀消費，但該測試只驗 p95
       latency、不驗 recall，且用固定亂數種子重建 embedding，不需要與當次 PG
       資料配對，故 tracked 版本可長期沿用。兩者皆僅在使用者明確帶
       `--output-queries`／`--output-ground-truth` 兩者（人工重生的顯式意圖）
       時才重寫。
"""
from __future__ import annotations

import json
from unittest.mock import patch

from tools import seed_kb


def test_write_json_produces_no_cr(tmp_path):
    path = tmp_path / "x.json"
    seed_kb._write_json(path, {"a": 1})
    raw = path.read_bytes()
    assert b"\r" not in raw


def test_write_json_creates_parent_dirs(tmp_path):
    path = tmp_path / "nested" / "dir" / "x.json"
    seed_kb._write_json(path, {"a": 1})
    assert json.loads(path.read_text(encoding="utf-8")) == {"a": 1}


def _fake_seed_pg_mock(*, dsn, count, dim, top_k, seed):
    """替身：不連 PG，回傳形狀正確（維度／normalize／top_k 長度皆合法）的資料，
    讓 `_validate_queries`／`_validate_ground_truth` 走真實驗證路徑。"""
    queries = [{"id": "q0", "embedding": [1.0] + [0.0] * (dim - 1)}]
    ground_truth = {"q0": [f"doc_{i}" for i in range(top_k)]}
    return queries, ground_truth


def test_mock_pg_seed_default_does_not_write_tracked_fixture():
    """DEF-200-305：未帶明確 --output-queries/--output-ground-truth 時，
    mock-pg-seed 完全不呼叫 `_write_json`（不寫任何 fixture 檔）。"""
    with (
        patch.object(seed_kb, "seed_pg_mock", side_effect=_fake_seed_pg_mock),
        patch.object(seed_kb, "_write_json") as mock_write,
    ):
        rc = seed_kb.main(["--mock-pg-seed", "--pg-dsn", "postgresql://x"])
    assert rc == 0
    mock_write.assert_not_called()


def test_mock_pg_seed_explicit_output_paths_still_write(tmp_path):
    """明確帶兩個 --output-* 旗標時仍可人工重生 fixture 檔（顯式意圖保留）。"""
    out_queries = tmp_path / "q.json"
    out_gt = tmp_path / "gt.json"
    with patch.object(seed_kb, "seed_pg_mock", side_effect=_fake_seed_pg_mock):
        rc = seed_kb.main(
            [
                "--mock-pg-seed",
                "--pg-dsn",
                "postgresql://x",
                "--output-queries",
                str(out_queries),
                "--output-ground-truth",
                str(out_gt),
            ]
        )
    assert rc == 0
    assert out_queries.exists()
    assert out_gt.exists()
    assert json.loads(out_queries.read_text(encoding="utf-8"))[0]["id"] == "q0"


def test_mock_pg_seed_partial_output_flag_still_skips_write():
    """只帶其中一個 --output-* 旗標視同未明確指定（需兩者皆備），不寫檔。"""
    with (
        patch.object(seed_kb, "seed_pg_mock", side_effect=_fake_seed_pg_mock),
        patch.object(seed_kb, "_write_json") as mock_write,
    ):
        rc = seed_kb.main(
            [
                "--mock-pg-seed",
                "--pg-dsn",
                "postgresql://x",
                "--output-queries",
                "/tmp/only-one.json",
            ]
        )
    assert rc == 0
    mock_write.assert_not_called()


def test_mock_branch_still_writes_defaults_when_unspecified(tmp_path):
    """--mock（純 mock、不連 PG）不受 DEF-200-305 影響，未指定 --output-* 時
    仍寫入呼叫端指定的路徑（此處以明確路徑驗證寫入行為本身未被破壞）。"""
    out_queries = tmp_path / "q.json"
    out_gt = tmp_path / "gt.json"
    rc = seed_kb.main(
        [
            "--mock",
            "--count",
            "20",
            "--top-k",
            "5",
            "--output-queries",
            str(out_queries),
            "--output-ground-truth",
            str(out_gt),
        ]
    )
    assert rc == 0
    assert out_queries.exists()
    assert out_gt.exists()
