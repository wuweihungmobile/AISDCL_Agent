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


# improving_62（v0.24，B L5 telemetry 活體化）autouse 隔離 — 與 _isolate_meta_loop_ledger 同精神。
# WHY：v0.24 把 SDD_ENABLE_RULE_FIRE_TELEMETRY / SDD_ENABLE_RULE_CATCH_TELEMETRY 預設翻為 **ON**
#   （production 活體常態）。fire 遙測在**每次 transition** 都呼叫 rule_loader.record_state_fires(dst)
#   寫 RULES_DIR（凍結 governance/rules/ 的真實 R-*.yaml）。測試套中未顯式隔離 RULES_DIR 的裸
#   transition 測試（test_chaos / test_decision_trace / test_e2e_smoke / test_phase_h /
#   test_timeout_checker / test_trajectory_predictor）若吃到預設 ON，會把 fire_count 寫穿凍結本體
#   → 髒樹 + 跨測試非確定。本 session 級 autouse fixture 把測試套**預設**兩 flag 顯式設為 "0"
#   （opt-out），使既有測試行為 **byte-identical v0.23 零退化**、零污染凍結 governance。
#   ── 不影響 telemetry 翻環的活體驗收：wiring 測試（test_rule_fire/catch_telemetry_wiring）以
#   function 級 monkeypatch.delenv(...) 覆寫本預設來驗「unset → 預設 ON 活體」，且各自以隔離
#   RULES_DIR（tmp）承接寫入；setenv("1") 的明確 ON 案同樣覆寫。production 出貨仍 ON——本隔離
#   純為「保護凍結本體不被測試 side-effect 污染」，與 meta-ledger 隔離同屬測試基建紀律。
@pytest.fixture(scope="session", autouse=True)
def _isolate_rule_telemetry_default():
    """測試套預設關閉兩 telemetry flag（opt-out），保護凍結 governance；wiring 測試自行覆寫。"""
    _ENVS = ("SDD_ENABLE_RULE_FIRE_TELEMETRY", "SDD_ENABLE_RULE_CATCH_TELEMETRY")
    prior = {k: os.environ.get(k) for k in _ENVS}
    for k in _ENVS:
        os.environ[k] = "0"
    try:
        yield
    finally:
        for k in _ENVS:
            if prior[k] is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = prior[k]


# improving_63（v0.25，B L5 鷹架代謝活體化）autouse 隔離 — 與 _isolate_rule_telemetry_default 同精神。
# WHY：v0.25 把 SDD_ENABLE_SCAFFOLD_GC_AUTO_PROPOSE 預設翻為 **ON**（production 活體常態）。進
#   SCAFFOLD_GC 態（enter_scaffold_gc）會自動跑 scaffold_gc.run_gc 並落盤 SCAFFOLD-ROI 報告至
#   GC_REPORT_DIR（預設 build/reports/gc/）。測試套中**未顯式 redirect GC_REPORT_DIR、未設 flag**
#   的裸 enter_scaffold_gc 測試（test_phase_h::test_scaffold_gc_enter_exit_continue /
#   ::test_scaffold_gc_respec）若吃到預設 ON，會把真實報告寫穿 build/reports/gc/ → 髒樹 + 跨測試
#   非確定。本 session 級 autouse fixture 把測試套**預設**該 flag 顯式設為 "0"（opt-out），使既有
#   測試行為 **byte-identical v0.24 零退化**、零污染 runtime 工作區。── 不影響翻環活體驗收：wiring
#   測試（test_scaffold_gc_auto_propose_wiring）以 function 級 monkeypatch.delenv(...) 覆寫本預設來
#   驗「unset → 預設 ON 自動跑 GC」，且以 _redirect_gc_report 把報告導向 tmp；setenv("1") 的明確
#   ON 案同樣覆寫。production 出貨仍 ON——本隔離純為「保護 runtime 工作區不被測試 side-effect 污染」。
@pytest.fixture(scope="session", autouse=True)
def _isolate_scaffold_gc_default():
    """測試套預設關閉 scaffold GC auto-propose flag（opt-out），杜絕裸 enter_scaffold_gc 落盤污染。"""
    _ENV = "SDD_ENABLE_SCAFFOLD_GC_AUTO_PROPOSE"
    prior = os.environ.get(_ENV)
    os.environ[_ENV] = "0"
    try:
        yield
    finally:
        if prior is None:
            os.environ.pop(_ENV, None)
        else:
            os.environ[_ENV] = prior
