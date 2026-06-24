"""Pytest 共用 fixtures（Phase L 接線隔離）.

Phase L M-L1 / ACT-090：`exit_learning_commit("approved")` 與 `set_maturity()` 已接線
到生產路徑的 `meta_halt_monitor`，會對**預設** meta-loop ledger 落帳。為避免既有測試
（test_slv_generator / test_phase_h / test_phase_j 等並未顯式指定 ledger_path 者）污染
repo 的真實 `build/state/meta-loop-ledger.yaml`，本 session 級 autouse fixture 把預設
ledger 重導向到一個臨時目錄（透過 meta_ledger 既有的 `SDD_META_LEDGER_PATH` 覆寫鉤子）。

顯式指定 `ledger_path=tmp_path/...` 的測試完全不受影響（覆寫只改「未指定時的預設」）。
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest


@pytest.fixture(scope="session", autouse=True)
def _isolate_meta_loop_ledger():
    """把預設 meta-loop ledger 路徑導向 session 級 tmp，杜絕生產接線污染 repo。"""
    prior = os.environ.get("SDD_META_LEDGER_PATH")
    with tempfile.TemporaryDirectory(prefix="sdd-meta-ledger-") as td:
        os.environ["SDD_META_LEDGER_PATH"] = str(Path(td) / "meta-loop-ledger.yaml")
        try:
            yield
        finally:
            if prior is None:
                os.environ.pop("SDD_META_LEDGER_PATH", None)
            else:
                os.environ["SDD_META_LEDGER_PATH"] = prior
